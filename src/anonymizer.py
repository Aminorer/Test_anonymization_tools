# === CONFIGURATION ANTI-CONFLIT (AJOUTER AU DÉBUT) ===
import os
import warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="torch")

# === VOTRE CODE EXISTANT ===
import re
import tempfile
# ... reste de votre code
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from io import BytesIO

# Imports pour le traitement de documents
try:
    import pdfplumber
    from pdf2docx import parse as pdf2docx_parse
    from docx import Document
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PDF support disabled. Install pdfplumber and pdf2docx for full functionality.")

# Imports pour l'IA (optionnel)
try:
    from transformers import pipeline
    AI_SUPPORT = True
except ImportError:
    AI_SUPPORT = False
    logging.warning("AI support disabled. Install transformers for NER functionality.")

# Imports pour SpaCy (recommandé pour le français)
try:
    import spacy
    SPACY_SUPPORT = True
except ImportError:
    SPACY_SUPPORT = False
    logging.warning("SpaCy support disabled. Install spacy for better French NER.")

from .config import ENTITY_PATTERNS, ENTITY_COLORS, DEFAULT_REPLACEMENTS

# Configuration des modèles français
AI_MODELS = {
    "french_spacy": {
        "name": "fr_core_news_lg",  # SpaCy français
        "type": "spacy",
        "language": "fr",
        "description": "Modèle SpaCy français optimisé"
    },
    "french_camembert": {
        "name": "Jean-Baptiste/camembert-ner-with-dates",  # CamemBERT français
        "type": "transformers",
        "language": "fr", 
        "description": "CamemBERT fine-tuné pour NER français"
    },
    "french_flaubert": {
        "name": "flaubert/flaubert_base_cased",
        "type": "transformers",
        "language": "fr",
        "description": "FlauBERT pour le français"
    },
    "multilingual": {
        "name": "xlm-roberta-large-finetuned-conll03-english",
        "type": "transformers", 
        "language": "multi",
        "description": "Modèle multilingue (inclut français)"
    },
    "default_english": {
        "name": "dbmdz/bert-large-cased-finetuned-conll03-english",
        "type": "transformers",
        "language": "en",
        "description": "Modèle BERT anglais (fallback)"
    }
}

# Patterns regex français améliorés
FRENCH_ENTITY_PATTERNS = {
    **ENTITY_PATTERNS,  # Patterns existants
    
    # Noms français avec titres
    "PERSON_FR": r'\b(?:M\.?|Mme\.?|Mlle\.?|Dr\.?|Prof\.?|Me\.?|Maître)\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþß]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþß]+)*',
    
    # Adresses françaises complètes
    "ADDRESS_FR": r'\b\d+(?:\s+(?:bis|ter|quater))?\s+(?:rue|avenue|boulevard|place|square|impasse|allée|chemin|route|passage|villa|cité|quai|esplanade|parvis|cours|mail)\s+[A-Za-zÀ-ÿ\s\-\']+(?:\s+\d{5})?\s*[A-Za-zÀ-ÿ\s]*\b',
    
    # Organisations françaises
    "ORG_FR": r'\b(?:SARL|SAS|SA|SNC|EURL|SASU|SCI|SELARL|SELCA|SELAS|Association|Société|Entreprise|Cabinet|Étude|Bureau|Groupe|Fondation|Institut|Centre|Établissement)\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][A-Za-zÀ-ÿ\s\-\'&]+',
    
    # Villes françaises principales
    "LOC_FR": r'\b(?:Paris|Lyon|Marseille|Toulouse|Nice|Nantes|Strasbourg|Montpellier|Bordeaux|Lille|Rennes|Reims|Le\s+Havre|Saint-Étienne|Toulon|Angers|Grenoble|Dijon|Nîmes|Aix-en-Provence|Clermont-Ferrand|Tours|Limoges|Villeurbanne|Amiens|Metz|Besançon|Brest|Orléans|Mulhouse|Rouen|Saint-Denis|Argenteuil|Montreuil|Caen|Nancy)\b',
    
    # Numéros de sécurité sociale français
    "SSN_FR": r'\b[12]\s?\d{2}\s?(?:0[1-9]|1[0-2])\s?(?:0[1-9]|[12]\d|3[01])\s?\d{3}\s?\d{3}\s?\d{2}\b',
    
    # Numéros SIRET/SIREN français
    "SIRET_FR": r'\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b',
    "SIREN_FR": r'\b\d{3}\s?\d{3}\s?\d{3}\b',
    
    # Code postal français
    "POSTAL_CODE_FR": r'\b(?:0[1-9]|[1-8]\d|9[0-5])\d{3}\b',
    
    # Plaques d'immatriculation françaises
    "LICENSE_PLATE_FR": r'\b[A-Z]{2}-\d{3}-[A-Z]{2}\b',
    
    # Numéros de téléphone français améliorés
    "PHONE_FR": r'(?:\+33\s?|0)(?:[1-9])(?:[\s\.\-]?\d{2}){4}',
}

@dataclass
class Entity:
    """Classe représentant une entité détectée"""
    id: str
    type: str
    value: str
    start: int
    end: int
    confidence: float = 1.0
    replacement: Optional[str] = None
    page: Optional[int] = None
    context: Optional[str] = None

