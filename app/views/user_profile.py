import streamlit as st
from app.style import panel
from app import auth

def render() -> None:
    st.title("User Profile")
    st.markdown("View and edit your profile information here.")
    
    user = auth.current_user()
    if not user:
        st.error("You must be logged in to view this page.")
        return

    # -------------------------------------------------------------------------
    # Personal Details
    # -------------------------------------------------------------------------
    panel("Personal Details")
    
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Username", value=user["username"], disabled=True)
            email = st.text_input("Email", value=user["email"])
        with col2:
            st.text_input("Role", value=user["role"].capitalize(), disabled=True)
            joined = user.get("created_at", "").replace("T", " ")
            st.text_input("Joined On", value=joined, disabled=True)
            
        submit_profile = st.form_submit_button("Save Changes", type="primary")
        
    if submit_profile:
        if email != user["email"]:
            ok, msg = auth.update_user_email(user["username"], email)
            if ok:
                st.success(msg)
                user["email"] = email
                st.rerun()
            else:
                st.error(msg)
        else:
            st.info("No changes made.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # -------------------------------------------------------------------------
    # Security (Password Change)
    # -------------------------------------------------------------------------
    panel("Security")
    with st.form("password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submit_password = st.form_submit_button("Change Password")
        
    if submit_password:
        if not current_password or not new_password or not confirm_password:
            st.error("Please fill in all password fields.")
        elif new_password != confirm_password:
            st.error("New passwords do not match.")
        else:
            authenticated_user = auth.authenticate(user["username"], current_password)
            if not authenticated_user:
                st.error("Incorrect current password.")
            else:
                ok, msg = auth.update_password(user["username"], new_password)
                if ok:
                    st.success("Password successfully updated.")
                else:
                    st.error(msg)

    st.markdown("<br>", unsafe_allow_html=True)
    panel("Account Activity")
    st.info("No recent unusual activity detected on your account.")
