"""Analytics and clips API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from src.api.routers.conversation_router import _require_family
from src.education.progress_tracker import ProgressTracker
from src.emotion.emotion_journal import EmotionJournal
from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter()


def _count_rows(query: str, params: tuple) -> int:
    """Run COUNT query and return integer result."""
    try:
        with get_db_connection() as conn:
            row = conn.execute(query, params).fetchone()
        if row is None:
            return 0
        return int(row[0])
    except Exception as exc:
        logger.debug("[Analytics] count query skipped: %s", exc)
        return 0


def get_weekly_analytics(family_id: str) -> dict:
    """
    Tong hop tu conversation logs, emotion journal, learning progress va tasks.

    Returns comprehensive weekly summary.
    """
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
        conversations = _count_rows(
            "SELECT COUNT(*) FROM conversations WHERE family_id = ? AND started_at >= ?",
            (family_id, since),
        )
        turns = _count_rows(
            """
            SELECT COUNT(*)
            FROM turns
            WHERE session_id IN (
                SELECT session_id FROM conversations
                WHERE family_id = ? AND started_at >= ?
            )
            """,
            (family_id, since),
        )
        tasks_completed = _count_rows(
            """
            SELECT COUNT(*)
            FROM tasks
            WHERE family_id = ? AND completed_today = 1
            """,
            (family_id,),
        )
        emotion_report = EmotionJournal().export_report(family_id)
        learning_report = ProgressTracker().generate_weekly_report(family_id)
        return {
            "family_id": family_id,
            "period_days": 7,
            "conversations": conversations,
            "turns": turns,
            "tasks_completed": tasks_completed,
            "emotion": emotion_report,
            "learning": learning_report,
        }
    except Exception:
        logger.exception("[Analytics] get_weekly_analytics failed")
        return {
            "family_id": family_id,
            "period_days": 7,
            "conversations": 0,
            "turns": 0,
            "tasks_completed": 0,
            "emotion": {},
            "learning": {},
        }


def get_daily_stats(family_id: str) -> dict:
    """Stats hom nay."""
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        conversations = _count_rows(
            "SELECT COUNT(*) FROM conversations WHERE family_id = ? AND date(started_at) = ?",
            (family_id, today),
        )
        events = _count_rows(
            "SELECT COUNT(*) FROM events WHERE family_id = ? AND date(timestamp) = ?",
            (family_id, today),
        )
        tasks_completed = _count_rows(
            "SELECT COUNT(*) FROM tasks WHERE family_id = ? AND completed_today = 1",
            (family_id,),
        )
        return {
            "family_id": family_id,
            "date": today,
            "conversations": conversations,
            "events": events,
            "tasks_completed": tasks_completed,
        }
    except Exception:
        logger.exception("[Analytics] get_daily_stats failed")
        return {"family_id": family_id, "date": datetime.now(timezone.utc).date().isoformat(), "conversations": 0, "events": 0, "tasks_completed": 0}


@router.get("/api/analytics/weekly")
async def weekly_analytics(_current_user: dict = Depends(get_current_user)):
    """Return weekly analytics for current family."""
    family_id = _require_family(_current_user)
    return get_weekly_analytics(family_id)


@router.get("/api/analytics/daily")
async def daily_analytics(_current_user: dict = Depends(get_current_user)):
    """Return daily analytics for current family."""
    family_id = _require_family(_current_user)
    return get_daily_stats(family_id)


@router.get("/api/clips/list")
async def list_clips(_current_user: dict = Depends(get_current_user)):
    """Return event clips list."""
    try:
        family_id = _require_family(_current_user)
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT event_id, timestamp, type, message, clip_path
                FROM events
                WHERE family_id = ? AND clip_path IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 100
                """,
                (family_id,),
            ).fetchall()
        return {"clips": [dict(row) for row in rows]}
    except HTTPException:
        raise
    except Exception:
        logger.exception("[Analytics] list_clips failed")
        raise HTTPException(status_code=500, detail="Khong the lay clips")


@router.delete("/api/clips/{clip_id}")
async def delete_clip(clip_id: str, _current_user: dict = Depends(get_current_user)):
    """Delete clip reference from event log."""
    try:
        family_id = _require_family(_current_user)
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE events SET clip_path = NULL WHERE family_id = ? AND event_id = ?",
                (family_id, clip_id),
            )
            conn.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        logger.exception("[Analytics] delete_clip failed")
        raise HTTPException(status_code=500, detail="Khong the xoa clip")
