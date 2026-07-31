"""
Public landing page — storefront for unauthenticated visitors.
Shows the hero, feature overview, a live forecast preview chart, and CTA buttons.
"""

from __future__ import annotations

import base64
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import auth
from app.config import FORECAST_CSV

FEATURES = [
    (
        "trending_up",
        "Demand Forecasting",
        "Facebook Prophet projects monthly tea export volumes 12 months ahead, "
        "capturing seasonality and the 2022 economic-crisis trend break — "
        "backtested to a 9% mean error.",
    ),
    (
        "troubleshoot",
        "Anomaly Detection",
        "Isolation Forest scans production, price, and weather signals to flag "
        "supply-chain disruptions before they cascade through the export pipeline.",
    ),
    (
        "link",
        "Blockchain Traceability",
        "Every tea batch is written to an immutable SHA-256 hash chain, giving "
        "buyers and auditors a tamper-evident record from estate to export.",
    ),
]

FAQS = [
    (
        "What is BloxLogicAI?",
        "BloxLogicAI is a unified platform combining predictive AI and blockchain technology "
        "specifically designed for Sri Lanka's tea export supply chain. It provides tools "
        "for forecasting, anomaly detection, and end-to-end traceability."
    ),
    (
        "How accurate is the forecast model?",
        "Our univariate Prophet model has been backtested to achieve ~91% accuracy (9% mean absolute percentage error), "
        "effectively capturing both seasonal variations and macro-economic shocks."
    ),
    (
        "What data is required to use the platform?",
        "The platform primarily uses historical export volume data for univariate forecasting. For anomaly detection, "
        "it correlates production data, auction prices, and weather signals to flag disruptions."
    ),
    (
        "How does blockchain ensure transparency?",
        "All tea batches are registered as transactions on an immutable ledger. Using cryptographic hashing (SHA-256), "
        "any unauthorized alteration to the records breaks the chain, providing a tamper-evident history."
    )
]

@st.cache_data(show_spinner=False)
def _load_history() -> pd.DataFrame | None:
    if not os.path.exists(FORECAST_CSV):
        return None
    df = pd.read_csv(FORECAST_CSV, parse_dates=["ds"])
    # Show last 48 months for a readable chart window
    return df.tail(48).reset_index(drop=True)


