"""Video call API routes."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.routers.conversation_router import _require_family
from src.communication.video_call import VideoCallManager
from src.infrastructure.auth.auth import get_current_user

router = APIRouter()
_manager = VideoCallManager()


@router.post("/api/video/call/start")
async def start_call(current_user: dict = Depends(get_current_user)):
    """Start a video call session for the current family."""
    family_id = _require_family(current_user)
    return _manager.start_call(
        family_id=family_id,
        caller_name=current_user.get("username", "Me"),
    )


@router.post("/api/video/call/end")
async def end_call(data: dict | None = None, current_user: dict = Depends(get_current_user)):
    """End a video call session."""
    family_id = _require_family(current_user)
    data = data or {}
    call_id = data.get("call_id", "")
    return {"ok": _manager.end_call(call_id, family_id=family_id)}


@router.get("/api/video/contacts")
async def get_contacts(current_user: dict = Depends(get_current_user)):
    """Return contacts for the current family."""
    family_id = _require_family(current_user)
    return {"contacts": _manager.get_contacts(family_id)}


@router.post("/api/video/contacts")
async def add_contact(data: dict | None = None, current_user: dict = Depends(get_current_user)):
    """Add a contact for the current family."""
    family_id = _require_family(current_user)
    data = data or {}
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Ten khong duoc rong")
    return _manager.add_contact(family_id, name)
