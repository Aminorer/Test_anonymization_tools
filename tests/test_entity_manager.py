import unittest
import sys
from pathlib import Path

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.entity_manager import EntityManager


class TestGroupManagement(unittest.TestCase):
    """Tests pour la gestion des groupes dans EntityManager"""

    def setUp(self):
        self.manager = EntityManager()

    def test_create_update_delete_group(self):
        """Création, mise à jour puis suppression d'un groupe"""
        group_id = self.manager.create_group("Test", "desc")
        self.assertIsNotNone(group_id)
        group = self.manager.get_group_by_id(group_id)
        self.assertEqual(group["name"], "Test")

        updated = self.manager.update_group(group_id, {"description": "new"})
        self.assertTrue(updated)
        self.assertEqual(self.manager.get_group_by_id(group_id)["description"], "new")

        deleted = self.manager.delete_group(group_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.manager.get_group_by_id(group_id))

    def test_filter_entities_by_group(self):
        """Filtrage d'entités par identifiant de groupe"""
        group_id = self.manager.create_group("Emails")
        e1 = self.manager.add_entity({"type": "EMAIL", "value": "a@b.com", "start": 0, "end": 7})
        e2 = self.manager.add_entity({"type": "EMAIL", "value": "c@d.com", "start": 8, "end": 15})
        self.manager.add_entity_to_group(group_id, e1)
        results = self.manager.filter_entities({"group_id": group_id})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], e1)

    def test_get_grouped_entities(self):
        """Vérifie la création correcte des groupes d'entités."""
        # Deux entités partageant le même jeton de remplacement
        self.manager.add_entity(
            {"type": "PERSON", "value": "Alice", "start": 0, "end": 5, "replacement": "[PERSON_1]"}
        )
        self.manager.add_entity(
            {"type": "PERSON", "value": "Bob", "start": 6, "end": 9, "replacement": "[PERSON_1]"}
        )
        # Réutilisation du même jeton pour une autre occurrence de "Alice"
        self.manager.add_entity(
            {"type": "PERSON", "value": "Alice", "start": 10, "end": 15, "replacement": "[PERSON_1]"}
        )
        # Entité avec un jeton différent
        self.manager.add_entity(
            {"type": "ORG", "value": "Acme", "start": 20, "end": 24, "replacement": "[ORG_1]"}
        )

        grouped = self.manager.get_grouped_entities()

        # Deux groupes distincts attendus
        self.assertEqual(len(grouped), 2)

        person_group = grouped.get("PERSON_1")
        self.assertIsNotNone(person_group)
        self.assertEqual(person_group["total_occurrences"], 3)

        # Vérifie les variantes et leurs positions
        alice = person_group["variants"].get("Alice")
        self.assertEqual(alice["count"], 2)
        self.assertEqual(
            alice["positions"], [{"start": 0, "end": 5}, {"start": 10, "end": 15}]
        )

        bob = person_group["variants"].get("Bob")
        self.assertEqual(bob["count"], 1)
        self.assertEqual(bob["positions"], [{"start": 6, "end": 9}])

        org_group = grouped.get("ORG_1")
        self.assertIsNotNone(org_group)
        self.assertEqual(org_group["total_occurrences"], 1)
        self.assertIn("Acme", org_group["variants"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
