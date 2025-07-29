import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, Edit3, Plus, Download, Eye, CheckCircle, 
  AlertCircle, ArrowLeft, Shield 
} from 'lucide-react';
import { useAnonymizerStore } from '../stores/anonymizerStore';
import { generateAnonymizedDocument, addCustomEntity } from '../services/api';
import { ENTITY_TYPES_CONFIG, EntityType, CustomEntity, Entity } from '../types/entities';

const EntityControlPage: React.FC = () => {
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
      entities: entities?.slice(0, 3), // Premiers éléments pour debug
      stats
    });
  }, [sessionId, filename, entities, stats]);

  // Rediriger si pas de session
  useEffect(() => {
    if (!sessionId || !filename) {
      console.warn('Redirection - Session ou filename manquant');
      navigate('/');
    }
  }, [sessionId, filename, navigate]);

  // Gestionnaire de filtres amélioré
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

  // Sources disponibles dynamiquement
  const availableSources = React.useMemo(() => {
    if (!entities || entities.length === 0) return [];
    const sources = [...new Set(entities.map(e => e.source))];
    console.log('Sources disponibles:', sources);
    return sources;
  }, [entities]);

  // Entités filtrées
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

  // Entités groupées par type
  const groupedEntities = React.useMemo(() => {
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
  }, [filteredEntities]);

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

      // Reset du formulaire
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
      
      // Téléchargement du fichier
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `anonymized_${filename}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      // Redirection vers la page d'accueil après succès
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
      {/* En-tête avec statistiques */}
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
                  {entities?.length || 0} entités détectées • {filteredEntities.length} affichées • {selectedCount}/{entities?.length || 0} sélectionnées
                </p>
              </div>
            </div>
            <div className="flex gap-3">
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
                <h2 className="text-xl font-semibold">Entités à anonymiser</h2>
                <p className="text-gray-600 mt-1">
                  Cochez les entités à anonymiser et personnalisez les remplacements
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
                    const config = getEntityTypeConfig(type);
                    
                    return (
                      <div key={type} className="border-b last:border-b-0">
                        <div 
                          className="p-4 font-medium flex items-center gap-3"
                          style={{ backgroundColor: `${config.color}10` }}
                        >
                          <span className="text-2xl">{config.icon}</span>
                          <span>{type}</span>
                          <span className="text-sm text-gray-500">({typeEntities.length})</span>
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
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex items-center gap-3">
                                {type === 'SIRET/SIREN' && config.replacement_options ? (
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
                                    disabled={!entity.selected}
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
                  onChange={(e) => setCustomEntityForm({...customEntityForm, entity_type: e.target.value as EntityType})}
                  className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {Object.values(EntityType).map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder="Remplacer par..."
                  value={customEntityForm.replacement}
                  onChange={(e) => setCustomEntityForm({...customEntityForm, replacement: e.target.value})}
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
    </div>
  );
};

export default EntityControlPage;