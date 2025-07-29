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
  
  // Getters calculés (corrigés)
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
  
  // Actions de base corrigées
  setSessionData: (sessionId, filename, textPreview) => {
    console.log('Store - setSessionData:', { sessionId, filename, textPreviewLength: textPreview?.length });
    set({ sessionId, filename, textPreview });
  },
  
  setEntities: (entities, stats) => {
    console.log('Store - setEntities:', { 
      entitiesCount: entities?.length || 0, 
      statsTotal: stats?.total_entities,
      firstEntities: entities?.slice(0, 3)
    });
    
    // S'assurer que les entités ont la structure correcte
    const processedEntities = (entities || []).map((entity, index) => ({
      ...entity,
      id: entity.id || `entity-${index}`,
      selected: entity.selected !== undefined ? entity.selected : true,
      replacement: entity.replacement || `ANONYME_${index}`,
      occurrences: entity.occurrences || 1,
      confidence: entity.confidence || 0.8,
      source: entity.source || 'unknown'
    }));
    
    set({ 
      entities: processedEntities, 
      stats: stats || { total_entities: processedEntities.length, by_type: {}, selected_count: processedEntities.length }
    });
  },
  
  toggleEntity: (entityId) => {
    console.log('Store - toggleEntity:', entityId);
    set((state) => {
      const updatedEntities = state.entities.map((entity) =>
        entity.id === entityId
          ? { ...entity, selected: !entity.selected }
          : entity
      );
      
      console.log('Store - Entity toggled:', {
        entityId,
        newSelected: updatedEntities.find(e => e.id === entityId)?.selected
      });
      
      return { entities: updatedEntities };
    });
  },
  
  updateReplacement: (entityId, replacement) => {
    console.log('Store - updateReplacement:', { entityId, replacement });
    set((state) => ({
      entities: state.entities.map((entity) =>
        entity.id === entityId
          ? { ...entity, replacement }
          : entity
      ),
    }));
  },
  
  addCustomEntity: (customEntity) => {
    console.log('Store - addCustomEntity:', customEntity);
    set((state) => {
      const newEntity: Entity = {
        id: `custom-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        text: customEntity.text,
        type: customEntity.entity_type,
        occurrences: 1,
        confidence: 1.0,
        selected: true,
        replacement: customEntity.replacement,
        source: 'manual'
      };
      
      const updatedEntities = [...state.entities, newEntity];
      
      const updatedStats = state.stats ? {
        ...state.stats,
        total_entities: state.stats.total_entities + 1,
        selected_count: state.stats.selected_count + 1,
        by_type: {
          ...state.stats.by_type,
          [customEntity.entity_type]: (state.stats.by_type[customEntity.entity_type] || 0) + 1
        }
      } : {
        total_entities: updatedEntities.length,
        selected_count: updatedEntities.filter(e => e.selected).length,
        by_type: { [customEntity.entity_type]: 1 }
      };
      
      console.log('Store - Custom entity added:', { newEntity, updatedStats });
      
      return {
        entities: updatedEntities,
        stats: updatedStats
      };
    });
  },
  
  selectAll: () => {
    console.log('Store - selectAll');
    set((state) => ({
      entities: state.entities.map((entity) => ({ ...entity, selected: true })),
    }));
  },
  
  deselectAll: () => {
    console.log('Store - deselectAll');
    set((state) => ({
      entities: state.entities.map((entity) => ({ ...entity, selected: false })),
    }));
  },
  
  setLoading: (isLoading) => {
    console.log('Store - setLoading:', isLoading);
    set({ isLoading });
  },
  
  setAnalyzing: (isAnalyzing) => {
    console.log('Store - setAnalyzing:', isAnalyzing);
    set({ isAnalyzing });
  },
  
  setGenerating: (isGenerating) => {
    console.log('Store - setGenerating:', isGenerating);
    set({ isGenerating });
  },
  
  setError: (error) => {
    console.log('Store - setError:', error);
    set({ error });
  },
  
  reset: () => {
    console.log('Store - reset');
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
    });
  },
  
  // Getters calculés corrigés avec gestion d'erreur
  getSelectedEntities: () => {
    const state = get();
    try {
      const selected = (state.entities || []).filter((entity) => entity.selected === true);
      console.log('Store - getSelectedEntities:', { total: state.entities?.length || 0, selected: selected.length });
      return selected;
    } catch (error) {
      console.error('Store - Error in getSelectedEntities:', error);
      return [];
    }
  },
  
  getSelectedCount: () => {
    const state = get();
    try {
      const count = (state.entities || []).filter((entity) => entity.selected === true).length;
      console.log('Store - getSelectedCount:', count);
      return count;
    } catch (error) {
      console.error('Store - Error in getSelectedCount:', error);
      return 0;
    }
  },
  
  getEntitiesByType: () => {
    const state = get();
    try {
      const grouped: Record<string, Entity[]> = {};
      
      (state.entities || []).forEach((entity) => {
        const type = entity.type || 'AUTRE';
        if (!grouped[type]) {
          grouped[type] = [];
        }
        grouped[type].push(entity);
      });
      
      console.log('Store - getEntitiesByType:', Object.keys(grouped).map(key => ({ type: key, count: grouped[key].length })));
      return grouped;
    } catch (error) {
      console.error('Store - Error in getEntitiesByType:', error);
      return {};
    }
  },
}));