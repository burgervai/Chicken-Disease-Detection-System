import { CheckCircle, AlertCircle, HelpCircle, Activity } from 'lucide-react';
import type { PredictionResult, DiseaseClass } from '../types';

interface PredictionDisplayProps {
  result: PredictionResult;
  modelVersion: string;
  processingTimeMs: number;
}

const diseaseConfig: Record<
  DiseaseClass,
  { label: string; description: string; color: string; icon: React.ReactNode }
> = {
  healthy: {
    label: 'Healthy',
    description: 'No signs of disease detected',
    color: 'text-green-600 bg-green-50 dark:bg-green-900/20',
    icon: <CheckCircle className="w-6 h-6" />,
  },
  coccidiosis: {
    label: 'Coccidiosis',
    description: 'Intestinal parasitic disease requiring treatment',
    color: 'text-red-600 bg-red-50 dark:bg-red-900/20',
    icon: <AlertCircle className="w-6 h-6" />,
  },
  salmonellosis: {
    label: 'Salmonellosis',
    description: 'Bacterial infection requiring antibiotic treatment',
    color: 'text-orange-600 bg-orange-50 dark:bg-orange-900/20',
    icon: <AlertCircle className="w-6 h-6" />,
  },
  newcastle_disease: {
    label: 'Newcastle Disease',
    description: 'Viral respiratory infection - highly contagious',
    color: 'text-purple-600 bg-purple-50 dark:bg-purple-900/20',
    icon: <AlertCircle className="w-6 h-6" />,
  },
  bird_flu: {
    label: 'Bird Flu (Avian Influenza)',
    description: 'Highly pathogenic viral disease - report immediately',
    color: 'text-red-700 bg-red-100 dark:bg-red-900/30',
    icon: <AlertCircle className="w-6 h-6" />,
  },
  unknown: {
    label: 'Unknown',
    description: 'Unable to classify with confidence',
    color: 'text-gray-600 bg-gray-50 dark:bg-gray-800',
    icon: <HelpCircle className="w-6 h-6" />,
  },
};

export function PredictionDisplay({
  result,
  modelVersion,
  processingTimeMs,
}: PredictionDisplayProps) {
  const config = diseaseConfig[result.disease] || diseaseConfig.unknown;
  const confidencePercent = (result.confidence * 100).toFixed(1);

  return (
    <div className="w-full">
      {/* Main Result */}
      <div
        className={`rounded-lg p-6 ${config.color} border border-current/20`}
      >
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">{config.icon}</div>
          <div className="flex-1">
            <h3 className="text-xl font-bold">{config.label}</h3>
            <p className="text-sm mt-1 opacity-80">{config.description}</p>

            {/* Confidence Bar */}
            <div className="mt-4">
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="font-medium">Confidence</span>
                <span className="font-mono">{confidencePercent}%</span>
              </div>
              <div className="h-2 bg-black/10 dark:bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-current rounded-full transition-all duration-500"
                  style={{ width: `${confidencePercent}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Probability Distribution */}
      <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="w-4 h-4 text-gray-500" />
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Probability Distribution
          </h4>
        </div>
        <div className="space-y-2">
          {Object.entries(result.probabilities).map(([disease, prob]) => {
            const diseaseLabel =
              diseaseConfig[disease as DiseaseClass]?.label || disease;
            return (
              <div key={disease} className="flex items-center gap-2">
                <span className="text-sm text-gray-600 dark:text-gray-400 w-28">
                  {diseaseLabel}
                </span>
                <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      disease === result.disease
                        ? 'bg-blue-500'
                        : 'bg-gray-400 dark:bg-gray-500'
                    }`}
                    style={{ width: `${(prob * 100).toFixed(1)}%` }}
                  />
                </div>
                <span className="text-sm font-mono w-12 text-right">
                  {(prob * 100).toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Metadata */}
      <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
        <span>Model: v{modelVersion}</span>
        <span>Processing: {processingTimeMs.toFixed(0)}ms</span>
      </div>
    </div>
  );
}
