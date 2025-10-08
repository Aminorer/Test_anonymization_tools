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
        self.assertEqual(group["token"], "[TEST]")

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

    def test_create_group_assigns_replacement(self):
        """Les entités sélectionnées doivent recevoir le nouveau token."""
        entity_id = self.manager.add_entity(
            {"type": "ORG", "value": "Acme", "start": 0, "end": 4}
        )
        group_id = self.manager.create_group("Mon Groupe", entity_ids=[entity_id])

        entity = self.manager.get_entity_by_id(entity_id)
        self.assertEqual(entity["replacement"], "[MON_GROUPE]")
        grouped = self.manager.get_grouped_entities()
        self.assertIn(group_id, grouped)
        self.assertEqual(grouped[group_id]["token"], "[MON_GROUPE]")

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

    def test_grouped_entities_use_total_occurrences_metadata(self):
        """Les occurrences agrégées doivent être prises en compte."""

        self.manager.add_entity(
            {
                "type": "EMAIL",
                "value": "john.doe@example.com",
                "start": 0,
                "end": 20,
                "replacement": "[EMAIL_1]",
                "total_occurrences": 3,
                "all_positions": [(0, 20), (30, 50), (60, 80)],
            }
        )

        grouped = self.manager.get_grouped_entities()

        self.assertIn("EMAIL_1", grouped)
        email_group = grouped["EMAIL_1"]
        self.assertEqual(email_group["total_occurrences"], 3)

        variant = email_group["variants"]["john.doe@example.com"]
        self.assertEqual(variant["count"], 3)
        self.assertEqual(len(variant["positions"]), 3)
        self.assertEqual(
            variant["positions"],
            [
                {"start": 0, "end": 20},
                {"start": 30, "end": 50},
                {"start": 60, "end": 80},
            ],
        )

    def test_update_group_from_grouped_entities(self):
        """Mettre à jour un groupe issu de get_grouped_entities met à jour les entités."""

        self.manager.add_entity(
            {
                "type": "ORGANISATION",
                "value": "Saint-Gobain",
                "start": 0,
                "end": 12,
                "replacement": "[ORGANISATION]",
            }
        )
        # Prime the cache to simulate l'utilisation via l'UI
        self.manager.get_grouped_entities()

        updated = self.manager.update_group(
            "ORGANISATION",
            {
                "token": "[Test]",
                "type": "ORG",
                "variants": {"Saint-Gobain": {"value": "Saint-Gobain", "count": 1, "positions": []}},
            },
        )

        self.assertTrue(updated)
        self.assertEqual(self.manager.entities[0]["replacement"], "[Test]")
        self.assertEqual(self.manager.entities[0]["type"], "ORG")
        self.assertEqual(self.manager.entities[0].get("variants"), ["Saint-Gobain"])

        grouped = self.manager.get_grouped_entities()
        self.assertIn("Test", grouped)
        self.assertEqual(grouped["Test"]["token"], "[Test]")

    def test_get_entity_conflicts(self):
        """Détection des conflits de chevauchement et de jeton."""

        e1 = self.manager.add_entity(
            {
                "type": "PERSON",
                "value": "Alice",
                "start": 0,
                "end": 5,
                "replacement": "[PERSON_1]",
            }
        )
        # Entité chevauchant la première
        self.manager.add_entity(
            {
                "type": "PERSON",
                "value": "Bob",
                "start": 3,
                "end": 8,
                "replacement": "[PERSON_2]",
            }
        )
        # Même valeur mais autre jeton
        self.manager.add_entity(
            {
                "type": "PERSON",
                "value": "Alice",
                "start": 10,
                "end": 15,
                "replacement": "[PERSON_3]",
            }
        )

        conflicts = self.manager.get_entity_conflicts()
        overlap_conflicts = [c for c in conflicts if c["type"] == "overlap"]
        token_conflicts = [c for c in conflicts if c["type"] == "token"]

        self.assertEqual(len(overlap_conflicts), 1)
        self.assertEqual(len(token_conflicts), 1)
        self.assertEqual(token_conflicts[0]["value"], "Alice")
        self.assertEqual(set(token_conflicts[0]["tokens"]), {"[PERSON_1]", "[PERSON_3]"})

    def test_split_and_merge_and_reassign(self):
        """Vérifie les helpers de résolution de conflits."""

        e1 = self.manager.add_entity(
            {
                "type": "PERSON",
                "value": "Alice",
                "start": 0,
                "end": 10,
                "replacement": "[PERSON_1]",
            }
        )
        e2 = self.manager.add_entity(
            {
                "type": "PERSON",
                "value": "Bob",
                "start": 11,
                "end": 20,
                "replacement": "[PERSON_2]",
            }
        )

        # Split first entity into two parts
        new_ids = self.manager.split_entity(
            e1,
            [
                {"start": 0, "end": 5, "value": "Al"},
                {"start": 5, "end": 10, "value": "ice"},
            ],
        )
        self.assertEqual(len(new_ids), 2)
        self.assertIsNone(self.manager.get_entity_by_id(e1))

        # Merge groups by token
        self.manager.merge_entity_groups("[PERSON_2]", "[PERSON_1]")
        replacements = {e["replacement"] for e in self.manager.entities}
        self.assertEqual(replacements, {"[PERSON_1]"})

        # Reassign variant
        self.manager.reassign_variant("ice", "[PERSON_1]", "[PERSON_3]")
        rep_map = {e["value"]: e["replacement"] for e in self.manager.entities}
        self.assertEqual(rep_map["ice"], "[PERSON_3]")
        self.assertEqual(rep_map["Al"], "[PERSON_1]")
        self.assertEqual(rep_map["Bob"], "[PERSON_1]")

    def test_delete_group_by_token(self):
        self.manager.add_entity({"type": "PERSON", "value": "Alice", "start": 0, "end": 5, "replacement": "[PERSON_1]"})
        self.manager.add_entity({"type": "PERSON", "value": "Bob", "start": 6, "end": 9, "replacement": "[PERSON_1]"})
        self.manager.add_entity({"type": "PERSON", "value": "Eve", "start": 10, "end": 13, "replacement": "[PERSON_2]"})
        self.manager.get_grouped_entities()
        deleted = self.manager.delete_group_by_token("PERSON_1")
        self.assertEqual(deleted, 2)
        self.assertEqual(len(self.manager.entities), 1)
        self.assertEqual(self.manager.entities[0]["value"], "Eve")
        self.assertIsNone(self.manager._grouped_entities_cache)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
