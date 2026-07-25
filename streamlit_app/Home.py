import os

import streamlit as st

try:
    for key, value in st.secrets.items():
        os.environ.setdefault(key, str(value))
except Exception:
    pass

home_page = st.Page("home_page.py", title="Home", icon=":material/home:")
doubt_solver = st.Page("pages/0_Doubt_Solver_API.py", title="AI Doubt Solver", icon=":material/chat:")
transcription = st.Page("pages/10_Lecture_Transcription.py", title="Lecture Transcription Studio", icon=":material/mic:")
study_materials = st.Page("pages/11_Flashcards_And_Quiz.py", title="Flashcards and Quiz Generator", icon=":material/quiz:")
attendance = st.Page("pages/12_Attendance_Studio.py", title="Attendance Studio", icon=":material/face:")
study_plan = st.Page("pages/13_Study_Plan.py", title="Personalized Study Plan", icon=":material/event_available:")
login_page = st.Page("pages/14_Login.py", title="Log In / Sign Up", icon=":material/login:")
profile_page = st.Page("pages/15_Profile.py", title="Profile", icon=":material/account_circle:")

navigation = st.navigation(
    {
        "Workspace": [home_page, doubt_solver, transcription, study_materials, attendance, study_plan],
        "Account": [login_page, profile_page],
    }
)

navigation.run()
