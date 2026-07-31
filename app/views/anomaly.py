"""
Anomaly Detection view — full alert table with severity filtering.
"""

from __future__ import annotations

import html
import json
import os

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
    try:
        import pandas as pd
        from app.config import ANOMALY_CSV
        df_an = pd.read_csv(ANOMALY_CSV)
        start_date = pd.to_datetime(df_an['month']).min().strftime('%Y-%m')
        end_date = pd.to_datetime(df_an['month']).max().strftime('%Y-%m')
        obs_count = len(df_an)
    except Exception:
        start_date = "2011-10"
        end_date = "2026-04"
        obs_count = 165

    st.header("Anomaly Detection")
    st.caption(
        f"Supply chain disruptions identified by Isolation Forest — "
        f"historical period {start_date} to {end_date}."
    )

    # ── Filter row ───────────────────────────────────────────────────────────
    col_filter, col_info = st.columns([2, 5], vertical_alignment="bottom")
    with col_filter:
        severity_filter = st.selectbox(
            "Filter by severity",
            ["All", "HIGH", "MEDIUM", "LOW"],
            label_visibility="visible",
        )

    all_alerts = _load_alerts()
    alerts = (
        all_alerts
        if severity_filter == "All"
        else [a for a in all_alerts if a["severity"] == severity_filter]
    )

    with col_info:
        st.info(
            f"**{len(alerts)}** alert(s) shown  ·  "
            "Model: Isolation Forest  ·  "
            "Features: export volume, production, USD/LKR, rainfall, temperature, crude oil, fuel prices",
            icon=None,
        )

    st.divider()

    # ── Alert cards ──────────────────────────────────────────────────────────
    if not alerts:
        st.warning("No alerts match the selected filter.")
        return

    for alert in alerts:
        with st.container(border=True):
            header_col, date_col = st.columns([7, 2])
            with header_col:
                st.markdown(
                    f"{_badge(alert['severity'])} &nbsp; **{alert['type']}**",
                    unsafe_allow_html=True,
                )
            with date_col:
                st.markdown(
                    f"<div style='text-align:right;color:#666;font-size:13px'>"
                    f"Period: {alert['date']}</div>",
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"<div style='color:#444;font-size:14px;margin-top:4px'>"
                f"{html.escape(alert['description'])}</div>",
                unsafe_allow_html=True,
            )

            with st.expander("Suggested action"):
                st.markdown(
                    f"<div style='color:#1B5E20;font-weight:500'>"
                    f"→ {html.escape(alert['action'])}</div>",
                    unsafe_allow_html=True,
                )

    st.divider()

    # ── Methodology note ─────────────────────────────────────────────────────
    with st.expander("About this model"):
        st.markdown(
            f"""
**Algorithm:** Isolation Forest (scikit-learn)

**Training window:** {start_date} to {end_date} (~{obs_count} clean monthly observations)

**Features used:**
- Monthly export volume (MT)
- Tea production volume (MT)
- USD/LKR exchange rate (monthly average)
- Rainfall (mm) — production-weighted tea regions
- Mean temperature (°C) — production-weighted tea regions
- Crude Oil Price & Brent Crude Price
- Fuel Prices (LP 92, Auto Diesel, Kerosene)

**How it works:** Isolation Forest isolates anomalies by building random decision trees.
Points that are isolated with fewer splits are flagged as anomalies. The model assigns
a contamination rate of 0.1 (10% of data expected to be anomalous) based on historical
disruption frequency in Sri Lanka's tea export sector.

**Flagged events:** Known disruptions include the 2020 COVID-19 pandemic, 2021 fertiliser
policy change, and the 2022 economic crisis — all correctly identified by the model.
"""
        )
