"""Game API routes."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.routers.conversation_router import _require_family
from src.entertainment.game_voice_quiz import VoiceQuizGame
from src.entertainment.game_word_quiz import WordQuizGame
from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import get_db_connection

router = APIRouter()
_word_games: dict[str, WordQuizGame] = {}
_voice_games: dict[str, VoiceQuizGame] = {}


def _json_array(value) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _content_row_to_dict(row) -> dict:
    return {
        "content_id": row["content_id"],
        "type": row["type"],
        "title": row["title"],
        "description": row["description"],
        "source_url": row["source_url"],
        "thumbnail_url": row["thumbnail_url"],
        "age_min": row["age_min"],
        "age_max": row["age_max"],
        "language": row["language"],
        "tags": _json_array(row["tags_json"]),
        "enabled": bool(row["enabled"]),
    }


def _validate_child_for_family(family_id: str, child_id: Optional[str]) -> str:
    key = (child_id or "").strip()
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


def _family_content_settings(family_id: str, child_id: str) -> dict:
    with get_db_connection() as conn:
        row = None
        if child_id:
            row = conn.execute(
                """
                SELECT enabled, min_age, max_age, blocked_topics_json, allowed_topics_json
                FROM child_content_settings
                WHERE family_id = ? AND child_id = ?
                """,
                (family_id, child_id),
            ).fetchone()
        if not row:
            row = conn.execute(
                """
                SELECT enabled, min_age, max_age, blocked_topics_json, allowed_topics_json
                FROM child_content_settings
                WHERE family_id = ? AND child_id = ''
                """,
                (family_id,),
            ).fetchone()
    if not row or not row["enabled"]:
        return {"enabled": False, "blocked_topics": [], "allowed_topics": []}
    return {
        "enabled": True,
        "min_age": row["min_age"],
        "max_age": row["max_age"],
        "blocked_topics": _json_array(row["blocked_topics_json"]),
        "allowed_topics": _json_array(row["allowed_topics_json"]),
    }


def _topic_allowed(item: dict, settings: dict) -> bool:
    if not settings.get("enabled"):
        return True
    tags = {str(tag).lower() for tag in item.get("tags", [])}
    blocked = {str(tag).lower() for tag in settings.get("blocked_topics", [])}
    allowed = {str(tag).lower() for tag in settings.get("allowed_topics", [])}
    if tags & blocked:
        return False
    if allowed and not (tags & allowed):
        return False
    return True


def _list_content_items(
    family_id: str,
    content_type: str,
    language: Optional[str],
    min_age: Optional[int],
    max_age: Optional[int],
    enabled_only: bool,
    child_id: Optional[str],
) -> list[dict]:
    child_key = _validate_child_for_family(family_id, child_id)
    settings = _family_content_settings(family_id, child_key)
    if settings.get("enabled"):
        if min_age is None:
            min_age = settings.get("min_age")
        if max_age is None:
            max_age = settings.get("max_age")

    if min_age is not None and (min_age < 0 or min_age > 18):
        raise HTTPException(status_code=422, detail="min_age must be 0-18")
    if max_age is not None and (max_age < 0 or max_age > 18):
        raise HTTPException(status_code=422, detail="max_age must be 0-18")
    if min_age is not None and max_age is not None and min_age > max_age:
        raise HTTPException(status_code=422, detail="min_age must be <= max_age")

    where = ["type = ?", "(family_id IS NULL OR family_id = ?)"]
    params: list = [content_type, family_id]
    if enabled_only:
        where.append("enabled = 1")
    if language:
        where.append("language = ?")
        params.append(language.strip().lower())
    if min_age is not None:
        where.append("(age_max IS NULL OR age_max >= ?)")
        params.append(min_age)
    if max_age is not None:
        where.append("(age_min IS NULL OR age_min <= ?)")
        params.append(max_age)

    with get_db_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT content_id, family_id, type, title, description, source_url,
                   thumbnail_url, age_min, age_max, language, tags_json, enabled,
                   sort_order, created_at, updated_at
            FROM content_items
            WHERE {' AND '.join(where)}
            ORDER BY sort_order ASC, title ASC
            """,
            tuple(params),
        ).fetchall()
    items = [_content_row_to_dict(row) for row in rows]
    return [item for item in items if _topic_allowed(item, settings)]


