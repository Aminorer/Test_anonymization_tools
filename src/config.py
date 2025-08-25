# src/config.py - CONFIGURATION OPTIMISÉE SANS LOC
"""
Configuration complète pour l'Anonymiseur de Documents Juridiques
Version 2.0 avec support NER et optimisations françaises
"""

import re

# === INFORMATIONS APPLICATION ===
APP_NAME = "Anonymiseur de Documents Juridiques"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Anonymisation intelligente avec NER et conformité RGPD"
APP_AUTHOR = "Assistant IA"
APP_LICENSE = "MIT"

# === CONFIGURATION GÉNÉRALE ===
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
SUPPORTED_FORMATS = ["pdf", "docx", "doc", "txt"]
MAX_TEXT_LENGTH = 10_000_000  # 10M caractères max
TEMP_FILE_RETENTION = 3600  # 1 heure en secondes

# === NORMALISATION DES NOMS ===
NAME_NORMALIZATION = {
    "titles": ["mr", "mme", "dr", "me", "maître"],
    "similarity_threshold": 0.85,
    # Default weights for name similarity components
    "similarity_weights": {
        "levenshtein": 0.5,
        "jaccard": 0.3,
        "phonetic": 0.2,
    },
}

# === PATTERNS REGEX OPTIMISÉS (SANS LOC COMME DEMANDÉ) ===
ENTITY_PATTERNS = {
    # Données de contact
    "EMAIL": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",  # RFC 5322
    "PHONE": r"\b(?:\+33|0)(?:[1-5]|[67])(?:[ .-]?\d{2}){4}\b",  # Plan national ARCEP
    
    # Dates et temps
    "DATE": r"\b(?:0?[1-9]|[12][0-9]|3[01])[-/](?:0?[1-9]|1[0-2])[-/](?:19|20)\d{2}\b",  # JJ/MM/AAAA
    "TIME": r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?\b",
    
    # Adresses (plus précis que LOC supprimé)
    "ADDRESS": r"\b\d{1,4}\s?(?:bis|ter|quater)?\s+(?:rue|avenue|boulevard|place|square|impasse|allée|chemin|route|passage|villa|cité|quai|esplanade|parvis|cours|mail|faubourg)\s+[A-Za-zÀ-ÿ'\-\s]+,?\s\d{5}\s[A-Za-zÀ-ÿ'\-\s]+\b",  # Norme AFNOR NF Z 10-011
    
    # Données bancaires et financières
    "IBAN": r"\bFR\d{2}\s?\d{5}\s?\d{5}\s?[A-Z0-9]{11}\s?\d{2}\b",  # IBAN FR ISO 13616 (27 caractères)
    "CREDIT_CARD": r"\b(?:\d{4}[- ]?){3}\d{4}\b",  # Carte bancaire 16 chiffres
    "BIC": r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b",  # Code BIC ISO 9362
    
    # Identifiants français
    "SIREN": r"\b\d{3}\s?\d{3}\s?\d{3}\b",  # INSEE SIREN (9 chiffres)
    "SIRET": r"\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b",  # INSEE SIRET (14 chiffres)
    "SSN": r"\b[12]\d{2}(?:0[1-9]|1[0-2])(?:[0-9]{2}|2A|2B)\d{3}\d{3}\d{2}\b",  # NIR 15 chiffres + clé
    "TVA_NUMBER": r"\bFR\d{2}\d{9}\b",  # TVA intracommunautaire
    
    # Codes et références
    "POSTAL_CODE": r'\b(?:0[1-9]|[1-8]\d|9[0-5])\d{3}\b',
    "LICENSE_PLATE": r'\b[A-Z]{2}-\d{3}-[A-Z]{2}\b',
    
    # Références juridiques
    "LEGAL_REFERENCE": r'\b[Aa]rticle\s+\d+(?:-\d+)?\s+(?:du\s+)?(?:Code\s+)?[A-Za-zÀ-ÿ\s]+\b',
    "CASE_NUMBER": r'\b(?:n°|N°|numéro|Numéro)\s*:?\s*\d{2,}/\d{2,}(?:/\d{2,})?\b',
    "COURT_REFERENCE": r'\bRG\s*:?\s*\d{2}/\d{5}\b',
    
    # Données techniques
    "IP_ADDRESS": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    "URL": r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*)?)?)?',
    "MAC_ADDRESS": r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b',
    
    # Montants et mesures
    "MONEY": r'\b\d+(?:\s?\d{3})*(?:[,.]\d{2})?\s?(?:€|EUR|euros?|francs?)\b',
    "PERCENTAGE": r'\b\d+(?:[,.]\d+)?\s?%\b'
}

