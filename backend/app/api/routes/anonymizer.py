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
    MODE STANDARD : Regex uniquement (téléphone, SIRET, email, adresse)
    MODE APPROFONDI : Regex + SpaCy NER + LLM validation (+ noms et organisations)
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
        
        # 1. Traitement du fichier (PDF→DOCX ou DOCX direct)
        try:
            processed_document, extracted_text = document_processor.process_uploaded_file(
                file_content, file.filename
            )
            logger.info(f"✅ Document traité: {len(extracted_text)} caractères extraits")
        except Exception as e:
            logger.error(f"Erreur traitement document: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur traitement document: {str(e)}")
        
        # 2. Analyse des entités selon le mode
        try:
            entities = nlp_analyzer.analyze_document(extracted_text, mode)
            logger.info(f"✅ Analyse terminée: {len(entities)} entités détectées")
        except Exception as e:
            logger.error(f"Erreur analyse NLP: {e}")
            # Fallback : retourner une liste vide
            entities = []
            logger.warning("Mode fallback: analyse sans entités")
        
        # 3. Génération des statistiques
        try:
            stats = _generate_entity_stats_safe(entities)
            logger.info(f"✅ Statistiques générées: {stats.total_entities} entités")
        except Exception as e:
            logger.error(f"Erreur statistiques: {e}")
            stats = EntityStats(
                total_entities=len(entities),
                by_type={},
                selected_count=len(entities)
            )
        
        # 4. Session en cache
        try:
            session_id = session_manager.create_session(
                processed_document, extracted_text, entities, file.filename
            )
            logger.info(f"✅ Session créée: {session_id}")
        except Exception as e:
            logger.error(f"Erreur création session: {e}")
            raise HTTPException(status_code=500, detail="Erreur création session")
        
        # 5. Préparation de la réponse avec règles de sélection
        entity_responses = []
        try:
            for i, entity in enumerate(entities):
                try:
                    # Validation des données d'entité
                    entity_text = getattr(entity, 'text', f'ENTITE_{i}')
                    entity_type = getattr(entity, 'type', EntityTypeEnum.PERSONNE)
                    entity_start = getattr(entity, 'start', 0)
                    entity_end = getattr(entity, 'end', len(entity_text))
                    entity_occurrences = getattr(entity, 'occurrences', 1)
                    entity_confidence = getattr(entity, 'confidence', 0.8)
                    entity_replacement = getattr(entity, 'replacement', f'ANONYME_{i}')
                    entity_source = getattr(entity, 'source', 'unknown')
                    
                    # Règles de sélection par défaut
                    default_selected = True
                    
                    # Obtenir le type d'entité en string
                    if hasattr(entity_type, 'value'):
                        type_value = entity_type.value
                    else:
                        type_value = str(entity_type)
                    
                    # Références juridiques décochées par défaut
                    if ('RÉFÉRENCE' in type_value or 
                        'REFERENCE' in type_value or 
                        'JURIDIQUE' in type_value):
                        default_selected = False
                    
                    entity_response = {
                        "id": getattr(entity, 'id', f'entity_{i}'),
                        "text": str(entity_text),
                        "type": type_value,
                        "subtype": getattr(entity, 'subtype', None),
                        "start": int(entity_start),
                        "end": int(entity_end),
                        "occurrences": int(entity_occurrences),
                        "confidence": float(entity_confidence),
                        "selected": default_selected,
                        "replacement": str(entity_replacement),
                        "valid": getattr(entity, 'valid', True),
                        "source": str(entity_source)
                    }
                    entity_responses.append(entity_response)
                    
                except Exception as e:
                    logger.error(f"Erreur préparation entité {i}: {e}")
                    # Entité de fallback
                    entity_responses.append({
                        "id": f'fallback_entity_{i}',
                        "text": f'ENTITE_DETECTEE_{i}',
                        "type": "PERSONNE",
                        "subtype": None,
                        "start": 0,
                        "end": 10,
                        "occurrences": 1,
                        "confidence": 0.5,
                        "selected": True,
                        "replacement": f'ANONYME_{i}',
                        "valid": True,
                        "source": "fallback"
                    })
        except Exception as e:
            logger.error(f"Erreur lors du traitement des entités: {e}")
        
        # Aperçu du texte (sécurisé)
        try:
            text_preview = extracted_text[:3000] + "..." if len(extracted_text) > 3000 else extracted_text
        except:
            text_preview = "Aperçu indisponible"
        
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
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur interne : {str(e)[:200]}"
        )

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
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        # Validation du type d'entité avec fallback
        try:
            entity_type_enum = EntityTypeEnum(entity_type)
        except ValueError:
            logger.warning(f"Type d'entité invalide: {entity_type}, fallback vers PERSONNE")
            entity_type_enum = EntityTypeEnum.PERSONNE
        
        # Création de la nouvelle entité
        try:
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
        except Exception as e:
            logger.error(f"Erreur création entité manuelle: {e}")
            raise HTTPException(status_code=400, detail="Erreur création entité")
        
        # Récupération des entités existantes
        try:
            existing_entities = []
            for entity_data in session_data.get('entities', []):
                try:
                    if isinstance(entity_data, dict):
                        existing_entities.append(Entity(**entity_data))
                    else:
                        existing_entities.append(entity_data)
                except Exception as e:
                    logger.debug(f"Erreur parsing entité existante: {e}")
                    continue
        except Exception as e:
            logger.error(f"Erreur récupération entités: {e}")
            existing_entities = []
        
        # Vérification des doublons
        for existing_entity in existing_entities:
            try:
                if existing_entity.text.lower() == text.lower():
                    raise HTTPException(status_code=400, detail="Cette entité existe déjà")
            except:
                continue
        
        # Ajout et mise à jour
        existing_entities.append(new_entity)
        
        try:
            session_manager.update_session_entities(session_id, existing_entities)
        except Exception as e:
            logger.error(f"Erreur mise à jour session: {e}")
            raise HTTPException(status_code=500, detail="Erreur mise à jour session")
        
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

