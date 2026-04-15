"""
api_server.py — Robot Bi: FastAPI Parent App Backend (Sprint 5 + Sprint 6)
==========================================================================
SRS Phần 4: Ứng dụng phụ huynh — REST API + WebSocket + Web Dashboard
SRS NFR-06: PIN authentication (Session G)

Truy cập: http://<IP_robot>:8000 từ browser trên phone cùng mạng LAN
Khởi động: gọi init_server() rồi start_api_server() từ main_loop.py

Endpoints (Sprint 5):
  GET  /                        → Web dashboard (index.html)
  WS   /ws                      → Real-time event push
  GET  /api/status              → Trạng thái robot
  GET  /api/events              → Danh sách sự kiện (filter: type, unread_only)
  POST /api/events/read_all     → Đánh dấu tất cả đã đọc
  GET  /api/chats               → Nhật ký hội thoại
  GET  /api/memories            → Danh sách trí nhớ
  POST /api/memories            → Thêm trí nhớ thủ công
  PUT  /api/memories/{id}       → Sửa trí nhớ
  DELETE /api/memories/{id}     → Xóa trí nhớ
  GET  /api/memories/export     → Export JSON backup
  POST /api/puppet              → Bi đọc text được gửi từ app

Endpoints (Sprint 6 — Session G):
  POST /api/auth/login          → Đăng nhập PIN (trả về token)
  POST /api/auth/logout         → Đăng xuất
  GET  /api/camera              → MJPEG live camera stream
  GET  /api/tasks               → Danh sách nhiệm vụ
  POST /api/tasks               → Thêm nhiệm vụ mới
  POST /api/tasks/{id}/complete → Hoàn thành nhiệm vụ (+1 sao)
  DELETE /api/tasks/{id}        → Xóa nhiệm vụ
  GET  /api/tasks/stars         → Tổng số sao
"""

import asyncio
import hashlib
import logging
import queue
import re
import secrets
import socket
import subprocess
import threading
from pathlib import Path
from typing import Optional

try:
    import numpy as np
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False


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

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

logger = logging.getLogger("api_server")

# ── Module-level state (injected bởi main_loop.py trước khi start) ────────────
_notifier = None       # EventNotifier instance
_rag = None            # RAGManager instance
_puppet_queue: queue.Queue = queue.Queue()
_api_loop: Optional[asyncio.AbstractEventLoop] = None

# ── PIN Authentication (SRS NFR-06) ───────────────────────────────────────────
PIN_CODE = "123456"           # Default PIN — thay đổi trong .env nếu cần
SESSION_TOKENS: set = set()   # In-memory session store

# ── Audio monitoring config ────────────────────────────────────────────────────
AUDIO_SAMPLE_RATE  = 16000   # Hz — khớp với ear_stt.py
AUDIO_CHANNELS     = 1       # Mono
AUDIO_CHUNK_MS     = 100     # Gửi mỗi 100ms
AUDIO_CHUNK_FRAMES = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)  # 1600 frames
AUDIO_MIC_DEVICE   = 1       # Microphone Array Realtek

# ── Trạng thái "mẹ đang nói chuyện trực tiếp" ────────────────────────────────
_mom_talking = False
_mom_audio_clients: list = []  # WebSocket clients đang stream audio từ điện thoại mẹ


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def require_auth(
    authorization: Optional[str] = Header(None),
    auth: Optional[str] = Query(None),  # query param cho <img src>
) -> str:
    """Dependency: kiểm tra token hợp lệ từ header hoặc query param."""
    token = authorization or auth
    if not token or token not in SESSION_TOKENS:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    return token


# ── Task Manager (SRS 4.4) ─────────────────────────────────────────────────────
_task_manager = None   # TaskManager instance, inject từ main_loop.py


def init_task_manager(tts_callback) -> None:
    """Inject TaskManager với TTS callback từ main_loop.py."""
    global _task_manager
    from src_brain.network.task_manager import TaskManager
    _task_manager = TaskManager(tts_callback=tts_callback)
    logger.info("[API] TaskManager injected.")


# ── SSL config ────────────────────────────────────────────────────────────────
_SSL_DIR  = Path(__file__).parent.parent.parent / "ssl"
_SSL_CERT = _SSL_DIR / "cert.pem"
_SSL_KEY  = _SSL_DIR / "key.pem"
_USE_HTTPS = _SSL_CERT.exists() and _SSL_KEY.exists()

