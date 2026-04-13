"""
api_server.py — Robot Bi: FastAPI Parent App Backend (Sprint 5)
===============================================================
SRS Phần 4: Ứng dụng phụ huynh — REST API + WebSocket + Web Dashboard

Truy cập: http://<IP_robot>:8000 từ browser trên phone cùng mạng LAN
Khởi động: gọi init_server() rồi start_api_server() từ main_loop.py

Endpoints:
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
"""

import asyncio
import logging
import queue
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

logger = logging.getLogger("api_server")

# ── Module-level state (injected bởi main_loop.py trước khi start) ────────────
_notifier = None       # EventNotifier instance
_rag = None            # RAGManager instance
_puppet_queue: queue.Queue = queue.Queue()
_api_loop: Optional[asyncio.AbstractEventLoop] = None

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

app = FastAPI(title="Robot Bi — Parent App API", version="1.0")

# Mount thư mục static
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.on_event("startup")
async def _on_startup():
    global _api_loop
    _api_loop = asyncio.get_event_loop()
    logger.info("[API] FastAPI server started. Event loop captured.")


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
    return {
        "status": "online",
        "ws_clients": _ws_manager.count,
        "puppet_queued": _puppet_queue.qsize(),
        "notifier": notifier_stats,
        "rag": rag_stats,
    }


# ── REST: Events ──────────────────────────────────────────────────────────────

@app.get("/api/events")
async def get_events(
    type: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 100,
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
async def mark_read():
    if _notifier:
        _notifier.mark_all_read()
    return {"status": "ok"}


# ── REST: Chat Log ────────────────────────────────────────────────────────────

@app.get("/api/chats")
async def get_chats(limit: int = 50):
    if not _notifier:
        return {"chats": [], "total": 0}
    with _notifier._lock:
        events = list(_notifier._events)
    chats = [e for e in events if e["type"] == "chat"]
    result = list(reversed(chats[-limit:]))
    return {"chats": result, "total": len(chats)}


# ── REST: Memories ────────────────────────────────────────────────────────────

@app.get("/api/memories")
async def list_memories():
    if not _rag:
        return {"memories": [], "total": 0}
    memories = _rag.list_memories()
    return {"memories": memories, "total": len(memories)}


class MemoryIn(BaseModel):
    text: str


@app.post("/api/memories")
async def add_memory(body: MemoryIn):
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
async def export_memories():
    if not _rag:
        return []
    return _rag.export_memories()


@app.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate):
    if not _rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _rag.update_memory(memory_id, body.text)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str):
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
async def puppet_say(body: PuppetIn):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text không được rỗng")
    _puppet_queue.put(text)
    logger.info("[Puppet] Queued: '%s'", text[:60])
    return {"status": "queued", "text": text}


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


def start_api_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Khởi động FastAPI + uvicorn trong background daemon thread.
    Non-blocking — không ảnh hưởng đến main_loop.py.
    """
    def _run():
        uvicorn.run(app, host=host, port=port, log_level="warning")

    t = threading.Thread(target=_run, daemon=True, name="api-server")
    t.start()
    print(f"[Hệ thống] Parent App: http://localhost:{port}")
    print(f"[Hệ thống] Truy cập từ điện thoại: http://<IP_máy>:{port}")