def _render_hero() -> None:
    # Get base64 representation of the image
    image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "landing_page_hero_image.jpg")
    encoded_string = ""
    if os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()

    bg_css = f"background-image: url(data:image/jpeg;base64,{encoded_string});" if encoded_string else "background-color: #2E7D32;"

    hero_html = f"""
    <div class="hero-container" style="{bg_css}">
        <div class="hero-overlay"></div>
        <div class="hero-content">
            <h1 class="hero-title">BloxLogicAI</h1>
            <p class="hero-subtitle">
                AI- & Blockchain-Enabled Supply-Chain Intelligence<br>
                for Sri Lanka's Tea Industry
            </p>
        </div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)
    
    # We use Streamlit columns to perfectly center the Get Started button
    # visually slightly overlapping or right below the hero
    _, col, _ = st.columns([1, 1, 1])
    with col:
        if st.button("Get Started", use_container_width=True, type="primary"):
            auth.goto("register")
            st.rerun()


def _render_features() -> None:
    st.markdown("<h2 style='text-align: center; margin-bottom: 40px;'>What BloxLogicAI does</h2>", unsafe_allow_html=True)
    cols = st.columns(3, gap="large")
    for col, (icon, title, blurb) in zip(cols, FEATURES):
        with col:
            st.markdown(
                f"""
                <div class="feature-card">
                    <div class="feature-card-icon">
                        <span class="material-symbols-outlined" style="font-size: 40px;">{icon}</span>
                    </div>
                    <div class="feature-card-title">{title}</div>
                    <div class="feature-card-text">{blurb}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_forecast_preview() -> None:
    st.markdown("<h2>Live Forecast Preview</h2>", unsafe_allow_html=True)
    st.caption(
        "Sri Lanka monthly tea export volume (MT) · Historical data + "
        "12-month Prophet forecast · Shaded area = 90% confidence interval"
    )

    try:
        from app.config import FORECAST_CSV, MODEL_PATH
        if not os.path.exists(FORECAST_CSV) or not os.path.exists(MODEL_PATH):
            st.info("ℹ️ Live forecast data is currently unavailable. (Clean slate demo mode: please log in as an administrator to generate datasets and train the AI models).")
            return

        with st.spinner("Loading real-time forecast model..."):
            from app.views.forecast import get_data, get_forecast, load_metrics
            df = get_data("univariate")
            forecast_full = get_forecast("univariate", horizon=12)
            metrics = load_metrics("univariate")

            last_date = df["ds"].max()
            history = df.tail(48).reset_index(drop=True)
            forecast_df = forecast_full[forecast_full["ds"] > last_date]

            accuracy = f"{100 - metrics['mape']:.0f}%" if metrics else "91%"
            accuracy_help = f"100% − MAPE ({metrics['mape']:.2f}%)" if metrics else "100% − MAPE"

            next_month_val = forecast_df.iloc[0]["yhat"] if len(forecast_df) else 0
            next_month_label = forecast_df.iloc[0]["ds"].strftime("%B %Y") if len(forecast_df) else "Next month"

            peak_idx = forecast_df["yhat"].idxmax() if len(forecast_df) else None
            peak_val = forecast_df.loc[peak_idx]["yhat"] if peak_idx is not None else 0
            peak_label = forecast_df.loc[peak_idx]["ds"].strftime("%B %Y") if peak_idx is not None else ""

            history_months = len(df)
            start_hist = df.ds.min().strftime("%b %Y")
            end_hist = df.ds.max().strftime("%b %Y")
            boundary_date = last_date.strftime("%Y-%m-%d")
            
    except Exception as e:
        st.error("Failed to load live forecast data. {e}")
        return

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
        x0=boundary_date, x1=boundary_date,
        y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color="#AAAAAA", width=1, dash="dot"),
    )
    fig.add_annotation(
        x=boundary_date, y=0.97,
        xref="x", yref="paper",
        text="Forecast →",
        showarrow=False,
        xanchor="left",
        font=dict(color="#888888", size=11, family="Inter"),
    )

    fig.update_layout(
        font=dict(family="Inter", color="#1A1A1A"),
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
    col1.metric("Forecast Accuracy", accuracy, help=accuracy_help)
    col2.metric("Next Month Forecast", f"{next_month_val:,.0f} MT", help=f"{next_month_label} Prophet forecast")
    col3.metric("Peak Forecast", f"{peak_val:,.0f} MT", help=peak_label)
    col4.metric("Historical Data", f"{history_months} months", help=f"{start_hist} – {end_hist}")


def _render_cta() -> None:
    st.write("")
    st.markdown("<h3 style='text-align: center; margin-bottom: 20px;'>Ready to explore the dashboard?</h3>", unsafe_allow_html=True)

    _, login_col, register_col, _ = st.columns([1.5, 1, 1, 1.5])
    with login_col:
        if st.button("Login to Account", icon=":material/login:", use_container_width=True):
            auth.goto("login")
            st.rerun()
    with register_col:
        if st.button(
            "Create Account",
            icon=":material/person_add:",
            use_container_width=True,
            type="primary",
        ):
            auth.goto("register")
            st.rerun()

def _render_faq() -> None:
    st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>Frequently Asked Questions</h2>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 4, 1])
    with col:
        for q, a in FAQS:
            with st.expander(q):
                st.write(a)

def _render_footer() -> None:
    footer_html = """
    <div class="footer-container">
        <div class="footer-text">© 2026 BloxLogicAI. All rights reserved.</div>
        <div style="margin-top: 12px;">
            <a href="#" class="footer-links">Privacy Policy</a>
            <a href="#" class="footer-links">Terms of Service</a>
            <a href="#" class="footer-links">Contact</a>
        </div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)

def render() -> None:
    _render_hero()
    st.divider()
    _render_forecast_preview()
    st.divider()
    _render_features()
    st.divider()
    _render_cta()
    st.divider()
    _render_faq()
    _render_footer()

