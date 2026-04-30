"""Navigation simulation placeholder."""

from __future__ import annotations

import logging

from src.motion.motor_controller import MotorController

logger = logging.getLogger(__name__)


class Navigation:
    """High-level navigation commands in simulation mode."""

    def __init__(self, motor: MotorController | None = None):
        """Khoi tao navigation voi motor controller."""
        self.motor = motor or MotorController()
        self.destination = None

    def go_to(self, destination: str) -> bool:
        """Mo phong di toi destination."""
        try:
            self.destination = destination
            logger.info("[Navigation] SIMULATION: go_to %s", destination)
            return self.motor.forward(speed=40, duration_ms=500)
        except Exception:
            logger.exception("[Navigation] go_to failed")
            return False

    def stop(self) -> bool:
        """Dung navigation."""
        try:
            self.destination = None
            return self.motor.stop()
        except Exception:
            logger.exception("[Navigation] stop failed")
            return False

    def get_status(self) -> dict:
        """Tra ve trang thai navigation."""
        return {"destination": self.destination, "motor": self.motor.get_status()}
