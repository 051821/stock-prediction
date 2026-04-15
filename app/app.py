import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
DEFAULT_SYMBOLS = ["AAPL", "GOOG", "MSFT", "AMZN"]


def fetch_symbols() -> list[str]:
    try:
        response = requests.get(f"{API_URL}/symbols", timeout=5)
        response.raise_for_status()
        payload = response.json()
        return payload.get("supported_symbols", DEFAULT_SYMBOLS)
    except requests.RequestException:
        return DEFAULT_SYMBOLS


def check_health() -> bool:
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def fetch_history(symbol: str, days: int = 90) -> pd.DataFrame:
    response = requests.get(f"{API_URL}/history/{symbol}", params={"days": days}, timeout=10)
    response.raise_for_status()
    payload = response.json()
    history = payload.get("history", [])
    history_df = pd.DataFrame(history)
    if history_df.empty:
        return history_df
    history_df["date"] = pd.to_datetime(history_df["date"])
    return history_df


def fetch_prediction(symbol: str) -> dict:
    response = requests.get(f"{API_URL}/predict/{symbol}", timeout=30)
    response.raise_for_status()
    return response.json()


def build_price_chart(history_df: pd.DataFrame, symbol: str, predicted_close: float | None = None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history_df["date"],
            y=history_df["close"],
            mode="lines",
            name=f"{symbol} Close",
            line={"color": "#0f766e", "width": 3},
            fill="tozeroy",
            fillcolor="rgba(15, 118, 110, 0.10)",
        )
    )
    if predicted_close is not None and not history_df.empty:
        fig.add_trace(
            go.Scatter(
                x=[history_df["date"].iloc[-1]],
                y=[predicted_close],
                mode="markers",
                name="Predicted Next Close",
                marker={"size": 12, "color": "#dc2626", "symbol": "diamond"},
            )
        )

    fig.update_layout(
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.7)",
        legend={"orientation": "h", "y": 1.08, "x": 0},
        xaxis_title="Date",
        yaxis_title="Price (USD)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(15, 23, 42, 0.08)")
    return fig


