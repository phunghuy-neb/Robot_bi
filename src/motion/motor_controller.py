"""
MotorController - Dieu khien motor robot qua ESP32/Serial hoac WiFi WebSocket.

PLACEHOLDER: implement serial protocol day du khi co hardware. Hien tai mac
dinh simulation mode va log command.
"""

from __future__ import annotations

import logging
import os
import threading

import serial  # giữ nguyên import

logger = logging.getLogger(__name__)

try:
    import websocket
    WS_AVAILABLE = True
except ImportError:
    WS_AVAILABLE = False

# Trần thời lượng chuyển động vật lý (H-NEW-3): clamp tập trung để MỌI caller
# (REST/WS/gọi trực tiếp) đều bị giới hạn, không chỉ riêng router. Khớp _MAX_DURATION_MS
# ở motor_router/streaming_router.
_MAX_DURATION_MS = 5000


def _clamp_duration(duration_ms) -> int:
    return min(max(0, int(duration_ms)), _MAX_DURATION_MS)


class MotorController:
    """Motor controller voi simulation fallback."""

    def __init__(self, port: str | None = None, baud: int = 115200):
        """Khoi tao controller va thu ket noi serial hoac WiFi WebSocket."""
        self.port = port or os.getenv("MOTOR_PORT")
        self.baud = baud
        self.ws_url = os.getenv("MOTOR_WS_URL")  # vi du: ws://192.168.1.x:81
        self._serial = None
        self._ws = None
        self._lock = threading.RLock()
        self.connected = False
        self.mode = "simulation"
        self.last_command: dict | None = None

        if self.ws_url and WS_AVAILABLE:
            self._try_connect_ws()
        elif self.port:
            self._try_connect_serial()
        else:
            logger.info("[MotorController] No port or WS URL — simulation mode")
        self._start_reconnect_thread()

    def _try_connect_ws(self):
        # Connect attempts run OUTSIDE the lock; only the socket swap is locked.
        # This prevents the ~19 s lock hold that starved the ASGI event loop (M1).
        import time
        if not self.ws_url:
            return
        new_ws = None
        for attempt in range(3):
            try:
                ws = websocket.WebSocket()
                ws.connect(self.ws_url, timeout=5)
                new_ws = ws
                break
            except Exception as e:
                logger.warning(f"[MotorController] WiFi connect attempt {attempt+1}/3 failed: {e}")
                if attempt < 2:
                    time.sleep(2)

        with self._lock:
            if new_ws is not None:
                self._ws = new_ws
                self.connected = True
                self.mode = "wifi"
                logger.info(f"[MotorController] WiFi WebSocket connected: {self.ws_url}")
            else:
                self._ws = None
                self.connected = False
                self.mode = "simulation"
                logger.warning("[MotorController] WiFi connect failed after 3 attempts — simulation mode")

    def _start_reconnect_thread(self):
        """Background thread tự động reconnect với exponential backoff."""
        import time, threading
        def reconnect_loop():
            delay = 10
            while True:
                time.sleep(delay)
                if self.mode == "simulation" and self.ws_url:
                    logger.info("[MotorController] Background reconnect attempt...")
                    self._try_connect_ws()
                    if self.mode == "wifi":
                        delay = 10  # reset backoff on success
                    else:
                        delay = min(delay * 2, 120)  # cap at 2 min
        t = threading.Thread(target=reconnect_loop, daemon=True)
        t.start()

    def _try_connect_serial(self):
        """Thu ket noi serial. Neu khong co thi simulation mode."""
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=1)
            self.connected = bool(self._serial and self._serial.is_open)
            self.mode = "serial" if self.connected else "simulation"
        except Exception:
            logger.exception("[MotorController] Serial connect failed, using simulation")
            self.connected = False
            self.mode = "simulation"

    def _send(self, command: str, **params) -> bool:
        """Gui command toi WiFi/serial hoac log simulation."""
        self.last_command = {"command": command, **params}
        payload_str = f"{command}:{params}\n"
        with self._lock:
            if self.mode == "wifi" and self._ws:
                try:
                    self._ws.send(payload_str.strip())
                    return True
                except Exception:
                    # Fast-fail (M1): KHÔNG reconnect inline ở đây — `_try_connect_ws` mất tới
                    # ~19s (3 lần thử + sleep) và GIỮ self._lock suốt thời gian đó, nuốt luôn
                    # lệnh `stop` đang chờ lock → nguy hiểm vật lý. Đóng ws + chuyển simulation;
                    # background reconnect thread sẽ tự kết nối lại (không giữ lock khi sleep).
                    logger.warning("[MotorController] WiFi send failed — fast-fail; background sẽ reconnect")
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                    self._ws = None
                    self.mode = "simulation"
                    return False
            elif self.mode == "serial" and self._serial:
                try:
                    self._serial.write(payload_str.encode("utf-8"))
                    return True
                except Exception as e:
                    logger.error(f"[MotorController] Serial send failed: {e}")
                    return False
            else:
                logger.info(f"[MotorController] SIMULATION: {payload_str.strip()}")
                return True

    def forward(self, speed: int = 50, duration_ms: int = 1000) -> bool:
        """Di tien voi speed va duration."""
        return self._send("forward", speed=max(0, min(100, int(speed))), duration_ms=_clamp_duration(duration_ms))

    def backward(self, speed: int = 50, duration_ms: int = 1000) -> bool:
        """Di lui voi speed va duration."""
        return self._send("backward", speed=max(0, min(100, int(speed))), duration_ms=_clamp_duration(duration_ms))

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

    def spin(self, speed: int = 50, duration_ms: int = 2000) -> bool:
        """Quay tron tai cho."""
        return self._send("spin", speed=max(0, min(100, int(speed))), duration_ms=_clamp_duration(duration_ms))

    def drive(self, left: int = 0, right: int = 0) -> bool:
        """Continuous drive: left/right PWM doc lap, -100 den 100.
        Am = lui, duong = tien. Khong co duration — chay den lenh tiep theo.
        ESP32 watchdog tu dung sau 500ms neu khong nhan lenh moi.
        """
        left  = max(-100, min(100, int(left)))
        right = max(-100, min(100, int(right)))
        return self._send("drive", left=left, right=right)

    def _send_raw(self, raw_str: str) -> bool:
        """Gửi raw string xuống ESP32 không qua format params."""
        with self._lock:
            if self.mode == "wifi" and self._ws:
                try:
                    self._ws.send(raw_str.strip())
                    return True
                except Exception as e:
                    logger.error(f"[MotorController] _send_raw failed: {e}")
                    return False
            else:
                logger.info(f"[MotorController] SIMULATION _send_raw: {raw_str}")
                return True

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


_shared_motor: "MotorController | None" = None


def get_shared_motor() -> "MotorController":
    global _shared_motor
    if _shared_motor is None:
        _shared_motor = MotorController()
    return _shared_motor
