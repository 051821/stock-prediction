from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_absolute_error
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

FEATURES = ["Open", "High", "Low", "Volume", "MA_10", "MA_20", "Volatility", "Price_Range", "Price_Momentum"]
TARGET = "Close"


def train_model(df: pd.DataFrame) -> Pipeline:
    """
    Train a Gradient Boosting model with feature scaling.
    Returns a sklearn Pipeline (scaler + model).
    """
    df = df.dropna(subset=FEATURES + [TARGET])

    if len(df) < 30:
        raise ValueError(f"Not enough data to train: {len(df)} rows")

    X = df[FEATURES]
    y = df[TARGET]

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model", GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=4,
            random_state=42,
        ))
    ])

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
    """Evaluate model on the last 20% of the dataset."""
    df = df.dropna(subset=FEATURES + [TARGET])
    split = int(len(df) * 0.8)
    test_df = df.iloc[split:]

    if test_df.empty:
        return {"r2_score": 0.0, "mae": 0.0}

    X_test = test_df[FEATURES]
    y_test = test_df[TARGET]
    y_pred = model.predict(X_test)

    return {
        "r2_score": float(r2_score(y_test, y_pred)),
        "mae": float(mean_absolute_error(y_test, y_pred)),
    }
