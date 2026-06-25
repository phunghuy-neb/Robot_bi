"""WiFi management routes — send WiFi commands to ESP32 via WebSocket."""

import ipaddress
import json
import logging
import os
from urllib.parse import urlparse

from fastapi import APIRouter, Depends

from src.infrastructure.auth.auth import get_current_user
from src.motion.motor_controller import get_shared_motor

logger = logging.getLogger(__name__)

router = APIRouter()

_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in _PRIVATE_NETS)
    except ValueError:
        return False


@router.post("/api/motor/register")
async def motor_register(
    payload: dict | None = None,
    _current_user: dict = Depends(get_current_user),
):
    payload = payload or {}
    ip = payload.get("ip", "").strip()
    port = int(payload.get("port", 81))

    if not ip:
        return {"ok": False, "error": "Invalid IP"}

    if not _is_private_ip(ip):
        return {"ok": False, "error": "Only private/LAN IP addresses are allowed"}

    new_url = f"ws://{ip}:{port}"
    os.environ["MOTOR_WS_URL"] = new_url

    motor = get_shared_motor()
    motor.ws_url = new_url
    motor.connected = False
    motor.mode = "simulation"

    if motor._ws:
        try:
            motor._ws.close()
        except Exception:
            pass
        motor._ws = None

    import threading
    threading.Thread(target=motor._try_connect_ws, daemon=True).start()

    logger.info(f"[Motor] ESP32 registered — IP: {ip}, URL: {new_url} — reconnecting in background")

    return {
        "ok": True,
        "message": f"Registered ESP32 at {new_url}. Reconnecting...",
        "motor_mode": "connecting",
    }


@router.get("/api/wifi/status")
async def wifi_status(_current_user: dict = Depends(get_current_user)):
    """Return the current known ESP32 WiFi registration status."""
    motor = get_shared_motor()
    parsed = urlparse(motor.ws_url or "")
    return {
        "ok": True,
        "connected": bool(motor.connected),
        "ip": parsed.hostname,
        "port": parsed.port,
        "ssid": None,
        "rssi": None,
        "security": None,
        "band": None,
        "dns": None,
        "mac": None,
    }


@router.post("/api/wifi/add")
async def wifi_add(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Gửi lệnh thêm WiFi mới xuống ESP32 qua WebSocket."""
    payload = payload or {}
    ssid = payload.get("ssid", "").strip()
    password = payload.get("password", "").strip()

    if not ssid:
        return {"ok": False, "error": "SSID không được để trống"}

    motor = get_shared_motor()
    wire = "add_wifi:" + json.dumps({"ssid": ssid, "password": password}, ensure_ascii=False)
    result = motor._send_raw(wire)
    return {"ok": result, "message": f"Đã gửi lệnh thêm WiFi '{ssid}' xuống robot"}