# ── Cloudflare Tunnel config ──────────────────────────────────────────────────
_CLOUDFLARED_ENABLED = True   # Set False để tắt tunnel
_CLOUDFLARED_EXE = "cloudflared"  # hoặc đường dẫn tuyệt đối nếu cần

# ── Thư mục static (dashboard HTML) ──────────────────────────────────────────
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  WebSocket Connection Manager
# ═══════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    """Thread-safe manager cho danh sách WebSocket clients."""

    def __init__(self):
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.append(ws)
        logger.info("[WS] Client kết nối. Tổng: %d", len(self._clients))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._clients:
            self._clients.remove(ws)
        logger.info("[WS] Client ngắt kết nối. Tổng: %d", len(self._clients))

    async def broadcast(self, data: dict) -> None:
        """Gửi JSON tới tất cả clients; tự loại bỏ client chết."""
        dead = []
        for client in list(self._clients):
            try:
                await client.send_json(data)
            except Exception:
                dead.append(client)
        for c in dead:
            self._clients.remove(c)

    @property
    def count(self) -> int:
        return len(self._clients)


_ws_manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════════════════════════
#  FastAPI App
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="Robot Bi — Parent App API", version="2.0")

# Mount thư mục static
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.on_event("startup")
async def _on_startup():
    global _api_loop
    _api_loop = asyncio.get_event_loop()
    logger.info("[API] FastAPI server started. Event loop captured.")


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(pin: str = Body(..., embed=True)):
    """Đăng nhập bằng PIN. Trả về session token."""
    if _hash_pin(pin) == _hash_pin(PIN_CODE):
        token = secrets.token_hex(16)
        SESSION_TOKENS.add(token)
        logger.info("[Auth] Login thành công. Tokens active: %d", len(SESSION_TOKENS))
        return {"token": token}
    raise HTTPException(status_code=401, detail="PIN sai")


@app.post("/api/auth/logout")
async def logout(token: str = Body(..., embed=True)):
    """Đăng xuất, huỷ session token."""
    SESSION_TOKENS.discard(token)
    return {"ok": True}


# ── Web Dashboard ─────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    index = _STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return HTMLResponse(
        "<h1>Robot Bi</h1>"
        "<p>Dashboard chưa có. Đặt file vào <code>src_brain/network/static/index.html</code></p>"
    )


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await _ws_manager.connect(websocket)
    # Gửi ngay 20 events chưa đọc gần nhất khi client vừa connect
    if _notifier:
        try:
            with _notifier._lock:
                unread = [e for e in _notifier._events if not e["read"]][-20:]
            for evt in unread:
                await websocket.send_json(evt)
        except Exception:
            pass
    try:
        while True:
            await websocket.receive_text()   # keep-alive
    except WebSocketDisconnect:
        _ws_manager.disconnect(websocket)


# ── REST: Status ──────────────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    notifier_stats = _notifier.get_stats() if _notifier else {}
    rag_stats = _rag.get_stats() if _rag else {}
    total_stars = _task_manager.get_total_stars() if _task_manager else 0
    return {
        "status": "online",
        "ws_clients": _ws_manager.count,
        "puppet_queued": _puppet_queue.qsize(),
        "notifier": notifier_stats,
        "rag": rag_stats,
        "total_stars": total_stars,
    }


# ── REST: Events ──────────────────────────────────────────────────────────────

@app.get("/api/events")
async def get_events(
    type: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 100,
    _auth: str = Depends(require_auth),
):
    if not _notifier:
        return {"events": [], "total": 0}
    with _notifier._lock:
        events = list(_notifier._events)
    if type:
        events = [e for e in events if e["type"] == type]
    if unread_only:
        events = [e for e in events if not e["read"]]
    result = events[-limit:]
    result = list(reversed(result))   # mới nhất lên trước
    return {"events": result, "total": len(events)}


@app.post("/api/events/read_all")
async def mark_read(_auth: str = Depends(require_auth)):
    if _notifier:
        _notifier.mark_all_read()
    return {"status": "ok"}


# ── REST: Chat Log ────────────────────────────────────────────────────────────

@app.get("/api/chats")
async def get_chats(limit: int = 50, _auth: str = Depends(require_auth)):
    if not _notifier:
        return {"chats": [], "total": 0}
    with _notifier._lock:
        events = list(_notifier._events)
    chats = [e for e in events if e["type"] == "chat"]
    result = list(reversed(chats[-limit:]))
    return {"chats": result, "total": len(chats)}


# ── REST: Memories ────────────────────────────────────────────────────────────

