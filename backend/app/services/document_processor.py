# backend/app/services/document_processor.py
# ⚠️ REMPLACER SEULEMENT LA MÉTHODE apply_global_replacements ET AJOUTER L'IMPORT

import io
import logging
import re  # ✅ AJOUTER CETTE LIGNE
from typing import BinaryIO, Tuple, Dict
from docx import Document
from docx.shared import Inches
import PyPDF2
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import tempfile
import os

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.supported_extensions = ['.pdf', '.docx']
    
    # ... GARDER TOUTES LES AUTRES MÉTHODES INCHANGÉES ...
    
    def apply_global_replacements(self, document: Document, replacements: dict) -> bytes:
        """
        🔧 REPLACEMENT ENGINE CORRIGÉ - Résout "Saïd OULHADJ" → "X X"
        """
        try:
            logger.info(f"🔄 Application de {len(replacements)} remplacements")
            
            # Replacements dans les paragraphes
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    self._replace_in_paragraph_fixed(paragraph, replacements)
            
            # Replacements dans les tableaux
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if paragraph.text.strip():
                                self._replace_in_paragraph_fixed(paragraph, replacements)
            
            # Sauvegarder en mémoire
            output_stream = io.BytesIO()
            document.save(output_stream)
            output_stream.seek(0)
            
            logger.info("✅ Remplacements appliqués avec succès")
            return output_stream.read()
            
        except Exception as e:
            logger.error(f"Erreur lors des remplacements: {e}")
            raise ValueError(f"Impossible d'appliquer les remplacements: {e}")

    def _replace_in_paragraph_fixed(self, paragraph, replacements: Dict[str, str]):
        """
        🎯 SOLUTION AU PROBLÈME : Remplacement complet sans fragmentation
        """
        try:
            full_text = paragraph.text
            if not full_text.strip():
                return
            
            # Appliquer tous les remplacements
            modified_text = full_text
            has_changes = False
            
            for original, replacement in replacements.items():
                if original.lower() in modified_text.lower():
                    # Remplacement insensible à la casse
                    pattern = re.compile(re.escape(original), re.IGNORECASE)
                    new_text = pattern.sub(replacement, modified_text)
                    if new_text != modified_text:
                        modified_text = new_text
                        has_changes = True
                        logger.debug(f"✅ '{original}' → '{replacement}'")
            
            if has_changes:
                # SOLUTION : Vider tous les runs et mettre le texte dans le premier
                for run in paragraph.runs:
                    run.text = ""
                
                if not paragraph.runs:
                    paragraph.add_run("")
                
                paragraph.runs[0].text = modified_text
                
        except Exception as e:
            logger.debug(f"Erreur replacement: {e}")

# Instance globale inchangée
document_processor = DocumentProcessor()