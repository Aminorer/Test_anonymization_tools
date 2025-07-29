import { create } from 'zustand';
import { Entity, EntityStats, CustomEntity, EntityGroup, EntityModification } from '../types/entities';

interface AnonymizerState {
  // État du document
  sessionId: string | null;
  filename: string | null;
  textPreview: string | null;
  
  // État des entités
  entities: Entity[];
  entityGroups: EntityGroup[];
  stats: EntityStats | null;
  
  // État de l'interface
  isLoading: boolean;
  isAnalyzing: boolean;
  isGenerating: boolean;
  error: string | null;
  
  // Nouveaux états pour l'édition
  editingEntity: Entity | null;
  selectedEntitiesForGrouping: string[];
  showGroupModal: boolean;
  showEditModal: boolean;
  
  // Actions de base
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
  
  // Nouvelles actions pour l'édition
  setEditingEntity: (entity: Entity | null) => void;
  modifyEntity: (entityId: string, newText: string, newReplacement?: string) => void;
  
  // Nouvelles actions pour les groupes
  toggleEntityForGrouping: (entityId: string) => void;
  setShowGroupModal: (show: boolean) => void;
  setShowEditModal: (show: boolean) => void;
  createEntityGroup: (name: string, replacement: string) => void;
  removeEntityGroup: (groupId: string) => void;
  updateGroupReplacement: (groupId: string, replacement: string) => void;
  toggleGroup: (groupId: string) => void;
  
  // Getters calculés
  getSelectedEntities: () => Entity[];
  getSelectedCount: () => number;
  getEntitiesByType: () => Record<string, Entity[]>;
  getUngroupedEntities: () => Entity[];
  getGroupableEntities: () => Entity[];
}

