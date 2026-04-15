from prometheus_client import Counter, Histogram, Gauge

# ─── Request metrics ────────────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "stock_api_requests_total",
    "Total number of prediction API requests",
    ["symbol", "status"],          # Labels: per-symbol and success/error
)

LATENCY = Histogram(
    "stock_api_latency_seconds",
    "End-to-end request latency in seconds",
    ["symbol"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)

ACTIVE_REQUESTS = Gauge(
    "stock_api_active_requests",
    "Number of requests currently being processed",
)

# ─── Model metrics ──────────────────────────────────────────────────────────
PREDICTION_VALUE = Gauge(
    "stock_predicted_price_usd",
    "Latest predicted closing price in USD",
    ["symbol"],
)

MODEL_ACCURACY = Gauge(
    "stock_model_r2_score",
    "R² score of the trained model on test data",
    ["symbol"],
)

# ─── Cache metrics ───────────────────────────────────────────────────────────
CACHE_HITS = Counter(
    "stock_model_cache_hits_total",
    "Number of times a cached model was reused (avoids retraining)",
)

MODEL_MAE = Gauge(
    "stock_model_mae_usd",
    "Mean absolute error of the trained model on holdout data in USD",
    ["symbol"],
)

DATA_POINTS_USED = Gauge(
    "stock_model_training_data_points",
    "Number of data points used for model training and validation",
    ["symbol"],
)
