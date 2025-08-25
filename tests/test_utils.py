import os
import unittest

from src.utils import normalize_name, similarity, get_similarity_weights


class TestNormalizeName(unittest.TestCase):
    """Tests for the normalize_name utility."""

    def test_remove_title_and_first_name(self):
        self.assertEqual(normalize_name("Dr Jean Dûpont"), "dupont")

    def test_particles_are_preserved(self):
        self.assertEqual(normalize_name("Mme de La Tour"), "de la tour")

    def test_env_override_titles(self):
        os.environ["ANONYMIZER_TITLES"] = "sir"
        try:
            self.assertEqual(normalize_name("Sir John Doe"), "doe")
        finally:
            del os.environ["ANONYMIZER_TITLES"]


class TestSimilarity(unittest.TestCase):
    def test_env_threshold(self):
        os.environ["ANONYMIZER_SIMILARITY_THRESHOLD"] = "0.5"
        try:
            self.assertTrue(similarity("Jean", "Jean"))
            self.assertFalse(similarity("Jean", "Paul"))
        finally:
            del os.environ["ANONYMIZER_SIMILARITY_THRESHOLD"]

    def test_env_weights(self):
        os.environ["ANONYMIZER_SIMILARITY_WEIGHTS"] = "levenshtein=1,jaccard=0,phonetic=0"
        try:
            weights = get_similarity_weights()
            self.assertEqual(weights["levenshtein"], 1.0)
            self.assertAlmostEqual(sum(weights.values()), 1.0)
        finally:
            del os.environ["ANONYMIZER_SIMILARITY_WEIGHTS"]

