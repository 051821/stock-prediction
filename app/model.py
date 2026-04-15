import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

FEATURES = ["Open", "High", "Low", "Volume", "MA_10", "MA_20", "Volatility", "Price_Range", "Price_Momentum"]
TARGET = "Target_Close"


def _build_pipeline() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=4,
            random_state=42,
        )),
    ])


def prepare_training_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a next-day prediction target using only information available
    at the end of the current trading day.
    """
    prepared = df.copy().sort_index()
    prepared[TARGET] = prepared["Close"].shift(-1)
    prepared = prepared.dropna(subset=FEATURES + [TARGET])
    return prepared


def split_train_test(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    prepared = prepare_training_data(df)
    split = int(len(prepared) * 0.8)
    train_df = prepared.iloc[:split]
    test_df = prepared.iloc[split:]
    return train_df, test_df


def train_model(df: pd.DataFrame, use_full_data: bool = True) -> Pipeline:
    """
    Train a Gradient Boosting model with feature scaling for next-day close prediction.
    Returns a sklearn Pipeline (scaler + model).
    """
    prepared = prepare_training_data(df)
    train_df = prepared if use_full_data else split_train_test(df)[0]

    if len(train_df) < 30:
        raise ValueError(f"Not enough data to train: {len(train_df)} rows")

    X = train_df[FEATURES]
    y = train_df[TARGET]

    pipeline = _build_pipeline()
    pipeline.fit(X, y)
    logger.info(f"Model trained on {len(X)} samples with {len(FEATURES)} features")
    return pipeline


def predict(model: Pipeline, df: pd.DataFrame) -> np.ndarray:
    """Run inference on a dataframe slice."""
    available = [f for f in FEATURES if f in df.columns]
    if len(available) < len(FEATURES):
        missing = set(FEATURES) - set(available)
        raise ValueError(f"Missing features for prediction: {missing}")
    return model.predict(df[FEATURES])


def get_model_metrics(model: Pipeline, df: pd.DataFrame) -> dict:
    """Evaluate model on a chronological holdout set."""
    _, test_df = split_train_test(df)

    if test_df.empty or len(test_df) < 2:
        return {"r2_score": 0.0, "mae": 0.0}

    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]
    y_pred = model.predict(X_test)

    return {
        "r2_score": float(r2_score(y_test, y_pred)),
        "mae": float(mean_absolute_error(y_test, y_pred)),
    }
