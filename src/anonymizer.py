import re
import os
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from io import BytesIO

# Imports pour le traitement de documents
try:
    import pdfplumber
    from pdf2docx import parse as pdf2docx_parse
    from docx import Document
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PDF support disabled. Install pdfplumber and pdf2docx for full functionality.")

# Imports pour l'IA (optionnel)
try:
    from transformers import pipeline
    AI_SUPPORT = True
except ImportError:
    AI_SUPPORT = False
    logging.warning("AI support disabled. Install transformers for NER functionality.")

from .config import ENTITY_PATTERNS, ENTITY_COLORS, DEFAULT_REPLACEMENTS

@dataclass
class Entity:
    """Classe représentant une entité détectée"""
    id: str
    type: str
    value: str
    start: int
    end: int
    confidence: float = 1.0
    replacement: Optional[str] = None
    page: Optional[int] = None
    context: Optional[str] = None

class RegexAnonymizer:
    """Anonymiseur basé sur des expressions régulières"""
    
    def __init__(self):
        self.patterns = ENTITY_PATTERNS
        self.replacements = DEFAULT_REPLACEMENTS
    
    def detect_entities(self, text: str) -> List[Entity]:
        """Détecter les entités dans le texte avec des regex"""
        entities = []
        entity_id = 0
        
        for entity_type, pattern in self.patterns.items():
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            for match in compiled_pattern.finditer(text):
                entity = Entity(
                    id=f"entity_{entity_id}",
                    type=entity_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=1.0,
                    replacement=self.replacements.get(entity_type, f"[{entity_type}]")
                )
                entities.append(entity)
                entity_id += 1
        
        return entities
    
    def anonymize_text(self, text: str, entities: List[Entity]) -> str:
        """Anonymiser le texte en remplaçant les entités"""
        # Trier les entités par position (de la fin vers le début pour éviter les décalages)
        sorted_entities = sorted(entities, key=lambda x: x.start, reverse=True)
        
        anonymized_text = text
        for entity in sorted_entities:
            replacement = entity.replacement or f"[{entity.type}]"
            anonymized_text = (
                anonymized_text[:entity.start] + 
                replacement + 
                anonymized_text[entity.end:]
            )
        
        return anonymized_text

class AIAnonymizer:
    """Anonymiseur basé sur l'IA (NER)"""
    
    def __init__(self, model_name: str = "dbmdz/bert-large-cased-finetuned-conll03-english"):
        self.model_name = model_name
        self.nlp_pipeline = None
        self.regex_anonymizer = RegexAnonymizer()
        
        if AI_SUPPORT:
            try:
                self.nlp_pipeline = pipeline(
                    "ner", 
                    model=model_name, 
                    aggregation_strategy="simple",
                    device=-1  # CPU par défaut
                )
                logging.info(f"AI model loaded: {model_name}")
            except Exception as e:
                logging.error(f"Failed to load AI model: {e}")
                self.nlp_pipeline = None
    
    def detect_entities_ai(self, text: str, confidence_threshold: float = 0.7) -> List[Entity]:
        """Détecter les entités avec l'IA"""
        entities = []
        
        if not self.nlp_pipeline:
            logging.warning("AI pipeline not available, falling back to regex")
            return self.regex_anonymizer.detect_entities(text)
        
        try:
            # Détection NER
            ner_results = self.nlp_pipeline(text)
            entity_id = 0
            
            for result in ner_results:
                if result['score'] >= confidence_threshold:
                    # Mapping des labels NER vers nos types
                    entity_type = self._map_ner_label(result['entity_group'])
                    
                    entity = Entity(
                        id=f"ai_entity_{entity_id}",
                        type=entity_type,
                        value=result['word'],
                        start=result['start'],
                        end=result['end'],
                        confidence=result['score'],
                        replacement=DEFAULT_REPLACEMENTS.get(entity_type, f"[{entity_type}]")
                    )
                    entities.append(entity)
                    entity_id += 1
            
            # Combiner avec la détection regex pour les entités non couvertes par NER
            regex_entities = self.regex_anonymizer.detect_entities(text)
            
            # Éviter les doublons en vérifiant les chevauchements
            for regex_entity in regex_entities:
                is_duplicate = False
                for ai_entity in entities:
                    if (regex_entity.start >= ai_entity.start and 
                        regex_entity.end <= ai_entity.end):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    regex_entity.id = f"regex_{regex_entity.id}"
                    entities.append(regex_entity)
            
            return entities
            
        except Exception as e:
            logging.error(f"AI detection failed: {e}")
            return self.regex_anonymizer.detect_entities(text)
    
    def _map_ner_label(self, ner_label: str) -> str:
        """Mapper les labels NER vers nos types d'entités"""
        mapping = {
            'PER': 'PERSON',
            'PERSON': 'PERSON',
            'ORG': 'ORG', 
            'ORGANIZATION': 'ORG',
            'LOC': 'LOC',
            'LOCATION': 'LOC',
            'MISC': 'MISC'
        }
        return mapping.get(ner_label.upper(), ner_label.upper())

