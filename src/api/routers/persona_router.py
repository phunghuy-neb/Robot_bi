"""Persona API routes for Robot Bi."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.ai.persona_manager import PersonaManager
from src.api.routers.conversation_router import _require_family
from src.infrastructure.auth.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/persona")
async def get_persona(_current_user: dict = Depends(get_current_user)):
    """Return persona settings for the current family."""
    try:
        family_id = _require_family(_current_user)
        return {"persona": PersonaManager(family_id).get_persona()}
    except HTTPException:
        raise
    except Exception:
        logger.exception("[PersonaRouter] get_persona failed")
        raise HTTPException(status_code=500, detail="Khong the lay persona")


@router.post("/api/persona/update")
async def update_persona(
    updates: dict,
    _current_user: dict = Depends(get_current_user),
):
    """Update persona settings for the current family."""
    try:
        family_id = _require_family(_current_user)
        manager = PersonaManager(family_id)
        if not manager.save(updates):
            raise HTTPException(status_code=400, detail="Persona khong hop le")
        return {"ok": True, "persona": manager.get_persona()}
    except HTTPException:
        raise
    except Exception:
        logger.exception("[PersonaRouter] update_persona failed")
        raise HTTPException(status_code=500, detail="Khong the cap nhat persona")
