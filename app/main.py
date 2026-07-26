"""
BloxLogicAI — Streamlit app entry point + router.

Run from the project root:  streamlit run app/main.py

A ``st.session_state`` router gates the app: unauthenticated visitors see the
landing / login / register pages; authenticated users see the protected
dashboard. Auth logic lives in ``app/auth.py``; each screen is a ``render()``
in ``app/views/``.
"""

from __future__ import annotations

import os
import sys

import streamlit as st

# make the project root importable so `app.*`, `models.*`, `utils.*` resolve
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import auth                                    # noqa: E402
from app.views import landing, login, register  # noqa: E402

st.set_page_config(page_title="BloxLogicAI — Tea Supply-Chain Intelligence",
                   page_icon="🍃", layout="wide")

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

    # --- Sidebar: identity + navigation + sign out ---
    st.sidebar.title("🍃 BloxLogicAI")
    st.sidebar.caption("Sri Lanka tea supply-chain intelligence")
    st.sidebar.markdown(
        f"**Signed in as** {user['username']}  \n"
        f"_Role: {user['role']}_"
    )
    if st.sidebar.button("🚪 Sign out", use_container_width=True):
        auth.logout_user()
        st.rerun()
    st.sidebar.divider()

    # Only the forecast page exists today; anomaly / blockchain / admin
    # views plug in here in later phases. Imported lazily so the public
    # landing/login path never pays the Prophet/cmdstanpy import cost.
    from app.views import forecast  # noqa: E402
    forecast.render()