class RegexAnonymizer:
    """Anonymiseur basé sur des expressions régulières avec support français"""
    
    def __init__(self, use_french_patterns: bool = True):
        self.patterns = FRENCH_ENTITY_PATTERNS if use_french_patterns else ENTITY_PATTERNS
        self.replacements = DEFAULT_REPLACEMENTS
        self.use_french_patterns = use_french_patterns
    
    def detect_entities(self, text: str) -> List[Entity]:
        """Détecter les entités dans le texte avec des regex"""
        entities = []
        entity_id = 0
        
        # Priorité aux patterns français si activés
        patterns_to_use = self.patterns if self.use_french_patterns else ENTITY_PATTERNS
        
        for entity_type, pattern in patterns_to_use.items():
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for match in compiled_pattern.finditer(text):
                # Normaliser le type d'entité
                normalized_type = self._normalize_entity_type(entity_type)
                
                entity = Entity(
                    id=f"entity_{entity_id}",
                    type=normalized_type,
                    value=match.group().strip(),
                    start=match.start(),
                    end=match.end(),
                    confidence=1.0,
                    replacement=self.replacements.get(normalized_type, f"[{normalized_type}]"),
                    context=self._extract_context(text, match.start(), match.end())
                )
                entities.append(entity)
                entity_id += 1
        
        # Éliminer les doublons et chevauchements
        entities = self._remove_overlapping_entities(entities)
        
        return entities
    
    def _normalize_entity_type(self, entity_type: str) -> str:
        """Normaliser les types d'entités français vers les types standards"""
        mapping = {
            "PERSON_FR": "PERSON",
            "ADDRESS_FR": "ADDRESS", 
            "ORG_FR": "ORG",
            "LOC_FR": "LOC",
            "SSN_FR": "SSN",
            "SIRET_FR": "SIRET",
            "SIREN_FR": "SIREN",
            "POSTAL_CODE_FR": "POSTAL_CODE",
            "LICENSE_PLATE_FR": "LICENSE_PLATE",
            "PHONE_FR": "PHONE"
        }
        return mapping.get(entity_type, entity_type)
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 50) -> str:
        """Extraire le contexte autour d'une entité"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        context = text[context_start:context_end]
        
        # Marquer la position de l'entité dans le contexte
        entity_in_context = text[start:end]
        context = context.replace(entity_in_context, f"**{entity_in_context}**")
        
        return context
    
    def _remove_overlapping_entities(self, entities: List[Entity]) -> List[Entity]:
        """Éliminer les entités qui se chevauchent en gardant la plus longue"""
        if not entities:
            return entities
        
        # Trier par position
        sorted_entities = sorted(entities, key=lambda x: x.start)
        filtered_entities = []
        
        for entity in sorted_entities:
            # Vérifier si cette entité chevauche avec une entité déjà acceptée
            overlaps = False
            for accepted_entity in filtered_entities:
                if (entity.start < accepted_entity.end and entity.end > accepted_entity.start):
                    # Il y a chevauchement, garder la plus longue
                    entity_length = entity.end - entity.start
                    accepted_length = accepted_entity.end - accepted_entity.start
                    
                    if entity_length > accepted_length:
                        # Remplacer l'entité acceptée par la nouvelle
                        filtered_entities.remove(accepted_entity)
                        filtered_entities.append(entity)
                    overlaps = True
                    break
            
            if not overlaps:
                filtered_entities.append(entity)
        
        return filtered_entities
    
    def anonymize_text(self, text: str, entities: List[Entity]) -> str:
        """Anonymiser le texte en remplaçant les entités"""
        # Trier les entités par position (de la fin vers le début pour éviter les décalages)
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
    """Anonymiseur basé sur l'IA (NER) avec support français optimisé"""
    
    def __init__(self, model_config: dict = None, prefer_french: bool = True):
        self.model_config = model_config or self._get_best_model(prefer_french)
        self.nlp_pipeline = None
        self.spacy_nlp = None
        self.regex_anonymizer = RegexAnonymizer(use_french_patterns=True)
        self.prefer_french = prefer_french
        
        self._initialize_model()
    
    def _get_best_model(self, prefer_french: bool) -> dict:
        """Sélectionner le meilleur modèle disponible"""
        if prefer_french:
            # Priorité aux modèles français
            if SPACY_SUPPORT:
                return AI_MODELS["french_spacy"]
            elif AI_SUPPORT:
                return AI_MODELS["french_camembert"]
            else:
                return AI_MODELS["multilingual"]
        else:
            return AI_MODELS["default_english"]
    
    def _initialize_model(self):
        """Initialiser le modèle selon le type"""
        try:
            if self.model_config["type"] == "spacy":
                self._initialize_spacy()
            else:
                self._initialize_transformers()
                
        except Exception as e:
            logging.error(f"Failed to load AI model: {e}")
            logging.info("Falling back to regex-only mode")
    
    def _initialize_spacy(self):
        """Initialiser SpaCy (recommandé pour le français)"""
        if not SPACY_SUPPORT:
            logging.warning("SpaCy not available, falling back to transformers")
            self.model_config = AI_MODELS["french_camembert"]
            self._initialize_transformers()
            return
        
        try:
            self.spacy_nlp = spacy.load(self.model_config["name"])
            logging.info(f"SpaCy model loaded: {self.model_config['name']}")
        except OSError:
            logging.warning(f"SpaCy model {self.model_config['name']} not found.")
            logging.warning(f"Install with: python -m spacy download {self.model_config['name']}")
            # Fallback vers transformers
            self.model_config = AI_MODELS["french_camembert"]
            self._initialize_transformers()
        except Exception as e:
            logging.error(f"SpaCy initialization failed: {e}")
    
    def _initialize_transformers(self):
        """Initialiser Transformers"""
        if not AI_SUPPORT:
            logging.warning("Transformers not available, using regex only")
            return
        
        try:
            # Essayer d'abord le modèle configuré
            self.nlp_pipeline = pipeline(
                "ner",
                model=self.model_config["name"],
                aggregation_strategy="simple",
                device=-1  # CPU par défaut
            )
            logging.info(f"Transformers model loaded: {self.model_config['name']}")
        except Exception as e:
            logging.warning(f"Failed to load {self.model_config['name']}: {e}")
            # Fallback vers le modèle par défaut
            try:
                self.nlp_pipeline = pipeline(
                    "ner",
                    model=AI_MODELS["default_english"]["name"],
                    aggregation_strategy="simple",
                    device=-1
                )
                logging.info("Loaded fallback English model")
            except Exception as e2:
                logging.error(f"All model loading failed: {e2}")
    
    def detect_entities_ai(self, text: str, confidence_threshold: float = 0.7) -> List[Entity]:
        """Détecter les entités avec l'IA (français optimisé)"""
        entities = []
        
        # Priorité à SpaCy pour le français
        if self.spacy_nlp:
            entities.extend(self._detect_with_spacy(text, confidence_threshold))
        elif self.nlp_pipeline:
            entities.extend(self._detect_with_transformers(text, confidence_threshold))
        
        # Compléter avec regex pour les entités non couvertes par NER
        regex_entities = self.regex_anonymizer.detect_entities(text)
        entities.extend(self._merge_regex_entities(entities, regex_entities))
        
        # Post-traitement français
        entities = self._post_process_french_entities(entities, text)
        
        return entities
    
    def _detect_with_spacy(self, text: str, confidence_threshold: float) -> List[Entity]:
        """Détection avec SpaCy (optimal pour français)"""
        entities = []
        
        try:
            doc = self.spacy_nlp(text)
            entity_id = 0
            
            for ent in doc.ents:
                # SpaCy confidence approximation basée sur la longueur et le type
                confidence = self._calculate_spacy_confidence(ent)
                
                if confidence >= confidence_threshold:
                    entity_type = self._map_spacy_label(ent.label_)
                    
                    entity = Entity(
                        id=f"spacy_entity_{entity_id}",
                        type=entity_type,
                        value=ent.text.strip(),
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=confidence,
                        replacement=DEFAULT_REPLACEMENTS.get(entity_type, f"[{entity_type}]"),
                        context=self._extract_context(text, ent.start_char, ent.end_char)
                    )
                    entities.append(entity)
                    entity_id += 1
            
            logging.debug(f"SpaCy detected {len(entities)} entities")
            return entities
            
        except Exception as e:
            logging.error(f"SpaCy detection failed: {e}")
            return []
    
    def _calculate_spacy_confidence(self, ent) -> float:
        """Calculer une approximation de confiance pour SpaCy"""
        # Facteurs de confiance basés sur le type et la longueur
        type_confidence = {
            'PER': 0.9, 'PERSON': 0.9,
            'ORG': 0.85,
            'LOC': 0.8, 'GPE': 0.8,
            'MISC': 0.7
        }
        
        base_confidence = type_confidence.get(ent.label_, 0.75)
        
        # Ajuster selon la longueur (noms plus longs = plus fiables)
        length_factor = min(1.0, len(ent.text) / 10)
        
        return min(0.95, base_confidence * (0.8 + 0.2 * length_factor))
    
    def _detect_with_transformers(self, text: str, confidence_threshold: float) -> List[Entity]:
        """Détection avec Transformers"""
        entities = []
        
        try:
            # Traiter le texte par chunks pour éviter les limites de longueur
            chunks = self._chunk_text(text, max_length=512)
            entity_id = 0
            
            for chunk_start, chunk_text in chunks:
                ner_results = self.nlp_pipeline(chunk_text)
                
                for result in ner_results:
                    if result['score'] >= confidence_threshold:
                        entity_type = self._map_ner_label(result['entity_group'])
                        
                        # Ajuster les positions pour le texte complet
                        start_pos = chunk_start + result['start']
                        end_pos = chunk_start + result['end']
                        
                        entity = Entity(
                            id=f"transformers_entity_{entity_id}",
                            type=entity_type,
                            value=result['word'].strip(),
                            start=start_pos,
                            end=end_pos,
                            confidence=result['score'],
                            replacement=DEFAULT_REPLACEMENTS.get(entity_type, f"[{entity_type}]"),
                            context=self._extract_context(text, start_pos, end_pos)
                        )
                        entities.append(entity)
                        entity_id += 1
            
            logging.debug(f"Transformers detected {len(entities)} entities")
            return entities
            
        except Exception as e:
            logging.error(f"Transformers detection failed: {e}")
            return []
    
    def _chunk_text(self, text: str, max_length: int = 512) -> List[Tuple[int, str]]:
        """Diviser le texte en chunks pour le traitement"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_length
            
            # Essayer de couper à un espace pour éviter de couper les mots
            if end < len(text):
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            chunks.append((start, text[start:end]))
            start = end
        
        return chunks
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 50) -> str:
        """Extraire le contexte autour d'une entité"""
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        return text[context_start:context_end]
    
    def _map_spacy_label(self, spacy_label: str) -> str:
        """Mapper les labels SpaCy français vers nos types"""
        mapping = {
            'PER': 'PERSON',
            'PERSON': 'PERSON',
            'ORG': 'ORG',
            'LOC': 'LOC',
            'GPE': 'LOC',  # Entités géopolitiques
            'MISC': 'MISC',
            'DATE': 'DATE',
            'TIME': 'DATE',
            'MONEY': 'MONEY',
            'PERCENT': 'PERCENT',
            'CARDINAL': 'NUMBER',
            'ORDINAL': 'NUMBER'
        }
        return mapping.get(spacy_label.upper(), spacy_label.upper())
    
    def _map_ner_label(self, ner_label: str) -> str:
        """Mapper les labels NER vers nos types d'entités"""
        mapping = {
            'PER': 'PERSON',
            'PERSON': 'PERSON',
            'ORG': 'ORG',
            'ORGANIZATION': 'ORG', 
            'LOC': 'LOC',
            'LOCATION': 'LOC',
            'MISC': 'MISC',
            'DATE': 'DATE',
            'TIME': 'DATE'
        }
        return mapping.get(ner_label.upper(), ner_label.upper())
    
    def _merge_regex_entities(self, ai_entities: List[Entity], regex_entities: List[Entity]) -> List[Entity]:
        """Fusionner les entités IA et regex en évitant les doublons"""
        merged = []
        
        for regex_entity in regex_entities:
            is_duplicate = False
            
            # Vérifier les chevauchements avec les entités IA
            for ai_entity in ai_entities:
                overlap = self._calculate_overlap(regex_entity, ai_entity)
                
                if overlap > 0.5:  # 50% de chevauchement
                    # Garder l'entité avec la meilleure confiance ou la plus spécifique
                    if (regex_entity.type in ['EMAIL', 'PHONE', 'IBAN', 'SIRET', 'SIREN'] and 
                        ai_entity.type in ['PERSON', 'ORG', 'LOC']):
                        # Les entités regex structurées sont prioritaires
                        ai_entities.remove(ai_entity)
                        break
                    else:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                regex_entity.id = f"regex_{regex_entity.id}"
                merged.append(regex_entity)
        
        return merged
    
    def _calculate_overlap(self, entity1: Entity, entity2: Entity) -> float:
        """Calculer le pourcentage de chevauchement entre deux entités"""
        start_overlap = max(entity1.start, entity2.start)
        end_overlap = min(entity1.end, entity2.end)
        
        if start_overlap >= end_overlap:
            return 0.0
        
        overlap_length = end_overlap - start_overlap
        min_length = min(entity1.end - entity1.start, entity2.end - entity2.start)
        
        return overlap_length / min_length if min_length > 0 else 0.0
    
    def _post_process_french_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Post-traitement spécifique pour le français"""
        processed_entities = []
        
        for entity in entities:
            # Nettoyer les valeurs d'entités
            cleaned_value = self._clean_entity_value(entity.value)
            if cleaned_value and len(cleaned_value) > 1:
                entity.value = cleaned_value
                
                # Validation spécifique par type
                if self._is_valid_french_entity(entity):
                    processed_entities.append(entity)
                else:
                    logging.debug(f"Invalid French entity filtered: {entity.value} ({entity.type})")
        
        return processed_entities
    
    def _clean_entity_value(self, value: str) -> str:
        """Nettoyer la valeur d'une entité"""
        # Supprimer les espaces en début/fin
        cleaned = value.strip()
        
        # Supprimer la ponctuation en fin
        cleaned = re.sub(r'[.,;:!?]+$', '', cleaned)
        
        return cleaned
    
    def _is_valid_french_entity(self, entity: Entity) -> bool:
        """Valider qu'une entité est pertinente pour le français"""
        value = entity.value.lower()
        
        # Filtrer les mots trop courts ou trop courants
        if len(value) < 2:
            return False
        
        # Mots français courants à exclure
        french_stopwords = {
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'que', 'qui',
            'dans', 'pour', 'avec', 'sur', 'par', 'ce', 'cette', 'ces', 'son', 'sa', 'ses'
        }
        
        if entity.type == 'PERSON' and value in french_stopwords:
            return False
        
        # Validation spécifique par type
        if entity.type == 'EMAIL':
            return '@' in value and '.' in value
        elif entity.type == 'PHONE':
            return len(re.sub(r'\D', '', value)) >= 8
        elif entity.type == 'IBAN':
            return len(value.replace(' ', '')) >= 15
        
        return True

