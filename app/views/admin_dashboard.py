"""
Admin Dashboard — system overview, quick actions, and status summary.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import streamlit as st

from app.config import FORECAST_CSV, LEDGER_PATH, METRICS_PATH, MODEL_PATH, USERS_CSV, ANOMALY_PATH
from app.style import metric_card
from blockchain.ledger import load_ledger, verify_chain


def _block_count() -> int:
    if not os.path.exists(LEDGER_PATH):
        return 0
    with open(LEDGER_PATH, encoding="utf-8") as fh:
        return len(json.load(fh))


def _user_count() -> int:
    if not os.path.exists(USERS_CSV):
        return 0
    import pandas as pd
    try:
        return len(pd.read_csv(USERS_CSV))
    except Exception:
        return 0


def _mape() -> str:
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, encoding="utf-8") as fh:
            return f"{json.load(fh).get('mape', 0):.2f}%"
    return "—"


def _anomaly_count() -> int | None:
    if not os.path.exists(ANOMALY_PATH):
        return None
    with open(ANOMALY_PATH, encoding="utf-8") as fh:
        alerts = json.load(fh)
        return len(alerts)


def _data_pipeline_status() -> str:
    import pandas as pd
    if os.path.exists(FORECAST_CSV):
        try:
            return f"{len(pd.read_csv(FORECAST_CSV))} months loaded"
        except Exception:
            return "Data error"
    return "Data pipeline pending"


def _status_row(label: str, value: str, ok: bool | None = True) -> None:
    icon  = "✓" if ok is True else ("✗" if ok is False else "—")
    color = "#2E7D32" if ok is True else ("#C62828" if ok is False else "#BDBDBD")
    st.markdown(
        f'<div class="status-row">'
        f'<span class="status-label">{label}</span>'
        f'<span class="status-value">{value}</span>'
        f'<span style="color:{color};font-weight:700;font-size:16px">{icon}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    st.header("Admin Dashboard")
    st.caption("System overview for BloxLogicAI administrators")

    # ── KPI row ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    model_trained = os.path.exists(MODEL_PATH)

    anomalies = _anomaly_count()
    anomaly_trained = anomalies is not None

    with c1:
        metric_card("Registered Users", str(_user_count()), note="CSV-based user store")
    with c2:
        metric_card(
            "Forecast Model",
            "Trained" if model_trained else "Not trained",
            note=f"MAPE: {_mape()}",
        )
    with c3:
        metric_card("Blockchain Blocks", str(_block_count()), note="Locally verified")
    with c4:
        metric_card(
            "Anomaly Model", 
            "Trained" if anomaly_trained else "Not trained", 
            positive=anomaly_trained, 
            note=f"{anomalies} anomalies flagged" if anomaly_trained else "Isolation Forest — pending"
        )

    st.divider()

    # ── Quick actions + system status ─────────────────────────────────────────
    left, right = st.columns(2)

    with left:
        st.subheader("Quick Actions")


        if st.button("Retrain Forecast Model", use_container_width=True, type="primary"):
            with st.spinner("Retraining Prophet model…"):
                try:
                    from models import forecasting as fc
                    from app.views import forecast as forecast_view
                    df = fc.load_forecast_data()
                    fc.run_univariate_model(df)
                    forecast_view.get_model.clear()
                    forecast_view.get_forecast.clear()
                    forecast_view.load_metrics.clear()
                    st.success("Forecast model retrained.")
                except Exception as exc:
                    st.error(f"Retraining failed: {exc}")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("Run Anomaly Detection", use_container_width=True):
            with st.spinner("Running Isolation Forest…"):
                try:
                    from models import anomaly
                    num = anomaly.run_anomaly_detection()
                    st.success(f"Anomaly Detection complete — {num} anomalies flagged.")
                except Exception as exc:
                    st.error(f"Anomaly detection failed: {exc}")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("Verify Blockchain Integrity", use_container_width=True):
            blocks = load_ledger()
            ok = verify_chain(blocks)
            if ok:
                st.success(f"Chain VALID — {len(blocks)} blocks verified.")
            else:
                st.error("Chain INVALID — tampering detected.")



    with right:
        st.subheader("System Status")
        blocks = load_ledger()
        chain_ok = verify_chain(blocks) if blocks else True


        _status_row("Forecast Model",  "Trained" if model_trained else "Not trained", model_trained)
        _status_row("Forecast MAPE",   _mape(), True)
        _status_row("Anomaly Model",   "Trained" if anomaly_trained else "Not trained", anomaly_trained)
        _status_row("Data Pipeline",   _data_pipeline_status(), True)
        _status_row("Blockchain",      f"{len(blocks)} blocks · {'VALID' if chain_ok else 'INVALID'}", chain_ok)
        _status_row("Last Updated",    datetime.now().strftime("%Y-%m-%d"), True)

