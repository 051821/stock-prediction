from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from data import get_stock_data
from model import train_model, predict, get_model_metrics
from metrics import (
    REQUEST_COUNT, LATENCY, PREDICTION_VALUE,
    MODEL_ACCURACY, ACTIVE_REQUESTS, CACHE_HITS
)
import time
import logging

# ─── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ─── App ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Stock Price Prediction API",
    description="Cloud-native ML API for real-time stock price prediction",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ─── In-memory model cache ──────────────────────────────────────────────────
_model_cache: dict = {}

SUPPORTED_SYMBOLS = ["AAPL", "GOOG", "MSFT", "AMZN"]


# ─── Routes ────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Kubernetes liveness & readiness probe endpoint."""
    return {"status": "healthy", "service": "stock-prediction-api"}


@app.get("/ready")
def readiness_check():
    """Kubernetes readiness probe — ensures model can load."""
    return {"status": "ready"}


@app.get("/predict/{symbol}")
def get_prediction(symbol: str):
    """
    Returns a next-day closing price prediction for the given stock symbol.
    Tracks Prometheus metrics: request count, latency, prediction value.
    """
    symbol = symbol.upper()

    if symbol not in SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol '{symbol}' not supported. Choose from {SUPPORTED_SYMBOLS}"
        )

    ACTIVE_REQUESTS.inc()
    start = time.time()

    try:
        # Fetch stock data
        df = get_stock_data(symbol)

        if df.empty:
            raise HTTPException(status_code=503, detail=f"Could not fetch data for {symbol}")

        # Use cached model or retrain
        if symbol in _model_cache:
            model = _model_cache[symbol]
            CACHE_HITS.inc()
            logger.info(f"Cache hit for {symbol}")
        else:
            logger.info(f"Training model for {symbol}...")
            model = train_model(df)
            _model_cache[symbol] = model

        # Predict on latest row
        preds = predict(model, df.tail(1))
        pred_value = float(preds[0])

        # Record metrics
        REQUEST_COUNT.labels(symbol=symbol, status="success").inc()
        PREDICTION_VALUE.labels(symbol=symbol).set(pred_value)

        duration = time.time() - start
        LATENCY.labels(symbol=symbol).observe(duration)

        # Model quality metrics
        metrics = get_model_metrics(model, df)
        MODEL_ACCURACY.labels(symbol=symbol).set(metrics["r2_score"])

        logger.info(f"Prediction for {symbol}: ${pred_value:.2f} | latency={duration:.3f}s")

        return {
            "symbol": symbol,
            "predicted_close": round(pred_value, 2),
            "model_r2": round(metrics["r2_score"], 4),
            "latency_seconds": round(duration, 4),
            "data_points_used": len(df),
        }

    except HTTPException:
        REQUEST_COUNT.labels(symbol=symbol, status="error").inc()
        raise
    except Exception as e:
        REQUEST_COUNT.labels(symbol=symbol, status="error").inc()
        logger.error(f"Prediction failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        ACTIVE_REQUESTS.dec()


@app.get("/symbols")
def list_symbols():
    """List all supported stock symbols."""
    return {"supported_symbols": SUPPORTED_SYMBOLS}


@app.get("/cache/clear")
def clear_cache():
    """Clear the in-memory model cache (forces retraining)."""
    _model_cache.clear()
    logger.info("Model cache cleared")
    return {"message": "Cache cleared successfully"}
