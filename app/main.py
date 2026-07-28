"""
BloxLogicAI — Streamlit app entry point + router.

Run from the project root:  streamlit run app/main.py

Unauthenticated visitors see landing / login / register.
Authenticated users are routed by role:
  - user  → Dashboard, Forecasting, Anomaly Detection, Blockchain Traceability
  - admin → Dashboard, Dataset Management, Model Management,
             Blockchain Ledger, User Management, Analytics
"""

from __future__ import annotations

import os
import sys

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import auth                                    # noqa: E402
from app.views import landing, login, register          # noqa: E402
from app.style import inject_theme                      # noqa: E402

st.set_page_config(
    page_title="BloxLogicAI — Tea Supply-Chain Intelligence",
    page_icon="🍃",
    layout="wide",
)

inject_theme()
auth.init_session()

PUBLIC_PAGES = {"landing": landing, "login": login, "register": register}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if not auth.is_authenticated():
    page = st.session_state.page
    if page not in PUBLIC_PAGES:
        page = "landing"
    PUBLIC_PAGES[page].render()

else:
    user = auth.current_user()
    role = user["role"]

    # ── Sidebar: brand + identity + sign out ────────────────────────────────
    st.sidebar.title("BloxLogicAI")
    st.sidebar.caption("Sri Lanka Tea Supply-Chain Intelligence")
    st.sidebar.markdown(
        f"**{user['username']}** &nbsp;·&nbsp; *{role}*",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Sign out", use_container_width=True):
        auth.logout_user()
        st.rerun()
    st.sidebar.divider()

    # ── Navigation menu (role-based) ────────────────────────────────────────
    if role == "admin":
        NAV = [
            "Dashboard",
            "Dataset Management",
            "Model Management",
            "Blockchain Ledger",
            "User Management",
            "Analytics",
        ]
    else:
        NAV = [
            "Dashboard",
            "Forecasting",
            "Anomaly Detection",
            "Blockchain Traceability",
        ]

    page = st.sidebar.radio("Menu", NAV, label_visibility="collapsed")

    # ── Page dispatch (lazy imports keep Prophet off the public-page path) ──
    if role == "admin":
        if page == "Dashboard":
            from app.views import admin_dashboard; admin_dashboard.render()
        elif page == "Dataset Management":
            from app.views import admin_dataset; admin_dataset.render()
        elif page == "Model Management":
            from app.views import admin_model; admin_model.render()
        elif page == "Blockchain Ledger":
            from app.views import admin_ledger; admin_ledger.render()
        elif page == "User Management":
            from app.views import admin_users; admin_users.render()
        elif page == "Analytics":
            from app.views import analytics; analytics.render()
    else:
        if page == "Dashboard":
            from app.views import user_dashboard; user_dashboard.render()
        elif page == "Forecasting":
            from app.views import forecast; forecast.render()
        elif page == "Anomaly Detection":
            from app.views import anomaly; anomaly.render()
        elif page == "Blockchain Traceability":
            from app.views import blockchain_trace; blockchain_trace.render()
