"""
student_db.py -- BridgeNote AI data layer
Loads the mock student sensory-profile catalogue and stores per-session
continuity notes so the next volunteer can pick up where the last one left off.
"""

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
STUDENTS_PATH = os.path.join(BASE_DIR, "data", "students.json")
SESSION_LOG_PATH = os.path.join(BASE_DIR, "data", "session_log.json")


def load_students() -> list:
    with open(STUDENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["students"]


def get_student_by_id(student_id: str) -> dict | None:
    for s in load_students():
        if s["id"] == student_id:
            return s
    return None


def load_session_memory() -> list:
    if not os.path.exists(SESSION_LOG_PATH):
        return []
    with open(SESSION_LOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_notes_for_student(student_id: str, limit: int = 10) -> list:
    memory = load_session_memory()
    notes = [n for n in memory if n.get("student_id") == student_id]
    return notes[-limit:][::-1]  # most recent first


def save_session_note(student_id: str, volunteer_name: str, note_type: str, note: str):
    """note_type: 'lesson_feedback' or 'sos_event'"""
    memory = load_session_memory()
    memory.append({
        "student_id": student_id,
        "volunteer_name": volunteer_name or "Anonymous volunteer",
        "note_type": note_type,
        "note": note,
        "timestamp": datetime.now().isoformat(timespec="minutes"),
    })
    os.makedirs(os.path.dirname(SESSION_LOG_PATH), exist_ok=True)
    with open(SESSION_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
