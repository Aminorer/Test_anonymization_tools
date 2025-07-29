import spacy
import re
from typing import List, Dict, Set, Tuple, Optional
from app.models.entities import (
    Entity,
    EntityTypeEnum,
    ENTITY_TYPES,
    STRUCTURED_ENTITY_TYPES,
    SPACY_ENTITY_TYPES
)
from app.core.config import settings
import logging
from dataclasses import dataclass
import hashlib
import time

logger = logging.getLogger(__name__)

@dataclass
class EntityCandidate:
    text: str
    start: int
    end: int
    entity_type: str
    confidence: float
    source: str
    context: str = ""

class SimplifiedNLPAnalyzer:
    def __init__(self):
        # 1. REGEX : Pour données structurées (téléphone, SIRET, email, etc.)
        self._compiled_patterns = {}
        self._compile_structured_patterns()
        
        # 2. SpaCy NER : Pour noms et organisations (mode approfondi seulement)
        self.spacy_nlp = None
        self._load_spacy_model()
        
        logger.info("🧠 NLP Analyzer simplifié initialisé (SANS LLM)")
        
    def _compile_structured_patterns(self):
        """Compile UNIQUEMENT les patterns pour données structurées"""
        logger.info("🔧 Compilation patterns STRUCTURÉS...")
        
        for entity_type in STRUCTURED_ENTITY_TYPES:
            config = STRUCTURED_ENTITY_TYPES[entity_type]
            patterns = config.get('patterns', [])
            self._compiled_patterns[entity_type] = []
            
            for pattern in patterns:
                try:
                    compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                    self._compiled_patterns[entity_type].append(compiled_pattern)
                except re.error as e:
                    logger.warning(f"Pattern invalide pour {entity_type}: {e}")
        
        logger.info(f"✅ {sum(len(patterns) for patterns in self._compiled_patterns.values())} patterns structurés compilés")
    
    def _load_spacy_model(self):
        """Charge le meilleur modèle SpaCy français pour NER"""
        models_to_try = [
            "fr_core_news_lg",    # Le plus précis pour NER
            "fr_core_news_md",    # Bon compromis
            "fr_core_news_sm"     # Léger mais moins précis
        ]
        
        for model_name in models_to_try:
            try:
                self.spacy_nlp = spacy.load(model_name)
                logger.info(f"✅ SpaCy NER chargé: {model_name}")
                return
            except OSError:
                continue
        
        logger.warning("⚠️ Aucun modèle SpaCy français trouvé - Mode approfondi désactivé")
        self.spacy_nlp = None
    
    def analyze_document(self, text: str, mode: str = "standard") -> List[Entity]:
        """
        Architecture simplifiée sans LLM :
        
        MODE STANDARD:
        - Regex UNIQUEMENT pour données structurées (téléphone, SIRET, email, adresse)
        
        MODE APPROFONDI:
        - Regex pour données structurées 
        - SpaCy NER pour détecter noms et organisations
        """
        start_time = time.time()
        logger.info(f"🚀 Analyse {mode.upper()} SIMPLIFIÉE - {len(text)} caractères")
        
        # ÉTAPE 1 : REGEX (toujours) - SEULEMENT données structurées
        structured_candidates = self._extract_structured_data(text)
        logger.info(f"✅ Regex structuré: {len(structured_candidates)} entités")
        
        if mode == "standard":
            # MODE STANDARD : SEULEMENT les données structurées
            logger.info("📋 Mode STANDARD : Regex uniquement")
            all_candidates = structured_candidates
            
        else:  # mode == "approfondi"
            # MODE APPROFONDI : Ajouter SpaCy NER
            logger.info("🔬 Mode APPROFONDI : Regex + SpaCy NER")
            
            # ÉTAPE 2 : SpaCy NER pour noms et organisations
            ner_candidates = []
            if self.spacy_nlp:
                ner_candidates = self._extract_persons_orgs_with_spacy(text)
                logger.info(f"✅ SpaCy NER: {len(ner_candidates)} candidats noms/organisations")
            else:
                logger.warning("❌ SpaCy indisponible - Mode approfondi limité")
                ner_candidates = []
            
            all_candidates = structured_candidates + ner_candidates
        
        # POST-TRAITEMENT : Déduplication et création entités finales
        deduplicated = self._deduplicate_candidates(all_candidates)
        final_entities = self._create_final_entities(deduplicated, text)
        
        total_time = time.time() - start_time
        logger.info(f"🎯 Analyse {mode} terminée: {len(final_entities)} entités en {total_time:.2f}s")
        
        return final_entities
    
    def _extract_structured_data(self, text: str) -> List[EntityCandidate]:
        """Extraction REGEX uniquement pour données structurées fiables"""
        candidates = []
        
        for entity_type, compiled_patterns in self._compiled_patterns.items():
            for pattern in compiled_patterns:
                try:
                    matches = pattern.finditer(text)
                    
                    for match in matches:
                        full_match = match.group(0).strip()
                        if len(full_match) < 2:
                            continue
                        
                        # Validation spécifique selon le type
                        confidence = 0.95
                        is_valid = True
                        
                        if entity_type == 'SIRET/SIREN':
                            is_valid = self._validate_siret_siren(full_match)
                            confidence = 0.98 if is_valid else 0.6
                        elif entity_type == 'EMAIL':
                            is_valid = '@' in full_match and '.' in full_match
                            confidence = 0.98 if is_valid else 0.5
                        elif entity_type == 'NUMÉRO DE TÉLÉPHONE':
                            digits = len(re.findall(r'\d', full_match))
                            is_valid = 8 <= digits <= 15
                            confidence = 0.95 if is_valid else 0.6
                        
                        if is_valid:
                            candidate = EntityCandidate(
                                text=full_match,
                                start=match.start(),
                                end=match.end(),
                                entity_type=entity_type,
                                confidence=confidence,
                                source='regex_structured',
                                context=text[max(0, match.start()-20):match.end()+20]
                            )
                            candidates.append(candidate)
                            
                except Exception as e:
                    logger.debug(f"Erreur pattern {entity_type}: {e}")
                    continue
        
        return candidates
    
    def _extract_persons_orgs_with_spacy(self, text: str) -> List[EntityCandidate]:
        """SpaCy NER UNIQUEMENT pour personnes et organisations"""
        candidates = []
        
        if not self.spacy_nlp:
            return candidates
        
        try:
            # Traitement SpaCy
            doc = self.spacy_nlp(text)
            
            for ent in doc.ents:
                # Mapping SpaCy vers nos types
                entity_type = None
                if ent.label_ in ['PER', 'PERSON']:
                    entity_type = 'PERSONNE'
                elif ent.label_ in ['ORG']:
                    entity_type = 'ORGANISATION'
                else:
                    continue  # Ignorer les autres types SpaCy
                
                # Filtrage qualité
                text_clean = ent.text.strip()
                if (len(text_clean) < 3 or 
                    len(text_clean) > 100 or
                    text_clean.isdigit() or
                    not any(c.isalpha() for c in text_clean)):
                    continue
                
                # Filtrage des mots communs (stopwords personnalisés)
                common_words = {
                    'le', 'la', 'les', 'de', 'du', 'des', 'et', 'ou', 'mais', 'donc',
                    'que', 'qui', 'quoi', 'où', 'quand', 'comment', 'pourquoi',
                    'avec', 'sans', 'pour', 'par', 'sur', 'sous', 'dans', 'vers',
                    'article', 'code', 'loi', 'décret', 'arrêt', 'jugement'
                }
                
                if text_clean.lower() in common_words:
                    continue
                
                # Confiance basée sur le score SpaCy
                confidence = 0.8  # Confiance de base SpaCy
                
                # Boost de confiance pour les patterns typiques français
                if entity_type == 'PERSONNE':
                    # Patterns de noms français
                    if any(title in text_clean for title in ['Monsieur', 'Madame', 'Maître', 'M.', 'Mme']):
                        confidence = 0.9
                    elif re.match(r'^[A-Z][a-z]+ [A-Z][A-Z]+$', text_clean):  # Prénom NOM
                        confidence = 0.85
                
                elif entity_type == 'ORGANISATION':
                    # Patterns d'organisations français
                    org_keywords = ['SARL', 'SAS', 'SA', 'EURL', 'SNC', 'Tribunal', 'Cour', 'Cabinet', 'Société']
                    if any(keyword in text_clean for keyword in org_keywords):
                        confidence = 0.9
                
                candidate = EntityCandidate(
                    text=text_clean,
                    start=ent.start_char,
                    end=ent.end_char,
                    entity_type=entity_type,
                    confidence=confidence,
                    source='spacy_ner',
                    context=text[max(0, ent.start_char-30):ent.end_char+30]
                )
                candidates.append(candidate)
                
        except Exception as e:
            logger.error(f"Erreur SpaCy NER: {e}")
        
        return candidates
    
    def _validate_siret_siren(self, text: str) -> bool:
        """Validation checksum SIRET/SIREN"""
        clean_number = re.sub(r'[^\d]', '', text)
        
        if len(clean_number) == 14:  # SIRET
            return self._luhn_checksum(clean_number)
        elif len(clean_number) == 9:  # SIREN
            return self._luhn_checksum(clean_number)
        elif len(clean_number) in [5, 11]:  # APE/NAF ou TVA
            return True
        return False
    
    def _luhn_checksum(self, number: str) -> bool:
        """Algorithme de Luhn pour validation"""
        try:
            total = 0
            for i, digit in enumerate(number):
                weight = 2 if i % 2 == 1 else 1
                product = int(digit) * weight
                if product > 9:
                    product = (product // 10) + (product % 10)
                total += product
            return total % 10 == 0
        except:
            return False
    
    def _deduplicate_candidates(self, candidates: List[EntityCandidate]) -> List[EntityCandidate]:
        """Déduplication avec priorité aux sources fiables"""
        seen = {}
        deduplicated = []
        
        # Trier par priorité de source (regex > spacy)
        source_priority = {
            'regex_structured': 3,
            'spacy_ner': 2
        }
        
        candidates_sorted = sorted(candidates, key=lambda c: source_priority.get(c.source, 1), reverse=True)
        
        for candidate in candidates_sorted:
            # Normaliser le texte pour la déduplication
            key = self._normalize_entity_text(candidate.text)
            
            if key not in seen:
                seen[key] = candidate
                deduplicated.append(candidate)
            else:
                # Garder celle avec la meilleure source ou confiance
                existing = seen[key]
                existing_priority = source_priority.get(existing.source, 1)
                candidate_priority = source_priority.get(candidate.source, 1)
                
                if (candidate_priority > existing_priority or 
                    (candidate_priority == existing_priority and candidate.confidence > existing.confidence)):
                    index = deduplicated.index(existing)
                    deduplicated[index] = candidate
                    seen[key] = candidate
        
        return deduplicated
    
    def _normalize_entity_text(self, text: str) -> str:
        """Normalise le texte d'une entité pour la déduplication"""
        # Enlever la ponctuation, normaliser les espaces
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _create_final_entities(self, candidates: List[EntityCandidate], full_text: str) -> List[Entity]:
        """Création des entités finales"""
        entities = []
        
        for candidate in candidates:
            try:
                # Mapping vers EntityTypeEnum
                try:
                    entity_type_enum = EntityTypeEnum(candidate.entity_type)
                except ValueError:
                    logger.debug(f"Type non mappé: {candidate.entity_type}")
                    continue
                
                # Comptage occurrences
                occurrences = full_text.lower().count(candidate.text.lower())
                occurrences = max(1, min(occurrences, 20))  # Limite raisonnable
                
                # Remplacement par défaut
                replacement = self._generate_replacement(candidate.entity_type, candidate.text)
                
                entity = Entity(
                    text=candidate.text,
                    type=entity_type_enum,
                    start=candidate.start,
                    end=candidate.end,
                    confidence=candidate.confidence,
                    source=candidate.source,
                    valid=True,
                    replacement=replacement,
                    occurrences=occurrences
                )
                
                entities.append(entity)
                
            except Exception as e:
                logger.debug(f"Erreur création entité: {e}")
                continue
        
        return entities
    
    def _generate_replacement(self, entity_type: str, original_text: str) -> str:
        """Génère un remplacement approprié"""
        hash_suffix = abs(hash(original_text.lower())) % 1000
        
        replacements = {
            'PERSONNE': f'PERSONNE_{hash_suffix}',
            'ORGANISATION': f'ORGANISATION_{hash_suffix}',
            'NUMÉRO DE TÉLÉPHONE': '0X XX XX XX XX',
            'EMAIL': 'email@anonyme.fr',
            'NUMÉRO DE SÉCURITÉ SOCIALE': 'X XX XX XX XXX XXX XX',
            'SIRET/SIREN': f'SIRET_{hash_suffix}',
            'ADRESSE': f'ADRESSE_{hash_suffix}',
            'RÉFÉRENCE JURIDIQUE': f'REFERENCE_{hash_suffix}'
        }
        
        return replacements.get(entity_type, f'ANONYME_{hash_suffix}')

# Instance globale
nlp_analyzer = SimplifiedNLPAnalyzer()