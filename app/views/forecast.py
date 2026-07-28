"""
Forecast dashboard view — Module 1 (tea export volume, Prophet).

The dashboard body lives in :func:`render`, called by the router once a user is
authenticated. ``st.set_page_config`` is owned by ``app/main.py``, not this module.
"""

from __future__ import annotations

import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from prophet import Prophet

from models import forecasting as fc
from utils import data_loader


# ---------------------------------------------------------------------------
# Cached data / model helpers
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def get_data(model_type: str = "univariate") -> pd.DataFrame:
    """Forecast dataset (ds, y); build it from sources if not yet generated."""
    if model_type == "univariate":
        path = fc.DATA
        builder = data_loader.build_forecast_dataset
    else:
        path = fc.MV_DATA
        builder = data_loader.build_multivariate_dataset

    if not os.path.exists(path):
        df = builder()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)
    df = pd.read_csv(path, parse_dates=["ds"])
    if "y_imputed" in df.columns:
        df["y_imputed"] = df["y_imputed"].astype(bool)
    return df


@st.cache_resource(show_spinner="Training Prophet model…")
def get_model(_df: pd.DataFrame, model_type: str = "univariate") -> Prophet:
    """Load the saved model, or train + save one if missing."""
    if model_type == "univariate":
        if os.path.exists(fc.MODEL_PATH):
            return fc.load_model(fc.MODEL_PATH)
        model = fc.train_model(_df[["ds", "y"]])
        fc.save_model(model, fc.MODEL_PATH)
        return model
    else:
        if os.path.exists(fc.MV_MODEL_PATH):
            return fc.load_model(fc.MV_MODEL_PATH)
        model = fc.train_model(_df, regressors=fc.MV_REGRESSORS)
        fc.save_model(model, fc.MV_MODEL_PATH)
        return model


@st.cache_data(show_spinner=False)
def load_metrics(model_type: str = "univariate") -> dict | None:
    path = fc.METRICS_PATH if model_type == "univariate" else fc.MV_METRICS_PATH
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return None


@st.cache_data(show_spinner="Computing forecast…")
def get_forecast(model_type: str, horizon: int) -> pd.DataFrame:
    """Return the full forecast DataFrame (history + future), cached by model_type + horizon."""
    df = get_data(model_type)
    model = get_model(df, model_type)
    if model_type == "univariate":
        return fc.predict(model, periods=horizon)
    return fc.predict_multivariate(
        model, df, regressors=fc.MV_REGRESSORS, periods=horizon
    )