st.set_page_config(page_title="Stock Prediction System", page_icon=":chart_with_upwards_trend:", layout="wide")
st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(16, 185, 129, 0.20), transparent 24%),
            radial-gradient(circle at top right, rgba(14, 165, 233, 0.18), transparent 20%),
            linear-gradient(180deg, #020617 0%, #0f172a 48%, #111827 100%);
        color: #e5eef9;
    }
    .block-container {
        padding-top: 1.5rem;
        max-width: 1280px;
    }
    .hero {
        padding: 1.5rem 1.7rem;
        border-radius: 20px;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.94), rgba(15, 118, 110, 0.86));
        color: white;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.16);
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0;
        font-size: 2.2rem;
    }
    .hero p {
        margin: 0.35rem 0 0;
        color: rgba(255,255,255,0.82);
    }
    .insight-card {
        padding: 1rem 1.1rem;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(30, 41, 59, 0.86));
        border: 1px solid rgba(94, 234, 212, 0.18);
        backdrop-filter: blur(8px);
        color: #f8fafc;
        box-shadow: 0 16px 36px rgba(2, 6, 23, 0.34);
    }
    .stApp h1, .stApp h2, .stApp h3, .stApp label, .stApp p, .stApp div {
        color: #e5eef9;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.88), rgba(30, 41, 59, 0.80));
        border: 1px solid rgba(125, 211, 252, 0.18);
        border-radius: 18px;
        padding: 0.9rem 1rem;
        box-shadow: 0 16px 28px rgba(2, 6, 23, 0.28);
    }
    [data-testid="stMetricLabel"] {
        color: #93c5fd;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: #f8fafc;
    }
    [data-testid="stMetricDelta"] {
        color: #4ade80;
    }
    .stPlotlyChart, [data-testid="stDataFrame"] {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.88), rgba(17, 24, 39, 0.82));
        border: 1px solid rgba(94, 234, 212, 0.16);
        border-radius: 18px;
        padding: 0.5rem;
        box-shadow: 0 14px 30px rgba(2, 6, 23, 0.28);
    }
    .stButton > button {
        border-radius: 14px;
        border: none;
        background: linear-gradient(135deg, #06b6d4, #14b8a6);
        color: white;
        font-weight: 700;
        box-shadow: 0 12px 24px rgba(20, 184, 166, 0.24);
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #0891b2, #0f766e);
        color: white;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.12);
    }
    section[data-testid="stSidebar"] * {
        color: #f8fafc;
    }
    [data-testid="stSidebar"] a {
        color: #67e8f9;
    }
    .stSlider [data-baseweb="slider"] > div > div {
        background: #22d3ee;
    }
    .stSelectbox [data-baseweb="select"] > div,
    .stTextInput input {
        background: rgba(15, 23, 42, 0.92);
        color: #f8fafc;
        border: 1px solid rgba(125, 211, 252, 0.18);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>Stock Prediction Studio</h1>
        <p>Track recent momentum, review model quality, and preview the next trading day's predicted close.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

symbols = fetch_symbols()

with st.sidebar:
    st.header("Settings")
    symbol = st.selectbox("Select Stock Symbol", symbols)
    lookback_days = st.slider("History Window", min_value=30, max_value=180, value=90, step=10)
    st.divider()
    st.markdown("**System Links**")
    st.markdown("- [API Docs](http://localhost:8000/docs)")
    st.markdown("- [Prometheus](http://localhost:9090)")
    st.markdown("- [Grafana](http://localhost:3000)")

run_prediction = st.button("Run Prediction", type="primary", use_container_width=True)

history_df = pd.DataFrame()
prediction: dict = {}

with st.spinner(f"Loading {symbol} market context..."):
    try:
        history_df = fetch_history(symbol, lookback_days)
    except requests.RequestException as exc:
        st.error(f"Could not load stock history: {exc}")

if run_prediction:
    with st.spinner(f"Generating next-day prediction for {symbol}..."):
        try:
            prediction = fetch_prediction(symbol)
        except requests.RequestException as exc:
            st.error(f"API request failed: {exc}")

latest_close = float(history_df["close"].iloc[-1]) if not history_df.empty else None
predicted_close = prediction.get("predicted_close") if prediction else None
delta_value = None
if latest_close is not None and predicted_close is not None:
    delta_value = predicted_close - latest_close

col1, col2, col3, col4 = st.columns(4)
col1.metric("Latest Close", f"${latest_close:.2f}" if latest_close is not None else "N/A")
col2.metric(
    "Predicted Next Close",
    f"${predicted_close:.2f}" if predicted_close is not None else "Run prediction",
    f"{delta_value:+.2f}" if delta_value is not None else None,
)
col3.metric("Validation R2", f"{prediction['model_r2']:.4f}" if prediction else "Pending")
col4.metric("Validation MAE", f"${prediction['model_mae']:.2f}" if prediction else "Pending")

chart_col, insight_col = st.columns([2.2, 1])

with chart_col:
    st.subheader(f"{symbol} Recent Trend")
    if history_df.empty:
        st.info("No history data available yet.")
    else:
        st.plotly_chart(
            build_price_chart(history_df, symbol, predicted_close if isinstance(predicted_close, (int, float)) else None),
            use_container_width=True,
        )

with insight_col:
    st.subheader("Snapshot")
    if history_df.empty:
        st.info("Historical market data will appear here once the API returns records.")
    else:
        start_close = float(history_df["close"].iloc[0])
        trend_pct = ((latest_close - start_close) / start_close) * 100 if latest_close is not None else 0.0
        day_range = float(history_df["high"].iloc[-1] - history_df["low"].iloc[-1])
        st.markdown(
            f"""
            <div class="insight-card">
                <strong>{symbol}</strong><br><br>
                {lookback_days}-day trend: <strong>{trend_pct:+.2f}%</strong><br>
                Latest daily range: <strong>${day_range:.2f}</strong><br>
                Horizon: <strong>{prediction.get('prediction_horizon', 'next trading day close')}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(
            history_df.tail(8).sort_values("date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

if prediction:
    st.success(f"Predicted next close for {symbol}: ${prediction['predicted_close']:.2f}")

st.divider()
st.subheader("System Health")
if check_health():
    st.success("API is healthy and reachable.")
else:
    st.error("API is unreachable.")
