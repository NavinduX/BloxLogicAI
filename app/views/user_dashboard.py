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
    
    try:
        from app.views.forecast import get_data, get_forecast
        df_mv = get_data("multivariate")
        fc_df = get_forecast("univariate", horizon=1)
        
        latest = df_mv.iloc[-1]
        prev = df_mv.iloc[-2]
        
        curr_prod = latest["production_mt"]
        prev_prod = prev["production_mt"]
        prod_pct = (curr_prod - prev_prod) / prev_prod * 100
        
        forecast_val = fc_df.iloc[-1]["yhat"]
        
        safety_margin = 4300
        available = curr_prod - safety_margin
        rec_export = min(forecast_val, available)
        if rec_export < 0: rec_export = 0
        date_str = latest["ds"].strftime("%B %Y")
        data_available = True
    except Exception:
        curr_prod = 0
        prod_pct = 0.0
        forecast_val = 0
        safety_margin = 0
        rec_export = 0
        date_str = "Data unavailable"
        data_available = False
        
    st.caption(f"Supply Chain Overview — Sri Lanka Tea Industry · {date_str}")

    if not data_available:
        st.info("ℹ️ Dashboard data is currently unavailable. (Clean slate demo mode: please log in as an administrator to generate datasets and train the AI models).")

    alerts = _load_alerts()
    active_count = len(alerts)
    high_count = sum(1 for a in alerts if a.get("severity") == "HIGH")
    med_count = sum(1 for a in alerts if a.get("severity") == "MEDIUM")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        prod_val_str = f"{curr_prod:,.0f} MT" if data_available else "—"
        prod_delta_str = f"{prod_pct:+.1f}% vs last month" if data_available else None
        metric_card("Current Production", prod_val_str, prod_delta_str, positive=(prod_pct>=0))
    with c2:
        fc_val_str = f"{forecast_val:,.0f} MT" if data_available else "—"
        metric_card("Forecasted Demand", fc_val_str, note="Next month · Prophet model")
    with c3:
        rec_val_str = f"{rec_export:,.0f} MT" if data_available else "—"
        metric_card("Recommended Export", rec_val_str, note="Based on stock & safety margin")
    with c4:
        metric_card("Active Alerts", str(active_count), positive=(active_count==0), note=f"{high_count} HIGH · {med_count} MEDIUM")

    st.divider()

    # ── Export recommendation + anomaly summary ───────────────────────────────
    left, right = st.columns([11, 9])

    with left:
        st.subheader("Export Recommendation")
        st.markdown(
            f"""
<div style="background:#FFFFFF;border:1px solid #C8E6C9;border-radius:8px;padding:20px;">
  <table style="width:100%;border-collapse:collapse">
    <tr>
      <td style="color:#555;padding:6px 0;font-size:14px">Forecasted Demand</td>
      <td style="text-align:right;font-weight:600;font-size:14px">{fc_val_str}</td>
    </tr>
    <tr>
      <td style="color:#555;padding:6px 0;font-size:14px">Current Stock</td>
      <td style="text-align:right;font-weight:600;font-size:14px">{prod_val_str}</td>
    </tr>
    <tr>
      <td style="color:#555;padding:6px 0;font-size:14px">Safety Margin</td>
      <td style="text-align:right;font-weight:600;font-size:14px">{f"{safety_margin:,.0f} MT" if data_available else "—"}</td>
    </tr>
    <tr>
      <td colspan="2" style="border-top:2px solid #C8E6C9;padding-top:8px"></td>
    </tr>
  </table>
</div>""",
            unsafe_allow_html=True,
        )
        rec_box("Recommended Export this month", rec_val_str)
        st.caption("Formula: min(Forecasted Demand, Current Stock − Safety Margin)")

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
