"""
control_router.py — Control endpoints cho Robot Bi API.
  GET  /api/status           — Trạng thái robot
  GET  /api/events           — Danh sách sự kiện
  POST /api/events/read_all  — Đánh dấu tất cả đã đọc
  GET  /api/chats            — Nhật ký hội thoại
  GET  /api/memories         — Danh sách trí nhớ
  POST /api/memories         — Thêm trí nhớ
  GET  /api/memories/export  — Export JSON backup
  PUT  /api/memories/{id}    — Sửa trí nhớ
  DELETE /api/memories/{id}  — Xóa trí nhớ
  POST /api/puppet           — Bi đọc text từ app
  GET  /api/tasks            — Danh sách nhiệm vụ
  POST /api/tasks            — Thêm nhiệm vụ
  GET  /api/tasks/stars      — Tổng sao
  POST /api/tasks/{id}/complete — Hoàn thành nhiệm vụ
  DELETE /api/tasks/{id}     — Xóa nhiệm vụ
"""
import logging
import csv
import hashlib
import json
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user, require_role
from src.api.routers.conversation_router import _require_family
from src.safety.safety_filter import get_global_policy
from src.infrastructure.database.db import (
    add_special_memory,
    create_parent_event_note,
    delete_parent_event_note,
    delete_special_memory,
    ensure_family_exists,
    event_exists_for_family,
    get_db_connection,
    list_parent_event_notes,
    list_special_memories,
    update_parent_event_note,
)
import src.infrastructure.sessions.state as _state

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Pydantic models ────────────────────────────────────────────────────────

class MemoryIn(BaseModel):
    text: str


class MemoryUpdate(BaseModel):
    text: str


class SpecialMemoryIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    kind: str = Field(default="other", max_length=20)
    memory_date: str = Field(default="", max_length=40)
    note: str = Field(default="", max_length=500)


class PuppetIn(BaseModel):
    text: str


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Ten nhiem vu")
    remind_time: Optional[str] = Field(
        None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Dinh dang HH:MM",
    )


# Request helpers

class ParentEventNoteIn(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)


class ChildProfileIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    birth_date: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[str] = Field(default=None, max_length=40)
    avatar: Optional[str] = Field(default=None, max_length=80)
    interests: list[str] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None, max_length=1000)


class ChildProfilePatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    birth_date: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[str] = Field(default=None, max_length=40)
    avatar: Optional[str] = Field(default=None, max_length=80)
    interests: Optional[list[str]] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class AgeFilterIn(BaseModel):
    child_id: Optional[str] = Field(default=None, max_length=80)
    enabled: bool = False
    min_age: Optional[int] = 5
    max_age: Optional[int] = 12
    blocked_topics: list[str] = Field(default_factory=list)
    allowed_topics: list[str] = Field(default_factory=list)
    strict_mode: bool = True


class TimeLimitIn(BaseModel):
    child_id: Optional[str] = Field(default=None, max_length=80)
    enabled: bool = False
    daily_limit_minutes: int = 60
    warning_minutes: int = 10
    reset_time: str = "00:00"


class SleepScheduleIn(BaseModel):
    enabled: bool = False
    start_time: str = "21:00"
    end_time: str = "06:30"
    days: list[str] = Field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=80)


class NotificationSettingsIn(BaseModel):
    enabled: bool = True
    event_types: dict = Field(default_factory=dict)
    quiet_hours: dict = Field(default_factory=dict)
    channels: dict = Field(default_factory=dict)
    push_subscription: Optional[dict] = None


class ReportExportIn(BaseModel):
    format: str = Field(..., max_length=12)
    start_date: str
    end_date: str
    sections: list[str] = Field(default_factory=lambda: ["events", "conversations", "emotions", "education", "tasks"])
    child_id: Optional[str] = Field(default=None, max_length=80)


class RobotLocationIn(BaseModel):
    room_name: Optional[str] = Field(default=None, max_length=120)
    location_label: Optional[str] = Field(default=None, max_length=200)
    source: str = Field(default="parent", max_length=20)
    confidence: float = 1.0


_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
_EVENT_TYPES = {
    "motion",
    "stranger",
    "known_face",
    "cry",
    "chat",
    "system",
    "homework",
    "special_memory_due",
}
_CHANNELS = {"in_app", "web_push"}
_REPORT_SECTIONS = {"events", "conversations", "emotions", "education", "tasks"}
_PAIRING_PURPOSES = {"parent_app", "robot_display", "esp32"}
_LOCATION_SOURCES = {"parent", "robot", "system"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_array(value) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _json_object(value) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _dump_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _child_key(child_id: Optional[str]) -> str:
    return (child_id or "").strip()


def _public_child_id(child_id: str | None) -> str | None:
    value = (child_id or "").strip()
    return value or None


def _validate_time(value: str, field_name: str) -> str:
    if not _TIME_RE.match(value or ""):
        raise HTTPException(status_code=422, detail=f"{field_name} must use HH:MM")
    return value


def _validate_iso_date(value: Optional[str], field_name: str) -> Optional[str]:
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field_name} must use YYYY-MM-DD")
    return value


