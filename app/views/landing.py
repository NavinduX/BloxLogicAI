"""Public landing page — the storefront for unauthenticated visitors.

A premium, image-led introduction to BloxLogicAI built entirely from
Streamlit's native layout primitives (no custom HTML/CSS). Icons use
Streamlit's Material Symbol syntax (``:material/<name>:``) rather than emojis.
"""

from __future__ import annotations

import os

import streamlit as st

from app import auth

# Thin hero banner ships with the repo so the dashboard renders fully offline.
HERO_IMAGE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "tea_banner.jpg",
)

# The three product pillars: (icon, title, blurb).
FEATURES = [
    (
        ":material/trending_up:",
        "Demand Forecasting",
        "A Facebook Prophet model projects monthly tea export volumes 12 "
        "months ahead, capturing seasonality and the 2022 economic-crisis "
        "trend break — backtested to a 9% mean error.",
    ),
    (
        ":material/troubleshoot:",
        "Anomaly Detection",
        "An Isolation Forest scans production, price and weather signals to "
        "flag supply-chain disruptions early, before they cascade through "
        "the export pipeline.",
    ),
    (
        ":material/link:",
        "Blockchain Traceability",
        "Every tea batch is written to an immutable SHA-256 hash chain, "
        "giving buyers and auditors a tamper-evident record from estate to "
        "export.",
    ),
]


def _render_hero() -> None:
    """Full-width plantation image plus the headline value proposition."""
    # st.image(HERO_IMAGE, use_container_width=True)

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
    """Three-column overview of the platform's core capabilities."""
    st.header(":material/analytics: What BloxLogicAI does")

    for column, (icon, title, blurb) in zip(st.columns(3, gap="large"), FEATURES):
        with column:
            st.subheader(f"{icon} {title}")
            st.write(blurb)


def _render_cta() -> None:
    """Centered Login / Register call-to-action buttons."""
    st.write("")
    st.markdown(
        "##### :material/rocket_launch: Ready to explore the dashboard?"
    )

    # Empty side columns pin the two buttons to the middle of the page.
    _, login_col, register_col, _ = st.columns([2, 1, 1, 2])

    with login_col:
        if st.button(
            ":material/login: Login",
            use_container_width=True,
        ):
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
    _render_features()
    st.divider()
    _render_cta()

    st.write("")
    st.caption(
        "A BSc (Hons) Software Engineering dissertation prototype · "
        "Cardiff Metropolitan University"
    )
