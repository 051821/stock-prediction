import logging
import os
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = APP_DIR / "stock_data.csv"
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


def get_stock_data(symbol: str) -> pd.DataFrame:
    symbol = symbol.upper()

    csv_df = _load_from_csv(symbol)
    if csv_df is not None:
        return csv_df

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"CSV dataset not found at {DATA_PATH}")

    raise ValueError(f"Symbol '{symbol}' not found in CSV dataset {DATA_PATH}")
