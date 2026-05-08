"""WiFi management routes — send WiFi commands to ESP32 via WebSocket."""

import asyncio
import logging

from fastapi import APIRouter, Depends

from src.infrastructure.auth.auth import get_current_user
from src.motion.motor_controller import get_shared_motor

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/wifi/add")
async def wifi_add(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Gửi lệnh thêm WiFi mới xuống ESP32 qua WebSocket."""
    payload = payload or {}
    ssid = payload.get("ssid", "").strip()
    password = payload.get("password", "").strip()

    if not ssid:
        return {"ok": False, "error": "SSID không được để trống"}

    motor = get_shared_motor()
    result = motor._send_raw(f"add_wifi:{{'ssid': '{ssid}', 'password': '{password}'}}")
    return {"ok": result, "message": f"Đã gửi lệnh thêm WiFi '{ssid}' xuống robot"}


@router.get("/api/wifi/status")
async def wifi_status(_current_user: dict = Depends(get_current_user)):
    """Lấy trạng thái WiFi hiện tại của ESP32."""
    motor = get_shared_motor()
    motor._send_raw("wifi_status")
    await asyncio.sleep(0.5)
    return {"ok": True, "mode": motor.mode, "connected": motor.connected}


@router.get("/api/wifi/list")
async def wifi_list(_current_user: dict = Depends(get_current_user)):
    """Lấy danh sách WiFi đã lưu trong ESP32."""
    motor = get_shared_motor()
    motor._send_raw("wifi_list")
    return {"ok": True, "message": "Đang lấy danh sách WiFi từ ESP32"}


@router.post("/api/wifi/scan")
async def wifi_scan(_current_user: dict = Depends(get_current_user)):
    """Scan WiFi lân cận."""
    motor = get_shared_motor()
    motor._send_raw("wifi_scan")
    return {"ok": True, "message": "Đang scan WiFi lân cận..."}


@router.post("/api/wifi/delete")
async def wifi_delete(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Xóa WiFi khỏi danh sách đã lưu trong ESP32."""
    payload = payload or {}
    ssid = payload.get("ssid", "").strip()
    if not ssid:
        return {"ok": False, "error": "SSID không được để trống"}
    motor = get_shared_motor()
    result = motor._send_raw(f"wifi_delete:{{'ssid': '{ssid}'}}")
    return {"ok": result, "message": f"Đã xóa WiFi '{ssid}'"}


@router.post("/api/wifi/connect")
async def wifi_connect(payload: dict | None = None, _current_user: dict = Depends(get_current_user)):
    """Kết nối tới WiFi đã lưu trong ESP32."""
    payload = payload or {}
    ssid = payload.get("ssid", "").strip()
    if not ssid:
        return {"ok": False, "error": "SSID không được để trống"}
    motor = get_shared_motor()
    result = motor._send_raw(f"wifi_connect:{{'ssid': '{ssid}'}}")
    return {"ok": result, "message": f"Robot đang kết nối WiFi '{ssid}' và khởi động lại..."}
