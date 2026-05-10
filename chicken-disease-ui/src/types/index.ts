// API Types

export type DiseaseClass =
  | 'healthy'
  | 'coccidiosis'
  | 'salmonellosis'
  | 'newcastle_disease'
  | 'bird_flu'
  | 'unknown';

export interface PredictionResult {
  disease: DiseaseClass;
  confidence: number;
  probabilities: Record<string, number>;
}

export interface PredictionResponse {
  id: string;
  result: PredictionResult;
  model_version: string;
  processing_time_ms: number;
  created_at: string;
}

export interface PredictionHistoryResponse {
  predictions: PredictionResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ModelInfo {
  version: string;
  name: string;
  description: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  training_date: string;
  dataset_size: number;
  classes: string[];
  is_active: boolean;
  status: 'loading' | 'ready' | 'error' | 'unloaded';
}

export interface Statistics {
  total_predictions: number;
  predictions_by_result: Record<string, number>;
  predictions_by_model: Record<string, number>;
  models_loaded: number;
}

export interface HealthStatus {
  status: string;
  app_name: string;
  version: string;
  models_loaded: number;
  mongodb_connected: boolean;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'prediction_complete' | 'model_updated' | 'error' | 'notification' | 'pong';
  data: Record<string, unknown>;
  timestamp: string;
}

// UI Types
export interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: Date;
  read: boolean;
}
