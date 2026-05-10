import { useState, useCallback } from 'react';
import { predictionApi } from '../services/api';
import type { PredictionResponse, PredictionResult } from '../types';

interface UsePredictionOptions {
  onSuccess?: (response: PredictionResponse) => void;
  onError?: (error: Error) => void;
}

interface UsePredictionReturn {
  predict: (file: File, modelVersion?: string, threshold?: number) => Promise<PredictionResponse | null>;
  isLoading: boolean;
  error: Error | null;
  result: PredictionResult | null;
  reset: () => void;
}

export function usePrediction(options: UsePredictionOptions = {}): UsePredictionReturn {
  const { onSuccess, onError } = options;
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);

  const predict = useCallback(
    async (file: File, modelVersion?: string, threshold: number = 0.5): Promise<PredictionResponse | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await predictionApi.predict(file, modelVersion, threshold);
        setResult(response.result);
        onSuccess?.(response);
        return response;
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Prediction failed');
        setError(error);
        onError?.(error);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [onSuccess, onError]
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    predict,
    isLoading,
    error,
    result,
    reset,
  };
}
