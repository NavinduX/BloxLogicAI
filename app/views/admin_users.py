"""
Admin — User Management: view, add, remove, and reset-password for accounts.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import auth


def _remove_user(username: str) -> tuple[bool, str]:
    return auth.remove_user(username)


def _reset_password(username: str, new_password: str) -> tuple[bool, str]:
    return auth.update_password(username, new_password)


def render() -> None:
    st.header("User Management")
    st.caption("Manage user accounts, roles, and credentials.")

    # ── User table ────────────────────────────────────────────────────────────
    st.subheader("Registered Users")
    df = auth.load_users()
    display = df[["username", "email", "role", "created_at"]].rename(columns={
        "username":   "Username",
        "email":      "Email",
        "role":       "Role",
        "created_at": "Created At",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()

    # ── Action tabs ───────────────────────────────────────────────────────────
    tab_add, tab_remove, tab_reset = st.tabs(["Add User", "Remove User", "Reset Password"])

    # Add user
    with tab_add:
        with st.form("add_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_email    = st.text_input("Email")
            with col2:
                new_password = st.text_input("Password", type="password")
                new_role     = st.selectbox("Role", ["user", "admin"])
            submitted = st.form_submit_button("Add User", use_container_width=True)

        if submitted:
            ok, msg = auth.add_user(new_username, new_email, new_password, role=new_role)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    # Remove user
    with tab_remove:
        st.warning("Removing a user is permanent. Admin accounts are protected.")
        with st.form("remove_user_form", clear_on_submit=True):
            rm_username  = st.text_input("Username to remove")
            confirmed    = st.checkbox("I confirm this action is irreversible")
            rm_submitted = st.form_submit_button("Remove User", use_container_width=True)

        if rm_submitted:
            if not confirmed:
                st.error("Please confirm the action by checking the box above.")
            else:
                ok, msg = _remove_user(rm_username)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # Reset password
    with tab_reset:
        with st.form("reset_pw_form", clear_on_submit=True):
            rp_username = st.text_input("Username")
            new_pw      = st.text_input("New password", type="password")
            confirm_pw  = st.text_input("Confirm password", type="password")
            rp_submitted = st.form_submit_button("Reset Password", use_container_width=True)

        if rp_submitted:
            if new_pw != confirm_pw:
                st.error("Passwords do not match.")
            else:
                ok, msg = _reset_password(rp_username, new_pw)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
