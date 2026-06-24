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

from src.config import env_admin
from src.entertainment.youtube_lessons import youtube_lessons
from src.safety import safety_filter as sf
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
    rag_cleaned = True
    if _state._rag:
        result = _state._rag.clear_all_memories(family_id=family_id)
        if not result:
            rag_cleaned = False
            logger.warning(
                "[Admin] ChromaDB cleanup failed for family %s - "
                "DB deleted but memories may remain (family_id reuse could inherit them)",
                family_id,
            )
    # Báo rõ trạng thái cleanup RAG (L-NEW-7 r35) để admin biết có memory mồ côi cần dọn.
    return {"ok": True, "family_id": family_id, "rag_cleaned": rag_cleaned}


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


# ── Config: public API keys + feature toggles (admin) ─────────────────────────
class KeyValue(BaseModel):
    value: str = Field(default="", max_length=400)


class ToggleValue(BaseModel):
    enabled: bool


@router.get("/api/admin/config/keys")
async def get_public_keys(_admin: dict = Depends(require_admin)):
    # Chỉ trạng thái + masked; KHÔNG trả giá trị thật, KHÔNG có key LLM.
    return {"keys": env_admin.keys_status()}


@router.post("/api/admin/config/keys/{name}")
async def set_public_key(name: str, body: KeyValue, _admin: dict = Depends(require_admin)):
    try:
        env_admin.write_env_var(name, body.value.strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "name": name}


@router.delete("/api/admin/config/keys/{name}")
async def clear_public_key(name: str, _admin: dict = Depends(require_admin)):
    try:
        env_admin.write_env_var(name, "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "name": name}


@router.post("/api/admin/config/keys/{name}/test")
async def test_public_key(name: str, _admin: dict = Depends(require_admin)):
    return env_admin.test_key(name)


@router.get("/api/admin/config/toggles")
async def get_toggles(_admin: dict = Depends(require_admin)):
    return {"toggles": env_admin.toggles_status()}


@router.post("/api/admin/config/toggles/{name}")
async def set_toggle(name: str, body: ToggleValue, _admin: dict = Depends(require_admin)):
    try:
        env_admin.write_env_var(name, "true" if body.enabled else "false")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "name": name, "enabled": body.enabled}


# ── YouTube: allowlist GLOBAL (admin — mọi gia đình thấy) ──────────────────────
class GlobalYouTubeChannel(BaseModel):
    channel_id: str = Field(..., min_length=10, max_length=64)
    label: str = Field(default="", max_length=120)
    language: str = Field(default="vi", max_length=20)
    age_min: int = Field(default=5, ge=0, le=18)
    age_max: int = Field(default=12, ge=0, le=18)
    tags: list[str] = Field(default_factory=list, max_length=12)


@router.get("/api/admin/youtube/channels")
async def admin_list_global_channels(_admin: dict = Depends(require_admin)):
    """Allowlist kênh YouTube GLOBAL (mọi gia đình đều thấy video từ các kênh này)."""
    return {
        "channels": youtube_lessons.list_global_channels(),
        "available": youtube_lessons.available,
        "enabled": youtube_lessons.enabled,
        "has_key": youtube_lessons._has_key,
    }


@router.post("/api/admin/youtube/channels")
async def admin_add_global_channel(body: GlobalYouTubeChannel, _admin: dict = Depends(require_admin)):
    try:
        channel = youtube_lessons.add_global_channel(body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True, "channel": channel}


