"""
admin_router.py - Admin-only family management endpoints.
"""

import collections
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user, hash_password
from src.infrastructure.database.db import (
    create_family_record,
    delete_family_record,
    get_db_connection,
    is_user_admin,
    list_families,
)
import src.infrastructure.sessions.state as _state

logger = logging.getLogger(__name__)
router = APIRouter()

# ── In-memory log buffer ──────────────────────────────────────────────────────
_LOG_BUFFER: collections.deque = collections.deque(maxlen=500)


class _BufferHandler(logging.Handler):
    """Captures log records into _LOG_BUFFER without touching the root handler chain."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            _LOG_BUFFER.append({
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "component": record.name.split(".")[0] if record.name else "root",
                "message": self.format(record),
                "source": "application",
            })
        except Exception:
            pass


_buffer_handler = _BufferHandler()
_buffer_handler.setLevel(logging.DEBUG)
_buffer_handler.setFormatter(logging.Formatter("%(message)s"))
logging.root.addHandler(_buffer_handler)

_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_SECRET_RE = re.compile(
    r"(?i)\b(bearer\s+)[a-z0-9._~+/=-]+|"
    r"\b(api[_-]?key|jwt[_-]?secret[_-]?key|secret|token|password)\s*[:=]\s*[^,\s;]+|"
    r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"
)
_CHILD_TEXT_RE = re.compile(r"(?i)\b(child_text|child_message|content|speech)\s*[:=]\s*[^,\n;]+")


class FamilyCreate(BaseModel):
    family_id: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str | None = Field(default=None, max_length=120)


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not is_user_admin(str(current_user.get("user_id", ""))):
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_log_message(message: str) -> str:
    value = str(message or "")

    def repl_secret(match: re.Match) -> str:
        text = match.group(0)
        if text.lower().startswith("bearer "):
            return "Bearer [REDACTED]"
        return "[REDACTED]"

    value = _SECRET_RE.sub(repl_secret, value)
    value = _CHILD_TEXT_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", value)
    return value[:1000]


def _system_log_entries() -> list[dict]:
    entries = list(_LOG_BUFFER)
    return [
        {**entry, "message": _sanitize_log_message(entry["message"])}
        for entry in entries
    ]


def _parse_since(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="since must be an ISO timestamp")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@router.post("/api/admin/families")
async def create_family(body: FamilyCreate, _admin: dict = Depends(require_admin)):
    family = create_family_record(body.family_id, body.display_name)
    if family is None:
        raise HTTPException(status_code=409, detail="Family already exists")
    return family


@router.get("/api/admin/families")
async def get_families(_admin: dict = Depends(require_admin)):
    return {"families": list_families()}


@router.get("/api/admin/logs")
async def get_admin_logs(
    level: Optional[str] = Query(default=None, max_length=20),
    component: Optional[str] = Query(default=None, max_length=80),
    since: Optional[str] = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_admin),
):
    level_filter = (level or "").strip().upper()
    if level_filter and level_filter not in _LEVELS:
        raise HTTPException(status_code=422, detail="level is invalid")
    component_filter = (component or "").strip().lower()
    since_dt = _parse_since(since)

    entries = []
    for entry in _system_log_entries():
        if level_filter and entry["level"] != level_filter:
            continue
        if component_filter and entry["component"].lower() != component_filter:
            continue
        if since_dt:
            entry_dt = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            if entry_dt < since_dt:
                continue
        entries.append(entry)

    total = len(entries)
    return {
        "logs": entries[offset: offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/api/admin/families/{family_id}")
async def delete_family(family_id: str, admin: dict = Depends(require_admin)):
    if family_id == admin.get("family_name"):
        raise HTTPException(status_code=400, detail="Cannot delete current admin family")
    ok = delete_family_record(family_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Family not found")
    if _state._rag:
        result = _state._rag.clear_all_memories(family_id=family_id)
        if not result:
            logger.warning(
                "[Admin] ChromaDB cleanup failed for family %s - "
                "DB deleted but memories may remain",
                family_id,
            )
    return {"ok": True, "family_id": family_id}


# ── User account management (admin) ───────────────────────────────────────────
class SetActive(BaseModel):
    active: bool


class SetAdmin(BaseModel):
    is_admin: bool


class ResetPassword(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


def _fetch_user(conn, user_id: str):
    return conn.execute(
        "SELECT user_id, username, family_name, is_active, is_admin, created_at "
        "FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()


def _guard_not_self(admin: dict, user_id: str, action: str) -> None:
    if str(admin.get("user_id", "")) == str(user_id):
        raise HTTPException(status_code=400, detail=f"Không thể tự {action} tài khoản đang đăng nhập")


@router.get("/api/admin/users")
async def list_users(_admin: dict = Depends(require_admin)):
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT user_id, username, family_name, is_active, is_admin, created_at "
            "FROM users ORDER BY created_at ASC"
        ).fetchall()
    return {"users": [
        {
            "user_id": r["user_id"],
            "username": r["username"],
            "family_name": r["family_name"],
            "is_active": bool(r["is_active"]),
            "is_admin": bool(r["is_admin"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]}


@router.post("/api/admin/users/{user_id}/active")
async def set_user_active(user_id: str, body: SetActive, admin: dict = Depends(require_admin)):
    if not body.active:
        _guard_not_self(admin, user_id, "khóa")
    with get_db_connection() as conn:
        if not _fetch_user(conn, user_id):
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute("UPDATE users SET is_active = ? WHERE user_id = ?",
                     (1 if body.active else 0, user_id))
        conn.commit()
    return {"ok": True, "user_id": user_id, "is_active": body.active}


@router.post("/api/admin/users/{user_id}/admin")
async def set_user_admin(user_id: str, body: SetAdmin, admin: dict = Depends(require_admin)):
    if not body.is_admin:
        _guard_not_self(admin, user_id, "bỏ quyền admin của")
    with get_db_connection() as conn:
        if not _fetch_user(conn, user_id):
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute("UPDATE users SET is_admin = ? WHERE user_id = ?",
                     (1 if body.is_admin else 0, user_id))
        conn.commit()
    return {"ok": True, "user_id": user_id, "is_admin": body.is_admin}


@router.post("/api/admin/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, body: ResetPassword, _admin: dict = Depends(require_admin)):
    with get_db_connection() as conn:
        if not _fetch_user(conn, user_id):
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute("UPDATE users SET password_hash = ? WHERE user_id = ?",
                     (hash_password(body.new_password), user_id))
        # Thu hồi refresh token cũ để buộc đăng nhập lại.
        conn.execute("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,))
        conn.commit()
    return {"ok": True, "user_id": user_id}


@router.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    _guard_not_self(admin, user_id, "xóa")
    with get_db_connection() as conn:
        if not _fetch_user(conn, user_id):
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
    return {"ok": True, "user_id": user_id}
