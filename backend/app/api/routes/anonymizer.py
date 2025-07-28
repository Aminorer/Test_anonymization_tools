from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import io
import json
import logging
from datetime import datetime

from app.models.entities import (
    Entity, EntityTypeEnum, AnalyzeResponse, EntityStats, 
    CustomEntity, GenerateRequest, ENTITY_TYPES
)
from app.services.nlp_analyzer import nlp_analyzer
from app.services.document_processor import document_processor
from app.services.session_manager import session_manager
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document(
    file: UploadFile = File(...),
    mode: str = Form("standard")
):
    """
    Analyse un document et retourne les entités détectées
    """
    try:
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        file_extension = file.filename.split('.')[-1].lower()
        if f".{file_extension}" not in settings.SUPPORTED_FILE_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"Format non supporté. Formats acceptés: {', '.join(settings.SUPPORTED_FILE_TYPES)}"
            )
        
        # Validation de la taille
        file_content = await file.read()
        if len(file_content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Fichier trop volumineux. Taille maximum: {settings.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Validation du mode
        if mode not in ["standard", "approfondi"]:
            mode = "standard"
        
        logger.info(f"Analyse du document: {file.filename} en mode {mode}")
        
        # 1. Traitement du fichier (PDF→DOCX ou DOCX direct)
        processed_document, extracted_text = document_processor.process_uploaded_file(
            file_content, file.filename
        )
        
        # 2. Analyse des entités
        entities = nlp_analyzer.analyze_document(extracted_text, mode)
        
        # 3. Génération des statistiques
        stats = _generate_entity_stats(entities)
        
        # 4. Session en cache (30min)
        session_id = session_manager.create_session(
            processed_document, extracted_text, entities, file.filename
        )
        
        # 5. Préparation de la réponse
        entity_responses = []
        for entity in entities:
            entity_response = {
                "id": entity.id,
                "text": entity.text,
                "type": entity.type.value,
                "subtype": getattr(entity, 'subtype', None),
                "start": entity.start,
                "end": entity.end,
                "occurrences": entity.occurrences,
                "confidence": entity.confidence,
                "selected": True,  # Par défaut sélectionné
                "replacement": entity.replacement,
                "valid": getattr(entity, 'valid', True),
                "source": entity.source
            }
            entity_responses.append(entity_response)
        
        # Aperçu du texte (limité à 3000 caractères)
        text_preview = extracted_text[:3000] + "..." if len(extracted_text) > 3000 else extracted_text
        
        logger.info(f"Analyse terminée: {len(entities)} entités détectées pour {file.filename}")
        
        return AnalyzeResponse(
            success=True,
            session_id=session_id,
            filename=file.filename,
            text_preview=text_preview,
            entities=entity_responses,
            stats=stats
        )
    
    except ValueError as e:
        logger.error(f"Erreur de validation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/add-entity")
async def add_custom_entity(
    session_id: str = Form(...),
    text: str = Form(...),
    entity_type: str = Form(...),
    replacement: str = Form(...)
):
    """
    Ajoute une entité personnalisée à la session
    """
    try:
        # Récupération de la session
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        # Validation que le texte existe dans le document
        if text not in session_data['original_text']:
            raise HTTPException(status_code=400, detail="Texte non trouvé dans le document")
        
        # Validation du type d'entité
        try:
            entity_type_enum = EntityTypeEnum(entity_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Type d'entité invalide")
        
        # Création de la nouvelle entité
        new_entity = Entity(
            text=text,
            type=entity_type_enum,
            start=session_data['original_text'].find(text),
            end=session_data['original_text'].find(text) + len(text),
            confidence=1.0,  # Entité manuelle = confiance maximale
            source='manual',
            replacement=replacement,
            occurrences=session_data['original_text'].count(text)
        )
        
        # Récupération des entités existantes
        existing_entities = [Entity(**entity_data) for entity_data in session_data['entities']]
        
        # Vérification des doublons
        for existing_entity in existing_entities:
            if existing_entity.text.lower() == text.lower():
                raise HTTPException(status_code=400, detail="Cette entité existe déjà")
        
        # Ajout de la nouvelle entité
        existing_entities.append(new_entity)
        
        # Mise à jour de la session
        session_manager.update_session_entities(session_id, existing_entities)
        
        logger.info(f"Entité manuelle ajoutée: '{text}' -> '{replacement}' (session: {session_id})")
        
        return {
            "success": True,
            "entity": {
                "id": new_entity.id,
                "text": new_entity.text,
                "type": new_entity.type.value,
                "replacement": new_entity.replacement,
                "occurrences": new_entity.occurrences,
                "confidence": new_entity.confidence,
                "source": new_entity.source
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout d'entité manuelle: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/generate")
async def generate_anonymized_document(
    session_id: str = Form(...),
    selected_entities: str = Form(...)  # JSON string des entités sélectionnées
):
    """
    Génère le document DOCX anonymisé selon les choix utilisateur
    """
    try:
        # Parsing des entités sélectionnées
        try:
            entities_data = json.loads(selected_entities)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Format JSON invalide pour les entités")
        
        # Récupération de la session
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        # Récupération du document original
        document = session_manager.get_document_from_session(session_id)
        if not document:
            raise HTTPException(status_code=500, detail="Document introuvable dans la session")
        
        # Création du mapping de remplacement
        replacements = {}
        for entity_data in entities_data:
            if entity_data.get("selected", False):
                original_text = entity_data.get("text", "")
                replacement_text = entity_data.get("replacement", "")
                if original_text and replacement_text:
                    replacements[original_text] = replacement_text
        
        if not replacements:
            raise HTTPException(status_code=400, detail="Aucune entité sélectionnée pour l'anonymisation")
        
        logger.info(f"Génération document anonymisé: {len(replacements)} remplacements (session: {session_id})")
        
        # Application de l'anonymisation globale (rechercher/remplacer)
        anonymized_docx_bytes = document_processor.apply_global_replacements(document, replacements)
        
        # Génération du log d'audit RGPD
        audit_log = session_manager.generate_audit_log(session_id, replacements)
        
        # Log d'audit pour traçabilité
        logger.info(f"Document anonymisé généré: {session_data['filename']} - {audit_log.entities_anonymized} entités")
        
        # Nettoyage de la session (conformité RGPD)
        session_manager.delete_session(session_id)
        
        # Préparation du nom de fichier
        original_filename = session_data['filename']
        filename_without_ext = '.'.join(original_filename.split('.')[:-1])
        anonymized_filename = f"anonymized_{filename_without_ext}.docx"
        
        # Retour du fichier anonymisé
        return StreamingResponse(
            io.BytesIO(anonymized_docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={anonymized_filename}",
                "X-Audit-Log": json.dumps(audit_log.dict()),
                "X-RGPD-Compliant": "true"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la génération du document: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du document")

@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Récupère les informations d'une session
    """
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        return {
            "success": True,
            "session_id": session_id,
            "filename": session_data['filename'],
            "created_at": session_data['created_at'],
            "expires_at": session_data['expires_at'],
            "entities_count": len(session_data['entities']),
            "text_length": len(session_data['original_text'])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de session: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/stats")
async def get_application_stats():
    """
    Retourne les statistiques de l'application
    """
    try:
        session_stats = session_manager.get_session_stats()
        
        return {
            "success": True,
            "application": {
                "name": settings.APP_NAME,
                "version": settings.VERSION,
                "rgpd_compliant": True,
                "supported_formats": settings.SUPPORTED_FILE_TYPES
            },
            "sessions": session_stats,
            "entity_types": {
                "total_types": len(ENTITY_TYPES),
                "types": list(ENTITY_TYPES.keys())
            }
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

def _generate_entity_stats(entities: List[Entity]) -> EntityStats:
    """Génère les statistiques des entités détectées"""
    by_type = {}
    selected_count = 0
    
    for entity in entities:
        # Compter par type
        entity_type = entity.type.value
        by_type[entity_type] = by_type.get(entity_type, 0) + 1
        
        # Compter les sélectionnées (toutes par défaut)
        if getattr(entity, 'selected', True):
            selected_count += 1
    
    return EntityStats(
        total_entities=len(entities),
        by_type=by_type,
        selected_count=selected_count
    )