@router.delete("/api/admin/youtube/channels/{channel_id}")
async def admin_remove_global_channel(channel_id: str, _admin: dict = Depends(require_admin)):
    if not youtube_lessons.remove_global_channel(channel_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy kênh trong allowlist global")
    return {"ok": True, "channel_id": channel_id.strip()}


# ── An toàn trẻ (admin — GLOBAL): blocklist + chủ đề cấm + chính sách + theo dõi ─
class WordList(BaseModel):
    words: list[str] = Field(default_factory=list, max_length=500)


class TopicList(BaseModel):
    topics: list[str] = Field(default_factory=list, max_length=500)


class _AgePolicy(BaseModel):
    min_age: int = Field(default=5, ge=0, le=18)
    max_age: int = Field(default=12, ge=0, le=18)
    strict_mode: bool = True


class _TimePolicy(BaseModel):
    daily_limit_minutes: int = Field(default=60, ge=1, le=480)
    warning_minutes: int = Field(default=10, ge=0, le=120)
    reset_time: str = Field(default="00:00", max_length=5)


class _SleepPolicy(BaseModel):
    start_time: str = Field(default="21:00", max_length=5)
    end_time: str = Field(default="06:30", max_length=5)


class SafetyPolicyIn(BaseModel):
    age: _AgePolicy | None = None
    time: _TimePolicy | None = None
    sleep: _SleepPolicy | None = None


_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


@router.get("/api/admin/safety/config")
async def get_safety_config(_admin: dict = Depends(require_admin)):
    return sf.get_safety_config_full()


@router.post("/api/admin/safety/blocklist")
async def set_safety_blocklist(body: WordList, _admin: dict = Depends(require_admin)):
    words = sf.set_blocklist_words([w for w in body.words if len(w) <= 60])
    return {"ok": True, "blocklist_words": words}


@router.post("/api/admin/safety/topics")
async def set_safety_topics(body: TopicList, _admin: dict = Depends(require_admin)):
    topics = sf.set_blocked_topics([t for t in body.topics if len(t) <= 80])
    return {"ok": True, "blocked_topics": topics}


@router.post("/api/admin/safety/policy")
async def set_safety_policy(body: SafetyPolicyIn, _admin: dict = Depends(require_admin)):
    incoming: dict = {}
    if body.age is not None:
        if body.age.min_age > body.age.max_age:
            raise HTTPException(status_code=422, detail="min_age phải ≤ max_age")
        incoming["age"] = body.age.model_dump()
    if body.time is not None:
        if body.time.warning_minutes > body.time.daily_limit_minutes:
            raise HTTPException(status_code=422, detail="warning_minutes phải ≤ daily_limit_minutes")
        if not _HHMM_RE.match(body.time.reset_time):
            raise HTTPException(status_code=422, detail="reset_time phải dạng HH:MM")
        incoming["time"] = body.time.model_dump()
    if body.sleep is not None:
        if not _HHMM_RE.match(body.sleep.start_time) or not _HHMM_RE.match(body.sleep.end_time):
            raise HTTPException(status_code=422, detail="start_time/end_time phải dạng HH:MM")
        incoming["sleep"] = body.sleep.model_dump()
    policy = sf.set_global_policy(incoming)
    return {"ok": True, "policy": policy}


@router.get("/api/admin/safety/stats")
async def get_safety_stats(limit: int = Query(default=50, ge=1, le=200), _admin: dict = Depends(require_admin)):
    return sf.get_safety_stats(limit)


@router.post("/api/admin/safety/stats/reset")
async def reset_safety_stats(_admin: dict = Depends(require_admin)):
    sf.reset_safety_stats()
    return {"ok": True}


# ── Nội dung GLOBAL: radio / video / game metadata (admin) ────────────────────
_CONTENT_TYPES = {"radio", "video", "game"}


class ContentItemIn(BaseModel):
    type: str = Field(..., max_length=20)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    source_url: str = Field(default="", max_length=600)
    thumbnail_url: str = Field(default="", max_length=600)
    age_min: int = Field(default=5, ge=0, le=18)
    age_max: int = Field(default=12, ge=0, le=18)
    language: str = Field(default="vi", max_length=20)
    tags: list[str] = Field(default_factory=list, max_length=20)
    enabled: bool = True
    sort_order: int = Field(default=0, ge=0, le=100000)


def _content_row(row) -> dict:
    import json as _json
    try:
        tags = _json.loads(row["tags_json"] or "[]")
    except Exception:
        tags = []
    return {
        "content_id": row["content_id"],
        "family_id": row["family_id"],
        "type": row["type"],
        "title": row["title"],
        "description": row["description"],
        "source_url": row["source_url"],
        "thumbnail_url": row["thumbnail_url"],
        "age_min": row["age_min"],
        "age_max": row["age_max"],
        "language": row["language"],
        "tags": tags if isinstance(tags, list) else [],
        "enabled": bool(row["enabled"]),
        "sort_order": row["sort_order"],
        "scope": "global" if row["family_id"] is None else "family",
    }


@router.get("/api/admin/content")
async def admin_list_content(
    type: Optional[str] = Query(default=None, max_length=20),
    _admin: dict = Depends(require_admin),
):
    where, params = [], []
    if type:
        if type not in _CONTENT_TYPES:
            raise HTTPException(status_code=422, detail="type phải là radio/video/game")
        where.append("type = ?")
        params.append(type)
    sql = "SELECT * FROM content_items"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY type, sort_order, created_at"
    with get_db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"items": [_content_row(r) for r in rows]}