# === PATTERNS FRANÇAIS AVANCÉS ===
FRENCH_ENTITY_PATTERNS = {
    **ENTITY_PATTERNS,  # Inclure tous les patterns de base

    # Noms avec titres de civilité français
    "PERSON_WITH_TITLE": r"\b(?:M\.?|Mme\.?|Mlle\.?|Dr\.?|Prof\.?|Me\.?|Maître)\s+[A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)*",  # Titres de civilité

    # Organisations françaises avec formes juridiques
    "FRENCH_COMPANY": r"\b(?:SARL|SAS|SA|SNC|EURL|SASU|SCI|SELARL|SELCA|SELAS|Association|Société|Entreprise|Cabinet|Étude|Bureau|Groupe|Fondation|Institut|Centre|Établissement)\s+[A-ZÀ-Ÿ][A-Za-zÀ-ÿ\s\-'&]+",  # Formes juridiques françaises

    # Numéros français spécialisés
    "FRENCH_SSN": r"\b[12]\d{2}(?:0[1-9]|1[0-2])(?:[0-9]{2}|2A|2B)\d{3}\d{3}\d{2}\b",  # NIR 15 chiffres (INSEE)
    "INSEE_NUMBER": r"\b[12]\d{14}\b",  # Numéro INSEE brut

    # Adresses françaises complètes
    "FRENCH_ADDRESS": r"\b\d{1,4}\s?(?:bis|ter|quater)?\s+(?:rue|avenue|boulevard|place|square|impasse|allée|chemin|route|passage|villa|cité|quai|esplanade|parvis|cours|mail|faubourg)\s+[A-Za-zÀ-ÿ'\-\s]+,?\s\d{5}\s[A-Za-zÀ-ÿ'\-\s]+\b",  # Norme adresse postale

    # Références administratives
    "PREFECTURE_REF": r"\b\d{3}-\d{4}-\d{5}\b",  # Référence préfectorale
    "CADASTRE_REF": r"\b\d{3}[A-Z]{2}\d{4}\b",  # Référence cadastrale

    # Numéros de téléphone français spécifiques
    "FRENCH_MOBILE": r"\b(?:\+33|0)[67](?:[ .-]?\d{2}){4}\b",  # Mobiles 06/07
    "FRENCH_LANDLINE": r"\b(?:\+33|0)[1-5](?:[ .-]?\d{2}){4}\b",  # Fixes 01-05

    # Références juridiques
    "LEGAL_REFERENCE": r"\b[Aa]rt(?:icle)?\.?\s+[LDR]\d+(?:-\d+)*\s+du\s+Code\s+[A-Za-zÀ-ÿ\s]+\b"  # Articles de loi français
}

# === COULEURS POUR LES TYPES D'ENTITÉS ===
ENTITY_COLORS = {
    "EMAIL": "#4CAF50",  # Vert
    "PHONE": "#2196F3",  # Bleu
    "DATE": "#FF9800",   # Orange
    "ADDRESS": "#9C27B0", # Violet
    "IBAN": "#F44336",   # Rouge
    "CREDIT_CARD": "#F44336",  # Rouge
    "PERSON": "#3F51B5", # Bleu foncé
    "ORG": "#009688",    # Turquoise
    "SSN": "#E91E63",    # Rose
    "SIRET": "#795548",  # Marron
    "SIREN": "#795548",  # Marron
    "TVA_NUMBER": "#795548",  # Marron
    "LEGAL_REFERENCE": "#607D8B",  # Bleu-gris
    "CASE_NUMBER": "#607D8B",  # Bleu-gris
    "COURT_REFERENCE": "#607D8B",  # Bleu-gris
    "MISC": "#9E9E9E"    # Gris
}

# === REMPLACEMENTS PAR DÉFAUT ===
DEFAULT_REPLACEMENTS = {
    "EMAIL": "[EMAIL]",
    "PHONE": "[TÉLÉPHONE]",
    "DATE": "[DATE]",
    "ADDRESS": "[ADRESSE]",
    "IBAN": "[IBAN]",
    "CREDIT_CARD": "[CARTE_BANCAIRE]",
    "PERSON": "[PERSONNE]",
    "ORG": "[ORGANISATION]",
    "SSN": "[NUMÉRO_SS]",
    "SIRET": "[SIRET]",
    "SIREN": "[SIREN]",
    "TVA_NUMBER": "[TVA]",
    "LEGAL_REFERENCE": "[RÉFÉRENCE_LÉGALE]",
    "CASE_NUMBER": "[NUMÉRO_DOSSIER]",
    "COURT_REFERENCE": "[RÉFÉRENCE_TRIBUNAL]",
    "MISC": "[DIVERS]"
}

