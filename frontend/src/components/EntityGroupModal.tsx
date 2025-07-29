import React, { useState } from 'react';
import { X, Link, Users, Save } from 'lucide-react';
import { Entity } from '../types/entities';

interface EntityGroupModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedEntities: Entity[];
  onCreateGroup: (name: string, replacement: string) => void;
  onApiCreateGroup?: (name: string, replacement: string) => Promise<void>;
}

const EntityGroupModal: React.FC<EntityGroupModalProps> = ({
  isOpen,
  onClose,
  selectedEntities,
  onCreateGroup,
  onApiCreateGroup
}) => {
  const [groupName, setGroupName] = useState('');
  const [groupReplacement, setGroupReplacement] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (isOpen && selectedEntities.length > 0) {
      // Générer un nom de groupe par défaut
      const firstEntity = selectedEntities[0];
      const defaultName = `Groupe ${firstEntity.type}`;
      setGroupName(defaultName);
      
      // Générer un remplacement par défaut
      const baseReplacement = firstEntity.replacement.replace(/_\d+$/, '');
      setGroupReplacement(baseReplacement);
      setError(null);
    }
  }, [isOpen, selectedEntities]);

  const handleCreateGroup = async () => {
    if (!groupName.trim() || !groupReplacement.trim()) {
      setError('Veuillez remplir tous les champs');
      return;
    }

    if (selectedEntities.length < 2) {
      setError('Sélectionnez au moins 2 entités pour créer un groupe');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Appel API si fourni
      if (onApiCreateGroup) {
        await onApiCreateGroup(groupName.trim(), groupReplacement.trim());
      }

      // Mise à jour locale
      onCreateGroup(groupName.trim(), groupReplacement.trim());
      
      // Reset et fermeture
      setGroupName('');
      setGroupReplacement('');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la création du groupe');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold flex items-center gap-2">
            <Link size={20} className="text-purple-600" />
            Grouper les entités
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* Aperçu des entités sélectionnées */}
        <div className="mb-6">
          <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
            <Users size={16} />
            Entités sélectionnées ({selectedEntities.length}) :
          </h4>
          <div className="bg-gray-50 rounded-lg p-4 max-h-48 overflow-y-auto">
            {selectedEntities.length === 0 ? (
              <p className="text-gray-500 text-sm text-center py-4">
                Aucune entité sélectionnée. Fermez ce modal et sélectionnez des entités à grouper.
              </p>
            ) : (
              <div className="space-y-2">
                {selectedEntities.map((entity) => (
                  <div key={entity.id} className="flex items-center justify-between p-2 bg-white rounded border">
                    <div className="flex-1">
                      <span className="font-mono text-sm">{entity.text}</span>
                      <div className="text-xs text-gray-500">
                        {entity.type} • {entity.occurrences} occurrence(s)
                      </div>
                    </div>
                    <div className="text-xs text-gray-400">
                      → {entity.replacement}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {selectedEntities.length > 0 && (
          <>
            {/* Configuration du groupe */}
            <div className="space-y-4 mb-6">
              <div>
                <label htmlFor="group-name" className="block text-sm font-medium text-gray-700 mb-2">
                  Nom du groupe * :
                </label>
                <input
                  id="group-name"
                  type="text"
                  value={groupName}
                  onChange={(e) => setGroupName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Ex: Groupe Personne Principale"
                />
              </div>

              <div>
                <label htmlFor="group-replacement" className="block text-sm font-medium text-gray-700 mb-2">
                  Remplacement commun * :
                </label>
                <input
                  id="group-replacement"
                  type="text"
                  value={groupReplacement}
                  onChange={(e) => setGroupReplacement(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="Ex: Monsieur X"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Toutes les entités du groupe seront remplacées par cette valeur
                </p>
              </div>
            </div>

            {/* Aperçu du résultat */}
            <div className="bg-purple-50 p-4 rounded-lg border-l-4 border-purple-400 mb-6">
              <h4 className="font-medium text-purple-800 mb-2">Aperçu du groupement :</h4>
              <div className="text-sm space-y-1">
                {selectedEntities.slice(0, 3).map((entity, index) => (
                  <div key={entity.id}>
                    <span className="text-gray-600">"{entity.text}"</span>
                    <span className="text-purple-600 mx-2">→</span>
                    <span className="font-medium text-purple-800">"{groupReplacement || '[REMPLACEMENT]'}"</span>
                  </div>
                ))}
                {selectedEntities.length > 3 && (
                  <div className="text-gray-500">
                    ... et {selectedEntities.length - 3} autre(s) entité(s)
                  </div>
                )}
              </div>
            </div>

            {/* Avantages du groupement */}
            <div className="bg-blue-50 p-3 rounded border-l-4 border-blue-400 mb-6">
              <h4 className="font-medium text-blue-800 mb-1">💡 Avantages du groupement :</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Cohérence : toutes les variantes sont anonymisées de la même façon</li>
                <li>• Simplicité : un seul remplacement à gérer pour plusieurs entités</li>
                <li>• Qualité : évite les incohérences dans le document final</li>
              </ul>
            </div>
          </>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            Annuler
          </button>
          <button
            onClick={handleCreateGroup}
            disabled={isLoading || selectedEntities.length < 2 || !groupName.trim() || !groupReplacement.trim()}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                Création...
              </>
            ) : (
              <>
                <Save size={16} />
                Créer le groupe
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EntityGroupModal;