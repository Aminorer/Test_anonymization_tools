import os
import unittest

from src.utils import normalize_name, similarity


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

