"""Registration (sign-up) view. Self-signup always creates a regular user."""

from __future__ import annotations

import streamlit as st

from app import auth


def render() -> None:
    # Use 3 columns to center the content. The middle column gets the form.
    _, col, _ = st.columns([1, 1, 1])
    
    with col:
        st.title(":material/person_add: Sign Up")

        with st.form("register_form"):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", type="primary",
                                              use_container_width=True)

        if submitted:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, msg = auth.add_user(username, email, password, role="user")
                if ok:
                    st.success(msg)
                    auth.goto("login")
                    st.rerun()
                else:
                    st.error(msg)

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button(":material/arrow_back: Back to home", use_container_width=True):
                auth.goto("landing")
                st.rerun()
        with c2:
            if st.button("Login", use_container_width=True):
                auth.goto("login")
                st.rerun()
