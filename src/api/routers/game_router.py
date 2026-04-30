"""Game API routes."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.routers.conversation_router import _require_family
from src.entertainment.game_voice_quiz import VoiceQuizGame
from src.entertainment.game_word_quiz import WordQuizGame
from src.infrastructure.auth.auth import get_current_user

router = APIRouter()
_word_games: dict[str, WordQuizGame] = {}
_voice_games: dict[str, VoiceQuizGame] = {}


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
    word_game = WordQuizGame()
    return {"leaderboard": word_game.get_leaderboard(family_id)}
