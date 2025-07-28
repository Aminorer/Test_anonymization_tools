import { create } from 'zustand';
import { Entity, EntityStats, CustomEntity } from '../types/entities';

interface AnonymizerState {
  // État du document
  sessionId: string | null;
  filename: string | null;
  textPreview: string | null;
  
  // État des entités
  entities: Entity[];
  stats: EntityStats | null;
  
  // État de l'interface
  isLoading: boolean;
  isAnalyzing: boolean;
  isGenerating: boolean;
  error: string | null;
  
  // Actions
  setSessionData: (sessionId: string, filename: string, textPreview: string) => void;
  setEntities: (entities: Entity[], stats: EntityStats) => void;
  toggleEntity: (entityId: string) => void;
  updateReplacement: (entityId: string, replacement: string) => void;
  addCustomEntity: (entity: CustomEntity) => void;
  selectAll: () => void;
  deselectAll: () => void;
  setLoading: (loading: boolean) => void;
  setAnalyzing: (analyzing: boolean) => void;
  setGenerating: (generating: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
  
  // Getters calculés
  getSelectedEntities: () => Entity[];
  getSelectedCount: () => number;
  getEntitiesByType: () => Record<string, Entity[]>;
}

export const useAnonymizerStore = create<AnonymizerState>((set, get) => ({
  // État initial
  sessionId: null,
  filename: null,
  textPreview: null,
  entities: [],
  stats: null,
  isLoading: false,
  isAnalyzing: false,
  isGenerating: false,
  error: null,
  
  // Actions de base
  setSessionData: (sessionId, filename, textPreview) => 
    set({ sessionId, filename, textPreview }),
  
  setEntities: (entities, stats) => 
    set({ entities, stats }),
  
  toggleEntity: (entityId) =>
    set((state) => ({
      entities: state.entities.map((entity) =>
        entity.id === entityId
          ? { ...entity, selected: !entity.selected }
          : entity
      ),
    })),
  
  updateReplacement: (entityId, replacement) =>
    set((state) => ({
      entities: state.entities.map((entity) =>
        entity.id === entityId
          ? { ...entity, replacement }
          : entity
      ),
    })),
  
  addCustomEntity: (customEntity) =>
    set((state) => {
      const newEntity: Entity = {
        id: `custom-${Date.now()}`,
        text: customEntity.text,
        type: customEntity.entity_type,
        occurrences: 1,
        confidence: 1.0,
        selected: true,
        replacement: customEntity.replacement,
        source: 'manual'
      };
      
      return {
        entities: [...state.entities, newEntity],
        stats: state.stats ? {
          ...state.stats,
          total_entities: state.stats.total_entities + 1,
          selected_count: state.stats.selected_count + 1,
          by_type: {
            ...state.stats.by_type,
            [customEntity.entity_type]: (state.stats.by_type[customEntity.entity_type] || 0) + 1
          }
        } : null
      };
    }),
  
  selectAll: () =>
    set((state) => ({
      entities: state.entities.map((entity) => ({ ...entity, selected: true })),
    })),
  
  deselectAll: () =>
    set((state) => ({
      entities: state.entities.map((entity) => ({ ...entity, selected: false })),
    })),
  
  setLoading: (isLoading) => set({ isLoading }),
  setAnalyzing: (isAnalyzing) => set({ isAnalyzing }),
  setGenerating: (isGenerating) => set({ isGenerating }),
  setError: (error) => set({ error }),
  
  reset: () =>
    set({
      sessionId: null,
      filename: null,
      textPreview: null,
      entities: [],
      stats: null,
      isLoading: false,
      isAnalyzing: false,
      isGenerating: false,
      error: null,
    }),
  
  // Getters calculés
  getSelectedEntities: () => {
    const state = get();
    return state.entities.filter((entity) => entity.selected);
  },
  
  getSelectedCount: () => {
    const state = get();
    return state.entities.filter((entity) => entity.selected).length;
  },
  
  getEntitiesByType: () => {
    const state = get();
    const grouped: Record<string, Entity[]> = {};
    
    state.entities.forEach((entity) => {
      const type = entity.type;
      if (!grouped[type]) {
        grouped[type] = [];
      }
      grouped[type].push(entity);
    });
    
    return grouped;
  },
}));