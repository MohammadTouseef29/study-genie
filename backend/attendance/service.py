from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timezone

import face_recognition
import numpy as np
from PIL import Image, ImageDraw
from sqlalchemy import text

from backend.db import get_engine, get_supabase_client

PHOTOS_BUCKET = "attendance-photos"

MATCH_TOLERANCE = 0.5
THUMBNAIL_SIZE = (240, 240)


def _ensure_bucket() -> None:
    storage = get_supabase_client().storage
    existing = {bucket.name for bucket in storage.list_buckets()}
    if PHOTOS_BUCKET not in existing:
        storage.create_bucket(PHOTOS_BUCKET, options={"public": True})


def _image_from_bytes(image_bytes: bytes) -> np.ndarray:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return np.array(image)


def _largest_face(face_locations: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    def area(location: tuple[int, int, int, int]) -> int:
        top, right, bottom, left = location
        return max(0, bottom - top) * max(0, right - left)

    return max(face_locations, key=area)


def _save_thumbnail(image_array: np.ndarray, face_location: tuple[int, int, int, int], student_id: str) -> str:
    """Crops, resizes, and uploads the enrollment thumbnail to Supabase Storage.
    Returns the object path (relative to the bucket), not a local file path."""
    top, right, bottom, left = face_location
    pad_y = int((bottom - top) * 0.25)
    pad_x = int((right - left) * 0.25)
    height, width = image_array.shape[:2]

    crop = Image.fromarray(image_array).crop(
        (
            max(left - pad_x, 0),
            max(top - pad_y, 0),
            min(right + pad_x, width),
            min(bottom + pad_y, height),
        )
    )
    crop.thumbnail(THUMBNAIL_SIZE)

    buffer = io.BytesIO()
    crop.save(buffer, format="JPEG", quality=88)

    _ensure_bucket()
    object_path = f"{student_id}.jpg"
    get_supabase_client().storage.from_(PHOTOS_BUCKET).upload(
        object_path,
        buffer.getvalue(),
        file_options={"content-type": "image/jpeg", "x-upsert": "true"},
    )
    return object_path


def enroll_student(student_id: str, name: str, image_bytes: bytes) -> dict:
    student_id = student_id.strip()
    name = name.strip()
    if not student_id or not name:
        raise ValueError("Student ID and name are required.")

    image_array = _image_from_bytes(image_bytes)
    face_locations = face_recognition.face_locations(image_array)

    if not face_locations:
        raise ValueError("No face detected in the uploaded photo. Use a clear, front-facing photo.")

    face_location = _largest_face(face_locations)
    encoding = face_recognition.face_encodings(image_array, known_face_locations=[face_location])[0]

    photo_path = _save_thumbnail(image_array, face_location, student_id)
    enrolled_at = datetime.now(timezone.utc)

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO attendance_roster
                    (student_id, name, encoding, photo_path, faces_detected_at_enrollment, enrolled_at)
                VALUES (:student_id, :name, :encoding, :photo_path, :faces_detected, :enrolled_at)
                ON CONFLICT (student_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    encoding = EXCLUDED.encoding,
                    photo_path = EXCLUDED.photo_path,
                    faces_detected_at_enrollment = EXCLUDED.faces_detected_at_enrollment,
                    enrolled_at = EXCLUDED.enrolled_at
                """
            ),
            {
                "student_id": student_id,
                "name": name,
                "encoding": encoding.tolist(),
                "photo_path": photo_path,
                "faces_detected": len(face_locations),
                "enrolled_at": enrolled_at,
            },
        )

    return {
        "student_id": student_id,
        "name": name,
        "enrolled_at": enrolled_at.isoformat(),
        "faces_detected": len(face_locations),
        "message": "Student enrolled successfully."
        if len(face_locations) == 1
        else "Student enrolled using the largest detected face; the photo contained multiple faces.",
    }


def list_roster() -> list[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT student_id, name, enrolled_at, photo_path FROM attendance_roster ORDER BY name")
        ).mappings()
        return [
            {
                "student_id": row["student_id"],
                "name": row["name"],
                "enrolled_at": row["enrolled_at"].isoformat() if row["enrolled_at"] else None,
                "photo_path": row["photo_path"],
            }
            for row in rows
        ]


def get_photo_url(student_id: str) -> str:
    with get_engine().connect() as conn:
        photo_path = conn.execute(
            text("SELECT photo_path FROM attendance_roster WHERE student_id = :sid"),
            {"sid": student_id},
        ).scalar_one_or_none()
    if not photo_path:
        raise FileNotFoundError(f"No enrolled photo found for student: {student_id}")
    return get_supabase_client().storage.from_(PHOTOS_BUCKET).get_public_url(photo_path)


def delete_enrollment(student_id: str) -> None:
    with get_engine().begin() as conn:
        photo_path = conn.execute(
            text("SELECT photo_path FROM attendance_roster WHERE student_id = :sid"),
            {"sid": student_id},
        ).scalar_one_or_none()
        if photo_path is None:
            raise FileNotFoundError(f"No enrolled student found with ID: {student_id}")
        conn.execute(text("DELETE FROM attendance_roster WHERE student_id = :sid"), {"sid": student_id})

    if photo_path:
        get_supabase_client().storage.from_(PHOTOS_BUCKET).remove([photo_path])


def _annotate_image(image_array: np.ndarray, detections: list[dict]) -> str:
    image = Image.fromarray(image_array)
    draw = ImageDraw.Draw(image)

    for detection in detections:
        top, right, bottom, left = detection["location"]
        color = (46, 139, 87) if detection["matched"] else (196, 64, 64)
        label = detection["name"] if detection["matched"] else "Unknown"

        draw.rectangle(((left, top), (right, bottom)), outline=color, width=3)
        text_y = bottom + 4 if bottom + 20 < image.height else max(top - 20, 0)
        draw.rectangle(((left, text_y), (left + 8 * len(label) + 8, text_y + 18)), fill=color)
        draw.text((left + 4, text_y + 2), label, fill=(255, 255, 255))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    import base64

    return base64.b64encode(buffer.getvalue()).decode("ascii")


def mark_attendance(
    course_id: str,
    course_name: str,
    session_label: str,
    session_date: str | None,
    image_bytes: bytes,
) -> dict:
    course_id = course_id.strip()
    course_name = course_name.strip()
    session_label = session_label.strip() or "Session"
    session_date = (session_date or "").strip() or date.today().isoformat()

    if not course_id:
        raise ValueError("Course ID is required.")

    with get_engine().connect() as conn:
        roster_rows = conn.execute(
            text("SELECT student_id, name, encoding FROM attendance_roster")
        ).mappings().all()

    if not roster_rows:
        raise ValueError("No students are enrolled yet. Enroll students before marking attendance.")

    roster = {row["student_id"]: {"name": row["name"], "encoding": row["encoding"]} for row in roster_rows}
    known_ids = list(roster.keys())
    known_encodings = [np.array(roster[student_id]["encoding"]) for student_id in known_ids]

    image_array = _image_from_bytes(image_bytes)
    face_locations = face_recognition.face_locations(image_array)
    face_encodings = face_recognition.face_encodings(image_array, known_face_locations=face_locations)

    detections = []
    matched_ids: set[str] = set()

    for location, encoding in zip(face_locations, face_encodings):
        distances = face_recognition.face_distance(known_encodings, encoding)
        best_index = int(np.argmin(distances)) if len(distances) else None
        matched = best_index is not None and distances[best_index] <= MATCH_TOLERANCE

        detection = {"location": location, "matched": matched}
        if matched:
            student_id = known_ids[best_index]
            if student_id in matched_ids:
                detection["matched"] = False
                detection["name"] = None
            else:
                matched_ids.add(student_id)
                detection["student_id"] = student_id
                detection["name"] = roster[student_id]["name"]
                detection["confidence"] = round(1 - float(distances[best_index]), 3)
        detections.append(detection)

    unmatched_face_count = sum(1 for detection in detections if not detection["matched"])

    session_id = uuid.uuid4().hex[:12]
    marked_at = datetime.now(timezone.utc)

    present = []
    absent = []
    rows = []
    for student_id, entry in roster.items():
        is_present = student_id in matched_ids
        confidence = next(
            (detection["confidence"] for detection in detections if detection.get("student_id") == student_id),
            None,
        )
        record = {
            "student_id": student_id,
            "name": entry["name"],
            "confidence": confidence,
        }
        (present if is_present else absent).append(record)
        rows.append(
            {
                "session_id": session_id,
                "course_id": course_id,
                "course_name": course_name,
                "session_label": session_label,
                "session_date": session_date,
                "student_id": student_id,
                "student_name": entry["name"],
                "status": "present" if is_present else "absent",
                "confidence": confidence,
                "marked_at": marked_at,
            }
        )

    with get_engine().begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO attendance_log
                    (session_id, course_id, course_name, session_label, session_date,
                     student_id, student_name, status, confidence, marked_at)
                VALUES
                    (:session_id, :course_id, :course_name, :session_label, :session_date,
                     :student_id, :student_name, :status, :confidence, :marked_at)
                """
            ),
            rows,
        )

    annotated_image_b64 = _annotate_image(image_array, detections)

    return {
        "session_id": session_id,
        "course_id": course_id,
        "course_name": course_name,
        "session_label": session_label,
        "session_date": session_date,
        "marked_at": marked_at.isoformat(),
        "roster_size": len(roster),
        "faces_detected": len(face_locations),
        "present_count": len(present),
        "absent_count": len(absent),
        "unmatched_face_count": unmatched_face_count,
        "present": sorted(present, key=lambda item: item["name"]),
        "absent": sorted(absent, key=lambda item: item["name"]),
        "annotated_image_base64": annotated_image_b64,
    }