def retrain(df: pd.DataFrame, model_type: str = "univariate") -> dict:
    """Force a fresh fit + backtest, refresh caches, persist artifacts."""
    if model_type == "univariate":
        metrics = fc.evaluate(df[["ds", "y"]], test_periods=12)
        model = fc.train_model(df[["ds", "y"]])
        fc.save_model(model, fc.MODEL_PATH)
        os.makedirs(fc.SAVED, exist_ok=True)
        with open(fc.METRICS_PATH, "w") as fh:
            json.dump(metrics, fh, indent=2)
    else:
        metrics = fc.evaluate(df, test_periods=12, regressors=fc.MV_REGRESSORS, future="forecast")
        model = fc.train_model(df, regressors=fc.MV_REGRESSORS)
        fc.save_model(model, fc.MV_MODEL_PATH)
        os.makedirs(fc.SAVED, exist_ok=True)
        with open(fc.MV_METRICS_PATH, "w") as fh:
            json.dump(metrics, fh, indent=2)
    get_model.clear()
    get_forecast.clear()
    load_metrics.clear()
    return metrics


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
def render() -> None:
    """Render the tea export forecast dashboard."""
    st.sidebar.header("Forecast settings")
    model_type = st.sidebar.radio("Model Type", ["univariate", "multivariate"], 
                                  format_func=lambda x: x.capitalize())
    horizon = st.sidebar.slider("Forecast horizon (months)", 3, 24, 12)
    show_band = st.sidebar.checkbox("Show confidence interval", value=True)
    show_imputed = st.sidebar.checkbox("Mark interpolated months", value=True)

    df = get_data(model_type)

    if st.sidebar.button("🔄 Retrain model", use_container_width=True):
        with st.spinner(f"Retraining {model_type} model and backtesting…"):
            retrain(df, model_type)
        st.sidebar.success(f"{model_type.capitalize()} model retrained.")

    metrics = load_metrics(model_type)
    forecast = get_forecast(model_type, horizon)

    # -----------------------------------------------------------------------
    # Header + KPIs
    # -----------------------------------------------------------------------
    st.title("Tea Export Volume Forecast")
    st.caption(f"Monthly Sri Lanka tea export volume (MT) — Prophet, {model_type} "
               f"({df.ds.min():%b %Y} → {df.ds.max():%b %Y}, {len(df)} months).")
    future = forecast[forecast["ds"] > df["ds"].max()]

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    delta_pct = (latest.y - prev.y) / prev.y * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Latest export ({latest.ds:%b %Y})",
              f"{latest.y:,.0f} MT", f"{delta_pct:+.1f}% MoM")
    c2.metric("Next-month forecast",
              f"{future.iloc[0].yhat:,.0f} MT" if len(future) else "—")
    if metrics:
        c3.metric("Backtest MAPE", f"{metrics['mape']:.1f}%")
        c4.metric("Backtest MAE", f"{metrics['mae']:,.0f} MT")
    else:
        c3.metric("Backtest MAPE", "—")
        c4.metric("Backtest MAE", "—")

    # -----------------------------------------------------------------------
    # Chart
    # -----------------------------------------------------------------------
    fig = go.Figure()

    if show_band:
        fig.add_trace(go.Scatter(
            x=list(future.ds) + list(future.ds[::-1]),
            y=list(future.yhat_upper) + list(future.yhat_lower[::-1]),
            fill="toself", fillcolor="rgba(0,150,80,0.15)",
            line=dict(width=0), hoverinfo="skip", name="Confidence interval"))

    fig.add_trace(go.Scatter(x=df.ds, y=df.y, mode="lines",
                             name="Actual", line=dict(color="#1f3b2d", width=2)))

    fig.add_trace(go.Scatter(x=future.ds, y=future.yhat, mode="lines",
                             name="Forecast",
                             line=dict(color="#2e9e5b", width=2, dash="dash")))

    if show_imputed and "y_imputed" in df.columns:
        imp = df[df["y_imputed"]]
        if len(imp):
            fig.add_trace(go.Scatter(x=imp.ds, y=imp.y, mode="markers",
                                     name="Interpolated",
                                     marker=dict(color="#d98e04", size=7,
                                                 symbol="circle-open")))

    fig.update_layout(height=460, hovermode="x unified",
                      margin=dict(t=30, b=10, l=10, r=10),
                      yaxis_title="Export volume (MT)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------------------------
    # Forecast table + download
    # -----------------------------------------------------------------------
    left, right = st.columns([2, 1])

    with left:
        st.subheader(f"Forecast — next {horizon} months")
        table = future.rename(columns={
            "ds": "Month", "yhat": "Forecast (MT)",
            "yhat_lower": "Lower", "yhat_upper": "Upper"}).copy()
        table["Month"] = table["Month"].dt.strftime("%Y-%m")
        for c in ["Forecast (MT)", "Lower", "Upper"]:
            table[c] = table[c].round(0).astype(int)
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download forecast (CSV)",
                           table.to_csv(index=False).encode(),
                           file_name="tea_export_forecast.csv", mime="text/csv")

    with right:
        st.subheader("Model")
        algo_text = "Prophet (univariate)" if model_type == "univariate" else "Prophet (multivariate)"
        st.markdown(
            f"- **Algorithm:** {algo_text}\n"
            f"- **Seasonality:** {fc.DEFAULT_PARAMS['seasonality_mode']}\n"
            f"- **Changepoint scale:** {fc.DEFAULT_PARAMS['changepoint_prior_scale']}\n"
            f"- **Training span:** {df.ds.min():%Y-%m} → {df.ds.max():%Y-%m}"
        )
        if model_type == "multivariate":
            st.markdown(f"- **Regressors:** {', '.join(fc.MV_REGRESSORS)}")
        if metrics:
            st.caption(f"Backtested on the last {metrics['test_periods']} months "
                       f"({metrics['test_start']} → {metrics['test_end']}).")
        if "y_imputed" in df.columns:
            n_imp = int(df["y_imputed"].sum())
            st.caption(f"{n_imp} of {len(df)} months were interpolated from "
                       "missing source records.")
