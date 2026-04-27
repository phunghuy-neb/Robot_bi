"""
api_server.py — Robot Bi: FastAPI Parent App Backend
=====================================================
Entry point: init_server() + start_api_server() từ main_loop.py.

Routes được tổ chức thành routers/:
  auth_router         — /api/auth/*, /auth/*
  conversation_router — /api/conversations/*
  streaming_router    — /ws, /api/audio/stream, /api/mom/*
  control_router      — /api/status, /api/events/*, /api/tasks/*, /api/memories/*, /api/puppet
  ops_router          — /health, /, /api/camera
"""

import asyncio
import logging
import os
import re
import socket
import threading
import warnings
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

import src_brain.network.state as _state
from src_brain.network.log_config import setup_logging
from src_brain.network.routers.auth_router import router as auth_router
from src_brain.network.routers.conversation_router import router as conversation_router, _require_family
from src_brain.network.routers.streaming_router import router as streaming_router
from src_brain.network.routers.control_router import router as control_router
from src_brain.network.routers.ops_router import router as ops_router
from src_brain.network.routers.ops_router import _build_ascii_qr, _start_cloudflare_tunnel
from src_brain.network.routers import webrtc_router

logger = logging.getLogger("api_server")

# ── SSL config ────────────────────────────────────────────────────────────────
_SSL_DIR  = Path(__file__).parent.parent.parent / "ssl"
_SSL_CERT = _SSL_DIR / "cert.pem"
_SSL_KEY  = _SSL_DIR / "key.pem"
_USE_HTTPS = _SSL_CERT.exists() and _SSL_KEY.exists()

# ── Thư mục static ────────────────────────────────────────────────────────────
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_DIR.mkdir(exist_ok=True)


def get_local_ip() -> str:
    """Lấy IP WiFi LAN thật, bỏ qua VPN/Hamachi/tunnel."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(title="Robot Bi — Parent App API", version="2.0")

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

app.include_router(auth_router)
app.include_router(conversation_router)
app.include_router(streaming_router)
app.include_router(control_router)
app.include_router(ops_router)
app.include_router(webrtc_router.router)


@app.on_event("startup")
async def _on_startup():
    setup_logging()
    _state._api_loop = asyncio.get_event_loop()
    logger.info("[API] FastAPI server started. Event loop captured.")


# ── Public API — gọi từ main_loop.py ─────────────────────────────────────────

def init_server(notifier, rag_manager) -> None:
    """Inject dependencies từ main_loop.py. Gọi TRƯỚC start_api_server()."""
    _state._notifier = notifier
    _state._rag = rag_manager
    notifier.set_ws_broadcaster(_state._broadcast_from_thread)
    from src_brain.network import notifier as _notifier_mod
    _notifier_mod.set_ws_broadcaster(_state._ws_manager.broadcast)
    logger.info("[API] Dependencies injected (notifier + rag).")


def get_puppet_queue():
    """Trả về queue puppet để main_loop.py poll và đọc commands."""
    return _state._puppet_queue


def init_task_manager(tts_callback) -> None:
    """Inject TaskManager với TTS callback từ main_loop.py."""
    from src_brain.network.task_manager import TaskManager
    _state._task_manager = TaskManager(tts_callback=tts_callback)
    logger.info("[API] TaskManager injected.")


def is_mom_talking() -> bool:
    """Public helper — main_loop.py import để check trạng thái mẹ."""
    return _state.is_mom_talking()


# ── QR helper (build via ops_router._build_ascii_qr) ─────────────────────────

def _print_qr_code(ip: str, port: int = 8000, scheme: str = "http") -> None:
    """In QR code ra terminal để phụ huynh quét."""
    url = f"{scheme}://{ip}:{port}"
    try:
        qr_text = _build_ascii_qr(url)
        print(f"\n{'='*50}")
        print(f"  Parent App: {url}")
        if scheme == "https":
            print(f"  (Lan dau bam 'Advanced' -> 'Proceed' vi self-signed cert)")
        print(f"  Quet QR tren dien thoai cung mang WiFi:")
        print(qr_text)
        print('='*50)
    except ImportError:
        print(f"\n{'='*50}")
        print(f"  Parent App: {url}")
        print(f"  (Cai qrcode de hien QR: pip install qrcode)")
        print('='*50)


def start_api_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Khởi động FastAPI + uvicorn trong background daemon thread.
    Non-blocking — không ảnh hưởng đến main_loop.py.
    """
    if not _state.AUTH_PIN:
        raise Exception(
            "[Auth] FATAL: AUTH_PIN chưa được cấu hình trong .env. "
            "Server không thể khởi động. Thêm AUTH_PIN=<pin> vào file .env rồi thử lại."
        )

    from src_brain.network.auth import _get_jwt_config
    _get_jwt_config()

    use_https = _USE_HTTPS
    actual_port = 8443 if use_https else port

    def _run():
        if use_https:
            print(f"[Server] HTTPS enabled — https://localhost:{actual_port}")
            uvicorn.run(
                app,
                host=host,
                port=actual_port,
                ssl_certfile=str(_SSL_CERT),
                ssl_keyfile=str(_SSL_KEY),
                log_level="warning",
            )
        else:
            print(f"[Server] HTTP mode — chay generate_ssl.py de bat HTTPS")
            uvicorn.run(app, host=host, port=actual_port, log_level="warning")

    t = threading.Thread(target=_run, daemon=True, name="api-server")
    t.start()

    _start_cloudflare_tunnel(actual_port, use_https)

    local_ip = get_local_ip()
    scheme = "https" if use_https else "http"
    _print_qr_code(local_ip, actual_port, scheme)
