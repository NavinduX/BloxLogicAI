"""
Admin — Forecast Model Management: train, retrain, and monitor forecasting model.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import streamlit as st

from app.config import FORECAST_CSV, METRICS_PATH, MODEL_PATH


def _load_metrics() -> dict | None:
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def render() -> None:
    st.header("Forecast Model")
    st.caption("Train and monitor the AI forecasting model.")

    metrics = _load_metrics()
    model_trained = os.path.exists(MODEL_PATH)


    st.subheader("Demand Forecasting — Prophet")
    status_color = "#2E7D32" if model_trained else "#C62828"
    status_text  = "Trained" if model_trained else "Not trained"
    st.markdown(
        f'<p><strong>Status:</strong> '
        f'<span style="color:{status_color};font-weight:700">{status_text}</span></p>',
        unsafe_allow_html=True,
    )
    st.markdown("**Algorithm:** Facebook Prophet (univariate)")
    st.markdown("**Seasonality:** yearly multiplicative")
    st.markdown("**Training span:** Oct 2011 – Apr 2026 (~175 months)")
    st.markdown("**Backtest:** last 12 months hold-out")

    if metrics:
        m1, m2, m3 = st.columns(3)
        m1.metric("MAPE",  f"{metrics['mape']:.2f}%")
        m2.metric("MAE",   f"{metrics['mae']:,.0f} MT")
        m3.metric("RMSE",  f"{metrics['rmse']:,.0f} MT")
    else:
        st.info("No metrics. Train the model first.")

    st.markdown("<br>", unsafe_allow_html=True)
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        if st.button("Train Model", use_container_width=True,
                     disabled=model_trained,
                     help="Model already trained — use Retrain."):
            _run_training()
    with bcol2:
        if st.button("Retrain Model", use_container_width=True, type="primary"):
            _run_training()


    # ── Action log ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Action Log")
    if "forecast_log" not in st.session_state:
        st.session_state.forecast_log = []
    if st.session_state.forecast_log:
        for entry in reversed(st.session_state.forecast_log[-5:]):
            st.markdown(f"- {entry}")
    else:
        st.info("No actions recorded this session.")


def _run_training() -> None:
    with st.spinner("Training Univariate & Multivariate Prophet models..."):
        try:
            from models import forecasting as fc
            
            # Train Univariate
            df_uni = fc.load_forecast_data()
            res_uni = fc.run_univariate_model(df_uni)
            
            # Train Multivariate
            df_mv = fc.load_multivariate_data()
            res_mv = fc.run_multivariate_model(df_mv)

            from app.views import forecast as forecast_view
            forecast_view.get_model.clear()
            forecast_view.get_forecast.clear()
            forecast_view.load_metrics.clear()
            
            metrics_uni = res_uni["metrics"]
            metrics_mv = res_mv["metrics"]

            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"{ts} — Retrained · Uni MAPE {metrics_uni['mape']:.2f}% · Multi MAPE {metrics_mv['mape']:.2f}%"
            st.success(f"Models trained! Univariate MAPE: {metrics_uni['mape']:.2f}% | Multivariate MAPE: {metrics_mv['mape']:.2f}%")
            st.session_state.setdefault("forecast_log", []).append(entry)
            st.rerun()
        except Exception as exc:
            st.error(f"Training failed: {exc}")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.setdefault("forecast_log", []).append(f"{ts} — Training failed: {exc}")