# === PRESETS D'ANONYMISATION ===
ANONYMIZATION_PRESETS = {
    "light": {
        "name": "Léger",
        "description": "Anonymisation légère - données de contact uniquement",
        "entity_types": ["EMAIL", "PHONE", "ADDRESS"],
        "confidence_threshold": 0.8
    },
    "standard": {
        "name": "Standard", 
        "description": "Anonymisation standard - données personnelles principales",
        "entity_types": [
            "EMAIL", "PHONE", "ADDRESS", "PERSON", "ORG",
            "DATE", "IBAN", "SSN"
        ],
        "confidence_threshold": 0.7
    },
    "complete": {
        "name": "Complet",
        "description": "Anonymisation complète - toutes les données sensibles",
        "entity_types": [
            "EMAIL", "PHONE", "ADDRESS", "PERSON", "ORG", "DATE",
            "IBAN", "SSN", "SIRET", "SIREN", "TVA_NUMBER",
            "CREDIT_CARD", "LEGAL_REFERENCE", "CASE_NUMBER",
            "COURT_REFERENCE"
        ],
        "confidence_threshold": 0.6
    },
    "gdpr_compliant": {
        "name": "RGPD",
        "description": "Anonymisation maximale conforme RGPD",
        "entity_types": [
            "EMAIL", "PHONE", "ADDRESS", "PERSON", "ORG", "DATE",
            "IBAN", "SSN", "SIRET", "SIREN", "TVA_NUMBER",
            "CREDIT_CARD", "LEGAL_REFERENCE", "CASE_NUMBER",
            "COURT_REFERENCE", "MISC"
        ],
        "confidence_threshold": 0.5
    }
}

# === TEMPLATES JURIDIQUES ===

class LegalTemplates:
    """Registry of domain-specific anonymization templates."""

    LEGAL_TEMPLATES = {
        "contrat_bail": {
            "entities": ["PERSON", "ORG", "DATE", "ADDRESS", "MONEY"],
            "preserve": ["LEGAL_REFERENCE"],
            "special_handling": {
                "distinguish_parties": True,
                "geo_anonymization": True,
            },
            "keywords": ["contrat de bail", "bailleur", "locataire"],
        },
        "procedure_civile": {
            "entities": [
                "PERSON",
                "ORG",
                "DATE",
                "CASE_NUMBER",
                "COURT_REFERENCE",
                "LEGAL_REFERENCE",
            ],
            "preserve": ["LEGAL_REFERENCE"],
            "special_handling": {
                "distinguish_parties": True,
                "geo_anonymization": False,
            },
            "keywords": ["procédure civile", "tribunal", "audience"],
        },
        "acte_notarie": {
            "entities": ["PERSON", "ORG", "DATE", "ADDRESS", "MONEY", "LEGAL_REFERENCE"],
            "preserve": ["LEGAL_REFERENCE", "MONEY"],
            "special_handling": {
                "distinguish_parties": False,
                "geo_anonymization": True,
            },
            "keywords": ["notarié", "notaire", "acte authentique"],
        },
    }

    @classmethod
    def get(cls, name: str):
        """Return a template by its name.

        Args:
            name: Template identifier.

        Returns:
            dict | None: Template configuration if found, else None.
        """

        return cls.LEGAL_TEMPLATES.get(name)

    @classmethod
    def detect(cls, text: str):
        """Auto-detect the template based on keywords found in ``text``.

        Args:
            text: Raw document text.

        Returns:
            tuple[str, dict] | tuple[None, None]: Detected template name and
            configuration, or ``(None, None)`` if no template matches.
        """

        text_lower = text.lower()
        for name, tpl in cls.LEGAL_TEMPLATES.items():
            for keyword in tpl.get("keywords", []):
                if keyword.lower() in text_lower:
                    return name, tpl
        return None, None


# Alias for direct access if a simple mapping is preferred
LEGAL_TEMPLATES = LegalTemplates.LEGAL_TEMPLATES


