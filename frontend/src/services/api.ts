import axios from 'axios';
import { AnalyzeResponse, CustomEntity, Entity } from '../types/entities';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes pour les gros fichiers
});

// Intercepteur de réponse pour la gestion d'erreurs
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    if (error.message) {
      throw new Error(error.message);
    }
    throw new Error('Erreur de connexion au serveur');
  }
);

export const analyzeDocument = async (
  file: File, 
  mode: 'standard' | 'approfondi' = 'standard'
): Promise<AnalyzeResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mode', mode);

  const response = await api.post<AnalyzeResponse>('/api/analyze', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const addCustomEntity = async (
  sessionId: string,
  entity: CustomEntity
): Promise<{ success: boolean; entity: Entity }> => {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('text', entity.text);
  formData.append('entity_type', entity.entity_type);
  formData.append('replacement', entity.replacement);

  const response = await api.post('/api/add-entity', formData);
  return response.data;
};

export const generateAnonymizedDocument = async (
  sessionId: string,
  selectedEntities: Entity[]
): Promise<Blob> => {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('selected_entities', JSON.stringify(selectedEntities));

  const response = await api.post('/api/generate', formData, {
    responseType: 'blob',
  });

  return response.data;
};

export const getSessionInfo = async (sessionId: string) => {
  const response = await api.get(`/api/session/${sessionId}`);
  return response.data;
};

export const getApplicationStats = async () => {
  const response = await api.get('/api/stats');
  return response.data;
};

export default api;