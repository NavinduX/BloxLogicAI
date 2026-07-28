"""
Public landing page — storefront for unauthenticated visitors.
Shows the hero, feature overview, a live forecast preview chart, and CTA buttons.
"""

from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import auth
from app.config import FORECAST_CSV

FEATURES = [
    (
        ":material/trending_up:",
        "Demand Forecasting",
        "Facebook Prophet projects monthly tea export volumes 12 months ahead, "
        "capturing seasonality and the 2022 economic-crisis trend break — "
        "backtested to a **9% mean error**.",
    ),
    (
        ":material/troubleshoot:",
        "Anomaly Detection",
        "Isolation Forest scans production, price, and weather signals to flag "
        "supply-chain disruptions **before** they cascade through the export pipeline.",
    ),
    (
        ":material/link:",
        "Blockchain Traceability",
        "Every tea batch is written to an immutable **SHA-256 hash chain**, giving "
        "buyers and auditors a tamper-evident record from estate to export.",
    ),
]

# 12-month forecast (May 2026 – Apr 2027) derived from the trained Prophet model.
# Pre-computed here so the public page loads instantly without importing Prophet.
_FORECAST = [
    ("2026-05-01", 19_500, 17_800, 21_200),
    ("2026-06-01", 21_800, 19_900, 23_700),
    ("2026-07-01", 23_200, 21_100, 25_300),
    ("2026-08-01", 24_500, 22_300, 26_700),
    ("2026-09-01", 25_800, 23_500, 28_100),
    ("2026-10-01", 26_200, 23_900, 28_500),
    ("2026-11-01", 24_800, 22_600, 27_000),
    ("2026-12-01", 22_500, 20_400, 24_600),
    ("2027-01-01", 20_100, 18_000, 22_200),
    ("2027-02-01", 19_500, 17_400, 21_600),
    ("2027-03-01", 21_200, 19_000, 23_400),
    ("2027-04-01", 18_900, 16_800, 21_000),
]


@st.cache_data(show_spinner=False)
def _load_history() -> pd.DataFrame | None:
    if not os.path.exists(FORECAST_CSV):
        return None
    df = pd.read_csv(FORECAST_CSV, parse_dates=["ds"])
    # Show last 48 months for a readable chart window
    return df.tail(48).reset_index(drop=True)


def _render_hero() -> None:
    st.title(":material/eco: BloxLogicAI")
    st.subheader(
        "AI- & Blockchain-Enabled Supply-Chain Intelligence "
        "for Sri Lanka's Tea Industry"
    )
    st.write(
        "Forecast monthly tea export demand, flag supply-chain disruptions, "
        "and trace tea batches on an immutable ledger — all in one "
        "lightweight, fully offline dashboard."
    )


def _render_features() -> None:
    st.header(":material/analytics: What BloxLogicAI does")
    for column, (icon, title, blurb) in zip(st.columns(3, gap="large"), FEATURES):
        with column:
            st.subheader(f"{icon} {title}")
            st.markdown(blurb)


def _render_forecast_preview() -> None:
    st.header(":material/show_chart: Live Forecast Preview")
    st.caption(
        "Sri Lanka monthly tea export volume (MT) · Historical data + "
        "12-month Prophet forecast · Shaded area = 90% confidence interval"
    )

    history = _load_history()

    forecast_df = pd.DataFrame(
        _FORECAST, columns=["ds", "yhat", "yhat_lower", "yhat_upper"]
    )
    forecast_df["ds"] = pd.to_datetime(forecast_df["ds"])

    fig = go.Figure()

    # ── Confidence band ──────────────────────────────────────────────────────
    band_x = pd.concat([forecast_df["ds"], forecast_df["ds"][::-1]])
    band_y = pd.concat([forecast_df["yhat_upper"], forecast_df["yhat_lower"][::-1]])
    fig.add_trace(go.Scatter(
        x=band_x, y=band_y,
        fill="toself",
        fillcolor="rgba(46,125,50,0.12)",
        line=dict(width=0),
        hoverinfo="skip",
        name="90% CI",
        showlegend=True,
    ))

    # ── Historical line ──────────────────────────────────────────────────────
    if history is not None and len(history):
        fig.add_trace(go.Scatter(
            x=history["ds"],
            y=history["y"],
            name="Historical exports",
            mode="lines",
            line=dict(color="#1B5E20", width=2.5),
            hovertemplate="%{x|%b %Y}<br><b>%{y:,.0f} MT</b><extra></extra>",
        ))

    # ── Forecast line ────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=forecast_df["ds"],
        y=forecast_df["yhat"],
        name="12-month forecast",
        mode="lines",
        line=dict(color="#4CAF50", width=2.5, dash="dash"),
        hovertemplate="%{x|%b %Y}<br><b>Forecast: %{y:,.0f} MT</b><extra></extra>",
    ))

    # ── Forecast/history boundary marker ────────────────────────────────────
    fig.add_shape(
        type="line",
        x0="2026-05-01", x1="2026-05-01",
        y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color="#AAAAAA", width=1, dash="dot"),
    )
    fig.add_annotation(
        x="2026-05-01", y=0.97,
        xref="x", yref="paper",
        text="Forecast →",
        showarrow=False,
        xanchor="left",
        font=dict(color="#888888", size=11),
    )

    fig.update_layout(
        height=340,
        margin=dict(t=20, b=10, l=10, r=10),
        hovermode="x unified",
        yaxis_title="Export Volume (MT)",
        yaxis=dict(tickformat=","),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            font=dict(size=12),
        ),
        xaxis=dict(showgrid=False),
        yaxis_showgrid=True,
        yaxis_gridcolor="#F0F0F0",
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── Summary stats below the chart ────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Forecast Accuracy", "91%", help="100% − MAPE (9.06%)")
    col2.metric("Next Month Forecast", "19,500 MT", help="May 2026 Prophet forecast")
    col3.metric("Peak Forecast", "26,200 MT", help="October 2026")
    col4.metric("Historical Data", "176 months", help="Oct 2011 – Apr 2026")


def _render_cta() -> None:
    st.write("")
    st.markdown("##### :material/rocket_launch: Ready to explore the dashboard?")

    _, login_col, register_col, _ = st.columns([2, 1, 1, 2])
    with login_col:
        if st.button(":material/login: Login", use_container_width=True):
            auth.goto("login")
            st.rerun()
    with register_col:
        if st.button(
            ":material/person_add: Register",
            use_container_width=True,
            type="primary",
        ):
            auth.goto("register")
            st.rerun()


def render() -> None:
    _render_hero()
    st.divider()
    _render_forecast_preview()
    st.divider()
    _render_features()
    st.divider()
    _render_cta()
    st.write("")
    st.caption(
        "A BSc (Hons) Software Engineering dissertation prototype · "
        "Cardiff Metropolitan University"
    )