@router.post("/api/admin/content")
async def admin_create_content(body: ContentItemIn, _admin: dict = Depends(require_admin)):
    import json as _json
    from uuid import uuid4
    if body.type not in _CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="type phải là radio/video/game")
    if body.age_min > body.age_max:
        raise HTTPException(status_code=422, detail="age_min phải ≤ age_max")
    cid = f"adm-{body.type}-{uuid4().hex[:10]}"
    now = _utc_now_iso()
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO content_items
               (content_id, family_id, type, title, description, source_url, thumbnail_url,
                age_min, age_max, language, tags_json, enabled, sort_order, created_at, updated_at)
               VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, body.type, body.title, body.description, body.source_url, body.thumbnail_url,
             body.age_min, body.age_max, body.language,
             _json.dumps([str(t).lower() for t in body.tags], ensure_ascii=False),
             1 if body.enabled else 0, body.sort_order, now, now),
        )
        conn.commit()
    return {"ok": True, "content_id": cid}


@router.post("/api/admin/content/{content_id}")
async def admin_update_content(content_id: str, body: ContentItemIn, _admin: dict = Depends(require_admin)):
    import json as _json
    if body.type not in _CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="type phải là radio/video/game")
    if body.age_min > body.age_max:
        raise HTTPException(status_code=422, detail="age_min phải ≤ age_max")
    with get_db_connection() as conn:
        if not conn.execute("SELECT 1 FROM content_items WHERE content_id = ?", (content_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Không tìm thấy nội dung")
        conn.execute(
            """UPDATE content_items SET type=?, title=?, description=?, source_url=?, thumbnail_url=?,
               age_min=?, age_max=?, language=?, tags_json=?, enabled=?, sort_order=?, updated_at=?
               WHERE content_id=?""",
            (body.type, body.title, body.description, body.source_url, body.thumbnail_url,
             body.age_min, body.age_max, body.language,
             _json.dumps([str(t).lower() for t in body.tags], ensure_ascii=False),
             1 if body.enabled else 0, body.sort_order, _utc_now_iso(), content_id),
        )
        conn.commit()
    return {"ok": True, "content_id": content_id}


@router.delete("/api/admin/content/{content_id}")
async def admin_delete_content(content_id: str, _admin: dict = Depends(require_admin)):
    with get_db_connection() as conn:
        cur = conn.execute("DELETE FROM content_items WHERE content_id = ?", (content_id,))
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy nội dung")
    return {"ok": True, "content_id": content_id}


# ── Thống kê tổng quan (admin) ────────────────────────────────────────────────
@router.get("/api/admin/stats")
async def admin_overview_stats(_admin: dict = Depends(require_admin)):
    def _count(conn, sql, params=()):
        try:
            return conn.execute(sql, params).fetchone()[0]
        except Exception:
            return 0

    with get_db_connection() as conn:
        users_total = _count(conn, "SELECT COUNT(*) FROM users")
        users_admin = _count(conn, "SELECT COUNT(*) FROM users WHERE is_admin = 1")
        users_active = _count(conn, "SELECT COUNT(*) FROM users WHERE is_active = 1")
        families = _count(conn, "SELECT COUNT(*) FROM families")
        conversations = _count(conn, "SELECT COUNT(*) FROM conversations")
        exam_papers = _count(conn, "SELECT COUNT(*) FROM exam_papers")
        exam_global = _count(conn, "SELECT COUNT(*) FROM exam_papers WHERE family_id IS NULL")
        exam_sessions = _count(conn, "SELECT COUNT(*) FROM exam_sessions")
        questions = _count(conn, "SELECT COUNT(*) FROM question_bank WHERE status = 'published'")
        content_radio = _count(conn, "SELECT COUNT(*) FROM content_items WHERE type = 'radio'")
        content_video = _count(conn, "SELECT COUNT(*) FROM content_items WHERE type = 'video'")
        content_game = _count(conn, "SELECT COUNT(*) FROM content_items WHERE type = 'game'")
        yt_family = _count(conn, "SELECT COUNT(*) FROM youtube_channels")

    safety = sf.get_safety_stats(1)["counts"]
    return {
        "users": {"total": users_total, "admins": users_admin, "active": users_active},
        "families": families,
        "conversations": conversations,
        "exams": {"papers": exam_papers, "global": exam_global, "sessions": exam_sessions, "questions": questions},
        "content": {"radio": content_radio, "video": content_video, "game": content_game},
        "youtube": {"global": len(youtube_lessons.list_global_channels()), "family": yt_family},
        "safety": safety,
    }


# ── Persona MẶC ĐỊNH GLOBAL của Bi (admin) ────────────────────────────────────
class GlobalPersonaIn(BaseModel):
    name: str | None = Field(default=None, max_length=40)
    gender: str | None = Field(default=None, max_length=10)
    voice: str | None = Field(default=None, max_length=60)
    language: str | None = Field(default=None, max_length=5)
    personality: dict | None = None


@router.get("/api/admin/persona")
async def get_global_persona(_admin: dict = Depends(require_admin)):
    """Persona mặc định GLOBAL — gia đình chưa tự cấu hình sẽ kế thừa.
    (Role/vai trò là contextual theo hội thoại, không có cấu hình global.)"""
    from src.ai.persona_manager import GLOBAL_PERSONA_FAMILY, PersonaManager
    return {"persona": PersonaManager(GLOBAL_PERSONA_FAMILY).get_persona()}


@router.post("/api/admin/persona")
async def set_global_persona(body: GlobalPersonaIn, _admin: dict = Depends(require_admin)):
    from src.ai.persona_manager import GLOBAL_PERSONA_FAMILY, PersonaManager
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="Không có trường nào để cập nhật")
    manager = PersonaManager(GLOBAL_PERSONA_FAMILY)
    if not manager.save(updates):
        raise HTTPException(status_code=422, detail="Persona không hợp lệ")
    return {"ok": True, "persona": manager.get_persona()}


# ── Radio Browser: tìm đài để admin DUYỆT thêm vào nội dung (admin) ────────────
@router.get("/api/admin/radio/search")
async def admin_radio_search(
    q: str = Query(..., min_length=1, max_length=80),
    limit: int = Query(15, ge=1, le=40),
    _admin: dict = Depends(require_admin),
):
    """Tìm ứng viên đài radio (radio-browser.info) để admin xem xét rồi tự thêm vào
    /api/admin/content (type=radio). KHÔNG tự thêm — admin là người duyệt cuối."""
    from src.knowledge import knowledge_client as kc
    return kc.radio_search(q, limit)
