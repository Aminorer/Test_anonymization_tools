import React, { useState, useEffect } from 'react';
import { X, Edit3, Save, AlertCircle } from 'lucide-react';
import { Entity } from '../types/entities';

interface EntityEditModalProps {
  entity: Entity | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (entityId: string, newText: string, newReplacement?: string) => void;
  onApiSave?: (entityId: string, newText: string, newReplacement?: string) => Promise<void>;
}

const EntityEditModal: React.FC<EntityEditModalProps> = ({
  entity,
  isOpen,
  onClose,
  onSave,
  onApiSave
}) => {
  const [newText, setNewText] = useState('');
  const [newReplacement, setNewReplacement] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (entity && isOpen) {
      setNewText(entity.text);
      setNewReplacement(entity.replacement);
      setError(null);
    }
  }, [entity, isOpen]);

  const handleSave = async () => {
    if (!entity || !newText.trim()) {
      setError('Le texte ne peut pas être vide');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Appel API si fourni
      if (onApiSave) {
        await onApiSave(entity.id, newText.trim(), newReplacement.trim());
      }

      // Mise à jour locale
      onSave(entity.id, newText.trim(), newReplacement.trim());
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTextSelection = () => {
    // Fonctionnalité pour sélectionner une partie du texte
    const textarea = document.getElementById('edit-text') as HTMLTextAreaElement;
    if (textarea && textarea.selectionStart !== textarea.selectionEnd) {
      const selectedText = textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
      setNewText(selectedText);
    }
  };

  if (!isOpen || !entity) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-2xl mx-4">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold flex items-center gap-2">
            <Edit3 size={20} className="text-blue-600" />
            Modifier l'entité
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 flex items-start gap-2">
            <AlertCircle size={16} className="text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          {/* Affichage du texte original complet */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Texte original complet :
            </label>
            <div className="bg-gray-50 p-3 rounded border text-sm font-mono">
              {entity.text}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Type: {entity.type} • Source: {entity.source} • Occurrences: {entity.occurrences}
            </p>
          </div>

          {/* Sélection de la partie à anonymiser */}
          <div>
            <label htmlFor="edit-text" className="block text-sm font-medium text-gray-700 mb-2">
              Partie à anonymiser * :
            </label>
            <textarea
              id="edit-text"
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
              onMouseUp={handleTextSelection}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              rows={3}
              placeholder="Sélectionnez ou modifiez la partie du texte à anonymiser..."
            />
            <div className="flex items-center justify-between mt-1">
              <p className="text-xs text-gray-500">
                💡 Sélectionnez du texte pour ne garder que cette partie
              </p>
              <button
                type="button"
                onClick={() => setNewText(entity.text)}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                Réinitialiser
              </button>
            </div>
          </div>

          {/* Nouveau remplacement */}
          <div>
            <label htmlFor="edit-replacement" className="block text-sm font-medium text-gray-700 mb-2">
              Remplacer par :
            </label>
            <input
              id="edit-replacement"
              type="text"
              value={newReplacement}
              onChange={(e) => setNewReplacement(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Nouveau texte de remplacement..."
            />
          </div>

          {/* Aperçu des changements */}
          {newText !== entity.text && (
            <div className="bg-blue-50 p-3 rounded border-l-4 border-blue-400">
              <h4 className="font-medium text-blue-800 mb-2">Aperçu des modifications :</h4>
              <div className="text-sm space-y-1">
                <div>
                  <span className="text-red-600">- Ancien :</span> 
                  <span className="font-mono bg-red-100 px-1 rounded">{entity.text}</span>
                </div>
                <div>
                  <span className="text-green-600">+ Nouveau :</span> 
                  <span className="font-mono bg-green-100 px-1 rounded">{newText}</span>
                </div>
                <div>
                  <span className="text-blue-600">→ Anonymisé :</span> 
                  <span className="font-mono bg-blue-100 px-1 rounded">{newReplacement}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            Annuler
          </button>
          <button
            onClick={handleSave}
            disabled={isLoading || !newText.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                Sauvegarde...
              </>
            ) : (
              <>
                <Save size={16} />
                Sauvegarder
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EntityEditModal;