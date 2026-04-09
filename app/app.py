import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="📈 Stock Prediction System",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Real-Time Stock Price Prediction")
st.caption("Cloud-native ML system powered by Kubernetes · Prometheus · Grafana")

# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    symbol = st.selectbox("Select Stock Symbol", ["AAPL", "GOOG", "MSFT", "AMZN"])
    st.markdown("---")
    st.markdown("**System Links**")
    st.markdown("- [Grafana Dashboard](http://localhost:3000)")
    st.markdown("- [Prometheus Metrics](http://localhost:9090)")
    st.markdown("- [API Docs](http://localhost:8000/docs)")

# ─── Prediction ─────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 2])

if st.button("🚀 Run Prediction", type="primary", use_container_width=True):
    with st.spinner(f"Fetching prediction for {symbol}..."):
        try:
            resp = requests.get(f"{API_URL}/predict/{symbol}", timeout=30)
            resp.raise_for_status()
            result = resp.json()

            col1.metric(
                label=f"💰 {symbol} Predicted Close",
                value=f"${result['predicted_close']:.2f}",
            )
            col2.metric(
                label="📊 Model R² Score",
                value=f"{result['model_r2']:.4f}",
                help="Closer to 1.0 = better model fit",
            )
            col3.metric(
                label="⚡ Latency",
                value=f"{result['latency_seconds'] * 1000:.1f} ms",
            )

            st.success(f"✅ Predicted next close price for **{symbol}**: **${result['predicted_close']:.2f}**")
            st.json(result)

        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to API. Is the backend running?")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# ─── System Health ───────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏥 System Health")

try:
    health = requests.get(f"{API_URL}/health", timeout=5)
    if health.status_code == 200:
        st.success("✅ API is healthy and running")
    else:
        st.warning("⚠️ API returned unexpected status")
except Exception:
    st.error("❌ API is unreachable")

# ─── Info cards ──────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏗️ System Architecture")

arch_col1, arch_col2, arch_col3 = st.columns(3)
with arch_col1:
    st.info("**☸️ Kubernetes**\nOrchestrates API pods with auto-scaling, rolling deployments, and self-healing.")
with arch_col2:
    st.info("**📊 Prometheus**\nScrapes /metrics every 15s — tracks latency, request counts, model accuracy.")
with arch_col3:
    st.info("**📈 Grafana**\nVisualises Prometheus data in real-time dashboards with alerting rules.")
