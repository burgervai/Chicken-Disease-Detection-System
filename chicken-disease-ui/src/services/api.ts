import axios from 'axios';
import type {
  PredictionResponse,
  PredictionHistoryResponse,
  ModelInfo,
  Statistics,
  HealthStatus,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

export const predictionApi = {
  async predict(
    imageFile: File,
    modelVersion?: string,
    threshold: number = 0.5
  ): Promise<PredictionResponse> {
    const formData = new FormData();
    formData.append('image', imageFile);
    if (modelVersion) {
      formData.append('model_version', modelVersion);
    }
    formData.append('threshold', threshold.toString());

    const response = await apiClient.post<PredictionResponse>('/predict', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getHistory(
    page: number = 1,
    pageSize: number = 10,
    modelVersion?: string
  ): Promise<PredictionHistoryResponse> {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());
    if (modelVersion) {
      params.append('model_version', modelVersion);
    }

    const response = await apiClient.get<PredictionHistoryResponse>(
      '/predictions/history',
      { params }
    );
    return response.data;
  },

  async getPrediction(predictionId: string): Promise<PredictionResponse> {
    const response = await apiClient.get<PredictionResponse>(
      `/predictions/${predictionId}`
    );
    return response.data;
  },
};

export const modelApi = {
  async listModels(): Promise<ModelInfo[]> {
    const response = await apiClient.get<ModelInfo[]>('/models');
    return response.data;
  },

  async getActiveModel(): Promise<ModelInfo> {
    const response = await apiClient.get<ModelInfo>('/models/active');
    return response.data;
  },

  async activateModel(version: string): Promise<{ message: string }> {
    const response = await apiClient.post<{ message: string }>(
      `/models/${version}/activate`
    );
    return response.data;
  },
};

export const statisticsApi = {
  async getStatistics(): Promise<Statistics> {
    const response = await apiClient.get<Statistics>('/statistics');
    return response.data;
  },
};

export const healthApi = {
  async check(): Promise<HealthStatus> {
    const baseUrl = import.meta.env.VITE_API_URL || '';
    const response = await axios.get<HealthStatus>(`${baseUrl}/health`);
    return response.data;
  },
};

export default apiClient;