@router.post("/generate")
async def generate_anonymized_document(
    session_id: str = Form(...),
    selected_entities: str = Form(...)
):
    """
    Génère le document DOCX anonymisé
    """
    try:
        # Parsing des entités sélectionnées
        try:
            entities_data = json.loads(selected_entities)
            if not isinstance(entities_data, list):
                raise ValueError("Format de données invalide")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Erreur parsing JSON entités: {e}")
            raise HTTPException(status_code=400, detail="Format JSON invalide pour les entités")
        
        # Récupération de la session
        session_data = session_manager.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session introuvable ou expirée")
        
        # Récupération du document original
        try:
            document = session_manager.get_document_from_session(session_id)
            if not document:
                raise HTTPException(status_code=500, detail="Document introuvable dans la session")
        except Exception as e:
            logger.error(f"Erreur récupération document: {e}")
            raise HTTPException(status_code=500, detail="Document introuvable")
        
        # Création du mapping de remplacement
        replacements = {}
        for entity_data in entities_data:
            try:
                if isinstance(entity_data, dict) and entity_data.get("selected", False):
                    original_text = str(entity_data.get("text", "")).strip()
                    replacement_text = str(entity_data.get("replacement", "")).strip()
                    if original_text and replacement_text:
                        replacements[original_text] = replacement_text
            except Exception as e:
                logger.debug(f"Erreur traitement entité: {e}")
                continue
        
        if not replacements:
            raise HTTPException(status_code=400, detail="Aucune entité sélectionnée pour l'anonymisation")
        
        logger.info(f"🚀 Génération document: {len(replacements)} remplacements")
        
        # Application de l'anonymisation
        try:
            anonymized_docx_bytes = document_processor.apply_global_replacements(document, replacements)
        except Exception as e:
            logger.error(f"Erreur anonymisation: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de l'anonymisation")
        
        # Génération du log d'audit RGPD
        try:
            audit_log = session_manager.generate_audit_log(session_id, replacements)
        except Exception as e:
            logger.error(f"Erreur audit log: {e}")
            audit_log = None
        
        # Nettoyage de la session
        try:
            session_manager.delete_session(session_id)
        except Exception as e:
            logger.warning(f"Erreur nettoyage session: {e}")
        
        # Préparation du nom de fichier
        try:
            original_filename = session_data.get('filename', 'document.docx')
            filename_parts = original_filename.split('.')
            filename_without_ext = '.'.join(filename_parts[:-1]) if len(filename_parts) > 1 else original_filename
            anonymized_filename = f"anonymized_{filename_without_ext}.docx"
        except:
            anonymized_filename = "anonymized_document.docx"
        
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
            "filename": session_data.get('filename', 'unknown'),
            "created_at": session_data.get('created_at', ''),
            "expires_at": session_data.get('expires_at', ''),
            "entities_count": len(session_data.get('entities', [])),
            "text_length": len(session_data.get('original_text', ''))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🚨 ERREUR SESSION INFO: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/stats")
async def get_application_stats():
    """
    Retourne les statistiques de l'application
    """
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
                "mode": "REGEX_NER_LLM"  # Nouveau mode
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

def _generate_entity_stats_safe(entities: List[Entity]) -> EntityStats:
    """Génère les statistiques des entités de manière sécurisée"""
    try:
        if not entities:
            return EntityStats(
                total_entities=0,
                by_type={},
                selected_count=0
            )
        
        by_type = {}
        selected_count = 0
        
        for entity in entities:
            try:
                # Compter par type
                entity_type = getattr(entity, 'type', None)
                if entity_type:
                    if hasattr(entity_type, 'value'):
                        type_key = entity_type.value
                    else:
                        type_key = str(entity_type)
                    
                    by_type[type_key] = by_type.get(type_key, 0) + 1
                
                # Compter les sélectionnées
                if getattr(entity, 'selected', True):
                    selected_count += 1
                    
            except Exception as e:
                logger.debug(f"Erreur stats entité: {e}")
                continue
        
        return EntityStats(
            total_entities=len(entities),
            by_type=by_type,
            selected_count=selected_count
        )
        
    except Exception as e:
        logger.error(f"Erreur génération stats: {e}")
        return EntityStats(
            total_entities=len(entities) if entities else 0,
            by_type={"UNKNOWN": len(entities) if entities else 0},
            selected_count=len(entities) if entities else 0
        )