def _content_response(alias: str, items: list[dict]) -> dict:
    return {"items": items, alias: items, "total": len(items)}


@router.get("/api/entertainment/radio")
async def list_radio_metadata(
    language: Optional[str] = Query(default=None, max_length=20),
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    enabled_only: bool = True,
    child_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    items = _list_content_items(family_id, "radio", language, min_age, max_age, enabled_only, child_id)
    return _content_response("channels", items)


@router.get("/api/entertainment/videos")
async def list_video_metadata(
    language: Optional[str] = Query(default=None, max_length=20),
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    enabled_only: bool = True,
    child_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    items = _list_content_items(family_id, "video", language, min_age, max_age, enabled_only, child_id)
    return _content_response("videos", items)


@router.get("/api/games/interactive")
async def list_interactive_game_metadata(
    language: Optional[str] = Query(default=None, max_length=20),
    min_age: Optional[int] = None,
    max_age: Optional[int] = None,
    enabled_only: bool = True,
    child_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    items = _list_content_items(family_id, "game", language, min_age, max_age, enabled_only, child_id)
    return _content_response("games", items)


@router.post("/api/game/word-quiz/start")
async def start_word_quiz(data: dict | None = None, current_user: dict = Depends(get_current_user)):
    """Start a word quiz game."""
    family_id = _require_family(current_user)
    data = data or {}
    difficulty = data.get("difficulty", "easy")
    game = WordQuizGame()
    _word_games[family_id] = game
    return game.start_game(family_id, difficulty)


@router.get("/api/game/word-quiz/question")
async def get_question(current_user: dict = Depends(get_current_user)):
    """Return the current word quiz question."""
    family_id = _require_family(current_user)
    game = _word_games.get(family_id)
    if not game:
        raise HTTPException(status_code=404, detail="Chua bat dau game")
    return game.get_question()


@router.post("/api/game/word-quiz/answer")
async def submit_word_answer(data: dict | None = None, current_user: dict = Depends(get_current_user)):
    """Submit a word quiz answer."""
    family_id = _require_family(current_user)
    game = _word_games.get(family_id)
    if not game:
        raise HTTPException(status_code=404, detail="Chua bat dau game")
    data = data or {}
    return game.submit_answer(data.get("answer", ""))


@router.post("/api/game/word-quiz/end")
async def end_word_quiz(current_user: dict = Depends(get_current_user)):
    """End a word quiz game."""
    family_id = _require_family(current_user)
    game = _word_games.pop(family_id, None)
    if not game:
        return {"total_score": 0, "correct": 0, "incorrect": 0}
    return game.end_game()


@router.post("/api/game/voice-quiz/start")
async def start_voice_quiz(current_user: dict = Depends(get_current_user)):
    """Start a voice quiz game."""
    family_id = _require_family(current_user)
    game = VoiceQuizGame()
    _voice_games[family_id] = game
    return game.start_game(family_id)


@router.get("/api/game/voice-quiz/riddle")
async def get_riddle(current_user: dict = Depends(get_current_user)):
    """Return the current voice quiz riddle."""
    family_id = _require_family(current_user)
    game = _voice_games.get(family_id)
    if not game:
        raise HTTPException(status_code=404, detail="Chua bat dau game")
    return game.get_riddle()


@router.post("/api/game/voice-quiz/answer")
async def submit_voice_answer(data: dict | None = None, current_user: dict = Depends(get_current_user)):
    """Submit a voice quiz answer."""
    family_id = _require_family(current_user)
    game = _voice_games.get(family_id)
    if not game:
        raise HTTPException(status_code=404, detail="Chua bat dau game")
    data = data or {}
    return game.check_voice_answer(data.get("spoken", ""))


@router.get("/api/game/scores")
async def get_scores(current_user: dict = Depends(get_current_user)):
    """Return game leaderboard for the current family."""
    family_id = _require_family(current_user)
    try:
        word_game = WordQuizGame()
        board = word_game.get_leaderboard(family_id)
    except Exception:
        board = []
    return {
        "word_quiz": board,
        "voice_quiz": [],
        "math_quiz": [],
    }
