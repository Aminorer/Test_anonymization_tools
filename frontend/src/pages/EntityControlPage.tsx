import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, Edit3, Plus, Download, Eye, CheckCircle, 
  AlertCircle, ArrowLeft, Shield, Users, Shuffle,
  UserPlus, Settings, Layers
} from 'lucide-react';
import { useAnonymizerStore } from '../stores/anonymizerStore';
import { generateAnonymizedDocument, addCustomEntity } from '../services/api';
import { ENTITY_TYPES_CONFIG, EntityType, CustomEntity, Entity } from '../types/entities';
import GroupementForm from '../components/GroupementForm';

interface EntityGroup {
  id: string;
  name: string;
  type: string;
  replacement: string;
  entities: string[]; // IDs des entités
  color: string;
}

const EnhancedEntityControlPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    sessionId,
    filename,
    entities,
    stats,
    toggleEntity,
    updateReplacement,
    addCustomEntity: addToStore,
    selectAll,
    deselectAll,
    getSelectedEntities,
    getSelectedCount,
    getEntitiesByType,
    setGenerating,
    setError,
    isGenerating,
    error,
    textPreview
  } = useAnonymizerStore();

  // États pour le groupement
  const [entityGroups, setEntityGroups] = useState<EntityGroup[]>([]);
  const [showGroupForm, setShowGroupForm] = useState(false);
  const [showAutoGroupModal, setShowAutoGroupModal] = useState(false);
  const [groupViewMode, setGroupViewMode] = useState<'individual' | 'grouped'>('individual');

  // États existants
  const [customEntityForm, setCustomEntityForm] = useState({
    text: '',
    entity_type: EntityType.PERSONNE,
    replacement: ''
  });
  const [showPreview, setShowPreview] = useState(false);
  const [sourceFilters, setSourceFilters] = useState({
    regex_french: true,
    regex_validated: true,
    llm_ollama: true,
    ollama_chunk: true,
    manual: true,
    spacy_targeted: true
  });

  // Debug logs
  useEffect(() => {
    console.log('EntityControlPage - État:', {
      sessionId,
      filename,
      entitiesCount: entities?.length || 0,
      entities: entities?.slice(0, 3),
      stats,
      groupsCount: entityGroups.length
    });
  }, [sessionId, filename, entities, stats, entityGroups]);

  // Rediriger si pas de session
  useEffect(() => {
    if (!sessionId || !filename) {
      console.warn('Redirection - Session ou filename manquant');
      navigate('/');
    }
  }, [sessionId, filename, navigate]);

  // Fonctions de groupement
  const createGroup = (groupData: {
    groupName: string;
    groupType: string;
    groupReplacement: string;
    selectedEntities: string[];
    applyToSimilar: boolean;
  }) => {
    const newGroup: EntityGroup = {
      id: `group-${Date.now()}`,
      name: groupData.groupName,
      type: groupData.groupType,
      replacement: groupData.groupReplacement,
      entities: groupData.selectedEntities,
      color: getRandomColor()
    };

    setEntityGroups(prev => [...prev, newGroup]);

    // Appliquer le remplacement à toutes les entités du groupe
    groupData.selectedEntities.forEach(entityId => {
      updateReplacement(entityId, groupData.groupReplacement);
    });

    // Si demandé, appliquer aussi aux entités similaires
    if (groupData.applyToSimilar) {
      applySimilarGrouping(newGroup);
    }

    console.log('Groupe créé:', newGroup);
  };

  const applySimilarGrouping = (group: EntityGroup) => {
    const groupEntities = entities.filter(e => group.entities.includes(e.id));
    const similarEntities: string[] = [];

    groupEntities.forEach(groupEntity => {
      entities.forEach(entity => {
        if (!group.entities.includes(entity.id) && 
            !entityGroups.some(g => g.entities.includes(entity.id))) {
          
          // Logique de similarité
          const isSimilar = (
            entity.type === groupEntity.type ||
            entity.text.toLowerCase().includes(groupEntity.text.toLowerCase()) ||
            groupEntity.text.toLowerCase().includes(entity.text.toLowerCase())
          );

          if (isSimilar && !similarEntities.includes(entity.id)) {
            similarEntities.push(entity.id);
            updateReplacement(entity.id, group.replacement);
          }
        }
      });
    });

    if (similarEntities.length > 0) {
      setEntityGroups(prev => 
        prev.map(g => 
          g.id === group.id 
            ? { ...g, entities: [...g.entities, ...similarEntities] }
            : g
        )
      );
    }
  };

  const autoGroupSimilarEntities = () => {
    const newGroups: EntityGroup[] = [];
    const processedEntities = new Set<string>();

    entities.forEach(entity => {
      if (processedEntities.has(entity.id)) return;

      // Chercher des entités similaires
      const similarEntities = entities.filter(e => 
        !processedEntities.has(e.id) &&
        e.type === entity.type &&
        (
          e.text.toLowerCase().includes(entity.text.toLowerCase()) ||
          entity.text.toLowerCase().includes(e.text.toLowerCase()) ||
          levenshteinDistance(e.text.toLowerCase(), entity.text.toLowerCase()) <= 2
        )
      );

      if (similarEntities.length >= 2) {
        const groupName = `Groupe ${entity.type} ${newGroups.length + 1}`;
        const groupReplacement = `${entity.type}_${newGroups.length + 1}`;

        const newGroup: EntityGroup = {
          id: `auto-group-${Date.now()}-${newGroups.length}`,
          name: groupName,
          type: entity.type,
          replacement: groupReplacement,
          entities: similarEntities.map(e => e.id),
          color: getRandomColor()
        };

        newGroups.push(newGroup);

        // Marquer comme traités
        similarEntities.forEach(e => {
          processedEntities.add(e.id);
          updateReplacement(e.id, groupReplacement);
        });
      }
    });

    setEntityGroups(prev => [...prev, ...newGroups]);
    setShowAutoGroupModal(false);
    
    console.log(`${newGroups.length} groupes automatiques créés`);
  };

  const removeGroup = (groupId: string) => {
    const group = entityGroups.find(g => g.id === groupId);
    if (group) {
      // Restaurer les remplacements individuels
      group.entities.forEach(entityId => {
        const entity = entities.find(e => e.id === entityId);
        if (entity) {
          const config = getEntityTypeConfig(entity.type);
          updateReplacement(entityId, `${config.default_replacement}_${Math.random().toString(36).substr(2, 4)}`);
        }
      });
    }

    setEntityGroups(prev => prev.filter(g => g.id !== groupId));
  };

  const getRandomColor = () => {
    const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4'];
    return colors[Math.floor(Math.random() * colors.length)];
  };

  const levenshteinDistance = (str1: string, str2: string): number => {
    const matrix = Array(str2.length + 1).fill(null).map(() => Array(str1.length + 1).fill(null));
    for (let i = 0; i <= str1.length; i++) matrix[0][i] = i;
    for (let j = 0; j <= str2.length; j++) matrix[j][0] = j;
    for (let j = 1; j <= str2.length; j++) {
      for (let i = 1; i <= str1.length; i++) {
        const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
        matrix[j][i] = Math.min(
          matrix[j][i - 1] + 1,
          matrix[j - 1][i] + 1,
          matrix[j - 1][i - 1] + indicator,
        );
      }
    }
    return matrix[str2.length][str1.length];
  };

  // Fonctions existantes
  const toggleSourceFilter = (source: string) => {
    console.log('Toggle filter:', source);
    setSourceFilters(prev => {
      const newFilters = {
        ...prev,
        [source]: !prev[source]
      };
      console.log('Nouveaux filtres:', newFilters);
      return newFilters;
    });
  };

  const availableSources = React.useMemo(() => {
    if (!entities || entities.length === 0) return [];
    const sources = [...new Set(entities.map(e => e.source))];
    console.log('Sources disponibles:', sources);
    return sources;
  }, [entities]);

  const filteredEntities = React.useMemo(() => {
    if (!entities || entities.length === 0) {
      console.log('Pas d\'entités à filtrer');
      return [];
    }

    const filtered = entities.filter(entity => {
      const sourceKey = entity.source;
      const isIncluded = sourceFilters[sourceKey as keyof typeof sourceFilters] !== false;
      return isIncluded;
    });

    console.log('Entités filtrées:', {
      total: entities.length,
      filtered: filtered.length,
      activeFilters: Object.entries(sourceFilters).filter(([_, active]) => active)
    });

    return filtered;
  }, [entities, sourceFilters]);

  const groupedEntities = React.useMemo(() => {
    if (groupViewMode === 'individual') {
      const grouped: Record<string, Entity[]> = {};
      
      filteredEntities.forEach((entity) => {
        const type = entity.type;
        if (!grouped[type]) {
          grouped[type] = [];
        }
        grouped[type].push(entity);
      });

      console.log('Entités groupées:', Object.keys(grouped).map(key => ({ type: key, count: grouped[key].length })));
      return grouped;
    } else {
      // Mode groupé par groupes d'entités
      const grouped: Record<string, Entity[]> = {};
      
      // Ajouter les groupes
      entityGroups.forEach(group => {
        grouped[`GROUP:${group.name}`] = entities.filter(e => group.entities.includes(e.id));
      });

      // Ajouter les entités non groupées
      const ungroupedEntities = filteredEntities.filter(entity => 
        !entityGroups.some(group => group.entities.includes(entity.id))
      );

      ungroupedEntities.forEach(entity => {
        const type = `INDIVIDUAL:${entity.type}`;
        if (!grouped[type]) {
          grouped[type] = [];
        }
        grouped[type].push(entity);
      });

      return grouped;
    }
  }, [filteredEntities, entityGroups, groupViewMode]);

  const selectedEntities = getSelectedEntities();
  const selectedCount = getSelectedCount();

  const getSourceLabel = (source: string) => {
    const labels: Record<string, string> = {
      'regex_french': 'Regex Français',
      'regex_validated': 'Regex Validé',
      'llm_ollama': 'LLM Ollama',
      'ollama_chunk': 'Ollama Chunk',
      'manual': 'Manuel',
      'spacy_targeted': 'SpaCy'
    };
    return labels[source] || source;
  };

  const getSourceBadgeStyle = (source: string) => {
    const styles: Record<string, string> = {
      'regex_french': 'bg-green-100 text-green-700',
      'regex_validated': 'bg-green-100 text-green-700',
      'llm_ollama': 'bg-purple-100 text-purple-700',
      'ollama_chunk': 'bg-purple-100 text-purple-700',
      'manual': 'bg-blue-100 text-blue-700',
      'spacy_targeted': 'bg-orange-100 text-orange-700'
    };
    return styles[source] || 'bg-gray-100 text-gray-700';
  };

  const handleSelectAll = () => {
    selectAll();
  };

  const handleDeselectAll = () => {
    deselectAll();
  };

  const handleAddCustomEntity = async () => {
    if (!customEntityForm.text.trim() || !customEntityForm.replacement.trim()) {
      setError('Veuillez remplir tous les champs obligatoires');
      return;
    }

    if (!sessionId) {
      setError('Session invalide');
      return;
    }

    try {
      const customEntity: CustomEntity = {
        text: customEntityForm.text.trim(),
        entity_type: customEntityForm.entity_type,
        replacement: customEntityForm.replacement.trim()
      };

      await addCustomEntity(sessionId, customEntity);
      addToStore(customEntity);

      setCustomEntityForm({
        text: '',
        entity_type: EntityType.PERSONNE,
        replacement: ''
      });

      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur lors de l\'ajout de l\'entité';
      setError(errorMessage);
    }
  };

  const handleGenerateDocument = async () => {
    if (selectedCount === 0) {
      setError('Veuillez sélectionner au moins une entité à anonymiser');
      return;
    }

    if (!sessionId) {
      setError('Session invalide');
      return;
    }

    try {
      setError(null);
      setGenerating(true);

      const blob = await generateAnonymizedDocument(sessionId, selectedEntities);
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `anonymized_${filename}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setTimeout(() => {
        navigate('/');
      }, 2000);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur lors de la génération du document';
      setError(errorMessage);
    } finally {
      setGenerating(false);
    }
  };

  const getEntityTypeConfig = (type: string) => {
    return ENTITY_TYPES_CONFIG[type] || ENTITY_TYPES_CONFIG['AUTRE'] || {
      color: '#6b7280',
      icon: '❓',
      default_replacement: 'ENTITE_X'
    };
  };

  if (!sessionId || !filename) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p>Chargement de la session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* En-tête avec statistiques et contrôles groupement */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft size={20} />
              </button>
              <FileText size={24} className="text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold">{filename}</h1>
                <p className="text-gray-600">
                  {entities?.length || 0} entités • {filteredEntities.length} affichées • {selectedCount}/{entities?.length || 0} sélectionnées
                  {entityGroups.length > 0 && ` • ${entityGroups.length} groupes`}
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              {/* Contrôles de groupement */}
              <div className="flex items-center gap-2 border-r pr-3">
                <button
                  onClick={() => setGroupViewMode(groupViewMode === 'individual' ? 'grouped' : 'individual')}
                  className={`px-3 py-2 rounded-lg transition-colors flex items-center gap-2 ${
                    groupViewMode === 'grouped' 
                      ? 'bg-blue-100 text-blue-700' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Layers size={16} />
                  {groupViewMode === 'individual' ? 'Vue groupée' : 'Vue individuelle'}
                </button>
                
                <button
                  onClick={() => setShowAutoGroupModal(true)}
                  className="px-3 py-2 bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg transition-colors flex items-center gap-2"
                >
                  <Shuffle size={16} />
                  Groupement auto
                </button>
                
                <button
                  onClick={() => setShowGroupForm(true)}
                  className="px-3 py-2 bg-green-100 text-green-700 hover:bg-green-200 rounded-lg transition-colors flex items-center gap-2"
                >
                  <UserPlus size={16} />
                  Créer groupe
                </button>
              </div>

              <button
                onClick={handleSelectAll}
                className="px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              >
                Tout sélectionner
              </button>
              <button
                onClick={handleDeselectAll}
                className="px-4 py-2 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
              >
                Tout désélectionner
              </button>
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-2"
              >
                <Eye size={16} />
                {showPreview ? 'Masquer' : 'Aperçu'}
              </button>
            </div>
          </div>
          
          {/* Groupes existants */}
          {entityGroups.length > 0 && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg">
              <h3 className="font-medium mb-3 flex items-center gap-2">
                <Users size={16} className="text-blue-600" />
                Groupes actifs ({entityGroups.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {entityGroups.map(group => (
                  <div 
                    key={group.id}
                    className="flex items-center gap-2 bg-white px-3 py-2 rounded-lg border shadow-sm"
                  >
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: group.color }}
                    ></div>
                    <span className="font-medium">{group.name}</span>
                    <span className="text-sm text-gray-500">({group.entities.length})</span>
                    <span className="text-sm bg-gray-100 px-2 py-1 rounded">→ {group.replacement}</span>
                    <button
                      onClick={() => removeGroup(group.id)}
                      className="text-red-500 hover:text-red-700 ml-2"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Colonne principale : Liste des entités */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Filtres par source */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                🔧 Filtrer par source de détection
              </h3>
              <div className="flex flex-wrap gap-3">
                {availableSources.map(source => {
                  const entityCount = entities?.filter(e => e.source === source).length || 0;
                  
                  return (
                    <label key={source} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={sourceFilters[source as keyof typeof sourceFilters] !== false}
                        onChange={() => toggleSourceFilter(source)}
                        className="w-4 h-4 text-blue-600"
                      />
                      <span className="text-sm font-medium">{getSourceLabel(source)}</span>
                      <span className={`text-xs px-2 py-1 rounded ${getSourceBadgeStyle(source)}`}>
                        {entityCount}
                      </span>
                    </label>
                  );
                })}
              </div>
              <div className="text-xs text-gray-500 mt-2 space-y-1">
                <p>✅ <strong>Regex</strong> : Données structurées fiables (téléphone, email, SIRET, etc.)</p>
                <p>🧠 <strong>LLM Ollama</strong> : Entités complexes analysées par IA locale (noms, organisations)</p>
                <p>💡 Mode "Standard" = Regex seul | Mode "Approfondi" = Regex + LLM</p>
              </div>
            </div>

            {/* Affichage d'erreur */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle size={20} className="text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-red-800">Erreur</h4>
                  <p className="text-red-700 text-sm mt-1">{error}</p>
                </div>
              </div>
            )}

            {/* Aperçu du texte */}
            {showPreview && textPreview && (
              <div className="bg-white rounded-xl shadow-sm">
                <div className="p-6 border-b">
                  <h3 className="text-lg font-semibold">Aperçu du document</h3>
                </div>
                <div className="p-6 max-h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
                    {textPreview}
                  </pre>
                </div>
              </div>
            )}

            {/* Liste des entités */}
            <div className="bg-white rounded-xl shadow-sm">
              <div className="p-6 border-b">
                <h2 className="text-xl font-semibold">
                  Entités à anonymiser
                  {groupViewMode === 'grouped' && ' (Vue par groupes)'}
                </h2>
                <p className="text-gray-600 mt-1">
                  {groupViewMode === 'individual' 
                    ? 'Cochez les entités à anonymiser et personnalisez les remplacements'
                    : 'Vue par groupes d\'entités - modifiez les groupes ou créez-en de nouveaux'
                  }
                </p>
              </div>
              
              {/* Message si aucune entité */}
              {filteredEntities.length === 0 ? (
                <div className="p-8 text-center">
                  <div className="text-gray-400 mb-4">
                    <FileText size={48} className="mx-auto" />
                  </div>
                  <h3 className="text-lg font-medium text-gray-600 mb-2">Aucune entité trouvée</h3>
                  <p className="text-gray-500">
                    {entities?.length === 0 
                      ? 'Aucune entité détectée dans le document'
                      : 'Toutes les entités sont filtrées. Ajustez les filtres ci-dessus.'
                    }
                  </p>
                </div>
              ) : (
                <div className="max-h-96 overflow-y-auto">
                  {Object.entries(groupedEntities).map(([type, typeEntities]) => {
                    const isGroup = type.startsWith('GROUP:');
                    const isIndividual = type.startsWith('INDIVIDUAL:');
                    
                    let config, displayType, groupInfo = null;
                    
                    if (isGroup) {
                      const groupName = type.replace('GROUP:', '');
                      groupInfo = entityGroups.find(g => g.name === groupName);
                      config = { color: groupInfo?.color || '#6b7280', icon: '👥', default_replacement: groupInfo?.replacement || 'GROUP_X' };
                      displayType = `🔗 ${groupName}`;
                    } else if (isIndividual) {
                      const actualType = type.replace('INDIVIDUAL:', '');
                      config = getEntityTypeConfig(actualType);
                      displayType = actualType;
                    } else {
                      config = getEntityTypeConfig(type);
                      displayType = type;
                    }
                    
                    return (
                      <div key={type} className="border-b last:border-b-0">
                        <div 
                          className="p-4 font-medium flex items-center gap-3"
                          style={{ backgroundColor: `${config.color}10` }}
                        >
                          <span className="text-2xl">{config.icon}</span>
                          <span>{displayType}</span>
                          <span className="text-sm text-gray-500">({typeEntities.length})</span>
                          {isGroup && groupInfo && (
                            <div className="ml-auto flex items-center gap-2">
                              <span className="text-xs bg-white px-2 py-1 rounded">
                                → {groupInfo.replacement}
                              </span>
                              <button
                                onClick={() => removeGroup(groupInfo.id)}
                                className="text-red-500 hover:text-red-700 text-xs"
                              >
                                Supprimer groupe
                              </button>
                            </div>
                          )}
                          {type === 'SIRET/SIREN' && (
                            <div className="ml-auto text-xs text-orange-700 bg-orange-200 px-2 py-1 rounded">
                              Validation checksum activée
                            </div>
                          )}
                        </div>
                        
                        {typeEntities.map((entity) => (
                          <div key={entity.id} className="p-4 border-b last:border-b-0 hover:bg-gray-50">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-4 flex-1">
                                <input
                                  type="checkbox"
                                  checked={entity.selected}
                                  onChange={() => toggleEntity(entity.id)}
                                  className="w-5 h-5 text-blue-600"
                                />
                                
                                <div className="flex-1">
                                  <div className="font-medium font-mono">"{entity.text}"</div>
                                  <div className="text-sm text-gray-500 flex items-center gap-4">
                                    <span>Apparaît {entity.occurrences} fois</span>
                                    <span>Confiance: {Math.round(entity.confidence * 100)}%</span>
                                    <span className="flex items-center gap-1">
                                      {entity.valid !== false ? (
                                        <><CheckCircle size={12} className="text-green-600" /> Valide</>
                                      ) : (
                                        <><AlertCircle size={12} className="text-red-600" /> Format suspect</>
                                      )}
                                    </span>
                                    <span className={`text-xs px-2 py-1 rounded ${getSourceBadgeStyle(entity.source)}`}>
                                      {getSourceLabel(entity.source)}
                                    </span>
                                    {isGroup && (
                                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                                        Groupé
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex items-center gap-3">
                                {!isGroup && type === 'SIRET/SIREN' && config.replacement_options ? (
                                  <select 
                                    value={entity.replacement}
                                    onChange={(e) => updateReplacement(entity.id, e.target.value)}
                                    className="px-3 py-1 border rounded text-sm w-40"
                                    disabled={!entity.selected}
                                  >
                                    {config.replacement_options.map(option => (
                                      <option key={option} value={option}>{option}</option>
                                    ))}
                                    <option value="custom">Personnalisé...</option>
                                  </select>
                                ) : (
                                  <input
                                    type="text"
                                    value={entity.replacement}
                                    onChange={(e) => updateReplacement(entity.id, e.target.value)}
                                    placeholder={config.default_replacement}
                                    className="px-3 py-1 border rounded text-sm w-32"
                                    disabled={!entity.selected || isGroup}
                                  />
                                )}
                                <button className="text-blue-600 hover:text-blue-800 p-1">
                                  <Edit3 size={16} />
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Colonne latérale : Actions */}
          <div className="space-y-6">
            
            {/* Ajout d'entité manuelle */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Plus size={20} />
                Ajouter entité manuelle
              </h3>
              <div className="space-y-4">
                <input
                  type="text"
                  placeholder="Texte à anonymiser"
                  value={customEntityForm.text}
                  onChange={(e) => setCustomEntityForm({...customEntityForm, text: e.target.value})}
                  className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <select
                  value={customEntityForm.entity_type}
                  onChange={(e) =>
                    setCustomEntityForm({
                      ...customEntityForm,
                      entity_type: e.target.value as EntityType,
                    })
                  }
                  className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Object.values(EntityType).map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder="Remplacer par..."
                  value={customEntityForm.replacement}
                  onChange={(e) =>
                    setCustomEntityForm({
                      ...customEntityForm,
                      replacement: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleAddCustomEntity}
                  className="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 transition-colors"
                >
                  Ajouter
                </button>
              </div>
            </div>

            {/* Nouvelles fonctionnalités */}
            <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl p-6 border border-purple-200">
              <h3 className="font-semibold mb-4 text-purple-800">🆕 Nouvelles fonctionnalités</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2">
                  <Edit3 size={14} className="text-blue-600" />
                  <span><strong>Modification d'entités</strong> : Éditez le texte à anonymiser</span>
                </div>
                <div className="flex items-center gap-2">
                  <Shuffle size={14} className="text-purple-600" />
                  <span><strong>Groupement d'entités</strong> : Anonymisez plusieurs variantes ensemble</span>
                </div>
                <div className="text-xs text-gray-600 mt-2">
                  💡 Exemple : Grouper "Monsieur OULHADJ" et "Monsieur Saïd OULHADJ" pour les remplacer tous deux par "Monsieur X"
                </div>
              </div>
            </div>

            {/* Statistiques */}
            {stats && (
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h3 className="font-semibold mb-4">Statistiques</h3>
                <div className="space-y-3">
                  {Object.entries(stats.by_type).map(([type, count]) => {
                    const config = getEntityTypeConfig(type);
                    return (
                      <div key={type} className="flex items-center justify-between">
                        <span className="flex items-center gap-2 text-sm">
                          <span>{config.icon}</span>
                          <span>{type}</span>
                        </span>
                        <span className="text-sm font-medium">{count}</span>
                      </div>
                    );
                  })}
                  {entityGroups.length > 0 && (
                    <div className="flex items-center justify-between pt-2 border-t">
                      <span className="flex items-center gap-2 text-sm">
                        <span>🔗</span>
                        <span>Groupes</span>
                      </span>
                      <span className="text-sm font-medium">{entityGroups.length}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Bouton de génération */}
            <div className="bg-blue-50 rounded-xl p-6 border-2 border-blue-200">
              <div className="text-center mb-4">
                <Shield size={24} className="mx-auto text-blue-600 mb-2" />
                <h3 className="font-semibold text-lg">Prêt pour l'anonymisation</h3>
                <p className="text-sm text-gray-600 mt-2">
                  {selectedCount} entités sélectionnées<br />
                  Format DOCX préservé • Conformité RGPD
                </p>
              </div>
              <button
                disabled={selectedCount === 0 || isGenerating}
                onClick={handleGenerateDocument}
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full"></div>
                    Génération...
                  </>
                ) : (
                  <>
                    <Download size={20} />
                    Générer document anonymisé
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Vues de groupement */}
      {showGroupForm && (
        <GroupementForm
          entities={entities}
          onCreateGroup={createGroup}
          onClose={() => setShowGroupForm(false)}
        />
      )}
      {showAutoGroupModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-lg space-y-4">
            <h3 className="font-semibold text-lg">Grouper les entités similaires ?</h3>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowAutoGroupModal(false)}
                className="px-4 py-2 bg-gray-100 rounded hover:bg-gray-200"
              >
                Annuler
              </button>
              <button
                onClick={autoGroupSimilarEntities}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Confirmer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhancedEntityControlPage;
