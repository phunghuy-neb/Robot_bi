"""Emotion summary API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.routers.conversation_router import _require_family
from src.emotion.emotion_analyzer import EmotionAnalyzer
from src.infrastructure.auth.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def get_weekly_summary(family_id: str) -> list[dict]:
    """Return seven-day emotion summary for a family."""
    return EmotionAnalyzer(family_id).get_weekly_summary(family_id)


@router.get("/api/emotion/today")
async def get_emotion_today(_current_user: dict = Depends(get_current_user)):
    """Return today's emotion summary for the current family."""
    try:
        family_id = _require_family(_current_user)
        return EmotionAnalyzer(family_id).get_today_summary(family_id)
    except HTTPException:
        raise
    except Exception:
        logger.exception("[EmotionRouter] today failed")
        raise HTTPException(status_code=500, detail="Khong the lay emotion hom nay")


@router.get("/api/emotion/summary")
async def get_emotion_summary(_current_user: dict = Depends(get_current_user)):
    """Return seven-day emotion summary for the current family."""
    try:
        family_id = _require_family(_current_user)
        try:
            from src.emotion.emotion_journal import EmotionJournal

            weekly = get_weekly_summary(family_id)
            journal = EmotionJournal()
            sad_streak = journal.get_streak(family_id, "sad")
            stress_streak = journal.get_streak(family_id, "stressed")
            max_streak = max(sad_streak, stress_streak)
            alert = max_streak >= 3
        except Exception:
            weekly = []
            alert = False
            max_streak = 0
        return {
            "days": weekly,
            "alert": alert,
            "alert_message": (
                f"Bé có vẻ buồn {max_streak} ngày liên tiếp 💙"
                if alert else ""
            ),
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("[EmotionRouter] summary failed")
        raise HTTPException(status_code=500, detail="Khong the lay emotion summary")
