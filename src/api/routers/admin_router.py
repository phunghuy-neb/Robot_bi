"""
admin_router.py - Admin-only family management endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import (
    create_family_record,
    delete_family_record,
    is_user_admin,
    list_families,
)
import src.infrastructure.sessions.state as _state

logger = logging.getLogger(__name__)
router = APIRouter()


class FamilyCreate(BaseModel):
    family_id: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str | None = Field(default=None, max_length=120)


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not is_user_admin(str(current_user.get("user_id", ""))):
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


@router.post("/api/admin/families")
async def create_family(body: FamilyCreate, _admin: dict = Depends(require_admin)):
    family = create_family_record(body.family_id, body.display_name)
    if family is None:
        raise HTTPException(status_code=409, detail="Family already exists")
    return family


@router.get("/api/admin/families")
async def get_families(_admin: dict = Depends(require_admin)):
    return {"families": list_families()}


@router.delete("/api/admin/families/{family_id}")
async def delete_family(family_id: str, admin: dict = Depends(require_admin)):
    if family_id == admin.get("family_name"):
        raise HTTPException(status_code=400, detail="Cannot delete current admin family")
    ok = delete_family_record(family_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Family not found")
    if _state._rag:
        result = _state._rag.clear_all_memories(family_id=family_id)
        if not result:
            logger.warning(
                "[Admin] ChromaDB cleanup failed for family %s - "
                "DB deleted but memories may remain",
                family_id,
            )
    return {"ok": True, "family_id": family_id}