@app.get("/api/memories")
async def list_memories(_auth: str = Depends(require_auth)):
    if not _rag:
        return {"memories": [], "total": 0}
    memories = _rag.list_memories()
    return {"memories": memories, "total": len(memories)}


class MemoryIn(BaseModel):
    text: str


@app.post("/api/memories")
async def add_memory(body: MemoryIn, _auth: str = Depends(require_auth)):
    if not body.text.strip():
        raise HTTPException(400, "text không được rỗng")
    if not _rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _rag.add_manual_memory(body.text.strip())
    return {"status": "ok" if ok else "fail"}


class MemoryUpdate(BaseModel):
    text: str


# Export phải đứng trước /{memory_id} để không bị capture
@app.get("/api/memories/export")
async def export_memories(_auth: str = Depends(require_auth)):
    if not _rag:
        return []
    return _rag.export_memories()


@app.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate, _auth: str = Depends(require_auth)):
    if not _rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _rag.update_memory(memory_id, body.text)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str, _auth: str = Depends(require_auth)):
    if not _rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _rag.delete_memory(memory_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


# ── REST: Puppet ──────────────────────────────────────────────────────────────

class PuppetIn(BaseModel):
    text: str


@app.post("/api/puppet")
async def puppet_say(body: PuppetIn, _auth: str = Depends(require_auth)):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text không được rỗng")
    _puppet_queue.put(text)
    logger.info("[Puppet] Queued: '%s'", text[:60])
    return {"status": "queued", "text": text}


# ── REST: Camera MJPEG (SRS 4.1) ──────────────────────────────────────────────

async def _mjpeg_generator():
    """Generator yield MJPEG frames từ camera."""
    if not _CV2_AVAILABLE:
        # Placeholder khi không có opencv
        placeholder = (
            b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
            + b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            + b'\r\n'
        )
        while True:
            yield placeholder
            await asyncio.sleep(1.0)
        return

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        # Trả về frame placeholder khi không có camera
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blank, "Camera khong kha dung", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, jpg = cv2.imencode('.jpg', blank)
        frame_bytes = jpg.tobytes()
        while True:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + frame_bytes + b'\r\n')
            await asyncio.sleep(0.5)
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (640, 480))
            _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + jpg.tobytes() + b'\r\n')
            await asyncio.sleep(0.05)   # ~20fps
    finally:
        cap.release()


@app.get("/api/camera")
async def camera_stream(_auth: str = Depends(require_auth)):
    """Live MJPEG camera stream. Token có thể truyền qua query param ?auth=<token>"""
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )


# ── REST: Tasks (SRS 4.4) ─────────────────────────────────────────────────────

@app.get("/api/tasks")
async def get_tasks(_auth: str = Depends(require_auth)):
    if not _task_manager:
        return []
    return _task_manager.get_all()


@app.post("/api/tasks")
async def add_task(
    name: str = Body(...),
    remind_time: str = Body(...),
    _auth: str = Depends(require_auth),
):
    if not _task_manager:
        raise HTTPException(503, "Task manager chưa khởi động")
    return _task_manager.add_task(name, remind_time)


# stars phải đứng trước /{task_id} để không bị capture
@app.get("/api/tasks/stars")
async def get_stars(_auth: str = Depends(require_auth)):
    return {"total_stars": _task_manager.get_total_stars() if _task_manager else 0}


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str, _auth: str = Depends(require_auth)):
    if _task_manager and _task_manager.complete_task(task_id):
        return {"ok": True, "stars": _task_manager.get_total_stars()}
    raise HTTPException(404, "Task không tìm thấy hoặc đã hoàn thành")


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, _auth: str = Depends(require_auth)):
    if _task_manager and _task_manager.delete_task(task_id):
        return {"ok": True}
    raise HTTPException(404, "Task không tìm thấy")


# ── WebSocket: Audio Monitoring (Session K) ──────────────────────────────────

