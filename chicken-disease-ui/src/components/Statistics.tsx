import { BarChart3, Activity, Cpu, Clock } from 'lucide-react';
import type { Statistics } from '../types';

interface StatisticsCardsProps {
  statistics: Statistics | null;
  isLoading?: boolean;
}

export function StatisticsCards({
  statistics,
  isLoading = false,
}: StatisticsCardsProps) {
  if (!statistics || isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-gray-100 dark:bg-gray-800 animate-pulse rounded-lg h-32"
          />
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: 'Total Predictions',
      value: statistics.total_predictions.toLocaleString(),
      icon: <BarChart3 className="w-6 h-6" />,
      color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
    },
    {
      title: 'Models Loaded',
      value: statistics.models_loaded.toString(),
      icon: <Cpu className="w-6 h-6" />,
      color: 'text-purple-600 bg-purple-50 dark:bg-purple-900/20',
    },
    {
      title: 'Model Versions',
      value: Object.keys(statistics.predictions_by_model).length.toString(),
      icon: <Activity className="w-6 h-6" />,
      color: 'text-green-600 bg-green-50 dark:bg-green-900/20',
    },
    {
      title: 'Healthy Results',
      value: (
        statistics.predictions_by_result['healthy'] || 0
      ).toLocaleString(),
      icon: <Clock className="w-6 h-6" />,
      color: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, index) => (
        <div
          key={index}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {card.title}
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {card.value}
              </p>
            </div>
            <div className={`p-2 rounded-lg ${card.color}`}>{card.icon}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

interface DiseaseDistributionProps {
  predictionsByResult: Record<string, number>;
}

export function DiseaseDistribution({
  predictionsByResult,
}: DiseaseDistributionProps) {
  const total = Object.values(predictionsByResult).reduce((a, b) => a + b, 0);

  if (total === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
          Disease Distribution
        </h4>
        <p className="text-center text-gray-500 py-8">No data available</p>
      </div>
    );
  }

  const colors: Record<string, string> = {
    healthy: 'bg-green-500',
    coccidiosis: 'bg-red-500',
    salmonellosis: 'bg-orange-500',
    newcastle_disease: 'bg-purple-500',
    bird_flu: 'bg-red-700',
    unknown: 'bg-gray-400',
  };

  const labels: Record<string, string> = {
    healthy: 'Healthy',
    coccidiosis: 'Coccidiosis',
    salmonellosis: 'Salmonellosis',
    newcastle_disease: 'Newcastle',
    bird_flu: 'Bird Flu',
    unknown: 'Unknown',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
        Disease Distribution
      </h4>
      <div className="space-y-3">
        {Object.entries(predictionsByResult).map(([disease, count]) => {
          const percentage = ((count / total) * 100).toFixed(1);
          return (
            <div key={disease}>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-gray-400">
                  {labels[disease] || disease}
                </span>
                <span className="font-medium text-gray-900 dark:text-white">
                  {percentage}%
                </span>
              </div>
              <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={`h-full ${colors[disease] || 'bg-gray-400'} rounded-full`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
