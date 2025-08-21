# 1. Nouveau fichier: streamlit_config.py
"""
Configuration spéciale pour éviter les conflits Streamlit/PyTorch
"""

import os
import sys
import logging

# Configuration pour éviter les conflits PyTorch/Streamlit
def setup_streamlit_environment():
    """Configurer l'environnement pour éviter les conflits"""
    
    # Désactiver les warnings PyTorch problématiques
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "1"
    
    # Configuration logging pour réduire le bruit
    logging.getLogger("transformers").setLevel(logging.ERROR)
    logging.getLogger("torch").setLevel(logging.ERROR)
    
    # Import conditionnel de PyTorch pour éviter les conflits
    try:
        import torch
        # Forcer PyTorch en mode CPU et single-thread
        torch.set_num_threads(1)
        if hasattr(torch, '_C') and hasattr(torch._C, '_disable_torch_function_mode'):
            torch._C._disable_torch_function_mode()
    except ImportError:
        pass
    except Exception as e:
        logging.warning(f"PyTorch configuration warning: {e}")

# 2. main.py modifié (début du fichier)
# Ajouter AVANT tous les autres imports

import os
import sys

# Configuration précoce pour éviter les conflits
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

# Import conditionnel et sécurisé de PyTorch
def safe_torch_import():
    try:
        import torch
        torch.set_num_threads(1)
        return True
    except Exception:
        return False

# Vérifier PyTorch avant Streamlit
TORCH_AVAILABLE = safe_torch_import()

import streamlit as st
import tempfile
import zipfile
from pathlib import Path
import json
from datetime import datetime
import time
import uuid

