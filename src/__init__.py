"""
Anonymiseur de Documents Juridiques - Version Streamlit
=======================================================

Ce package contient tous les modules nécessaires pour l'anonymisation
de documents juridiques conforme au RGPD.

Modules principaux:
- anonymizer: Classes d'anonymisation (Regex et IA)
- entity_manager: Gestion des entités et groupes
- config: Configuration et constantes
- utils: Fonctions utilitaires

Usage:
    from src.anonymizer import DocumentAnonymizer
    from src.entity_manager import EntityManager
    
    anonymizer = DocumentAnonymizer()
    result = anonymizer.process_document("document.pdf", mode="ai", audit=False)
"""

__version__ = "2.0.0"
__author__ = "Assistant IA"
__license__ = "MIT"

# Imports principaux pour faciliter l'utilisation
from .anonymizer import (
    DocumentAnonymizer,
    RegexAnonymizer,
    AIAnonymizer,
    DocumentProcessor,
    Entity
)

from .entity_manager import EntityManager

from .config import (
    ENTITY_PATTERNS,
    ENTITY_COLORS,
    DEFAULT_REPLACEMENTS,
    ANONYMIZATION_PRESETS
)

from .utils import (
    format_file_size,
    save_upload_file,
    cleanup_temp_files,
    generate_anonymization_stats,
    serialize_entity_mapping
)

__all__ = [
    # Classes principales
    "DocumentAnonymizer",
    "RegexAnonymizer", 
    "AIAnonymizer",
    "DocumentProcessor",
    "EntityManager",
    "Entity",
    
    # Configuration
    "ENTITY_PATTERNS",
    "ENTITY_COLORS", 
    "DEFAULT_REPLACEMENTS",
    "ANONYMIZATION_PRESETS",
    
    # Utilitaires
    "format_file_size",
    "save_upload_file",
    "cleanup_temp_files",
    "generate_anonymization_stats",
    "serialize_entity_mapping"
]