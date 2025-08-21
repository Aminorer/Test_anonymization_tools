# src/anonymizer.py - VERSION NER FONCTIONNELLE CORRIGÉE
"""
Anonymiseur de Documents avec NER fonctionnel
Résolution des conflits PyTorch/Streamlit
"""

# === CONFIGURATION ANTI-CONFLIT ===
import os
import warnings
import logging
import threading
import uuid
from datetime import datetime

# Configuration logging précoce
logging.basicConfig(level=logging.WARNING)
for logger_name in ["transformers", "torch", "tensorflow", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

# Variables d'environnement critiques
os.environ.update({
    "TOKENIZERS_PARALLELISM": "false",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "KMP_DUPLICATE_LIB_OK": "TRUE",
    "PYTORCH_JIT": "0",
    "PYTORCH_JIT_USE_NNC": "0"
})

# Suppression warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# === IMPORTS STANDARDS ===
import re
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from io import BytesIO
import hashlib

# === CONFIGURATION PYTORCH THREAD-SAFE ===
_pytorch_lock = threading.Lock()
_pytorch_configured = False

def configure_pytorch_safe():
    """Configuration PyTorch thread-safe pour Streamlit"""
    global _pytorch_configured
    
    if _pytorch_configured:
        return True
    
    with _pytorch_lock:
        if _pytorch_configured:
            return True
        
        try:
            import torch
            
            # Configuration threads
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            
            # Désactiver JIT et optimisations problématiques
            if hasattr(torch, 'jit'):
                torch.jit.set_fuser('fuser0')
                torch._C._jit_set_profiling_mode(False)
                torch._C._jit_set_profiling_executor(False)
            
            # Mode évaluation par défaut
            torch.set_grad_enabled(False)
            
            # Éviter les conflits de classes
            if hasattr(torch, '_C') and hasattr(torch._C, '_disable_torch_function_mode'):
                torch._C._disable_torch_function_mode()
            
            _pytorch_configured = True
            logging.info("PyTorch configuré avec succès pour Streamlit")
            return True
            
        except Exception as e:
            logging.warning(f"Configuration PyTorch échouée: {e}")
            return False

# Configurer PyTorch immédiatement
PYTORCH_AVAILABLE = configure_pytorch_safe()

# === IMPORTS POUR TRAITEMENT DE DOCUMENTS ===
try:
    import pdfplumber
    from pdf2docx import parse as pdf2docx_parse
    from docx import Document
    PDF_SUPPORT = True
    logging.info("Support PDF activé")
except ImportError as e:
    PDF_SUPPORT = False
    logging.warning(f"Support PDF désactivé: {e}")

# === IMPORTS IA SÉCURISÉS ===
AI_SUPPORT = False
SPACY_SUPPORT = False
TRANSFORMERS_SUPPORT = False

# Configuration SpaCy (plus stable avec Streamlit)
try:
    import spacy
    SPACY_SUPPORT = True
    logging.info("SpaCy disponible")
except ImportError:
    logging.warning("SpaCy non disponible")

# Configuration Transformers (avec protection anti-conflit)
if PYTORCH_AVAILABLE:
    try:
        # Import sécurisé de transformers
        with _pytorch_lock:
            import transformers
            from transformers import pipeline
            
            # Réduire les logs transformers
            transformers.logging.set_verbosity_error()
            
            TRANSFORMERS_SUPPORT = True
            AI_SUPPORT = True
            logging.info("Transformers configuré avec succès")
            
    except Exception as e:
        logging.warning(f"Transformers non disponible: {e}")

# === IMPORTS LOCAUX ===
# Assuming these are in a config.py file
ENTITY_PATTERNS = {
    "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "PHONE": r'\b(?:\+33|0)[1-9](?:[0-9\s.-]{8,13})\b',
    "IBAN": r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}[A-Z0-9]*\b'
}

ENTITY_COLORS = {
    "PERSON": "#FF6B6B",
    "ORG": "#4ECDC4",
    "EMAIL": "#45B7D1"
}

DEFAULT_REPLACEMENTS = {
    "PERSON": "[PERSONNE]",
    "ORG": "[ORGANISATION]",
    "EMAIL": "[EMAIL]",
    "PHONE": "[TÉLÉPHONE]",
    "IBAN": "[IBAN]"
}

# === PATTERNS FRANÇAIS AMÉLIORÉS ===
FRENCH_ENTITY_PATTERNS = {
    **{k: v for k, v in ENTITY_PATTERNS.items() if k != "LOC"},
    
    # Noms français avec titres de civilité
    "PERSON_FR": r'\b(?:M\.?|Mme\.?|Mlle\.?|Dr\.?|Prof\.?|Me\.?|Maître)\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþß]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþß]+)*',
    
    # Organisations françaises spécifiques
    "ORG_FR": r'\b(?:SARL|SAS|SA|SNC|EURL|SASU|SCI|SELARL|SELCA|SELAS|Association|Société|Entreprise|Cabinet|Étude|Bureau|Groupe|Fondation|Institut|Centre|Établissement)\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][A-Za-zÀ-ÿ\s\-\'&]+',
    
    # Numéros français spécialisés
    "SSN_FR": r'\b[12]\s?\d{2}\s?(?:0[1-9]|1[0-2])\s?(?:0[1-9]|[12]\d|3[01])\s?\d{3}\s?\d{3}\s?\d{2}\b',
    "SIRET_FR": r'\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b',
    "SIREN_FR": r'\b\d{3}\s?\d{3}\s?\d{3}\b',
    "TVA_FR": r'\bFR\s?\d{2}\s?\d{9}\b',
    
    # Références juridiques
    "ARTICLE_LOI": r'\b[Aa]rticle\s+\d+(?:-\d+)?\s+(?:du\s+)?(?:Code\s+)?[A-Za-zÀ-ÿ\s]+\b',
    "NUMERO_DOSSIER": r'\b(?:n°|N°|numéro|Numéro)\s*:?\s*\d{2,}/\d{2,}(?:/\d{2,})?\b',
    "RG_NUMBER": r'\bRG\s*:?\s*\d{2}/\d{5}\b',
}

# === MODÈLES IA OPTIMISÉS ===
AI_MODELS = {
    "french_spacy_lg": {
        "name": "fr_core_news_lg",
        "type": "spacy",
        "language": "fr",
        "description": "Modèle SpaCy français large (recommandé)"
    },
    "french_spacy_sm": {
        "name": "fr_core_news_sm", 
        "type": "spacy",
        "language": "fr",
        "description": "Modèle SpaCy français compact"
    },
    "french_camembert": {
        "name": "Jean-Baptiste/camembert-ner",
        "type": "transformers",
        "language": "fr",
        "description": "CamemBERT NER français"
    },
    "multilingual_bert": {
        "name": "dbmdz/bert-large-cased-finetuned-conll03-english",
        "type": "transformers",
        "language": "multi",
        "description": "BERT multilingue"
    },
    "distilbert_lightweight": {
        "name": "distilbert-base-cased",
        "type": "transformers",
        "language": "en",
        "description": "DistilBERT léger (fallback)"
    }
}

@dataclass
class Entity:
    """Classe représentant une entité détectée avec informations enrichies"""
    id: str
    type: str
    value: str
    start: int
    end: int
    confidence: float = 1.0
    replacement: Optional[str] = None
    page: Optional[int] = None
    context: Optional[str] = None
    method: Optional[str] = "regex"  # "regex", "spacy", "transformers"
    source_model: Optional[str] = None

