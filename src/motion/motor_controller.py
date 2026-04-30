"""
MotorController - Dieu khien motor robot qua ESP32/Serial.

PLACEHOLDER: implement serial protocol day du khi co hardware. Hien tai mac
dinh simulation mode va log command.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class MotorController:
    """Motor controller voi simulation fallback."""

    def __init__(self, port: str | None = None, baud: int = 115200):
        """Khoi tao controller va thu ket noi serial neu co MOTOR_PORT."""
        self.port = port or os.getenv("MOTOR_PORT", None)
        self.baud = baud
        self.connected = False
        self.mode = "simulation"
        self.last_command: dict | None = None
        self._serial = None
        self._try_connect()

    def _try_connect(self):
        """Thu ket noi serial. Neu khong co thi simulation mode."""
        try:
            if not self.port:
                logger.info("[MotorController] SIMULATION: no MOTOR_PORT configured")
                self.connected = False
                self.mode = "simulation"
                return
            try:
                import serial  # type: ignore
            except Exception:
                logger.info("[MotorController] SIMULATION: pyserial unavailable")
                self.connected = False
                self.mode = "simulation"
                return
            self._serial = serial.Serial(self.port, self.baud, timeout=1)
            self.connected = bool(self._serial and self._serial.is_open)
            self.mode = "serial" if self.connected else "simulation"
        except Exception:
            logger.exception("[MotorController] Serial connect failed, using simulation")
            self.connected = False
            self.mode = "simulation"

    def _send(self, command: str, **params) -> bool:
        """Gui command toi serial hoac log simulation."""
        try:
            self.last_command = {"command": command, **params}
            if self.connected and self._serial:
                payload = f"{command}:{params}\n".encode("utf-8")
                self._serial.write(payload)
            else:
                logger.info("[MotorController] SIMULATION: %s %s", command, params)
            return True
        except Exception:
            logger.exception("[MotorController] send command failed")
            return False

    def forward(self, speed: int = 50, duration_ms: int = 1000) -> bool:
        """Di tien voi speed va duration."""
        return self._send("forward", speed=max(0, min(100, int(speed))), duration_ms=max(0, int(duration_ms)))

    def backward(self, speed: int = 50, duration_ms: int = 1000) -> bool:
        """Di lui voi speed va duration."""
        return self._send("backward", speed=max(0, min(100, int(speed))), duration_ms=max(0, int(duration_ms)))

    def turn_left(self, degrees: int = 90) -> bool:
        """Quay trai theo degrees."""
        return self._send("turn_left", degrees=max(0, min(360, int(degrees))))

    def turn_right(self, degrees: int = 90) -> bool:
        """Quay phai theo degrees."""
        return self._send("turn_right", degrees=max(0, min(360, int(degrees))))

    def stop(self) -> bool:
        """Dung motor."""
        return self._send("stop")

    def go_home(self) -> bool:
        """Lenh tu ve dock sac."""
        return self._send("go_home")

    def get_status(self) -> dict:
        """Returns `{connected, mode, last_command}`."""
        try:
            return {"connected": self.connected, "mode": self.mode, "last_command": self.last_command}
        except Exception:
            logger.exception("[MotorController] get_status failed")
            return {"connected": False, "mode": "simulation", "last_command": None}

    def is_simulation(self) -> bool:
        """Tra ve True neu dang chay simulation mode."""
        return self.mode == "simulation"
