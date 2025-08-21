"""
Tests unitaires pour l'anonymiseur de documents
"""

import unittest
from unittest import mock
import tempfile
import os
from pathlib import Path
import sys

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.anonymizer import RegexAnonymizer, DocumentAnonymizer, Entity
from src.entity_manager import EntityManager
from src.utils import format_file_size, validate_entities

class TestRegexAnonymizer(unittest.TestCase):
    """Tests pour l'anonymiseur Regex"""
    
    def setUp(self):
        self.anonymizer = RegexAnonymizer()
    
    def test_email_detection(self):
        """Test de détection d'emails"""
        text = "Contactez-moi à john.doe@example.com ou admin@test.fr"
        entities = self.anonymizer.detect_entities(text)
        
        email_entities = [e for e in entities if e.type == "EMAIL"]
        self.assertEqual(len(email_entities), 2)
        self.assertEqual(email_entities[0].value, "john.doe@example.com")
        self.assertEqual(email_entities[1].value, "admin@test.fr")
    
    def test_phone_detection(self):
        """Test de détection de téléphones"""
        text = "Appelez le 01 23 45 67 89 ou 0987654321"
        entities = self.anonymizer.detect_entities(text)
        
        phone_entities = [e for e in entities if e.type == "PHONE"]
        self.assertGreaterEqual(len(phone_entities), 1)
    
    def test_date_detection(self):
        """Test de détection de dates"""
        text = "Signé le 15/03/2024 et expirant le 31/12/2025"
        entities = self.anonymizer.detect_entities(text)
        
        date_entities = [e for e in entities if e.type == "DATE"]
        self.assertEqual(len(date_entities), 2)
    
    def test_iban_detection(self):
        """Test de détection d'IBAN"""
        text = "Virement sur FR1420041010050500013M02606"
        entities = self.anonymizer.detect_entities(text)
        
        iban_entities = [e for e in entities if e.type == "IBAN"]
        self.assertEqual(len(iban_entities), 1)
    
    def test_anonymization(self):
        """Test d'anonymisation complète"""
        text = "Contact: john@example.com, tél: 01 23 45 67 89"
        entities = self.anonymizer.detect_entities(text)
        anonymized = self.anonymizer.anonymize_text(text, entities)
        
        self.assertNotIn("john@example.com", anonymized)
        self.assertNotIn("01 23 45 67 89", anonymized)
        self.assertIn("[EMAIL]", anonymized)
        self.assertIn("[PHONE]", anonymized)

class TestEntityManager(unittest.TestCase):
    """Tests pour le gestionnaire d'entités"""
    
    def setUp(self):
        self.manager = EntityManager()
    
    def test_add_entity(self):
        """Test d'ajout d'entité"""
        entity_data = {
            "type": "EMAIL",
            "value": "test@example.com",
            "start": 0,
            "end": 16
        }
        
        entity_id = self.manager.add_entity(entity_data)
        self.assertIsNotNone(entity_id)
        
        entity = self.manager.get_entity_by_id(entity_id)
        self.assertEqual(entity["value"], "test@example.com")
    
    def test_update_entity(self):
        """Test de mise à jour d'entité"""
        entity_data = {
            "type": "EMAIL", 
            "value": "test@example.com",
            "start": 0,
            "end": 16
        }
        
        entity_id = self.manager.add_entity(entity_data)
        success = self.manager.update_entity(entity_id, {
            "replacement": "[EMAIL_PERSONNALISÉ]"
        })
        
        self.assertTrue(success)
        entity = self.manager.get_entity_by_id(entity_id)
        self.assertEqual(entity["replacement"], "[EMAIL_PERSONNALISÉ]")
    
    def test_delete_entity(self):
        """Test de suppression d'entité"""
        entity_data = {
            "type": "EMAIL",
            "value": "test@example.com", 
            "start": 0,
            "end": 16
        }
        
        entity_id = self.manager.add_entity(entity_data)
        success = self.manager.delete_entity(entity_id)
        
        self.assertTrue(success)
        entity = self.manager.get_entity_by_id(entity_id)
        self.assertIsNone(entity)
    
    def test_create_group(self):
        """Test de création de groupe"""
        group_id = self.manager.create_group(
            "Emails test",
            "Groupe de test pour les emails"
        )
        
        self.assertIsNotNone(group_id)
        group = self.manager.get_group_by_id(group_id)
        self.assertEqual(group["name"], "Emails test")
    
    def test_group_entities(self):
        """Test de groupement d'entités"""
        # Créer des entités
        entity1_id = self.manager.add_entity({
            "type": "EMAIL",
            "value": "user1@example.com",
            "start": 0,
            "end": 17
        })
        
        entity2_id = self.manager.add_entity({
            "type": "EMAIL", 
            "value": "user2@example.com",
            "start": 18,
            "end": 35
        })
        
        # Créer un groupe
        group_id = self.manager.create_group("Emails")
        
        # Ajouter les entités au groupe
        self.manager.add_entity_to_group(group_id, entity1_id)
        self.manager.add_entity_to_group(group_id, entity2_id)
        
        # Vérifier
        entities_in_group = self.manager.get_entities_in_group(group_id)
        self.assertEqual(len(entities_in_group), 2)
    
    def test_undo_functionality(self):
        """Test de la fonctionnalité d'annulation"""
        # Ajouter une entité
        entity_data = {
            "type": "EMAIL",
            "value": "test@example.com",
            "start": 0, 
            "end": 16
        }
        
        entity_id = self.manager.add_entity(entity_data)
        self.assertEqual(len(self.manager.entities), 1)
        
        # Annuler l'ajout
        success = self.manager.undo_last_action()
        self.assertTrue(success)
        self.assertEqual(len(self.manager.entities), 0)
    
    def test_filter_entities(self):
        """Test de filtrage d'entités"""
        # Ajouter plusieurs entités
        self.manager.add_entity({
            "type": "EMAIL",
            "value": "user@example.com",
            "start": 0,
            "end": 16,
            "confidence": 0.9
        })
        
        self.manager.add_entity({
            "type": "PHONE", 
            "value": "0123456789",
            "start": 17,
            "end": 27,
            "confidence": 0.6
        })
        
        # Filtrer par type
        emails = self.manager.filter_entities({"types": ["EMAIL"]})
        self.assertEqual(len(emails), 1)
        
        # Filtrer par confiance
        high_conf = self.manager.filter_entities({"min_confidence": 0.8})
        self.assertEqual(len(high_conf), 1)

