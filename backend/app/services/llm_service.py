import httpx
import json
import re
import os
from typing import List, Dict, Optional
from app.models.entities import Entity, EntityTypeEnum
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # Utiliser la variable d'environnement ou le service Docker par défaut
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')
        self.model = "llama3.1:8b"  # Modèle recommandé
        self.max_chunk_size = 4000  # Taille optimale pour le contexte
        logger.info(f"LLM Service initialisé avec URL: {self.ollama_url}")
        
    def check_ollama_available(self) -> bool:
        """Vérifie si Ollama est disponible"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            is_available = response.status_code == 200
            if is_available:
                logger.info("Ollama disponible et opérationnel")
            else:
                logger.warning(f"Ollama répond mais avec erreur: {response.status_code}")
            return is_available
        except Exception as e:
            logger.warning(f"Ollama non disponible: {e}")
            return False
    
    def extract_complex_entities(self, text: str) -> List[Entity]:
        """Extrait les entités complexes (personnes, organisations) avec LLM"""
        if not self.check_ollama_available():
            logger.warning("Ollama non disponible, retour de liste vide")
            return []
        
        # Découper le texte en chunks intelligents
        chunks = self._split_text_intelligently(text)
        all_entities = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Traitement chunk {i+1}/{len(chunks)} avec LLM")
            chunk_entities = self._process_chunk_with_llm(chunk, i * self.max_chunk_size)
            all_entities.extend(chunk_entities)
        
        # Déduplication finale
        return self._deduplicate_llm_entities(all_entities)
    
    def _split_text_intelligently(self, text: str) -> List[str]:
        """Découpe le texte en chunks logiques"""
        # Découper par paragraphes d'abord
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Si ajouter ce paragraphe dépasse la limite
            if len(current_chunk) + len(paragraph) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Paragraphe trop long, découper par phrases
                    sentences = re.split(r'[.!?]+', paragraph)
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) > self.max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            current_chunk += sentence + ". "
            else:
                current_chunk += "\n\n" + paragraph
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _process_chunk_with_llm(self, chunk: str, offset: int) -> List[Entity]:
        """Traite un chunk avec le LLM"""
        prompt = self._build_extraction_prompt(chunk)
        
        try:
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Très bas pour la cohérence
                        "top_p": 0.9,
                        "num_predict": 1000
                    }
                },
                timeout=300.0,
            )
            response.raise_for_status()
            result = response.json()
            return self._parse_llm_response(result.get("response", ""), chunk, offset)

        except httpx.TimeoutException:
            logger.error("Timeout lors de l'appel LLM")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur LLM HTTP {e.response.status_code}: {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Erreur lors de l'appel LLM: {e}")
            return []
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Construit le prompt pour l'extraction d'entités"""
        return f"""Tu es un expert en anonymisation de documents juridiques français. 

Analyse ce texte et identifie UNIQUEMENT les vraies personnes physiques et organisations/entreprises.

RÈGLES STRICTES:
1. PERSONNES: Noms complets de personnes réelles (prénom + nom, titres comme "Maître", "Monsieur")
2. ORGANISATIONS: Vraies entreprises, cabinets d'avocats, tribunaux, institutions
3. IGNORE: Mots isolés, morceaux de phrases, concepts abstraits, verbes, adjectifs

TEXTE À ANALYSER:
{text}

RÉPONDS UNIQUEMENT au format JSON suivant (sans explication):
{{
  "personnes": [
    {{"texte": "Maître Jean Dupont", "type": "PERSONNE"}},
    {{"texte": "Monsieur Pierre Martin", "type": "PERSONNE"}}
  ],
  "organisations": [
    {{"texte": "Cabinet Juridique SARL", "type": "ORGANISATION"}},
    {{"texte": "Tribunal de Grande Instance de Paris", "type": "ORGANISATION"}}
  ]
}}

Si aucune entité trouvée, réponds: {{"personnes": [], "organisations": []}}"""

    def _parse_llm_response(self, response: str, original_text: str, offset: int) -> List[Entity]:
        """Parse la réponse du LLM et crée les entités"""
        entities = []
        
        try:
            # Nettoyer la réponse (enlever les backticks markdown si présents)
            clean_response = response.strip()
            if clean_response.startswith('```'):
                clean_response = re.sub(r'```[a-zA-Z]*\n', '', clean_response)
                clean_response = re.sub(r'```$', '', clean_response)
            
            # Parser le JSON
            data = json.loads(clean_response)
            
            # Traiter les personnes
            for person in data.get('personnes', []):
                entity = self._create_entity_from_llm(
                    person, EntityTypeEnum.PERSONNE, original_text, offset
                )
                if entity:
                    entities.append(entity)
            
            # Traiter les organisations
            for org in data.get('organisations', []):
                entity = self._create_entity_from_llm(
                    org, EntityTypeEnum.ORGANISATION, original_text, offset
                )
                if entity:
                    entities.append(entity)
        
        except json.JSONDecodeError as e:
            logger.error(f"Erreur parsing JSON LLM: {e}")
            logger.debug(f"Réponse LLM: {response}")
        except Exception as e:
            logger.error(f"Erreur traitement réponse LLM: {e}")
        
        return entities
    
    def _create_entity_from_llm(self, llm_entity: dict, entity_type: EntityTypeEnum, 
                               original_text: str, offset: int) -> Optional[Entity]:
        """Crée une entité à partir de la réponse LLM"""
        try:
            text = llm_entity.get('texte', '').strip()
            if not text or len(text) < 3:
                return None
            
            # Trouver la position dans le texte original
            start_pos = original_text.lower().find(text.lower())
            if start_pos == -1:
                # Essayer de trouver des variantes
                words = text.split()
                if len(words) >= 2:
                    # Chercher par nom/prénom séparément
                    for word in words:
                        pos = original_text.lower().find(word.lower())
                        if pos != -1:
                            start_pos = pos
                            break
            
            if start_pos == -1:
                logger.debug(f"Entité '{text}' non trouvée dans le texte")
                # Créer quand même l'entité (elle sera marquée comme manuelle)
                start_pos = 0
                end_pos = len(text)
            else:
                end_pos = start_pos + len(text)
            
            # Générer le remplacement par défaut
            if entity_type == EntityTypeEnum.PERSONNE:
                replacement = f"PERSONNE_{hash(text) % 100}"
            else:
                replacement = f"ORGANISATION_{hash(text) % 100}"
            
            return Entity(
                text=text,
                type=entity_type,
                start=offset + start_pos,
                end=offset + end_pos,
                confidence=0.85,  # Confiance élevée pour LLM
                source='llm_ollama',
                replacement=replacement
            )
        
        except Exception as e:
            logger.error(f"Erreur création entité LLM: {e}")
            return None
    
    def _deduplicate_llm_entities(self, entities: List[Entity]) -> List[Entity]:
        """Déduplication des entités LLM"""
        seen = {}
        deduplicated = []
        
        for entity in entities:
            # Normaliser le texte pour la déduplication
            key = self._normalize_entity_text(entity.text)
            
            if key not in seen:
                seen[key] = entity
                deduplicated.append(entity)
            else:
                # Garder celle avec la meilleure confiance
                if entity.confidence > seen[key].confidence:
                    index = deduplicated.index(seen[key])
                    deduplicated[index] = entity
                    seen[key] = entity
        
        return deduplicated
    
    def _normalize_entity_text(self, text: str) -> str:
        """Normalise le texte d'une entité pour la déduplication"""
        # Enlever la ponctuation, normaliser les espaces
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        normalized = ' '.join(normalized.split())
        return normalized

# Instance globale
llm_service = LLMService()