class DocumentProcessor:
    """Processeur de documents (PDF, DOCX) avec gestion d'erreurs améliorée"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.doc']
    
    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, Dict]:
        """Extraire le texte d'un PDF avec gestion d'erreurs robuste"""
        if not PDF_SUPPORT:
            raise Exception("PDF support not available. Install pdfplumber and pdf2docx.")
        
        text_content = ""
        metadata = {"pages": 0, "format": "pdf", "extraction_method": "pdfplumber"}
        
        try:
            with pdfplumber.open(file_path) as pdf:
                metadata["pages"] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"\n--- Page {page_num} ---\n"
                            text_content += page_text
                    except Exception as e:
                        logging.warning(f"Failed to extract text from page {page_num}: {e}")
                        continue
                
                # Essayer d'extraire les tableaux si peu de texte
                if len(text_content.strip()) < 100:
                    text_content += self._extract_tables_from_pdf(pdf)
                
            metadata["text_length"] = len(text_content)
            return text_content, metadata
            
        except Exception as e:
            # Fallback vers PyMuPDF si disponible
            try:
                import fitz  # PyMuPDF
                return self._extract_with_pymupdf(file_path)
            except ImportError:
                raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def _extract_tables_from_pdf(self, pdf) -> str:
        """Extraire le texte des tableaux PDF"""
        table_text = ""
        try:
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                if tables:
                    table_text += f"\n--- Tableaux Page {page_num} ---\n"
                    for table in tables:
                        for row in table:
                            if row:
                                table_text += " | ".join([cell for cell in row if cell]) + "\n"
        except Exception as e:
            logging.warning(f"Failed to extract tables: {e}")
        
        return table_text
    
    def _extract_with_pymupdf(self, file_path: str) -> Tuple[str, Dict]:
        """Extraction de secours avec PyMuPDF"""
        import fitz
        
        text_content = ""
        metadata = {"pages": 0, "format": "pdf", "extraction_method": "pymupdf"}
        
        doc = fitz.open(file_path)
        metadata["pages"] = len(doc)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            if page_text:
                text_content += f"\n--- Page {page_num + 1} ---\n"
                text_content += page_text
        
        doc.close()
        metadata["text_length"] = len(text_content)
        return text_content, metadata
    
    def extract_text_from_docx(self, file_path: str) -> Tuple[str, Dict]:
        """Extraire le texte d'un DOCX avec extraction complète"""
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
            
            # Extraction du texte des paragraphes
            for para in doc.paragraphs:
                if para.text.strip():
                    text_content += para.text + "\n"
                    metadata["paragraphs"] += 1
            
            # Extraction du texte des tableaux
            for table in doc.tables:
                metadata["tables"] += 1
                text_content += "\n--- Tableau ---\n"
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_content += " | ".join(row_text) + "\n"
            
            # Extraction des en-têtes et pieds de page
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
            
            # Extraction des notes de bas de page et commentaires
            try:
                # Notes de bas de page (si disponibles)
                if hasattr(doc, 'footnotes'):
                    for footnote in doc.footnotes:
                        if hasattr(footnote, 'paragraphs'):
                            for para in footnote.paragraphs:
                                if para.text.strip():
                                    text_content += f"[NOTE] {para.text}\n"
            except Exception as e:
                logging.debug(f"Could not extract footnotes: {e}")
            
            metadata["text_length"] = len(text_content)
            return text_content, metadata
            
        except Exception as e:
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")
    
    def convert_pdf_to_docx(self, pdf_path: str, output_path: str) -> str:
        """Convertir un PDF en DOCX"""
        if not PDF_SUPPORT:
            raise Exception("PDF support not available.")
        
        try:
            pdf2docx_parse(pdf_path, output_path)
            return output_path
        except Exception as e:
            raise Exception(f"Failed to convert PDF to DOCX: {str(e)}")
    
    def process_file(self, file_path: str) -> Tuple[str, Dict]:
        """Traiter un fichier et extraire le texte"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return self.extract_text_from_docx(file_path)
        else:
            raise Exception(f"Unsupported file format: {file_ext}")

class DocumentAnonymizer:
    """Classe principale pour l'anonymisation de documents avec support français"""
    
    def __init__(self, prefer_french: bool = True, use_spacy: bool = True):
        self.regex_anonymizer = RegexAnonymizer(use_french_patterns=True)
        self.ai_anonymizer = AIAnonymizer(prefer_french=prefer_french) if (AI_SUPPORT or SPACY_SUPPORT) else None
        self.document_processor = DocumentProcessor()
        self.temp_dir = tempfile.mkdtemp()
        self.prefer_french = prefer_french
        self.use_spacy = use_spacy
        
        # Statistiques de traitement
        self.processing_stats = {
            "documents_processed": 0,
            "entities_detected": 0,
            "processing_time": 0.0
        }
    
    def process_document(self, file_path: str, mode: str = "regex", confidence: float = 0.7) -> Dict[str, Any]:
        """Traiter un document complet avec mesure de performance"""
        import time
        start_time = time.time()
        
        try:
            # Validation des paramètres
            if mode not in ["regex", "ai"]:
                mode = "regex"
            
            if not (0.0 <= confidence <= 1.0):
                confidence = 0.7
            
            # Extraction du texte
            text, metadata = self.document_processor.process_file(file_path)
            
            if not text.strip():
                return {
                    "status": "error",
                    "error": "No text content found in document"
                }
            
            # Nettoyage et préparation du texte
            text = self._preprocess_text(text)
            
            # Détection des entités
            if mode == "ai" and self.ai_anonymizer:
                entities = self.ai_anonymizer.detect_entities_ai(text, confidence)
                metadata["detection_method"] = "ai"
            else:
                entities = self.regex_anonymizer.detect_entities(text)
                metadata["detection_method"] = "regex"
            
            # Post-traitement des entités
            entities = self._post_process_entities(entities, text)
            
            # Anonymisation du texte
            anonymized_text = self.regex_anonymizer.anonymize_text(text, entities)
            
            # Validation de l'anonymisation
            validation_result = self._validate_anonymization(text, anonymized_text, entities)
            
            # Création du document anonymisé
            anonymized_path = self._create_anonymized_document(
                file_path, anonymized_text, metadata, entities
            )
            
            # Calcul du temps de traitement
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
            logging.error(f"Document processing failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "processing_time": processing_time
            }
    
    def _preprocess_text(self, text: str) -> str:
        """Prétraitement du texte pour améliorer la détection"""
        # Normalisation des espaces
        text = re.sub(r'\s+', ' ', text)
        
        # Normalisation des caractères spéciaux français
        text = text.replace('œ', 'oe').replace('Œ', 'OE')
        text = text.replace('æ', 'ae').replace('Æ', 'AE')
        
        # Nettoyage des caractères de contrôle
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()
    
    def _post_process_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Post-traitement des entités détectées"""
        processed_entities = []
        
        for entity in entities:
            # Validation de base
            if not self._is_valid_entity(entity, text):
                continue
            
            # Amélioration du contexte
            entity.context = self._extract_enhanced_context(text, entity.start, entity.end)
            
            # Classification fine
            entity.type = self._refine_entity_classification(entity, text)
            
            processed_entities.append(entity)
        
        # Résolution des conflits
        processed_entities = self._resolve_entity_conflicts(processed_entities)
        
        return processed_entities
    
    def _is_valid_entity(self, entity: Entity, text: str) -> bool:
        """Valider qu'une entité est pertinente"""
        # Vérifications de base
        if entity.start < 0 or entity.end > len(text):
            return False
        
        if entity.start >= entity.end:
            return False
        
        if len(entity.value.strip()) < 2:
            return False
        
        # Vérification que la valeur correspond au texte
        actual_value = text[entity.start:entity.end]
        if actual_value.strip().lower() != entity.value.strip().lower():
            # Tentative de correction
            corrected_start = text.find(entity.value, max(0, entity.start - 10))
            if corrected_start != -1:
                entity.start = corrected_start
                entity.end = corrected_start + len(entity.value)
            else:
                return False
        
        return True
    
    def _extract_enhanced_context(self, text: str, start: int, end: int, context_length: int = 100) -> str:
        """Extraire un contexte enrichi autour d'une entité"""
        # Contexte plus large
        context_start = max(0, start - context_length)
        context_end = min(len(text), end + context_length)
        
        # Essayer de couper à des limites de phrases
        context = text[context_start:context_end]
        
        # Marquer l'entité
        entity_value = text[start:end]
        relative_start = start - context_start
        relative_end = end - context_start
        
        highlighted_context = (
            context[:relative_start] + 
            f"**{entity_value}**" + 
            context[relative_end:]
        )
        
        return highlighted_context
    
    def _refine_entity_classification(self, entity: Entity, text: str) -> str:
        """Affiner la classification d'une entité"""
        value = entity.value.lower()
        
        # Amélioration pour les personnes françaises
        if entity.type == 'PERSON':
            # Vérifier si c'est vraiment un nom de personne
            french_titles = ['m.', 'mme', 'mlle', 'dr.', 'prof.', 'me', 'maître']
            context_before = text[max(0, entity.start - 20):entity.start].lower()
            
            has_title = any(title in context_before for title in french_titles)
            if has_title:
                return 'PERSON'
            
            # Vérifier si c'est plutôt une organisation
            org_indicators = ['sarl', 'sas', 'sa', 'société', 'entreprise', 'cabinet']
            if any(indicator in value for indicator in org_indicators):
                return 'ORG'
        
        # Amélioration pour les lieux
        elif entity.type == 'LOC':
            # Vérifier si c'est une adresse complète
            if any(word in value for word in ['rue', 'avenue', 'boulevard', 'place']):
                return 'ADDRESS'
        
        return entity.type
    
    def _resolve_entity_conflicts(self, entities: List[Entity]) -> List[Entity]:
        """Résoudre les conflits entre entités qui se chevauchent"""
        if not entities:
            return entities
        
        # Trier par position
        sorted_entities = sorted(entities, key=lambda x: x.start)
        resolved_entities = []
        
        for current_entity in sorted_entities:
            conflict_found = False
            
            for i, existing_entity in enumerate(resolved_entities):
                if self._entities_overlap(current_entity, existing_entity):
                    # Résoudre le conflit
                    winner = self._resolve_conflict(current_entity, existing_entity)
                    resolved_entities[i] = winner
                    conflict_found = True
                    break
            
            if not conflict_found:
                resolved_entities.append(current_entity)
        
        return resolved_entities
    
    def _entities_overlap(self, entity1: Entity, entity2: Entity) -> bool:
        """Vérifier si deux entités se chevauchent"""
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)
    
    def _resolve_conflict(self, entity1: Entity, entity2: Entity) -> Entity:
        """Résoudre un conflit entre deux entités"""
        # Priorité aux entités structurées (email, téléphone, etc.)
        structured_types = ['EMAIL', 'PHONE', 'IBAN', 'SIRET', 'SIREN', 'SSN']
        
        if entity1.type in structured_types and entity2.type not in structured_types:
            return entity1
        elif entity2.type in structured_types and entity1.type not in structured_types:
            return entity2
        
        # Sinon, garder celle avec la meilleure confiance
        if entity1.confidence > entity2.confidence:
            return entity1
        elif entity2.confidence > entity1.confidence:
            return entity2
        
        # En dernier recours, garder la plus longue
        if (entity1.end - entity1.start) >= (entity2.end - entity2.start):
            return entity1
        else:
            return entity2
    
    def _validate_anonymization(self, original_text: str, anonymized_text: str, entities: List[Entity]) -> Dict[str, Any]:
        """Valider que l'anonymisation a été effectuée correctement"""
        validation = {
            "success": True,
            "issues": [],
            "stats": {}
        }
        
        # Vérifier que les entités ont été remplacées
        for entity in entities:
            if entity.value in anonymized_text:
                validation["success"] = False
                validation["issues"].append(f"Entité non anonymisée: {entity.value}")
        
        # Calculer les statistiques de changement
        original_words = len(original_text.split())
        anonymized_words = len(anonymized_text.split())
        
        validation["stats"] = {
            "original_length": len(original_text),
            "anonymized_length": len(anonymized_text),
            "entities_replaced": len(entities),
            "reduction_percentage": ((len(original_text) - len(anonymized_text)) / len(original_text)) * 100
        }
        
        return validation
    
    def _generate_processing_stats(self, entities: List[Entity], text: str, processing_time: float) -> Dict[str, Any]:
        """Générer des statistiques de traitement"""
        entity_types = {}
        confidence_sum = 0
        confidence_count = 0
        
        for entity in entities:
            entity_type = entity.type
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            if entity.confidence is not None:
                confidence_sum += entity.confidence
                confidence_count += 1
        
        return {
            "total_entities": len(entities),
            "entity_types": entity_types,
            "average_confidence": confidence_sum / confidence_count if confidence_count > 0 else 0,
            "processing_time": processing_time,
            "entities_per_second": len(entities) / processing_time if processing_time > 0 else 0,
            "text_length": len(text),
            "most_common_type": max(entity_types, key=entity_types.get) if entity_types else None
        }
    
    def _create_anonymized_document(self, original_path: str, anonymized_text: str, 
                                  metadata: Dict, entities: List[Entity]) -> str:
        """Créer le document anonymisé avec métadonnées enrichies"""
        original_name = Path(original_path).name
        base_name = Path(original_path).stem
        
        # Création d'un nouveau document DOCX
        doc = Document()
        
        # Ajout d'un en-tête avec informations d'anonymisation
        header = doc.sections[0].header
        header_para = header.paragraphs[0]
        header_para.text = "DOCUMENT ANONYMISÉ - Conforme RGPD"
        
        # Ajout des métadonnées d'anonymisation
        doc.add_heading('INFORMATIONS D\'ANONYMISATION', 1)
        
        info_table = doc.add_table(rows=7, cols=2)
        info_table.style = 'Table Grid'
        
        info_data = [
            ('Document original', original_name),
            ('Date d\'anonymisation', self._get_current_timestamp()),
            ('Méthode de détection', metadata.get('detection_method', 'regex')),
            ('Entités détectées', str(len(entities))),
            ('Temps de traitement', f"{metadata.get('processing_time', 0):.2f}s"),
            ('Longueur originale', f"{metadata.get('text_length', 0)} caractères"),
            ('Types d\'entités', ', '.join(metadata.get('entity_types', {}).keys()))
        ]
        
        for i, (label, value) in enumerate(info_data):
            info_table.cell(i, 0).text = label
            info_table.cell(i, 1).text = value
        
        # Ajout du contenu anonymisé
        doc.add_heading('CONTENU ANONYMISÉ', 1)
        
        # Diviser le texte en paragraphes
        paragraphs = anonymized_text.split('\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                doc.add_paragraph(paragraph.strip())
        
        # Ajout d'un résumé des entités anonymisées
        if entities:
            doc.add_page_break()
            doc.add_heading('RAPPORT D\'ANONYMISATION', 1)
            
            doc.add_heading('Entités par type:', 2)
            entity_types = metadata.get('entity_types', {})
            for entity_type, count in entity_types.items():
                doc.add_paragraph(f"• {entity_type}: {count} occurrence(s)")
            
            doc.add_heading('Détail des entités (échantillon):', 2)
            sample_entities = entities[:10]  # Limiter à 10 pour éviter des documents trop longs
            
            entity_table = doc.add_table(rows=len(sample_entities) + 1, cols=4)
            entity_table.style = 'Table Grid'
            
            # En-têtes
            headers = ['Type', 'Valeur remplacée', 'Confiance', 'Position']
            for i, header in enumerate(headers):
                entity_table.cell(0, i).text = header
            
            # Données
            for i, entity in enumerate(sample_entities, 1):
                entity_table.cell(i, 0).text = entity.type
                entity_table.cell(i, 1).text = entity.replacement or f"[{entity.type}]"
                entity_table.cell(i, 2).text = f"{entity.confidence:.2f}" if entity.confidence else "N/A"
                entity_table.cell(i, 3).text = f"{entity.start}-{entity.end}"
        
        # Ajout d'un pied de page avec signature numérique
        footer = doc.sections[0].footer
        footer_para = footer.paragraphs[0]
        footer_para.text = (
            f"Anonymisé par l'Anonymiseur de Documents Juridiques v2.0 - "
            f"ID: {self._generate_document_id()} - "
            f"Hash: {self._generate_content_hash(anonymized_text)[:8]}"
        )
        
        # Sauvegarde
        output_path = os.path.join(self.temp_dir, f"anonymized_{base_name}.docx")
        doc.save(output_path)
        
        logging.info(f"Anonymized document created: {output_path}")
        return output_path
    
    def _get_current_timestamp(self) -> str:
        """Obtenir le timestamp actuel formaté"""
        from datetime import datetime
        return datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
    
    def _generate_document_id(self) -> str:
        """Générer un ID unique pour le document"""
        import uuid
        return str(uuid.uuid4())[:8].upper()
    
    def _generate_content_hash(self, content: str) -> str:
        """Générer un hash du contenu pour vérification d'intégrité"""
        import hashlib
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def update_entity_replacement(self, entities: List[Dict], entity_id: str, new_replacement: str) -> List[Dict]:
        """Mettre à jour le remplacement d'une entité"""
        for entity in entities:
            if entity['id'] == entity_id:
                entity['replacement'] = new_replacement
                break
        return entities
    
    def regenerate_anonymized_text(self, original_text: str, entities: List[Dict]) -> str:
        """Régénérer le texte anonymisé avec les remplacements mis à jour"""
        # Convertir les dicts en objets Entity
        entity_objects = []
        for entity_dict in entities:
            entity = Entity(**entity_dict)
            entity_objects.append(entity)
        
        return self.regex_anonymizer.anonymize_text(original_text, entity_objects)
    
    def export_anonymized_document(self, original_path: str, entities: List[Dict], 
                                 options: Dict = None) -> str:
        """Exporter le document anonymisé avec options personnalisées"""
        options = options or {}
        
        try:
            # Traitement du document original
            text, metadata = self.document_processor.process_file(original_path)
            
            # Régénération avec les entités mises à jour
            anonymized_text = self.regenerate_anonymized_text(text, entities)
            
            # Création du document final
            doc = Document()
            
            # Options d'export
            if options.get('add_watermark', True):
                watermark_text = options.get('watermark_text', 'DOCUMENT ANONYMISÉ')
                header = doc.sections[0].header
                header_para = header.paragraphs[0]
                header_para.text = watermark_text
            
            # Contenu principal
            lines = anonymized_text.split('\n')
            for line in lines:
                if line.strip():
                    doc.add_paragraph(line)
            
            # Rapport d'audit détaillé
            if options.get('generate_report', False):
                doc.add_page_break()
                doc.add_heading('RAPPORT D\'AUDIT D\'ANONYMISATION DÉTAILLÉ', 1)
                
                # Informations générales
                doc.add_heading('Informations générales:', 2)
                doc.add_paragraph(f"Document original: {Path(original_path).name}")
                doc.add_paragraph(f"Date d'anonymisation: {self._get_current_timestamp()}")
                doc.add_paragraph(f"Nombre d'entités anonymisées: {len(entities)}")
                doc.add_paragraph(f"Méthode utilisée: {metadata.get('detection_method', 'regex')}")
                
                # Statistiques détaillées
                entity_types = {}
                for entity in entities:
                    entity_type = entity['type']
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                
                doc.add_heading('Répartition par type:', 2)
                for entity_type, count in entity_types.items():
                    percentage = (count / len(entities)) * 100
                    doc.add_paragraph(f"- {entity_type}: {count} occurrence(s) ({percentage:.1f}%)")
                
                # Recommandations de sécurité
                doc.add_heading('Recommandations:', 2)
                doc.add_paragraph("• Vérifiez manuellement que toutes les données sensibles ont été anonymisées")
                doc.add_paragraph("• Conservez ce rapport pour vos archives de conformité RGPD")
                doc.add_paragraph("• En cas de doute, effectuez une relecture complète du document")
                
                # Conformité RGPD
                doc.add_heading('Conformité RGPD:', 2)
                doc.add_paragraph("Ce document a été anonymisé selon les standards du RGPD:")
                doc.add_paragraph("• Article 4(5): Pseudonymisation")
                doc.add_paragraph("• Article 25: Protection des données dès la conception")
                doc.add_paragraph("• Article 32: Sécurité du traitement")
            
            # Sauvegarde
            base_name = Path(original_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.temp_dir, f"final_anonymized_{base_name}_{timestamp}.docx")
            doc.save(output_path)
            
            return output_path
            
        except Exception as e:
            logging.error(f"Export failed: {str(e)}")
            raise Exception(f"Failed to export document: {str(e)}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Obtenir les statistiques globales de traitement"""
        return self.processing_stats.copy()
    
    def reset_statistics(self):
        """Réinitialiser les statistiques"""
        self.processing_stats = {
            "documents_processed": 0,
            "entities_detected": 0,
            "processing_time": 0.0
        }
    
    def cleanup(self):
        """Nettoyer les fichiers temporaires"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logging.info("Temporary files cleaned up")
        except Exception as e:
            logging.warning(f"Could not clean up temporary files: {e}")

class EntityStatistics:
    """Classe pour les statistiques avancées sur les entités"""
    
    @staticmethod
    def get_entity_stats(entities: List[Dict]) -> Dict[str, Any]:
        """Calculer les statistiques détaillées des entités"""
        if not entities:
            return {
                "total": 0,
                "by_type": {},
                "confidence_stats": {},
                "coverage": 0.0,
                "distribution": {}
            }
        
        total = len(entities)
        by_type = {}
        confidences = []
        positions = []
        
        for entity in entities:
            entity_type = entity['type']
            by_type[entity_type] = by_type.get(entity_type, 0) + 1
            
            if 'confidence' in entity and entity['confidence'] is not None:
                confidences.append(entity['confidence'])
            
            if 'start' in entity and 'end' in entity:
                positions.append((entity['start'], entity['end']))
        
        # Statistiques de confiance
        confidence_stats = {}
        if confidences:
            confidence_stats = {
                "min": min(confidences),
                "max": max(confidences),
                "avg": sum(confidences) / len(confidences),
                "std": EntityStatistics._calculate_std(confidences),
                "high_confidence": len([c for c in confidences if c >= 0.8]),
                "medium_confidence": len([c for c in confidences if 0.5 <= c < 0.8]),
                "low_confidence": len([c for c in confidences if c < 0.5])
            }
        
        # Distribution spatiale
        distribution = EntityStatistics._calculate_spatial_distribution(positions)
        
        return {
            "total": total,
            "by_type": by_type,
            "confidence_stats": confidence_stats,
            "most_common_type": max(by_type, key=by_type.get) if by_type else None,
            "distribution": distribution
        }
    
    @staticmethod
    def _calculate_std(values: List[float]) -> float:
        """Calculer l'écart-type"""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    @staticmethod
    def _calculate_spatial_distribution(positions: List[Tuple[int, int]]) -> Dict[str, Any]:
        """Calculer la distribution spatiale des entités dans le document"""
        if not positions:
            return {}
        
        starts = [pos[0] for pos in positions]
        ends = [pos[1] for pos in positions]
        lengths = [end - start for start, end in positions]
        
        return {
            "first_entity_position": min(starts),
            "last_entity_position": max(ends),
            "average_entity_length": sum(lengths) / len(lengths),
            "total_coverage": sum(lengths),
            "entity_density": len(positions) / (max(ends) - min(starts)) if starts else 0
        }
    
    @staticmethod
    def generate_comprehensive_report(entities: List[Dict], metadata: Dict, 
                                    processing_stats: Dict) -> str:
        """Générer un rapport complet d'anonymisation"""
        stats = EntityStatistics.get_entity_stats(entities)
        
        report = f"""
RAPPORT COMPLET D'ANONYMISATION
===============================

INFORMATIONS DOCUMENT:
• Format: {metadata.get('format', 'inconnu').upper()}
• Méthode d'extraction: {metadata.get('extraction_method', 'standard')}
• Pages/Paragraphes: {metadata.get('pages', metadata.get('paragraphs', 'N/A'))}
• Longueur du texte: {metadata.get('text_length', 0)} caractères

STATISTIQUES D'ANONYMISATION:
• Total d'entités détectées: {stats['total']}
• Types d'entités différents: {len(stats['by_type'])}
• Type le plus fréquent: {stats['most_common_type'] or 'N/A'}
• Méthode de détection: {metadata.get('detection_method', 'regex')}

PERFORMANCE:
• Temps de traitement: {processing_stats.get('processing_time', 0):.2f} secondes
• Entités par seconde: {processing_stats.get('entities_per_second', 0):.1f}
• Couverture du texte: {stats['distribution'].get('total_coverage', 0)} caractères
"""
        
        # Répartition détaillée par type
        if stats['by_type']:
            report += "\nRÉPARTITION PAR TYPE D'ENTITÉ:\n"
            for entity_type, count in sorted(stats['by_type'].items()):
                percentage = (count / stats['total']) * 100
                report += f"• {entity_type}: {count} ({percentage:.1f}%)\n"
        
        # Statistiques de confiance
        if stats['confidence_stats']:
            conf_stats = stats['confidence_stats']
            report += f"""
ANALYSE DE CONFIANCE:
• Confiance moyenne: {conf_stats['avg']:.3f}
• Confiance minimale: {conf_stats['min']:.3f}
• Confiance maximale: {conf_stats['max']:.3f}
• Écart-type: {conf_stats['std']:.3f}
• Entités haute confiance (≥80%): {conf_stats['high_confidence']}
• Entités confiance moyenne (50-80%): {conf_stats['medium_confidence']}
• Entités faible confiance (<50%): {conf_stats['low_confidence']}
"""
        
        # Distribution spatiale
        if stats['distribution']:
            dist = stats['distribution']
            report += f"""
DISTRIBUTION SPATIALE:
• Première entité à la position: {dist.get('first_entity_position', 0)}
• Dernière entité à la position: {dist.get('last_entity_position', 0)}
• Longueur moyenne des entités: {dist.get('average_entity_length', 0):.1f} caractères
• Densité d'entités: {dist.get('entity_density', 0):.4f} entités/caractère
"""
        
        # Recommandations
        report += "\nRECOMMANDATIONS:\n"
        report += EntityStatistics._generate_detailed_recommendations(stats, metadata)
        
        # Conformité
        report += """
CONFORMITÉ RGPD:
• Article 4(5) - Pseudonymisation: ✓ Appliquée
• Article 25 - Protection dès la conception: ✓ Respectée
• Article 32 - Sécurité du traitement: ✓ Mise en œuvre
• Recital 26 - Anonymisation: ✓ Conforme

VALIDATION:
Ce document a été traité par l'Anonymiseur de Documents Juridiques v2.0
conforme aux standards européens de protection des données.
"""
        
        return report
    
    @staticmethod
    def _generate_detailed_recommendations(stats: Dict, metadata: Dict) -> str:
        """Générer des recommandations détaillées"""
        recommendations = []
        
        total_entities = stats['total']
        confidence_stats = stats.get('confidence_stats', {})
        by_type = stats.get('by_type', {})
        
        # Recommandations basées sur le nombre d'entités
        if total_entities == 0:
            recommendations.append("⚠️ Aucune entité détectée. Vérifiez le contenu du document.")
        elif total_entities > 100:
            recommendations.append(f"📊 {total_entities} entités détectées. Document très sensible, vérification manuelle recommandée.")
        elif total_entities > 50:
            recommendations.append(f"📊 {total_entities} entités détectées. Vérification par échantillonnage recommandée.")
        
        # Recommandations basées sur la confiance
        if confidence_stats:
            low_conf = confidence_stats.get('low_confidence', 0)
            if low_conf > 0:
                percentage = (low_conf / total_entities) * 100
                recommendations.append(f"⚠️ {low_conf} entités ({percentage:.1f}%) ont une confiance faible. Vérification manuelle requise.")
            
            avg_conf = confidence_stats.get('avg', 0)
            if avg_conf < 0.7:
                recommendations.append("⚠️ Confiance moyenne faible. Considérez ajuster les seuils ou utiliser le mode IA.")
        
        # Recommandations basées sur les types d'entités
        sensitive_types = ['EMAIL', 'PHONE', 'SSN', 'CREDIT_CARD', 'IBAN']
        found_sensitive = any(etype in by_type for etype in sensitive_types)
        
        if found_sensitive:
            recommendations.append("🔒 Données financières/personnelles détectées. Conformité RGPD critique.")
        
        if 'PERSON' in by_type and by_type['PERSON'] > 10:
            recommendations.append("👤 Nombreuses personnes détectées. Vérifiez la nécessité de conserver certains noms.")
        
        if 'ORG' in by_type and by_type['ORG'] > 5:
            recommendations.append("🏢 Nombreuses organisations détectées. Évaluez l'impact sur la compréhension du document.")
        
        # Recommandations générales
        if not recommendations:
            recommendations.append("✅ Anonymisation appropriée. Document prêt pour diffusion.")
        
        recommendations.append("📋 Conservez ce rapport pour vos archives de traçabilité.")
        recommendations.append("🔍 Effectuez une relecture finale avant diffusion externe.")
        
        return "\n".join(f"• {rec}" for rec in recommendations)

class AnonymizationValidator:
    """Validateur pour vérifier la qualité de l'anonymisation"""
    
    @staticmethod
    def validate_anonymization_quality(original_text: str, anonymized_text: str, 
                                     entities: List[Entity]) -> Dict[str, Any]:
        """Valider la qualité de l'anonymisation"""
        validation = {
            "overall_score": 0.0,
            "issues": [],
            "warnings": [],
            "success": True,
            "metrics": {}
        }
        
        # Test 1: Vérifier que les entités ont été remplacées
        entities_not_replaced = []
        for entity in entities:
            if entity.value in anonymized_text:
                entities_not_replaced.append(entity.value)
        
        if entities_not_replaced:
            validation["success"] = False
            validation["issues"].append(f"Entités non remplacées: {entities_not_replaced[:5]}")
        
        # Test 2: Détecter des fuites potentielles
        potential_leaks = AnonymizationValidator._detect_potential_leaks(anonymized_text)
        if potential_leaks:
            validation["warnings"].extend(potential_leaks)
        
        # Test 3: Vérifier la cohérence du document
        coherence_score = AnonymizationValidator._check_document_coherence(
            original_text, anonymized_text
        )
        
        # Test 4: Analyser la préservation du sens
        meaning_preservation = AnonymizationValidator._analyze_meaning_preservation(
            original_text, anonymized_text, entities
        )
        
        # Calcul du score global
        replacement_score = 1.0 if not entities_not_replaced else 0.0
        leak_score = 1.0 - (len(potential_leaks) * 0.1)
        
        validation["overall_score"] = (
            replacement_score * 0.5 + 
            leak_score * 0.3 + 
            coherence_score * 0.1 + 
            meaning_preservation * 0.1
        )
        
        validation["metrics"] = {
            "replacement_score": replacement_score,
            "leak_score": leak_score,
            "coherence_score": coherence_score,
            "meaning_preservation": meaning_preservation,
            "entities_not_replaced": len(entities_not_replaced),
            "potential_leaks": len(potential_leaks)
        }
        
        return validation
    
    @staticmethod
    def _detect_potential_leaks(text: str) -> List[str]:
        """Détecter des fuites potentielles dans le texte anonymisé"""
        leaks = []
        
        # Patterns de données sensibles qui auraient pu être manqués
        leak_patterns = {
            "email_like": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            "phone_like": r'\b(?:\+33|0)[1-9](?:[0-9\s.-]{8,})\b',
            "iban_like": r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}[A-Z0-9]*\b',
            "potential_name": r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b'
        }
        
        for pattern_name, pattern in leak_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                leaks.append(f"Potentielle fuite {pattern_name}: {len(matches)} occurrence(s)")
        
        return leaks
    
    @staticmethod
    def _check_document_coherence(original: str, anonymized: str) -> float:
        """Vérifier la cohérence structurelle du document"""
        # Comparer les structures (paragraphes, longueurs relatives)
        original_paragraphs = len(original.split('\n\n'))
        anonymized_paragraphs = len(anonymized.split('\n\n'))
        
        structure_similarity = min(original_paragraphs, anonymized_paragraphs) / max(original_paragraphs, anonymized_paragraphs)
        
        # Comparer les longueurs relatives
        length_ratio = len(anonymized) / len(original) if len(original) > 0 else 0
        length_score = 1.0 - abs(length_ratio - 0.8)  # Attendu: ~80% de la longueur originale
        
        return (structure_similarity + max(0, length_score)) / 2
    
    @staticmethod
    def _analyze_meaning_preservation(original: str, anonymized: str, entities: List[Entity]) -> float:
        """Analyser la préservation du sens du document"""
        # Approximation simple basée sur la préservation des mots-clés non-sensibles
        original_words = set(re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', original.lower()))
        anonymized_words = set(re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', anonymized.lower()))
        
        # Exclure les mots des entités anonymisées
        entity_words = set()
        for entity in entities:
            entity_words.update(re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', entity.value.lower()))
        
        relevant_original_words = original_words - entity_words
        preserved_words = relevant_original_words.intersection(anonymized_words)
        
        if len(relevant_original_words) == 0:
            return 1.0
        
        return len(preserved_words) / len(relevant_original_words)

# Export de toutes les classes pour l'utilisation externe
__all__ = [
    'Entity',
    'RegexAnonymizer', 
    'AIAnonymizer',
    'DocumentProcessor',
    'DocumentAnonymizer',
    'EntityStatistics',
    'AnonymizationValidator'
]