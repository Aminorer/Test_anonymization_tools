from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from enum import Enum
import uuid
from datetime import datetime

class EntityTypeEnum(str, Enum):
    PERSONNE = "PERSONNE"
    ADRESSE = "ADRESSE"
    TELEPHONE = "NUMÉRO DE TÉLÉPHONE"
    EMAIL = "EMAIL"
    SECURITE_SOCIALE = "NUMÉRO DE SÉCURITÉ SOCIALE"
    ORGANISATION = "ORGANISATION"
    SIRET_SIREN = "SIRET/SIREN"
    AUTRE = "AUTRE"

class Entity(BaseModel):
    id: str = None
    text: str
    type: EntityTypeEnum
    subtype: Optional[str] = None
    start: int
    end: int
    confidence: float
    source: str
    selected: bool = True
    replacement: str = ""
    occurrences: int = 1
    valid: bool = True
    
    def __init__(self, **data):
        if data.get('id') is None:
            data['id'] = str(uuid.uuid4())
        super().__init__(**data)

class CustomEntity(BaseModel):
    text: str
    entity_type: EntityTypeEnum
    replacement: str

class EntityStats(BaseModel):
    total_entities: int
    by_type: Dict[str, int]
    selected_count: int

class AnalyzeRequest(BaseModel):
    mode: str = "standard"

class GenerateRequest(BaseModel):
    session_id: str
    selected_entities: List[Dict[str, Any]]

class AnalyzeResponse(BaseModel):
    success: bool
    session_id: str
    filename: str
    text_preview: str
    entities: List[Entity]
    stats: EntityStats

class AuditLog(BaseModel):
    document: str
    timestamp: str
    processing_tool: str = "Anonymiseur Juridique RGPD v1.0"
    processing_location: str = "local_server"
    rgpd_compliant: bool = True
    entities_anonymized: int
    replacement_summary: List[Dict[str, Any]]

# Configuration des types d'entités
ENTITY_TYPES = {
    'PERSONNE': {
        'patterns': [
            r'Ma?ître\s+([A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][a-zàáâäçéèêëïîôöùúûüñ-]+(?:\s+[A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][a-zàáâäçéèêëïîôöùúûüñ-]+)*)',
            r'(?:Monsieur|Madame|M\.|Mme)\s+([A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][a-zàáâäçéèêëïîôöùúûüñ-]+(?:\s+[A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][a-zàáâäçéèêëïîôöùúûüñ-]+)*)',
            r'\b([A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ]{2,}(?:\s+[A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ]{2,})+)\b'
        ],
        'default_replacement': 'PERSONNE_X',
        'color': '#3b82f6',
        'icon': '👤'
    },
    'ADRESSE': {
        'patterns': [
            r'\d+(?:\s+(?:bis|ter))?\s+(?:rue|avenue|boulevard|place|impasse)\s+[^,\n.]{5,}(?:\s+\d{5}\s+[A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][a-zàáâäçéèêëïîôöùúûüñ-]+)?',
            r'\d{5}\s+[A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ\s-]+'
        ],
        'default_replacement': 'ADRESSE_X',
        'color': '#8b5cf6',
        'icon': '🏠'
    },
    'NUMÉRO DE TÉLÉPHONE': {
        'patterns': [
            r'\b0[1-9](?:[\s.-]?\d{2}){4}\b',
            r'\+33\s?[1-9](?:[\s.-]?\d{2}){4}\b'
        ],
        'default_replacement': '0X XX XX XX XX',
        'color': '#f59e0b',
        'icon': '📞'
    },
    'EMAIL': {
        'patterns': [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'],
        'default_replacement': 'email@anonyme.fr',
        'color': '#10b981',
        'icon': '📧'
    },
    'NUMÉRO DE SÉCURITÉ SOCIALE': {
        'patterns': [r'\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b'],
        'default_replacement': 'X XX XX XX XXX XXX XX',
        'color': '#ef4444',
        'icon': '🆔'
    },
    'ORGANISATION': {
        'patterns': [
            r'\b([A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ\s&\'-]+)(?:\s+(?:SASU|SAS|SARL|SA|EURL|SCI))\b',
            r'(?:Tribunal|Cour)\s+(?:de\s+(?:Grande\s+Instance|Commerce)|d\'[Aa]ppel)\s+de\s+([A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][a-zàáâäçéèêëïîôöùúûüñ-]+)'
        ],
        'default_replacement': 'ORGANISATION_X',
        'color': '#06b6d4',
        'icon': '🏢'
    },
    'SIRET/SIREN': {
        'patterns': [
            r'\b(?:SIRET\s*:?\s*)?(\d{3}[\s\.]?\d{3}[\s\.]?\d{3}[\s\.]?\d{5})\b',
            r'\b(?:SIREN\s*:?\s*)?(\d{3}[\s\.]?\d{3}[\s\.]?\d{3})\b',
            r'(?:n°\s*)?(?:SIRET|SIREN)\s*:?\s*(\d{3}[\s\.]?\d{3}[\s\.]?\d{3}(?:[\s\.]?\d{5})?)',
            r'RCS\s+[A-Z][a-z]+\s+(\d{3}[\s\.]?\d{3}[\s\.]?\d{3})',
            r'(?:APE|NAF)\s*:?\s*(\d{4}[A-Z])',
            r'(?:n°\s*TVA\s*:?\s*|TVA\s+intra\w*\s*:?\s*)?FR\s*(\d{2}\s?\d{9})'
        ],
        'default_replacement': 'SIRET_X',
        'color': '#f97316',
        'icon': '🏭',
        'validation_required': True,
        'replacement_options': [
            'SIRET_MASQUE',
            'SIREN_MASQUE', 
            'XXX XXX XXX',
            'ENTREPRISE_A',
            'NUMERO_REGISTRE'
        ]
    },
    'AUTRE': {
        'patterns': [
            r'N°\s?RG\s?\d+[\/\-\s]*\d*',
            r'(?:Dossier|Affaire)\s+n°\s?\d+[\/\-\s]*\d*'
        ],
        'default_replacement': 'REFERENCE_X',
        'color': '#6b7280',
        'icon': '❓'
    }
}