# Configuration de la page APRÈS la configuration PyTorch
st.set_page_config(
    page_title="Anonymiseur de Documents Juridiques",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 3. Modifications dans src/anonymizer.py (début du fichier)

import re
import os
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from io import BytesIO

# Configuration précoce pour éviter les conflits
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Imports pour le traitement de documents
try:
    import pdfplumber
    from pdf2docx import parse as pdf2docx_parse
    from docx import Document
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PDF support disabled. Install pdfplumber and pdf2docx for full functionality.")

# Imports pour l'IA avec gestion des conflits
try:
    # Configuration PyTorch avant import
    import torch
    torch.set_num_threads(1)
    
    from transformers import pipeline
    import transformers
    
    # Réduire les logs transformers
    transformers.logging.set_verbosity_error()
    
    AI_SUPPORT = True
    logging.info("AI support enabled with PyTorch")
except ImportError:
    AI_SUPPORT = False
    logging.warning("AI support disabled. Install transformers for NER functionality.")
except Exception as e:
    AI_SUPPORT = False
    logging.warning(f"AI support disabled due to configuration issue: {e}")

# Imports pour SpaCy (plus stable que transformers avec Streamlit)
try:
    import spacy
    SPACY_SUPPORT = True
    logging.info("SpaCy support enabled")
except ImportError:
    SPACY_SUPPORT = False
    logging.warning("SpaCy support disabled. Install spacy for better French NER.")

# 4. Alternative: Version simplifiée sans PyTorch (src/anonymizer_simple.py)

import re
import os
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# Imports pour le traitement de documents
try:
    import pdfplumber
    from pdf2docx import parse as pdf2docx_parse
    from docx import Document
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# Version sans IA pour éviter les conflits
AI_SUPPORT = False
SPACY_SUPPORT = False

class SimpleAnonymizer:
    """Version simplifiée sans IA pour éviter les conflits Streamlit/PyTorch"""
    
    def __init__(self):
        from .config import ENTITY_PATTERNS, DEFAULT_REPLACEMENTS
        self.patterns = ENTITY_PATTERNS
        self.replacements = DEFAULT_REPLACEMENTS
    
    def detect_entities(self, text: str) -> List[Dict]:
        """Détection avec regex uniquement"""
        entities = []
        entity_id = 0
        
        for entity_type, pattern in self.patterns.items():
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for match in compiled_pattern.finditer(text):
                entity = {
                    "id": f"entity_{entity_id}",
                    "type": entity_type,
                    "value": match.group().strip(),
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 1.0,
                    "replacement": self.replacements.get(entity_type, f"[{entity_type}]")
                }
                entities.append(entity)
                entity_id += 1
        
        return self._remove_overlapping_entities(entities)
    
    def _remove_overlapping_entities(self, entities: List[Dict]) -> List[Dict]:
        """Éliminer les chevauchements"""
        if not entities:
            return entities
        
        sorted_entities = sorted(entities, key=lambda x: x["start"])
        filtered_entities = []
        
        for entity in sorted_entities:
            overlaps = False
            for accepted_entity in filtered_entities:
                if (entity["start"] < accepted_entity["end"] and 
                    entity["end"] > accepted_entity["start"]):
                    entity_length = entity["end"] - entity["start"]
                    accepted_length = accepted_entity["end"] - accepted_entity["start"]
                    
                    if entity_length > accepted_length:
                        filtered_entities.remove(accepted_entity)
                        filtered_entities.append(entity)
                    overlaps = True
                    break
            
            if not overlaps:
                filtered_entities.append(entity)
        
        return filtered_entities
    
    def anonymize_text(self, text: str, entities: List[Dict]) -> str:
        """Anonymiser le texte"""
        sorted_entities = sorted(entities, key=lambda x: x["start"], reverse=True)
        
        anonymized_text = text
        for entity in sorted_entities:
            replacement = entity.get("replacement", f"[{entity['type']}]")
            anonymized_text = (
                anonymized_text[:entity["start"]] + 
                replacement + 
                anonymized_text[entity["end"]:]
            )
        
        return anonymized_text

# 5. Script de diagnostic: check_environment.py

import sys
import importlib

def check_dependencies():
    """Vérifier les dépendances et diagnostiquer les problèmes"""
    
    print("=== DIAGNOSTIC DE L'ENVIRONNEMENT ===\n")
    
    dependencies = {
        "streamlit": "Interface utilisateur",
        "pdfplumber": "Extraction PDF",
        "python-docx": "Traitement DOCX", 
        "torch": "IA (PyTorch)",
        "transformers": "Modèles NER",
        "spacy": "NER français"
    }
    
    available = {}
    issues = []
    
    for dep, description in dependencies.items():
        try:
            if dep == "python-docx":
                importlib.import_module("docx")
            else:
                importlib.import_module(dep.replace("-", "_"))
            
            available[dep] = True
            print(f"✅ {dep}: {description}")
            
        except ImportError:
            available[dep] = False
            print(f"❌ {dep}: {description} - NON INSTALLÉ")
            issues.append(dep)
        except Exception as e:
            available[dep] = False
            print(f"⚠️ {dep}: {description} - ERREUR: {e}")
            issues.append(dep)
    
    print(f"\n=== RÉSUMÉ ===")
    print(f"Python version: {sys.version}")
    print(f"Dépendances disponibles: {sum(available.values())}/{len(dependencies)}")
    
    if available.get("torch") and available.get("transformers"):
        try:
            import torch
            torch.set_num_threads(1)
            print("✅ Configuration PyTorch: OK")
        except Exception as e:
            print(f"⚠️ Configuration PyTorch: {e}")
            issues.append("torch-config")
    
    if issues:
        print(f"\n=== ACTIONS RECOMMANDÉES ===")
        if "torch" in issues or "transformers" in issues:
            print("• Pour éviter les conflits, utilisez la version sans IA")
            print("• Ou installez: pip install torch transformers")
        
        if "spacy" in issues:
            print("• Pour le français: pip install spacy")
            print("• Puis: python -m spacy download fr_core_news_lg")
    
    return available, issues

if __name__ == "__main__":
    check_dependencies()