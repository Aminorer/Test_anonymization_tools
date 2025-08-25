import pytest

from src.enhanced_anonymizer import EnhancedDocumentAnonymizer


def test_process_pipeline_graceful_ollama_unavailable(tmp_path):
    # Create a simple text file containing identifiable information
    content = "M. Jean Dupont a écrit à jean.dupont@example.com"
    file_path = tmp_path / "sample.txt"
    file_path.write_text(content, encoding="utf-8")

    anonymizer = EnhancedDocumentAnonymizer()
    result = anonymizer.process_legal_document(str(file_path))

    # Ensure email has been anonymized
    assert "[EMAIL_" in result["anonymized_text"]

    # Ollama is not expected to be available in tests; document type should be unknown
    assert result["compliance_report"]["document_type"] in {"unknown", None, ""}

    # Canonical form for the detected person should be normalized
    persons = [e for e in result["entities"] if e["type"] == "PERSON"]
    if persons:
        assert persons[0]["canonical"] == "jean dupont"

    # Compliance report should contain entity counts
    assert result["compliance_report"]["entity_counts"]["EMAIL"] == 1
