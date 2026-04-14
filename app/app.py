import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_DOCS_URL = os.getenv("API_DOCS_URL", f"{API_URL}/docs").rstrip("/")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "").rstrip("/")
GRAFANA_URL = os.getenv("GRAFANA_URL", "").rstrip("/")
API_TIMEOUT_SECONDS = int(os.getenv("API_TIMEOUT_SECONDS", "15"))
DEFAULT_SYMBOLS = ["AAPL", "GOOG", "MSFT", "AMZN"]


def fetch_symbols() -> list[str]:
    try:
        response = requests.get(f"{API_URL}/symbols", timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        return payload.get("supported_symbols", DEFAULT_SYMBOLS)
    except requests.RequestException:
        return DEFAULT_SYMBOLS


def check_health() -> tuple[bool, str | None]:
    try:
        response = requests.get(f"{API_URL}/health", timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        return True, None
    except requests.RequestException as exc:
        return False, str(exc)


st.set_page_config(page_title="Stock Prediction System", page_icon=":chart_with_upwards_trend:", layout="wide")

st.title("Real-Time Stock Price Prediction")
st.caption("Small stock prediction demo with FastAPI, Streamlit, and Prometheus metrics.")

symbols = fetch_symbols()

with st.sidebar:
    st.header("Settings")
    symbol = st.selectbox("Select Stock Symbol", symbols)
    st.caption(f"API URL: {API_URL}")
    st.divider()
    st.markdown("**System Links**")
    st.markdown(f"- [API Docs]({API_DOCS_URL})")
    if PROMETHEUS_URL:
        st.markdown(f"- [Prometheus]({PROMETHEUS_URL})")
    if GRAFANA_URL:
        st.markdown(f"- [Grafana]({GRAFANA_URL})")

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
is_healthy, health_error = check_health()
if is_healthy:
    st.success("API is healthy and reachable.")
else:
    st.error("API is unreachable.")
    if health_error:
        st.caption(f"Health check error: {health_error}")
    st.caption("If this is hosted on Render, confirm the UI service has API_URL set to your deployed API URL.")
