import unittest
from unittest import mock
import json
import requests

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


class TestOllamaAnalyzerMockedResponses(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_get = mock.patch("requests.get").start()
        self.mock_get.return_value.raise_for_status.return_value = None

    def tearDown(self) -> None:
        mock.patch.stopall()

    def _make_response(self, payload):
        resp = mock.Mock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = payload
        return resp

    def test_successful_calls(self):
        mock_post = mock.patch("requests.post").start()
        mock_post.side_effect = [
            self._make_response({"response": "contract"}),
            self._make_response({
                "response": json.dumps([{"text": "John", "label": "PERSON"}])
            }),
            self._make_response(
                {
                    "response": json.dumps(
                        {"coherent": True, "issues": ["none"]}
                    )
                }
            ),
            self._make_response({"response": "All good."}),
        ]

        analyzer = OllamaLegalAnalyzer(base_url="http://mock")
        self.assertTrue(analyzer.is_available)

        doc_type = analyzer.detect_document_type("dummy")
        self.assertEqual(doc_type, "contract")

        entities = analyzer.enhance_entity_detection(
            "text", [{"text": "J", "label": "PERSON"}]
        )
        self.assertEqual(entities[0]["text"], "John")

        coherence = analyzer.validate_anonymization_coherence("a", "b", entities)
        self.assertTrue(coherence["coherent"])
        self.assertEqual(coherence["issues"], ["none"])

        suggestion = analyzer.suggest_anonymization_improvements("foo", entities)
        self.assertEqual(suggestion, "All good.")

    def test_failure_sets_unavailable(self):
        mock_post = mock.patch("requests.post").start()
        mock_post.side_effect = requests.RequestException

        analyzer = OllamaLegalAnalyzer(base_url="http://mock")
        self.assertTrue(analyzer.is_available)

        self.assertEqual(analyzer.detect_document_type("x"), "unknown")
        self.assertFalse(analyzer.is_available)
        self.assertEqual(
            analyzer.suggest_anonymization_improvements("foo", []),
            "No suggestions: Ollama server unavailable.",
        )


if __name__ == "__main__":
    unittest.main()
