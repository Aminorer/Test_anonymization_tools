import unittest

from src.utils import normalize_name


class TestNormalizeName(unittest.TestCase):
    """Tests for the normalize_name utility."""

    def test_remove_title_and_first_name(self):
        self.assertEqual(normalize_name("Dr Jean Dûpont"), "dupont")

    def test_particles_are_preserved(self):
        self.assertEqual(normalize_name("Mme de La Tour"), "de la tour")

