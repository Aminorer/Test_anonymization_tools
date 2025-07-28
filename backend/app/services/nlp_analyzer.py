import spacy
import re
from typing import List, Dict, Set
from app.models.entities import Entity, EntityTypeEnum, ENTITY_TYPES
import logging

logger = logging.getLogger(__name__)

class NLPAnalyzer:
    def __init__(self):
        try:
            self.nlp = spacy.load("fr_core_news_lg")
            logger.info("Modèle spaCy fr_core_news_lg chargé avec succès")
        except OSError:
            logger.error("Impossible de charger le modèle spaCy fr_core_news_lg")
            self.nlp = None
    
    def analyze_document(self, text: str, mode: str = "standard") -> List[Entity]:
        """
        Analyse un document et retourne les entités détectées
        Mode 'standard' : regex + spaCy basique (5-30s)
        Mode 'approfondi' : regex + spaCy + validation croisée (30s-2min)
        """
        entities = []
        
        # Étape 1 : TOUJOURS patterns regex français
        regex_entities = self._extract_with_french_patterns(text)
        entities.extend(regex_entities)
        
        # Étape 2 : spaCy selon mode
        if self.nlp is not None:
            if mode == "standard":
                spacy_entities = self._extract_with_spacy_basic(text) 
            else:  # approfondi
                spacy_entities = self._extract_with_spacy_detailed(text)
            entities.extend(spacy_entities)
        
        # Étape 3 : Déduplication (CRITIQUE)
        deduplicated_entities = self._deduplicate_entities(entities, text)
        
        # Étape 4 : Compter les occurrences
        for entity in deduplicated_entities:
            entity.occurrences = self._count_occurrences(entity.text, text)
        
        return deduplicated_entities
    
    def _extract_with_french_patterns(self, text: str) -> List[Entity]:
        """Extraction avec patterns regex français spécialisés"""
        entities = []
        
        for entity_type, config in ENTITY_TYPES.items():
            for pattern in config['patterns']:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    full_match = match.group(0).strip()
                    if len(full_match) < 2:  # Ignore les matches trop courts
                        continue
                    
                    # Validation spéciale pour SIRET/SIREN
                    is_valid = True
                    if entity_type == 'SIRET/SIREN':
                        is_valid = self._validate_siret_siren(full_match)
                    
                    entity = Entity(
                        text=full_match,
                        type=EntityTypeEnum(entity_type),
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9 if is_valid else 0.6,
                        source='regex_french',
                        valid=is_valid,
                        replacement=self._generate_default_replacement(entity_type, full_match)
                    )
                    entities.append(entity)
        
        return entities
    
    def _extract_with_spacy_basic(self, text: str) -> List[Entity]:
        """Extraction spaCy basique"""
        entities = []
        
        try:
            doc = self.nlp(text)
            
            for ent in doc.ents:
                entity_type = self._map_spacy_to_entity_type(ent.label_)
                if entity_type:
                    entity = Entity(
                        text=ent.text.strip(),
                        type=entity_type,
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=0.7,
                        source='spacy_basic',
                        replacement=self._generate_default_replacement(entity_type.value, ent.text)
                    )
                    entities.append(entity)
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse spaCy basique: {e}")
        
        return entities
    
    def _extract_with_spacy_detailed(self, text: str) -> List[Entity]:
        """Extraction spaCy détaillée avec validation croisée"""
        entities = self._extract_with_spacy_basic(text)
        
        try:
            # Analyse supplémentaire avec patterns contextuels
            doc = self.nlp(text)
            
            # Recherche de noms propres dans le contexte juridique
            for token in doc:
                if (token.pos_ == "PROPN" and 
                    len(token.text) > 2 and 
                    token.text[0].isupper()):
                    
                    # Vérifier le contexte
                    context = doc[max(0, token.i-3):min(len(doc), token.i+4)]
                    context_text = " ".join([t.text for t in context])
                    
                    if self._is_juridical_context(context_text):
                        entity = Entity(
                            text=token.text,
                            type=EntityTypeEnum.PERSONNE,
                            start=token.idx,
                            end=token.idx + len(token.text),
                            confidence=0.8,
                            source='spacy_detailed',
                            replacement=self._generate_default_replacement('PERSONNE', token.text)
                        )
                        entities.append(entity)
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse spaCy détaillée: {e}")
        
        return entities
    
    def _map_spacy_to_entity_type(self, spacy_label: str) -> EntityTypeEnum:
        """Mapping des labels spaCy vers nos types d'entités"""
        mapping = {
            'PER': EntityTypeEnum.PERSONNE,
            'PERSON': EntityTypeEnum.PERSONNE,
            'ORG': EntityTypeEnum.ORGANISATION,
            'LOC': EntityTypeEnum.ADRESSE,
            'MISC': EntityTypeEnum.AUTRE
        }
        return mapping.get(spacy_label)
    
    def _is_juridical_context(self, context: str) -> bool:
        """Détermine si le contexte est juridique"""
        juridical_keywords = [
            'maître', 'avocat', 'tribunal', 'cour', 'jugement', 'arrêt',
            'contrat', 'accord', 'convention', 'société', 'client',
            'demandeur', 'défendeur', 'parties', 'signataire'
        ]
        context_lower = context.lower()
        return any(keyword in context_lower for keyword in juridical_keywords)
    
    def _validate_siret_siren(self, text: str) -> bool:
        """Validation des numéros SIRET/SIREN"""
        # Nettoyer le texte
        clean_number = re.sub(r'[\s\.-]', '', text)
        clean_number = re.sub(r'[^\d]', '', clean_number)
        
        if len(clean_number) == 14:
            return self._validate_siret_checksum(clean_number)
        elif len(clean_number) == 9:
            return self._validate_siren_checksum(clean_number)
        elif len(clean_number) == 11:  # TVA
            return True
        elif len(clean_number) == 5:  # APE/NAF
            return True
        
        return False
    
    def _validate_siret_checksum(self, siret: str) -> bool:
        """Validation checksum SIRET"""
        if len(siret) != 14:
            return False
        
        try:
            total = 0
            for i, digit in enumerate(siret):
                weight = 2 if i % 2 == 1 else 1
                product = int(digit) * weight
                if product > 9:
                    product = (product // 10) + (product % 10)
                total += product
            
            return total % 10 == 0
        except ValueError:
            return False
    
    def _validate_siren_checksum(self, siren: str) -> bool:
        """Validation checksum SIREN"""
        if len(siren) != 9:
            return False
        
        try:
            total = 0
            for i, digit in enumerate(siren):
                weight = 2 if i % 2 == 1 else 1
                product = int(digit) * weight
                if product > 9:
                    product = (product // 10) + (product % 10)
                total += product
            
            return total % 10 == 0
        except ValueError:
            return False
    
    def _deduplicate_entities(self, entities: List[Entity], text: str) -> List[Entity]:
        """Déduplication des entités basée sur le texte et la position"""
        seen = {}
        deduplicated = []
        
        for entity in entities:
            # Clé de déduplication basée sur le texte normalisé
            key = entity.text.lower().strip()
            
            if key not in seen:
                seen[key] = entity
                deduplicated.append(entity)
            else:
                # Garder l'entité avec la meilleure confiance
                if entity.confidence > seen[key].confidence:
                    # Remplacer dans la liste
                    index = deduplicated.index(seen[key])
                    deduplicated[index] = entity
                    seen[key] = entity
        
        return deduplicated
    
    def _count_occurrences(self, entity_text: str, full_text: str) -> int:
        """Compte le nombre d'occurrences d'une entité dans le texte"""
        return len(re.findall(re.escape(entity_text), full_text, re.IGNORECASE))
    
    def _generate_default_replacement(self, entity_type: str, original_text: str) -> str:
        """Génère un remplacement par défaut pour une entité"""
        config = ENTITY_TYPES.get(entity_type, {})
        base_replacement = config.get('default_replacement', 'ANONYME_X')
        
        # Ajouter un suffixe unique basé sur la longueur du texte original
        suffix = len(original_text) % 10
        return f"{base_replacement.replace('_X', '')}_{suffix}"

# Instance globale
nlp_analyzer = NLPAnalyzer()