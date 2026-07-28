"""
User dashboard — overview KPI cards, export recommendation, anomaly summary.
"""

from __future__ import annotations

import html
import json
import os

import streamlit as st

from app.config import ANOMALY_PATH
from app.style import badge, metric_card, rec_box


def _load_alerts() -> list[dict]:
    if os.path.exists(ANOMALY_PATH):
        with open(ANOMALY_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return []


def render() -> None:
    st.header("Dashboard")
    st.caption("Supply Chain Overview — Sri Lanka Tea Industry · June 2026")

    # ── KPI cards ────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Current Production", "24,221 MT", "+3.2% vs last month", positive=True)
    with c2:
        metric_card("Forecasted Demand", "18,500 MT", note="Next month · Prophet model")
    with c3:
        metric_card("Recommended Export", "14,200 MT", note="Based on stock & safety margin")
    with c4:
        metric_card("Active Alerts", "3", "-2 vs last month", positive=False, note="1 HIGH · 2 MEDIUM")

    st.divider()

    # ── Export recommendation + anomaly summary ───────────────────────────────
    left, right = st.columns([11, 9])

    with left:
        st.subheader("Export Recommendation")
        st.markdown(
            """
<div style="background:#FFFFFF;border:1px solid #C8E6C9;border-radius:8px;padding:20px;">
  <table style="width:100%;border-collapse:collapse">
    <tr>
      <td style="color:#555;padding:6px 0;font-size:14px">Forecasted Demand</td>
      <td style="text-align:right;font-weight:600;font-size:14px">18,500 MT</td>
    </tr>
    <tr>
      <td style="color:#555;padding:6px 0;font-size:14px">Current Stock</td>
      <td style="text-align:right;font-weight:600;font-size:14px">24,221 MT</td>
    </tr>
    <tr>
      <td style="color:#555;padding:6px 0;font-size:14px">Safety Margin</td>
      <td style="text-align:right;font-weight:600;font-size:14px">4,300 MT</td>
    </tr>
    <tr>
      <td colspan="2" style="border-top:2px solid #C8E6C9;padding-top:8px"></td>
    </tr>
  </table>
</div>""",
            unsafe_allow_html=True,
        )
        rec_box("Recommended Export this month", "14,200 MT")
        st.caption("Formula: Forecasted Demand − (Current Stock − Safety Margin)")

    with right:
        st.subheader("Recent Anomaly Alerts")
        alerts = _load_alerts()
        st.markdown(
            '<div style="background:#FFFFFF;border:1px solid #C8E6C9;'
            'border-radius:8px;padding:16px 20px;">',
            unsafe_allow_html=True,
        )
        if alerts:
            for alert in alerts[:3]:
                st.markdown(
                    f"{badge(alert['severity'])} &nbsp;"
                    f"<strong>{html.escape(alert['date'])}</strong> &nbsp; "
                    f"<span style='font-size:14px'>{html.escape(alert['type'])}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='color:#777;font-size:12px;margin:2px 0 12px 0'>"
                    f"{html.escape(alert['action'])}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No anomaly data loaded.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("Open **Anomaly Detection** in the sidebar to view all alerts.")
