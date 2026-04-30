"""Story API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.entertainment.story_engine import StoryEngine
from src.infrastructure.auth.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
_ENGINE = StoryEngine()


@router.get("/api/story/list")
async def story_list(category: str | None = Query(None), _current_user: dict = Depends(get_current_user)):
    """Return story list."""
    return {"stories": _ENGINE.get_story_list(category)}


@router.post("/api/story/tell")
async def story_tell(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Tell a story by id or request."""
    try:
        payload = payload or {}
        return _ENGINE.tell_story(
            payload.get("story_id"),
            payload.get("custom_request"),
            payload.get("character_name"),
        )
    except Exception:
        logger.exception("[StoryRouter] tell failed")
        raise HTTPException(status_code=500, detail="Khong the ke chuyen")


@router.post("/api/story/personalized")
async def story_personalized(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Tell a personalized story."""
    payload = payload or {}
    return _ENGINE.tell_personalized_story(payload.get("child_name", "Bi"), payload.get("interests", []))


@router.post("/api/story/bedtime")
async def story_bedtime(_current_user: dict = Depends(get_current_user)):
    """Tell a bedtime story."""
    return _ENGINE.get_bedtime_story()
