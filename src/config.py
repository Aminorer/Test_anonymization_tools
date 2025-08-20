import re

# Configuration générale
APP_NAME = "Anonymiseur de Documents Juridiques"
APP_VERSION = "2.0.0"
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
SUPPORTED_FORMATS = ["pdf", "docx", "doc"]

# Patterns regex pour la détection d'entités
ENTITY_PATTERNS = {
    "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "PHONE": r'(?:\+33|0)[1-9](?:[0-9]{8})|(?:\+33|0)[1-9](?:\s[0-9]{2}){4}|(?:\+33|0)[1-9](?:\.[0-9]{2}){4}',
    "DATE": r'\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{2,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b',
    "ADDRESS": r'\b\d+\s+[A-Za-z\s]+(?:rue|avenue|boulevard|place|square|impasse|allée|chemin|route)\s+[A-Za-z\s]+(?:\d{5})?\s*[A-Za-z\s]*\b',
    "IBAN": r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b',
    "SIREN": r'\b\d{3}\s?\d{3}\s?\d{3}\b',
    "SIRET": r'\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b',
    "LOC": r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*(?:\s(?:sur|en|de|du|des|le|la|les)\s[A-Z][a-z]+)*\b',
    "POSTAL_CODE": r'\b\d{5}\b',
    "SSN": r'\b[12]\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}\d{3}\d{2}\b',
    "CREDIT_CARD": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    "IP_ADDRESS": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    "URL": r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*)?)?)?',
}

# Couleurs pour les types d'entités (format hexadécimal)
ENTITY_COLORS = {
    "EMAIL": "#3b82f6",      # Bleu
    "PHONE": "#10b981",      # Vert
    "DATE": "#a855f7",       # Violet
    "ADDRESS": "#ef4444",    # Rouge
    "IBAN": "#9ca3af",       # Gris
    "SIREN": "#fbbf24",      # Jaune
    "SIRET": "#0ea5e9",      # Bleu clair
    "LOC": "#22c55e",        # Vert clair
    "PERSON": "#8b5cf6",     # Pourpre
    "ORG": "#f59e0b",        # Orange
    "POSTAL_CODE": "#84cc16", # Vert lime
    "SSN": "#ec4899",        # Rose
    "CREDIT_CARD": "#6366f1", # Indigo
    "IP_ADDRESS": "#14b8a6", # Teal
    "URL": "#f97316",        # Orange foncé
    "MISC": "#6b7280",       # Gris foncé
}

# Remplacements par défaut pour chaque type d'entité
DEFAULT_REPLACEMENTS = {
    "EMAIL": "[EMAIL]",
    "PHONE": "[TÉLÉPHONE]",
    "DATE": "[DATE]",
    "ADDRESS": "[ADRESSE]",
    "IBAN": "[IBAN]",
    "SIREN": "[SIREN]",
    "SIRET": "[SIRET]",
    "LOC": "[LIEU]",
    "PERSON": "[PERSONNE]",
    "ORG": "[ORGANISATION]",
    "POSTAL_CODE": "[CODE_POSTAL]",
    "SSN": "[NUMÉRO_SÉCU]",
    "CREDIT_CARD": "[CARTE_BANCAIRE]",
    "IP_ADDRESS": "[ADRESSE_IP]",
    "URL": "[URL]",
    "MISC": "[DONNÉES]",
}

# Configuration des modèles IA
AI_MODELS = {
    "french": {
        "name": "dbmdz/bert-large-cased-finetuned-conll03-english",
        "language": "fr",
        "description": "Modèle BERT pour le français"
    },
    "multilingual": {
        "name": "xlm-roberta-large-finetuned-conll03-english",
        "language": "multi",
        "description": "Modèle multilingue XLM-RoBERTa"
    },
    "small": {
        "name": "dbmdz/distilbert-base-cased-finetuned-conll03-english",
        "language": "en",
        "description": "Modèle léger DistilBERT"
    }
}

# Préréglages d'anonymisation
ANONYMIZATION_PRESETS = {
    "light": {
        "name": "Anonymisation légère",
        "description": "Supprime uniquement les emails, téléphones et adresses",
        "entity_types": ["EMAIL", "PHONE", "ADDRESS"],
        "confidence_threshold": 0.9
    },
    "standard": {
        "name": "Anonymisation standard",
        "description": "Supprime les données personnelles principales",
        "entity_types": ["EMAIL", "PHONE", "ADDRESS", "DATE", "PERSON", "IBAN"],
        "confidence_threshold": 0.7
    },
    "complete": {
        "name": "Anonymisation complète",
        "description": "Supprime toutes les données identifiantes",
        "entity_types": ["EMAIL", "PHONE", "ADDRESS", "DATE", "PERSON", "ORG", "LOC", "IBAN", "SIREN", "SIRET", "SSN", "CREDIT_CARD"],
        "confidence_threshold": 0.5
    },
    "gdpr_compliant": {
        "name": "Conformité RGPD",
        "description": "Anonymisation selon les standards RGPD",
        "entity_types": ["EMAIL", "PHONE", "ADDRESS", "PERSON", "SSN", "CREDIT_CARD", "IBAN"],
        "confidence_threshold": 0.8
    }
}

