"""
Analytics view — forecast model performance metrics and export trend chart.
"""

from __future__ import annotations

import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.config import FORECAST_CSV, METRICS_PATH
from app.style import metric_card


def _load_metrics() -> dict | None:
    if os.path.exists(METRICS_PATH):
        with open(METRICS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def render() -> None:
    st.header("Analytics")
    st.caption(
        "Forecast model performance and historical export volume trends "
        "for Sri Lanka's tea industry."
    )

    metrics = _load_metrics()

    # ── Model performance ─────────────────────────────────────────────────
    st.subheader("Forecast Model Performance")
    st.caption("Prophet univariate — backtested on last 12 months (May 2025 – Apr 2026)")

    c1, c2, c3, c4 = st.columns(4)
    if metrics:
        with c1:
            metric_card("MAPE", f"{metrics['mape']:.2f}%", note="Target < 15%")
        with c2:
            metric_card("MAE", f"{metrics['mae']:,.0f} MT", note="Mean Absolute Error")
        with c3:
            metric_card("RMSE", f"{metrics['rmse']:,.0f} MT", note="Root Mean Sq Error")
        with c4:
            accuracy = max(0.0, 100 - metrics["mape"])
            metric_card("Accuracy", f"{accuracy:.1f}%", note="100% − MAPE")
    else:
        st.warning("No metrics file found. Train the model from Model Management first.")

    st.divider()

    # ── Export trend chart ────────────────────────────────────────────────
    st.subheader("Tea Export Volume — Historical Trend")
    st.caption("Monthly Sri Lanka tea export volume (metric tonnes), Oct 2011 – Apr 2026")

    if not os.path.exists(FORECAST_CSV):
        st.warning("Forecast dataset not found.")
        return

    df = pd.read_csv(FORECAST_CSV, parse_dates=["ds"])

    # Try to load forecast from cached model
    forecast_df: pd.DataFrame | None = None
    try:
        from app.views.forecast import get_data, get_model, get_forecast
        fc_df    = get_data("univariate")
        fc_model = get_model(fc_df, "univariate")
        forecast_df = get_forecast("univariate", 12)
    except Exception:
        pass

    fig = go.Figure()

    imputed = df["y_imputed"].astype(bool) if "y_imputed" in df.columns else pd.Series([False] * len(df))
    actual  = df[~imputed]
    interp  = df[imputed]

    # Actual line
    fig.add_trace(go.Scatter(
        x=actual["ds"], y=actual["y"],
        name="Actual exports",
        mode="lines",
        line=dict(color="#1B5E20", width=2.5),
    ))
    # Interpolated markers
    if len(interp):
        fig.add_trace(go.Scatter(
            x=interp["ds"], y=interp["y"],
            name="Interpolated",
            mode="markers",
            marker=dict(color="#F9A825", size=8, symbol="circle-open", line=dict(width=2)),
        ))
    # Forecast
    if forecast_df is not None:
        future = forecast_df[forecast_df["ds"] > df["ds"].max()]
        if len(future):
            fig.add_trace(go.Scatter(
                x=pd.concat([future["ds"], future["ds"][::-1]]),
                y=pd.concat([future["yhat_upper"], future["yhat_lower"][::-1]]),
                fill="toself", fillcolor="rgba(46,125,50,0.10)",
                line=dict(width=0), hoverinfo="skip", name="90% CI",
            ))
            fig.add_trace(go.Scatter(
                x=future["ds"], y=future["yhat"],
                name="12-month forecast",
                mode="lines",
                line=dict(color="#4CAF50", width=2.5, dash="dash"),
            ))

    # Event annotations
    safe_annots = []
    for target_ym, text in [("2020-04", "COVID-19"), ("2022-04", "Econ. Crisis")]:
        match = df[df["ds"].dt.strftime("%Y-%m") == target_ym]
        if not match.empty:
            safe_annots.append(dict(
                x=match.iloc[0]["ds"], y=float(match.iloc[0]["y"]),
                text=text, showarrow=True, arrowhead=2,
                font=dict(size=11, color="#C62828"),
                arrowcolor="#C62828", ax=0, ay=-45,
            ))

    fig.update_layout(
        height=460,
        hovermode="x unified",
        margin=dict(t=30, b=10, l=10, r=10),
        yaxis_title="Export Volume (MT)",
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#F8FBF8",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        annotations=safe_annots,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Year-on-year table ────────────────────────────────────────────────
    st.subheader("Year-on-Year Summary")
    df["year"] = df["ds"].dt.year
    yearly = (
        df.groupby("year")["y"]
        .agg(["sum", "mean", "min", "max"])
        .reset_index()
        .rename(columns={
            "year": "Year",
            "sum":  "Total (MT)",
            "mean": "Avg / Month (MT)",
            "min":  "Min Month (MT)",
            "max":  "Max Month (MT)",
        })
    )
    for col in ["Total (MT)", "Avg / Month (MT)", "Min Month (MT)", "Max Month (MT)"]:
        yearly[col] = yearly[col].round(0).astype(int)
    st.dataframe(yearly, use_container_width=True, hide_index=True)

    with st.expander("Model details"):
        st.markdown(
            "**Algorithm:** Facebook Prophet (univariate)  \n"
            "**Seasonality:** yearly multiplicative, weekly/daily off  \n"
            "**Changepoint scale:** 0.5 (captures 2022 economic crisis break)  \n"
            "**Training data:** 176 months (Oct 2011 – Apr 2026)  \n"
            "**Backtest:** last 12 months held out as test set"
        )
