import spacy
import re
import httpx
import json
from typing import List, Dict, Set, Tuple, Optional
from app.models.entities import (
    Entity,
    EntityTypeEnum,
    ENTITY_TYPES,
    STRUCTURED_ENTITY_TYPES,
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

class CorrectNLPAnalyzer:
    def __init__(self):
        # 1. REGEX : SEULEMENT pour données structurées (téléphone, SIRET, email, adresse)
        self._compiled_patterns = {}
        self._compile_structured_patterns()
        
        # 2. NER SpaCy : Pour noms et organisations (mode approfondi seulement)
        self.spacy_nlp = None
        self._load_spacy_model()
        
        # 3. LLM Validation : Pour valider les résultats NER (mode approfondi seulement)
        self.ollama_url = settings.OLLAMA_URL
        self.ollama_model = "qwen2.5:0.5b"  # Modèle ultra-léger pour validation
        self.ollama_timeout = 8
        self.ollama_available = False
        self._test_ollama_connection()
        
        logger.info("🧠 NLP Analyzer correct initialisé")
        
    def _compile_structured_patterns(self):
        """Compile UNIQUEMENT les patterns pour données structurées"""
        logger.info("🔧 Compilation patterns STRUCTURÉS uniquement...")
        
        # SEULEMENT les types de données structurées
        structured_types = [
            'NUMÉRO DE TÉLÉPHONE',
            'EMAIL', 
            'SIRET/SIREN',
            'NUMÉRO DE SÉCURITÉ SOCIALE',
            'ADRESSE',
            'RÉFÉRENCE JURIDIQUE'
        ]
        
        for entity_type in structured_types:
            if entity_type in STRUCTURED_ENTITY_TYPES:
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
        logger.info("❌ AUCUN pattern regex pour noms/organisations (volontairement)")
    
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
    
    def _test_ollama_connection(self):
        """Test Ollama pour validation LLM"""
        try:
            response = httpx.get(f"{self.ollama_url}/api/tags", timeout=3.0)
            if response.status_code == 200:
                models = response.json().get('models', [])
                available_models = [m['name'] for m in models]
                
                validation_models = [
                    "qwen2.5:0.5b", "gemma2:2b", "phi3:mini", 
                    "mistral:7b-instruct", "llama3.2:3b"
                ]
                
                for model in validation_models:
                    if model in available_models:
                        self.ollama_model = model
                        self.ollama_available = True
                        logger.info(f"✅ LLM Validation: {model}")
                        return
                        
                logger.warning("⚠️ Aucun modèle léger pour validation LLM")
                self.ollama_available = False
        except Exception as e:
            logger.info(f"ℹ️ LLM Validation indisponible: {e}")
            self.ollama_available = False
    
    def analyze_document(self, text: str, mode: str = "standard") -> List[Entity]:
        """
        Architecture claire :
        
        MODE STANDARD:
        - Regex UNIQUEMENT pour données structurées (téléphone, SIRET, email, adresse)
        - AUCUNE détection de noms/organisations
        
        MODE APPROFONDI:
        - Regex pour données structurées (téléphone, SIRET, email, adresse)
        - SpaCy NER pour détecter noms et organisations
        - LLM pour valider les résultats SpaCy
        """
        start_time = time.time()
        logger.info(f"🚀 Analyse {mode.upper()} - {len(text)} caractères")
        
        # ÉTAPE 1 : REGEX (toujours) - SEULEMENT données structurées
        structured_candidates = self._extract_structured_data(text)
        logger.info(f"✅ Regex structuré: {len(structured_candidates)} entités (téléphone, SIRET, email...)")
        
        if mode == "standard":
            # MODE STANDARD : SEULEMENT les données structurées
            logger.info("📋 Mode STANDARD : Aucune détection noms/organisations")
            all_candidates = structured_candidates
            
        else:  # mode == "approfondi"
            # MODE APPROFONDI : Ajouter NER + Validation LLM
            logger.info("🔬 Mode APPROFONDI : NER + Validation LLM pour noms/organisations")
            
            # ÉTAPE 2 : SpaCy NER pour noms et organisations
            ner_candidates = []
            if self.spacy_nlp:
                ner_candidates = self._extract_persons_orgs_with_spacy(text)
                logger.info(f"✅ SpaCy NER: {len(ner_candidates)} candidats noms/organisations")
            else:
                logger.error("❌ SpaCy indisponible - Mode approfondi impossible")
                ner_candidates = []
            
            # ÉTAPE 3 : Validation LLM des candidats NER
            validated_candidates = []
            if self.ollama_available and ner_candidates:
                validated_candidates = self._validate_ner_with_llm(ner_candidates, text)
                logger.info(f"✅ LLM Validation: {len(validated_candidates)}/{len(ner_candidates)} validés")
            else:
                if ner_candidates:
                    logger.warning("⚠️ LLM indisponible - Garder candidats SpaCy avec filtrage confiance")
                    validated_candidates = self._filter_by_confidence(ner_candidates)
                else:
                    validated_candidates = []
            
            all_candidates = structured_candidates + validated_candidates
        
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
                        
                        if is_valid:  # Seulement garder les entités valides
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
                
                # Confiance basée sur le score SpaCy (si disponible)
                confidence = 0.8  # Confiance de base SpaCy
                if hasattr(ent, 'ent_kb_id_') and ent.ent_kb_id_:
                    confidence = 0.9  # Plus de confiance si entité liée
                
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
    
    def _validate_ner_with_llm(self, candidates: List[EntityCandidate], text: str) -> List[EntityCandidate]:
        """LLM validation des candidats SpaCy - Traitement par batch"""
        if not candidates:
            return []
        
        validated = []
        
        # Traiter par petits batches pour éviter timeout
        batch_size = 5
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i+batch_size]
            batch_validated = self._validate_batch_with_llm(batch, text)
            validated.extend(batch_validated)
            
            # Pause courte entre batches
            time.sleep(0.5)
        
        return validated
    
    def _validate_batch_with_llm(self, batch: List[EntityCandidate], text: str) -> List[EntityCandidate]:
        """Validation LLM d'un batch de candidats"""
        if not batch:
            return []
        
        # Créer le prompt de validation
        entities_to_validate = []
        for candidate in batch:
            entities_to_validate.append({
                "text": candidate.text,
                "type": candidate.entity_type,
                "context": candidate.context
            })
        
        prompt = f"""Tu es un expert en reconnaissance d'entités nommées françaises.

Valide si ces entités détectées par SpaCy sont correctes :

{json.dumps(entities_to_validate, ensure_ascii=False, indent=2)}

Pour chaque entité, réponds SEULEMENT par JSON :
[
  {{"text": "nom exact", "valid": true, "confidence": 0.95, "reason": "nom de personne français valide"}},
  {{"text": "autre", "valid": false, "confidence": 0.2, "reason": "pas un nom réel"}}
]

Critères de validation :
- PERSONNE : Vrai nom français (prénom + nom, titre + nom)
- ORGANISATION : Vraie entreprise, cabinet, tribunal, institution
- Rejeter : Mots isolés, concepts abstraits, erreurs OCR"""

        try:
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.8,
                        "num_predict": 500
                    }
                },
                timeout=self.ollama_timeout,
            )
            response.raise_for_status()
            
            result = response.json()
            return self._parse_llm_validation(result.get('response', ''), batch)
            
        except Exception as e:
            logger.warning(f"Erreur validation LLM batch: {e}")
            # Fallback : garder les candidats avec confiance réduite
            return self._filter_by_confidence(batch, min_confidence=0.7)
    
    def _parse_llm_validation(self, llm_response: str, original_batch: List[EntityCandidate]) -> List[EntityCandidate]:
        """Parse la réponse LLM de validation"""
        validated = []
        
        try:
            # Extraire le JSON de la réponse
            json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
            if not json_match:
                logger.warning("Pas de JSON dans réponse LLM")
                return self._filter_by_confidence(original_batch)
            
            validations = json.loads(json_match.group(0))
            
            # Mapper les validations aux candidats originaux
            for i, validation in enumerate(validations):
                if i < len(original_batch):
                    candidate = original_batch[i]
                    
                    if validation.get('valid', False):
                        # Mettre à jour la confiance avec celle du LLM
                        candidate.confidence = min(validation.get('confidence', 0.8), 0.95)
                        candidate.source = 'spacy_llm_validated'
                        validated.append(candidate)
                        
        except Exception as e:
            logger.debug(f"Erreur parsing validation LLM: {e}")
            # Fallback
            return self._filter_by_confidence(original_batch)
        
        return validated
    
    def _filter_by_confidence(self, candidates: List[EntityCandidate], min_confidence: float = 0.75) -> List[EntityCandidate]:
        """Filtrage par confiance (fallback sans LLM)"""
        return [c for c in candidates if c.confidence >= min_confidence]
    
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
        """Déduplication simple mais efficace"""
        seen = {}
        deduplicated = []
        
        for candidate in candidates:
            key = f"{candidate.text.lower().strip()}_{candidate.entity_type}"
            
            if key not in seen:
                seen[key] = candidate
                deduplicated.append(candidate)
            else:
                # Garder celui avec la meilleure source (regex > spacy_llm > spacy)
                existing = seen[key]
                if (candidate.source == 'regex_structured' or 
                    (candidate.source == 'spacy_llm_validated' and existing.source == 'spacy_ner')):
                    idx = deduplicated.index(existing)
                    deduplicated[idx] = candidate
                    seen[key] = candidate
        
        return deduplicated
    
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
nlp_analyzer = CorrectNLPAnalyzer()