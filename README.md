# 📈 Cloud-Based Stock Price Prediction System
### Real-Time ML Inference · Kubernetes · Prometheus · Grafana · GitHub Actions

---

## Table of Contents
1. [What This System Does](#what-this-system-does)
2. [Architecture Overview](#architecture-overview)
3. [Why Each Technology Was Chosen](#why-each-technology-was-chosen)
4. [Project Structure](#project-structure)
5. [Quick Start (Local)](#quick-start-local)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Monitoring & Alerting](#monitoring--alerting)
8. [CI/CD Pipeline](#cicd-pipeline)
9. [API Reference](#api-reference)
10. [Configuration & Secrets](#configuration--secrets)

---

## What This System Does

This is a **production-grade, cloud-native ML system** that:
- Trains a Gradient Boosting model on OHLCV stock data with technical indicators
- Exposes predictions via a **FastAPI REST API** with per-symbol latency tracking
- Visualises results in a **Streamlit** UI
- Runs as **containerised pods on Kubernetes** with auto-scaling
- Exposes **Prometheus metrics** (request count, latency, model R², predicted price)
- Visualises those metrics in **Grafana dashboards** with alerting rules
- Deploys automatically via **GitHub Actions** on every push to `main`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                       │
│                   (namespace: stock-prediction)              │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Streamlit   │───▶│  FastAPI     │───▶│  Prometheus   │  │
│  │  UI Pod      │    │  API Pods    │    │  Pod          │  │
│  │  :8501       │    │  (×2 → ×8)  │    │  :9090        │  │
│  └──────────────┘    │  :8000       │    └───────┬───────┘  │
│                      └──────┬───────┘            │           │
│                             │ /metrics           ▼           │
│                             │            ┌───────────────┐   │
│                      ┌──────▼───────┐    │   Grafana     │   │
│                      │ HPA          │    │   Pod :3000   │   │
│                      │ (auto-scale) │    └───────────────┘   │
│                      └─────────────┘                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Ingress (nginx)  ← external traffic          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
          ▲
          │  GitHub Actions CI/CD
          │  (lint → test → build → scan → deploy)
```

---

## Why Each Technology Was Chosen

### ☸️ Kubernetes — Container Orchestration

**Problem without it:** Running `docker run` on a single VM means one crash = full outage. Manual scaling for bursty market-hours traffic is impossible.

**Why Kubernetes solves it:**

| Feature | How it helps this system |
|---|---|
| **Replica management** | Keeps exactly N healthy API pods running at all times |
| **Rolling deployments** | Zero-downtime model updates — new pods start before old ones stop |
| **Self-healing** | Liveness probes restart hung pods automatically |
| **HPA (auto-scaling)** | Scales from 2 → 8 pods when CPU/memory exceeds threshold during market hours |
| **Service discovery** | Streamlit UI reaches the API via `stock-prediction-api-service` DNS — no hardcoded IPs |
| **Resource limits** | Prevents a runaway ML training job from starving other pods |
| **ConfigMaps & Secrets** | API keys and config injected at runtime, not baked into images |

**Concrete example:** During NYSE open (9:30 AM ET), prediction traffic spikes 5×. The HPA automatically creates more API pods within ~60 seconds. At close, it scales back down, saving cloud cost.

---

### 📊 Prometheus — Metrics Collection

**Problem without it:** You don't know if your model is degrading, if latency is spiking, or which stock symbol is causing errors until a user complains.

**Why Prometheus solves it:**

| Feature | How it helps this system |
|---|---|
| **Pull-based scraping** | Prometheus reaches into every pod at `/metrics` every 15s — if a pod dies, metrics stop; no stale data builds up |
| **Kubernetes SD** | Auto-discovers new pods via annotations — no manual config when HPA adds replicas |
| **Custom business metrics** | Tracks `stock_predicted_price_usd`, `stock_model_r2_score` alongside infra metrics |
| **PromQL alerting** | Query `histogram_quantile(0.95, ...)` to fire alerts before users notice slowness |
| **Time-series storage** | 15-day retention window lets you correlate model accuracy drift with market events |

**Metrics exposed by this system:**
```
stock_api_requests_total{symbol, status}   # request throughput per symbol
stock_api_latency_seconds{symbol}          # latency histogram (P50/P95/P99)
stock_api_active_requests                  # in-flight requests (concurrency)
stock_predicted_price_usd{symbol}          # latest predicted price
stock_model_r2_score{symbol}               # live model accuracy
stock_model_cache_hits_total               # cache efficiency
```

---

### 📈 Grafana — Visualisation & Alerting

**Problem without it:** Prometheus has a basic expression browser, but you can't build a meaningful operational dashboard or share it with the team.

**Why Grafana solves it:**

| Feature | How it helps this system |
|---|---|
| **Auto-provisioned datasource** | Grafana connects to Prometheus on startup via ConfigMap — no manual wiring |
| **Pre-built dashboard** | Stock prices, latency percentiles, error rates, model accuracy in one view |
| **Threshold colouring** | R² gauge turns red below 0.70, alerting you to model drift instantly |
| **Alert rules** | `HighAPILatency`, `HighErrorRate`, `LowModelAccuracy` alerts fire to Slack/PagerDuty |
| **Team-friendly UI** | Non-engineers can watch the system without writing PromQL |

---

### ⚙️ GitHub Actions — CI/CD Pipeline

**Problem without it:** Manual `docker build && kubectl apply` is error-prone, untested images go to production, and there is no audit trail of deployments.

**Why GitHub Actions solves it:**

| Stage | What it does |
|---|---|
| **Lint (Ruff + mypy)** | Catches style errors and type mistakes before they reach CI |
| **Tests (pytest + coverage)** | Validates model training, prediction, and every API endpoint; fails if coverage < 70% |
| **Build & Push** | Multi-stage Docker build with layer caching — fast rebuilds |
| **Security scan (Trivy)** | Blocks deployment if CRITICAL/HIGH CVEs are found in the image |
| **Deploy** | `kubectl set image` triggers a rolling update; pipeline waits for `rollout status` |
| **Slack notification** | Team is alerted immediately on pipeline failure |

**Every commit to `main` triggers:**
```
lint ──▶ test ──▶ build/push ──▶ security scan ──▶ deploy (with manual approval gate)
```

---

### 🤖 ML Stack — Gradient Boosting + Feature Engineering

| Choice | Reasoning |
|---|---|
| **GradientBoostingRegressor** | Outperforms plain RandomForest on tabular time-series; handles non-linear interactions between OHLCV features |
| **sklearn Pipeline (scaler + model)** | Ensures feature scaling is part of the model artefact — no train/serve skew |
| **Technical indicators (MA, volatility, momentum)** | Domain features proven to improve short-term price prediction |
| **In-memory model cache** | Avoids retraining (2-3s) on every API call; cache is keyed per symbol |
| **R² as live metric** | Exposed to Prometheus so model accuracy degradation triggers an alert |

---

## Project Structure

```
stock-prediction-system/
├── app/
│   ├── api.py              # FastAPI app, routes, Prometheus integration
│   ├── data.py             # Data loading (CSV → API → synthetic fallback)
│   ├── model.py            # GradientBoosting pipeline, train/predict/metrics
│   ├── metrics.py          # Prometheus Counter/Histogram/Gauge definitions
│   ├── app.py              # Streamlit frontend
│   └── requirements.txt    # Python dependencies
│
├── k8s/
│   ├── base/
│   │   ├── namespace.yaml        # Namespace + ConfigMap
│   │   ├── deployment.yaml       # API Deployment + Service
│   │   └── hpa-ingress.yaml      # HPA (auto-scaling) + Ingress + UI
│   └── monitoring/
│       └── monitoring-stack.yaml # Prometheus + Grafana + RBAC
│
├── prometheus/
│   ├── prometheus.yml      # Scrape config (Kubernetes SD)
│   └── alerts.yml          # Alerting rules (latency, error rate, model drift)
│
├── grafana/
│   └── dashboards/
│       └── stock-prediction.json # Pre-built Grafana dashboard
│
├── tests/
│   └── test_system.py      # Unit + integration tests (pytest)
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml       # 6-stage GitHub Actions pipeline
│
├── Dockerfile              # Multi-stage build (builder + runtime)
├── docker-compose.yml      # Local development stack
└── README.md
```

---

## Quick Start (Local)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for running tests locally)

### 1. Clone and configure
```bash
git clone https://github.com/your-org/stock-prediction-system
cd stock-prediction-system

# Copy sample env file
cp .env.example .env
# Edit .env — set ALPHAVANTAGE_API_KEY if you have one (optional; falls back to CSV/synthetic data)
```

### 2. Run the full stack
```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| API docs (Swagger) | http://localhost:8000/docs |
| Streamlit UI | http://localhost:8501 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin / admin123) |

### 3. Run tests
```bash
pip install -r app/requirements.txt
pytest tests/ -v --cov=app
```

---

## Kubernetes Deployment

### Prerequisites
- `kubectl` configured against your cluster (GKE / EKS / AKS / kind)
- Container registry credentials

### 1. Build and push your image
```bash
docker build -t ghcr.io/your-org/stock-prediction-api:latest .
docker push ghcr.io/your-org/stock-prediction-api:latest
```

### 2. Create secrets
```bash
kubectl create namespace stock-prediction

kubectl create secret generic stock-prediction-secrets \
  --namespace stock-prediction \
  --from-literal=alphavantage-api-key=YOUR_KEY

kubectl create secret generic grafana-secrets \
  --namespace stock-prediction \
  --from-literal=admin-password=YOUR_GRAFANA_PASSWORD
```

### 3. Apply manifests
```bash
# Core application
kubectl apply -f k8s/base/

# Monitoring stack
kubectl apply -f k8s/monitoring/
```

### 4. Verify deployment
```bash
kubectl get pods -n stock-prediction
kubectl get hpa -n stock-prediction
kubectl get svc -n stock-prediction
```

### 5. Access services (port-forward for testing)
```bash
kubectl port-forward svc/stock-prediction-api-service 8000:8000 -n stock-prediction
kubectl port-forward svc/grafana-service 3000:3000 -n stock-prediction
kubectl port-forward svc/prometheus-service 9090:9090 -n stock-prediction
```

---

## Monitoring & Alerting

### Prometheus Alerts

| Alert | Condition | Severity |
|---|---|---|
| `APIDown` | No healthy pods for 1m | 🔴 Critical |
| `HighErrorRate` | Error rate > 5% over 1m | 🔴 Critical |
| `HighAPILatency` | P95 latency > 2s over 2m | 🟡 Warning |
| `LowModelAccuracy` | R² < 0.70 for 5m | 🟡 Warning |
| `PodCrashLooping` | Pod restarts detected | 🔴 Critical |

### Grafana Dashboard Panels
- 🚦 API requests per second (per symbol, per status)
- ⚡ P50/P95 latency time series
- 💰 Live predicted prices per symbol
- 📊 Model R² score gauges (red/yellow/green thresholds)
- 🔴 Active in-flight requests
- ❌ Error rate percentage

---

## CI/CD Pipeline

```yaml
On push to main / PR to main:

  lint        → ruff + mypy
      ↓
  test        → pytest (70% coverage gate)
      ↓
  build       → docker buildx (layer cache) → push to GHCR
      ↓
  security    → Trivy scan (block on CRITICAL/HIGH CVEs)
      ↓
  deploy      → kubectl set image → rollout status wait
      ↓
  notify      → Slack alert on any failure
```

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `KUBECONFIG` | Base64-encoded kubeconfig for your cluster |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook for failure notifications |

The `GITHUB_TOKEN` is auto-provided for pushing to GitHub Container Registry.

---

## API Reference

### `GET /predict/{symbol}`
Returns the predicted next closing price for a stock symbol.

**Supported symbols:** `AAPL`, `GOOG`, `MSFT`, `AMZN`

**Response:**
```json
{
  "symbol": "AAPL",
  "predicted_close": 187.42,
  "model_r2": 0.9231,
  "latency_seconds": 0.087,
  "data_points_used": 145
}
```

### `GET /health`
Kubernetes liveness probe. Returns `{"status": "healthy"}`.

### `GET /ready`
Kubernetes readiness probe. Returns `{"status": "ready"}`.

### `GET /symbols`
Lists all supported symbols.

### `GET /metrics`
Prometheus metrics scrape endpoint.

### `GET /cache/clear`
Clears the in-memory model cache (forces retraining on next request).

---

## Configuration & Secrets

| Variable | Default | Description |
|---|---|---|
| `ALPHAVANTAGE_API_KEY` | `demo` | Alpha Vantage API key (optional; falls back to CSV/synthetic) |
| `STOCK_DATA_PATH` | `stock_data.csv` | Path to local CSV data file |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `API_URL` | `http://localhost:8000` | API URL for Streamlit UI |

---

## Tech Stack Summary

| Layer | Technology | Why |
|---|---|---|
| ML Model | GradientBoostingRegressor + sklearn Pipeline | Accurate tabular regression, no train/serve skew |
| API | FastAPI + Uvicorn | Async, fast, auto-generates OpenAPI docs |
| UI | Streamlit + Plotly | Rapid data app with real-time metrics display |
| Containerisation | Docker (multi-stage) | Reproducible, minimal runtime image |
| Orchestration | Kubernetes | Self-healing, auto-scaling, rolling deployments |
| Metrics | Prometheus | Pull-based, Kubernetes-native service discovery |
| Dashboards | Grafana | Rich visualisation, alerting, auto-provisioned |
| CI/CD | GitHub Actions | Integrated, free for public repos, matrix builds |
| Security | Trivy | Blocks vulnerable images before production deploy |
