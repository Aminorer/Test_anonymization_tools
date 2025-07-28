export enum EntityType {
  PERSONNE = "PERSONNE",
  ADRESSE = "ADRESSE",
  TELEPHONE = "NUMÉRO DE TÉLÉPHONE",
  EMAIL = "EMAIL",
  SECURITE_SOCIALE = "NUMÉRO DE SÉCURITÉ SOCIALE",
  ORGANISATION = "ORGANISATION",
  SIRET_SIREN = "SIRET/SIREN",
  AUTRE = "AUTRE"
}

export interface Entity {
  id: string;
  text: string;
  type: EntityType;
  subtype?: string;
  occurrences: number;
  confidence: number;
  selected: boolean;
  replacement: string;
  valid?: boolean;
  source: string;
}

export interface EntityStats {
  total_entities: number;
  by_type: Record<string, number>;
  selected_count: number;
}

export interface AnalyzeResponse {
  success: boolean;
  session_id: string;
  filename: string;
  text_preview: string;
  entities: Entity[];
  stats: EntityStats;
}

export interface CustomEntity {
  text: string;
  entity_type: EntityType;
  replacement: string;
}

export const ENTITY_TYPES_CONFIG = {
  'PERSONNE': {
    color: '#3b82f6',
    icon: '👤',
    default_replacement: 'PERSONNE_X'
  },
  'ADRESSE': {
    color: '#8b5cf6',
    icon: '🏠',
    default_replacement: 'ADRESSE_X'
  },
  'NUMÉRO DE TÉLÉPHONE': {
    color: '#f59e0b',
    icon: '📞',
    default_replacement: '0X XX XX XX XX'
  },
  'EMAIL': {
    color: '#10b981',
    icon: '📧',
    default_replacement: 'email@anonyme.fr'
  },
  'NUMÉRO DE SÉCURITÉ SOCIALE': {
    color: '#ef4444',
    icon: '🆔',
    default_replacement: 'X XX XX XX XXX XXX XX'
  },
  'ORGANISATION': {
    color: '#06b6d4',
    icon: '🏢',
    default_replacement: 'ORGANISATION_X'
  },
  'SIRET/SIREN': {
    color: '#f97316',
    icon: '🏭',
    default_replacement: 'SIRET_X',
    replacement_options: [
      'SIRET_MASQUE',
      'SIREN_MASQUE', 
      'XXX XXX XXX',
      'ENTREPRISE_A',
      'NUMERO_REGISTRE'
    ]
  },
  'AUTRE': {
    color: '#6b7280',
    icon: '❓',
    default_replacement: 'REFERENCE_X'
  }
};