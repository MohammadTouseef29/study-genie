import base64
import os

import requests
import streamlit as st
from ui import apply_theme, chip_row, hero, section_title

API_BASE_URL = os.getenv("STUDY_GENIE_API_URL", "http://localhost:8000")

apply_theme("Automated Attendance Studio")
hero(
    "Automated Attendance Studio",
    "Enroll student faces once, then mark classroom attendance automatically from a single group photo.",
    eyebrow="Face Recognition",
    chips=["Face Enrollment", "Group Photo Matching", "Session History", "API Backed"],
)


def _error_detail(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return "Could not reach the backend API."
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text or f"Request failed with status {response.status_code}."


def enroll_student(student_id: str, name: str, uploaded_file) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/attendance/enroll",
        data={"student_id": student_id, "name": name},
        files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "image/jpeg")},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def get_roster() -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/attendance/roster", timeout=30)
    response.raise_for_status()
    return response.json()["roster"]


def delete_student(student_id: str) -> None:
    response = requests.delete(f"{API_BASE_URL}/attendance/roster/{student_id}", timeout=30)
    response.raise_for_status()


def mark_attendance(course_id: str, course_name: str, session_label: str, session_date: str, uploaded_file) -> dict:
    response = requests.post(
        f"{API_BASE_URL}/attendance/mark",
        data={
            "course_id": course_id,
            "course_name": course_name,
            "session_label": session_label,
            "session_date": session_date,
        },
        files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type or "image/jpeg")},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def get_history(course_id: str | None = None) -> list[dict]:
    params = {"course_id": course_id} if course_id else None
    response = requests.get(f"{API_BASE_URL}/attendance/history", params=params, timeout=30)
    response.raise_for_status()
    return response.json()["sessions"]


def get_session_detail(session_id: str) -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/attendance/history/{session_id}", timeout=30)
    response.raise_for_status()
    return response.json()["records"]


enroll_tab, mark_tab, roster_tab = st.tabs(["Enroll Student", "Mark Attendance", "Roster & History"])

with enroll_tab:
    section_title("Enroll a Student Face", "Upload one clear, front-facing photo per student to register them for recognition.")

    with st.container(border=True):
        enroll_col1, enroll_col2 = st.columns(2)
        with enroll_col1:
            enroll_student_id = st.text_input("Student ID", key="enroll_student_id")
        with enroll_col2:
            enroll_name = st.text_input("Full Name", key="enroll_name")

        enroll_photo = st.file_uploader("Face photo", type=["jpg", "jpeg", "png"], key="enroll_photo")

        if st.button(
            "Enroll Student",
            use_container_width=True,
            disabled=not (enroll_student_id and enroll_name and enroll_photo),
            type="primary",
        ):
            try:
                result = enroll_student(enroll_student_id, enroll_name, enroll_photo)
                st.success(result["message"])
            except requests.RequestException as exc:
                st.error(f"Could not enroll student: {_error_detail(exc)}")

with mark_tab:
    section_title("Mark Attendance from a Group Photo", "Upload a classroom photo; every enrolled face detected in it is marked present.")

    with st.container(border=True):
        mark_col1, mark_col2, mark_col3 = st.columns(3)
        with mark_col1:
            mark_course_id = st.text_input("Course ID", value="CSE101", key="mark_course_id")
        with mark_col2:
            mark_course_name = st.text_input("Course Name", value="", key="mark_course_name")
        with mark_col3:
            mark_session_label = st.text_input("Session Label", value="Lecture", key="mark_session_label")

        mark_session_date = st.date_input("Session Date", key="mark_session_date")
        classroom_photo = st.file_uploader("Classroom photo", type=["jpg", "jpeg", "png"], key="classroom_photo")

        if st.button("Mark Attendance", use_container_width=True, disabled=not (mark_course_id and classroom_photo), type="primary"):
            try:
                st.session_state["attendance_result"] = mark_attendance(
                    mark_course_id,
                    mark_course_name,
                    mark_session_label,
                    mark_session_date.isoformat(),
                    classroom_photo,
                )
            except requests.RequestException as exc:
                st.error(f"Could not mark attendance: {_error_detail(exc)}")

    attendance_result = st.session_state.get("attendance_result")
    if attendance_result:
        section_title("Session Result", f"Session {attendance_result['session_id']} · {attendance_result['session_label']} · {attendance_result['session_date']}")

        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        metric_col1.metric("Present", attendance_result["present_count"])
        metric_col2.metric("Absent", attendance_result["absent_count"])
        metric_col3.metric("Faces Detected", attendance_result["faces_detected"])
        metric_col4.metric("Unrecognized Faces", attendance_result["unmatched_face_count"])

        image_bytes = base64.b64decode(attendance_result["annotated_image_base64"])
        st.image(image_bytes, caption="Green = recognized and marked present, red = unrecognized face", use_container_width=True)

        present_col, absent_col = st.columns(2)
        with present_col:
            st.markdown("**Present**")
            if attendance_result["present"]:
                st.dataframe(attendance_result["present"], use_container_width=True, hide_index=True)
            else:
                st.caption("No enrolled students were recognized in this photo.")
        with absent_col:
            st.markdown("**Absent**")
            if attendance_result["absent"]:
                st.dataframe(attendance_result["absent"], use_container_width=True, hide_index=True)
            else:
                st.caption("Every enrolled student was recognized.")

with roster_tab:
    section_title("Enrolled Roster", "Students currently registered for face-recognition attendance.")

    try:
        roster = get_roster()
    except requests.RequestException as exc:
        roster = []
        st.error(f"Could not load roster: {_error_detail(exc)}")

    if not roster:
        st.caption("No students enrolled yet. Use the Enroll Student tab to get started.")
    else:
        chip_row([f"{len(roster)} students enrolled"])
        for entry in roster:
            with st.container(border=True):
                photo_col, info_col, action_col = st.columns([1, 3, 1])
                with photo_col:
                    st.image(f"{API_BASE_URL}/attendance/roster/{entry['student_id']}/photo", width=80)
                with info_col:
                    st.markdown(f"**{entry['name']}**")
                    st.caption(f"ID: {entry['student_id']} · Enrolled: {entry['enrolled_at'][:10]}")
                with action_col:
                    if st.button("Remove", key=f"remove_{entry['student_id']}"):
                        try:
                            delete_student(entry["student_id"])
                            st.rerun()
                        except requests.RequestException as exc:
                            st.error(f"Could not remove student: {_error_detail(exc)}")

    section_title("Attendance History", "Past sessions recorded through automated face-recognition attendance.")
    try:
        history = get_history()
    except requests.RequestException as exc:
        history = []
        st.error(f"Could not load history: {_error_detail(exc)}")

    if not history:
        st.caption("No attendance sessions recorded yet.")
    else:
        st.dataframe(history, use_container_width=True, hide_index=True)

        session_labels = [f"{item['session_id']} · {item['course_id']} · {item['session_label']} · {item['session_date']}" for item in history]
        selected = st.selectbox("View session detail", session_labels)
        if selected:
            selected_session_id = selected.split(" · ")[0]
            try:
                detail = get_session_detail(selected_session_id)
                st.dataframe(detail, use_container_width=True, hide_index=True)
            except requests.RequestException as exc:
                st.error(f"Could not load session detail: {_error_detail(exc)}")