export const useAnonymizerStore = create<AnonymizerState>((set, get) => ({
  // État initial
  sessionId: null,
  filename: null,
  textPreview: null,
  entities: [],
  entityGroups: [],
  stats: null,
  isLoading: false,
  isAnalyzing: false,
  isGenerating: false,
  error: null,
  editingEntity: null,
  selectedEntitiesForGrouping: [],
  showGroupModal: false,
  showEditModal: false,
  
  // Actions de base
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
    
    const processedEntities = (entities || []).map((entity, index) => ({
      ...entity,
      id: entity.id || `entity-${index}`,
      selected: entity.selected !== undefined ? entity.selected : true,
      replacement: entity.replacement || `ANONYME_${index}`,
      occurrences: entity.occurrences || 1,
      confidence: entity.confidence || 0.8,
      source: entity.source || 'unknown',
      groupId: entity.groupId || undefined,
      isGrouped: entity.isGrouped || false,
      groupVariants: entity.groupVariants || []
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
      
      // Si l'entité fait partie d'un groupe, mettre à jour le groupe aussi
      const entity = state.entities.find(e => e.id === entityId);
      const updatedGroups = entity?.groupId 
        ? state.entityGroups.map(group => 
            group.id === entity.groupId 
              ? { ...group, selected: updatedEntities.find(e => e.id === entityId)?.selected || false }
              : group
          )
        : state.entityGroups;
      
      return { entities: updatedEntities, entityGroups: updatedGroups };
    });
  },
  
  updateReplacement: (entityId, replacement) => {
    console.log('Store - updateReplacement:', { entityId, replacement });
    set((state) => {
      const updatedEntities = state.entities.map((entity) =>
        entity.id === entityId
          ? { ...entity, replacement }
          : entity
      );
      
      // Si l'entité fait partie d'un groupe, mettre à jour le groupe aussi
      const entity = state.entities.find(e => e.id === entityId);
      const updatedGroups = entity?.groupId 
        ? state.entityGroups.map(group => 
            group.id === entity.groupId 
              ? { ...group, replacement }
              : group
          )
        : state.entityGroups;
      
      return { entities: updatedEntities, entityGroups: updatedGroups };
    });
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
      
      return { entities: [...state.entities, newEntity] };
    });
  },
  
  selectAll: () => {
    set((state) => ({
      entities: state.entities.map((entity) => ({ ...entity, selected: true })),
      entityGroups: state.entityGroups.map((group) => ({ ...group, selected: true }))
    }));
  },
  
  deselectAll: () => {
    set((state) => ({
      entities: state.entities.map((entity) => ({ ...entity, selected: false })),
      entityGroups: state.entityGroups.map((group) => ({ ...group, selected: false }))
    }));
  },
  
  setLoading: (isLoading) => set({ isLoading }),
  setAnalyzing: (isAnalyzing) => set({ isAnalyzing }),
  setGenerating: (isGenerating) => set({ isGenerating }),
  setError: (error) => set({ error }),
  
  // Nouvelles actions pour l'édition
  setEditingEntity: (editingEntity) => set({ editingEntity }),
  
  modifyEntity: (entityId, newText, newReplacement) => {
    console.log('Store - modifyEntity:', { entityId, newText, newReplacement });
    set((state) => ({
      entities: state.entities.map((entity) =>
        entity.id === entityId
          ? { 
              ...entity, 
              text: newText,
              replacement: newReplacement || entity.replacement
            }
          : entity
      ),
    }));
  },
  
  // Nouvelles actions pour les groupes
  toggleEntityForGrouping: (entityId) => {
    set((state) => {
      const isSelected = state.selectedEntitiesForGrouping.includes(entityId);
      return {
        selectedEntitiesForGrouping: isSelected
          ? state.selectedEntitiesForGrouping.filter(id => id !== entityId)
          : [...state.selectedEntitiesForGrouping, entityId]
      };
    });
  },
  
  setShowGroupModal: (showGroupModal) => set({ showGroupModal }),
  setShowEditModal: (showEditModal) => set({ showEditModal }),
  
  createEntityGroup: (name, replacement) => {
    set((state) => {
      const groupId = `group-${Date.now()}`;
      const selectedEntities = state.entities.filter(e => 
        state.selectedEntitiesForGrouping.includes(e.id)
      );
      
      const newGroup: EntityGroup = {
        id: groupId,
        name,
        entities: selectedEntities,
        replacement,
        type: selectedEntities[0]?.type || 'PERSONNE' as any,
        selected: true
      };
      
      // Marquer les entités comme groupées
      const updatedEntities = state.entities.map(entity =>
        state.selectedEntitiesForGrouping.includes(entity.id)
          ? { ...entity, groupId, isGrouped: true, replacement, selected: true }
          : entity
      );
      
      return {
        entityGroups: [...state.entityGroups, newGroup],
        entities: updatedEntities,
        selectedEntitiesForGrouping: [],
        showGroupModal: false
      };
    });
  },
  
  removeEntityGroup: (groupId) => {
    set((state) => {
      // Dégrouper les entités
      const updatedEntities = state.entities.map(entity =>
        entity.groupId === groupId
          ? { ...entity, groupId: undefined, isGrouped: false }
          : entity
      );
      
      return {
        entityGroups: state.entityGroups.filter(g => g.id !== groupId),
        entities: updatedEntities
      };
    });
  },
  
  updateGroupReplacement: (groupId, replacement) => {
    set((state) => {
      const updatedGroups = state.entityGroups.map(group =>
        group.id === groupId ? { ...group, replacement } : group
      );
      
      const updatedEntities = state.entities.map(entity =>
        entity.groupId === groupId ? { ...entity, replacement } : entity
      );
      
      return { entityGroups: updatedGroups, entities: updatedEntities };
    });
  },
  
  toggleGroup: (groupId) => {
    set((state) => {
      const updatedGroups = state.entityGroups.map(group =>
        group.id === groupId ? { ...group, selected: !group.selected } : group
      );
      
      const group = updatedGroups.find(g => g.id === groupId);
      const updatedEntities = state.entities.map(entity =>
        entity.groupId === groupId 
          ? { ...entity, selected: group?.selected || false }
          : entity
      );
      
      return { entityGroups: updatedGroups, entities: updatedEntities };
    });
  },
  
  reset: () => {
    set({
      sessionId: null,
      filename: null,
      textPreview: null,
      entities: [],
      entityGroups: [],
      stats: null,
      isLoading: false,
      isAnalyzing: false,
      isGenerating: false,
      error: null,
      editingEntity: null,
      selectedEntitiesForGrouping: [],
      showGroupModal: false,
      showEditModal: false,
    });
  },
  
  // Getters calculés
  getSelectedEntities: () => {
    const state = get();
    try {
      return (state.entities || []).filter((entity) => entity.selected === true);
    } catch (error) {
      console.error('Store - Error in getSelectedEntities:', error);
      return [];
    }
  },
  
  getSelectedCount: () => {
    const state = get();
    try {
      return (state.entities || []).filter((entity) => entity.selected === true).length;
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
      
      return grouped;
    } catch (error) {
      console.error('Store - Error in getEntitiesByType:', error);
      return {};
    }
  },
  
  getUngroupedEntities: () => {
    const state = get();
    return (state.entities || []).filter(entity => !entity.isGrouped);
  },
  
  getGroupableEntities: () => {
    const state = get();
    return (state.entities || []).filter(entity => 
      !entity.isGrouped && state.selectedEntitiesForGrouping.includes(entity.id)
    );
  }
}));