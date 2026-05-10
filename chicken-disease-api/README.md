# Chicken Disease Classification API

Production-ready FastAPI backend for chicken disease classification.

## Features

- FastAPI-based REST API with async support
- CNN model inference with TensorFlow
- PostgreSQL database for predictions logging
- Redis caching for model outputs
- JWT authentication
- Rate limiting and request validation
- Health check endpoints
- OpenAPI documentation
- Docker containerization

## Quick Start

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build and run
docker-compose up --build

# Run in detached mode
docker-compose up -d
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/v1/predict` - Predict disease from image
- `GET /api/v1/models` - List available models
- `POST /api/v1/models/upload` - Upload new model
- `GET /api/v1/predictions/history` - Get prediction history

## Environment Variables

See `.env.example` for configuration options.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

## License

MIT