@app.websocket("/api/audio/stream")
async def audio_stream(websocket: WebSocket):
    """
    Stream audio từ mic phòng → browser (1 chiều).
    Format: PCM 16-bit little-endian, 16kHz, mono.
    Browser nhận raw PCM → phát qua Web Audio API.
    Auth qua query param: /api/audio/stream?auth=TOKEN
    """
    token = websocket.query_params.get("auth", "")
    if token not in SESSION_TOKENS:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info("[Bi - Tai Giam Sat] Client ket noi audio stream")

    if not _SD_AVAILABLE:
        logger.warning("[Bi - Tai Giam Sat] sounddevice/numpy khong co san — dong stream")
        await websocket.close(code=1011)
        return

    loop = asyncio.get_event_loop()
    audio_queue: asyncio.Queue = asyncio.Queue(maxsize=10)

    def audio_callback(indata, frames, time_info, status):
        """Callback sounddevice — chạy trong thread riêng."""
        # Convert float32 → int16 PCM
        pcm = (indata[:, 0] * 32767).astype(np.int16)
        raw_bytes = pcm.tobytes()
        try:
            loop.call_soon_threadsafe(audio_queue.put_nowait, raw_bytes)
        except asyncio.QueueFull:
            pass  # Drop frame nếu client chậm

    stream = None
    try:
        stream = sd.InputStream(
            samplerate=AUDIO_SAMPLE_RATE,
            channels=AUDIO_CHANNELS,
            dtype="float32",
            blocksize=AUDIO_CHUNK_FRAMES,
            device=AUDIO_MIC_DEVICE,
            callback=audio_callback,
        )
        stream.start()
        logger.info("[Bi - Tai Giam Sat] Bat dau stream audio mic")

        while True:
            try:
                raw_bytes = await asyncio.wait_for(audio_queue.get(), timeout=5.0)
                await websocket.send_bytes(raw_bytes)
            except asyncio.TimeoutError:
                # Gửi ping rỗng để giữ kết nối
                try:
                    await websocket.send_bytes(b"")
                except Exception:
                    break
            except Exception:
                break

    except Exception as e:
        logger.error("[Bi - Tai Giam Sat] Loi mic: %s", e)
    finally:
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        logger.info("[Bi - Tai Giam Sat] Client ngat ket noi audio stream")


# ── REST + WebSocket: Mom Direct Talk (Session L) ─────────────────────────────

def is_mom_talking() -> bool:
    """Public helper — main_loop.py import để check trạng thái mẹ."""
    return _mom_talking


@app.post("/api/mom/start")
async def mom_start_talking(_auth: str = Depends(require_auth)):
    """Mẹ bắt đầu nói — Bi tạm dừng AI, chờ nhận audio từ mẹ."""
    global _mom_talking
    _mom_talking = True
    logger.info("[Me] Me bat dau noi chuyen truc tiep")
    return {"status": "mom_talking", "message": "Bi đang nhường loa cho mẹ"}


@app.post("/api/mom/stop")
async def mom_stop_talking(_auth: str = Depends(require_auth)):
    """Mẹ dừng nói — Bi hoạt động bình thường lại."""
    global _mom_talking
    _mom_talking = False
    logger.info("[Me] Me ngung noi — Bi hoat dong binh thuong")
    return {"status": "bi_active", "message": "Bi đang hoạt động trở lại"}


@app.get("/api/mom/status")
async def mom_status():
    """Trả về trạng thái hiện tại (không cần auth — main_loop poll nội bộ)."""
    return {"mom_talking": _mom_talking}


@app.websocket("/api/mom/audio")
async def mom_audio_receive(websocket: WebSocket):
    """
    Nhận audio PCM float32 từ browser điện thoại mẹ → phát qua loa robot.
    Format: PCM float32, 16000Hz, mono (Web Audio API getUserMedia).
    Auth: /api/mom/audio?auth=TOKEN
    """
    global _mom_talking

    token = websocket.query_params.get("auth", "")
    if token not in SESSION_TOKENS:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _mom_audio_clients.append(websocket)
    logger.info("[Me] Ket noi audio tu dien thoai me")

    try:
        import pygame
        import numpy as np

        # Đảm bảo pygame mixer đã init (main_loop đã init, chỉ init nếu chưa có)
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=16000, size=-16, channels=1, buffer=512)

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=10.0)
                if not data or len(data) == 0:
                    continue
                if not _mom_talking:
                    continue  # Bỏ qua audio nếu mẹ chưa bật mic

                # Convert PCM float32 → int16 → ghi WAV tạm → phát qua pygame
                import wave
                import tempfile
                import os as _os

                float_array = np.frombuffer(data, dtype=np.float32)
                if len(float_array) == 0:
                    continue
                float_array = np.clip(float_array, -1.0, 1.0)
                int16_array = (float_array * 32767).astype(np.int16)

                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
                _os.close(tmp_fd)
                with wave.open(tmp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(int16_array.tobytes())

                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=16000, size=-16, channels=1, buffer=1024)
                sound = pygame.mixer.Sound(tmp_path)
                sound.set_volume(1.0)
                sound.play()

                async def _cleanup(path):
                    await asyncio.sleep(2)
                    try:
                        _os.unlink(path)
                    except Exception:
                        pass
                asyncio.create_task(_cleanup(tmp_path))

            except asyncio.TimeoutError:
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break
            except Exception as e:
                logger.error("[Me] Loi nhan audio: %s", e)
                break

    finally:
        if websocket in _mom_audio_clients:
            _mom_audio_clients.remove(websocket)
        logger.info("[Me] Ngat ket noi audio tu me")


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers — gọi từ thread khác (notifier)
# ═══════════════════════════════════════════════════════════════════════════════

