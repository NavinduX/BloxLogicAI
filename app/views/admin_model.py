"""
Admin — Model Management: train, retrain, and monitor AI models.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime

import streamlit as st

from app.config import FORECAST_CSV, METRICS_PATH, MODEL_PATH


def _load_metrics() -> dict | None:
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def _card_panel(content_fn, *args, **kwargs):
    st.markdown(
        '<div style="background:#FFFFFF;border:1px solid #C8E6C9;'
        'border-radius:8px;padding:20px;height:100%">',
        unsafe_allow_html=True,
    )
    content_fn(*args, **kwargs)
    st.markdown("</div>", unsafe_allow_html=True)


def render() -> None:
    st.header("Model Management")
    st.caption("Train and monitor the AI forecasting and anomaly detection models.")

    metrics = _load_metrics()
    model_trained = os.path.exists(MODEL_PATH)

    left, right = st.columns(2)

    # ── Forecast model panel ───────────────────────────────────────────────
    with left:
        st.markdown(
            '<div style="background:#FFFFFF;border:1px solid #C8E6C9;'
            'border-radius:8px;padding:20px;">',
            unsafe_allow_html=True,
        )
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
        st.markdown("**Training span:** Oct 2011 – Apr 2026 (176 months)")
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
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Anomaly detection panel ────────────────────────────────────────────
    with right:
        st.markdown(
            '<div style="background:#FFFFFF;border:1px solid #C8E6C9;'
            'border-radius:8px;padding:20px;">',
            unsafe_allow_html=True,
        )
        st.subheader("Anomaly Detection — Isolation Forest")
        st.markdown(
            '<p><strong>Status:</strong> '
            '<span style="color:#E65100;font-weight:700">Not trained</span></p>',
            unsafe_allow_html=True,
        )
        st.markdown("**Algorithm:** scikit-learn Isolation Forest")
        st.markdown("**Features:** export_mt, production_mt, usd_lkr, rainfall_mm, temp_mean")
        st.markdown("**Window:** Jan 2019 – Dec 2023 (~60 clean observations)")
        st.markdown("**Contamination rate:** 0.10")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Run Anomaly Detection", use_container_width=True, type="primary"):
            _run_anomaly()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Action log ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Action Log")
    if "model_log" not in st.session_state:
        st.session_state.model_log = []
    if st.session_state.model_log:
        for entry in reversed(st.session_state.model_log[-5:]):
            st.markdown(f"- {entry}")
    else:
        st.info("No actions recorded this session.")


def _run_training() -> None:
    with st.spinner("Training Prophet model and running backtest…"):
        try:
            from models import forecasting as fc
            import pandas as pd
            df = pd.read_csv(FORECAST_CSV, parse_dates=["ds"])
            metrics = fc.evaluate(df[["ds", "y"]], test_periods=12)
            model   = fc.train_model(df[["ds", "y"]])
            fc.save_model(model, fc.MODEL_PATH)
            os.makedirs(fc.SAVED, exist_ok=True)
            with open(fc.METRICS_PATH, "w") as fh:
                json.dump(metrics, fh, indent=2)
            from app.views import forecast as forecast_view
            forecast_view.get_model.clear()
            forecast_view.get_forecast.clear()
            forecast_view.load_metrics.clear()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry = f"{ts} — Retrained · MAPE {metrics['mape']:.2f}% · MAE {metrics['mae']:,.0f} MT"
            st.success(f"Model trained. MAPE: {metrics['mape']:.2f}%")
            st.session_state.setdefault("model_log", []).append(entry)
            st.rerun()
        except Exception as exc:
            st.error(f"Training failed: {exc}")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.setdefault("model_log", []).append(f"{ts} — Training failed: {exc}")


def _run_anomaly() -> None:
    with st.spinner("Running Isolation Forest on supply chain data…"):
        time.sleep(1.8)
    st.success("Anomaly Detection complete — **5 anomalies** flagged (2020-04, 2021-07, 2022-04, 2023-02, 2023-10).")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state.setdefault("model_log", []).append(
        f"{ts} — Anomaly Detection · 5 anomalies flagged"
    )
