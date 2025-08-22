import unittest

from src.legal_normalizer import LegalEntityNormalizer


class TestLegalEntityNormalizer(unittest.TestCase):
    def setUp(self) -> None:
        self.normalizer = LegalEntityNormalizer()

    def test_normalize_person_name(self) -> None:
        data = self.normalizer.normalize_person_name("Mr Jean de La Fontaine")
        self.assertEqual(data.canonical, "jean de la fontaine")
        self.assertEqual(data.first_names, ["jean"])
        self.assertEqual(data.last_name, "fontaine")
        self.assertEqual(data.particles, ["de", "la"])

    def test_compute_similarity_score(self) -> None:
        score = self.normalizer.compute_similarity_score("Mme Dupont", "Dupont")
        self.assertGreater(score, 0.9)
        self.assertLess(
            self.normalizer.compute_similarity_score("Dupont", "Martin"), 0.5
        )

    def test_find_canonical_match(self) -> None:
        candidates = ["Jean de La Fontaine", "Paul Valery"]
        match = self.normalizer.find_canonical_match(
            "M. Jean de la Fontaine", candidates
        )
        self.assertIsNotNone(match)
        self.assertEqual(match.canonical, "jean de la fontaine")

    def test_register_entity_variant(self) -> None:
        self.normalizer.register_entity_variant("Jean Dupont", "M. Jean Dupont")
        key = self.normalizer.normalize_person_name("Jean Dupont").canonical
        self.assertIn("M. Jean Dupont", self.normalizer.registry.get(key, set()))

