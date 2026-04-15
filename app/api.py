import logging
import os
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

try:
    from .data import get_stock_data
    from .metrics import (
        ACTIVE_REQUESTS,
        CACHE_HITS,
        DATA_POINTS_USED,
        LATENCY,
        MODEL_ACCURACY,
        MODEL_MAE,
        PREDICTION_VALUE,
        REQUEST_COUNT,
    )
    from .model import get_model_metrics, predict, train_model
except ImportError:
    from data import get_stock_data
    from metrics import (  # type: ignore
        ACTIVE_REQUESTS,
        CACHE_HITS,
        DATA_POINTS_USED,
        LATENCY,
        MODEL_ACCURACY,
        MODEL_MAE,
        PREDICTION_VALUE,
        REQUEST_COUNT,
    )
    from model import get_model_metrics, predict, train_model  # type: ignore


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

SUPPORTED_SYMBOLS = ("AAPL", "GOOG", "MSFT", "AMZN")
_model_cache: dict[str, object] = {}


def _validate_symbol(symbol: str) -> str:
    normalized = symbol.upper()
    if normalized not in SUPPORTED_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol '{normalized}' not supported. Choose from {list(SUPPORTED_SYMBOLS)}",
        )
    return normalized

app = FastAPI(
    title="Stock Price Prediction API",
    description="FastAPI service for simple stock price predictions.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/metrics", make_asgi_app())


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "stock-prediction-api"}


@app.get("/ready")
def readiness_check() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/symbols")
def list_symbols() -> dict[str, list[str]]:
    return {"supported_symbols": list(SUPPORTED_SYMBOLS)}


@app.get("/history/{symbol}")
def get_history(symbol: str, days: int = 90) -> dict[str, list[dict[str, float | str]] | str]:
    symbol = _validate_symbol(symbol)
    df = get_stock_data(symbol)
    if df.empty:
        raise HTTPException(status_code=503, detail=f"Could not fetch data for {symbol}")

    history_df = df.sort_index().tail(max(5, min(days, 365)))
    history = [
        {
            "date": index.strftime("%Y-%m-%d"),
            "close": round(float(row["Close"]), 2),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "volume": int(row["Volume"]),
        }
        for index, row in history_df.iterrows()
    ]
    return {"symbol": symbol, "history": history}


@app.get("/predict/{symbol}")
def get_prediction(symbol: str) -> dict[str, float | int | str]:
    symbol = _validate_symbol(symbol)

    ACTIVE_REQUESTS.inc()
    start = time.perf_counter()

    try:
        df = get_stock_data(symbol)
        if df.empty:
            raise HTTPException(status_code=503, detail=f"Could not fetch data for {symbol}")

        model = _model_cache.get(symbol)
        if model is None:
            logger.info("Training model for %s", symbol)
            model = train_model(df, use_full_data=True)
            _model_cache[symbol] = model
        else:
            CACHE_HITS.inc()
            logger.info("Cache hit for %s", symbol)

        validation_model = train_model(df, use_full_data=False)
        pred_value = float(predict(model, df.sort_index().tail(1))[0])
        model_metrics = get_model_metrics(validation_model, df)
        duration = time.perf_counter() - start

        REQUEST_COUNT.labels(symbol=symbol, status="success").inc()
        LATENCY.labels(symbol=symbol).observe(duration)
        PREDICTION_VALUE.labels(symbol=symbol).set(pred_value)
        MODEL_ACCURACY.labels(symbol=symbol).set(model_metrics["r2_score"])
        MODEL_MAE.labels(symbol=symbol).set(model_metrics["mae"])
        DATA_POINTS_USED.labels(symbol=symbol).set(len(df))

        return {
            "symbol": symbol,
            "predicted_close": round(pred_value, 2),
            "model_r2": round(model_metrics["r2_score"], 4),
            "model_mae": round(model_metrics["mae"], 4),
            "latency_seconds": round(duration, 4),
            "data_points_used": int(len(df)),
            "prediction_horizon": "next trading day close",
        }
    except HTTPException:
        REQUEST_COUNT.labels(symbol=symbol, status="error").inc()
        raise
    except Exception as exc:
        REQUEST_COUNT.labels(symbol=symbol, status="error").inc()
        logger.exception("Prediction failed for %s", symbol)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        ACTIVE_REQUESTS.dec()


@app.post("/cache/clear")
def clear_cache() -> dict[str, str]:
    _model_cache.clear()
    logger.info("Model cache cleared")
    return {"message": "Cache cleared successfully"}
