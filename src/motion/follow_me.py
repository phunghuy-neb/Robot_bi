"""Follow-me simulation placeholder."""

from __future__ import annotations

import logging

from src.motion.motor_controller import MotorController

logger = logging.getLogger(__name__)


class FollowMe:
    """Mo phong che do robot di theo nguoi."""

    def __init__(self, motor: MotorController | None = None):
        """Khoi tao follow-me."""
        self.motor = motor or MotorController()
        self.enabled = False

    def start(self) -> bool:
        """Bat dau follow-me simulation."""
        try:
            self.enabled = True
            logger.info("[FollowMe] SIMULATION: start")
            return True
        except Exception:
            logger.exception("[FollowMe] start failed")
            return False

    def stop(self) -> bool:
        """Dung follow-me."""
        try:
            self.enabled = False
            return self.motor.stop()
        except Exception:
            logger.exception("[FollowMe] stop failed")
            return False

    def update_target(self, distance_m: float, offset_deg: float) -> bool:
        """Cap nhat vi tri target va mo phong motor command."""
        try:
            if not self.enabled:
                return False
            if abs(offset_deg) > 15:
                return self.motor.turn_left(abs(int(offset_deg))) if offset_deg < 0 else self.motor.turn_right(int(offset_deg))
            if distance_m > 1.2:
                return self.motor.forward(speed=35, duration_ms=300)
            return self.motor.stop()
        except Exception:
            logger.exception("[FollowMe] update_target failed")
            return False

    def get_status(self) -> dict:
        """Tra ve trang thai follow-me."""
        return {"enabled": self.enabled, "motor": self.motor.get_status()}