class RegexAnonymizer:
    """Anonymiseur Regex avancé avec patterns français optimisés"""
    
    def __init__(self, use_french_patterns: bool = True):
        self.patterns = FRENCH_ENTITY_PATTERNS if use_french_patterns else ENTITY_PATTERNS
        self.replacements = DEFAULT_REPLACEMENTS
        self.use_french_patterns = use_french_patterns
        logging.info(f"RegexAnonymizer initialisé avec {len(self.patterns)} patterns")
    
    def detect_entities(self, text: str) -> List[Entity]:
        """Détection d'entités avec patterns regex optimisés"""
        entities = []
        entity_id = 0
        
        for entity_type, pattern in self.patterns.items():
            try:
                compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                
                for match in compiled_pattern.finditer(text):
                    # Normaliser le type d'entité
                    normalized_type = self._normalize_entity_type(entity_type)
                    
                    # Validation de l'entité
                    if not self._is_valid_entity_match(match.group(), normalized_type):
                        continue
                    
                    entity = Entity(
                        id=f"regex_{entity_id}",
                        type=normalized_type,
                        value=match.group().strip(),
                        start=match.start(),
                        end=match.end(),
                        confidence=1.0,
                        replacement=self.replacements.get(normalized_type, f"[{normalized_type}]"),
                        context=self._extract_context(text, match.start(), match.end()),
                        method="regex"
                    )
                    entities.append(entity)
                    entity_id += 1
                    
            except re.error as e:
                logging.warning(f"Pattern regex invalide pour {entity_type}: {e}")
                continue
        
        # Post-traitement: éliminer chevauchements et nettoyer
        entities = self._remove_overlapping_entities(entities)
        entities = self._clean_entities(entities)
        
        logging.info(f"RegexAnonymizer: {len(entities)} entités détectées")
        return entities
    
    def _normalize_entity_type(self, entity_type: str) -> str:
        """Normaliser les types d'entités français"""
        mapping = {
            "PERSON_FR": "PERSON",
            "ORG_FR": "ORG", 
            "SSN_FR": "SSN",
            "SIRET_FR": "SIRET",
            "SIREN_FR": "SIREN",
            "TVA_FR": "TVA",
            "ARTICLE_LOI": "LEGAL_REF",
            "NUMERO_DOSSIER": "CASE_NUMBER",
            "RG_NUMBER": "COURT_REF"
        }
        return mapping.get(entity_type, entity_type)
    
    def _is_valid_entity_match(self, value: str, entity_type: str) -> bool:
        """Valider qu'une entité détectée est pertinente"""
        value = value.strip()
        
        # Longueur minimale
        if len(value) < 2:
            return False
        
        # Filtres spécifiques par type
        if entity_type == "EMAIL":
            return "@" in value and "." in value.split("@")[-1]
        elif entity_type == "PHONE":
            digits = re.sub(r'\D', '', value)
            return 8 <= len(digits) <= 15
        elif entity_type == "IBAN":
            return len(value.replace(' ', '')) >= 15
        elif entity_type in ["SIREN", "SIRET"]:
            digits = re.sub(r'\D', '', value)
            return len(digits) in [9, 14]  # SIREN: 9, SIRET: 14
        
        return True
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 80) -> str:
        """Extraire le contexte enrichi autour d'une entité"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        
        context = text[context_start:context_end]
        entity_value = text[start:end]
        
        # Position relative dans le contexte
        relative_start = start - context_start
        relative_end = end - context_start
        
        # Marquer l'entité dans le contexte
        highlighted_context = (
            context[:relative_start] + 
            f"**{entity_value}**" + 
            context[relative_end:]
        )
        
        return highlighted_context.strip()
    
    def _remove_overlapping_entities(self, entities: List[Entity]) -> List[Entity]:
        """Éliminer les chevauchements avec priorité intelligente"""
        if not entities:
            return entities
        
        # Trier par position puis par longueur
        sorted_entities = sorted(entities, key=lambda x: (x.start, -(x.end - x.start)))
        filtered_entities = []
        
        for entity in sorted_entities:
            overlaps = False
            
            for i, accepted in enumerate(filtered_entities):
                if self._entities_overlap(entity, accepted):
                    # Résoudre le conflit selon des règles de priorité
                    winner = self._resolve_overlap_conflict(entity, accepted)
                    
                    if winner == entity:
                        filtered_entities[i] = entity
                    
                    overlaps = True
                    break
            
            if not overlaps:
                filtered_entities.append(entity)
        
        return filtered_entities
    
    def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool:
        """Vérification de chevauchement"""
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)
    
    def _resolve_conflict(self, entity1: Entity, entity2: Entity) -> Entity:
        """Résolution de conflit avec priorités intelligentes"""
        # Priorité 1: Types structurés
        structured_types = {'EMAIL', 'PHONE', 'IBAN', 'SIRET', 'SIREN', 'SSN', 'TVA'}
        
        if entity1.type in structured_types and entity2.type not in structured_types:
            return entity1
        elif entity2.type in structured_types and entity1.type not in structured_types:
            return entity2
        
        # Priorité 2: Méthode (regex > spacy > transformers pour les conflits)
        method_priority = {'regex': 3, 'spacy': 2, 'transformers': 1}
        
        priority1 = method_priority.get(entity1.method, 0)
        priority2 = method_priority.get(entity2.method, 0)
        
        if priority1 != priority2:
            return entity1 if priority1 > priority2 else entity2
        
        # Priorité 3: Confiance
        if abs(entity1.confidence - entity2.confidence) > 0.15:
            return entity1 if entity1.confidence > entity2.confidence else entity2
        
        # Priorité 4: Longueur (plus spécifique)
        len1 = entity1.end - entity1.start
        len2 = entity2.end - entity2.start
        
        return entity1 if len1 >= len2 else entity2
    
    def _validate_anonymization(self, original_text: str, anonymized_text: str, entities: List[Entity]) -> Dict[str, Any]:
        """Validation complète de l'anonymisation"""
        validation = {
            "success": True,
            "issues": [],
            "warnings": [],
            "stats": {}
        }
        
        # Vérifier que les entités ont été remplacées
        not_replaced = []
        for entity in entities:
            if entity.value in anonymized_text:
                not_replaced.append(entity.value)
        
        if not_replaced:
            validation["success"] = False
            validation["issues"].extend([f"Non remplacé: {val}" for val in not_replaced[:5]])
        
        # Détection de fuites potentielles
        potential_leaks = self._detect_potential_leaks(anonymized_text)
        if potential_leaks:
            validation["warnings"].extend(potential_leaks)
        
        # Statistiques
        validation["stats"] = {
            "original_length": len(original_text),
            "anonymized_length": len(anonymized_text),
            "entities_replaced": len(entities),
            "not_replaced_count": len(not_replaced),
            "potential_leaks": len(potential_leaks),
            "success_rate": (len(entities) - len(not_replaced)) / len(entities) * 100 if entities else 100
        }
        
        return validation
    
    def _detect_potential_leaks(self, text: str) -> List[str]:
        """Détecter des fuites potentielles dans le texte anonymisé"""
        leaks = []
        
        # Patterns pour détecter des données manquées
        leak_patterns = {
            "email_like": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            "phone_like": r'\b(?:\+33|0)[1-9](?:[0-9\s.-]{8,})\b',
            "iban_like": r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}[A-Z0-9]*\b',
            "potential_name": r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b',
            "date_like": r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b'
        }
        
        for pattern_name, pattern in leak_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                # Filtrer les faux positifs connus
                filtered_matches = self._filter_false_positives(matches, pattern_name)
                if filtered_matches:
                    leaks.append(f"Fuite potentielle {pattern_name}: {len(filtered_matches)} occurrence(s)")
        
        return leaks
    
    def _filter_false_positives(self, matches: List[str], pattern_type: str) -> List[str]:
        """Filtrer les faux positifs selon le type"""
        if pattern_type == "potential_name":
            # Exclure les mots français courants
            common_words = {'Le Havre', 'La Rochelle', 'Saint Pierre', 'Notre Dame'}
            return [m for m in matches if m not in common_words]
        
        elif pattern_type == "phone_like":
            # Vérifier que c'est vraiment un numéro de téléphone
            return [m for m in matches if len(re.sub(r'\D', '', m)) >= 8]
        
        return matches
    
    def _generate_processing_stats(self, entities: List[Entity], text: str, processing_time: float) -> Dict[str, Any]:
        """Générer des statistiques complètes de traitement"""
        entity_types = {}
        confidence_values = []
        method_counts = {}
        
        for entity in entities:
            # Types
            entity_type = entity.type
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            # Confiance
            if hasattr(entity, 'confidence') and entity.confidence is not None:
                confidence_values.append(entity.confidence)
            
            # Méthodes
            method = getattr(entity, 'method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1
        
        # Statistiques de confiance
        confidence_stats = {}
        if confidence_values:
            confidence_stats = {
                "min": min(confidence_values),
                "max": max(confidence_values),
                "avg": sum(confidence_values) / len(confidence_values),
                "std": self._calculate_std(confidence_values),
                "high_confidence": len([c for c in confidence_values if c >= 0.8]),
                "medium_confidence": len([c for c in confidence_values if 0.5 <= c < 0.8]),
                "low_confidence": len([c for c in confidence_values if c < 0.5])
            }
        
        return {
            "total_entities": len(entities),
            "entity_types": entity_types,
            "method_distribution": method_counts,
            "confidence_stats": confidence_stats,
            "processing_time": processing_time,
            "entities_per_second": len(entities) / processing_time if processing_time > 0 else 0,
            "text_length": len(text),
            "most_common_type": max(entity_types, key=entity_types.get) if entity_types else None,
            "ai_used": any(method in ['spacy', 'transformers'] for method in method_counts.keys())
        }
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculer l'écart-type"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _create_anonymized_document(self, original_path: str, anonymized_text: str, 
                                  metadata: Dict, entities: List[Entity]) -> str:
        """Créer le document anonymisé avec métadonnées enrichies"""
        try:
            doc = Document()
            
            # En-tête avec informations de traitement
            header = doc.sections[0].header
            header_para = header.paragraphs[0]
            header_para.text = "DOCUMENT ANONYMISÉ - CONFORME RGPD"
            
            # Page de titre
            doc.add_heading('DOCUMENT ANONYMISÉ', 0)
            
            # Informations d'anonymisation
            doc.add_heading('INFORMATIONS D\'ANONYMISATION', 1)
            
            info_para = doc.add_paragraph()
            info_para.add_run("Document original: ").bold = True
            info_para.add_run(f"{Path(original_path).name}\n")
            info_para.add_run("Date d'anonymisation: ").bold = True
            info_para.add_run(f"{datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}\n")
            info_para.add_run("Méthode de détection: ").bold = True
            info_para.add_run(f"{metadata.get('detection_method', 'regex').upper()}\n")
            info_para.add_run("Entités anonymisées: ").bold = True
            info_para.add_run(f"{len(entities)}\n")
            info_para.add_run("Temps de traitement: ").bold = True
            info_para.add_run(f"{metadata.get('processing_time', 0):.2f} secondes\n")
            
            # IA utilisée si applicable
            if metadata.get('ai_used', False):
                info_para.add_run("Intelligence Artificielle: ").bold = True
                info_para.add_run("Activée (NER)\n")
            
            # Tableau récapitulatif des entités
            if entities:
                doc.add_heading('RÉCAPITULATIF DES ENTITÉS', 2)
                
                # Grouper par type
                entity_types = {}
                for entity in entities:
                    entity_type = entity.type
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                
                # Créer tableau
                table = doc.add_table(rows=len(entity_types) + 1, cols=3)
                table.style = 'Table Grid'
                
                # En-têtes
                header_cells = table.rows[0].cells
                header_cells[0].text = 'Type d\'entité'
                header_cells[1].text = 'Nombre'
                header_cells[2].text = 'Pourcentage'
                
                # Données
                for i, (entity_type, count) in enumerate(sorted(entity_types.items()), 1):
                    row_cells = table.rows[i].cells
                    row_cells[0].text = entity_type
                    row_cells[1].text = str(count)
                    row_cells[2].text = f"{(count / len(entities) * 100):.1f}%"
            
            # Contenu anonymisé
            doc.add_page_break()
            doc.add_heading('CONTENU ANONYMISÉ', 1)
            
            # Diviser le texte en paragraphes
            paragraphs = anonymized_text.split('\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    doc.add_paragraph(paragraph.strip())
            
            # Rapport d'audit détaillé
            doc.add_page_break()
            doc.add_heading('RAPPORT D\'AUDIT RGPD', 1)
            
            audit_para = doc.add_paragraph()
            audit_para.add_run("Conformité RGPD:\n").bold = True
            audit_para.add_run("• Article 4(5) - Pseudonymisation: Appliquée\n")
            audit_para.add_run("• Article 25 - Protection dès la conception: Respectée\n")
            audit_para.add_run("• Article 32 - Sécurité du traitement: Mise en œuvre\n")
            audit_para.add_run("• Recital 26 - Anonymisation: Conforme\n\n")
            
            audit_para.add_run("Recommandations:\n").bold = True
            audit_para.add_run("• Vérifiez manuellement les entités détectées\n")
            audit_para.add_run("• Conservez ce rapport pour traçabilité\n")
            audit_para.add_run("• Relecture recommandée avant diffusion\n")
            
            # Signature numérique et traçabilité
            footer = doc.sections[0].footer
            footer_para = footer.paragraphs[0]
            
            # Générer signature
            document_hash = hashlib.md5(anonymized_text.encode('utf-8')).hexdigest()[:16]
            document_id = str(uuid.uuid4())[:8].upper()
            
            footer_para.text = (
                f"Anonymiseur v2.0 - ID: {document_id} - "
                f"Hash: {document_hash} - "
                f"Généré: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            
            # Sauvegarde
            output_path = os.path.join(self.temp_dir, f"anonymized_{uuid.uuid4().hex[:8]}.docx")
            doc.save(output_path)
            
            logging.info(f"Document anonymisé créé: {output_path}")
            return output_path
        
        except Exception as e:
            logging.error(f"Erreur création document: {e}")
            raise Exception(f"Impossible de créer le document anonymisé: {str(e)}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Obtenir les statistiques globales"""
        stats = self.processing_stats.copy()
        
        # Ajouter des informations système
        stats.update({
            "ai_support": AI_SUPPORT,
            "spacy_support": SPACY_SUPPORT,
            "transformers_support": TRANSFORMERS_SUPPORT,
            "pdf_support": PDF_SUPPORT,
            "pytorch_available": PYTORCH_AVAILABLE
        })
        
        return stats
    
    def cleanup(self):
        """Nettoyer les ressources"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            logging.info("Nettoyage terminé")
        except Exception as e:
            logging.warning(f"Erreur nettoyage: {e}")

# === CLASSES UTILITAIRES ===

class EntityValidator:
    """Validateur spécialisé pour les entités françaises"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validation email française"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        """Vérifier si deux entités se chevauchent"""
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)
    
    def _resolve_overlap_conflict(self, entity1: Entity, entity2: Entity) -> Entity:
        """Résoudre un conflit de chevauchement avec priorité intelligente"""
        # Priorité 1: Types structurés (EMAIL, PHONE, etc.)
        structured_types = {"EMAIL", "PHONE", "IBAN", "SIRET", "SIREN", "SSN", "TVA"}
        
        if entity1.type in structured_types and entity2.type not in structured_types:
            return entity1
        elif entity2.type in structured_types and entity1.type not in structured_types:
            return entity2
        
        # Priorité 2: Longueur (plus long = plus spécifique)
        len1 = entity1.end - entity1.start
        len2 = entity2.end - entity2.start
        
        if len1 != len2:
            return entity1 if len1 > len2 else entity2
        
        # Priorité 3: Confiance
        return entity1 if entity1.confidence >= entity2.confidence else entity2
    
    def _clean_entities(self, entities: List[Entity]) -> List[Entity]:
        """Nettoyer et valider les entités"""
        cleaned = []
        
        for entity in entities:
            # Nettoyer la valeur
            cleaned_value = self._clean_entity_value(entity.value)
            if cleaned_value and len(cleaned_value) > 1:
                entity.value = cleaned_value
                cleaned.append(entity)
        
        return cleaned
    
    def _clean_entity_value(self, value: str) -> str:
        """Nettoyer la valeur d'une entité"""
        # Supprimer espaces début/fin
        cleaned = value.strip()
        
        # Supprimer ponctuation finale
        cleaned = re.sub(r'[.,;:!?]+$', '', cleaned)
        
        # Supprimer caractères de contrôle
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        return cleaned
    
    def anonymize_text(self, text: str, entities: List[Entity]) -> str:
        """Anonymiser le texte en remplaçant les entités"""
        # Trier par position décroissante pour éviter les décalages
        sorted_entities = sorted(entities, key=lambda x: x.start, reverse=True)
        
        anonymized_text = text
        for entity in sorted_entities:
            replacement = entity.replacement or f"[{entity.type}]"
            anonymized_text = (
                anonymized_text[:entity.start] + 
                replacement + 
                anonymized_text[entity.end:]
            )
        
        return anonymized_text

class AIAnonymizer:
    """Anonymiseur IA avec NER multi-modèles et gestion des conflits Streamlit"""
    
    def __init__(self, model_config: dict = None, prefer_french: bool = True):
        self.model_config = model_config or self._get_best_model(prefer_french)
        self.nlp_pipeline = None
        self.spacy_nlp = None
        self.regex_anonymizer = RegexAnonymizer(use_french_patterns=True)
        self.prefer_french = prefer_french
        self.model_loaded = False
        
        # Initialiser le modèle en mode thread-safe
        self._initialize_model_safe()
    
    def _get_best_model(self, prefer_french: bool) -> dict:
        """Sélectionner le meilleur modèle disponible selon les préférences"""
        if prefer_french:
            if SPACY_SUPPORT:
                return AI_MODELS["french_spacy_lg"]
            elif TRANSFORMERS_SUPPORT:
                return AI_MODELS["french_camembert"]
            else:
                return AI_MODELS["multilingual_bert"]
        else:
            return AI_MODELS["distilbert_lightweight"]
    
    def _initialize_model_safe(self):
        """Initialisation thread-safe du modèle IA"""
        with _pytorch_lock:
            try:
                if self.model_config["type"] == "spacy":
                    self._initialize_spacy()
                else:
                    self._initialize_transformers()
                self.model_loaded = True
                
            except Exception as e:
                logging.error(f"Échec du chargement du modèle IA: {e}")
                logging.info("Fallback vers mode regex uniquement")
    
    def _initialize_spacy(self):
        """Initialiser SpaCy (recommandé pour le français)"""
        if not SPACY_SUPPORT:
            raise Exception("SpaCy non disponible")
        
        try:
            self.spacy_nlp = spacy.load(self.model_config["name"])
            logging.info(f"Modèle SpaCy chargé: {self.model_config['name']}")
            
        except OSError:
            # Essayer le modèle compact si le large n'est pas disponible
            if self.model_config["name"] == "fr_core_news_lg":
                try:
                    self.spacy_nlp = spacy.load("fr_core_news_sm")
                    logging.info("Modèle SpaCy compact chargé: fr_core_news_sm")
                    return
                except OSError:
                    pass
            
            raise Exception(f"Modèle SpaCy non trouvé: {self.model_config['name']}")
        
        except Exception as e:
            raise Exception(f"Erreur SpaCy: {e}")
    
    def _initialize_transformers(self):
        """Initialiser Transformers avec protection anti-conflit"""
        if not TRANSFORMERS_SUPPORT:
            raise Exception("Transformers non disponible")
        
        try:
            # Configuration pipeline avec protection thread
            self.nlp_pipeline = pipeline(
                "ner",
                model=self.model_config["name"],
                aggregation_strategy="simple",
                device=-1,  # Forcer CPU
                return_all_scores=False
            )
            
            logging.info(f"Pipeline Transformers chargé: {self.model_config['name']}")
            
        except Exception as e:
            # Fallback vers un modèle plus léger
            try:
                self.nlp_pipeline = pipeline(
                    "ner",
                    model=AI_MODELS["distilbert_lightweight"]["name"],
                    aggregation_strategy="simple",
                    device=-1
                )
                logging.info("Modèle fallback Transformers chargé")
                
            except Exception as e2:
                raise Exception(f"Tous les modèles Transformers ont échoué: {e}, {e2}")
    
    def detect_entities_ai(self, text: str, confidence_threshold: float = 0.7) -> List[Entity]:
        """Détection d'entités avec IA + fusion regex"""
        entities = []
        
        # Étape 1: Détection IA
        if self.model_loaded:
            try:
                if self.spacy_nlp:
                    ai_entities = self._detect_with_spacy(text, confidence_threshold)
                elif self.nlp_pipeline:
                    ai_entities = self._detect_with_transformers(text, confidence_threshold)
                else:
                    ai_entities = []
                
                entities.extend(ai_entities)
                logging.info(f"IA: {len(ai_entities)} entités détectées")
                
            except Exception as e:
                logging.error(f"Erreur détection IA: {e}")
        
        # Étape 2: Compléter avec regex pour les entités structurées
        regex_entities = self.regex_anonymizer.detect_entities(text)
        entities.extend(self._merge_regex_entities(entities, regex_entities))
        
        # Étape 3: Post-traitement final
        entities = self._post_process_entities(entities, text)
        
        logging.info(f"Total final: {len(entities)} entités")
        return entities
    
    def _detect_with_spacy(self, text: str, confidence_threshold: float) -> List[Entity]:
        """Détection avec SpaCy optimisée"""
        entities = []
        
        try:
            # Traitement par chunks pour les gros documents
            chunks = self._chunk_text(text, max_length=1000000)  # 1M chars max par chunk
            
            for chunk_start, chunk_text in chunks:
                doc = self.spacy_nlp(chunk_text)
                
                for ent in doc.ents:
                    # Calculer confiance approximative pour SpaCy
                    confidence = self._calculate_spacy_confidence(ent)
                    
                    if confidence >= confidence_threshold:
                        entity_type = self._map_spacy_label(ent.label_)
                        
                        entity = Entity(
                            id=f"spacy_{uuid.uuid4().hex[:8]}",
                            type=entity_type,
                            value=ent.text.strip(),
                            start=chunk_start + ent.start_char,
                            end=chunk_start + ent.end_char,
                            confidence=confidence,
                            replacement=DEFAULT_REPLACEMENTS.get(entity_type, f"[{entity_type}]"),
                            context=self._extract_context(text, chunk_start + ent.start_char, chunk_start + ent.end_char),
                            method="spacy",
                            source_model=self.model_config["name"]
                        )
                        entities.append(entity)
            
            return entities
            
        except Exception as e:
            logging.error(f"Erreur SpaCy: {e}")
            return []
    
    def _detect_with_transformers(self, text: str, confidence_threshold: float) -> List[Entity]:
        """Détection avec Transformers en mode sécurisé"""
        entities = []
        
        try:
            # Protection thread pour Transformers
            with _pytorch_lock:
                chunks = self._chunk_text(text, max_length=512)
                
                for chunk_start, chunk_text in chunks:
                    try:
                        # Pipeline NER avec gestion d'erreurs
                        ner_results = self.nlp_pipeline(chunk_text)
                        
                        for result in ner_results:
                            if result['score'] >= confidence_threshold:
                                entity_type = self._map_ner_label(result['entity_group'])
                                
                                entity = Entity(
                                    id=f"transformers_{uuid.uuid4().hex[:8]}",
                                    type=entity_type,
                                    value=result['word'].strip(),
                                    start=chunk_start + result['start'],
                                    end=chunk_start + result['end'],
                                    confidence=result['score'],
                                    replacement=DEFAULT_REPLACEMENTS.get(entity_type, f"[{entity_type}]"),
                                    context=self._extract_context(text, chunk_start + result['start'], chunk_start + result['end']),
                                    method="transformers",
                                    source_model=self.model_config["name"]
                                )
                                entities.append(entity)
                    
                    except Exception as e:
                        logging.warning(f"Erreur sur chunk: {e}")
                        continue
            
            return entities
            
        except Exception as e:
            logging.error(f"Erreur Transformers: {e}")
            return []
    
    def _chunk_text(self, text: str, max_length: int = 512) -> List[Tuple[int, str]]:
        """Diviser le texte en chunks intelligents"""
        if len(text) <= max_length:
            return [(0, text)]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_length
            
            # Essayer de couper à une limite de phrase ou de paragraphe
            if end < len(text):
                # Chercher un point suivi d'espace et majuscule
                sentence_end = text.rfind('. ', start, end)
                if sentence_end > start + max_length // 2:
                    end = sentence_end + 1
                else:
                    # Sinon, chercher un espace
                    space_pos = text.rfind(' ', start + max_length // 2, end)
                    if space_pos > start:
                        end = space_pos
            
            chunks.append((start, text[start:end]))
            start = end
        
        return chunks
    
    def _calculate_spacy_confidence(self, ent) -> float:
        """Calculer une confiance approximative pour SpaCy"""
        # Facteurs de confiance basés sur le type et les caractéristiques
        type_confidence = {
            'PER': 0.92, 'PERSON': 0.92,
            'ORG': 0.88,
            'LOC': 0.85, 'GPE': 0.85,
            'MISC': 0.75,
            'DATE': 0.90,
            'MONEY': 0.88,
            'PERCENT': 0.85
        }
        
        base_confidence = type_confidence.get(ent.label_, 0.80)
        
        # Ajustements
        # Longueur: entités plus longues = plus fiables
        length_factor = min(1.1, 1.0 + (len(ent.text) - 3) * 0.02)
        
        # Capitalisation: noms propres plus fiables
        if ent.text[0].isupper() and ent.label_ in ['PER', 'PERSON', 'ORG']:
            capitalization_factor = 1.05
        else:
            capitalization_factor = 1.0
        
        final_confidence = base_confidence * length_factor * capitalization_factor
        return min(0.98, final_confidence)
    
    def _map_spacy_label(self, spacy_label: str) -> str:
        """Mapper les labels SpaCy vers nos types"""
        mapping = {
            'PER': 'PERSON', 'PERSON': 'PERSON',
            'ORG': 'ORG',
            'LOC': 'LOCATION', 'GPE': 'LOCATION',
            'MISC': 'MISC',
            'DATE': 'DATE', 'TIME': 'DATE',
            'MONEY': 'MONEY',
            'PERCENT': 'PERCENT',
            'CARDINAL': 'NUMBER',
            'ORDINAL': 'NUMBER'
        }
        return mapping.get(spacy_label.upper(), spacy_label.upper())
    
    def _map_ner_label(self, ner_label: str) -> str:
        """Mapper les labels NER Transformers vers nos types"""
        mapping = {
            'PER': 'PERSON', 'PERSON': 'PERSON',
            'ORG': 'ORG', 'ORGANIZATION': 'ORG',
            'LOC': 'LOCATION', 'LOCATION': 'LOCATION',
            'MISC': 'MISC',
            'DATE': 'DATE', 'TIME': 'DATE'
        }
        return mapping.get(ner_label.upper(), ner_label.upper())
    
    def _merge_regex_entities(self, ai_entities: List[Entity], regex_entities: List[Entity]) -> List[Entity]:
        """Fusionner intelligemment les entités IA et regex"""
        merged = []
        
        for regex_entity in regex_entities:
            is_duplicate = False
            
            # Vérifier les chevauchements avec les entités IA
            for ai_entity in ai_entities:
                overlap = self._calculate_overlap(regex_entity, ai_entity)
                
                if overlap > 0.3:  # 30% de chevauchement
                    # Priorité aux entités structurées regex
                    if regex_entity.type in ['EMAIL', 'PHONE', 'IBAN', 'SIRET', 'SIREN', 'SSN', 'TVA']:
                        # Garder regex, supprimer IA
                        try:
                            ai_entities.remove(ai_entity)
                        except ValueError:
                            pass
                        break
                    else:
                        # Garder IA pour les entités non-structurées
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                merged.append(regex_entity)
        
        return merged
    
    def _calculate_overlap(self, entity1: Entity, entity2: Entity) -> float:
        """Calculer le pourcentage de chevauchement entre deux entités"""
        if entity1.end <= entity2.start or entity2.end <= entity1.start:
            return 0.0  # Pas de chevauchement
        
        overlap_start = max(entity1.start, entity2.start)
        overlap_end = min(entity1.end, entity2.end)
        overlap_length = max(0, overlap_end - overlap_start)
        total_length = min(entity1.end, entity2.end) - max(entity1.start, entity2.start)
        
        return overlap_length / total_length if total_length > 0 else 0.0
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 120) -> str:
        """Extraction de contexte intelligent"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        
        # Essayer de couper à des limites de mots
        context = text[context_start:context_end]
        
        # Marquer l'entité
        entity_value = text[start:end]
        relative_start = start - context_start
        relative_end = end - context_start
        
        if 0 <= relative_start < len(context) and 0 <= relative_end <= len(context):
            highlighted_context = (
                context[:relative_start] + 
                f"**{entity_value}**" + 
                context[relative_end:]
            )
        else:
            highlighted_context = context
        
        return highlighted_context.strip()
    
    def _post_process_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Post-traitement avec optimisations françaises"""
        processed = []
        
        for entity in entities:
            # Validation de base
            if not self._is_valid_entity(entity, text):
                continue
            
            # Nettoyage de la valeur
            entity.value = self._clean_entity_value(entity.value)
            
            # Amélioration du contexte
            if not entity.context:
                entity.context = self._extract_context(text, entity.start, entity.end)
            
            # Classification fine française
            entity.type = self._refine_french_classification(entity, text)
            
            processed.append(entity)
        
        # Résolution des conflits
        processed = self._resolve_entity_conflicts(processed)
        
        return processed
    
    def _is_valid_entity(self, entity: Entity, text: str) -> bool:
        """Validation robuste des entités"""
        # Vérifications de base
        if entity.start < 0 or entity.end > len(text):
            return False
        
        if entity.start >= entity.end:
            return False
        
        if len(entity.value.strip()) < 2:
            return False
        
        # Vérification cohérence texte
        actual_value = text[entity.start:entity.end]
        if actual_value.strip().lower() != entity.value.strip().lower():
            # Tentative de correction
            search_start = max(0, entity.start - 10)
            search_end = min(len(text), entity.end + 10)
            search_area = text[search_start:search_end]
            
            if entity.value in search_area:
                corrected_start = search_area.find(entity.value) + search_start
                entity.start = corrected_start
                entity.end = corrected_start + len(entity.value)
            else:
                return False
        
        return True
    
    def _clean_entity_value(self, value: str) -> str:
        """Nettoyage avancé des valeurs d'entités"""
        # Supprimer espaces début/fin
        cleaned = value.strip()
        
        # Supprimer ponctuation finale
        cleaned = re.sub(r'[.,;:!?]+, '', cleaned)
        
        # Supprimer caractères bizarres
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        # Normaliser espaces internes
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def _refine_french_classification(self, entity: Entity, text: str) -> str:
        """Classification fine pour le contexte français"""
        value = entity.value.lower()
        
        # Amélioration PERSON
        if entity.type == 'PERSON':
            context_before = text[max(0, entity.start - 30):entity.start].lower()
            
            # Vérifier titres français
            french_titles = ['monsieur', 'madame', 'mademoiselle', 'docteur', 'professeur', 'maître']
            if any(title in context_before for title in french_titles):
                return 'PERSON'
            
            # Détecter organisations
            org_words = ['société', 'entreprise', 'sarl', 'sas', 'cabinet', 'étude', 'bureau']
            if any(word in value for word in org_words):
                return 'ORG'
        
        # Amélioration ORG
        elif entity.type == 'ORG':
            legal_forms = ['sarl', 'sas', 'sa', 'snc', 'eurl', 'sasu', 'sci', 'selarl', 'selas', 'selca']
            if any(form in value for form in legal_forms):
                return 'ORG'
        
        return entity.type
    
    def _resolve_entity_conflicts(self, entities: List[Entity]) -> List[Entity]:
        """Résolution intelligente des conflits"""
        if not entities:
            return entities
        
        # Trier par position
        sorted_entities = sorted(entities, key=lambda x: x.start)
        resolved = []
        
        for current in sorted_entities:
            conflict_found = False
            
            for i, existing in enumerate(resolved):
                if self._entities_overlap(current, existing):
                    winner = self._resolve_conflict(current, existing)
                    resolved[i] = winner
                    conflict_found = True
                    break
            
            if not conflict_found:
                resolved.append(current)
        
        return resolved
    
    def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool:
        """Vérification de chevauchement"""
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)
    
    def _resolve_conflict(self, entity1: Entity, entity2: Entity) -> Entity:
        """Résolution de conflit avec priorités intelligentes"""
        # Priorité 1: Types structurés
        structured_types = {'EMAIL', 'PHONE', 'IBAN', 'SIRET', 'SIREN', 'SSN', 'TVA'}
        
        if entity1.type in structured_types and entity2.type not in structured_types:
            return entity1
        elif entity2.type in structured_types and entity1.type not in structured_types:
            return entity2
        
        # Priorité 2: Méthode (regex > spacy > transformers pour les conflits)
        method_priority = {'regex': 3, 'spacy': 2, 'transformers': 1}
        
        priority1 = method_priority.get(entity1.method, 0)
        priority2 = method_priority.get(entity2.method, 0)
        
        if priority1 != priority2:
            return entity1 if priority1 > priority2 else entity2
        
        # Priorité 3: Confiance
        if abs(entity1.confidence - entity2.confidence) > 0.15:
            return entity1 if entity1.confidence > entity2.confidence else entity2
        
        # Priorité 4: Longueur (plus spécifique)
        len1 = entity1.end - entity1.start
        len2 = entity2.end - entity2.start
        
        return entity1 if len1 >= len2 else entity2

class DocumentProcessor:
    """Processeur de documents avec gestion d'erreurs robuste"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.doc', '.txt']
        self.max_text_length = 10_000_000  # 10M caractères max
    
    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, Dict]:
        """Extraction PDF robuste avec fallbacks multiples"""
        if not PDF_SUPPORT:
            raise Exception("Support PDF non disponible. Installez pdfplumber et pdf2docx.")
        
        text_content = ""
        metadata = {"pages": 0, "format": "pdf", "extraction_method": None}
        
        # Méthode 1: pdfplumber (recommandée)
        try:
            with pdfplumber.open(file_path) as pdf:
                metadata["pages"] = len(pdf.pages)
                metadata["extraction_method"] = "pdfplumber"
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"\n--- Page {page_num} ---\n{page_text}"
                        
                        # Extraire les tableaux si peu de texte
                        if len(page_text or "") < 100:
                            tables = page.extract_tables()
                            if tables:
                                text_content += f"\n--- Tableaux Page {page_num} ---\n"
                                for table in tables:
                                    for row in table:
                                        if row:
                                            text_content += " | ".join([cell or "" for cell in row]) + "\n"
                    
                    except Exception as e:
                        logging.warning(f"Erreur page {page_num}: {e}")
                        continue
            
            if text_content.strip():
                metadata["text_length"] = len(text_content)
                return text_content, metadata
        
        except Exception as e:
            logging.warning(f"pdfplumber échoué: {e}")
        
        # Méthode 2: PyMuPDF fallback
        try:
            import fitz
            metadata["extraction_method"] = "pymupdf"
            
            doc = fitz.open(file_path)
            metadata["pages"] = len(doc)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text:
                    text_content += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            doc.close()
            metadata["text_length"] = len(text_content)
            return text_content, metadata
        
        except ImportError:
            logging.warning("PyMuPDF non disponible")
        except Exception as e:
            logging.warning(f"PyMuPDF échoué: {e}")
        
        # Méthode 3: pdf2docx puis extraction DOCX
        try:
            temp_docx = tempfile.mktemp(suffix='.docx')
            pdf2docx_parse(file_path, temp_docx)
            
            text_content, docx_metadata = self.extract_text_from_docx(temp_docx)
            metadata.update(docx_metadata)
            metadata["extraction_method"] = "pdf2docx"
            
            os.unlink(temp_docx)
            return text_content, metadata
        
        except Exception as e:
            logging.warning(f"pdf2docx échoué: {e}")
        
        raise Exception("Impossible d'extraire le texte du PDF avec toutes les méthodes disponibles")
    
    def extract_text_from_docx(self, file_path: str) -> Tuple[str, Dict]:
        """Extraction DOCX complète avec métadonnées"""
        try:
            doc = Document(file_path)
            
            text_content = ""
            metadata = {
                "paragraphs": 0,
                "tables": 0, 
                "headers": 0,
                "footers": 0,
                "format": "docx"
            }
            
            # Extraction paragraphes
            for para in doc.paragraphs:
                if para.text.strip():
                    text_content += para.text + "\n"
                    metadata["paragraphs"] += 1
            
            # Extraction tableaux
            for table in doc.tables:
                metadata["tables"] += 1
                text_content += "\n--- Tableau ---\n"
                
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            row_text.append(cell_text)
                    
                    if row_text:
                        text_content += " | ".join(row_text) + "\n"
            
            # Extraction en-têtes et pieds de page
            for section in doc.sections:
                if section.header:
                    for para in section.header.paragraphs:
                        if para.text.strip():
                            text_content += f"[EN-TÊTE] {para.text}\n"
                            metadata["headers"] += 1
                
                if section.footer:
                    for para in section.footer.paragraphs:
                        if para.text.strip():
                            text_content += f"[PIED DE PAGE] {para.text}\n"
                            metadata["footers"] += 1
            
            # Limitation de taille
            if len(text_content) > self.max_text_length:
                text_content = text_content[:self.max_text_length]
                logging.warning(f"Texte tronqué à {self.max_text_length} caractères")
            
            metadata["text_length"] = len(text_content)
            return text_content, metadata
        
        except Exception as e:
            raise Exception(f"Échec extraction DOCX: {str(e)}")
    
    def extract_text_from_txt(self, file_path: str) -> Tuple[str, Dict]:
        """Extraction fichier texte avec encodage intelligent"""
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text_content = f.read()
                
                # Limitation de taille
                if len(text_content) > self.max_text_length:
                    text_content = text_content[:self.max_text_length]
                    logging.warning(f"Texte tronqué à {self.max_text_length} caractères")
                
                metadata = {
                    "format": "txt",
                    "encoding": encoding,
                    "text_length": len(text_content),
                    "lines": text_content.count('\n') + 1
                }
                
                return text_content, metadata
            
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise Exception(f"Erreur lecture fichier texte: {e}")
        
        raise Exception("Impossible de décoder le fichier texte avec les encodages supportés")
    
    def process_file(self, file_path: str) -> Tuple[str, Dict]:
        """Traitement unifié avec détection automatique"""
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        
        if file_ext == '.pdf':
            return self.extract_text_from_pdf(str(file_path))
        elif file_ext in ['.docx', '.doc']:
            return self.extract_text_from_docx(str(file_path))
        elif file_ext == '.txt':
            return self.extract_text_from_txt(str(file_path))
        else:
            raise Exception(f"Format non supporté: {file_ext}")

class DocumentAnonymizer:
    """Anonymiseur principal avec IA fonctionnelle et optimisations Streamlit"""
    
    def __init__(self, prefer_french: bool = True, use_spacy: bool = True):
        self.regex_anonymizer = RegexAnonymizer(use_french_patterns=True)
        
        # Initialisation IA conditionnelle
        if AI_SUPPORT or SPACY_SUPPORT:
            try:
                self.ai_anonymizer = AIAnonymizer(prefer_french=prefer_french)
                logging.info("AIAnonymizer initialisé avec succès")
            except Exception as e:
                self.ai_anonymizer = None
                logging.warning(f"AIAnonymizer non disponible: {e}")
        else:
            self.ai_anonymizer = None
            logging.info("Mode regex uniquement (IA non disponible)")
        
        self.document_processor = DocumentProcessor()
        self.temp_dir = tempfile.mkdtemp()
        self.prefer_french = prefer_french
        
        # Statistiques de traitement
        self.processing_stats = {
            "documents_processed": 0,
            "entities_detected": 0,
            "processing_time": 0.0,
            "ai_available": self.ai_anonymizer is not None
        }
    
    def process_document(self, file_path: str, mode: str = "ai", confidence: float = 0.7) -> Dict[str, Any]:
        """Traitement principal avec gestion optimisée des performances"""
        import time
        start_time = time.time()
        
        try:
            # Validation des paramètres
            if mode not in ["regex", "ai"]:
                mode = "regex"
            
            if not (0.0 <= confidence <= 1.0):
                confidence = 0.7
            
            # Forcer regex si IA non disponible
            if mode == "ai" and not self.ai_anonymizer:
                mode = "regex"
                logging.warning("Mode IA demandé mais non disponible, fallback vers regex")
            
            # Extraction du texte
            logging.info(f"Traitement du document: {file_path}")
            text, metadata = self.document_processor.process_file(file_path)
            
            if not text.strip():
                return {
                    "status": "error",
                    "error": "Aucun texte trouvé dans le document"
                }
            
            # Prétraitement du texte
            text = self._preprocess_text(text)
            logging.info(f"Texte extrait: {len(text)} caractères")
            
            # Détection des entités selon le mode
            if mode == "ai" and self.ai_anonymizer:
                logging.info("Détection IA en cours...")
                entities = self.ai_anonymizer.detect_entities_ai(text, confidence)
                metadata["detection_method"] = "ai"
            else:
                logging.info("Détection regex en cours...")
                entities = self.regex_anonymizer.detect_entities(text)
                metadata["detection_method"] = "regex"
            
            logging.info(f"Entités détectées: {len(entities)}")
            
            # Post-traitement et validation
            entities = self._post_process_entities(entities, text)
            
            # Anonymisation
            anonymized_text = self.regex_anonymizer.anonymize_text(text, entities)
            
            # Validation de l'anonymisation
            validation_result = self._validate_anonymization(text, anonymized_text, entities)
            
            # Création du document anonymisé
            anonymized_path = self._create_anonymized_document(
                file_path, anonymized_text, metadata, entities
            )
            
            # Calcul des métriques
            processing_time = time.time() - start_time
            self.processing_stats["documents_processed"] += 1
            self.processing_stats["entities_detected"] += len(entities)
            self.processing_stats["processing_time"] += processing_time
            
            # Génération des statistiques
            stats = self._generate_processing_stats(entities, text, processing_time)
            
            return {
                "status": "success",
                "entities": [asdict(entity) for entity in entities],
                "text": text,
                "anonymized_text": anonymized_text,
                "anonymized_path": anonymized_path,
                "metadata": {**metadata, **stats},
                "mode": mode,
                "confidence": confidence,
                "validation": validation_result,
                "processing_time": processing_time
            }
        
        except Exception as e:
            processing_time = time.time() - start_time
            logging.error(f"Erreur traitement document: {str(e)}")
            return {
                "status": "error", 
                "error": str(e),
                "processing_time": processing_time
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Prétraitement optimisé du texte français"""
        # Normalisation des espaces
        text = re.sub(r'\s+', ' ', text)
        
        # Normalisation caractères français
        replacements = {
            'œ': 'oe', 'Œ': 'OE',
            'æ': 'ae', 'Æ': 'AE',
            '«': '"', '»': '"',
            ''': "'", ''': "'",
            '"': '"', '"': '"'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Nettoyage caractères de contrôle
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()
    
    def _post_process_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Post-traitement avec optimisations françaises"""
        processed = []
        
        for entity in entities:
            # Validation de base
            if not self._is_valid_entity(entity, text):
                continue
            
            # Nettoyage de la valeur
            entity.value = self._clean_entity_value(entity.value)
            
            # Amélioration du contexte
            if not entity.context:
                entity.context = self._extract_context(text, entity.start, entity.end)
            
            # Classification fine française
            entity.type = self._refine_french_classification(entity, text)
            
            processed.append(entity)
        
        # Résolution des conflits
        processed = self._resolve_entity_conflicts(processed)
        
        return processed
    
    def _is_valid_entity(self, entity: Entity, text: str) -> bool:
        """Validation robuste des entités"""
        # Vérifications de base
        if entity.start < 0 or entity.end > len(text):
            return False
        
        if entity.start >= entity.end:
            return False
        
        if len(entity.value.strip()) < 2:
            return False
        
        # Vérification cohérence texte
        actual_value = text[entity.start:entity.end]
        if actual_value.strip().lower() != entity.value.strip().lower():
            # Tentative de correction
            search_start = max(0, entity.start - 10)
            search_end = min(len(text), entity.end + 10)
            search_area = text[search_start:search_end]
            
            if entity.value in search_area:
                corrected_start = search_area.find(entity.value) + search_start
                entity.start = corrected_start
                entity.end = corrected_start + len(entity.value)
            else:
                return False
        
        return True
    
    def _clean_entity_value(self, value: str) -> str:
        """Nettoyage avancé des valeurs d'entités"""
        # Supprimer espaces début/fin
        cleaned = value.strip()
        
        # Supprimer ponctuation finale
        cleaned = re.sub(r'[.,;:!?]+, '', cleaned)
        
        # Supprimer caractères bizarres
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        # Normaliser espaces internes
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 120) -> str:
        """Extraction de contexte intelligent"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        
        # Essayer de couper à des limites de mots
        context = text[context_start:context_end]
        
        # Marquer l'entité
        entity_value = text[start:end]
        relative_start = start - context_start
        relative_end = end - context_start
        
        if 0 <= relative_start < len(context) and 0 <= relative_end <= len(context):
            highlighted_context = (
                context[:relative_start] + 
                f"**{entity_value}**" + 
                context[relative_end:]
            )
        else:
            highlighted_context = context
        
        return highlighted_context.strip()
    
    def _refine_french_classification(self, entity: Entity, text: str) -> str:
        """Classification fine pour le contexte français"""
        value = entity.value.lower()
        
        # Amélioration PERSON
        if entity.type == 'PERSON':
            context_before = text[max(0, entity.start - 30):entity.start].lower()
            
            # Vérifier titres français
            french_titles = ['monsieur', 'madame', 'mademoiselle', 'docteur', 'professeur', 'maître']
            if any(title in context_before for title in french_titles):
                return 'PERSON'
            
            # Détecter organisations
            org_words = ['société', 'entreprise', 'sarl', 'sas', 'cabinet', 'étude', 'bureau']
            if any(word in value for word in org_words):
                return 'ORG'
        
        # Amélioration ORG
        elif entity.type == 'ORG':
            legal_forms = ['sarl', 'sas', 'sa', 'snc', 'eurl', 'sasu', 'sci', 'selarl', 'selas', 'selca']
            if any(form in value for form in legal_forms):
                return 'ORG'
        
        return entity.type
    
    def _resolve_entity_conflicts(self, entities: List[Entity]) -> List[Entity]:
        """Résolution intelligente des conflits"""
        if not entities:
            return entities
        
        # Trier par position
        sorted_entities = sorted(entities, key=lambda x: x.start)
        resolved = []
        
        for current in sorted_entities:
            conflict_found = False
            
            for i, existing in enumerate(resolved):
                if self._entities_overlap(current, existing):
                    winner = self._resolve_conflict(current, existing)
                    resolved[i] = winner
                    conflict_found = True
                    break
            
            if not conflict_found:
                resolved.append(current)
        
        return resolved
    
    def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool:
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)
    
    @staticmethod
    def validate_phone_fr(phone: str) -> bool:
        """Validation téléphone français"""
        # Nettoyer le numéro
        digits = re.sub(r'\D', '', phone)
        
        # Formats français acceptés
        if len(digits) == 10 and digits.startswith(('01', '02', '03', '04', '05', '06', '07', '08', '09')):
            return True
        elif len(digits) == 11 and digits.startswith('33') and digits[2] in '123456789':
            return True
        elif len(digits) == 12 and digits.startswith('0033'):
            return True
        
        return False
    
    @staticmethod
    def validate_siren(siren: str) -> bool:
        """Validation SIREN avec algorithme de Luhn"""
        digits = re.sub(r'\D', '', siren)
        
        if len(digits) != 9:
            return False
        
        # Algorithme de Luhn pour SIREN
        total = 0
        for i, digit in enumerate(digits):
            num = int(digit)
            if i % 2 == 1:
                num *= 2
                if num > 9:
                    num = num // 10 + num % 10
            total += num
        
        return total % 10 == 0
    
    @staticmethod
    def validate_siret(siret: str) -> bool:
        """Validation SIRET"""
        digits = re.sub(r'\D', '', siret)
        
        if len(digits) != 14:
            return False
        
        # Vérifier le SIREN (9 premiers chiffres)
        siren = digits[:9]
        if not EntityValidator.validate_siren(siren):
            return False
        
        # Vérifier le NIC (5 derniers chiffres)
        # Algorithme de validation SIRET
        total = 0
        for i, digit in enumerate(digits):
            num = int(digit)
            if i % 2 == 1:
                num *= 2
                if num > 9:
                    num = num // 10 + num % 10
            total += num
        
        return total % 10 == 0

class PerformanceMonitor:
    """Moniteur de performance pour l'anonymisation"""
    
    def __init__(self):
        self.metrics = {
            "processing_times": [],
            "entity_counts": [],
            "text_lengths": [],
            "memory_usage": []
        }
    
    def record_processing(self, processing_time: float, entity_count: int, text_length: int):
        """Enregistrer les métriques d'un traitement"""
        self.metrics["processing_times"].append(processing_time)
        self.metrics["entity_counts"].append(entity_count)
        self.metrics["text_lengths"].append(text_length)
        
        # Mesurer l'utilisation mémoire si psutil disponible
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.metrics["memory_usage"].append(memory_mb)
        except:
            pass
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Générer un rapport de performance"""
        if not self.metrics["processing_times"]:
            return {"status": "no_data"}
        
        processing_times = self.metrics["processing_times"]
        entity_counts = self.metrics["entity_counts"]
        text_lengths = self.metrics["text_lengths"]
        
        return {
            "total_documents": len(processing_times),
            "avg_processing_time": sum(processing_times) / len(processing_times),
            "min_processing_time": min(processing_times),
            "max_processing_time": max(processing_times),
            "avg_entities_per_doc": sum(entity_counts) / len(entity_counts),
            "avg_text_length": sum(text_lengths) / len(text_lengths),
            "throughput_docs_per_minute": 60 / (sum(processing_times) / len(processing_times)),
            "memory_usage_mb": sum(self.metrics["memory_usage"]) / len(self.metrics["memory_usage"]) if self.metrics["memory_usage"] else 0
        }

class DocumentAnonymizer:
    """Anonymiseur principal avec IA fonctionnelle et optimisations Streamlit"""
    
    def __init__(self, prefer_french: bool = True, use_spacy: bool = True):
        self.regex_anonymizer = RegexAnonymizer(use_french_patterns=True)
        
        # Initialisation IA conditionnelle
        if AI_SUPPORT or SPACY_SUPPORT:
            try:
                self.ai_anonymizer = AIAnonymizer(prefer_french=prefer_french)
                logging.info("AIAnonymizer initialisé avec succès")
            except Exception as e:
                self.ai_anonymizer = None
                logging.warning(f"AIAnonymizer non disponible: {e}")
        else:
            self.ai_anonymizer = None
            logging.info("Mode regex uniquement (IA non disponible)")
        
        self.document_processor = DocumentProcessor()
        self.temp_dir = tempfile.mkdtemp()
        self.prefer_french = prefer_french
        
        # Statistiques de traitement
        self.processing_stats = {
            "documents_processed": 0,
            "entities_detected": 0,
            "processing_time": 0.0,
            "ai_available": self.ai_anonymizer is not None
        }
    
    def process_document(self, file_path: str, mode: str = "ai", confidence: float = 0.7) -> Dict[str, Any]:
        """Traitement principal avec gestion optimisée des performances"""
        import time
        start_time = time.time()
        
        try:
            # Validation des paramètres
            if mode not in ["regex", "ai"]:
                mode = "regex"
            
            if not (0.0 <= confidence <= 1.0):
                confidence = 0.7
            
            # Forcer regex si IA non disponible
            if mode == "ai" and not self.ai_anonymizer:
                mode = "regex"
                logging.warning("Mode IA demandé mais non disponible, fallback vers regex")
            
            # Extraction du texte
            logging.info(f"Traitement du document: {file_path}")
            text, metadata = self.document_processor.process_file(file_path)
            
            if not text.strip():
                return {
                    "status": "error",
                    "error": "Aucun texte trouvé dans le document"
                }
            
            # Prétraitement du texte
            text = self._preprocess_text(text)
            logging.info(f"Texte extrait: {len(text)} caractères")
            
            # Détection des entités selon le mode
            if mode == "ai" and self.ai_anonymizer:
                logging.info("Détection IA en cours...")
                entities = self.ai_anonymizer.detect_entities_ai(text, confidence)
                metadata["detection_method"] = "ai"
            else:
                logging.info("Détection regex en cours...")
                entities = self.regex_anonymizer.detect_entities(text)
                metadata["detection_method"] = "regex"
            
            logging.info(f"Entités détectées: {len(entities)}")
            
            # Post-traitement et validation
            entities = self._post_process_entities(entities, text)
            
            # Anonymisation
            anonymized_text = self.regex_anonymizer.anonymize_text(text, entities)
            
            # Validation de l'anonymisation
            validation_result = self._validate_anonymization(text, anonymized_text, entities)
            
            # Création du document anonymisé
            anonymized_path = self._create_anonymized_document(
                file_path, anonymized_text, metadata, entities
            )
            
            # Calcul des métriques
            processing_time = time.time() - start_time
            self.processing_stats["documents_processed"] += 1
            self.processing_stats["entities_detected"] += len(entities)
            self.processing_stats["processing_time"] += processing_time
            
            # Génération des statistiques
            stats = self._generate_processing_stats(entities, text, processing_time)
            
            return {
                "status": "success",
                "entities": [asdict(entity) for entity in entities],
                "text": text,
                "anonymized_text": anonymized_text,
                "anonymized_path": anonymized_path,
                "metadata": {**metadata, **stats},
                "mode": mode,
                "confidence": confidence,
                "validation": validation_result,
                "processing_time": processing_time
            }
        
        except Exception as e:
            processing_time = time.time() - start_time
            logging.error(f"Erreur traitement document: {str(e)}")
            return {
                "status": "error", 
                "error": str(e),
                "processing_time": processing_time
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Prétraitement optimisé du texte français"""
        # Normalisation des espaces
        text = re.sub(r'\s+', ' ', text)
        
        # Normalisation caractères français
        replacements = {
            'œ': 'oe', 'Œ': 'OE',
            'æ': 'ae', 'Æ': 'AE',
            '«': '"', '»': '"',
            ''': "'", ''': "'",
            '"': '"', '"': '"'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Nettoyage caractères de contrôle
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()
    
    def _post_process_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Post-traitement avec optimisations françaises"""
        processed = []
        
        for entity in entities:
            # Validation de base
            if not self._is_valid_entity(entity, text):
                continue
            
            # Nettoyage de la valeur
            entity.value = self._clean_entity_value(entity.value)
            
            # Amélioration du contexte
            if not entity.context:
                entity.context = self._extract_context(text, entity.start, entity.end)
            
            # Classification fine française
            entity.type = self._refine_french_classification(entity, text)
            
            processed.append(entity)
        
        # Résolution des conflits
        processed = self._resolve_entity_conflicts(processed)
        
        return processed
    
    def _is_valid_entity(self, entity: Entity, text: str) -> bool:
        """Validation robuste des entités"""
        # Vérifications de base
        if entity.start < 0 or entity.end > len(text):
            return False
        
        if entity.start >= entity.end:
            return False
        
        if len(entity.value.strip()) < 2:
            return False
        
        # Vérification cohérence texte
        actual_value = text[entity.start:entity.end]
        if actual_value.strip().lower() != entity.value.strip().lower():
            # Tentative de correction
            search_start = max(0, entity.start - 10)
            search_end = min(len(text), entity.end + 10)
            search_area = text[search_start:search_end]
            
            if entity.value in search_area:
                corrected_start = search_area.find(entity.value) + search_start
                entity.start = corrected_start
                entity.end = corrected_start + len(entity.value)
            else:
                return False
        
        return True
    
    def _clean_entity_value(self, value: str) -> str:
        """Nettoyage avancé des valeurs d'entités"""
        # Supprimer espaces début/fin
        cleaned = value.strip()
        
        # Supprimer ponctuation finale
        cleaned = re.sub(r'[.,;:!?]+$', '', cleaned)
        
        # Supprimer caractères bizarres
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        # Normaliser espaces internes
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def _refine_french_classification(self, entity: Entity, text: str) -> str:
        """Classification fine pour le contexte français"""
        value = entity.value.lower()
        
        # Amélioration PERSON
        if entity.type == 'PERSON':
            context_before = text[max(0, entity.start - 30):entity.start].lower()
            
            # Vérifier titres français
            french_titles = ['monsieur', 'madame', 'mademoiselle', 'docteur', 'professeur', 'maître']
            if any(title in context_before for title in french_titles):
                return 'PERSON'
            
            # Détecter organisations
            org_words = ['société', 'entreprise', 'sarl', 'sas', 'cabinet', 'étude', 'bureau']
            if any(word in value for word in org_words):
                return 'ORG'
        
        # Amélioration ORG
        elif entity.type == 'ORG':
            legal_forms = ['sarl', 'sas', 'sa', 'snc', 'eurl', 'sasu', 'sci', 'selarl', 'selas', 'selca']
            if any(form in value for form in legal_forms):
                return 'ORG'
        
        return entity.type
    
    def _resolve_entity_conflicts(self, entities: List[Entity]) -> List[Entity]:
        """Résolution intelligente des conflits"""
        if not entities:
            return entities
        
        # Trier par position
        sorted_entities = sorted(entities, key=lambda x: x.start)
        resolved = []
        
        for current in sorted_entities:
            conflict_found = False
            
            for i, existing in enumerate(resolved):
                if self._entities_overlap(current, existing):
                    winner = self._resolve_conflict(current, existing)
                    resolved[i] = winner
                    conflict_found = True
                    break
            
            if not conflict_found:
                resolved.append(current)
        
        return resolved
    
    def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool:
        """Vérification de chevauchement"""
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)
    
    def _resolve_conflict(self, entity1: Entity, entity2: Entity) -> Entity:
        """Résolution de conflit avec priorités intelligentes"""
        # Priorité 1: Types structurés
        structured_types = {'EMAIL', 'PHONE', 'IBAN', 'SIRET', 'SIREN', 'SSN', 'TVA'}
        
        if entity1.type in structured_types and entity2.type not in structured_types:
            return entity1
        elif entity2.type in structured_types and entity1.type not in structured_types:
            return entity2
        
        # Priorité 2: Méthode
        method_priority = {'regex': 3, 'spacy': 2, 'transformers': 1}
        priority1 = method_priority.get(entity1.method, 0)
        priority2 = method_priority.get(entity2.method, 0)
        
        if priority1 != priority2:
            return entity1 if priority1 > priority2 else entity2
        
        # Priorité 3: Confiance
        if abs(entity1.confidence - entity2.confidence) > 0.15:
            return entity1 if entity1.confidence > entity2.confidence else entity2
        
        # Priorité 4: Longueur
        len1 = entity1.end - entity1.start
        len2 = entity2.end - entity2.start
        
        return entity1 if len1 >= len2 else entity2
    
    def _validate_anonymization(self, original_text: str, anonymized_text: str, entities: List[Entity]) -> Dict[str, Any]:
        """Validation complète de l'anonymisation"""
        validation = {
            "success": True,
            "issues": [],
            "warnings": [],
            "stats": {}
        }
        
        # Vérifier que les entités ont été remplacées
        not_replaced = []
        for entity in entities:
            if entity.value in anonymized_text:
                not_replaced.append(entity.value)
        
        if not_replaced:
            validation["success"] = False
            validation["issues"].extend([f"Non remplacé: {val}" for val in not_replaced[:5]])
        
        # Détection de fuites potentielles
        potential_leaks = self._detect_potential_leaks(anonymized_text)
        if potential_leaks:
            validation["warnings"].extend(potential_leaks)
        
        # Statistiques
        validation["stats"] = {
            "original_length": len(original_text),
            "anonymized_length": len(anonymized_text),
            "entities_replaced": len(entities),
            "not_replaced_count": len(not_replaced),
            "potential_leaks": len(potential_leaks),
            "success_rate": (len(entities) - len(not_replaced)) / len(entities) * 100 if entities else 100
        }
        
        return validation
    
    def _detect_potential_leaks(self, text: str) -> List[str]:
        """Détecter des fuites potentielles dans le texte anonymisé"""
        leaks = []
        
        # Patterns pour détecter des données manquées
        leak_patterns = {
            "email_like": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            "phone_like": r'\b(?:\+33|0)[1-9](?:[0-9\s.-]{8,})\b',
            "iban_like": r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}[A-Z0-9]*\b',
            "potential_name": r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b',
            "date_like": r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b'
        }
        
        for pattern_name, pattern in leak_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                # Filtrer les faux positifs connus
                filtered_matches = self._filter_false_positives(matches, pattern_name)
                if filtered_matches:
                    leaks.append(f"Fuite potentielle {pattern_name}: {len(filtered_matches)} occurrence(s)")
        
        return leaks
    
    def _filter_false_positives(self, matches: List[str], pattern_type: str) -> List[str]:
        """Filtrer les faux positifs"""
        if pattern_type == "potential_name":
            # Exclure les mots français courants
            common_words = {'Le Havre', 'La Rochelle', 'Saint Pierre', 'Notre Dame'}
            return [m for m in matches if m not in common_words]
        
        elif pattern_type == "phone_like":
            # Vérifier que c'est vraiment un numéro de téléphone
            return [m for m in matches if len(re.sub(r'\D', '', m)) >= 8]
        
        return matches
    
    def _generate_processing_stats(self, entities: List[Entity], text: str, processing_time: float) -> Dict[str, Any]:
        """Générer des statistiques de traitement"""
        entity_types = {}
        confidence_values = []
        method_counts = {}
        
        for entity in entities:
            # Types
            entity_type = entity.type
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            # Confiance
            if hasattr(entity, 'confidence'):
                confidence_values.append(entity.confidence)
            
            # Méthodes
            method = getattr(entity, 'method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            "total_entities": len(entities),
            "entity_types": entity_types,
            "method_distribution": method_counts,
            "processing_time": processing_time,
            "text_length": len(text),
            "entities_per_second": len(entities) / processing_time if processing_time > 0 else 0,
            "most_common_type": max(entity_types, key=entity_types.get) if entity_types else None
        }
    
    def cleanup(self):
        """Nettoyer les ressources"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logging.warning(f"Erreur nettoyage: {e}")

# === EXPORT DES CLASSES PRINCIPALES ===
__all__ = [
    'Entity',
    'RegexAnonymizer', 
    'AIAnonymizer',
    'DocumentProcessor',
    'DocumentAnonymizer',
    'EntityValidator',
    'PerformanceMonitor',
    'AI_SUPPORT',
    'SPACY_SUPPORT',
    'TRANSFORMERS_SUPPORT',
    'PDF_SUPPORT',
    'PYTORCH_AVAILABLE'
]

# === INITIALISATION ET TESTS ===
if __name__ == "__main__":
    # Test rapide du système
    print("=== TEST DU SYSTÈME D'ANONYMISATION ===")
    print(f"PyTorch disponible: {PYTORCH_AVAILABLE}")
    print(f"Support IA: {AI_SUPPORT}")
    print(f"Support SpaCy: {SPACY_SUPPORT}")
    print(f"Support Transformers: {TRANSFORMERS_SUPPORT}")
    print(f"Support PDF: {PDF_SUPPORT}")
    
    # Test de base
    try:
        anonymizer = DocumentAnonymizer()
        print("✅ DocumentAnonymizer initialisé avec succès")
        
        # Test regex
        test_text = "Contactez Jean Dupont au 01 23 45 67 89 ou jean.dupont@email.com"
        entities = anonymizer.regex_anonymizer.detect_entities(test_text)
        print(f"✅ Test regex: {len(entities)} entités détectées")
        
        # Test IA si disponible
        if anonymizer.ai_anonymizer:
            ai_entities = anonymizer.ai_anonymizer.detect_entities_ai(test_text, 0.7)
            print(f"✅ Test IA: {len(ai_entities)} entités détectées")
        else:
            print("ℹ️ Test IA ignoré (non disponible)")
        
        print("✅ Tous les tests passés avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur lors des tests: {e}")
        """Vérifier si deux entités se chevauchent"""
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)
    
    def _resolve_overlap_conflict(self, entity1: Entity, entity2: Entity) -> Entity:
        """Résoudre un conflit de chevauchement avec priorité intelligente"""
        # Priorité 1: Types structurés (EMAIL, PHONE, etc.)
        structured_types = {"EMAIL", "PHONE", "IBAN", "SIRET", "SIREN", "SSN", "TVA"}
        
        if entity1.type in structured_types and entity2.type not in structured_types:
            return entity1
        elif entity2.type in structured_types and entity1.type not in structured_types:
            return entity2
        
        # Priorité 2: Longueur (plus long = plus spécifique)
        len1 = entity1.end - entity1.start
        len2 = entity2.end - entity2.start
        
        if len1 != len2:
            return entity1 if len1 > len2 else entity2
        
        # Priorité 3: Confiance
        return entity1 if entity1.confidence >= entity2.confidence else entity2
    
    def _clean_entities(self, entities: List[Entity]) -> List[Entity]:
        """Nettoyer et valider les entités"""
        cleaned = []
        
        for entity in entities:
            # Nettoyer la valeur
            cleaned_value = self._clean_entity_value(entity.value)
            if cleaned_value and len(cleaned_value) > 1:
                entity.value = cleaned_value
                cleaned.append(entity)
        
        return cleaned
    
    def _clean_entity_value(self, value: str) -> str:
        """Nettoyer la valeur d'une entité"""
        # Supprimer espaces début/fin
        cleaned = value.strip()
        
        # Supprimer ponctuation finale
        cleaned = re.sub(r'[.,;:!?]+$', '', cleaned)
        
        # Supprimer caractères de contrôle
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        return cleaned
    
    def anonymize_text(self, text: str, entities: List[Entity]) -> str:
        """Anonymiser le texte en remplaçant les entités"""
        # Trier par position décroissante pour éviter les décalages
        sorted_entities = sorted(entities, key=lambda x: x.start, reverse=True)
        
        anonymized_text = text
        for entity in sorted_entities:
            replacement = entity.replacement or f"[{entity.type}]"
            anonymized_text = (
                anonymized_text[:entity.start] + 
                replacement + 
                anonymized_text[entity.end:]
            )
        
        return anonymized_text

class AIAnonymizer:
    """Anonymiseur IA avec NER multi-modèles et gestion des conflits Streamlit"""
    
    def __init__(self, model_config: dict = None, prefer_french: bool = True):
        self.model_config = model_config or self._get_best_model(prefer_french)
        self.nlp_pipeline = None
        self.spacy_nlp = None
        self.regex_anonymizer = RegexAnonymizer(use_french_patterns=True)
        self.prefer_french = prefer_french
        self.model_loaded = False
        
        # Initialiser le modèle en mode thread-safe
        self._initialize_model_safe()
    
    def _get_best_model(self, prefer_french: bool) -> dict:
        """Sélectionner le meilleur modèle disponible selon les préférences"""
        if prefer_french:
            if SPACY_SUPPORT:
                return AI_MODELS["french_spacy_lg"]
            elif TRANSFORMERS_SUPPORT:
                return AI_MODELS["french_camembert"]
            else:
                return AI_MODELS["multilingual_bert"]
        else:
            return AI_MODELS["distilbert_lightweight"]
    
    def _initialize_model_safe(self):
        """Initialisation thread-safe du modèle IA"""
        with _pytorch_lock:
            try:
                if self.model_config["type"] == "spacy":
                    self._initialize_spacy()
                else:
                    self._initialize_transformers()
                self.model_loaded = True
                
            except Exception as e:
                logging.error(f"Échec du chargement du modèle IA: {e}")
                logging.info("Fallback vers mode regex uniquement")
    
    def _initialize_spacy(self):
        """Initialiser SpaCy (recommandé pour le français)"""
        if not SPACY_SUPPORT:
            raise Exception("SpaCy non disponible")
        
        try:
            self.spacy_nlp = spacy.load(self.model_config["name"])
            logging.info(f"Modèle SpaCy chargé: {self.model_config['name']}")
            
        except OSError:
            # Essayer le modèle compact si le large n'est pas disponible
            if self.model_config["name"] == "fr_core_news_lg":
                try:
                    self.spacy_nlp = spacy.load("fr_core_news_sm")
                    logging.info("Modèle SpaCy compact chargé: fr_core_news_sm")
                    return
                except OSError:
                    pass
            
            raise Exception(f"Modèle SpaCy non trouvé: {self.model_config['name']}")
        
        except Exception as e:
            raise Exception(f"Erreur SpaCy: {e}")
    
    def _initialize_transformers(self):
        """Initialiser Transformers avec protection anti-conflit"""
        if not TRANSFORMERS_SUPPORT:
            raise Exception("Transformers non disponible")
        
        try:
            # Configuration pipeline avec protection thread
            self.nlp_pipeline = pipeline(
                "ner",
                model=self.model_config["name"],
                aggregation_strategy="simple",
                device=-1,  # Forcer CPU
                return_all_scores=False
            )
            
            logging.info(f"Pipeline Transformers chargé: {self.model_config['name']}")
            
        except Exception as e:
            # Fallback vers un modèle plus léger
            try:
                self.nlp_pipeline = pipeline(
                    "ner",
                    model=AI_MODELS["distilbert_lightweight"]["name"],
                    aggregation_strategy="simple",
                    device=-1
                )
                logging.info("Modèle fallback Transformers chargé")
                
            except Exception as e2:
                raise Exception(f"Tous les modèles Transformers ont échoué: {e}, {e2}")
    
    def detect_entities_ai(self, text: str, confidence_threshold: float = 0.7) -> List[Entity]:
        """Détection d'entités avec IA + fusion regex"""
        entities = []
        
        # Étape 1: Détection IA
        if self.model_loaded:
            try:
                if self.spacy_nlp:
                    ai_entities = self._detect_with_spacy(text, confidence_threshold)
                elif self.nlp_pipeline:
                    ai_entities = self._detect_with_transformers(text, confidence_threshold)
                else:
                    ai_entities = []
                
                entities.extend(ai_entities)
                logging.info(f"IA: {len(ai_entities)} entités détectées")
                
            except Exception as e:
                logging.error(f"Erreur détection IA: {e}")
        
        # Étape 2: Compléter avec regex pour les entités structurées
        regex_entities = self.regex_anonymizer.detect_entities(text)
        entities.extend(self._merge_regex_entities(entities, regex_entities))
        
        # Étape 3: Post-traitement final
        entities = self._post_process_entities(entities, text)
        
        logging.info(f"Total final: {len(entities)} entités")
        return entities
    
    def _detect_with_spacy(self, text: str, confidence_threshold: float) -> List[Entity]:
        """Détection avec SpaCy optimisée"""
        entities = []
        
        try:
            # Traitement par chunks pour les gros documents
            chunks = self._chunk_text(text, max_length=1000000)  # 1M chars max par chunk
            
            for chunk_start, chunk_text in chunks:
                doc = self.spacy_nlp(chunk_text)
                
                for ent in doc.ents:
                    # Calculer confiance approximative pour SpaCy
                    confidence = self._calculate_spacy_confidence(ent)
                    
                    if confidence >= confidence_threshold:
                        entity_type = self._map_spacy_label(ent.label_)
                        
                        entity = Entity(
                            id=f"spacy_{uuid.uuid4().hex[:8]}",
                            type=entity_type,
                            value=ent.text.strip(),
                            start=chunk_start + ent.start_char,
                            end=chunk_start + ent.end_char,
                            confidence=confidence,
                            replacement=DEFAULT_REPLACEMENTS.get(entity_type, f"[{entity_type}]"),
                            context=self._extract_context(text, chunk_start + ent.start_char, chunk_start + ent.end_char),
                            method="spacy",
                            source_model=self.model_config["name"]
                        )
                        entities.append(entity)
            
            return entities
            
        except Exception as e:
            logging.error(f"Erreur SpaCy: {e}")
            return []
    
    def _detect_with_transformers(self, text: str, confidence_threshold: float) -> List[Entity]:
        """Détection avec Transformers en mode sécurisé"""
        entities = []
        
        try:
            # Protection thread pour Transformers
            with _pytorch_lock:
                chunks = self._chunk_text(text, max_length=512)
                
                for chunk_start, chunk_text in chunks:
                    try:
                        # Pipeline NER avec gestion d'erreurs
                        ner_results = self.nlp_pipeline(chunk_text)
                        
                        for result in ner_results:
                            if result['score'] >= confidence_threshold:
                                entity_type = self._map_ner_label(result['entity_group'])
                                
                                entity = Entity(
                                    id=f"transformers_{uuid.uuid4().hex[:8]}",
                                    type=entity_type,
                                    value=result['word'].strip(),
                                    start=chunk_start + result['start'],
                                    end=chunk_start + result['end'],
                                    confidence=result['score'],
                                    replacement=DEFAULT_REPLACEMENTS.get(entity_type, f"[{entity_type}]"),
                                    context=self._extract_context(text, chunk_start + result['start'], chunk_start + result['end']),
                                    method="transformers",
                                    source_model=self.model_config["name"]
                                )
                                entities.append(entity)
                    
                    except Exception as e:
                        logging.warning(f"Erreur sur chunk: {e}")
                        continue
            
            return entities
            
        except Exception as e:
            logging.error(f"Erreur Transformers: {e}")
            return []
    
    def _chunk_text(self, text: str, max_length: int = 512) -> List[Tuple[int, str]]:
        """Diviser le texte en chunks intelligents"""
        if len(text) <= max_length:
            return [(0, text)]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_length
            
            # Essayer de couper à une limite de phrase ou de paragraphe
            if end < len(text):
                # Chercher un point suivi d'espace et majuscule
                sentence_end = text.rfind('. ', start, end)
                if sentence_end > start + max_length // 2:
                    end = sentence_end + 1
                else:
                    # Sinon, chercher un espace
                    space_pos = text.rfind(' ', start + max_length // 2, end)
                    if space_pos > start:
                        end = space_pos
            
            chunks.append((start, text[start:end]))
            start = end
        
        return chunks
    
    def _calculate_spacy_confidence(self, ent) -> float:
        """Calculer une confiance approximative pour SpaCy"""
        # Facteurs de confiance basés sur le type et les caractéristiques
        type_confidence = {
            'PER': 0.92, 'PERSON': 0.92,
            'ORG': 0.88,
            'LOC': 0.85, 'GPE': 0.85,
            'MISC': 0.75,
            'DATE': 0.90,
            'MONEY': 0.88,
            'PERCENT': 0.85
        }
        
        base_confidence = type_confidence.get(ent.label_, 0.80)
        
        # Ajustements
        # Longueur: entités plus longues = plus fiables
        length_factor = min(1.1, 1.0 + (len(ent.text) - 3) * 0.02)
        
        # Capitalisation: noms propres plus fiables
        if ent.text[0].isupper() and ent.label_ in ['PER', 'PERSON', 'ORG']:
            capitalization_factor = 1.05
        else:
            capitalization_factor = 1.0
        
        final_confidence = base_confidence * length_factor * capitalization_factor
        return min(0.98, final_confidence)
    
    def _map_spacy_label(self, spacy_label: str) -> str:
        """Mapper les labels SpaCy vers nos types"""
        mapping = {
            'PER': 'PERSON', 'PERSON': 'PERSON',
            'ORG': 'ORG',
            'LOC': 'LOCATION', 'GPE': 'LOCATION',
            'MISC': 'MISC',
            'DATE': 'DATE', 'TIME': 'DATE',
            'MONEY': 'MONEY',
            'PERCENT': 'PERCENT',
            'CARDINAL': 'NUMBER',
            'ORDINAL': 'NUMBER'
        }
        return mapping.get(spacy_label.upper(), spacy_label.upper())
    
    def _map_ner_label(self, ner_label: str) -> str:
        """Mapper les labels NER Transformers vers nos types"""
        mapping = {
            'PER': 'PERSON', 'PERSON': 'PERSON',
            'ORG': 'ORG', 'ORGANIZATION': 'ORG',
            'LOC': 'LOCATION', 'LOCATION': 'LOCATION',
            'MISC': 'MISC',
            'DATE': 'DATE', 'TIME': 'DATE'
        }
        return mapping.get(ner_label.upper(), ner_label.upper())
    
    def _merge_regex_entities(self, ai_entities: List[Entity], regex_entities: List[Entity]) -> List[Entity]:
        """Fusionner intelligemment les entités IA et regex"""
        merged = []
        
        for regex_entity in regex_entities:
            is_duplicate = False
            
            # Vérifier les chevauchements avec les entités IA
            for ai_entity in ai_entities:
                overlap = self._calculate_overlap(regex_entity, ai_entity)
                
                if overlap > 0.3:  # 30% de chevauchement
                    # Priorité aux entités structurées regex
                    if regex_entity.type in ['EMAIL', 'PHONE', 'IBAN', 'SIRET', 'SIREN', 'SSN', 'TVA']:
                        # Garder regex, supprimer IA
                        try:
                            ai_entities.remove(ai_entity)
                        except ValueError:
                            pass
                        break
                    else:
                        # Garder IA pour les entités non-structurées
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                merged.append(regex_entity)
        
        return merged
    
    def _calculate_overlap(self, entity1: Entity, entity2: Entity) -> float:
        """Calculer le pourcentage de chevauchement entre deux entités"""
        if entity1.end <= entity2.start or entity2.end <= entity1.start:
            return 0.0  # Pas de chevauchement
        
        overlap_start = max(entity1.start, entity2.start)
        overlap_end = min(entity1.end, entity2.end)
        overlap_length = max(0, overlap_end - overlap_start)
        total_length = min(entity1.end, entity2.end) - max(entity1.start, entity2.start)
        
        return overlap_length / total_length if total_length > 0 else 0.0
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 120) -> str:
        """Extraction de contexte intelligent"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        
        # Essayer de couper à des limites de mots
        context = text[context_start:context_end]
        
        # Marquer l'entité
        entity_value = text[start:end]
        relative_start = start - context_start
        relative_end = end - context_start
        
        if 0 <= relative_start < len(context) and 0 <= relative_end <= len(context):
            highlighted_context = (
                context[:relative_start] + 
                f"**{entity_value}**" + 
                context[relative_end:]
            )
        else:
            highlighted_context = context
        
        return highlighted_context.strip()
    
    def _post_process_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Post-traitement avec optimisations françaises"""
        processed = []
        
        for entity in entities:
            # Validation de base
            if not self._is_valid_entity(entity, text):
                continue
            
            # Nettoyage de la valeur
            entity.value = self._clean_entity_value(entity.value)
            
            # Amélioration du contexte
            if not entity.context:
                entity.context = self._extract_context(text, entity.start, entity.end)
            
            # Classification fine française
            entity.type = self._refine_french_classification(entity, text)
            
            processed.append(entity)
        
        # Résolution des conflits
        processed = self._resolve_entity_conflicts(processed)
        
        return processed
    
    def _is_valid_entity(self, entity: Entity, text: str) -> bool:
        """Validation robuste des entités"""
        # Vérifications de base
        if entity.start < 0 or entity.end > len(text):
            return False
        
        if entity.start >= entity.end:
            return False
        
        if len(entity.value.strip()) < 2:
            return False
        
        # Vérification cohérence texte
        actual_value = text[entity.start:entity.end]
        if actual_value.strip().lower() != entity.value.strip().lower():
            # Tentative de correction
            search_start = max(0, entity.start - 10)
            search_end = min(len(text), entity.end + 10)
            search_area = text[search_start:search_end]
            
            if entity.value in search_area:
                corrected_start = search_area.find(entity.value) + search_start
                entity.start = corrected_start
                entity.end = corrected_start + len(entity.value)
            else:
                return False
        
        return True
    
    def _clean_entity_value(self, value: str) -> str:
        """Nettoyage avancé des valeurs d'entités"""
        # Supprimer espaces début/fin
        cleaned = value.strip()
        
        # Supprimer ponctuation finale
        cleaned = re.sub(r'[.,;:!?]+, '', cleaned)
        
        # Supprimer caractères bizarres
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        # Normaliser espaces internes
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def _refine_french_classification(self, entity: Entity, text: str) -> str:
        """Classification fine pour le contexte français"""
        value = entity.value.lower()
        
        # Amélioration PERSON
        if entity.type == 'PERSON':
            context_before = text[max(0, entity.start - 30):entity.start].lower()
            
            # Vérifier titres français
            french_titles = ['monsieur', 'madame', 'mademoiselle', 'docteur', 'professeur', 'maître']
            if any(title in context_before for title in french_titles):
                return 'PERSON'
            
            # Détecter organisations
            org_words = ['société', 'entreprise', 'sarl', 'sas', 'cabinet', 'étude', 'bureau']
            if any(word in value for word in org_words):
                return 'ORG'
        
        # Amélioration ORG
        elif entity.type == 'ORG':
            legal_forms = ['sarl', 'sas', 'sa', 'snc', 'eurl', 'sasu', 'sci', 'selarl', 'selas', 'selca']
            if any(form in value for form in legal_forms):
                return 'ORG'
        
        return entity.type
    
    def _resolve_entity_conflicts(self, entities: List[Entity]) -> List[Entity]:
        """Résolution intelligente des conflits"""
        if not entities:
            return entities
        
        # Trier par position
        sorted_entities = sorted(entities, key=lambda x: x.start)
        resolved = []
        
        for current in sorted_entities:
            conflict_found = False
            
            for i, existing in enumerate(resolved):
                if self._entities_overlap(current, existing):
                    winner = self._resolve_conflict(current, existing)
                    resolved[i] = winner
                    conflict_found = True
                    break
            
            if not conflict_found:
                resolved.append(current)
        
        return resolved
    
    def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool:
        """Vérification de chevauchement"""
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)
    
    def _resolve_conflict(self, entity1: Entity, entity2: Entity) -> Entity:
        """Résolution de conflit avec priorités intelligentes"""
        # Priorité 1: Types structurés
        structured_types = {'EMAIL', 'PHONE', 'IBAN', 'SIRET', 'SIREN', 'SSN', 'TVA'}
        
        if entity1.type in structured_types and entity2.type not in structured_types:
            return entity1
        elif entity2.type in structured_types and entity1.type not in structured_types:
            return entity2
        
        # Priorité 2: Méthode (regex > spacy > transformers pour les conflits)
        method_priority = {'regex': 3, 'spacy': 2, 'transformers': 1}
        
        priority1 = method_priority.get(entity1.method, 0)
        priority2 = method_priority.get(entity2.method, 0)
        
        if priority1 != priority2:
            return entity1 if priority1 > priority2 else entity2
        
        # Priorité 3: Confiance
        if abs(entity1.confidence - entity2.confidence) > 0.15:
            return entity1 if entity1.confidence > entity2.confidence else entity2
        
        # Priorité 4: Longueur (plus spécifique)
        len1 = entity1.end - entity1.start
        len2 = entity2.end - entity2.start
        
        return entity1 if len1 >= len2 else entity2

class DocumentProcessor:
    """Processeur de documents avec gestion d'erreurs robuste"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.doc', '.txt']
        self.max_text_length = 10_000_000  # 10M caractères max
    
    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, Dict]:
        """Extraction PDF robuste avec fallbacks multiples"""
        if not PDF_SUPPORT:
            raise Exception("Support PDF non disponible. Installez pdfplumber et pdf2docx.")
        
        text_content = ""
        metadata = {"pages": 0, "format": "pdf", "extraction_method": None}
        
        # Méthode 1: pdfplumber (recommandée)
        try:
            with pdfplumber.open(file_path) as pdf:
                metadata["pages"] = len(pdf.pages)
                metadata["extraction_method"] = "pdfplumber"
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"\n--- Page {page_num} ---\n{page_text}"
                        
                        # Extraire les tableaux si peu de texte
                        if len(page_text or "") < 100:
                            tables = page.extract_tables()
                            if tables:
                                text_content += f"\n--- Tableaux Page {page_num} ---\n"
                                for table in tables:
                                    for row in table:
                                        if row:
                                            text_content += " | ".join([cell or "" for cell in row]) + "\n"
                    
                    except Exception as e:
                        logging.warning(f"Erreur page {page_num}: {e}")
                        continue
            
            if text_content.strip():
                metadata["text_length"] = len(text_content)
                return text_content, metadata
        
        except Exception as e:
            logging.warning(f"pdfplumber échoué: {e}")
        
        # Méthode 2: PyMuPDF fallback
        try:
            import fitz
            metadata["extraction_method"] = "pymupdf"
            
            doc = fitz.open(file_path)
            metadata["pages"] = len(doc)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text:
                    text_content += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            doc.close()
            metadata["text_length"] = len(text_content)
            return text_content, metadata
        
        except ImportError:
            logging.warning("PyMuPDF non disponible")
        except Exception as e:
            logging.warning(f"PyMuPDF échoué: {e}")
        
        # Méthode 3: pdf2docx puis extraction DOCX
        try:
            temp_docx = tempfile.mktemp(suffix='.docx')
            pdf2docx_parse(file_path, temp_docx)
            
            text_content, docx_metadata = self.extract_text_from_docx(temp_docx)
            metadata.update(docx_metadata)
            metadata["extraction_method"] = "pdf2docx"
            
            os.unlink(temp_docx)
            return text_content, metadata
        
        except Exception as e:
            logging.warning(f"pdf2docx échoué: {e}")
        
        raise Exception("Impossible d'extraire le texte du PDF avec toutes les méthodes disponibles")
    
    def extract_text_from_docx(self, file_path: str) -> Tuple[str, Dict]:
        """Extraction DOCX complète avec métadonnées"""
        try:
            doc = Document(file_path)
            
            text_content = ""
            metadata = {
                "paragraphs": 0,
                "tables": 0, 
                "headers": 0,
                "footers": 0,
                "format": "docx"
            }
            
            # Extraction paragraphes
            for para in doc.paragraphs:
                if para.text.strip():
                    text_content += para.text + "\n"
                    metadata["paragraphs"] += 1
            
            # Extraction tableaux
            for table in doc.tables:
                metadata["tables"] += 1
                text_content += "\n--- Tableau ---\n"
                
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            row_text.append(cell_text)
                    
                    if row_text:
                        text_content += " | ".join(row_text) + "\n"
            
            # Extraction en-têtes et pieds de page
            for section in doc.sections:
                if section.header:
                    for para in section.header.paragraphs:
                        if para.text.strip():
                            text_content += f"[EN-TÊTE] {para.text}\n"
                            metadata["headers"] += 1
                
                if section.footer:
                    for para in section.footer.paragraphs:
                        if para.text.strip():
                            text_content += f"[PIED DE PAGE] {para.text}\n"
                            metadata["footers"] += 1
            
            # Limitation de taille
            if len(text_content) > self.max_text_length:
                text_content = text_content[:self.max_text_length]
                logging.warning(f"Texte tronqué à {self.max_text_length} caractères")
            
            metadata["text_length"] = len(text_content)
            return text_content, metadata
        
        except Exception as e:
            raise Exception(f"Échec extraction DOCX: {str(e)}")
    
    def extract_text_from_txt(self, file_path: str) -> Tuple[str, Dict]:
        """Extraction fichier texte avec encodage intelligent"""
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    text_content = f.read()
                
                # Limitation de taille
                if len(text_content) > self.max_text_length:
                    text_content = text_content[:self.max_text_length]
                    logging.warning(f"Texte tronqué à {self.max_text_length} caractères")
                
                metadata = {
                    "format": "txt",
                    "encoding": encoding,
                    "text_length": len(text_content),
                    "lines": text_content.count('\n') + 1
                }
                
                return text_content, metadata
            
            except UnicodeDecodeError:
                continue
            except Exception as e:
                raise Exception(f"Erreur lecture fichier texte: {e}")
        
        raise Exception("Impossible de décoder le fichier texte avec les encodages supportés")
    
    def process_file(self, file_path: str) -> Tuple[str, Dict]:
        """Traitement unifié avec détection automatique"""
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        
        if file_ext == '.pdf':
            return self.extract_text_from_pdf(str(file_path))
        elif file_ext in ['.docx', '.doc']:
            return self.extract_text_from_docx(str(file_path))
        elif file_ext == '.txt':
            return self.extract_text_from_txt(str(file_path))
        else:
            raise Exception(f"Format non supporté: {file_ext}")

class DocumentAnonymizer:
    """Anonymiseur principal avec IA fonctionnelle et optimisations Streamlit"""
    
    def __init__(self, prefer_french: bool = True, use_spacy: bool = True):
        self.regex_anonymizer = RegexAnonymizer(use_french_patterns=True)
        
        # Initialisation IA conditionnelle
        if AI_SUPPORT or SPACY_SUPPORT:
            try:
                self.ai_anonymizer = AIAnonymizer(prefer_french=prefer_french)
                logging.info("AIAnonymizer initialisé avec succès")
            except Exception as e:
                self.ai_anonymizer = None
                logging.warning(f"AIAnonymizer non disponible: {e}")
        else:
            self.ai_anonymizer = None
            logging.info("Mode regex uniquement (IA non disponible)")
        
        self.document_processor = DocumentProcessor()
        self.temp_dir = tempfile.mkdtemp()
        self.prefer_french = prefer_french
        
        # Statistiques de traitement
        self.processing_stats = {
            "documents_processed": 0,
            "entities_detected": 0,
            "processing_time": 0.0,
            "ai_available": self.ai_anonymizer is not None
        }
    
    def process_document(self, file_path: str, mode: str = "ai", confidence: float = 0.7) -> Dict[str, Any]:
        """Traitement principal avec gestion optimisée des performances"""
        import time
        start_time = time.time()
        
        try:
            # Validation des paramètres
            if mode not in ["regex", "ai"]:
                mode = "regex"
            
            if not (0.0 <= confidence <= 1.0):
                confidence = 0.7
            
            # Forcer regex si IA non disponible
            if mode == "ai" and not self.ai_anonymizer:
                mode = "regex"
                logging.warning("Mode IA demandé mais non disponible, fallback vers regex")
            
            # Extraction du texte
            logging.info(f"Traitement du document: {file_path}")
            text, metadata = self.document_processor.process_file(file_path)
            
            if not text.strip():
                return {
                    "status": "error",
                    "error": "Aucun texte trouvé dans le document"
                }
            
            # Prétraitement du texte
            text = self._preprocess_text(text)
            logging.info(f"Texte extrait: {len(text)} caractères")
            
            # Détection des entités selon le mode
            if mode == "ai" and self.ai_anonymizer:
                logging.info("Détection IA en cours...")
                entities = self.ai_anonymizer.detect_entities_ai(text, confidence)
                metadata["detection_method"] = "ai"
            else:
                logging.info("Détection regex en cours...")
                entities = self.regex_anonymizer.detect_entities(text)
                metadata["detection_method"] = "regex"
            
            logging.info(f"Entités détectées: {len(entities)}")
            
            # Post-traitement et validation
            entities = self._post_process_entities(entities, text)
            
            # Anonymisation
            anonymized_text = self.regex_anonymizer.anonymize_text(text, entities)
            
            # Validation de l'anonymisation
            validation_result = self._validate_anonymization(text, anonymized_text, entities)
            
            # Création du document anonymisé
            anonymized_path = self._create_anonymized_document(
                file_path, anonymized_text, metadata, entities
            )
            
            # Calcul des métriques
            processing_time = time.time() - start_time
            self.processing_stats["documents_processed"] += 1
            self.processing_stats["entities_detected"] += len(entities)
            self.processing_stats["processing_time"] += processing_time
            
            # Génération des statistiques
            stats = self._generate_processing_stats(entities, text, processing_time)
            
            return {
                "status": "success",
                "entities": [asdict(entity) for entity in entities],
                "text": text,
                "anonymized_text": anonymized_text,
                "anonymized_path": anonymized_path,
                "metadata": {**metadata, **stats},
                "mode": mode,
                "confidence": confidence,
                "validation": validation_result,
                "processing_time": processing_time
            }
        
        except Exception as e:
            processing_time = time.time() - start_time
            logging.error(f"Erreur traitement document: {str(e)}")
            return {
                "status": "error", 
                "error": str(e),
                "processing_time": processing_time
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Prétraitement optimisé du texte français"""
        # Normalisation des espaces
        text = re.sub(r'\s+', ' ', text)
        
        # Normalisation caractères français
        replacements = {
            'œ': 'oe', 'Œ': 'OE',
            'æ': 'ae', 'Æ': 'AE',
            '«': '"', '»': '"',
            ''': "'", ''': "'",
            '"': '"', '"': '"'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Nettoyage caractères de contrôle
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()
    
    def _post_process_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Post-traitement avec optimisations françaises"""
        processed = []
        
        for entity in entities:
            # Validation de base
            if not self._is_valid_entity(entity, text):
                continue
            
            # Nettoyage de la valeur
            entity.value = self._clean_entity_value(entity.value)
            
            # Amélioration du contexte
            if not entity.context:
                entity.context = self._extract_context(text, entity.start, entity.end)
            
            # Classification fine française
            entity.type = self._refine_french_classification(entity, text)
            
            processed.append(entity)
        
        # Résolution des conflits
        processed = self._resolve_entity_conflicts(processed)
        
        return processed
    
    def _is_valid_entity(self, entity: Entity, text: str) -> bool:
        """Validation robuste des entités"""
        # Vérifications de base
        if entity.start < 0 or entity.end > len(text):
            return False
        
        if entity.start >= entity.end:
            return False
        
        if len(entity.value.strip()) < 2:
            return False
        
        # Vérification cohérence texte
        actual_value = text[entity.start:entity.end]
        if actual_value.strip().lower() != entity.value.strip().lower():
            # Tentative de correction
            search_start = max(0, entity.start - 10)
            search_end = min(len(text), entity.end + 10)
            search_area = text[search_start:search_end]
            
            if entity.value in search_area:
                corrected_start = search_area.find(entity.value) + search_start
                entity.start = corrected_start
                entity.end = corrected_start + len(entity.value)
            else:
                return False
        
        return True
    
    def _clean_entity_value(self, value: str) -> str:
        """Nettoyage avancé des valeurs d'entités"""
        # Supprimer espaces début/fin
        cleaned = value.strip()
        
        # Supprimer ponctuation finale
        cleaned = re.sub(r'[.,;:!?]+, '', cleaned)
        
        # Supprimer caractères bizarres
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        # Normaliser espaces internes
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 120) -> str:
        """Extraction de contexte intelligent"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        
        # Essayer de couper à des limites de mots
        context = text[context_start:context_end]
        
        # Marquer l'entité
        entity_value = text[start:end]
        relative_start = start - context_start
        relative_end = end - context_start
        
        if 0 <= relative_start < len(context) and 0 <= relative_end <= len(context):
            highlighted_context = (
                context[:relative_start] + 
                f"**{entity_value}**" + 
                context[relative_end:]
            )
        else:
            highlighted_context = context
        
        return highlighted_context.strip()
    
    def _refine_french_classification(self, entity: Entity, text: str) -> str:
        """Classification fine pour le contexte français"""
        value = entity.value.lower()
        
        # Amélioration PERSON
        if entity.type == 'PERSON':
            context_before = text[max(0, entity.start - 30):entity.start].lower()
            
            # Vérifier titres français
            french_titles = ['monsieur', 'madame', 'mademoiselle', 'docteur', 'professeur', 'maître']
            if any(title in context_before for title in french_titles):
                return 'PERSON'
            
            # Détecter organisations
            org_words = ['société', 'entreprise', 'sarl', 'sas', 'cabinet', 'étude', 'bureau']
            if any(word in value for word in org_words):
                return 'ORG'
        
        # Amélioration ORG
        elif entity.type == 'ORG':
            legal_forms = ['sarl', 'sas', 'sa', 'snc', 'eurl', 'sasu', 'sci', 'selarl', 'selas', 'selca']
            if any(form in value for form in legal_forms):
                return 'ORG'
        
        return entity.type
    
    def _resolve_entity_conflicts(self, entities: List[Entity]) -> List[Entity]:
        """Résolution intelligente des conflits"""
        if not entities:
            return entities
        
        # Trier par position
        sorted_entities = sorted(entities, key=lambda x: x.start)
        resolved = []
        
        for current in sorted_entities:
            conflict_found = False
            
            for i, existing in enumerate(resolved):
                if self._entities_overlap(current, existing):
                    winner = self._resolve_conflict(current, existing)
                    resolved[i] = winner
                    conflict_found = True
                    break
            
            if not conflict_found:
                resolved.append(current)
        
        return resolved
    
    def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool: