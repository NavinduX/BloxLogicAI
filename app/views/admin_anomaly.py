"""
Admin — Anomaly Model Management: train and monitor anomaly detection model.
"""

from __future__ import annotations

import json
import os
import html
from datetime import datetime

import streamlit as st

from app.config import ANOMALY_PATH


def _load_alerts() -> list[dict]:
    if os.path.exists(ANOMALY_PATH):
        with open(ANOMALY_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return []


def _badge(severity: str) -> str:
    cls = {
        "HIGH":   "badge-high",
        "MEDIUM": "badge-medium",
        "LOW":    "badge-low",
    }.get(severity.upper(), "badge-low")
    return f'<span class="{cls}">{severity}</span>'


def render() -> None:
    st.header("Anomaly Detection Model")
    st.caption("Train and monitor the Isolation Forest anomaly detection model.")

    alerts = _load_alerts()
    model_trained = os.path.exists(ANOMALY_PATH)

    st.markdown(
        '<div style="background:#FFFFFF;border:1px solid #C8E6C9;'
        'border-radius:8px;padding:20px;">',
        unsafe_allow_html=True,
    )
    st.subheader("Anomaly Detection — Isolation Forest")
    status_color = "#2E7D32" if model_trained else "#E65100"
    status_text  = "Trained" if model_trained else "Not trained"
    st.markdown(
        f'<p><strong>Status:</strong> '
        f'<span style="color:{status_color};font-weight:700">{status_text}</span></p>',
        unsafe_allow_html=True,
    )
    st.markdown("**Algorithm:** scikit-learn Isolation Forest")
    st.markdown("**Features:** export volume, production, USD/LKR, rainfall, temperature, crude oil, fuel prices")
    st.markdown("**Training window:** 2011 to 2026 (~160 clean monthly observations)")
    st.markdown("**Contamination rate:** 0.10")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Run Anomaly Detection", use_container_width=True, type="primary"):
        _run_anomaly()
    st.markdown("</div>", unsafe_allow_html=True)

    if model_trained and alerts:
        st.subheader("Detected Anomalies")
        for alert in alerts:
            with st.container(border=True):
                header_col, date_col = st.columns([7, 2])
                with header_col:
                    st.markdown(f"{_badge(alert['severity'])} &nbsp; **{alert['type']}**", unsafe_allow_html=True)
                with date_col:
                    st.markdown(f"<div style='text-align:right;color:#666;font-size:13px'>Period: {alert['date']}</div>", unsafe_allow_html=True)

                st.markdown(f"<div style='color:#444;font-size:14px;margin-top:4px'>{html.escape(alert['description'])}</div>", unsafe_allow_html=True)
                with st.expander("Suggested action"):
                    st.markdown(f"<div style='color:#1B5E20;font-weight:500'>→ {html.escape(alert['action'])}</div>", unsafe_allow_html=True)


    # ── Action log ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Action Log")
    if "anomaly_log" not in st.session_state:
        st.session_state.anomaly_log = []
    if st.session_state.anomaly_log:
        for entry in reversed(st.session_state.anomaly_log[-5:]):
            st.markdown(f"- {entry}")
    else:
        st.info("No actions recorded this session.")


def _run_anomaly() -> None:
    with st.spinner("Running Isolation Forest on supply chain data…"):
        from models import anomaly
        try:
            num_anomalies = anomaly.run_anomaly_detection()
            st.success(f"Anomaly Detection complete — **{num_anomalies} anomalies** flagged.")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.setdefault("anomaly_log", []).append(
                f"{ts} — Anomaly Detection · {num_anomalies} anomalies flagged"
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Anomaly detection failed: {exc}")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            st.session_state.setdefault("anomaly_log", []).append(f"{ts} — Anomaly detection failed: {exc}")