class DocumentProcessor:
    """Processeur de documents (PDF, DOCX)"""
    
    def __init__(self):
        self.supported_formats = ['.pdf', '.docx', '.doc']
    
    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, Dict]:
        """Extraire le texte d'un PDF"""
        if not PDF_SUPPORT:
            raise Exception("PDF support not available. Install pdfplumber and pdf2docx.")
        
        text_content = ""
        metadata = {"pages": 0, "format": "pdf"}
        
        try:
            with pdfplumber.open(file_path) as pdf:
                metadata["pages"] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_content += f"\n--- Page {page_num} ---\n"
                        text_content += page_text
                
            return text_content, metadata
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def extract_text_from_docx(self, file_path: str) -> Tuple[str, Dict]:
        """Extraire le texte d'un DOCX"""
        try:
            doc = Document(file_path)
            
            text_content = ""
            metadata = {"paragraphs": 0, "format": "docx"}
            
            # Extraction du texte des paragraphes
            for para in doc.paragraphs:
                if para.text.strip():
                    text_content += para.text + "\n"
                    metadata["paragraphs"] += 1
            
            # Extraction du texte des tableaux
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_content += cell.text + " "
                    text_content += "\n"
            
            # Extraction des en-têtes et pieds de page
            for section in doc.sections:
                if section.header:
                    for para in section.header.paragraphs:
                        if para.text.strip():
                            text_content += para.text + "\n"
                
                if section.footer:
                    for para in section.footer.paragraphs:
                        if para.text.strip():
                            text_content += para.text + "\n"
            
            return text_content, metadata
            
        except Exception as e:
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")
    
    def convert_pdf_to_docx(self, pdf_path: str, output_path: str) -> str:
        """Convertir un PDF en DOCX"""
        if not PDF_SUPPORT:
            raise Exception("PDF support not available.")
        
        try:
            pdf2docx_parse(pdf_path, output_path)
            return output_path
        except Exception as e:
            raise Exception(f"Failed to convert PDF to DOCX: {str(e)}")
    
    def process_file(self, file_path: str) -> Tuple[str, Dict]:
        """Traiter un fichier et extraire le texte"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return self.extract_text_from_docx(file_path)
        else:
            raise Exception(f"Unsupported file format: {file_ext}")

class DocumentAnonymizer:
    """Classe principale pour l'anonymisation de documents"""
    
    def __init__(self):
        self.regex_anonymizer = RegexAnonymizer()
        self.ai_anonymizer = AIAnonymizer() if AI_SUPPORT else None
        self.document_processor = DocumentProcessor()
        self.temp_dir = tempfile.mkdtemp()
    
    def process_document(self, file_path: str, mode: str = "regex", confidence: float = 0.7) -> Dict[str, Any]:
        """Traiter un document complet"""
        try:
            # Extraction du texte
            text, metadata = self.document_processor.process_file(file_path)
            
            if not text.strip():
                return {
                    "status": "error",
                    "error": "No text content found in document"
                }
            
            # Détection des entités
            if mode == "ai" and self.ai_anonymizer:
                entities = self.ai_anonymizer.detect_entities_ai(text, confidence)
            else:
                entities = self.regex_anonymizer.detect_entities(text)
            
            # Anonymisation du texte
            anonymized_text = self.regex_anonymizer.anonymize_text(text, entities)
            
            # Création du document anonymisé
            anonymized_path = self._create_anonymized_document(
                file_path, anonymized_text, metadata
            )
            
            return {
                "status": "success",
                "entities": [asdict(entity) for entity in entities],
                "text": text,
                "anonymized_text": anonymized_text,
                "anonymized_path": anonymized_path,
                "metadata": metadata,
                "mode": mode,
                "confidence": confidence
            }
            
        except Exception as e:
            logging.error(f"Document processing failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _create_anonymized_document(self, original_path: str, anonymized_text: str, metadata: Dict) -> str:
        """Créer le document anonymisé"""
        original_name = Path(original_path).name
        base_name = Path(original_path).stem
        
        # Création d'un nouveau document DOCX
        doc = Document()
        
        # Ajout d'un en-tête
        header = doc.sections[0].header
        header_para = header.paragraphs[0]
        header_para.text = "DOCUMENT ANONYMISÉ - Conforme RGPD"
        
        # Ajout du contenu anonymisé
        lines = anonymized_text.split('\n')
        for line in lines:
            if line.strip():
                doc.add_paragraph(line)
        
        # Ajout d'un pied de page avec métadonnées
        footer = doc.sections[0].footer
        footer_para = footer.paragraphs[0]
        footer_para.text = f"Anonymisé le {self._get_current_timestamp()} - Original: {original_name}"
        
        # Sauvegarde
        output_path = os.path.join(self.temp_dir, f"anonymized_{base_name}.docx")
        doc.save(output_path)
        
        return output_path
    
    def _get_current_timestamp(self) -> str:
        """Obtenir le timestamp actuel"""
        from datetime import datetime
        return datetime.now().strftime("%d/%m/%Y à %H:%M")
    
    def update_entity_replacement(self, entities: List[Dict], entity_id: str, new_replacement: str) -> List[Dict]:
        """Mettre à jour le remplacement d'une entité"""
        for entity in entities:
            if entity['id'] == entity_id:
                entity['replacement'] = new_replacement
                break
        return entities
    
    def regenerate_anonymized_text(self, original_text: str, entities: List[Dict]) -> str:
        """Régénérer le texte anonymisé avec les remplacements mis à jour"""
        # Convertir les dicts en objets Entity
        entity_objects = []
        for entity_dict in entities:
            entity = Entity(**entity_dict)
            entity_objects.append(entity)
        
        return self.regex_anonymizer.anonymize_text(original_text, entity_objects)
    
    def export_anonymized_document(self, original_path: str, entities: List[Dict], 
                                 options: Dict = None) -> str:
        """Exporter le document anonymisé avec options personnalisées"""
        options = options or {}
        
        try:
            # Traitement du document original
            text, metadata = self.document_processor.process_file(original_path)
            
            # Régénération avec les entités mises à jour
            anonymized_text = self.regenerate_anonymized_text(text, entities)
            
            # Création du document final
            doc = Document()
            
            # Options d'export
            if options.get('add_watermark', True):
                watermark_text = options.get('watermark_text', 'DOCUMENT ANONYMISÉ')
                header = doc.sections[0].header
                header_para = header.paragraphs[0]
                header_para.text = watermark_text
            
            # Contenu principal
            lines = anonymized_text.split('\n')
            for line in lines:
                if line.strip():
                    doc.add_paragraph(line)
            
            # Rapport d'audit
            if options.get('generate_report', False):
                doc.add_page_break()
                doc.add_heading('RAPPORT D\'AUDIT D\'ANONYMISATION', 1)
                
                doc.add_paragraph(f"Document original: {Path(original_path).name}")
                doc.add_paragraph(f"Date d'anonymisation: {self._get_current_timestamp()}")
                doc.add_paragraph(f"Nombre d'entités anonymisées: {len(entities)}")
                
                # Détail par type
                entity_types = {}
                for entity in entities:
                    entity_type = entity['type']
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                
                doc.add_heading('Répartition par type:', 2)
                for entity_type, count in entity_types.items():
                    doc.add_paragraph(f"- {entity_type}: {count} occurrence(s)")
            
            # Sauvegarde
            base_name = Path(original_path).stem
            output_path = os.path.join(self.temp_dir, f"final_anonymized_{base_name}.docx")
            doc.save(output_path)
            
            return output_path
            
        except Exception as e:
            logging.error(f"Export failed: {str(e)}")
            raise Exception(f"Failed to export document: {str(e)}")
    
    def cleanup(self):
        """Nettoyer les fichiers temporaires"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

class EntityStatistics:
    """Classe pour les statistiques sur les entités"""
    
    @staticmethod
    def get_entity_stats(entities: List[Dict]) -> Dict[str, Any]:
        """Calculer les statistiques des entités"""
        if not entities:
            return {
                "total": 0,
                "by_type": {},
                "confidence_stats": {},
                "coverage": 0.0
            }
        
        total = len(entities)
        by_type = {}
        confidences = []
        
        for entity in entities:
            entity_type = entity['type']
            by_type[entity_type] = by_type.get(entity_type, 0) + 1
            
            if 'confidence' in entity:
                confidences.append(entity['confidence'])
        
        confidence_stats = {}
        if confidences:
            confidence_stats = {
                "min": min(confidences),
                "max": max(confidences),
                "avg": sum(confidences) / len(confidences),
                "high_confidence": len([c for c in confidences if c >= 0.8])
            }
        
        return {
            "total": total,
            "by_type": by_type,
            "confidence_stats": confidence_stats,
            "most_common_type": max(by_type, key=by_type.get) if by_type else None
        }
    
    @staticmethod
    def generate_summary_report(entities: List[Dict], metadata: Dict) -> str:
        """Générer un rapport de synthèse"""
        stats = EntityStatistics.get_entity_stats(entities)
        
        report = f"""
RAPPORT DE SYNTHÈSE D'ANONYMISATION
===================================

Document traité: {metadata.get('format', 'inconnu').upper()}
Pages/Paragraphes: {metadata.get('pages', metadata.get('paragraphs', 'N/A'))}

STATISTIQUES D'ANONYMISATION:
- Total d'entités détectées: {stats['total']}
- Type le plus fréquent: {stats['most_common_type'] or 'N/A'}

RÉPARTITION PAR TYPE:
"""
        
        for entity_type, count in stats['by_type'].items():
            percentage = (count / stats['total']) * 100 if stats['total'] > 0 else 0
            report += f"- {entity_type}: {count} ({percentage:.1f}%)\n"
        
        if stats['confidence_stats']:
            conf_stats = stats['confidence_stats']
            report += f"""
STATISTIQUES DE CONFIANCE:
- Confiance moyenne: {conf_stats['avg']:.2f}
- Confiance minimale: {conf_stats['min']:.2f}
- Confiance maximale: {conf_stats['max']:.2f}
- Entités haute confiance (≥80%): {conf_stats['high_confidence']}
"""
        
        return report