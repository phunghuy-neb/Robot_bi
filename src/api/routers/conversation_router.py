"""
conversation_router.py — Conversation Threads endpoints cho Robot Bi API.
  GET    /api/conversations                        — Danh sách sessions
  GET    /api/conversations/homework               — Danh sách sessions bài tập
  GET    /api/conversations/{session_id}           — Chi tiết session + turns
  DELETE /api/conversations/{session_id}           — Xóa session
  POST   /api/conversations/{session_id}/homework  — Đánh dấu session bài tập
"""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import (
    ensure_family_exists,
    get_db_connection,
    get_homework_sessions,
    get_session_turns,
    mark_session_homework,
)

router = APIRouter()


def _require_family(current_user: dict) -> str:
    fid = current_user.get("family_name")
    if not fid:
        raise HTTPException(status_code=403, detail="Token thieu family_name")
    return fid


class ParentChatMessageIn(BaseModel):
    session_id: str | None = Field(default=None, max_length=80)
    role: str = Field(..., max_length=20)
    content: str = Field(..., min_length=1, max_length=4000)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parent_session_to_dict(row) -> dict:
    return {
        "session_id": row["session_id"],
        "title": row["title"] or "Parent chat",
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "message_count": int(row["message_count"] or 0),
    }


def _parent_message_to_dict(row) -> dict:
    return {
        "message_id": row["message_id"],
        "role": row["role"],
        "content": row["content"],
        "timestamp": row["timestamp"],
    }


def _load_parent_chat(family_id: str, session_id: str) -> dict:
    with get_db_connection() as conn:
        session = conn.execute(
            """
            SELECT session_id, title, started_at, ended_at, message_count
            FROM parent_chat_sessions
            WHERE family_id = ? AND session_id = ?
            """,
            (family_id, session_id),
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Parent chat session not found")
        messages = conn.execute(
            """
            SELECT message_id, role, content, timestamp
            FROM parent_chat_messages
            WHERE family_id = ? AND session_id = ?
            ORDER BY timestamp ASC
            """,
            (family_id, session_id),
        ).fetchall()
    return {
        "session": _parent_session_to_dict(session),
        "messages": [_parent_message_to_dict(row) for row in messages],
    }


@router.get("/api/conversations")
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT session_id, title, started_at, ended_at, turn_count
            FROM conversations
            WHERE family_id = ?
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (family_id, limit, offset),
        ).fetchall()
        total_row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM conversations
            WHERE family_id = ?
            """,
            (family_id,),
        ).fetchone()

    conversations = [
        {
            "session_id": row["session_id"],
            "title": row["title"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "turn_count": row["turn_count"],
        }
        for row in rows
    ]
    total = int(total_row["total"]) if total_row else 0
    return {"conversations": conversations, "total": total}


@router.get("/api/conversations/homework")
async def list_homework_conversations(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    sessions = get_homework_sessions(family_id, limit, offset)
    with get_db_connection() as conn:
        total_row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM conversations
            WHERE family_id = ? AND is_homework = 1
            """,
            (family_id,),
        ).fetchone()
    total = int(total_row["total"] or 0) if total_row else 0
    return {"sessions": sessions, "total": total}


@router.get("/api/conversations/parent")
async def list_parent_chat_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT session_id, title, started_at, ended_at, message_count
            FROM parent_chat_sessions
            WHERE family_id = ?
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (family_id, limit, offset),
        ).fetchall()
        total_row = conn.execute(
            "SELECT COUNT(*) AS total FROM parent_chat_sessions WHERE family_id = ?",
            (family_id,),
        ).fetchone()
    return {
        "sessions": [_parent_session_to_dict(row) for row in rows],
        "total": int(total_row["total"] or 0) if total_row else 0,
    }


@router.post("/api/conversations/parent/messages")
async def add_parent_chat_message(
    payload: ParentChatMessageIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = ensure_family_exists(_require_family(_current_user))
    user_id = str(_current_user.get("user_id") or "")
    role = (payload.role or "").strip().lower()
    if role not in {"parent", "bi"}:
        raise HTTPException(status_code=422, detail="role must be parent or bi")
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="content must not be empty")
    if len(content) > 4000:
        raise HTTPException(status_code=422, detail="content length must be <= 4000")

    now = _utc_now_iso()
    session_id = (payload.session_id or "").strip()
    with get_db_connection() as conn:
        if session_id:
            row = conn.execute(
                """
                SELECT session_id
                FROM parent_chat_sessions
                WHERE family_id = ? AND session_id = ?
                """,
                (family_id, session_id),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Parent chat session not found")
        else:
            session_id = uuid4().hex
            conn.execute(
                """
                INSERT INTO parent_chat_sessions (
                    session_id, family_id, user_id, title, started_at, ended_at, message_count
                ) VALUES (?, ?, ?, ?, ?, NULL, 0)
                """,
                (session_id, family_id, user_id, "Parent chat", now),
            )

        conn.execute(
            """
            INSERT INTO parent_chat_messages (
                message_id, session_id, family_id, role, content, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (uuid4().hex, session_id, family_id, role, content, now),
        )
        conn.execute(
            """
            UPDATE parent_chat_sessions
            SET message_count = message_count + 1
            WHERE family_id = ? AND session_id = ?
            """,
            (family_id, session_id),
        )
        conn.commit()
    return _load_parent_chat(family_id, session_id)


@router.get("/api/conversations/parent/{session_id}")
async def get_parent_chat_session(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    return _load_parent_chat(family_id, session_id)


@router.get("/api/conversations/{session_id}")
async def get_conversation(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT session_id, family_id, title, started_at, ended_at, turn_count
            FROM conversations
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, family_id),
        ).fetchone()

    if not row:
        raise HTTPException(404, "Conversation khong tim thay")

    return {
        "session": {
            "session_id": row["session_id"],
            "family_id": row["family_id"],
            "title": row["title"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "turn_count": row["turn_count"],
        },
        "turns": get_session_turns(session_id, family_id=family_id),
    }


@router.delete("/api/conversations/{session_id}")
async def delete_conversation(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT session_id
            FROM conversations
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, family_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Conversation khong tim thay")

        conn.execute(
            """
            DELETE FROM turns
            WHERE session_id IN (
                SELECT session_id FROM conversations
                WHERE session_id = ? AND family_id = ?
            )
            """,
            (session_id, family_id),
        )
        conn.execute(
            "DELETE FROM conversations WHERE session_id = ? AND family_id = ?",
            (session_id, family_id),
        )
        conn.commit()

    return {"ok": True}


@router.post("/api/conversations/{session_id}/homework")
async def mark_homework_conversation(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT session_id
            FROM conversations
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, family_id),
        ).fetchone()

    if not row:
        raise HTTPException(404, "Conversation khong tim thay")

    ok = mark_session_homework(session_id, family_id=family_id)
    if not ok:
        raise HTTPException(404, "Conversation khong tim thay")
    return {"ok": True}
