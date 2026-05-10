import { useState } from 'react';
import { ChevronLeft, ChevronRight, Search } from 'lucide-react';
import type { PredictionResponse, PredictionHistoryResponse } from '../types';
import { PredictionDisplay } from './PredictionDisplay';

interface PredictionHistoryProps {
  history: PredictionHistoryResponse;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
}

export function PredictionHistory({
  history,
  onPageChange,
  isLoading = false,
}: PredictionHistoryProps) {
  const [selectedPrediction, setSelectedPrediction] =
    useState<PredictionResponse | null>(null);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Prediction History
        </h3>
        <span className="text-sm text-gray-500">
          Total: {history.total} predictions
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* History List */}
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {history.predictions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Search className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No predictions yet</p>
            </div>
          ) : (
            history.predictions.map((pred) => (
              <button
                key={pred.id}
                onClick={() => setSelectedPrediction(pred)}
                className={`
                  w-full text-left p-3 rounded-lg border transition-all
                  ${
                    selectedPrediction?.id === pred.id
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-blue-300'
                  }
                `}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`
                      px-2 py-0.5 rounded text-sm font-medium
                      ${
                        pred.result.disease === 'healthy'
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : pred.result.disease === 'unknown'
                          ? 'bg-gray-100 text-gray-700 dark:bg-gray-800'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                      }
                    `}
                  >
                    {pred.result.disease.replace('_', ' ')}
                  </span>
                  <span className="text-xs text-gray-500">
                    {formatDate(pred.created_at)}
                  </span>
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-gray-500">
                  <span>{(pred.result.confidence * 100).toFixed(1)}% confidence</span>
                  <span>v{pred.model_version}</span>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Selected Prediction Detail */}
        <div className="border rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
          {selectedPrediction ? (
            <div>
              <PredictionDisplay
                result={selectedPrediction.result}
                modelVersion={selectedPrediction.model_version}
                processingTimeMs={selectedPrediction.processing_time_ms}
              />
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-500">
              <p>Select a prediction to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Pagination */}
      {history.total_pages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <button
            onClick={() => onPageChange(history.page - 1)}
            disabled={history.page <= 1 || isLoading}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:pointer-events-none"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <span className="px-4 text-sm">
            Page {history.page} of {history.total_pages}
          </span>

          <button
            onClick={() => onPageChange(history.page + 1)}
            disabled={history.page >= history.total_pages || isLoading}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:pointer-events-none"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
}
