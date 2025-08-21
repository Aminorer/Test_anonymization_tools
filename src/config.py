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

# === PATTERNS REGEX OPTIMISÉS (SANS LOC COMME DEMANDÉ) ===
ENTITY_PATTERNS = {
    # Données de contact
    "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "PHONE": r'(?:\+33\s?|0)[1-9](?:[0-9\s.-]{8,})|(?:\+33\s?|0)[1-9](?:\s[0-9]{2}){4}|(?:\+33\s?|0)[1-9](?:\.[0-9]{2}){4}',
    
    # Dates et temps
    "DATE": r'\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{2,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b',
    "TIME": r'\b(?:[01]?[0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?\b',
    
    # Adresses (plus précis que LOC supprimé)
    "ADDRESS": r'\b\d+(?:\s+(?:bis|ter|quater))?\s+(?:rue|avenue|boulevard|place|square|impasse|allée|chemin|route|passage|villa|cité|quai|esplanade|parvis|cours|mail)\s+[A-Za-zÀ-ÿ\s\-\']+(?:\s+\d{5})?\s*[A-Za-zÀ-ÿ\s]*\b',
    
    # Données bancaires et financières
    "IBAN": r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b',
    "CREDIT_CARD": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
    "BIC": r'\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b',
    
    # Identifiants français
    "SIREN": r'\b\d{3}\s?\d{3}\s?\d{3}\b',
    "SIRET": r'\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b',
    "SSN": r'\b[12]\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}\d{3}\d{2}\b',
    "TVA_NUMBER": r'\bFR\s?\d{2}\s?\d{9}\b',
    
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
    "PERSON_WITH_TITLE": r'\b(?:M\.?|Mme\.?|Mlle\.?|Dr\.?|Prof\.?|Me\.?|Maître)\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþß]+(?:\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþß]+)*',
    
    # Organisations françaises avec formes juridiques
    "FRENCH_COMPANY": r'\b(?:SARL|SAS|SA|SNC|EURL|SASU|SCI|SELARL|SELCA|SELAS|Association|Société|Entreprise|Cabinet|Étude|Bureau|Groupe|Fondation|Institut|Centre|Établissement)\s+[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][A-Za-zÀ-ÿ\s\-\'&]+',
    
    # Numéros français spécialisés
    "FRENCH_SSN": r'\b[12]\s?\d{2}\s?(?:0[1-9]|1[0-2])\s?(?:0[1-9]|[12]\d|3[01])\s?\d{3}\s?\d{3}\s?\d{2}\b',
    "INSEE_NUMBER": r'\b[12]\d{14}\b',
    
    # Adresses françaises complètes
    "FRENCH_ADDRESS": r'\b\d+(?:\s+(?:bis|ter|quater))?\s+(?:rue|avenue|boulevard|place|square|impasse|allée|chemin|route|passage|villa|cité|quai|esplanade|parvis|cours|mail|faubourg)\s+[A-Za-zÀ-ÿ\s\-\']+(?:\s+\d{5})?\s*[A-Za-zÀ-ÿ\s]*\b',
    
    # Références administratives
    "PREFECTURE_REF": r'\b\d{3}-\d{4}-\d{5}\b',
    "CADASTRE_REF": r'\b\d{3}[A-Z]{2}\d{4}\b',
    
    # Numéros de téléphone français spécifiques
    "FRENCH_MOBILE": r'\b(?:\+33\s?|0)[67](?:[0-9\s.-]{8})\b',
    "FRENCH_LANDLINE": r'\b(?:\+33\s?|0)[1-5](?:[0-9\s.-]{8})\b'
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