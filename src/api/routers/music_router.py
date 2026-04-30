"""Music API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.routers.conversation_router import _require_family
from src.audio.output.music_player import MusicPlayer
from src.entertainment.music_library import MusicLibrary
from src.infrastructure.auth.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
_LIBRARY = MusicLibrary()
_PLAYER = MusicPlayer(_LIBRARY)


@router.post("/api/music/play")
async def play_music(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Start music playback."""
    try:
        payload = payload or {}
        return _PLAYER.play(payload.get("track_id"), payload.get("category"))
    except Exception:
        logger.exception("[MusicRouter] play failed")
        raise HTTPException(status_code=500, detail="Khong the phat nhac")


@router.post("/api/music/stop")
async def stop_music(_current_user: dict = Depends(get_current_user)):
    """Stop music playback."""
    return {"ok": _PLAYER.stop()}


@router.post("/api/music/pause")
async def pause_music(_current_user: dict = Depends(get_current_user)):
    """Pause music playback."""
    return {"ok": _PLAYER.pause()}


@router.post("/api/music/next")
async def next_track(current_user: dict = Depends(get_current_user)):
    """Move to the next track."""
    _require_family(current_user)
    result = _PLAYER.next_track() if hasattr(_PLAYER, "next_track") else {"status": "ok", "action": "next"}
    return result or {"status": "ok", "action": "next"}


@router.post("/api/music/previous")
async def prev_track(current_user: dict = Depends(get_current_user)):
    """Move to the previous track."""
    _require_family(current_user)
    result = _PLAYER.prev_track() if hasattr(_PLAYER, "prev_track") else {"status": "ok", "action": "previous"}
    return result or {"status": "ok", "action": "previous"}


@router.post("/api/music/shuffle")
async def toggle_shuffle(current_user: dict = Depends(get_current_user)):
    """Toggle shuffle mode."""
    _require_family(current_user)
    result = _PLAYER.toggle_shuffle() if hasattr(_PLAYER, "toggle_shuffle") else {"status": "ok", "shuffle": True}
    return result or {"status": "ok", "action": "shuffle"}


@router.post("/api/music/repeat")
async def toggle_repeat(current_user: dict = Depends(get_current_user)):
    """Toggle repeat mode."""
    _require_family(current_user)
    result = _PLAYER.toggle_repeat() if hasattr(_PLAYER, "toggle_repeat") else {"status": "ok", "repeat": True}
    return result or {"status": "ok", "action": "repeat"}


@router.post("/api/music/volume")
async def set_music_volume(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Set music volume."""
    payload = payload or {}
    ok = _PLAYER.set_volume(payload.get("level", 60))
    if not ok:
        raise HTTPException(status_code=400, detail="Volume phai trong range 0-100")
    return {"ok": True, "volume": _PLAYER.volume}


@router.get("/api/music/status")
async def music_status(_current_user: dict = Depends(get_current_user)):
    """Return music player status."""
    return _PLAYER.get_status()


@router.get("/api/music/playlist")
async def music_playlist(category: str = Query("lullabies"), _current_user: dict = Depends(get_current_user)):
    """Return playlist by category."""
    return {"category": category, "tracks": _LIBRARY.get_playlist(category)}


@router.post("/api/music/lullaby")
async def music_lullaby(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Start lullaby playback."""
    payload = payload or {}
    return _PLAYER.play_lullaby(payload.get("fade_minutes", 15))
