# Chicken Disease Classification UI

Production-ready React frontend for chicken disease classification with AI-powered health detection.

## Features

- Modern React with TypeScript
- Tailwind CSS styling with dark mode support
- Real-time WebSocket notifications
- Prediction history with pagination
- Statistics dashboard
- Multi-model support
- Responsive design

## Tech Stack

- **Framework**: React 19 + TypeScript
- **Styling**: Tailwind CSS 4
- **Build Tool**: Vite
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **State**: React hooks

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/       # Reusable UI components
├── hooks/            # Custom React hooks
├── pages/            # Page components
├── services/         # API services
├── types/            # TypeScript type definitions
└── App.tsx           # Main application component
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| VITE_API_URL | Backend API URL | /api/v1 |

## Features

### Image Upload

Drag and drop or click to upload chicken fecal images for analysis.

### Prediction History

View all past predictions with detailed results and confidence scores.

### Statistics Dashboard

Track total predictions, disease distribution, and model performance.

### Real-time Notifications

Receive instant notifications via WebSocket when predictions complete.

## License

MIT
