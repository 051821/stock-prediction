import pandas as pd
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "demo")
DATA_PATH = os.getenv("STOCK_DATA_PATH", "stock_data.csv")


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicator features to the dataframe."""
    df = df.copy()
    df["MA_10"] = df["Close"].rolling(10).mean()
    df["MA_20"] = df["Close"].rolling(20).mean()
    df["MA_50"] = df["Close"].rolling(50).mean()
    df["Daily_Return"] = df["Close"].pct_change()
    df["Volatility"] = df["Daily_Return"].rolling(10).std()
    df["Price_Range"] = df["High"] - df["Low"]
    df["Price_Momentum"] = df["Close"] - df["Close"].shift(5)
    df = df.dropna()
    return df


def get_stock_data(symbol: str) -> pd.DataFrame:
    """
    Load stock data for the given symbol.
    Priority: local CSV → Alpha Vantage API → synthetic fallback (demo mode).
    """
    symbol = symbol.upper()

    # ── 1. Try local CSV ───────────────────────────────────────────────────
    if os.path.exists(DATA_PATH):
        try:
            df = pd.read_csv(DATA_PATH, index_col="date", parse_dates=True)
            subset = df[df["company_name"] == symbol].drop(columns=["company_name"])
            subset.sort_index(inplace=True)
            if not subset.empty:
                logger.info(f"Loaded {symbol} from CSV ({len(subset)} rows)")
                return _add_features(subset)
        except Exception as e:
            logger.warning(f"CSV load failed: {e}")

    # ── 2. Try Alpha Vantage API ───────────────────────────────────────────
    if API_KEY != "demo":
        try:
            import requests
            url = (
                f"https://www.alphavantage.co/query"
                f"?function=TIME_SERIES_DAILY&symbol={symbol}"
                f"&outputsize=full&apikey={API_KEY}"
            )
            resp = requests.get(url, timeout=10)
            data = resp.json()

            if "Time Series (Daily)" in data:
                df = pd.DataFrame.from_dict(
                    data["Time Series (Daily)"], orient="index"
                )
                df = df.rename(columns={
                    "1. open": "Open", "2. high": "High",
                    "3. low": "Low",   "4. close": "Close",
                    "5. volume": "Volume"
                }).astype(float)
                df.index = pd.to_datetime(df.index)
                df.sort_index(inplace=True)
                logger.info(f"Fetched {symbol} from Alpha Vantage ({len(df)} rows)")
                return _add_features(df)
        except Exception as e:
            logger.warning(f"Alpha Vantage fetch failed: {e}")

    # ── 3. Synthetic fallback (for demo / CI) ─────────────────────────────
    logger.warning(f"Using synthetic data for {symbol}")
    np.random.seed(abs(hash(symbol)) % (2**31))
    n = 300
    base_prices = {"AAPL": 175, "GOOG": 140, "MSFT": 380, "AMZN": 185}.get(symbol, 150)
    closes = base_prices + np.cumsum(np.random.randn(n) * 2)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="B")
    df = pd.DataFrame({
        "Open":   closes * np.random.uniform(0.99, 1.01, n),
        "High":   closes * np.random.uniform(1.00, 1.02, n),
        "Low":    closes * np.random.uniform(0.98, 1.00, n),
        "Close":  closes,
        "Volume": np.random.randint(10_000_000, 50_000_000, n).astype(float),
    }, index=dates)
    return _add_features(df)
