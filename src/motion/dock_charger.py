"""Charging dock simulation placeholder."""

from __future__ import annotations

import logging

from src.motion.motor_controller import MotorController

logger = logging.getLogger(__name__)


class DockCharger:
    """Mo phong quay ve dock sac."""

    def __init__(self, motor: MotorController | None = None):
        """Khoi tao dock charger helper."""
        self.motor = motor or MotorController()
        self.docked = False

    def go_home(self) -> bool:
        """Mo phong ve dock sac."""
        try:
            logger.info("[DockCharger] SIMULATION: go_home")
            ok = self.motor.go_home()
            self.docked = ok
            return ok
        except Exception:
            logger.exception("[DockCharger] go_home failed")
            return False

    def undock(self) -> bool:
        """Mo phong roi dock."""
        try:
            self.docked = False
            return self.motor.backward(speed=30, duration_ms=500)
        except Exception:
            logger.exception("[DockCharger] undock failed")
            return False

    def get_status(self) -> dict:
        """Tra ve trang thai dock."""
        return {"docked": self.docked, "motor": self.motor.get_status()}
