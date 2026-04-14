# Stock Prediction System

A small full-stack stock prediction demo built with FastAPI, Streamlit, Prometheus, Docker, and optional Kubernetes manifests.

The project exposes:

- a FastAPI backend for health checks, supported symbols, and predictions
- a Streamlit frontend for interactive predictions
- Prometheus metrics for observability
- Docker and Kubernetes configuration for local and cloud deployment

## Features

- Predicts the next close price for supported stock symbols
- Trains and caches a model per symbol on demand
- Includes health and readiness endpoints
- Exposes Prometheus-compatible metrics
- Ships with a Streamlit dashboard for quick testing
- Includes local Docker Compose orchestration for API, UI, Prometheus, and Grafana

## Tech Stack

- Python 3.11
- FastAPI
- Streamlit
- pandas and NumPy
- scikit-learn
- Prometheus and Grafana
- Docker and Docker Compose
- Optional Kubernetes manifests

## Project Structure

```text
app/
  api.py          FastAPI application
  app.py          Streamlit UI
  data.py         Data loading and feature preparation
  model.py        Training and prediction logic
  metrics.py      Prometheus metrics
  stock_data.csv  Bundled sample dataset
tests/
  test_system.py  API, data, and model tests
Dockerfile        API container image
Dockerfile.ui     Streamlit UI container image
docker-compose.yml
README.md
```

## Supported Symbols

The current API supports these symbols:

- `AAPL`
- `GOOG`
- `MSFT`
- `AMZN`

## API Endpoints

Base URL for local development: `http://localhost:8000`

- `GET /health` - basic liveness check
- `GET /ready` - readiness check
- `GET /symbols` - returns supported stock symbols
- `GET /predict/{symbol}` - returns prediction details for a symbol
- `POST /cache/clear` - clears the in-memory model cache
- `GET /docs` - Swagger UI documentation
- `GET /metrics` - Prometheus metrics endpoint

Example prediction response:

```json
{
  "symbol": "AAPL",
  "predicted_close": 189.24,
  "model_r2": 0.8123,
  "latency_seconds": 0.1452,
  "data_points_used": 200
}
```

## Local Development

### Prerequisites

- Python 3.11+
- `pip`
- Docker Desktop (optional, for containerized setup)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.

### 3. Start the Streamlit UI

Open a second terminal and run:

```bash
streamlit run app/app.py --server.port 8054
```

The UI will be available at `http://localhost:8054`.

By default, the Streamlit app talks to `http://localhost:8000`.

## Running with Docker Compose

To start the full local stack:

```bash
docker compose up --build
```

Available services:

- FastAPI API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Streamlit UI: `http://localhost:8054`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

To stop the stack:

```bash
docker compose down
```

To stop and remove volumes:

```bash
docker compose down -v
```

## Environment Variables

### Backend

- `ALPHAVANTAGE_API_KEY`: optional Alpha Vantage API key
- `STOCK_DATA_PATH`: optional path override for the CSV dataset
- `LOG_LEVEL`: logging level for the API, such as `INFO` or `DEBUG`

### Frontend

- `API_URL`: base URL used by the Streamlit UI to reach the API
- `API_DOCS_URL`: optional override for the API docs link shown in the sidebar
- `PROMETHEUS_URL`: optional override for the Prometheus sidebar link
- `GRAFANA_URL`: optional override for the Grafana sidebar link
- `PORT`: deployment port injected by platforms like Render; the UI binds to this automatically in the container

## Testing

Run the test suite with:

```bash
pytest tests -q
```

The tests cover:

- model training and prediction flow
- stock data loading and feature generation
- API health, readiness, symbol, prediction, and cache endpoints

## Deployment

### Deploying the Streamlit UI on Render

Render does not expose `localhost:8054` as your public URL. Instead, Render assigns a runtime port through the `PORT` environment variable and gives you a public `onrender.com` URL.

This repository is already set up so the Streamlit container will:

- use `8054` locally
- use Render's injected `PORT` in production

For the UI service on Render:

1. Deploy using `Dockerfile.ui`.
2. Set `API_URL` to your deployed FastAPI backend URL.
3. Open the generated Render URL, not `http://localhost:8054`.

Example:

```text
API_URL=https://your-api-service.onrender.com
API_DOCS_URL=https://your-api-service.onrender.com/docs
```

### Deploying the API on Render

If you deploy the API as a separate Render service, use the backend `Dockerfile` and expose the FastAPI service publicly. Then point the UI's `API_URL` at that deployed backend.

## Kubernetes

The `k8s/` directory contains optional manifests for running the stack in Kubernetes, including monitoring-related resources. These files are not required for local development.

## Notes

- The app can fall back from local CSV data to Alpha Vantage and then to synthetic demo data.
- The model cache is in memory, so it resets when the API process restarts.
- Prometheus and Grafana are mainly intended for local observability and platform-based deployments.
