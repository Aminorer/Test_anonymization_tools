"""Interface with a local Ollama server for legal document analysis."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import requests


__all__ = ["OllamaLegalAnalyzer"]


class OllamaLegalAnalyzer:
    """Legal document analyzer backed by an Ollama server.

    Parameters
    ----------
    base_url: str
        Base URL of the Ollama server.
    model: str
        Name of the model to query on the Ollama server.
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.is_available = self._check_ollama_availability()

    # --- Availability -------------------------------------------------
    def _check_ollama_availability(self) -> bool:
        """Check whether the Ollama server is reachable."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            response.raise_for_status()
            return True
        except requests.RequestException:
            logging.warning("Ollama server unavailable at %s", self.base_url)
            return False

    # --- Prompt loaders -----------------------------------------------
    def _load_document_type_prompt(self) -> str:
        return (
            "You are a legal expert. Determine the document type such as "
            "contract, court_decision, legislation, correspondence or other "
            "for the following document:\n\n{document}\n\nType:"
        )

    def _load_entity_analysis_prompt(self) -> str:
        return (
            "You help anonymize legal documents. Given the document text and the "
            "currently detected entities in JSON format, return an improved JSON "
            "list of entities with fields 'text' and 'label'.\n\nDocument:\n{document}\n\n"
            "Current entities:\n{entities}\n\nImproved entities:"
        )

    def _load_coherence_prompt(self) -> str:
        return (
            "Check if the anonymized legal document is coherent. Compare the "
            "original text and the anonymized text using the provided entities. "
            "Return a JSON object with keys 'coherent' (true/false) and 'issues' "
            "(list of strings).\n\nOriginal:\n{original}\n\nAnonymized:\n{anonymized}\n\n"
            "Entities:\n{entities}\n\nResult:"
        )

    def _load_improvement_prompt(self) -> str:
        return (
            "Suggest improvements to the anonymization of the following legal "
            "text. Use the provided entities and output plain text suggestions.\n\n"
            "Text:\n{text}\n\nEntities:\n{entities}\n\nSuggestions:"
        )

    # --- Core methods -------------------------------------------------
    def detect_document_type(self, document_text: str) -> str:
        """Return the detected document type or ``"unknown"`` if unavailable."""
        if not self.is_available:
            return "unknown"

        prompt = self._load_document_type_prompt().format(document=document_text)
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip().lower() or "unknown"
        except (requests.RequestException, ValueError, json.JSONDecodeError):
            self.is_available = False
            return "unknown"

    def enhance_entity_detection(
        self, document_text: str, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Return an improved list of entities using Ollama.

        If the server is unavailable, the original list is returned unchanged.
        """
        if not self.is_available:
            return entities

        prompt = self._load_entity_analysis_prompt().format(
            document=document_text, entities=json.dumps(entities, ensure_ascii=False)
        )
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            return json.loads(text) if text else entities
        except (requests.RequestException, ValueError, json.JSONDecodeError):
            self.is_available = False
            return entities

    def validate_anonymization_coherence(
        self, original_text: str, anonymized_text: str, entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate anonymization coherence using the Ollama server."""
        if not self.is_available:
            return {"coherent": True, "issues": ["Ollama server unavailable"]}

        prompt = self._load_coherence_prompt().format(
            original=original_text,
            anonymized=anonymized_text,
            entities=json.dumps(entities, ensure_ascii=False),
        )
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()
            if text:
                result = json.loads(text)
                if isinstance(result, dict):
                    return result
        except (requests.RequestException, ValueError, json.JSONDecodeError):
            pass

        self.is_available = False
        return {"coherent": True, "issues": ["Ollama server unavailable"]}

    def suggest_anonymization_improvements(
        self, text: str, entities: List[Dict[str, Any]]
    ) -> str:
        """Suggest improvements for anonymization.

        Returns a plain text message or a fallback note if the server is unavailable.
        """
        if not self.is_available:
            return "No suggestions: Ollama server unavailable."

        prompt = self._load_improvement_prompt().format(
            text=text, entities=json.dumps(entities, ensure_ascii=False)
        )
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
        except (requests.RequestException, ValueError, json.JSONDecodeError):
            self.is_available = False
            return "No suggestions: Ollama server unavailable."
