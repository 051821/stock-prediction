import os

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


st.set_page_config(page_title="Stock Prediction System", page_icon=":chart_with_upwards_trend:", layout="wide")

st.title("Real-Time Stock Price Prediction")
st.caption("Small stock prediction demo with FastAPI, Streamlit, and Prometheus metrics.")

symbols = fetch_symbols()

with st.sidebar:
    st.header("Settings")
    symbol = st.selectbox("Select Stock Symbol", symbols)
    st.divider()
    st.markdown("**System Links**")
    st.markdown("- [API Docs](http://localhost:8000/docs)")
    st.markdown("- [Prometheus](http://localhost:9090)")
    st.markdown("- [Grafana](http://localhost:3000)")

col1, col2, col3 = st.columns(3)

if st.button("Run Prediction", type="primary", use_container_width=True):
    with st.spinner(f"Fetching prediction for {symbol}..."):
        try:
            response = requests.get(f"{API_URL}/predict/{symbol}", timeout=30)
            response.raise_for_status()
            result = response.json()

            col1.metric("Predicted Close", f"${result['predicted_close']:.2f}")
            col2.metric("Model R2", f"{result['model_r2']:.4f}")
            col3.metric("Latency", f"{result['latency_seconds'] * 1000:.1f} ms")

            st.success(f"Predicted next close for {symbol}: ${result['predicted_close']:.2f}")
            st.json(result)
        except requests.RequestException as exc:
            st.error(f"API request failed: {exc}")

st.divider()
st.subheader("System Health")
if check_health():
    st.success("API is healthy and reachable.")
else:
    st.error("API is unreachable.")
