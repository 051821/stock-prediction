import asyncio
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

from app.api import app
from app.data import get_stock_data
from app.model import get_model_metrics, predict, train_model


@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n_rows = 200
    closes = 150 + np.cumsum(rng.normal(size=n_rows))
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_rows, freq="B")
    df = pd.DataFrame(
        {
            "Open": closes * 0.995,
            "High": closes * 1.01,
            "Low": closes * 0.99,
            "Close": closes,
            "Volume": rng.integers(10_000_000, 50_000_000, n_rows).astype(float),
        },
        index=dates,
    )
    df["MA_10"] = df["Close"].rolling(10).mean()
    df["MA_20"] = df["Close"].rolling(20).mean()
    df["MA_50"] = df["Close"].rolling(50).mean()
    df["Daily_Return"] = df["Close"].pct_change()
    df["Volatility"] = df["Daily_Return"].rolling(10).std()
    df["Price_Range"] = df["High"] - df["Low"]
    df["Price_Momentum"] = df["Close"] - df["Close"].shift(5)
    return df.dropna()


def request_json(method: str, path: str) -> httpx.Response:
    async def _request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path)

    return asyncio.run(_request())


def test_train_model_returns_pipeline(sample_df: pd.DataFrame) -> None:
    model = train_model(sample_df)
    assert model is not None


def test_predict_returns_single_value(sample_df: pd.DataFrame) -> None:
    model = train_model(sample_df)
    preds = predict(model, sample_df.tail(1))
    assert len(preds) == 1
    assert isinstance(float(preds[0]), float)


def test_model_metrics_r2_range(sample_df: pd.DataFrame) -> None:
    model = train_model(sample_df)
    metrics = get_model_metrics(model, sample_df)
    assert "r2_score" in metrics
    assert -1.0 <= metrics["r2_score"] <= 1.0


def test_train_raises_on_small_df() -> None:
    tiny_df = pd.DataFrame(
        {
            "Open": [1],
            "High": [2],
            "Low": [0.5],
            "Close": [1.5],
            "Volume": [1000],
            "MA_10": [1],
            "MA_20": [1],
            "MA_50": [1],
            "Daily_Return": [0],
            "Volatility": [0.1],
            "Price_Range": [0.5],
            "Price_Momentum": [0],
        }
    )
    with pytest.raises(ValueError, match="Not enough data"):
        train_model(tiny_df)


def test_get_stock_data_returns_dataframe() -> None:
    df = get_stock_data("AAPL")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_get_stock_data_has_required_columns() -> None:
    df = get_stock_data("MSFT")
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        assert column in df.columns


def test_get_stock_data_has_feature_columns() -> None:
    df = get_stock_data("GOOG")
    for column in ["MA_10", "MA_20", "Volatility", "Price_Range"]:
        assert column in df.columns


def test_health_endpoint() -> None:
    response = request_json("GET", "/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_ready_endpoint() -> None:
    response = request_json("GET", "/ready")
    assert response.status_code == 200


def test_predict_valid_symbol() -> None:
    response = request_json("GET", "/predict/AAPL")
    assert response.status_code == 200
    payload = response.json()
    assert payload["predicted_close"] > 0
    assert "model_r2" in payload


def test_predict_invalid_symbol() -> None:
    response = request_json("GET", "/predict/INVALID")
    assert response.status_code == 400


def test_symbols_endpoint() -> None:
    response = request_json("GET", "/symbols")
    assert response.status_code == 200
    assert response.json()["supported_symbols"]


def test_cache_clear_endpoint() -> None:
    request_json("GET", "/predict/AAPL")
    response = request_json("POST", "/cache/clear")
    assert response.status_code == 200
