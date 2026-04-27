"""
conversation_router.py — Conversation Threads endpoints cho Robot Bi API.
  GET    /api/conversations                        — Danh sách sessions
  GET    /api/conversations/{session_id}           — Chi tiết session + turns
  DELETE /api/conversations/{session_id}           — Xóa session
  POST   /api/conversations/{session_id}/homework  — Thêm homework turn
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src_brain.network.auth import get_current_user
from src_brain.network.db import add_turn, get_db_connection, get_session_turns

router = APIRouter()


class HomeworkTurnIn(BaseModel):
    content: str


def _require_family(current_user: dict) -> str:
    fid = current_user.get("family_name")
    if not fid:
        raise HTTPException(status_code=403, detail="Token thieu family_name")
    return fid


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
        "turns": get_session_turns(session_id),
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

        conn.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
        conn.execute(
            "DELETE FROM conversations WHERE session_id = ? AND family_id = ?",
            (session_id, family_id),
        )
        conn.commit()

    return {"ok": True}


@router.post("/api/conversations/{session_id}/homework")
async def add_homework_turn(
    session_id: str,
    body: HomeworkTurnIn,
    _current_user: dict = Depends(get_current_user),
):
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "content khong duoc rong")

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

    turn_id = add_turn(session_id, "homework", content)
    return {"turn_id": turn_id, "session_id": session_id}
