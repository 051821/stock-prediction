"""
Tests for the Stock Prediction API.
Run with: pytest tests/ -v --cov=app
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../app"))

import pytest
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sample_df():
    """Synthetic stock dataframe for testing."""
    np.random.seed(42)
    n = 200
    closes = 150 + np.cumsum(np.random.randn(n))
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")
    df = pd.DataFrame({
        "Open":   closes * 0.995,
        "High":   closes * 1.01,
        "Low":    closes * 0.99,
        "Close":  closes,
        "Volume": np.random.randint(10_000_000, 50_000_000, n).astype(float),
    }, index=dates)
    # Add features manually
    df["MA_10"] = df["Close"].rolling(10).mean()
    df["MA_20"] = df["Close"].rolling(20).mean()
    df["MA_50"] = df["Close"].rolling(50).mean()
    df["Daily_Return"] = df["Close"].pct_change()
    df["Volatility"] = df["Daily_Return"].rolling(10).std()
    df["Price_Range"] = df["High"] - df["Low"]
    df["Price_Momentum"] = df["Close"] - df["Close"].shift(5)
    return df.dropna()


# ─── Model Tests ──────────────────────────────────────────────────────────────

class TestModel:
    def test_train_model_returns_pipeline(self, sample_df):
        from model import train_model
        model = train_model(sample_df)
        assert model is not None

    def test_predict_returns_float(self, sample_df):
        from model import train_model, predict
        model = train_model(sample_df)
        preds = predict(model, sample_df.tail(1))
        assert len(preds) == 1
        assert isinstance(float(preds[0]), float)

    def test_model_metrics_r2_range(self, sample_df):
        from model import train_model, get_model_metrics
        model = train_model(sample_df)
        metrics = get_model_metrics(model, sample_df)
        assert "r2_score" in metrics
        assert -1.0 <= metrics["r2_score"] <= 1.0

    def test_train_raises_on_small_df(self):
        from model import train_model
        tiny_df = pd.DataFrame({"Open": [1], "High": [2], "Low": [0.5],
                                 "Close": [1.5], "Volume": [1000],
                                 "MA_10": [1], "MA_20": [1], "MA_50": [1],
                                 "Daily_Return": [0], "Volatility": [0.1],
                                 "Price_Range": [0.5], "Price_Momentum": [0]})
        with pytest.raises(ValueError, match="Not enough data"):
            train_model(tiny_df)


# ─── Data Tests ───────────────────────────────────────────────────────────────

class TestData:
    def test_get_stock_data_returns_dataframe(self):
        from data import get_stock_data
        df = get_stock_data("AAPL")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_get_stock_data_has_required_columns(self):
        from data import get_stock_data
        df = get_stock_data("MSFT")
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_get_stock_data_has_feature_columns(self):
        from data import get_stock_data
        df = get_stock_data("GOOG")
        for col in ["MA_10", "MA_20", "Volatility", "Price_Range"]:
            assert col in df.columns


# ─── API Tests ────────────────────────────────────────────────────────────────

class TestAPI:
    @pytest.fixture(autouse=True)
    def client(self):
        from api import app
        self.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_ready_endpoint(self):
        resp = self.client.get("/ready")
        assert resp.status_code == 200

    def test_predict_valid_symbol(self):
        resp = self.client.get("/predict/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert "predicted_close" in data
        assert "model_r2" in data
        assert data["predicted_close"] > 0

    def test_predict_invalid_symbol(self):
        resp = self.client.get("/predict/INVALID")
        assert resp.status_code == 400

    def test_symbols_endpoint(self):
        resp = self.client.get("/symbols")
        assert resp.status_code == 200
        assert "supported_symbols" in resp.json()

    def test_cache_clear(self):
        # Warm cache
        self.client.get("/predict/AAPL")
        # Clear
        resp = self.client.get("/cache/clear")
        assert resp.status_code == 200
