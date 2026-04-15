# Stock Prediction System

A small stock prediction demo built with FastAPI, Streamlit, Prometheus, Docker, and optional Kubernetes manifests.

## What is in the repo

- `app/`: API, UI, model code, and bundled sample data
- `tests/`: pytest coverage for model, data loading, and API endpoints
- `docker-compose.yml`: local stack for API, UI, Prometheus, and Grafana
- `k8s/`: optional deployment manifests
- `.github/workflows/ci-cd.yml`: lightweight CI that lints, tests, and builds an image on pushes

## Quick start

### Run locally with Python

```bash
pip install -r requirements.txt
uvicorn app.api:app --reload
```

In a second terminal:

```bash
streamlit run app/app.py
```

### Run the local stack with Docker

```bash
docker compose up --build
```

Services:

- API docs: `http://localhost:8000/docs`
- Streamlit UI: `http://localhost:8504`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

## Tests

```bash
pytest tests -q
```

## Environment variables

- `API_URL`: UI base URL for the API
- `STOCK_DATA_PATH`: optional override for the CSV data path
- `LOG_LEVEL`: API log level

## Notes

- The app reads market history from the local CSV dataset and serves predictions from that data only.
- The checked-in Kubernetes and monitoring manifests are optional and not required for local development.