# Configuration des formats d'export
EXPORT_FORMATS = {
    "docx": {
        "extension": ".docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "description": "Document Word"
    },
    "pdf": {
        "extension": ".pdf",
        "mime_type": "application/pdf",
        "description": "Document PDF"
    },
    "txt": {
        "extension": ".txt",
        "mime_type": "text/plain",
        "description": "Fichier texte"
    }
}

# Messages et textes de l'interface
UI_MESSAGES = {
    "upload": {
        "title": "📁 Upload de Document",
        "description": "Choisissez un document à anonymiser",
        "success": "✅ Fichier sélectionné avec succès",
        "error_size": "❌ Fichier trop volumineux",
        "error_format": "❌ Format de fichier non supporté"
    },
    "processing": {
        "initializing": "🔧 Initialisation du traitement...",
        "reading": "📖 Lecture du document...",
        "analyzing": "🔍 Analyse en cours...",
        "completed": "✅ Traitement terminé!",
        "error": "❌ Erreur lors du traitement"
    },
    "results": {
        "title": "📊 Résultats de l'Analyse",
        "no_entities": "Aucune entité détectée",
        "entities_found": "entités détectées"
    },
    "export": {
        "title": "📤 Export du Document Anonymisé",
        "success": "✅ Fichier prêt au téléchargement!",
        "error": "❌ Erreur lors de l'export"
    }
}

# Configuration de sécurité
SECURITY_CONFIG = {
    "max_upload_size": MAX_FILE_SIZE,
    "allowed_extensions": SUPPORTED_FORMATS,
    "temp_file_retention": 3600,  # 1 heure en secondes
    "max_concurrent_processes": 5,
    "rate_limit_requests": 100,   # Par heure
    "enable_logging": True
}

# Configuration des logs
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_rotation": True,
    "max_file_size": "10MB",
    "backup_count": 5
}

# Métadonnées de l'application
APP_METADATA = {
    "name": APP_NAME,
    "version": APP_VERSION,
    "description": "Application d'anonymisation de documents juridiques conforme RGPD",
    "author": "Assistant IA",
    "license": "MIT",
    "keywords": ["anonymisation", "RGPD", "documents", "juridique", "IA", "NER"],
    "requirements": [
        "streamlit>=1.28.0",
        "python-docx>=0.8.11",
        "pdfplumber>=0.7.0",
        "pdf2docx>=0.5.6",
        "transformers>=4.21.0",
        "torch>=1.12.0",
        "pandas>=1.5.0",
        "plotly>=5.10.0"
    ]
}

# Configuration de validation
VALIDATION_RULES = {
    "entity_value_max_length": 1000,
    "entity_type_max_length": 50,
    "replacement_max_length": 200,
    "group_name_max_length": 100,
    "group_description_max_length": 500,
    "document_max_pages": 100,
    "max_entities_per_document": 10000
}

# Configuration des alertes et notifications
ALERT_CONFIG = {
    "high_entity_count_threshold": 100,
    "low_confidence_threshold": 0.5,
    "processing_time_warning": 300,  # 5 minutes
    "enable_success_notifications": True,
    "enable_error_notifications": True,
    "enable_warning_notifications": True
}

# Templates pour les rapports
REPORT_TEMPLATES = {
    "audit_header": """
RAPPORT D'AUDIT D'ANONYMISATION
================================

Document original: {filename}
Date de traitement: {timestamp}
Mode d'analyse: {mode}
Seuil de confiance: {confidence}

""",
    "statistics_section": """
STATISTIQUES GÉNÉRALES
======================

Nombre total d'entités détectées: {total_entities}
Types d'entités différents: {unique_types}
Entités haute confiance (≥80%): {high_confidence_count}
Temps de traitement: {processing_time} secondes

""",
    "entities_by_type": """
RÉPARTITION PAR TYPE D'ENTITÉ
=============================

{entity_breakdown}

""",
    "recommendations": """
RECOMMANDATIONS
==============

{recommendations_text}

Ce document a été anonymisé selon les standards RGPD.
Vérifiez manuellement les entités détectées avant diffusion.

"""
}

# Configuration des raccourcis clavier (pour référence dans l'UI)
KEYBOARD_SHORTCUTS = {
    "save": "Ctrl+S",
    "export": "Ctrl+E",
    "search": "Ctrl+F",
    "select_all": "Ctrl+A",
    "undo": "Ctrl+Z",
    "redo": "Ctrl+Y",
    "new_group": "Ctrl+G",
    "delete": "Delete",
    "help": "F1"
}

# Configuration par défaut pour les nouveaux utilisateurs
DEFAULT_USER_SETTINGS = {
    "preferred_mode": "regex",
    "default_confidence": 0.7,
    "auto_save": True,
    "show_confidence": True,
    "highlight_entities": True,
    "generate_audit_report": True,
    "add_watermark": True,
    "watermark_text": "DOCUMENT ANONYMISÉ",
    "preferred_export_format": "docx"
}