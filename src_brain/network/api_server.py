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
import secrets
import socket
import threading
from pathlib import Path
from typing import Optional


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


def _print_qr_code(ip: str, port: int = 8000) -> None:
    """In QR code ra terminal để phụ huynh quét."""
    url = f"http://{ip}:{port}"
    try:
        import qrcode, io
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        f = io.StringIO()
        qr.print_ascii(out=f)
        print(f"\n{'='*50}")
        print(f"  Parent App: {url}")
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
    def _run():
        uvicorn.run(app, host=host, port=port, log_level="warning")

    t = threading.Thread(target=_run, daemon=True, name="api-server")

    t.start()

    local_ip = get_local_ip()
    _print_qr_code(local_ip, port)