def _age_from_birth_date(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        born = datetime.strptime(value, "%Y-%m-%d").date()
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except ValueError:
        return None


def _birth_date_from_age(age: int) -> str:
    today = date.today()
    try:
        return today.replace(year=today.year - age).isoformat()
    except ValueError:
        return (today - timedelta(days=365 * age)).isoformat()


def _validate_age(age: Optional[int]) -> Optional[int]:
    if age is None:
        return None
    if int(age) < 5 or int(age) > 12:
        raise HTTPException(status_code=422, detail="age must be between 5 and 12")
    return int(age)


def _validate_string_list(values: list[str] | None, field_name: str) -> list[str]:
    result = []
    for value in values or []:
        item = str(value).strip()
        if not item:
            continue
        if len(item) > 80:
            raise HTTPException(status_code=422, detail=f"{field_name} entries must be <= 80 chars")
        result.append(item)
    if len(result) > 50:
        raise HTTPException(status_code=422, detail=f"{field_name} supports at most 50 entries")
    return result


def _child_row_to_dict(row) -> dict:
    birth_date = row["birth_date"]
    return {
        "child_id": row["child_id"],
        "name": row["name"],
        "birth_date": birth_date,
        "age": _age_from_birth_date(birth_date),
        "grade": row["grade"],
        "avatar": row["avatar"],
        "interests": _json_array(row["interests_json"]),
        "notes": row["notes"] or "",
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _validate_child_for_family(family_id: str, child_id: Optional[str]) -> str:
    key = _child_key(child_id)
    if not key:
        return ""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT child_id FROM child_profiles WHERE family_id = ? AND child_id = ?",
            (family_id, key),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Child profile not found")
    return key


def _normalize_child_payload(data: dict, *, partial: bool = False) -> dict:
    normalized = {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="name must not be empty")
        normalized["name"] = name
    elif not partial:
        raise HTTPException(status_code=422, detail="name is required")

    birth_date = data.get("birth_date")
    age = data.get("age")
    if birth_date:
        birth_date = _validate_iso_date(str(birth_date), "birth_date")
        computed_age = _age_from_birth_date(birth_date)
        if computed_age is not None:
            _validate_age(computed_age)
        normalized["birth_date"] = birth_date
    elif age is not None:
        normalized["birth_date"] = _birth_date_from_age(_validate_age(age))
    elif not partial:
        raise HTTPException(status_code=422, detail="birth_date or age is required")

    if "grade" in data:
        normalized["grade"] = (data.get("grade") or "").strip()[:40] or None
    if "avatar" in data:
        normalized["avatar"] = (data.get("avatar") or "").strip()[:80] or None
    if "interests" in data:
        normalized["interests_json"] = _dump_json(_validate_string_list(data.get("interests"), "interests"))
    elif not partial:
        normalized["interests_json"] = "[]"
    if "notes" in data:
        normalized["notes"] = (data.get("notes") or "").strip()[:1000]
    elif not partial:
        normalized["notes"] = ""
    return normalized


def _default_age_filter(child_id: Optional[str] = None) -> dict:
    # Mặc định global do admin đặt (Phase 5); fallback giá trị an toàn cũ.
    pol = get_global_policy()["age"]
    return {
        "child_id": child_id,
        "enabled": False,
        "min_age": pol["min_age"],
        "max_age": pol["max_age"],
        "blocked_topics": [],
        "allowed_topics": [],
        "strict_mode": bool(pol["strict_mode"]),
        "updated_at": None,
    }


def _default_time_limits(child_id: Optional[str] = None) -> dict:
    pol = get_global_policy()["time"]
    return {
        "child_id": child_id,
        "enabled": False,
        "daily_limit_minutes": pol["daily_limit_minutes"],
        "warning_minutes": pol["warning_minutes"],
        "reset_time": pol["reset_time"],
        "updated_at": None,
    }


def _default_sleep_settings() -> dict:
    pol = get_global_policy()["sleep"]
    return {
        "enabled": False,
        "start_time": pol["start_time"],
        "end_time": pol["end_time"],
        "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        "timezone": "Asia/Ho_Chi_Minh",
        "updated_at": None,
    }


def _default_notification_settings() -> dict:
    return {
        "enabled": True,
        "event_types": {},
        "quiet_hours": {},
        "channels": {"in_app": True, "web_push": False},
        "updated_at": None,
    }


def _age_filter_row_to_dict(row) -> dict:
    if not row:
        return _default_age_filter()
    return {
        "child_id": _public_child_id(row["child_id"]),
        "enabled": bool(row["enabled"]),
        "min_age": row["min_age"],
        "max_age": row["max_age"],
        "blocked_topics": _json_array(row["blocked_topics_json"]),
        "allowed_topics": _json_array(row["allowed_topics_json"]),
        "strict_mode": bool(row["strict_mode"]),
        "updated_at": row["updated_at"],
    }


def _time_limits_row_to_dict(row) -> dict:
    if not row:
        return _default_time_limits()
    return {
        "child_id": _public_child_id(row["child_id"]),
        "enabled": bool(row["enabled"]),
        "daily_limit_minutes": int(row["daily_limit_minutes"]),
        "warning_minutes": int(row["warning_minutes"]),
        "reset_time": row["reset_time"],
        "updated_at": row["updated_at"],
    }


def _usage_today(family_id: str, child_id: str, settings: dict | None = None) -> dict:
    today = date.today().isoformat()
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT seconds_used, sessions_count, updated_at
            FROM daily_interaction_usage
            WHERE family_id = ? AND child_id = ? AND usage_date = ?
            """,
            (family_id, child_id, today),
        ).fetchone()
    seconds_used = int(row["seconds_used"] or 0) if row else 0
    limit_minutes = int((settings or {}).get("daily_limit_minutes") or 60)
    enabled = bool((settings or {}).get("enabled", False))
    limit_seconds = limit_minutes * 60
    return {
        "date": today,
        "child_id": _public_child_id(child_id),
        "seconds_used": seconds_used,
        "sessions_count": int(row["sessions_count"] or 0) if row else 0,
        "remaining_seconds": max(0, limit_seconds - seconds_used),
        "limit_reached": bool(enabled and seconds_used >= limit_seconds),
        "updated_at": row["updated_at"] if row else None,
    }


def _parse_event_types(types: Optional[str]) -> list[str] | None:
    if not types:
        return None
    parsed = [value.strip() for value in types.split(",") if value.strip()]
    if len(parsed) > 20:
        raise HTTPException(status_code=422, detail="types supports at most 20 values")
    return parsed or None


def _validate_event_date(value: Optional[str], field_name: str) -> Optional[str]:
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field_name} must use YYYY-MM-DD")
    return value


def _clean_parent_note(note: str) -> str:
    cleaned = (note or "").strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="note must not be empty")
    return cleaned


def _validate_report_sections(sections: list[str] | None) -> list[str]:
    cleaned = []
    for section in sections or []:
        value = str(section).strip().lower()
        if not value:
            continue
        if value not in _REPORT_SECTIONS:
            raise HTTPException(status_code=422, detail=f"Unsupported report section: {value}")
        if value not in cleaned:
            cleaned.append(value)
    return cleaned or ["events", "conversations", "emotions", "education", "tasks"]


def _report_rows(family_id: str, start_date: str, end_date: str, sections: list[str]) -> list[dict]:
    rows: list[dict] = []
    with get_db_connection() as conn:
        if "events" in sections:
            for row in conn.execute(
                """
                SELECT timestamp AS happened_at, type, message, metadata_json
                FROM events
                WHERE family_id = ?
                  AND date(timestamp) BETWEEN ? AND ?
                ORDER BY timestamp ASC
                """,
                (family_id, start_date, end_date),
            ).fetchall():
                metadata = _json_object(row["metadata_json"])
                rows.append(
                    {
                        "section": "events",
                        "timestamp": row["happened_at"],
                        "title": row["type"] or "event",
                        "detail": str(row["message"] or metadata.get("summary") or "")[:500],
                    }
                )

        if "conversations" in sections:
            for row in conn.execute(
                """
                SELECT started_at, title, turn_count
                FROM conversations
                WHERE family_id = ?
                  AND date(started_at) BETWEEN ? AND ?
                ORDER BY started_at ASC
                """,
                (family_id, start_date, end_date),
            ).fetchall():
                rows.append(
                    {
                        "section": "conversations",
                        "timestamp": row["started_at"],
                        "title": row["title"] or "Conversation",
                        "detail": f"{int(row['turn_count'] or 0)} turns",
                    }
                )

        if "emotions" in sections:
            try:
                emotion_rows = conn.execute(
                    """
                    SELECT timestamp, emotion
                    FROM emotion_logs
                    WHERE family_id = ?
                      AND date(timestamp) BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                    """,
                    (family_id, start_date, end_date),
                ).fetchall()
            except Exception:
                emotion_rows = []
            for row in emotion_rows:
                rows.append(
                    {
                        "section": "emotions",
                        "timestamp": row["timestamp"],
                        "title": row["emotion"] or "emotion",
                        "detail": "",
                    }
                )

        if "education" in sections:
            for row in conn.execute(
                """
                SELECT day_of_week, subject, time
                FROM learning_schedules
                WHERE family_id = ?
                ORDER BY day_of_week ASC
                """,
                (family_id,),
            ).fetchall():
                rows.append(
                    {
                        "section": "education",
                        "timestamp": row["day_of_week"],
                        "title": row["subject"] or "Learning schedule",
                        "detail": row["time"] or "",
                    }
                )

        if "tasks" in sections:
            for row in conn.execute(
                """
                SELECT created_at, name, completed_today, stars
                FROM tasks
                WHERE family_id = ?
                  AND date(created_at) BETWEEN ? AND ?
                ORDER BY created_at ASC
                """,
                (family_id, start_date, end_date),
            ).fetchall():
                status = "completed" if row["completed_today"] else "open"
                rows.append(
                    {
                        "section": "tasks",
                        "timestamp": row["created_at"],
                        "title": row["name"],
                        "detail": f"{status}; stars={int(row['stars'] or 0)}",
                    }
                )
    return rows


def _csv_safe(value):
    """Chống CSV formula injection (L-NEW-8): ô bắt đầu bằng = + - @ (hoặc tab/CR)
    có thể bị Excel/Sheets thực thi → thêm dấu nháy đơn dẫn đầu để vô hiệu."""
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _render_report_csv(rows: list[dict]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["section", "timestamp", "title", "detail"])
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _csv_safe(v) for k, v in row.items()})
    return output.getvalue()


def _pdf_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _render_report_pdf(rows: list[dict], start_date: str, end_date: str) -> bytes:
    lines = [f"Robot Bi report {start_date} to {end_date}", f"Rows: {len(rows)}"]
    for row in rows[:36]:
        title = str(row.get("title") or "")[:80]
        lines.append(f"{row.get('section')} | {row.get('timestamp')} | {title}")
    text_ops = ["BT", "/F1 10 Tf", "72 760 Td", "14 TL"]
    for line in lines:
        text_ops.append(f"({_pdf_escape(line)}) Tj")
        text_ops.append("T*")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_at = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def _location_row_to_dict(family_id: str, row) -> dict:
    if not row:
        return {
            "family_id": family_id,
            "room_name": None,
            "location_label": None,
            "source": "system",
            "confidence": 0.0,
            "updated_at": None,
        }
    return {
        "family_id": family_id,
        "room_name": row["room_name"],
        "location_label": row["location_label"],
        "source": row["source"],
        "confidence": float(row["confidence"]),
        "updated_at": row["updated_at"],
    }


# REST: Status

@router.get("/api/status")
async def get_status(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    total_stars = (
        _state._task_manager.get_total_stars(family_id=family_id)
        if _state._task_manager
        else 0
    )
    return {
        "status": "online",
        "ws_clients": _state._ws_manager.count,
        "puppet_queued": _state._puppet_queue.qsize(),
        "total_stars": total_stars,
    }


# ── REST: Events ──────────────────────────────────────────────────────────

# REST: Children and Parent App Settings

@router.get("/api/children")
async def list_children(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT child_id, name, birth_date, grade, avatar, interests_json,
                   notes, is_active, created_at, updated_at
            FROM child_profiles
            WHERE family_id = ?
            ORDER BY is_active DESC, created_at ASC
            """,
            (family_id,),
        ).fetchall()
    children = [_child_row_to_dict(row) for row in rows]
    active = next((child["child_id"] for child in children if child["is_active"]), None)
    return {"children": children, "active_child_id": active}


@router.post("/api/children")
async def create_child_profile(
    payload: ChildProfileIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = ensure_family_exists(_require_family(_current_user))
    values = _normalize_child_payload(payload.dict())
    child_id = uuid4().hex
    now = _now_iso()
    with get_db_connection() as conn:
        active_row = conn.execute(
            "SELECT 1 FROM child_profiles WHERE family_id = ? AND is_active = 1 LIMIT 1",
            (family_id,),
        ).fetchone()
        is_active = 0 if active_row else 1
        conn.execute(
            """
            INSERT INTO child_profiles (
                child_id, family_id, name, birth_date, grade, avatar,
                interests_json, notes, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                child_id,
                family_id,
                values["name"],
                values["birth_date"],
                values.get("grade"),
                values.get("avatar"),
                values.get("interests_json", "[]"),
                values.get("notes", ""),
                is_active,
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT child_id, name, birth_date, grade, avatar, interests_json,
                   notes, is_active, created_at, updated_at
            FROM child_profiles
            WHERE family_id = ? AND child_id = ?
            """,
            (family_id, child_id),
        ).fetchone()
    return {"ok": True, "child": _child_row_to_dict(row)}


@router.get("/api/children/{child_id}")
async def get_child_profile(
    child_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT child_id, name, birth_date, grade, avatar, interests_json,
                   notes, is_active, created_at, updated_at
            FROM child_profiles
            WHERE family_id = ? AND child_id = ?
            """,
            (family_id, child_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Child profile not found")
    return {"child": _child_row_to_dict(row)}


@router.patch("/api/children/{child_id}")
async def update_child_profile(
    child_id: str,
    payload: ChildProfilePatch,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    _validate_child_for_family(family_id, child_id)
    values = _normalize_child_payload(payload.dict(exclude_unset=True), partial=True)
    if values:
        assignments = [f"{column} = ?" for column in values.keys()]
        params = list(values.values())
        assignments.append("updated_at = ?")
        params.append(_now_iso())
        params.extend([family_id, child_id])
        with get_db_connection() as conn:
            conn.execute(
                f"""
                UPDATE child_profiles
                SET {', '.join(assignments)}
                WHERE family_id = ? AND child_id = ?
                """,
                tuple(params),
            )
            conn.commit()
    return await get_child_profile(child_id, _current_user)


@router.delete("/api/children/{child_id}")
async def delete_child_profile(
    child_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    _validate_child_for_family(family_id, child_id)
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT is_active FROM child_profiles WHERE family_id = ? AND child_id = ?",
            (family_id, child_id),
        ).fetchone()
        was_active = bool(row and row["is_active"])
        conn.execute("DELETE FROM child_profiles WHERE family_id = ? AND child_id = ?", (family_id, child_id))
        if was_active:
            next_row = conn.execute(
                """
                SELECT child_id FROM child_profiles
                WHERE family_id = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (family_id,),
            ).fetchone()
            if next_row:
                conn.execute(
                    "UPDATE child_profiles SET is_active = 1, updated_at = ? WHERE family_id = ? AND child_id = ?",
                    (_now_iso(), family_id, next_row["child_id"]),
                )
        conn.commit()
    return {"ok": True}


@router.put("/api/children/{child_id}/activate")
async def activate_child_profile(
    child_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    _validate_child_for_family(family_id, child_id)
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute("UPDATE child_profiles SET is_active = 0 WHERE family_id = ?", (family_id,))
        conn.execute(
            "UPDATE child_profiles SET is_active = 1, updated_at = ? WHERE family_id = ? AND child_id = ?",
            (now, family_id, child_id),
        )
        conn.commit()
    return await get_child_profile(child_id, _current_user)


@router.get("/api/settings/age-filter")
async def get_age_filter(
    child_id: Optional[str] = None,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    key = _validate_child_for_family(family_id, child_id)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT child_id, enabled, min_age, max_age, blocked_topics_json,
                   allowed_topics_json, strict_mode, updated_at
            FROM child_content_settings
            WHERE family_id = ? AND child_id = ?
            """,
            (family_id, key),
        ).fetchone()
    settings = _age_filter_row_to_dict(row) if row else _default_age_filter(_public_child_id(key))
    return {"ok": True, "settings": settings}


@router.post("/api/settings/age-filter")
async def save_age_filter(
    payload: AgeFilterIn,
    _current_user: dict = Depends(require_role("owner", "parent")),
):
    family_id = _require_family(_current_user)
    key = _validate_child_for_family(family_id, payload.child_id)
    min_age = _validate_age(payload.min_age)
    max_age = _validate_age(payload.max_age)
    if min_age is not None and max_age is not None and min_age > max_age:
        raise HTTPException(status_code=422, detail="min_age must be <= max_age")
    blocked = _validate_string_list(payload.blocked_topics, "blocked_topics")
    allowed = _validate_string_list(payload.allowed_topics, "allowed_topics")
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute("DELETE FROM child_content_settings WHERE family_id = ? AND child_id = ?", (family_id, key))
        conn.execute(
            """
            INSERT INTO child_content_settings (
                setting_id, family_id, child_id, enabled, min_age, max_age,
                blocked_topics_json, allowed_topics_json, strict_mode, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                family_id,
                key,
                1 if payload.enabled else 0,
                min_age,
                max_age,
                _dump_json(blocked),
                _dump_json(allowed),
                1 if payload.strict_mode else 0,
                now,
            ),
        )
        conn.commit()
    return await get_age_filter(_public_child_id(key), _current_user)


@router.get("/api/settings/time-limits")
async def get_time_limits(
    child_id: Optional[str] = None,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    key = _validate_child_for_family(family_id, child_id)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT child_id, enabled, daily_limit_minutes, warning_minutes,
                   reset_time, updated_at
            FROM interaction_limit_settings
            WHERE family_id = ? AND child_id = ?
            """,
            (family_id, key),
        ).fetchone()
    settings = _time_limits_row_to_dict(row) if row else _default_time_limits(_public_child_id(key))
    return {"ok": True, "settings": settings, "usage_today": _usage_today(family_id, key, settings)}


@router.post("/api/settings/time-limits")
async def save_time_limits(
    payload: TimeLimitIn,
    _current_user: dict = Depends(require_role("owner", "parent")),
):
    family_id = _require_family(_current_user)
    key = _validate_child_for_family(family_id, payload.child_id)
    if payload.daily_limit_minutes < 1 or payload.daily_limit_minutes > 480:
        raise HTTPException(status_code=422, detail="daily_limit_minutes must be 1-480")
    if payload.warning_minutes < 0 or payload.warning_minutes > 120:
        raise HTTPException(status_code=422, detail="warning_minutes must be 0-120")
    if payload.warning_minutes > payload.daily_limit_minutes:
        raise HTTPException(status_code=422, detail="warning_minutes must be <= daily_limit_minutes")
    reset_time = _validate_time(payload.reset_time, "reset_time")
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute("DELETE FROM interaction_limit_settings WHERE family_id = ? AND child_id = ?", (family_id, key))
        conn.execute(
            """
            INSERT INTO interaction_limit_settings (
                setting_id, family_id, child_id, enabled, daily_limit_minutes,
                warning_minutes, reset_time, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                family_id,
                key,
                1 if payload.enabled else 0,
                int(payload.daily_limit_minutes),
                int(payload.warning_minutes),
                reset_time,
                now,
            ),
        )
        conn.commit()
    return await get_time_limits(_public_child_id(key), _current_user)


@router.get("/api/usage/today")
async def get_usage_today(
    child_id: Optional[str] = None,
    _current_user: dict = Depends(get_current_user),
):
    data = await get_time_limits(child_id, _current_user)
    return {"usage_today": data["usage_today"], "settings": data["settings"]}


@router.get("/api/settings/sleep")
async def get_sleep_schedule(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT enabled, start_time, end_time, days_json, timezone, updated_at
            FROM sleep_schedule_settings
            WHERE family_id = ?
            """,
            (family_id,),
        ).fetchone()
    if row:
        settings = {
            "enabled": bool(row["enabled"]),
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "days": _json_array(row["days_json"]),
            "timezone": row["timezone"],
            "updated_at": row["updated_at"],
        }
    else:
        settings = _default_sleep_settings()
    return {"ok": True, "settings": settings}


@router.post("/api/settings/sleep")
async def save_sleep_schedule(
    payload: SleepScheduleIn,
    _current_user: dict = Depends(require_role("owner", "parent")),
):
    family_id = _require_family(_current_user)
    start_time = _validate_time(payload.start_time, "start_time")
    end_time = _validate_time(payload.end_time, "end_time")
    days = [str(day).strip().lower() for day in payload.days]
    if not days or any(day not in _DAYS for day in days):
        raise HTTPException(status_code=422, detail="days must contain mon..sun values")
    tz = (payload.timezone or "").strip()
    if not tz or len(tz) > 80:
        raise HTTPException(status_code=422, detail="timezone is invalid")
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sleep_schedule_settings (
                family_id, enabled, start_time, end_time, days_json, timezone, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (family_id, 1 if payload.enabled else 0, start_time, end_time, _dump_json(days), tz, now),
        )
        conn.commit()
    return await get_sleep_schedule(_current_user)


@router.get("/api/settings/notifications")
async def get_notification_settings(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT enabled, event_types_json, quiet_hours_json, channels_json, updated_at
            FROM notification_settings
            WHERE family_id = ?
            """,
            (family_id,),
        ).fetchone()
    if row:
        settings = {
            "enabled": bool(row["enabled"]),
            "event_types": _json_object(row["event_types_json"]),
            "quiet_hours": _json_object(row["quiet_hours_json"]),
            "channels": _json_object(row["channels_json"]),
            "updated_at": row["updated_at"],
        }
    else:
        settings = _default_notification_settings()
    return {"ok": True, "settings": settings}


@router.post("/api/settings/notifications")
async def save_notification_settings(
    payload: NotificationSettingsIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    user_id = str(_current_user.get("user_id") or "")
    event_types = {}
    for key, enabled in (payload.event_types or {}).items():
        if key not in _EVENT_TYPES:
            raise HTTPException(status_code=422, detail=f"Unsupported event type: {key}")
        event_types[key] = bool(enabled)
    channels = {}
    for key, enabled in (payload.channels or {"in_app": True, "web_push": False}).items():
        if key not in _CHANNELS:
            raise HTTPException(status_code=422, detail=f"Unsupported notification channel: {key}")
        channels[key] = bool(enabled)
    channels.setdefault("in_app", True)
    channels.setdefault("web_push", False)

    quiet_hours = dict(payload.quiet_hours or {})
    if quiet_hours.get("enabled"):
        quiet_hours["start_time"] = _validate_time(str(quiet_hours.get("start_time", "")), "quiet_hours.start_time")
        quiet_hours["end_time"] = _validate_time(str(quiet_hours.get("end_time", "")), "quiet_hours.end_time")
        quiet_hours["enabled"] = True
    elif quiet_hours:
        quiet_hours["enabled"] = False

    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO notification_settings (
                family_id, enabled, event_types_json, quiet_hours_json, channels_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                family_id,
                1 if payload.enabled else 0,
                _dump_json(event_types),
                _dump_json(quiet_hours),
                _dump_json(channels),
                now,
            ),
        )
        if payload.push_subscription:
            endpoint = str(payload.push_subscription.get("endpoint", "")).strip()
            if not endpoint or len(endpoint) > 2048:
                raise HTTPException(status_code=422, detail="push_subscription.endpoint is invalid")
            endpoint_hash = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
            conn.execute(
                """
                INSERT INTO push_subscriptions (
                    subscription_id, family_id, user_id, endpoint_hash,
                    subscription_json, created_at, updated_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    uuid4().hex,
                    family_id,
                    user_id,
                    endpoint_hash,
                    _dump_json(payload.push_subscription),
                    now,
                    now,
                ),
            )
        conn.commit()
    return await get_notification_settings(_current_user)


@router.post("/api/reports/export")
async def export_parent_report(
    payload: ReportExportIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    report_format = (payload.format or "").strip().lower()
    if report_format not in {"csv", "pdf"}:
        raise HTTPException(status_code=422, detail="format must be csv or pdf")
    start = _validate_iso_date(payload.start_date, "start_date")
    end = _validate_iso_date(payload.end_date, "end_date")
    if not start or not end:
        raise HTTPException(status_code=422, detail="start_date and end_date are required")
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start_date must be <= end_date")
    if payload.child_id:
        _validate_child_for_family(family_id, payload.child_id)
    sections = _validate_report_sections(payload.sections)
    rows = _report_rows(family_id, start, end, sections)
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO report_exports (
                export_id, family_id, user_id, format, start_date, end_date,
                sections_json, row_count, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                family_id,
                str(_current_user.get("user_id") or ""),
                report_format,
                start,
                end,
                _dump_json(sections),
                len(rows),
                now,
                "completed",
            ),
        )
        conn.commit()

    filename = f"robot-bi-report-{start}-{end}.{report_format}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if report_format == "csv":
        return Response(
            content=_render_report_csv(rows),
            media_type="text/csv; charset=utf-8",
            headers=headers,
        )
    return Response(
        content=_render_report_pdf(rows, start, end),
        media_type="application/pdf",
        headers=headers,
    )


@router.get("/api/device/connection-qr")
async def get_device_connection_qr(
    request: Request,
    purpose: str = Query(default="parent_app", max_length=40),
    ttl_seconds: int = Query(default=300, ge=60, le=3600),
    _current_user: dict = Depends(get_current_user),
):
    family_id = ensure_family_exists(_require_family(_current_user))
    purpose_value = (purpose or "").strip()
    if purpose_value not in _PAIRING_PURPOSES:
        raise HTTPException(status_code=422, detail="purpose must be parent_app, robot_display, or esp32")

    pairing_id = uuid4().hex
    raw_code = secrets.token_urlsafe(18)
    code_hash = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
    now_dt = datetime.now(timezone.utc)
    expires_dt = now_dt + timedelta(seconds=int(ttl_seconds))
    base_url = str(request.base_url).rstrip("/")
    payload_url = f"{base_url}/connect?pairing_id={pairing_id}&code={raw_code}&purpose={purpose_value}"
    tunnel_url = os.getenv("CLOUDFLARE_TUNNEL_URL", "").strip() or None

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO device_pairing_codes (
                pairing_id, family_id, purpose, code_hash, expires_at, used_at,
                created_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                pairing_id,
                family_id,
                purpose_value,
                code_hash,
                expires_dt.isoformat(),
                now_dt.isoformat(),
                str(_current_user.get("user_id") or ""),
            ),
        )
        conn.commit()

    return {
        "qr": {
            "pairing_id": pairing_id,
            "payload_url": payload_url,
            "expires_at": expires_dt.isoformat(),
            "ttl_seconds": int(ttl_seconds),
        },
        "network": {
            "local_url": base_url,
            "tunnel_url": tunnel_url,
            "https_enabled": request.url.scheme == "https",
        },
    }


@router.get("/api/robot/location")
async def get_robot_location(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT room_name, location_label, source, confidence, updated_at
            FROM robot_location_metadata
            WHERE family_id = ?
            """,
            (family_id,),
        ).fetchone()
    return {"ok": True, "location": _location_row_to_dict(family_id, row)}


@router.post("/api/robot/location")
async def save_robot_location(
    payload: RobotLocationIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = ensure_family_exists(_require_family(_current_user))
    source = (payload.source or "").strip().lower()
    if source not in _LOCATION_SOURCES:
        raise HTTPException(status_code=422, detail="source must be parent, robot, or system")
    confidence = float(payload.confidence)
    if confidence < 0.0 or confidence > 1.0:
        raise HTTPException(status_code=422, detail="confidence must be between 0.0 and 1.0")
    room_name = (payload.room_name or "").strip() or None
    location_label = (payload.location_label or "").strip() or None
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO robot_location_metadata (
                family_id, room_name, location_label, source, confidence,
                updated_at, updated_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                family_id,
                room_name,
                location_label,
                source,
                confidence,
                now,
                str(_current_user.get("user_id") or ""),
            ),
        )
        conn.commit()
    return await get_robot_location(_current_user)


@router.get("/api/events")
async def get_events(
    type: Optional[str] = None,
    types: Optional[str] = Query(default=None, max_length=500),
    unread_only: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    has_clip: Optional[bool] = None,
    has_note: Optional[bool] = None,
    q: Optional[str] = Query(default=None, min_length=1, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    sort: str = Query(default="desc", max_length=4),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    event_types = _parse_event_types(types)
    start = _validate_event_date(start_date, "start_date")
    end = _validate_event_date(end_date, "end_date")
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start_date must be before or equal to end_date")
    sort_value = (sort or "desc").lower()
    if sort_value not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="sort must be asc or desc")

    events = _state._fetch_events_from_db(
        event_type=type,
        event_types=event_types,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
        newest_first=(sort_value == "desc"),
        family_id=family_id,
        start_date=start,
        end_date=end,
        has_clip=has_clip,
        has_note=has_note,
        q=q,
        include_note_count=True,
    )
    total = _state._count_events_from_db(
        event_type=type,
        event_types=event_types,
        unread_only=unread_only,
        family_id=family_id,
        start_date=start,
        end_date=end,
        has_clip=has_clip,
        has_note=has_note,
        q=q,
    )
    return {
        "events": events,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "type": type,
            "types": event_types,
            "unread_only": unread_only,
            "start_date": start,
            "end_date": end,
            "has_clip": has_clip,
            "has_note": has_note,
            "q": q,
            "sort": sort_value,
        },
    }


@router.post("/api/events/read_all")
async def mark_read(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._notifier:
        _state._notifier.mark_all_read(family_id=family_id)
    return {"status": "ok"}


# REST: Event Notes

@router.get("/api/events/{event_id}/notes")
async def get_event_notes(
    event_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"notes": list_parent_event_notes(family_id, event_id)}


@router.post("/api/events/{event_id}/notes")
async def add_event_note(
    event_id: str,
    payload: ParentEventNoteIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    note = create_parent_event_note(
        family_id=family_id,
        event_id=event_id,
        user_id=str(_current_user.get("user_id") or ""),
        note=_clean_parent_note(payload.note),
    )
    return note


@router.put("/api/events/{event_id}/notes/{note_id}")
async def edit_event_note(
    event_id: str,
    note_id: str,
    payload: ParentEventNoteIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    note = update_parent_event_note(
        family_id=family_id,
        event_id=event_id,
        note_id=note_id,
        note=_clean_parent_note(payload.note),
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/api/events/{event_id}/notes/{note_id}")
async def remove_event_note(
    event_id: str,
    note_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    if not delete_parent_event_note(family_id, event_id, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "ok"}


# REST: Chat Log

@router.get("/api/chats")
async def get_chats(
    limit: int = Query(default=20, ge=1, le=200),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not _state._notifier:
        return {"chats": [], "total": 0}
    chats = _state._fetch_events_from_db(
        event_type="chat",
        unread_only=False,
        limit=limit,
        newest_first=True,
        family_id=family_id,
    )
    total = _state._count_events_from_db(
        event_type="chat",
        unread_only=False,
        family_id=family_id,
    )
    return {"chats": chats, "total": total}


# ── REST: Memories ────────────────────────────────────────────────────────

@router.get("/api/memories")
async def list_memories(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "list")
    if not _state._rag:
        return {"memories": [], "total": 0}
    memories = _state._rag.list_memories(family_id=family_id)
    return {"memories": memories, "total": len(memories)}


@router.post("/api/memories")
async def add_memory(body: MemoryIn, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "add")
    if not body.text.strip():
        raise HTTPException(400, "text không được rỗng")
    if not _state._rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _state._rag.add_manual_memory(body.text.strip(), family_id=family_id)
    return {"status": "ok" if ok else "fail"}


# Export phải đứng trước /{memory_id} để không bị capture
@router.get("/api/memories/export")
async def export_memories(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "export")
    if not _state._rag:
        return []
    return _state._rag.export_memories(family_id=family_id)


# ── Special Memories (Stage 2) — kỷ niệm có cấu trúc, family-scoped ───────────
# Khai báo TRƯỚC /{memory_id} để literal path không bị capture.
_SPECIAL_KIND_LABELS = {
    "birthday": "sinh nhật", "milestone": "cột mốc",
    "favorite": "sở thích", "other": "kỷ niệm",
}


_DATE_PAIR_RE = re.compile(r"(\d{1,2})\s*[/\-.]\s*(\d{1,2})")


def _memory_due_today(memory_date: str, day: int, month: int) -> bool:
    """True nếu `memory_date` (free-text) khớp ngày/tháng hôm nay.
    Hỗ trợ 'D/M', 'DD/MM', 'DD/MM/YYYY', 'DD-MM', 'DD.MM' (ngày trước, tháng sau)."""
    if not memory_date:
        return False
    for d_str, m_str in _DATE_PAIR_RE.findall(memory_date):
        try:
            if int(d_str) == day and int(m_str) == month:
                return True
        except ValueError:
            continue
    return False


def _annotate_special_memories_due_today(memories: list[dict], now: datetime) -> list[dict]:
    for memory in memories:
        memory["due_today"] = _memory_due_today(
            memory.get("memory_date", ""),
            now.day,
            now.month,
        )
    return memories


def _record_due_special_memory_events(family_id: str, now: datetime | None = None) -> dict:
    """Create one unread Parent App event per due special memory per local day."""
    fid = ensure_family_exists(family_id)
    current = now or datetime.now()
    memories = _annotate_special_memories_due_today(list_special_memories(fid), current)
    due_memories = [m for m in memories if m.get("due_today")]
    created_events: list[dict] = []
    today_key = current.date().isoformat()
    timestamp = _now_iso()

    with get_db_connection() as conn:
        for memory in due_memories:
            memory_id = str(memory.get("memory_id") or "")
            if not memory_id:
                continue
            event_id = f"special-memory-{memory_id}-{today_key}"
            import_key = f"special-memory-due:{fid}:{memory_id}:{today_key}"
            title = str(memory.get("title") or "").strip() or "Kỷ niệm"
            metadata = {
                "memory_id": memory_id,
                "kind": memory.get("kind") or "other",
                "title": title,
                "memory_date": memory.get("memory_date") or "",
                "note": memory.get("note") or "",
                "source": "special_memories",
            }
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    family_id, event_id, timestamp, type, message, clip_path,
                    metadata_json, is_read, import_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fid,
                    event_id,
                    timestamp,
                    "special_memory_due",
                    f"Hôm nay có kỷ niệm: {title}",
                    None,
                    _dump_json(metadata),
                    0,
                    import_key,
                ),
            )
            if cur.rowcount > 0:
                created_events.append(
                    {
                        "id": event_id,
                        "family_id": fid,
                        "timestamp": timestamp,
                        "type": "special_memory_due",
                        "message": f"Hôm nay có kỷ niệm: {title}",
                        "metadata": metadata,
                        "read": False,
                    }
                )
        conn.commit()

    return {
        "ok": True,
        "due_count": len(due_memories),
        "created_count": len(created_events),
        "events": created_events,
        "due_today": due_memories,
    }


@router.get("/api/memories/special")
async def list_special(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    now = datetime.now()
    memories = _annotate_special_memories_due_today(list_special_memories(family_id), now)
    return {"memories": memories, "due_today": [m for m in memories if m["due_today"]]}


@router.post("/api/memories/special")
async def add_special(body: SpecialMemoryIn, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    mem = add_special_memory(
        family_id, body.title, kind=body.kind,
        memory_date=body.memory_date, note=body.note,
    )
    # Nạp vào RAG (best-effort) để robot có thể nhắc lại trong hội thoại.
    if _state._rag:
        try:
            label = _SPECIAL_KIND_LABELS.get(mem["kind"], "kỷ niệm")
            parts = [f"Kỷ niệm đặc biệt ({label}): {mem['title']}"]
            if mem["memory_date"]:
                parts.append(f"ngày {mem['memory_date']}")
            if mem["note"]:
                parts.append(mem["note"])
            _state._rag.add_manual_memory(". ".join(parts), source="special", family_id=family_id)
        except Exception:
            logger.warning("[SpecialMemory] không nạp được vào RAG (bỏ qua)")
    return {"ok": True, "memory": mem}


@router.post("/api/memories/special/remind-due")
async def remind_due_special(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    return _record_due_special_memory_events(family_id)


@router.delete("/api/memories/special/{memory_id}")
async def remove_special(memory_id: str, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    if not delete_special_memory(family_id, memory_id):
        raise HTTPException(404, "Không tìm thấy kỷ niệm")
    return {"ok": True, "memory_id": memory_id}


@router.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "update")
    if not _state._rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _state._rag.update_memory(memory_id, body.text, family_id=family_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


@router.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "delete")
    if not _state._rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _state._rag.delete_memory(memory_id, family_id=family_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


# ── REST: Puppet ──────────────────────────────────────────────────────────

@router.post("/api/puppet")
async def puppet_say(body: PuppetIn, _current_user: dict = Depends(get_current_user)):
    import logging as _logging
    _logger = _logging.getLogger("api_server")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text không được rỗng")
    _state._puppet_queue.put(text)
    _logger.debug("[Puppet] Queued text_len=%d", len(text))
    return {"status": "queued", "text": text}


# ── REST: Tasks ───────────────────────────────────────────────────────────

@router.get("/api/tasks")
async def get_tasks(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if not _state._task_manager:
        return []
    return _state._task_manager.get_all(family_id=family_id)


@router.post("/api/tasks")
async def add_task(
    body: TaskCreate,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not _state._task_manager:
        raise HTTPException(503, "Task manager chưa khởi động")
    return _state._task_manager.add_task(body.name, body.remind_time, family_id=family_id)


# stars phải đứng trước /{task_id} để không bị capture
@router.get("/api/tasks/stars")
async def get_stars(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    return {
        "total_stars": (
            _state._task_manager.get_total_stars(family_id=family_id)
            if _state._task_manager else 0
        )
    }


@router.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str, _current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._task_manager and _state._task_manager.complete_task(task_id, family_id=family_id):
        return {"ok": True, "stars": _state._task_manager.get_total_stars(family_id=family_id)}
    raise HTTPException(404, "Task không tìm thấy hoặc đã hoàn thành")


@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, _current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._task_manager and _state._task_manager.delete_task(task_id, family_id=family_id):
        return {"ok": True}
    raise HTTPException(404, "Task không tìm thấy")
