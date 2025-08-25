import unittest

from src.ollama_analyzer import OllamaLegalAnalyzer


class TestOllamaAnalyzerFallback(unittest.TestCase):
    def test_fallbacks_when_server_unavailable(self):
        analyzer = OllamaLegalAnalyzer(base_url="http://localhost:1")
        self.assertFalse(analyzer.is_available)

        entities = [{"text": "John", "label": "PERSON"}]
        self.assertEqual(analyzer.detect_document_type("foo"), "unknown")
        self.assertEqual(analyzer.enhance_entity_detection("foo", entities), entities)

        coherence = analyzer.validate_anonymization_coherence("a", "b", entities)
        self.assertTrue(coherence["coherent"])
        self.assertIn("Ollama server unavailable", coherence["issues"][0])

        suggestion = analyzer.suggest_anonymization_improvements("foo", entities)
        self.assertEqual(
            suggestion, "No suggestions: Ollama server unavailable."
        )


if __name__ == "__main__":
    unittest.main()
