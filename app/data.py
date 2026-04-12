import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = APP_DIR / "stock_data.csv"
API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "demo")
DATA_PATH = Path(os.getenv("STOCK_DATA_PATH", str(DEFAULT_DATA_PATH)))


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA_10"] = df["Close"].rolling(10).mean()
    df["MA_20"] = df["Close"].rolling(20).mean()
    df["MA_50"] = df["Close"].rolling(50).mean()
    df["Daily_Return"] = df["Close"].pct_change()
    df["Volatility"] = df["Daily_Return"].rolling(10).std()
    df["Price_Range"] = df["High"] - df["Low"]
    df["Price_Momentum"] = df["Close"] - df["Close"].shift(5)
    return df.dropna()


def _load_from_csv(symbol: str) -> pd.DataFrame | None:
    if not DATA_PATH.exists():
        return None

    try:
        df = pd.read_csv(DATA_PATH, index_col="date", parse_dates=True)
        subset = df[df["company_name"] == symbol].drop(columns=["company_name"])
        subset.sort_index(inplace=True)
        if subset.empty:
            return None
        logger.info("Loaded %s from CSV (%s rows)", symbol, len(subset))
        return _add_features(subset)
    except Exception as exc:
        logger.warning("CSV load failed for %s: %s", symbol, exc)
        return None


def _load_from_api(symbol: str) -> pd.DataFrame | None:
    if API_KEY == "demo":
        return None

    try:
        import requests

        url = (
            "https://www.alphavantage.co/query"
            f"?function=TIME_SERIES_DAILY&symbol={symbol}"
            f"&outputsize=full&apikey={API_KEY}"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        series = data.get("Time Series (Daily)")
        if not series:
            return None

        df = pd.DataFrame.from_dict(series, orient="index")
        df = df.rename(
            columns={
                "1. open": "Open",
                "2. high": "High",
                "3. low": "Low",
                "4. close": "Close",
                "5. volume": "Volume",
            }
        ).astype(float)
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        logger.info("Fetched %s from Alpha Vantage (%s rows)", symbol, len(df))
        return _add_features(df)
    except Exception as exc:
        logger.warning("Alpha Vantage fetch failed for %s: %s", symbol, exc)
        return None


def _load_synthetic(symbol: str) -> pd.DataFrame:
    rng = np.random.default_rng(abs(hash(symbol)) % (2**31))
    n_rows = 300
    base_prices = {"AAPL": 175, "GOOG": 140, "MSFT": 380, "AMZN": 185}
    close = base_prices.get(symbol, 150) + np.cumsum(rng.normal(0, 2, n_rows))
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n_rows, freq="B")
    df = pd.DataFrame(
        {
            "Open": close * rng.uniform(0.99, 1.01, n_rows),
            "High": close * rng.uniform(1.00, 1.02, n_rows),
            "Low": close * rng.uniform(0.98, 1.00, n_rows),
            "Close": close,
            "Volume": rng.integers(10_000_000, 50_000_000, n_rows).astype(float),
        },
        index=dates,
    )
    logger.warning("Using synthetic data for %s", symbol)
    return _add_features(df)


def get_stock_data(symbol: str) -> pd.DataFrame:
    symbol = symbol.upper()

    csv_df = _load_from_csv(symbol)
    if csv_df is not None:
        return csv_df

    api_df = _load_from_api(symbol)
    if api_df is not None:
        return api_df

    return _load_synthetic(symbol)
