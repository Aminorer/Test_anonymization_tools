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
    REFERENCE_JURIDIQUE = "RÉFÉRENCE JURIDIQUE"

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
    # Nouvelles propriétés pour les groupes
    group_id: Optional[str] = None
    is_grouped: bool = False
    group_variants: List[str] = []
    
    def __init__(self, **data):
        if data.get('id') is None:
            data['id'] = str(uuid.uuid4())
        super().__init__(**data)

class EntityGroup(BaseModel):
    id: str
    name: str
    entity_ids: List[str]
    replacement: str
    entity_type: EntityTypeEnum
    selected: bool = True
    created_at: str = None
    
    def __init__(self, **data):
        if data.get('id') is None:
            data['id'] = str(uuid.uuid4())
        if data.get('created_at') is None:
            data['created_at'] = datetime.now().isoformat()
        super().__init__(**data)

class CustomEntity(BaseModel):
    text: str
    entity_type: EntityTypeEnum
    replacement: str

class EntityModification(BaseModel):
    entity_id: str
    new_text: str
    new_replacement: Optional[str] = None

class GroupEntitiesRequest(BaseModel):
    session_id: str
    entity_ids: List[str]
    group_name: str
    group_replacement: str

class EntityStats(BaseModel):
    total_entities: int
    by_type: Dict[str, int]
    selected_count: int
    grouped_count: Optional[int] = 0

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
    groups_processed: int = 0
    replacement_summary: List[Dict[str, Any]]

# Configuration des types d'entités (Regex seulement pour données structurées)
STRUCTURED_ENTITY_TYPES = {
    'NUMÉRO DE TÉLÉPHONE': {
        'patterns': [
            r'\b0[1-9](?:[\s.-]?\d{2}){4}\b',
            r'\+33\s?[1-9](?:[\s.-]?\d{2}){4}\b'
        ],
        'default_replacement': '0X XX XX XX XX',
        'color': '#f59e0b',
        'icon': '📞',
        'validation': 'phone'
    },
    'EMAIL': {
        'patterns': [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'],
        'default_replacement': 'email@anonyme.fr',
        'color': '#10b981',
        'icon': '📧',
        'validation': 'email'
    },
    'NUMÉRO DE SÉCURITÉ SOCIALE': {
        'patterns': [r'\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b'],
        'default_replacement': 'X XX XX XX XXX XXX XX',
        'color': '#ef4444',
        'icon': '🆔',
        'validation': 'social_security'
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
        'validation': 'siret_siren',
        'replacement_options': [
            'SIRET_MASQUE',
            'SIREN_MASQUE', 
            'XXX XXX XXX',
            'ENTREPRISE_A',
            'NUMERO_REGISTRE'
        ]
    },
    'ADRESSE': {
        'patterns': [
            r'\d+(?:\s+(?:bis|ter))?\s+(?:rue|avenue|boulevard|place|impasse|allée|square|passage)\s+[^,\n.]{5,}(?:\s+\d{5}\s+[A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][a-zàáâäçéèêëïîôöùúûüñ-]+)?',
            r'\d{5}\s+[A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ][A-ZÀÁÂÄÇÉÈÊËÏÎÔÖÙÚÛÜÑ\s-]+'
        ],
        'default_replacement': 'ADRESSE_X',
        'color': '#8b5cf6',
        'icon': '🏠',
        'validation': 'address'
    },
    'RÉFÉRENCE JURIDIQUE': {
        'patterns': [
            r'N°\s?RG\s?\d+[\/\-\s]*\d*',
            r'(?:Dossier|Affaire)\s+n°\s?\d+[\/\-\s]*\d*',
            r'Article\s+\d+(?:\s+du\s+Code\s+[a-zA-Z\s]+)?',
            r'Arrêt\s+n°\s?\d+[\/\-\s]*\d*'
        ],
        'default_replacement': 'REFERENCE_X',
        'color': '#6b7280',
        'icon': '⚖️',
        'validation': 'reference'
    }
}

# Types d'entités pour SpaCy NER (entités complexes)
SPACY_ENTITY_TYPES = {
    'PERSONNE': {
        'default_replacement': 'PERSONNE_X',
        'color': '#3b82f6',
        'icon': '👤'
    },
    'ORGANISATION': {
        'default_replacement': 'ORGANISATION_X',
        'color': '#06b6d4',
        'icon': '🏢'
    }
}

# Combinaison pour compatibilité
ENTITY_TYPES = {**STRUCTURED_ENTITY_TYPES, **SPACY_ENTITY_TYPES}