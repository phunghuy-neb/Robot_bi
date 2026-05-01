"""Education API routes for flashcards and learning summaries."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.routers.conversation_router import _require_family
from src.education.curriculum import Curriculum
from src.education.flashcard_engine import FlashcardEngine
from src.infrastructure.auth.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
_ENGINES: dict[str, FlashcardEngine] = {}


def _engine_for(family_id: str) -> FlashcardEngine:
    """Return cached flashcard engine for family."""
    engine = _ENGINES.get(family_id)
    if engine is None:
        engine = FlashcardEngine(family_id)
        _ENGINES[family_id] = engine
    return engine


@router.post("/api/education/flashcard/start")
async def start_flashcard(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Start a flashcard session."""
    try:
        family_id = _require_family(_current_user)
        payload = payload or {}
        return _engine_for(family_id).start_session(
            payload.get("subject", "english"),
            payload.get("topic", "animals"),
            payload.get("language", "en"),
            payload.get("difficulty", "easy"),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("[EducationRouter] start flashcard failed")
        raise HTTPException(status_code=500, detail="Khong the bat dau flashcard")


@router.get("/api/education/flashcard/next")
async def next_flashcard(_current_user: dict = Depends(get_current_user)):
    """Return next flashcard."""
    try:
        return _engine_for(_require_family(_current_user)).get_next_card()
    except HTTPException:
        raise
    except Exception:
        logger.exception("[EducationRouter] next flashcard failed")
        raise HTTPException(status_code=500, detail="Khong the lay flashcard")


@router.post("/api/education/flashcard/answer")
async def answer_flashcard(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Submit flashcard answer."""
    try:
        family_id = _require_family(_current_user)
        payload = payload or {}
        return _engine_for(family_id).submit_answer(
            payload.get("card_id", ""),
            bool(payload.get("is_correct", False)),
            payload.get("pronunciation_score"),
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("[EducationRouter] answer flashcard failed")
        raise HTTPException(status_code=500, detail="Khong the nop cau tra loi")


@router.post("/api/education/flashcard/end")
async def end_flashcard(_current_user: dict = Depends(get_current_user)):
    """End flashcard session."""
    try:
        return _engine_for(_require_family(_current_user)).end_session()
    except HTTPException:
        raise
    except Exception:
        logger.exception("[EducationRouter] end flashcard failed")
        raise HTTPException(status_code=500, detail="Khong the ket thuc flashcard")


@router.get("/api/education/summary")
async def education_summary(_current_user: dict = Depends(get_current_user)):
    """Return education summary fields expected by the parent app."""
    family_id = _require_family(_current_user)
    try:
        from src.education.progress_tracker import ProgressTracker

        tracker = ProgressTracker()
        overall = tracker.get_overall_progress(family_id)
        streak = tracker.get_streak(family_id)
        en_progress = tracker.get_subject_progress(family_id, "english")
        math_progress = tracker.get_subject_progress(family_id, "math")
        sci_progress = tracker.get_subject_progress(family_id, "science")
    except Exception:
        overall = {}
        streak = 0
        en_progress = math_progress = sci_progress = {}

    total_correct = int(overall.get("correct", 0) or 0)
    total_incorrect = int(overall.get("incorrect", 0) or 0)
    return {
        "streak": streak,
        "words_learned": total_correct,
        "math_solved": int(math_progress.get("correct", 0) or 0),
        "questions_answered": total_correct + total_incorrect,
        "subject_progress": {
            "english": en_progress.get("accuracy", 0),
            "math": math_progress.get("accuracy", 0),
            "science": sci_progress.get("accuracy", 0),
        },
    }


@router.get("/api/education/vocabulary")
async def education_vocabulary(_current_user: dict = Depends(get_current_user)):
    """Return vocabulary review cards."""
    family_id = _require_family(_current_user)
    return {"words": _engine_for(family_id).get_review_cards()}


@router.get("/api/education/schedule")
async def get_education_schedule(_current_user: dict = Depends(get_current_user)):
    """Return saved education schedule."""
    family_id = _require_family(_current_user)
    curriculum = Curriculum()
    return {"schedule": curriculum.get_schedule(family_id)}


@router.post("/api/education/schedule")
async def update_education_schedule(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Update education schedule."""
    family_id = _require_family(_current_user)
    payload = payload or {}
    if isinstance(payload.get("schedule"), dict):
        schedule = payload["schedule"]
    elif "day" in payload:
        curriculum = Curriculum()
        schedule = curriculum.get_schedule(family_id)
        schedule[str(payload.get("day"))] = {
            "subject": payload.get("subject"),
            "time": payload.get("time"),
        }
    else:
        schedule = payload
    curriculum = Curriculum()
    ok = curriculum.update_schedule(family_id, schedule)
    if not ok:
        raise HTTPException(status_code=500, detail="Khong the luu lich hoc")
    return {"ok": True, "schedule": curriculum.get_schedule(family_id)}
