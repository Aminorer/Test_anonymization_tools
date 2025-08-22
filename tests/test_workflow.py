import os
import tempfile
import unittest
import sys
from pathlib import Path

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.anonymizer import DocumentAnonymizer
from docx import Document


class TestWorkflowIntegration(unittest.TestCase):
    """Test d'intégration simulant un upload et un export anonymisé"""

    def test_docx_upload_and_export(self):
        anonymizer = DocumentAnonymizer()
        doc = Document()
        doc.add_paragraph("Email: workflow@example.com")

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            doc.save(tmp.name)
            docx_path = tmp.name

        try:
            result = anonymizer.process_document(docx_path, mode="regex")
            self.assertEqual(result["status"], "success")

            export_path = anonymizer.export_anonymized_document(
                docx_path, result["entities"], {"format": "txt"}
            )
            self.assertTrue(os.path.exists(export_path))

            with open(export_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("[EMAIL_1]", content)
            self.assertNotIn("workflow@example.com", content)
        finally:
            os.unlink(docx_path)
            if os.path.exists(result.get("anonymized_path", "")):
                os.unlink(result["anonymized_path"])
            if 'export_path' in locals() and os.path.exists(export_path):
                os.unlink(export_path)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
