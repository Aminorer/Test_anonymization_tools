from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
import io
import json
import logging
from datetime import datetime

from app.models.entities import (
    Entity, EntityTypeEnum, AnalyzeResponse, EntityStats, 
    CustomEntity, GenerateRequest, ENTITY_TYPES, EntityGroup,
    EntityModification, GroupEntitiesRequest
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
    MODE STANDARD : Regex uniquement (téléphone, SIRET, email, adresse)
    MODE APPROFONDI : Regex + SpaCy NER (+ noms et organisations)
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
        
        logger.info(f"🚀 ANALYSE {mode.upper()} - Fichier: {file.filename}")
        
        # 1. Traitement du fichier
        processed_document, extracted_text = document_processor.process_uploaded_file(
            file_content, file.filename
        )
        logger.info(f"✅ Document traité: {len(extracted_text)} caractères extraits")
        
        # 2. Analyse des entités
        entities = nlp_analyzer.analyze_document(extracted_text, mode)
        logger.info(f"✅ Analyse terminée: {len(entities)} entités détectées")
        
        # 3. Génération des statistiques
        stats = _generate_entity_stats_safe(entities)
        
        # 4. Session en cache
        session_id = session_manager.create_session(
            processed_document, extracted_text, entities, file.filename
        )
        logger.info(f"✅ Session créée: {session_id}")
        
        # 5. Préparation de la réponse
        entity_responses = []
        for i, entity in enumerate(entities):
            # Règles de sélection par défaut
            default_selected = True
            type_value = entity.type.value if hasattr(entity.type, 'value') else str(entity.type)
            
            # Références juridiques décochées par défaut
            if 'RÉFÉRENCE' in type_value or 'JURIDIQUE' in type_value:
                default_selected = False
            
            entity_response = {
                "id": entity.id,
                "text": entity.text,
                "type": type_value,
                "subtype": getattr(entity, 'subtype', None),
                "start": entity.start,
                "end": entity.end,
                "occurrences": entity.occurrences,
                "confidence": entity.confidence,
                "selected": default_selected,
                "replacement": entity.replacement,
                "valid": getattr(entity, 'valid', True),
                "source": entity.source,
                "group_id": getattr(entity, 'group_id', None),
                "is_grouped": getattr(entity, 'is_grouped', False),
                "group_variants": getattr(entity, 'group_variants', [])
            }
            entity_responses.append(entity_response)
        
        # Aperçu du texte (sécurisé)
        text_preview = extracted_text[:3000] + "..." if len(extracted_text) > 3000 else extracted_text
        
        logger.info(f"🎯 ANALYSE RÉUSSIE: {file.filename} - {len(entity_responses)} entités prêtes")
        
        return AnalyzeResponse(
            success=True,
            session_id=session_id,
            filename=file.filename,
            text_preview=text_preview,
            entities=entity_responses,
            stats=stats
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 ERREUR CRITIQUE ANALYSE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne : {str(e)[:200]}")

@router.post("/add-entity")
async def add_custom_entity(
    session_id: str = Form(...),
    text: str = Form(...),
    entity_type: str = Form(...),
    replacement: str = Form(...)
):
    """Ajoute une entité personnalisée à la session"""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        # Validation du type d'entité
        try:
            entity_type_enum = EntityTypeEnum(entity_type)
        except ValueError:
            entity_type_enum = EntityTypeEnum.PERSONNE
        
        # Création de la nouvelle entité
        text_position = session_data['original_text'].find(text)
        if text_position == -1:
            text_position = 0
        
        new_entity = Entity(
            text=text,
            type=entity_type_enum,
            start=text_position,
            end=text_position + len(text),
            confidence=1.0,
            source='manual',
            replacement=replacement,
            occurrences=session_data['original_text'].count(text) if text in session_data['original_text'] else 1
        )
        
        # Récupération et mise à jour des entités existantes
        existing_entities = _get_entities_from_session(session_data)
        
        # Vérification des doublons
        for existing_entity in existing_entities:
            if existing_entity.text.lower() == text.lower():
                raise HTTPException(status_code=400, detail="Cette entité existe déjà")
        
        existing_entities.append(new_entity)
        session_manager.update_session_entities(session_id, existing_entities)
        
        logger.info(f"✅ Entité manuelle ajoutée: '{text}' -> '{replacement}'")
        
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
        logger.error(f"🚨 ERREUR AJOUT ENTITÉ: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/modify-entity")
async def modify_entity(
    session_id: str = Form(...),
    entity_id: str = Form(...),
    new_text: str = Form(...),
    new_replacement: str = Form(None)
):
    """Modifie une entité existante"""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        existing_entities = _get_entities_from_session(session_data)
        
        # Trouver et modifier l'entité
        entity_found = False
        for i, entity in enumerate(existing_entities):
            if entity.id == entity_id:
                existing_entities[i].text = new_text.strip()
                if new_replacement:
                    existing_entities[i].replacement = new_replacement.strip()
                
                # Recalculer les occurrences
                original_text = session_data.get('original_text', '')
                existing_entities[i].occurrences = original_text.count(new_text.strip())
                existing_entities[i].source = 'manual_modified'
                
                entity_found = True
                break
        
        if not entity_found:
            raise HTTPException(status_code=404, detail="Entité introuvable")
        
        session_manager.update_session_entities(session_id, existing_entities)
        logger.info(f"✅ Entité modifiée: {entity_id} -> '{new_text}'")
        
        return {
            "success": True,
            "entity": {
                "id": entity_id,
                "text": new_text.strip(),
                "replacement": new_replacement.strip() if new_replacement else None
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 ERREUR MODIFICATION ENTITÉ: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/group-entities-by-text")
async def group_entities_by_text(
    session_id: str = Form(...),
    entity_texts: str = Form(...),
    group_name: str = Form(...),
    group_replacement: str = Form(...)
):
    """Groupe plusieurs entités par leur texte (méthode robuste)"""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        # Parser les textes d'entités
        try:
            entity_texts_list = json.loads(entity_texts)
            if not isinstance(entity_texts_list, list) or len(entity_texts_list) < 2:
                raise ValueError("Au moins 2 entités requises pour créer un groupe")
            
            entity_texts_list = [text.strip() for text in entity_texts_list if text.strip()]
            logger.info(f"🔗 Groupement par texte pour: {entity_texts_list}")
            
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Format invalide: {str(e)}")
        
        # Récupération des entités et groupes existants
        existing_entities = _get_entities_from_session(session_data)
        existing_groups = session_data.get('entity_groups', [])
        if not isinstance(existing_groups, list):
            existing_groups = []
        
        # Créer le nouveau groupe
        group = EntityGroup(
            name=group_name.strip(),
            entity_ids=[],
            replacement=group_replacement.strip(),
            entity_type=EntityTypeEnum.PERSONNE
        )
        
        # Chercher les entités par texte (robuste)
        grouped_entities = []
        entity_found_count = 0
        
        for i, entity in enumerate(existing_entities):
            entity_text_clean = entity.text.strip().lower()
            
            for target_text in entity_texts_list:
                target_text_clean = target_text.strip().lower()
                
                if entity_text_clean == target_text_clean:
                    logger.info(f"✅ Entité trouvée: '{entity.text}' (ID: {entity.id})")
                    
                    # Marquer comme groupée
                    existing_entities[i].group_id = group.id
                    existing_entities[i].is_grouped = True
                    existing_entities[i].replacement = group_replacement.strip()
                    
                    grouped_entities.append(entity)
                    group.entity_ids.append(entity.id)
                    entity_found_count += 1
                    
                    if len(grouped_entities) == 1:
                        group.entity_type = entity.type
                    
                    break
        
        # Vérification
        if entity_found_count < 2:
            available_texts = [entity.text for entity in existing_entities]
            logger.error(f"❌ Textes cherchés: {entity_texts_list}")
            logger.error(f"❌ Textes disponibles: {available_texts}")
            
            raise HTTPException(
                status_code=400, 
                detail=f"Seulement {entity_found_count} entité(s) trouvée(s). Minimum 2 requis."
            )
        
        # Mise à jour de la session
        existing_groups.append(group.dict())
        
        success = session_manager.update_session_data(session_id, {
            'entities': [e.dict() for e in existing_entities],
            'entity_groups': existing_groups
        })
        
        if not success:
            raise HTTPException(status_code=500, detail="Erreur mise à jour session")
        
        logger.info(f"✅ Groupe créé: '{group_name}' avec {entity_found_count} entités")
        
        return {
            "success": True,
            "group": {
                "id": group.id,
                "name": group.name,
                "entity_count": entity_found_count,
                "replacement": group.replacement,
                "entities_found": [e.text for e in grouped_entities]
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 ERREUR GROUPEMENT: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/ungroup-entities")
async def ungroup_entities(
    session_id: str = Form(...),
    group_id: str = Form(...)
):
    """Supprime un groupe d'entités"""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        existing_entities = _get_entities_from_session(session_data)
        existing_groups = session_data.get('entity_groups', [])
        
        # Trouver et supprimer le groupe
        group_found = False
        updated_groups = []
        
        for group_data in existing_groups:
            if isinstance(group_data, dict) and group_data.get('id') == group_id:
                group_found = True
                # Dégrouper les entités
                for i, entity in enumerate(existing_entities):
                    if entity.group_id == group_id:
                        existing_entities[i].group_id = None
                        existing_entities[i].is_grouped = False
                        # Restaurer le remplacement par défaut
                        config = ENTITY_TYPES.get(str(entity.type), {})
                        existing_entities[i].replacement = config.get('default_replacement', f'ANONYME_{i}')
            else:
                updated_groups.append(group_data)
        
        if not group_found:
            raise HTTPException(status_code=404, detail="Groupe introuvable")
        
        # Mise à jour de la session
        success = session_manager.update_session_data(session_id, {
            'entities': [e.dict() for e in existing_entities],
            'entity_groups': updated_groups
        })
        
        if not success:
            raise HTTPException(status_code=500, detail="Erreur mise à jour session")
        
        logger.info(f"✅ Groupe supprimé: {group_id}")
        
        return {"success": True, "message": "Groupe supprimé avec succès"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 ERREUR DÉGROUPEMENT: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.post("/generate")
async def generate_anonymized_document(
    session_id: str = Form(...),
    selected_entities: str = Form(...)
):
    """Génère le document DOCX anonymisé avec le nouveau moteur intelligent"""
    try:
        # Parsing des entités sélectionnées
        try:
            entities_data = json.loads(selected_entities)
            if not isinstance(entities_data, list):
                raise ValueError("Format de données invalide")
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail="Format JSON invalide")
        
        # Récupération de la session
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        # Récupération du document original
        document = session_manager.get_document_from_session(session_id)
        if not document:
            raise HTTPException(status_code=500, detail="Document introuvable")
        
        # Filtrer seulement les entités sélectionnées
        selected_entities_data = [e for e in entities_data if e.get("selected", False)]
        
        if not selected_entities_data:
            raise HTTPException(status_code=400, detail="Aucune entité sélectionnée")
        
        # Récupération des groupes
        groups_data = session_data.get('entity_groups', [])
        
        logger.info(f"🚀 Génération intelligente: {len(selected_entities_data)} entités, {len(groups_data)} groupes")
        
        # Application de l'anonymisation intelligente
        try:
            anonymized_docx_bytes = document_processor.apply_intelligent_replacements(
                document, selected_entities_data, groups_data
            )
        except Exception as e:
            logger.error(f"Erreur anonymisation: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de l'anonymisation")
        
        # Génération du log d'audit RGPD
        try:
            replacements = {e['text']: e['replacement'] for e in selected_entities_data}
            groups_count = len(groups_data)
            audit_log = session_manager.generate_audit_log(session_id, replacements, groups_count)
        except Exception as e:
            logger.error(f"Erreur audit log: {e}")
            audit_log = None
        
        # Nettoyage de la session
        try:
            session_manager.delete_session(session_id)
        except Exception as e:
            logger.warning(f"Erreur nettoyage session: {e}")
        
        # Préparation du nom de fichier
        original_filename = session_data.get('filename', 'document.docx')
        filename_parts = original_filename.split('.')
        filename_without_ext = '.'.join(filename_parts[:-1]) if len(filename_parts) > 1 else original_filename
        anonymized_filename = f"anonymized_{filename_without_ext}.docx"
        
        logger.info(f"✅ Document anonymisé généré: {anonymized_filename}")
        
        # Préparation des headers
        headers = {
            "Content-Disposition": f"attachment; filename={anonymized_filename}",
            "X-RGPD-Compliant": "true"
        }
        
        if audit_log:
            try:
                headers["X-Audit-Log"] = json.dumps(audit_log.dict())
            except:
                pass
        
        return StreamingResponse(
            io.BytesIO(anonymized_docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 ERREUR GÉNÉRATION: {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du document")

@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Récupère les informations d'une session"""
    try:
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        return {
            "success": True,
            "session_id": session_id,
            "filename": session_data.get('filename', 'unknown'),
            "created_at": session_data.get('created_at', ''),
            "expires_at": session_data.get('expires_at', ''),
            "entities_count": len(session_data.get('entities', [])),
            "groups_count": len(session_data.get('entity_groups', [])),
            "text_length": len(session_data.get('original_text', ''))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 ERREUR SESSION INFO: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/stats")
async def get_application_stats():
    """Retourne les statistiques de l'application"""
    try:
        try:
            session_stats = session_manager.get_session_stats()
        except:
            session_stats = {"active_sessions": 0, "total_entities": 0}
        
        return {
            "success": True,
            "application": {
                "name": settings.APP_NAME,
                "version": settings.VERSION,
                "rgpd_compliant": True,
                "supported_formats": settings.SUPPORTED_FILE_TYPES,
                "mode": "REGEX_SPACY_INTELLIGENT"  # Nouveau mode intelligent
            },
            "sessions": session_stats,
            "entity_types": {
                "total_types": len(ENTITY_TYPES),
                "types": list(ENTITY_TYPES.keys())
            }
        }
    
    except Exception as e:
        logger.error(f"🚨 ERREUR STATS: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

# Fonctions utilitaires
def _get_entities_from_session(session_data: Dict) -> List[Entity]:
    """Récupère les entités de la session de manière robuste"""
    entities = []
    for entity_data in session_data.get('entities', []):
        try:
            if isinstance(entity_data, dict):
                entities.append(Entity(**entity_data))
            else:
                entities.append(entity_data)
        except Exception as e:
            logger.debug(f"Erreur parsing entité: {e}")
            continue
    return entities

def _generate_entity_stats_safe(entities: List[Entity]) -> EntityStats:
    """Génère les statistiques des entités de manière sécurisée"""
    try:
        if not entities:
            return EntityStats(
                total_entities=0,
                by_type={},
                selected_count=0,
                grouped_count=0
            )
        
        by_type = {}
        selected_count = 0
        grouped_count = 0
        
        for entity in entities:
            try:
                # Compter par type
                entity_type = getattr(entity, 'type', None)
                if entity_type:
                    type_key = entity_type.value if hasattr(entity_type, 'value') else str(entity_type)
                    by_type[type_key] = by_type.get(type_key, 0) + 1
                
                # Compter les sélectionnées
                if getattr(entity, 'selected', True):
                    selected_count += 1
                
                # Compter les groupées
                if getattr(entity, 'is_grouped', False):
                    grouped_count += 1
                    
            except Exception as e:
                logger.debug(f"Erreur stats entité: {e}")
                continue
        
        return EntityStats(
            total_entities=len(entities),
            by_type=by_type,
            selected_count=selected_count,
            grouped_count=grouped_count
        )
        
    except Exception as e:
        logger.error(f"Erreur génération stats: {e}")
        return EntityStats(
            total_entities=len(entities) if entities else 0,
            by_type={"UNKNOWN": len(entities) if entities else 0},
            selected_count=len(entities) if entities else 0,
            grouped_count=0
        )