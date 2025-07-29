// frontend/src/components/GroupementForm.tsx
// NOUVEAU FICHIER À CRÉER

import React, { useState } from 'react';
import { Plus, Users, X, Check } from 'lucide-react';
import { Entity, EntityType } from '../types/entities';

interface GroupFormProps {
  entities: Entity[];
  onCreateGroup: (groupData: GroupCreationData) => void;
  onClose: () => void;
}

interface GroupCreationData {
  groupName: string;
  groupType: string;
  groupReplacement: string;
  selectedEntities: string[];
  applyToSimilar: boolean;
}

const GroupementForm: React.FC<GroupFormProps> = ({ 
  entities, 
  onCreateGroup, 
  onClose 
}) => {
  const [formData, setFormData] = useState<GroupCreationData>({
    groupName: '',
    groupType: '',
    groupReplacement: '',
    selectedEntities: [],
    applyToSimilar: false
  });

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('ALL');

  // Filtrer les entités disponibles
  const availableEntities = entities.filter(entity => {
    const matchesSearch = entity.text.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = selectedType === 'ALL' || entity.type === selectedType;
    return matchesSearch && matchesType;
  });

  // Types d'entités uniques
  const uniqueTypes = [...new Set(entities.map(e => e.type))];

  const handleEntityToggle = (entityId: string) => {
    setFormData(prev => ({
      ...prev,
      selectedEntities: prev.selectedEntities.includes(entityId)
        ? prev.selectedEntities.filter(id => id !== entityId)
        : [...prev.selectedEntities, entityId]
    }));
  };

  const handleSelectAllVisible = () => {
    const visibleIds = availableEntities.map(e => e.id);
    setFormData(prev => ({
      ...prev,
      selectedEntities: [...new Set([...prev.selectedEntities, ...visibleIds])]
    }));
  };

  const handleCreateGroup = () => {
    if (!formData.groupName.trim() || !formData.groupReplacement.trim() || formData.selectedEntities.length === 0) {
      alert('Veuillez remplir tous les champs obligatoires et sélectionner au moins une entité');
      return;
    }

    // Auto-détection du type si pas spécifié
    if (!formData.groupType) {
      const selectedEntitiesData = entities.filter(e => formData.selectedEntities.includes(e.id));
      const types = [...new Set(selectedEntitiesData.map(e => e.type))];
      formData.groupType = types.length === 1 ? types[0] : 'MIXTE';
    }

    onCreateGroup(formData);
    onClose();
  };

  const getEntityPreview = () => {
    return entities
      .filter(e => formData.selectedEntities.includes(e.id))
      .map(e => e.text)
      .join(', ');
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        
        {/* En-tête */}
        <div className="bg-blue-600 text-white p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Users size={24} />
            <h2 className="text-xl font-bold">Créer un Groupe d'Entités</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Configuration du groupe */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <Users size={20} className="text-blue-600" />
                Configuration du Groupe
              </h3>
              
              <div>
                <label className="block text-sm font-medium mb-2">
                  Nom du groupe *
                </label>
                <input
                  type="text"
                  value={formData.groupName}
                  onChange={(e) => setFormData(prev => ({ ...prev, groupName: e.target.value }))}
                  placeholder="Ex: Avocats du Cabinet, Magistrats, Parties..."
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Type du groupe
                </label>
                <select
                  value={formData.groupType}
                  onChange={(e) => setFormData(prev => ({ ...prev, groupType: e.target.value }))}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Auto-détection</option>
                  {uniqueTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                  <option value="MIXTE">Type mixte</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Remplacement pour tout le groupe *
                </label>
                <input
                  type="text"
                  value={formData.groupReplacement}
                  onChange={(e) => setFormData(prev => ({ ...prev, groupReplacement: e.target.value }))}
                  placeholder="Ex: AVOCAT_A, MAGISTRAT_X, PARTIE_1..."
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="applyToSimilar"
                  checked={formData.applyToSimilar}
                  onChange={(e) => setFormData(prev => ({ ...prev, applyToSimilar: e.target.checked }))}
                  className="w-4 h-4 text-blue-600"
                />
                <label htmlFor="applyToSimilar" className="text-sm">
                  Appliquer aussi aux entités similaires détectées automatiquement
                </label>
              </div>

              {/* Aperçu */}
              {formData.selectedEntities.length > 0 && (
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h4 className="font-medium mb-2">Aperçu du groupe :</h4>
                  <p className="text-sm text-gray-700">
                    <strong>{formData.selectedEntities.length} entités</strong> seront remplacées par 
                    <strong className="text-blue-600"> "{formData.groupReplacement}"</strong>
                  </p>
                  <p className="text-xs text-gray-600 mt-2">
                    {getEntityPreview()}
                  </p>
                </div>
              )}
            </div>

            {/* Sélection des entités */}
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Sélectionner les Entités</h3>
              
              {/* Filtres */}
              <div className="space-y-3">
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Rechercher une entité..."
                  className="w-full px-3 py-2 border rounded-lg"
                />
                
                <div className="flex gap-2">
                  <select
                    value={selectedType}
                    onChange={(e) => setSelectedType(e.target.value)}
                    className="flex-1 px-3 py-2 border rounded-lg text-sm"
                  >
                    <option value="ALL">Tous les types</option>
                    {uniqueTypes.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                  
                  <button
                    onClick={handleSelectAllVisible}
                    className="px-3 py-2 bg-blue-100 text-blue-700 rounded-lg text-sm hover:bg-blue-200"
                  >
                    Tout sélectionner
                  </button>
                </div>
              </div>

              {/* Liste des entités */}
              <div className="border rounded-lg max-h-80 overflow-y-auto">
                {availableEntities.length === 0 ? (
                  <div className="p-4 text-center text-gray-500">
                    Aucune entité disponible
                  </div>
                ) : (
                  availableEntities.map(entity => (
                    <label 
                      key={entity.id}
                      className="flex items-center gap-3 p-3 hover:bg-gray-50 cursor-pointer border-b last:border-b-0"
                    >
                      <input
                        type="checkbox"
                        checked={formData.selectedEntities.includes(entity.id)}
                        onChange={() => handleEntityToggle(entity.id)}
                        className="w-4 h-4 text-blue-600"
                      />
                      <div className="flex-1">
                        <div className="font-medium">"{entity.text}"</div>
                        <div className="text-sm text-gray-500">
                          {entity.type} • {entity.occurrences} occurrence(s)
                        </div>
                      </div>
                    </label>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-gray-50 px-6 py-4 flex justify-between">
          <div className="text-sm text-gray-600">
            {formData.selectedEntities.length} entité(s) sélectionnée(s)
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg"
            >
              Annuler
            </button>
            <button
              onClick={handleCreateGroup}
              disabled={!formData.groupName.trim() || !formData.groupReplacement.trim() || formData.selectedEntities.length === 0}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Check size={16} />
              Créer le Groupe
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GroupementForm;