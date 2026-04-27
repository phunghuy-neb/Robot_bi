"""
ops_router.py — Ops endpoints + Cloudflare Tunnel cho Robot Bi API.
  GET /health      — Health check (no auth)
  GET /            — Web dashboard
  GET /api/camera  — MJPEG live camera stream
"""
import asyncio
import logging
import os
import queue
import re
import subprocess
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Cloudflare Tunnel config ──────────────────────────────────────────────────
TUNNEL_TOKEN = os.getenv("CLOUDFLARE_TUNNEL_TOKEN", "").strip()
TUNNEL_URL   = os.getenv("CLOUDFLARE_TUNNEL_URL", "").strip()
_CLOUDFLARED_EXE = "cloudflared.exe" if os.name == "nt" else "cloudflared"
_tunnel_process = None

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

router = APIRouter()


def _build_ascii_qr(data: str, border: int = 1, invert: bool = False) -> str:
    """Render QR code bang ky tu ASCII thuan va ANSI color."""
    import qrcode
    if os.name == "nt":
        os.system("")
    qr = qrcode.QRCode(border=border)
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    dark = "\033[40m  \033[0m"
    light = "\033[47m  \033[0m"
    return "\n".join(
        "".join(dark if cell else light for cell in row)
        for row in matrix
    )


def _start_cloudflare_tunnel(port: int, use_https: bool = False) -> None:
    """Khởi động Named Tunnel nếu có CLOUDFLARE_TUNNEL_TOKEN, fallback quick tunnel."""
    def _run():
        global _tunnel_process
        try:
            result = subprocess.run(
                [_CLOUDFLARED_EXE, "--version"],
                capture_output=True, timeout=5,
            )
            if result.returncode != 0:
                print("[Tunnel] cloudflared khong tim thay — bo qua tunnel")
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("[Tunnel] cloudflared chua cai — bo qua tunnel")
            print("[Tunnel] Tai tai: https://github.com/cloudflare/cloudflared/releases")
            return

        if TUNNEL_TOKEN:
            # Named Tunnel — URL cố định, không đổi sau restart
            cmd = [_CLOUDFLARED_EXE, "tunnel", "--no-autoupdate", "run",
                   "--token", TUNNEL_TOKEN]
            logger.info("[Tunnel] Named Tunnel dang khoi dong...")
            fixed_url = TUNNEL_URL or "(xem Cloudflare dashboard)"
            print("\n" + "=" * 60)
            print(f"  URL CO DINH (Named Tunnel):")
            print(f"  {fixed_url}")
            print("=" * 60 + "\n")
            if TUNNEL_URL:
                try:
                    print(_build_ascii_qr(TUNNEL_URL, invert=True))
                except ImportError:
                    pass
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                )
                _tunnel_process = proc
                for _ in proc.stdout:
                    pass  # drain stdout de tranh block
            except Exception as e:
                logger.error("[Tunnel] Loi Named Tunnel: %s", e)
        else:
            # Quick tunnel — fallback, URL thay đổi mỗi restart
            scheme = "https" if use_https else "http"
            print(f"[Tunnel] Quick tunnel -> {scheme}://localhost:{port} (URL thay doi moi restart)...")
            cmd = [_CLOUDFLARED_EXE, "tunnel", "--no-autoupdate", "--url",
                   f"{scheme}://localhost:{port}"]
            if use_https:
                cmd.append("--no-tls-verify")
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                )
                _tunnel_process = proc
                for line in proc.stdout:
                    line = line.strip()
                    if "trycloudflare.com" in line or "https://" in line:
                        urls = re.findall(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
                        if urls:
                            public_url = urls[0]
                            print("\n" + "=" * 60)
                            print(f"  URL CONG KHAI (thay doi moi restart):")
                            print(f"  {public_url}")
                            print("=" * 60 + "\n")
                            try:
                                print(_build_ascii_qr(public_url, invert=True))
                            except ImportError:
                                pass
            except Exception as e:
                print(f"[Tunnel] Loi: {e}")

    t = threading.Thread(target=_run, daemon=True, name="cloudflared-tunnel")
    t.start()

_STATIC_DIR = Path(__file__).parent.parent / "static"

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


async def _camera_auth(
    request: Request,
    auth: Optional[str] = Query(None),
) -> dict:
    """
    Camera/stream auth: chap nhan JWT qua Authorization header HOAC ?auth= query param.
    Dung cho <img src='/api/camera?auth=TOKEN'> trong browser.
    """
    from src_brain.network.auth import verify_access_token
    authorization = request.headers.get("Authorization", "")
    token = auth or (authorization[7:] if authorization.startswith("Bearer ") else None)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_access_token(token)
    except HTTPException:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": payload["sub"], "family_name": payload["family"]}


@router.get("/health")
async def health():
    """Health check — khong can auth."""
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    index = _STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return HTMLResponse(
        "<h1>Robot Bi</h1>"
        "<p>Dashboard chưa có. Đặt file vào <code>src_brain/network/static/index.html</code></p>"
    )


def _camera_capture_thread(frame_queue: queue.Queue, stop_event: threading.Event):
    """Thread riêng capture frame — không block event loop."""
    import time as _time
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        stop_event.set()
        return

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 30)

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            _time.sleep(0.01)
            continue

        frame = cv2.resize(frame, (640, 480))
        _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_bytes = jpg.tobytes()

        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
        try:
            frame_queue.put_nowait(frame_bytes)
        except queue.Full:
            pass

    cap.release()


async def _mjpeg_generator():
    """Generator yield MJPEG frames — camera capture chạy trong thread riêng."""
    if not _CV2_AVAILABLE:
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blank, 'Camera not available', (80, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, jpg = cv2.imencode('.jpg', blank)
        frame_bytes = jpg.tobytes()
        while True:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + frame_bytes + b'\r\n')
            await asyncio.sleep(0.5)
        return

    frame_queue: queue.Queue = queue.Queue(maxsize=2)
    stop_event = threading.Event()

    t = threading.Thread(
        target=_camera_capture_thread,
        args=(frame_queue, stop_event),
        daemon=True,
        name="camera-capture",
    )
    t.start()

    try:
        while True:
            try:
                frame_bytes = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: frame_queue.get(timeout=0.1),
                )
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + frame_bytes + b'\r\n')
                await asyncio.sleep(0)
            except queue.Empty:
                await asyncio.sleep(0.033)
            except GeneratorExit:
                break
    finally:
        stop_event.set()


@router.get("/api/camera")
async def camera_stream(_current_user: dict = Depends(_camera_auth)):
    """Live MJPEG camera stream. Token co the truyen qua query param ?auth=<JWT>"""
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )
