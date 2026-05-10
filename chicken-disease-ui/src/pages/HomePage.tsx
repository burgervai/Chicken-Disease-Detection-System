import { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  History,
  BarChart3,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import {
  ImageUpload,
  PredictionDisplay,
  PredictionHistory,
  StatisticsCards,
  DiseaseDistribution,
  NotificationBell,
} from '../components';
import { usePrediction, useWebSocket } from '../hooks';
import {
  predictionApi,
  statisticsApi,
  modelApi,
} from '../services/api';
import type {
  PredictionResponse,
  PredictionHistoryResponse,
  Statistics,
  ModelInfo,
  Notification,
  WebSocketMessage,
} from '../types';

type TabType = 'predict' | 'history' | 'statistics';

interface HomePageProps {
  clientId: string;
}

export function HomePage({ clientId }: HomePageProps) {
  const [activeTab, setActiveTab] = useState<TabType>('predict');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [lastPrediction, setLastPrediction] = useState<PredictionResponse | null>(null);
  const [history, setHistory] = useState<PredictionHistoryResponse | null>(null);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | undefined>();
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const { predict, isLoading, result, error } = usePrediction();

  // WebSocket for real-time notifications
  const { isConnected } = useWebSocket({
    clientId,
    onMessage: (message: WebSocketMessage) => {
      if (message.type === 'prediction_complete') {
        const notification: Notification = {
          id: Date.now().toString(),
          title: 'Prediction Complete',
          message: `Disease detected: ${(message.data.result as { disease: string }).disease}`,
          type: 'success',
          timestamp: new Date(),
          read: false,
        };
        setNotifications((prev) => [notification, ...prev]);
      } else if (message.type === 'model_updated') {
        const notification: Notification = {
          id: Date.now().toString(),
          title: 'Model Updated',
          message: `Model v${message.data.model_version} has been ${message.data.status}`,
          type: 'info',
          timestamp: new Date(),
          read: false,
        };
        setNotifications((prev) => [notification, ...prev]);
      } else if (message.type === 'error') {
        const notification: Notification = {
          id: Date.now().toString(),
          title: 'Error',
          message: (message.data.error as string) || 'An error occurred',
          type: 'error',
          timestamp: new Date(),
          read: false,
        };
        setNotifications((prev) => [notification, ...prev]);
      }
    },
  });

  // Fetch initial data
  useEffect(() => {
    fetchHistory(1);
    fetchStatistics();
    fetchModels();
  }, []);

  const fetchHistory = async (page: number) => {
    try {
      const data = await predictionApi.getHistory(page, 10, selectedModel);
      setHistory(data);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  };

  const fetchStatistics = async () => {
    try {
      const data = await statisticsApi.getStatistics();
      setStatistics(data);
    } catch (err) {
      console.error('Failed to fetch statistics:', err);
    }
  };

  const fetchModels = async () => {
    try {
      const data = await modelApi.listModels();
      setModels(data);
      const activeModel = data.find((m) => m.is_active);
      if (activeModel) {
        setSelectedModel(activeModel.version);
      }
    } catch (err) {
      console.error('Failed to fetch models:', err);
    }
  };

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  }, []);

  const handlePredict = useCallback(async () => {
    if (!selectedFile) return;

    const response = await predict(selectedFile, selectedModel, 0.5);
    if (response) {
      setLastPrediction(response);
      // Refresh history and statistics
      fetchHistory(1);
      fetchStatistics();
    }
  }, [selectedFile, selectedModel, predict]);

  const handleClear = useCallback(() => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    setLastPrediction(null);
  }, [previewUrl]);

  const handleMarkNotificationAsRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const handleMarkAllNotificationsAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const tabs = [
    { id: 'predict' as const, label: 'Predict', icon: Activity },
    { id: 'history' as const, label: 'History', icon: History },
    { id: 'statistics' as const, label: 'Statistics', icon: BarChart3 },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                  Chicken Disease Classifier
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Production AI-Powered Health Detection
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Connection Status */}
              <div className="flex items-center gap-2 text-sm">
                {isConnected ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-gray-500">Connected</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-red-500" />
                    <span className="text-gray-500">Disconnected</span>
                  </>
                )}
              </div>

              {/* Notifications */}
              <NotificationBell
                notifications={notifications}
                onMarkAsRead={handleMarkNotificationAsRead}
                onMarkAllAsRead={handleMarkAllNotificationsAsRead}
                unreadCount={unreadCount}
              />
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors
                  ${
                    activeTab === tab.id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                  }
                `}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {activeTab === 'predict' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Upload Section */}
            <div className="space-y-4">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Upload Image
                </h2>

                <ImageUpload
                  onFileSelect={handleFileSelect}
                  isLoading={isLoading}
                  previewUrl={previewUrl}
                  onClear={handleClear}
                />

                {/* Model Selection */}
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Select Model
                  </label>
                  <select
                    value={selectedModel || ''}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {models.map((model) => (
                      <option key={model.version} value={model.version}>
                        {model.name} {model.is_active && '(Active)'}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Predict Button */}
                <button
                  onClick={handlePredict}
                  disabled={!selectedFile || isLoading}
                  className="w-full mt-4 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                >
                  {isLoading ? 'Analyzing...' : 'Analyze Image'}
                </button>

                {/* Error Display */}
                {error && (
                  <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-sm text-red-600 dark:text-red-400">
                      {error.message}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Result Section */}
            <div className="space-y-4">
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Analysis Result
                </h2>

                {lastPrediction ? (
                  <PredictionDisplay
                    result={lastPrediction.result}
                    modelVersion={lastPrediction.model_version}
                    processingTimeMs={lastPrediction.processing_time_ms}
                  />
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>Upload an image to see the analysis result</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            {history ? (
              <PredictionHistory
                history={history}
                onPageChange={fetchHistory}
              />
            ) : (
              <div className="text-center py-12 text-gray-500">
                <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Loading history...</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'statistics' && (
          <div className="space-y-6">
            <StatisticsCards statistics={statistics} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <DiseaseDistribution
                predictionsByResult={statistics?.predictions_by_result || {}}
              />

              {/* Models Table */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
                  Available Models
                </h4>
                <div className="space-y-3">
                  {models.map((model) => (
                    <div
                      key={model.version}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                    >
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {model.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          Accuracy: {(model.accuracy * 100).toFixed(1)}%
                        </p>
                      </div>
                      {model.is_active && (
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded">
                          Active
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-8">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <p className="text-center text-sm text-gray-500">
            &copy; 2024 Chicken Disease Classifier. Production-ready API.
          </p>
        </div>
      </footer>
    </div>
  );
}
