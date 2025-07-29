# backend/app/services/document_processor.py
# REMPLACER SEULEMENT la méthode apply_global_replacements

import io
import logging
from typing import BinaryIO, Tuple, Dict
from docx import Document
from docx.shared import Inches
import PyPDF2
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import tempfile
import os
import re

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.supported_extensions = ['.pdf', '.docx']
        
    def process_uploaded_file(self, file_content: bytes, filename: str) -> Tuple[Document, str]:
        """
        Traite un fichier uploadé et retourne un document DOCX et son texte
        PDF → OCR si nécessaire → Texte → Conversion DOCX
        DOCX → Extraction texte direct → DOCX de travail
        """
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension not in self.supported_extensions:
            raise ValueError(f"Format de fichier non supporté: {file_extension}")
        
        if file_extension == '.pdf':
            return self._process_pdf(file_content)
        elif file_extension == '.docx':
            return self._process_docx(file_content)
        else:
            raise ValueError(f"Extension non gérée: {file_extension}")
    
    def _process_pdf(self, pdf_content: bytes) -> Tuple[Document, str]:
        """Traite un fichier PDF"""
        try:
            # Tenter extraction texte direct
            text = self._extract_text_from_pdf(pdf_content)
            
            # Si peu de texte extrait, utiliser OCR
            if len(text.strip()) < 100:
                logger.info("PDF scanné détecté, utilisation de l'OCR")
                text = self._ocr_pdf_with_tesseract(pdf_content)
            
            # Créer DOCX à partir du texte extrait
            docx_document = self._create_docx_from_text(text)
            
            return docx_document, text
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement PDF: {e}")
            raise ValueError(f"Impossible de traiter le fichier PDF: {e}")
    
    def _process_docx(self, docx_content: bytes) -> Tuple[Document, str]:
        """Traite un fichier DOCX"""
        try:
            # Charger le document DOCX
            docx_stream = io.BytesIO(docx_content)
            document = Document(docx_stream)
            
            # Extraire le texte
            text = self._extract_text_from_docx(document)
            
            return document, text
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement DOCX: {e}")
            raise ValueError(f"Impossible de traiter le fichier DOCX: {e}")
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extrait le texte d'un PDF"""
        text = ""
        try:
            pdf_stream = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            return text
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction PDF: {e}")
            return ""
    
    def _ocr_pdf_with_tesseract(self, pdf_content: bytes) -> str:
        """Effectue l'OCR sur un PDF scanné"""
        text = ""
        try:
            # Convertir PDF en images
            images = convert_from_bytes(pdf_content, dpi=300)
            
            for i, image in enumerate(images):
                logger.info(f"OCR sur la page {i+1}/{len(images)}")
                
                # Effectuer l'OCR avec Tesseract
                page_text = pytesseract.image_to_string(
                    image, 
                    lang='fra',
                    config='--psm 6'
                )
                text += page_text + "\n"
            
            return text
            
        except Exception as e:
            logger.error(f"Erreur lors de l'OCR: {e}")
            return ""
    
    def _extract_text_from_docx(self, document: Document) -> str:
        """Extrait le texte complet d'un document DOCX"""
        text_parts = []
        
        # Extraire le texte des paragraphes
        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
        
        # Extraire le texte des tableaux
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_parts.append(cell.text)
        
        return "\n".join(text_parts)
    
    def _create_docx_from_text(self, text: str) -> Document:
        """Crée un document DOCX à partir d'un texte"""
        document = Document()
        
        # Ajouter un titre
        title = document.add_heading('Document converti', 0)
        
        # Diviser le texte en paragraphes
        paragraphs = text.split('\n')
        
        for paragraph_text in paragraphs:
            if paragraph_text.strip():
                paragraph = document.add_paragraph(paragraph_text.strip())
        
        return document
    
    def apply_global_replacements(self, document: Document, replacements: dict) -> bytes:
        """
        🔧 REPLACEMENT ENGINE CORRIGÉ - Version 2.0
        
        PROBLÈME RÉSOLU : "Saïd OULHADJ" → "X X" (pas "X OULHADJ")
        
        Solution : Traitement char par char avec reconstruction des runs
        """
        try:
            logger.info(f"🔄 Application de {len(replacements)} remplacements avec engine v2.0")
            
            # ÉTAPE 1: Replacements dans les paragraphes principaux
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    self._replace_in_paragraph_v2(paragraph, replacements)
            
            # ÉTAPE 2: Replacements dans les tableaux
            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if paragraph.text.strip():
                                self._replace_in_paragraph_v2(paragraph, replacements)
            
            # ÉTAPE 3: Replacements dans headers/footers
            for section in document.sections:
                # Header
                if section.header:
                    for paragraph in section.header.paragraphs:
                        if paragraph.text.strip():
                            self._replace_in_paragraph_v2(paragraph, replacements)
                
                # Footer  
                if section.footer:
                    for paragraph in section.footer.paragraphs:
                        if paragraph.text.strip():
                            self._replace_in_paragraph_v2(paragraph, replacements)
            
            # Sauvegarder en mémoire
            output_stream = io.BytesIO()
            document.save(output_stream)
            output_stream.seek(0)
            
            logger.info("✅ Remplacements v2.0 appliqués avec succès")
            return output_stream.read()
            
        except Exception as e:
            logger.error(f"Erreur lors des remplacements v2.0: {e}")
            raise ValueError(f"Impossible d'appliquer les remplacements: {e}")

    def _replace_in_paragraph_v2(self, paragraph, replacements: Dict[str, str]):
        """
        🎯 ALGORITHME V2.0 - Résout le problème des runs fragmentés
        
        AVANT : "Saïd OULHADJ" → "X OULHADJ" (problème)
        APRÈS : "Saïd OULHADJ" → "X X" (corrigé)
        """
        try:
            full_text = paragraph.text
            if not full_text.strip():
                return
            
            # Vérifier si on a des remplacements à faire
            has_replacements = False
            modified_text = full_text
            
            for original, replacement in replacements.items():
                if original.lower() in full_text.lower():
                    has_replacements = True
                    # Remplacement insensible à la casse
                    pattern = re.compile(re.escape(original), re.IGNORECASE)
                    modified_text = pattern.sub(replacement, modified_text)
                    logger.debug(f"Remplacement: '{original}' → '{replacement}'")
            
            if not has_replacements:
                return
            
            # SOLUTION ROBUSTE : Remplacer tout le contenu du paragraphe
            # Effacer tous les runs existants
            for run in paragraph.runs:
                run.text = ""
            
            # Si on n'a plus de runs, en créer un
            if not paragraph.runs:
                paragraph.add_run("")
            
            # Mettre le texte modifié dans le premier run
            paragraph.runs[0].text = modified_text
            
            logger.debug(f"Paragraphe modifié: '{full_text}' → '{modified_text}'")
            
        except Exception as e:
            logger.debug(f"Erreur replacement paragraphe v2.0: {e}")

# Instance globale inchangée
document_processor = DocumentProcessor()