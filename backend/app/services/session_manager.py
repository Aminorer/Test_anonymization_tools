import uuid
import pickle
import redis
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from docx import Document
import io
import logging

from app.models.entities import Entity, AuditLog
from app.core.config import settings

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False  # Pour stocker les données binaires
            )
            # Test de connexion
            self.redis_client.ping()
            logger.info("Connexion Redis établie avec succès")
        except Exception as e:
            logger.error(f"Erreur de connexion Redis: {e}")
            self.redis_client = None
    
    def create_session(self, document: Document, original_text: str, 
                      entities: List[Entity], filename: str) -> str:
        """Crée une nouvelle session et la stocke en cache"""
        session_id = str(uuid.uuid4())
        
        # Sérialiser le document DOCX
        doc_stream = io.BytesIO()
        document.save(doc_stream)
        doc_bytes = doc_stream.getvalue()
        
        # Préparer les données de session
        session_data = {
            'session_id': session_id,
            'filename': filename,
            'original_text': original_text,
            'entities': [entity.dict() for entity in entities],
            'document_bytes': doc_bytes,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)).isoformat()
        }
        
        try:
            if self.redis_client:
                # Stocker en Redis avec expiration
                serialized_data = pickle.dumps(session_data)
                self.redis_client.setex(
                    f"session:{session_id}",
                    settings.SESSION_EXPIRE_MINUTES * 60,
                    serialized_data
                )
                logger.info(f"Session {session_id} créée et stockée en Redis")
            else:
                # Fallback: stockage en mémoire (développement uniquement)
                if not hasattr(self, '_memory_sessions'):
                    self._memory_sessions = {}
                self._memory_sessions[session_id] = session_data
                logger.warning(f"Session {session_id} stockée en mémoire (fallback)")
        
        except Exception as e:
            logger.error(f"Erreur lors de la création de session: {e}")
            raise ValueError("Impossible de créer la session")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les données d'une session"""
        try:
            if self.redis_client:
                serialized_data = self.redis_client.get(f"session:{session_id}")
                if serialized_data:
                    session_data = pickle.loads(serialized_data)
                    return session_data
            else:
                # Fallback mémoire
                if hasattr(self, '_memory_sessions'):
                    return self._memory_sessions.get(session_id)
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de session {session_id}: {e}")
        
        return None
    
    def update_session_entities(self, session_id: str, entities: List[Entity]) -> bool:
        """Met à jour les entités d'une session"""
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        try:
            # Mettre à jour les entités
            session_data['entities'] = [entity.dict() for entity in entities]
            session_data['updated_at'] = datetime.now().isoformat()
            
            if self.redis_client:
                serialized_data = pickle.dumps(session_data)
                self.redis_client.setex(
                    f"session:{session_id}",
                    settings.SESSION_EXPIRE_MINUTES * 60,
                    serialized_data
                )
            else:
                if hasattr(self, '_memory_sessions'):
                    self._memory_sessions[session_id] = session_data
            
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de session {session_id}: {e}")
            return False
    
    def get_document_from_session(self, session_id: str) -> Optional[Document]:
        """Récupère le document DOCX d'une session"""
        session_data = self.get_session(session_id)
        if not session_data:
            return None
        
        try:
            doc_bytes = session_data.get('document_bytes')
            if doc_bytes:
                doc_stream = io.BytesIO(doc_bytes)
                return Document(doc_stream)
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du document de session {session_id}: {e}")
        
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Supprime une session (conformité RGPD)"""
        try:
            if self.redis_client:
                result = self.redis_client.delete(f"session:{session_id}")
                logger.info(f"Session {session_id} supprimée de Redis")
                return result > 0
            else:
                if hasattr(self, '_memory_sessions') and session_id in self._memory_sessions:
                    del self._memory_sessions[session_id]
                    return True
        
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de session {session_id}: {e}")
        
        return False
    
    def cleanup_expired_sessions(self):
        """Nettoie les sessions expirées (tâche de maintenance)"""
        try:
            if not self.redis_client:
                # Nettoyage mémoire
                if hasattr(self, '_memory_sessions'):
                    current_time = datetime.now()
                    expired_sessions = []
                    
                    for session_id, session_data in self._memory_sessions.items():
                        expires_at = datetime.fromisoformat(session_data['expires_at'])
                        if current_time > expires_at:
                            expired_sessions.append(session_id)
                    
                    for session_id in expired_sessions:
                        del self._memory_sessions[session_id]
                        logger.info(f"Session expirée {session_id} nettoyée")
        
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des sessions: {e}")
    
    def generate_audit_log(self, session_id: str, replacements: Dict[str, str]) -> AuditLog:
        """Génère un log d'audit RGPD pour une session"""
        session_data = self.get_session(session_id)
        if not session_data:
            raise ValueError("Session introuvable")
        
        # Déterminer le type d'entité pour chaque remplacement
        entities_dict = {entity['text']: entity for entity in session_data['entities']}
        
        replacement_summary = []
        for original, replacement in replacements.items():
            entity_info = entities_dict.get(original, {})
            replacement_summary.append({
                "type": entity_info.get('type', 'UNKNOWN'),
                "method": "user_validated_replacement",
                "original_length": len(original),
                "replacement": replacement,
                "confidence": entity_info.get('confidence', 0.0)
            })
        
        audit_log = AuditLog(
            document=session_data['filename'],
            timestamp=datetime.now().isoformat(),
            entities_anonymized=len(replacements),
            replacement_summary=replacement_summary
        )
        
        return audit_log
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques des sessions actives"""
        stats = {
            "active_sessions": 0,
            "total_entities": 0,
            "memory_usage": "N/A"
        }
        
        try:
            if self.redis_client:
                # Compter les sessions actives en Redis
                keys = self.redis_client.keys("session:*")
                stats["active_sessions"] = len(keys)
                
                # Calculer le total des entités
                for key in keys:
                    try:
                        session_data = pickle.loads(self.redis_client.get(key))
                        stats["total_entities"] += len(session_data.get('entities', []))
                    except:
                        continue
            else:
                if hasattr(self, '_memory_sessions'):
                    stats["active_sessions"] = len(self._memory_sessions)
                    for session_data in self._memory_sessions.values():
                        stats["total_entities"] += len(session_data.get('entities', []))
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul des statistiques: {e}")
        
        return stats

# Instance globale
session_manager = SessionManager()