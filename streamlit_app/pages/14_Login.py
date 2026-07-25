import os

import requests
import streamlit as st
from ui import apply_theme, hero, section_title

API_BASE_URL = os.getenv("STUDY_GENIE_API_URL", "http://localhost:8000")

apply_theme("Log In")
hero(
    "Welcome to Study Genie",
    "Create an account to save your study materials, track quiz history, and unlock personalized study plans and risk insights.",
    eyebrow="Account",
    chips=["Email & Password", "Personal Activity", "Demo Risk Profile"],
)

if st.session_state.get("auth_user"):
    st.success(f"You're already logged in as {st.session_state['auth_user']['name']}.")
    if st.button("Go to Home", type="primary"):
        st.switch_page("home_page.py")
    st.stop()


def _error_detail(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return "Could not reach the backend API."
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text or f"Request failed with status {response.status_code}."


login_tab, signup_tab = st.tabs(["Log In", "Sign Up"])

with login_tab:
    with st.container(border=True):
        section_title("Log In", "Access your saved materials, quiz history, and personalized recommendations.")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Log In", use_container_width=True, type="primary", key="login_submit"):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/auth/login",
                    json={"email": login_email, "password": login_password},
                    timeout=30,
                )
                response.raise_for_status()
                st.session_state["auth_user"] = response.json()
                st.switch_page("home_page.py")
            except requests.RequestException as exc:
                st.error(_error_detail(exc))

with signup_tab:
    with st.container(border=True):
        section_title("Create an Account", "Takes a minute — used to personalize your study plan, risk profile, and activity history.")
        signup_name = st.text_input("Full Name", key="signup_name")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password", help="At least 8 characters.")
        signup_confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")

        if st.button("Create Account", use_container_width=True, type="primary", key="signup_submit"):
            if signup_password != signup_confirm:
                st.warning("Passwords do not match.")
            else:
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/auth/signup",
                        json={"email": signup_email, "password": signup_password, "name": signup_name},
                        timeout=30,
                    )
                    response.raise_for_status()
                    st.session_state["auth_user"] = response.json()
                    st.switch_page("home_page.py")
                except requests.RequestException as exc:
                    st.error(_error_detail(exc))

st.caption(
    "New accounts are linked to a stable demo classroom profile so risk scoring, study plans, and analytics "
    "work immediately. Saved materials, quiz attempts, and attendance are tracked against your real account."
)
