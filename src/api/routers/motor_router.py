"""Motor API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.infrastructure.auth.auth import get_current_user
from src.motion.motor_controller import MotorController

logger = logging.getLogger(__name__)

router = APIRouter()
_MOTOR = MotorController()


@router.post("/api/motor/forward")
async def motor_forward(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Move forward."""
    payload = payload or {}
    return {"ok": _MOTOR.forward(payload.get("speed", 50), payload.get("duration_ms", 1000))}


@router.post("/api/motor/backward")
async def motor_backward(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Move backward."""
    payload = payload or {}
    return {"ok": _MOTOR.backward(payload.get("speed", 50), payload.get("duration_ms", 1000))}


@router.post("/api/motor/left")
async def motor_left(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Turn left."""
    payload = payload or {}
    return {"ok": _MOTOR.turn_left(payload.get("degrees", 90))}


@router.post("/api/motor/right")
async def motor_right(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Turn right."""
    payload = payload or {}
    return {"ok": _MOTOR.turn_right(payload.get("degrees", 90))}


@router.post("/api/motor/stop")
async def motor_stop(_current_user: dict = Depends(get_current_user)):
    """Stop motor."""
    return {"ok": _MOTOR.stop()}


@router.post("/api/motor/home")
async def motor_home(_current_user: dict = Depends(get_current_user)):
    """Go home to charging dock."""
    return {"ok": _MOTOR.go_home()}


@router.get("/api/motor/status")
async def motor_status(_current_user: dict = Depends(get_current_user)):
    """Return motor status."""
    try:
        return _MOTOR.get_status()
    except Exception:
        logger.exception("[MotorRouter] status failed")
        raise HTTPException(status_code=500, detail="Khong the lay motor status")
