import spacy
import re
import requests
import json
from typing import List, Dict, Set, Tuple
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

class EnhancedNLPAnalyzer:
    def __init__(self):
        # SpaCy pour la structure de base
        try:
            self.nlp = spacy.load("fr_core_news_lg")
            logger.info("Modèle spaCy fr_core_news_lg chargé")
        except OSError:
            logger.warning("Impossible de charger spaCy - Mode dégradé")
            self.nlp = None
        
        # Configuration Ollama depuis les settings
        self.ollama_url = settings.OLLAMA_URL
        self.ollama_model = settings.OLLAMA_MODEL
        self.ollama_timeout = settings.OLLAMA_TIMEOUT
        
        # Test de connexion Ollama
        self._test_ollama_connection()
        
    def _test_ollama_connection(self):
        """Test la connexion à Ollama"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                if self.ollama_model in model_names:
                    logger.info(f"Ollama connecté - Modèle {self.ollama_model} disponible")
                    self.ollama_available = True
                else:
                    logger.warning(f"Modèle {self.ollama_model} non trouvé. Modèles disponibles: {model_names}")
                    self.ollama_available = False
            else:
                logger.warning(f"Ollama non accessible - Status {response.status_code}")
                self.ollama_available = False
        except Exception as e:
            logger.warning(f"Ollama non disponible: {e}")
            self.ollama_available = False
        
    def analyze_document(self, text: str, mode: str = "standard") -> List[Entity]:
        """
        Analyse hybride optimisée : Regex > Ollama > Déduplication globale
        """
        logger.info(f"Démarrage analyse {mode} - {len(text)} caractères")
        
        # 1. REGEX PATTERNS (toujours en premier - très rapide et fiable)
        regex_candidates = self._extract_with_french_patterns(text)
        logger.info(f"Regex: {len(regex_candidates)} candidats")
        
        # 2. OLLAMA selon le mode et disponibilité
        ollama_candidates = []
        if mode == "approfondi" and self.ollama_available:
            ollama_candidates = self._extract_with_ollama(text)
            logger.info(f"Ollama: {len(ollama_candidates)} candidats")
        
        # 3. SpaCy en complément (si disponible et mode approfondi)
        spacy_candidates = []
        if self.nlp and mode == "approfondi":
            spacy_candidates = self._extract_with_spacy_targeted(text)
            logger.info(f"SpaCy: {len(spacy_candidates)} candidats")
        
        # 4. FUSION ET DÉDUPLICATION GLOBALE
        all_candidates = regex_candidates + ollama_candidates + spacy_candidates
        deduplicated_entities = self._smart_deduplicate(all_candidates, text)
        
        # 5. POST-TRAITEMENT ET VALIDATION
        final_entities = self._post_process_entities(deduplicated_entities, text)
        
        logger.info(f"Analyse terminée: {len(final_entities)} entités finales")
        return final_entities
    
    def _extract_with_ollama(self, text: str) -> List[EntityCandidate]:
        """Extraction avec Ollama - traitement par chunks intelligents"""
        if not self.ollama_available:
            logger.warning("Ollama non disponible - Skip analyse Ollama")
            return []
            
        candidates = []
        
        try:
            # Diviser le texte en chunks avec chevauchement pour éviter les coupures
            chunks = self._smart_chunk_text(text, max_chunk_size=2000, overlap=200)
            
            for i, chunk in enumerate(chunks):
                chunk_candidates = self._analyze_chunk_with_ollama(chunk, i)
                # Ajuster les positions pour le texte complet
                for candidate in chunk_candidates:
                    # Trouver la position réelle dans le texte complet
                    real_start = text.find(candidate.text)
                    if real_start != -1:
                        candidate.start = real_start
                        candidate.end = real_start + len(candidate.text)
                        candidates.append(candidate)
                
        except Exception as e:
            logger.error(f"Erreur Ollama: {e}")
        
        return candidates
    
    def _analyze_chunk_with_ollama(self, chunk: str, chunk_index: int) -> List[EntityCandidate]:
        """Analyse d'un chunk avec Ollama"""
        prompt = f"""Tu es un expert en anonymisation de documents juridiques français. 
Identifie PRÉCISÉMENT les entités à anonymiser dans ce texte juridique.

TYPES D'ENTITÉS À DÉTECTER :
- PERSONNE: noms, prénoms, Maître X, M./Mme X
- ADRESSE: adresses complètes, codes postaux + villes
- NUMÉRO DE TÉLÉPHONE: numéros français (01..., +33...)
- EMAIL: adresses email
- NUMÉRO DE SÉCURITÉ SOCIALE: numéros de sécurité sociale
- SIRET/SIREN: numéros SIRET, SIREN, RCS
- ORGANISATION: entreprises, tribunaux, institutions
- AUTRE: références de dossiers, numéros RG

TEXTE À ANALYSER :
{chunk}

RÉPONDS UNIQUEMENT en JSON strict, sans commentaire :
[
  {{
    "text": "texte exact trouvé",
    "type": "TYPE_ENTITÉ",
    "confidence": 0.95
  }}
]"""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,  # Très peu de créativité
                        "top_p": 0.9,
                        "repeat_penalty": 1.1
                    }
                },
                timeout=self.ollama_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_ollama_response(result.get('response', ''), chunk, chunk_index)
            else:
                logger.error(f"Erreur Ollama HTTP {response.status_code}: {response.text}")
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout Ollama chunk {chunk_index}")
        except Exception as e:
            logger.error(f"Erreur requête Ollama chunk {chunk_index}: {e}")
        
        return []
    
    def _parse_ollama_response(self, response: str, chunk: str, chunk_index: int) -> List[EntityCandidate]:
        """Parse la réponse JSON d'Ollama"""
        candidates = []
        
        try:
            # Nettoyer la réponse (parfois Ollama ajoute du texte avant/après le JSON)
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                entities_data = json.loads(json_str)
                
                for entity_data in entities_data:
                    # Validation des données
                    text = entity_data.get('text', '').strip()
                    entity_type = entity_data.get('type', 'AUTRE')
                    confidence = float(entity_data.get('confidence', 0.8))
                    
                    if len(text) < 2:
                        continue
                    
                    # Trouver la position réelle dans le chunk
                    start_pos = chunk.find(text)
                    if start_pos != -1:
                        candidate = EntityCandidate(
                            text=text,
                            start=start_pos,
                            end=start_pos + len(text),
                            entity_type=entity_type,
                            confidence=confidence,
                            source=f'ollama_chunk_{chunk_index}',
                            context=chunk[max(0, start_pos-50):start_pos+len(text)+50]
                        )
                        candidates.append(candidate)
                        
        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON Ollama: {e}")
            logger.debug(f"Réponse brute: {response[:200]}...")
        except Exception as e:
            logger.error(f"Erreur traitement réponse Ollama: {e}")
        
        return candidates
    
    def _smart_chunk_text(self, text: str, max_chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        """Découpage intelligent du texte pour préserver le contexte"""
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_chunk_size
            
            # Si c'est le dernier chunk, prendre tout ce qui reste
            if end >= len(text):
                chunks.append(text[start:])
                break
            
            # Chercher une coupure propre (fin de phrase, paragraphe)
            chunk_text = text[start:end]
            
            # Chercher la dernière fin de phrase dans les 200 derniers caractères
            search_start = max(0, len(chunk_text) - 200)
            last_sentence_end = -1
            
            for i in range(len(chunk_text) - 1, search_start, -1):
                if chunk_text[i] in '.!?\n':
                    last_sentence_end = i + 1
                    break
            
            if last_sentence_end > 0:
                # Couper à la fin de phrase
                chunks.append(text[start:start + last_sentence_end])
                start = start + last_sentence_end - overlap
            else:
                # Pas de fin de phrase trouvée, couper brutalement
                chunks.append(chunk_text)
                start = end - overlap
        
        return chunks
    
    def _extract_with_french_patterns(self, text: str) -> List[EntityCandidate]:
        """Extraction regex optimisée (le plus fiable)"""
        candidates = []
        
        for entity_type, config in STRUCTURED_ENTITY_TYPES.items():
            patterns = config.get('patterns', [])
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    full_match = match.group(0).strip()
                    if len(full_match) < 2:
                        continue
                    
                    # Validation spéciale selon le type
                    confidence = 0.95  # Regex = haute confiance
                    is_valid = True
                    
                    if entity_type == 'SIRET/SIREN':
                        is_valid = self._validate_siret_siren(full_match)
                        confidence = 0.98 if is_valid else 0.6
                    
                    candidate = EntityCandidate(
                        text=full_match,
                        start=match.start(),
                        end=match.end(),
                        entity_type=entity_type,
                        confidence=confidence,
                        source='regex_french',
                        context=text[max(0, match.start()-30):match.end()+30]
                    )
                    candidates.append(candidate)
        
        return candidates
    
    def _extract_with_spacy_targeted(self, text: str) -> List[EntityCandidate]:
        """SpaCy ciblé sur ce que regex n'a pas trouvé"""
        candidates = []
        
        try:
            doc = self.nlp(text)
            
            for ent in doc.ents:
                # Mapper les types spaCy vers nos types
                entity_type = self._map_spacy_to_entity_type(ent.label_)
                if entity_type:
                    candidate = EntityCandidate(
                        text=ent.text.strip(),
                        start=ent.start_char,
                        end=ent.end_char,
                        entity_type=entity_type,
                        confidence=0.7,  # SpaCy = confiance moyenne
                        source='spacy_targeted',
                        context=text[max(0, ent.start_char-30):ent.end_char+30]
                    )
                    candidates.append(candidate)
                    
        except Exception as e:
            logger.error(f"Erreur spaCy: {e}")
        
        return candidates
    
    def _smart_deduplicate(self, candidates: List[EntityCandidate], full_text: str) -> List[EntityCandidate]:
        """Déduplication intelligente avec scoring"""
        # Créer des groupes par texte normalisé
        groups = {}
        
        for candidate in candidates:
            # Clé de déduplication : texte normalisé
            key = self._normalize_text(candidate.text)
            
            if key not in groups:
                groups[key] = []
            groups[key].append(candidate)
        
        # Pour chaque groupe, garder le meilleur candidat
        deduplicated = []
        
        for key, group_candidates in groups.items():
            if len(group_candidates) == 1:
                deduplicated.extend(group_candidates)
            else:
                # Choisir le meilleur selon plusieurs critères
                best_candidate = self._select_best_candidate(group_candidates)
                deduplicated.append(best_candidate)
        
        return deduplicated
    
    def _select_best_candidate(self, candidates: List[EntityCandidate]) -> EntityCandidate:
        """Sélectionne le meilleur candidat parmi les doublons"""
        # Priorité : regex > ollama > spacy
        source_priority = {'regex_french': 3, 'ollama': 2, 'spacy': 1}
        
        best = candidates[0]
        best_score = 0
        
        for candidate in candidates:
            # Score basé sur : source + confiance + longueur
            source_score = source_priority.get(candidate.source.split('_')[0], 0)
            confidence_score = candidate.confidence
            length_score = len(candidate.text) / 100  # Bonus pour textes plus longs
            
            total_score = source_score * 2 + confidence_score + length_score
            
            if total_score > best_score:
                best = candidate
                best_score = total_score
        
        return best
    
    def _post_process_entities(self, candidates: List[EntityCandidate], full_text: str) -> List[Entity]:
        """Post-traitement final : validation, comptage d'occurrences"""
        entities = []
        
        for candidate in candidates:
            # Compter les occurrences réelles dans tout le texte
            occurrences = self._count_occurrences(candidate.text, full_text)
            
            # Valider selon le type
            is_valid = self._validate_entity(candidate)
            
            # Générer remplacement par défaut
            replacement = self._generate_default_replacement(candidate.entity_type, candidate.text)
            
            # Créer l'entité finale
            entity = Entity(
                text=candidate.text,
                type=EntityTypeEnum(candidate.entity_type),
                start=candidate.start,
                end=candidate.end,
                confidence=candidate.confidence,
                source=candidate.source,
                valid=is_valid,
                replacement=replacement,
                occurrences=occurrences
            )
            
            entities.append(entity)
        
        return entities
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour la déduplication"""
        return re.sub(r'\s+', ' ', text.lower().strip())
    
    def _validate_entity(self, candidate: EntityCandidate) -> bool:
        """Validation selon le type d'entité"""
        if candidate.entity_type == 'SIRET/SIREN':
            return self._validate_siret_siren(candidate.text)
        elif candidate.entity_type == 'EMAIL':
            return '@' in candidate.text and '.' in candidate.text
        elif candidate.entity_type == 'NUMÉRO DE TÉLÉPHONE':
            return len(re.findall(r'\d', candidate.text)) >= 8
        return True
    
    def _validate_siret_siren(self, text: str) -> bool:
        """Validation checksum SIRET/SIREN"""
        clean_number = re.sub(r'[^\d]', '', text)
        
        if len(clean_number) == 14:
            return self._validate_siret_checksum(clean_number)
        elif len(clean_number) == 9:
            return self._validate_siren_checksum(clean_number)
        return len(clean_number) in [5, 11]  # APE/NAF ou TVA
    
    def _validate_siret_checksum(self, siret: str) -> bool:
        """Validation Luhn pour SIRET"""
        try:
            total = 0
            for i, digit in enumerate(siret):
                weight = 2 if i % 2 == 1 else 1
                product = int(digit) * weight
                if product > 9:
                    product = (product // 10) + (product % 10)
                total += product
            return total % 10 == 0
        except:
            return False
    
    def _validate_siren_checksum(self, siren: str) -> bool:
        """Validation Luhn pour SIREN"""
        try:
            total = 0
            for i, digit in enumerate(siren):
                weight = 2 if i % 2 == 1 else 1
                product = int(digit) * weight
                if product > 9:
                    product = (product // 10) + (product % 10)
                total += product
            return total % 10 == 0
        except:
            return False
    
    def _count_occurrences(self, entity_text: str, full_text: str) -> int:
        """Compte les occurrences exactes et variations"""
        count = len(re.findall(re.escape(entity_text), full_text, re.IGNORECASE))
        return max(1, count)
    
    def _generate_default_replacement(self, entity_type: str, original_text: str) -> str:
        """Génère un remplacement par défaut intelligent"""
        config = ENTITY_TYPES.get(entity_type, {})
        base_replacement = config.get('default_replacement', 'ANONYME_X')
        
        # Hash pour cohérence (même entité = même remplacement)
        hash_suffix = hashlib.md5(original_text.lower().encode()).hexdigest()[:3].upper()
        return f"{base_replacement.replace('_X', '')}_{hash_suffix}"
    
    def _map_spacy_to_entity_type(self, spacy_label: str) -> str:
        """Mapping spaCy vers nos types"""
        mapping = {
            'PER': 'PERSONNE',
            'PERSON': 'PERSONNE',
            'ORG': 'ORGANISATION',
            'LOC': 'ADRESSE',
            'MISC': 'AUTRE'
        }
        return mapping.get(spacy_label, 'AUTRE')

# Instance globale
nlp_analyzer = EnhancedNLPAnalyzer()