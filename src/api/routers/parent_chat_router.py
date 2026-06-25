"""
parent_chat_router.py — Parent ↔ Bi text chat endpoints.

GET  /api/parent-chat        — conversation history (newest first)
POST /api/parent-chat/send   — send a message, get Bi's reply
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import get_db_connection
from src.api.routers.conversation_router import _require_family

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_MSG_LEN = 1000
_MAX_REPLY_LEN = 2000
_HISTORY_TURNS = 6          # last N exchanges fed to AI for context
_PARENT_CHAT_EVENT_TYPE = "parent_chat"


class ParentChatSend(BaseModel):
    message: str = Field(..., min_length=1, max_length=_MAX_MSG_LEN)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_chat_event(family_id: str, chat_id: str, parent_msg: str, bi_reply: str) -> None:
    import json
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO events (event_id, family_id, type, message, metadata_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                family_id,
                _PARENT_CHAT_EVENT_TYPE,
                parent_msg[:_MAX_MSG_LEN],
                json.dumps(
                    {"parent": parent_msg[:_MAX_MSG_LEN], "bi": bi_reply[:_MAX_REPLY_LEN]},
                    ensure_ascii=False,
                ),
                _utc_now(),
            ),
        )
        conn.commit()


def _fetch_chat_history(family_id: str, limit: int) -> list[dict]:
    import json
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT event_id, metadata_json, timestamp
            FROM events
            WHERE family_id = ? AND type = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (family_id, _PARENT_CHAT_EVENT_TYPE, limit),
        ).fetchall()
    result = []
    for row in rows:
        try:
            payload = json.loads(row["metadata_json"] or "{}")
        except Exception:
            payload = {}
        result.append(
            {
                "chat_id": row["event_id"],
                "parent": payload.get("parent", ""),
                "bi": payload.get("bi", ""),
                "created_at": row["timestamp"],
            }
        )
    return result


@router.get("/api/parent-chat")
async def get_parent_chat_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    chats = _fetch_chat_history(family_id, limit)
    return {"chats": chats, "total": len(chats)}


@router.post("/api/parent-chat/send")
async def send_parent_chat(
    body: ParentChatSend,
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    parent_msg = body.message.strip()
    if not parent_msg:
        raise HTTPException(status_code=422, detail="message không được trống")

    # Build conversation context from recent history
    history = _fetch_chat_history(family_id, _HISTORY_TURNS)
    messages: list[dict] = []
    for entry in reversed(history):          # oldest first for context
        if entry["parent"]:
            messages.append({"role": "user", "content": entry["parent"]})
        if entry["bi"]:
            messages.append({"role": "assistant", "content": entry["bi"]})
    messages.append({"role": "user", "content": parent_msg})

    # Call AI engine — collect full response, no streaming needed for REST
    try:
        from src.ai.ai_engine import stream_chat

        def _collect() -> str:
            out = ""
            for token in stream_chat(messages, role="parent_advisor"):
                out += token
                if len(out) >= _MAX_REPLY_LEN:
                    break
            return out.strip()

        # M-NEW-8: stream_chat đồng bộ → threadpool để không block event loop.
        full_reply = await run_in_threadpool(_collect)
        if not full_reply:
            full_reply = "Bi chưa hiểu câu hỏi. Bạn có thể hỏi lại không?"
    except Exception as exc:
        logger.warning("[ParentChat] AI error: %s", exc)
        raise HTTPException(status_code=503, detail="AI tạm thời không khả dụng")

    chat_id = uuid.uuid4().hex
    try:
        _store_chat_event(family_id, chat_id, parent_msg, full_reply)
    except Exception:
        logger.exception("[ParentChat] failed to store event")

    return {"ok": True, "chat_id": chat_id, "reply": full_reply}
