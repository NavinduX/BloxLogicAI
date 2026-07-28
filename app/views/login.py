"""Login view."""

from __future__ import annotations

import streamlit as st

from app import auth


def render() -> None:
    # Use 3 columns to center the content. The middle column gets the form.
    _, col, _ = st.columns([1, 1, 1])
    
    with col:
        st.title(":material/login: Login")

        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary",
                                              use_container_width=True)

        if submitted:
            record = auth.authenticate(username, password)
            if record:
                auth.login_user(record)
                st.rerun()
            else:
                st.error("Invalid username or password.")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button(":material/arrow_back: Back to home", use_container_width=True):
                auth.goto("landing")
                st.rerun()
        with c2:
            if st.button("Create an account", use_container_width=True):
                auth.goto("register")
                st.rerun()
