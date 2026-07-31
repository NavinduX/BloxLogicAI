"""Registration (sign-up) view. Self-signup always creates a regular user."""

from __future__ import annotations

import base64
import os
import streamlit as st

from app import auth


def render() -> None:
    # Use 2 columns to split the page: half for the image, half for the form.
    # Vertically center the contents.
    col1, col2 = st.columns([1, 1], gap="large", vertical_alignment="center")
    
    with col1:
        image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "signup_login_page_image.jpg")
        if os.path.exists(image_path):
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<img src="data:image/jpeg;base64,{encoded}" style="max-height: 65vh; width: 100%; object-fit: cover; border-radius: 16px;">',
                unsafe_allow_html=True
            )
        else:
            st.info("Image not found.")
            
    with col2:
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
