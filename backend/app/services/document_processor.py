import io
import logging
from typing import BinaryIO, Tuple, Dict, List
from docx import Document
from docx.shared import Inches
import PyPDF2
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import tempfile
import os

from .replacement_engine import IntelligentReplacementEngine

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
    
    def apply_intelligent_replacements(self, document: Document, entities_data: List[Dict], 
                                     groups_data: List[Dict] = None) -> bytes:
        """
        Applique les remplacements de manière intelligente en évitant les conflits
        """
        try:
            logger.info("🚀 Début de l'anonymisation intelligente")
            
            # Créer le moteur de remplacement
            engine = IntelligentReplacementEngine()
            
            # 1. Ajouter les groupes en premier (priorité haute)
            if groups_data:
                for group in groups_data:
                    group_replacement = group.get('replacement', 'GROUPE_X')
                    entity_ids = group.get('entity_ids', [])
                    
                    # Trouver les entités de ce groupe
                    for entity_data in entities_data:
                        if entity_data.get('selected') and entity_data.get('id') in entity_ids:
                            engine.add_replacement(
                                original=entity_data['text'],
                                replacement=group_replacement,
                                entity_id=entity_data['id'],
                                is_grouped=True,
                                group_id=group.get('id')
                            )
                            logger.info(f"Groupe ajouté: '{entity_data['text']}' -> '{group_replacement}'")
            
            # 2. Ajouter les entités individuelles (non groupées)
            for entity_data in entities_data:
                if (entity_data.get('selected') and 
                    not entity_data.get('is_grouped', False)):
                    
                    engine.add_replacement(
                        original=entity_data['text'],
                        replacement=entity_data['replacement'],
                        entity_id=entity_data['id'],
                        is_grouped=False
                    )
                    logger.info(f"Entité ajoutée: '{entity_data['text']}' -> '{entity_data['replacement']}'")
            
            # 3. Appliquer les remplacements à chaque partie du document
            self._apply_replacements_to_document(document, engine)
            
            # 4. Générer le rapport
            report = engine.get_replacement_report()
            logger.info(f"📊 Rapport d'anonymisation: {report['total_rules']} règles, "
                       f"{report['active_rules']} actives, {report['grouped_rules']} groupées")
            
            # 5. Sauvegarder en mémoire
            output_stream = io.BytesIO()
            document.save(output_stream)
            output_stream.seek(0)
            
            logger.info("✅ Anonymisation intelligente terminée")
            return output_stream.read()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'anonymisation intelligente: {e}")
            raise ValueError(f"Impossible d'appliquer l'anonymisation: {e}")
    
    def _apply_replacements_to_document(self, document: Document, engine: IntelligentReplacementEngine):
        """Applique les remplacements à toutes les parties du document"""
        replacements_count = 0
        
        # Remplacements dans les paragraphes
        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                original_text = paragraph.text
                new_text, stats = engine.apply_replacements(original_text)
                
                if new_text != original_text:
                    # Remplacer le texte du paragraphe
                    self._replace_paragraph_text(paragraph, new_text)
                    replacements_count += sum(stats.values())
        
        # Remplacements dans les tableaux
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        if paragraph.text.strip():
                            original_text = paragraph.text
                            new_text, stats = engine.apply_replacements(original_text)
                            
                            if new_text != original_text:
                                self._replace_paragraph_text(paragraph, new_text)
                                replacements_count += sum(stats.values())
        
        logger.info(f"✅ {replacements_count} remplacements appliqués dans le document")
    
    def _replace_paragraph_text(self, paragraph, new_text: str):
        """Remplace le texte d'un paragraphe en préservant le formatage"""
        # Vider le paragraphe
        for run in paragraph.runs:
            run.text = ""
        
        # Ajouter le nouveau texte
        if paragraph.runs:
            paragraph.runs[0].text = new_text
        else:
            paragraph.add_run(new_text)
    
    def apply_global_replacements(self, document: Document, replacements: dict) -> bytes:
        """
        Version simple pour compatibilité - utilise l'ancien système
        """
        try:
            # Convertir au nouveau format
            entities_data = []
            for original, replacement in replacements.items():
                entities_data.append({
                    'id': f'compat_{hash(original)}',
                    'text': original,
                    'replacement': replacement,
                    'selected': True,
                    'is_grouped': False
                })
            
            return self.apply_intelligent_replacements(document, entities_data)
            
        except Exception as e:
            logger.error(f"Erreur lors des remplacements globaux: {e}")
            raise ValueError(f"Impossible d'appliquer les remplacements: {e}")

# Instance globale
document_processor = DocumentProcessor()