class TestUtils(unittest.TestCase):
    """Tests pour les fonctions utilitaires"""
    
    def test_format_file_size(self):
        """Test de formatage de taille de fichier"""
        self.assertEqual(format_file_size(0), "0 B")
        self.assertEqual(format_file_size(1024), "1.0 KB")
        self.assertEqual(format_file_size(1024*1024), "1.0 MB")
        self.assertEqual(format_file_size(1024*1024*1024), "1.0 GB")
    
    def test_validate_entities(self):
        """Test de validation d'entités"""
        # Entités valides
        valid_entities = [
            {
                "id": "1",
                "type": "EMAIL",
                "value": "test@example.com", 
                "start": 0,
                "end": 16,
                "confidence": 0.9
            }
        ]
        
        errors = validate_entities(valid_entities)
        self.assertEqual(len(errors), 0)
        
        # Entités invalides
        invalid_entities = [
            {
                "type": "EMAIL",
                "value": "test@example.com",
                "start": 10,
                "end": 5  # Fin avant début
            }
        ]
        
        errors = validate_entities(invalid_entities)
        self.assertGreater(len(errors), 0)

class TestDocumentAnonymizer(unittest.TestCase):
    """Tests pour l'anonymiseur de documents"""
    
    def setUp(self):
        self.anonymizer = DocumentAnonymizer()
    
    def test_create_anonymized_document(self):
        """Test de création de document anonymisé"""
        test_text = "Email: test@example.com, Phone: 01 23 45 67 89"
        metadata = {"format": "test", "pages": 1}
        
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_text)
            temp_path = f.name
        
        try:
            result_path = self.anonymizer._create_anonymized_document(
                temp_path, 
                test_text.replace("test@example.com", "[EMAIL]").replace("01 23 45 67 89", "[PHONE]"),
                metadata
            )
            
            self.assertTrue(os.path.exists(result_path))
            
            # Nettoyer
            os.unlink(result_path)
            
        finally:
            os.unlink(temp_path)

    def test_conflict_resolution_delegates(self):
        """Vérifie que la résolution de conflits utilise l'aide dédiée"""
        e1 = Entity(
            id="1",
            type="EMAIL",
            value="john@example.com",
            start=0,
            end=16,
            confidence=0.9,
            method="regex",
        )
        e2 = Entity(
            id="2",
            type="PERSON",
            value="john",
            start=0,
            end=4,
            confidence=0.99,
            method="spacy",
        )

        original = self.anonymizer._resolve_conflict
        with mock.patch.object(self.anonymizer, "_resolve_conflict", wraps=original) as mocked:
            resolved = self.anonymizer._resolve_entity_conflicts([e1, e2])
            mocked.assert_called_once()

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].type, "EMAIL")

class TestIntegration(unittest.TestCase):
    """Tests d'intégration"""
    
    def test_full_workflow(self):
        """Test du workflow complet"""
        # 1. Créer un anonymiseur
        anonymizer = RegexAnonymizer()
        entity_manager = EntityManager()
        
        # 2. Texte de test
        text = """
        Contrat entre Jean Dupont (jean.dupont@email.com) 
        et Marie Martin (marie.martin@example.fr).
        Téléphone: 01 23 45 67 89
        Date: 15/03/2024
        IBAN: FR1420041010050500013M02606
        """
        
        # 3. Détection d'entités
        entities = anonymizer.detect_entities(text)
        self.assertGreater(len(entities), 0)
        
        # 4. Ajouter les entités au gestionnaire
        for entity in entities:
            entity_dict = {
                "id": entity.id,
                "type": entity.type,
                "value": entity.value,
                "start": entity.start,
                "end": entity.end,
                "confidence": entity.confidence
            }
            entity_manager.add_entity(entity_dict)
        
        # 5. Créer des groupes
        email_group = entity_manager.create_group("Emails", "Adresses email")
        phone_group = entity_manager.create_group("Téléphones", "Numéros de téléphone")
        
        # 6. Assigner les entités aux groupes
        for entity in entity_manager.entities:
            if entity["type"] == "EMAIL":
                entity_manager.add_entity_to_group(email_group, entity["id"])
            elif entity["type"] == "PHONE":
                entity_manager.add_entity_to_group(phone_group, entity["id"])
        
        # 7. Anonymiser le texte
        anonymized = anonymizer.anonymize_text(text, entities)
        
        # 8. Vérifications finales
        self.assertNotIn("jean.dupont@email.com", anonymized)
        self.assertNotIn("marie.martin@example.fr", anonymized)
        self.assertNotIn("01 23 45 67 89", anonymized)
        self.assertIn("[EMAIL]", anonymized)
        self.assertIn("[PHONE]", anonymized)
        
        # 9. Statistiques
        stats = entity_manager.get_statistics()
        self.assertGreater(stats["total_entities"], 0)
        self.assertGreater(len(stats["entity_types"]), 0)

if __name__ == "__main__":
    # Configuration des tests
    unittest.main(verbosity=2)