def _broadcast_from_thread(event: dict) -> None:
    """
    Thread-safe: broadcast event tới tất cả WebSocket clients.
    Được gọi từ notifier._send_ws() (non-async thread).
    """
    if _api_loop and not _api_loop.is_closed():
        asyncio.run_coroutine_threadsafe(_ws_manager.broadcast(event), _api_loop)


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API — gọi từ main_loop.py
# ═══════════════════════════════════════════════════════════════════════════════

def init_server(notifier, rag_manager) -> None:
    """
    Inject dependencies từ main_loop.py.
    Gọi TRƯỚC start_api_server().

    Args:
        notifier:    EventNotifier singleton
        rag_manager: RAGManager singleton
    """
    global _notifier, _rag
    _notifier = notifier
    _rag = rag_manager
    notifier.set_ws_broadcaster(_broadcast_from_thread)
    logger.info("[API] Dependencies injected (notifier + rag).")


def get_puppet_queue() -> queue.Queue:
    """Trả về queue puppet để main_loop.py poll và đọc commands."""
    return _puppet_queue


def _start_cloudflare_tunnel(port: int, use_https: bool = False) -> None:
    """Khởi động cloudflared tunnel trong background thread."""
    def _run():
        try:
            result = subprocess.run(
                [_CLOUDFLARED_EXE, "--version"],
                capture_output=True, timeout=5
            )
            if result.returncode != 0:
                print("[Tunnel] cloudflared khong tim thay — bo qua tunnel")
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("[Tunnel] cloudflared chua cai — bo qua tunnel")
            print("[Tunnel] Tai tai: https://github.com/cloudflare/cloudflared/releases")
            return

        scheme = "https" if use_https else "http"
        print(f"[Tunnel] Dang khoi dong Cloudflare Tunnel -> {scheme}://localhost:{port}...")
        cmd = [_CLOUDFLARED_EXE, "tunnel", "--url", f"{scheme}://localhost:{port}"]
        if use_https:
            cmd.append("--no-tls-verify")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in proc.stdout:
                line = line.strip()
                if "trycloudflare.com" in line or "https://" in line:
                    urls = re.findall(r'https://[a-z0-9\-]+\.trycloudflare\.com', line)
                    if urls:
                        public_url = urls[0]
                        print("\n" + "="*60)
                        print(f"  URL CONG KHAI (dung tu bat cu dau):")
                        print(f"  {public_url}")
                        print("="*60 + "\n")
                        try:
                            import qrcode, io
                            qr = qrcode.QRCode(border=1)
                            qr.add_data(public_url)
                            qr.make(fit=True)
                            f = io.StringIO()
                            qr.print_ascii(out=f, invert=True)
                            print(f.getvalue())
                        except ImportError:
                            pass
        except Exception as e:
            print(f"[Tunnel] Loi: {e}")

    t = threading.Thread(target=_run, daemon=True, name="cloudflared-tunnel")
    t.start()


def _print_qr_code(ip: str, port: int = 8000, scheme: str = "http") -> None:
    """In QR code ra terminal để phụ huynh quét."""
    url = f"{scheme}://{ip}:{port}"
    try:
        import qrcode, io
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        f = io.StringIO()
        qr.print_ascii(out=f)
        print(f"\n{'='*50}")
        print(f"  Parent App: {url}")
        if scheme == "https":
            print(f"  (Lan dau bam 'Advanced' -> 'Proceed' vi self-signed cert)")
        print(f"  Quet QR tren dien thoai cung mang WiFi:")
        print(f.getvalue())
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

    if _CLOUDFLARED_ENABLED:
        _start_cloudflare_tunnel(actual_port, use_https)

    local_ip = get_local_ip()
    scheme = "https" if use_https else "http"
    _print_qr_code(local_ip, actual_port, scheme)
