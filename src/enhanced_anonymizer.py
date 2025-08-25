from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from .anonymizer import RegexAnonymizer, AIAnonymizer, DocumentProcessor, Entity
from .legal_normalizer import LegalEntityNormalizer
from .ollama_analyzer import OllamaLegalAnalyzer
from .config import LegalTemplates


class EnhancedDocumentAnonymizer:
    """High level anonymizer orchestrating multiple components.

    This class wires together regex based anonymization, optional AI based
    entity detection, a local Ollama server for legal reasoning and the
    domain specific :class:`LegalTemplates` registry.  The goal is to expose a
    simple ``process_legal_document`` method performing all the required steps
    to anonymize a document while producing a small compliance report.

    The implementation favours robustness.  Each optional dependency
    (transformer models or an Ollama server) is used when available and a
    graceful degradation path is ensured otherwise.
    """

    def __init__(
        self,
        *,
        use_ai: bool = True,
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "llama3",
    ) -> None:
        # Core components
        self.regex_anonymizer = RegexAnonymizer(use_french_patterns=True)
        self.document_processor = DocumentProcessor()
        self.normalizer = LegalEntityNormalizer()

        # Optional AI based NER
        self.ai_anonymizer: Optional[AIAnonymizer]
        if use_ai:
            try:
                self.ai_anonymizer = AIAnonymizer()
            except Exception:  # pragma: no cover - any failure disables AI
                logging.warning("AI anonymizer unavailable, falling back to regex only")
                self.ai_anonymizer = None
        else:
            self.ai_anonymizer = None

        # Ollama server for document analysis
        self.ollama = OllamaLegalAnalyzer(base_url=ollama_base_url, model=ollama_model)

    # ------------------------------------------------------------------
    def _extract_text(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text and metadata from ``file_path``."""
        return self.document_processor.process_file(file_path)

    def _detect_document_type(self, text: str) -> str:
        """Detect the document type using the Ollama analyzer if available."""
        return self.ollama.detect_document_type(text)

    def _select_template(self, text: str, doc_type: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Select the most appropriate :class:`LegalTemplates` entry."""
        name: Optional[str] = None
        tpl: Optional[Dict[str, Any]] = None

        if doc_type and doc_type != "unknown":
            tpl = LegalTemplates.get(doc_type)
            if tpl:
                name = doc_type

        if tpl is None:
            name, tpl = LegalTemplates.detect(text)

        return name, tpl

    def _detect_entities(self, text: str) -> List[Entity]:
        """Run regex detection and optionally AI NER on ``text``."""
        entities = self.regex_anonymizer.detect_entities(text)

        # Harmonise some French specific labels with canonical ones so that
        # downstream processing can reuse the "PERSON" and "ORG" logic.
        for e in entities:
            if e.type in {"PERSON_WITH_TITLE", "PERSON_FR"}:
                e.type = "PERSON"
            elif e.type in {"FRENCH_COMPANY", "ORG_FR"}:
                e.type = "ORG"

        if self.ai_anonymizer and getattr(self.ai_anonymizer, "model_loaded", False):
            try:
                ai_entities = self.ai_anonymizer.detect_entities_ai(text)
            except Exception:  # pragma: no cover - failure is non fatal
                ai_entities = []
            # Merge AI entities while avoiding duplicates
            existing = {(e.start, e.end, e.type) for e in entities}
            for ent in ai_entities:
                key = (ent.start, ent.end, ent.type)
                if key not in existing:
                    entities.append(ent)
        return entities

    def _canonicalize_entities(self, entities: List[Entity]) -> List[Dict[str, Any]]:
        """Return a serialisable representation of ``entities`` with canonical forms."""
        serialised: List[Dict[str, Any]] = []
        for ent in entities:
            data = asdict(ent)
            if ent.type == "PERSON":
                data["canonical"] = self.normalizer.normalize_person_name(ent.value).canonical
            else:
                data["canonical"] = ent.value
            serialised.append(data)
        return serialised

    def _validate_context(self, original: str, anonymized: str, entities: List[Entity]) -> Dict[str, Any]:
        """Validate anonymization using heuristic checks."""
        return self.regex_anonymizer._validate_anonymization(original, anonymized, entities)

    def _coherence_report(self, original: str, anonymized: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ask the Ollama server to check anonymization coherence."""
        return self.ollama.validate_anonymization_coherence(
            original, anonymized, [{"text": e["value"], "label": e["type"]} for e in entities]
        )

    # ------------------------------------------------------------------
    def process_legal_document(self, file_path: str) -> Dict[str, Any]:
        """Full processing pipeline for a legal document.

        Parameters
        ----------
        file_path:
            Path to the document to anonymize.  Supported formats mirror the
            :class:`DocumentProcessor` capabilities.

        Returns
        -------
        dict
            A dictionary containing the original text, anonymized text, list of
            entities and a compliance report.
        """

        text, metadata = self._extract_text(file_path)

        # Document classification and template selection
        doc_type = self._detect_document_type(text)
        template_name, template_cfg = self._select_template(text, doc_type)

        # Entity detection and canonicalisation
        entities = self._detect_entities(text)
        serialised_entities = self._canonicalize_entities(entities)

        # Anonymization
        anonymized_text, mapping = self.regex_anonymizer.anonymize_text(text, entities)

        # Validation and coherence checks
        validation = self._validate_context(text, anonymized_text, entities)
        coherence = self._coherence_report(text, anonymized_text, serialised_entities)

        # Build compliance report
        counts: Dict[str, int] = {}
        for ent in serialised_entities:
            counts[ent["type"]] = counts.get(ent["type"], 0) + 1

        compliance_report = {
            "document_type": doc_type,
            "template": template_name,
            "entity_counts": counts,
            "validation": validation,
            "coherence": coherence,
        }

        return {
            "text": text,
            "anonymized_text": anonymized_text,
            "entities": serialised_entities,
            "mapping": mapping,
            "compliance_report": compliance_report,
            "metadata": metadata,
        }