def list_attendance_history(course_id: str | None = None) -> list[dict]:
    query = """
        SELECT session_id, course_id, course_name, session_label, session_date,
               max(marked_at) AS marked_at,
               count(*) FILTER (WHERE status = 'present') AS present_count,
               count(*) FILTER (WHERE status = 'absent') AS absent_count
        FROM attendance_log
    """
    params: dict = {}
    if course_id:
        query += " WHERE course_id = :course_id"
        params["course_id"] = course_id
    query += """
        GROUP BY session_id, course_id, course_name, session_label, session_date
        ORDER BY marked_at DESC
    """

    with get_engine().connect() as conn:
        rows = conn.execute(text(query), params).mappings()
        return [
            {
                "session_id": row["session_id"],
                "course_id": row["course_id"],
                "course_name": row["course_name"],
                "session_label": row["session_label"],
                "session_date": row["session_date"].isoformat() if row["session_date"] else None,
                "marked_at": row["marked_at"].isoformat() if row["marked_at"] else None,
                "present_count": row["present_count"],
                "absent_count": row["absent_count"],
            }
            for row in rows
        ]


def get_session_detail(session_id: str) -> list[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT session_id, course_id, course_name, session_label, session_date,
                       student_id, student_name, status, confidence, marked_at
                FROM attendance_log
                WHERE session_id = :session_id
                ORDER BY status, student_name
                """
            ),
            {"session_id": session_id},
        ).mappings()
        return [
            {
                "session_id": row["session_id"],
                "course_id": row["course_id"],
                "course_name": row["course_name"],
                "session_label": row["session_label"],
                "session_date": row["session_date"].isoformat() if row["session_date"] else None,
                "student_id": row["student_id"],
                "student_name": row["student_name"],
                "status": row["status"],
                "confidence": row["confidence"],
                "marked_at": row["marked_at"].isoformat() if row["marked_at"] else None,
            }
            for row in rows
        ]
