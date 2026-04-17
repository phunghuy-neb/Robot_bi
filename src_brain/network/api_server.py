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
import logging
import math
import os
import warnings
import queue
import re
import secrets
import socket
import subprocess
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

try:
    import numpy as np
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False

try:
    from scipy import signal as _scipy_signal
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


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

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from src_brain.network.db import add_turn, get_db_connection, get_session_turns
from src_brain.network.auth import get_current_user

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
AUTH_PIN = os.getenv("AUTH_PIN", "").strip()
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


def require_auth(
    authorization: Optional[str] = Header(None),
    auth: Optional[str] = Query(None),  # query param cho <img src>
) -> str:
    """Dependency: kiểm tra token hợp lệ từ header hoặc query param."""
    token = authorization or auth
    # Hỗ trợ cả "Bearer xxx" lẫn token thẳng
    if token and token.startswith("Bearer "):
        token = token[7:]
    if not token or token not in SESSION_TOKENS:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    return token


# get_current_user imported from src_brain.network.auth (Step 1.6)


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
import os as _os
_CLOUDFLARED_EXE = "cloudflared.exe" if _os.name == 'nt' else "cloudflared"

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


def _event_row_to_dict(row) -> dict:
    import json

    metadata = row["metadata_json"]
    try:
        parsed_metadata = json.loads(metadata) if metadata else {}
    except Exception:
        parsed_metadata = {}
    return {
        "id": row["event_id"],
        "timestamp": row["timestamp"],
        "type": row["type"],
        "message": row["message"],
        "clip_path": row["clip_path"],
        "metadata": parsed_metadata,
        "read": bool(row["is_read"]),
    }


def _fetch_events_from_db(
    event_type: Optional[str] = None,
    unread_only: bool = False,
    limit: Optional[int] = None,
    newest_first: bool = False,
):
    where_parts = []
    params = []

    if event_type:
        where_parts.append("type = ?")
        params.append(event_type)
    if unread_only:
        where_parts.append("is_read = 0")

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    order_sql = "DESC" if newest_first else "ASC"
    limit_sql = " LIMIT ?" if limit is not None else ""
    if limit is not None:
        params.append(limit)

    query = f"""
        SELECT event_id, timestamp, type, message, clip_path, metadata_json, is_read
        FROM events
        {where_sql}
        ORDER BY db_id {order_sql}{limit_sql}
    """
    with get_db_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_event_row_to_dict(row) for row in rows]


def _count_events_from_db(
    event_type: Optional[str] = None,
    unread_only: bool = False,
) -> int:
    where_parts = []
    params = []

    if event_type:
        where_parts.append("type = ?")
        params.append(event_type)
    if unread_only:
        where_parts.append("is_read = 0")

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    query = f"SELECT COUNT(*) AS total FROM events {where_sql}"
    with get_db_connection() as conn:
        row = conn.execute(query, tuple(params)).fetchone()
    return int(row["total"]) if row else 0


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


@app.get("/health")
async def health():
    """Health check — khong can auth."""
    return {"status": "ok"}


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(request: Request, pin: str = Body(..., embed=True)):
    """Đăng nhập bằng PIN. Trả về session token. Rate-limited: 5 lần sai → khóa 15 phút."""
    client_ip = request.client.host
    now = datetime.now(timezone.utc)

    with get_db_connection() as conn:
        # Cleanup: reset các record đã hết hạn lock (locked_until <= now)
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE locked_until IS NOT NULL AND locked_until <= ?",
            (now.isoformat(),),
        )
        conn.commit()

        # Kiểm tra xem IP có đang bị lock không
        row = conn.execute(
            "SELECT attempt_count, locked_until FROM login_attempts WHERE ip_address = ?",
            (client_ip,),
        ).fetchone()

        if row and row["locked_until"]:
            locked_until_str = row["locked_until"]
            locked_until = datetime.fromisoformat(locked_until_str)
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Quá nhiều lần thử. Vui lòng thử lại sau {remaining_minutes} phút.",
                )

        # Kiểm tra PIN
        if pin == AUTH_PIN:
            # PIN đúng: reset record của IP này
            conn.execute(
                "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
                "WHERE ip_address = ?",
                (client_ip,),
            )
            conn.commit()
            token = secrets.token_hex(16)
            SESSION_TOKENS.add(token)
            logger.info("[Auth] Login thành công. Tokens active: %d", len(SESSION_TOKENS))
            return {"token": token}

        # PIN sai: tăng attempt_count
        if row:
            current_count = row["attempt_count"] or 0
            new_count = current_count + 1
            if new_count >= 5:
                locked_until_val = (now + timedelta(minutes=15)).isoformat()
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = ?, locked_until = ? "
                    "WHERE ip_address = ?",
                    (new_count, locked_until_val, client_ip),
                )
            elif current_count == 0:
                # Lần sai đầu tiên của chu kỳ mới (sau khi cleanup reset về 0) — set first_attempt_at
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = 1, first_attempt_at = ? "
                    "WHERE ip_address = ?",
                    (now.isoformat(), client_ip),
                )
            else:
                # Lần sai tiếp theo trong cùng chu kỳ — KHÔNG cập nhật first_attempt_at
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = ? WHERE ip_address = ?",
                    (new_count, client_ip),
                )
        else:
            # Row chưa tồn tại — lần sai đầu tiên, set first_attempt_at
            conn.execute(
                "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                "VALUES (?, 1, ?, NULL)",
                (client_ip, now.isoformat()),
            )
        conn.commit()

    raise HTTPException(status_code=401, detail="PIN sai")


@app.post("/auth/register")
async def register_user(request: Request):
    """Đăng ký tài khoản username + password mới."""
    from src_brain.network.auth import create_user

    body = await request.json()
    username: str = body.get("username", "").strip()
    password: str = body.get("password", "")
    family_name: str = body.get("family_name", "").strip()

    # Validation username: 3-50 ký tự, chỉ a-zA-Z0-9_
    import re as _re
    if not username or not _re.fullmatch(r"[a-zA-Z0-9_]{3,50}", username):
        raise HTTPException(
            status_code=422,
            detail="username phai tu 3-50 ky tu, chi duoc dung a-zA-Z0-9_",
        )
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="password phai co it nhat 8 ky tu")
    if not family_name:
        raise HTTPException(status_code=422, detail="family_name khong duoc de trong")

    return create_user(username, password, family_name)


@app.post("/auth/login/v2")
async def login_v2(request: Request):
    """
    Đăng nhập bằng username + password.
    Rate limiting: 5 lần sai theo username → khóa 15 phút.
    Trả về JWT access_token (60 phút) + refresh_token (30 ngày).
    """
    from src_brain.network.auth import (
        authenticate_user,
        create_access_token,
        create_refresh_token,
        store_refresh_token,
    )

    body = await request.json()
    username: str = body.get("username", "").strip()
    password: str = body.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=422, detail="Thieu username hoac password")

    rate_key = f"user:{username}"
    now = datetime.now(timezone.utc)
    authenticated_user = None

    with get_db_connection() as conn:
        # Cleanup record hết hạn lock
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE locked_until IS NOT NULL AND locked_until <= ?",
            (now.isoformat(),),
        )
        conn.commit()

        row = conn.execute(
            "SELECT attempt_count, locked_until FROM login_attempts WHERE ip_address = ?",
            (rate_key,),
        ).fetchone()

        if row and row["locked_until"]:
            locked_until_str = row["locked_until"]
            locked_until = datetime.fromisoformat(locked_until_str)
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Quá nhiều lần thử. Vui lòng thử lại sau {remaining_minutes} phút.",
                )

        user = authenticate_user(username, password)

        if user:
            # Đúng: reset rate limit record
            conn.execute(
                "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
                "WHERE ip_address = ?",
                (rate_key,),
            )
            conn.commit()
            authenticated_user = user
        else:
            # Sai: tăng attempt_count
            if row:
                current_count = row["attempt_count"] or 0
                new_count = current_count + 1
                if new_count >= 5:
                    locked_until_val = (now + timedelta(minutes=15)).isoformat()
                    conn.execute(
                        "UPDATE login_attempts SET attempt_count = ?, locked_until = ? "
                        "WHERE ip_address = ?",
                        (new_count, locked_until_val, rate_key),
                    )
                elif current_count == 0:
                    conn.execute(
                        "UPDATE login_attempts SET attempt_count = 1, first_attempt_at = ? "
                        "WHERE ip_address = ?",
                        (now.isoformat(), rate_key),
                    )
                else:
                    conn.execute(
                        "UPDATE login_attempts SET attempt_count = ? WHERE ip_address = ?",
                        (new_count, rate_key),
                    )
            else:
                conn.execute(
                    "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                    "VALUES (?, 1, ?, NULL)",
                    (rate_key, now.isoformat()),
                )
            conn.commit()

    if not authenticated_user:
        raise HTTPException(status_code=401, detail="Sai ten dang nhap hoac mat khau")

    # Tạo JWT access token + refresh token
    access_token = create_access_token(
        str(authenticated_user["user_id"]), authenticated_user["family_name"]
    )
    raw_refresh, hashed_refresh = create_refresh_token(str(authenticated_user["user_id"]))
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    store_refresh_token(str(authenticated_user["user_id"]), hashed_refresh, refresh_expires_at)

    logger.info("[Auth v2] Login thanh cong: user_id=%s", authenticated_user["user_id"])
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@app.post("/auth/refresh")
async def refresh_token_endpoint(request: Request):
    """
    Đổi refresh token lấy access token + refresh token mới (rotation).
    Body: {"refresh_token": str}
    """
    from src_brain.network.auth import rotate_refresh_token, create_access_token

    body = await request.json()
    old_refresh = body.get("refresh_token", "").strip()

    if not old_refresh:
        raise HTTPException(status_code=422, detail="Thieu refresh_token")

    new_raw, _new_hashed, user_id = rotate_refresh_token(old_refresh)

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT family_name FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="User khong ton tai")

    new_access = create_access_token(user_id, row["family_name"])

    return {
        "access_token": new_access,
        "refresh_token": new_raw,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@app.post("/auth/logout")
async def logout_v2(request: Request, _current_user: dict = Depends(get_current_user)):
    """
    Đăng xuất JWT: verify access token → revoke refresh token của chính user đó.
    Header: Authorization: Bearer <access_token>
    Body: {"refresh_token": str}
    """
    import hashlib as _hl
    from src_brain.network.auth import verify_access_token

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thieu Authorization: Bearer <token>")
    access_token = authorization[7:]

    payload = verify_access_token(access_token)
    user_id = str(payload.get("sub", ""))

    body = await request.json()
    refresh_token_str = body.get("refresh_token", "").strip()
    if not refresh_token_str:
        raise HTTPException(status_code=422, detail="Thieu refresh_token")

    hashed = _hl.sha256(refresh_token_str.encode()).hexdigest()

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_id, user_id FROM auth_tokens "
            "WHERE refresh_token_hash = ? AND is_revoked = 0",
            (hashed,),
        ).fetchone()

        if not row or str(row["user_id"]) != user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token",
            )

        conn.execute(
            "UPDATE auth_tokens SET is_revoked = 1 WHERE token_id = ?",
            (row["token_id"],),
        )
        conn.commit()

    return {"message": "Đã đăng xuất"}


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
    token = websocket.query_params.get("token", "")
    try:
        from src_brain.network.auth import verify_access_token
        verify_access_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    await _ws_manager.connect(websocket)
    # Gửi ngay 20 events chưa đọc gần nhất khi client vừa connect
    if _notifier:
        try:
            unread = _fetch_events_from_db(unread_only=True, limit=20, newest_first=True)
            unread.reverse()
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
    _current_user: dict = Depends(get_current_user),
):
    if not _notifier:
        return {"events": [], "total": 0}
    events = _fetch_events_from_db(
        event_type=type,
        unread_only=unread_only,
        limit=limit,
        newest_first=True,
    )
    total = _count_events_from_db(event_type=type, unread_only=unread_only)
    return {"events": events, "total": total}
    result = list(reversed(result))   # mới nhất lên trước
    return {"events": result, "total": len(events)}


@app.post("/api/events/read_all")
async def mark_read(_current_user: dict = Depends(get_current_user)):
    if _notifier:
        _notifier.mark_all_read()
    return {"status": "ok"}


# ── REST: Chat Log ────────────────────────────────────────────────────────────

@app.get("/api/chats")
async def get_chats(limit: int = 50, _current_user: dict = Depends(get_current_user)):
    if not _notifier:
        return {"chats": [], "total": 0}
    chats = _fetch_events_from_db(
        event_type="chat",
        unread_only=False,
        limit=limit,
        newest_first=True,
    )
    total = _count_events_from_db(event_type="chat", unread_only=False)
    return {"chats": chats, "total": total}


# ── REST: Memories ────────────────────────────────────────────────────────────

class HomeworkTurnIn(BaseModel):
    content: str


#  Conversation Threads (Phase 2)

@app.get("/api/conversations")
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    _current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT session_id, title, started_at, ended_at, turn_count
            FROM conversations
            WHERE family_id = ?
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            ("default", limit, offset),
        ).fetchall()
        total_row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM conversations
            WHERE family_id = ?
            """,
            ("default",),
        ).fetchone()

    conversations = [
        {
            "session_id": row["session_id"],
            "title": row["title"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "turn_count": row["turn_count"],
        }
        for row in rows
    ]
    total = int(total_row["total"]) if total_row else 0
    return {"conversations": conversations, "total": total}


@app.get("/api/conversations/{session_id}")
async def get_conversation(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT session_id, family_id, title, started_at, ended_at, turn_count
            FROM conversations
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, "default"),
        ).fetchone()

    if not row:
        raise HTTPException(404, "Conversation khong tim thay")

    return {
        "session": {
            "session_id": row["session_id"],
            "family_id": row["family_id"],
            "title": row["title"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "turn_count": row["turn_count"],
        },
        "turns": get_session_turns(session_id),
    }


@app.delete("/api/conversations/{session_id}")
async def delete_conversation(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT session_id
            FROM conversations
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, "default"),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Conversation khong tim thay")

        conn.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
        conn.execute(
            "DELETE FROM conversations WHERE session_id = ? AND family_id = ?",
            (session_id, "default"),
        )
        conn.commit()

    return {"ok": True}


@app.post("/api/conversations/{session_id}/homework")
async def add_homework_turn(
    session_id: str,
    body: HomeworkTurnIn,
    _current_user: dict = Depends(get_current_user),
):
    content = body.content.strip()
    if not content:
        raise HTTPException(400, "content khong duoc rong")

    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT session_id
            FROM conversations
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, "default"),
        ).fetchone()

    if not row:
        raise HTTPException(404, "Conversation khong tim thay")

    turn_id = add_turn(session_id, "homework", content)
    return {"turn_id": turn_id, "session_id": session_id}


@app.get("/api/memories")
async def list_memories(_current_user: dict = Depends(get_current_user)):
    if not _rag:
        return {"memories": [], "total": 0}
    memories = _rag.list_memories()
    return {"memories": memories, "total": len(memories)}


class MemoryIn(BaseModel):
    text: str


@app.post("/api/memories")
async def add_memory(body: MemoryIn, _current_user: dict = Depends(get_current_user)):
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
async def export_memories(_current_user: dict = Depends(get_current_user)):
    if not _rag:
        return []
    return _rag.export_memories()


@app.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate, _current_user: dict = Depends(get_current_user)):
    if not _rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _rag.update_memory(memory_id, body.text)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str, _current_user: dict = Depends(get_current_user)):
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
async def puppet_say(body: PuppetIn, _current_user: dict = Depends(get_current_user)):
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text không được rỗng")
    _puppet_queue.put(text)
    logger.info("[Puppet] Queued: '%s'", text[:60])
    return {"status": "queued", "text": text}


# ── REST: Camera MJPEG (SRS 4.1) ──────────────────────────────────────────────

def _camera_capture_thread(frame_queue: queue.Queue, stop_event: threading.Event):
    """Thread riêng capture frame — không block event loop."""
    import time as _time
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        stop_event.set()
        return

    # Buffer = 1 để luôn lấy frame mới nhất, tránh frame cũ tích lũy
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

        # Chỉ giữ frame mới nhất — xóa frame cũ nếu queue đầy
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
                # Lấy frame từ thread qua executor — không block event loop
                frame_bytes = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: frame_queue.get(timeout=0.1),
                )
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + frame_bytes + b'\r\n')
                await asyncio.sleep(0)   # yield control về event loop
            except queue.Empty:
                await asyncio.sleep(0.033)   # 30fps target nếu chưa có frame
            except GeneratorExit:
                break
    finally:
        stop_event.set()


@app.get("/api/camera")
async def camera_stream(_current_user: dict = Depends(_camera_auth)):
    """Live MJPEG camera stream. Token co the truyen qua query param ?auth=<JWT>"""
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )


# ── REST: Tasks (SRS 4.4) ─────────────────────────────────────────────────────

@app.get("/api/tasks")
async def get_tasks(_current_user: dict = Depends(get_current_user)):
    if not _task_manager:
        return []
    return _task_manager.get_all()


@app.post("/api/tasks")
async def add_task(
    name: str = Body(...),
    remind_time: str = Body(...),
    _current_user: dict = Depends(get_current_user),
):
    if not _task_manager:
        raise HTTPException(503, "Task manager chưa khởi động")
    return _task_manager.add_task(name, remind_time)


# stars phải đứng trước /{task_id} để không bị capture
@app.get("/api/tasks/stars")
async def get_stars(_current_user: dict = Depends(get_current_user)):
    return {"total_stars": _task_manager.get_total_stars() if _task_manager else 0}


@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str, _current_user: dict = Depends(get_current_user)):
    if _task_manager and _task_manager.complete_task(task_id):
        return {"ok": True, "stars": _task_manager.get_total_stars()}
    raise HTTPException(404, "Task không tìm thấy hoặc đã hoàn thành")


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, _current_user: dict = Depends(get_current_user)):
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
    Auth qua query param: /api/audio/stream?token=JWT_ACCESS_TOKEN
    """
    token = websocket.query_params.get("token", "")
    try:
        from src_brain.network.auth import verify_access_token
        verify_access_token(token)
    except Exception:
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
async def mom_start_talking(_current_user: dict = Depends(get_current_user)):
    """Mẹ bắt đầu nói — Bi tạm dừng AI, chờ nhận audio từ mẹ."""
    global _mom_talking
    _mom_talking = True
    print("[Me] ===== ME BAT DAU NOI — BI TAM DUNG =====")
    logger.info("[Me] Me bat dau noi chuyen truc tiep")
    return {"status": "mom_talking", "message": "Bi đang nhường loa cho mẹ"}


@app.post("/api/mom/stop")
async def mom_stop_talking(_current_user: dict = Depends(get_current_user)):
    """Mẹ dừng nói — Bi hoạt động bình thường lại."""
    global _mom_talking
    _mom_talking = False
    print("[Me] ===== ME DUNG NOI — BI HOAT DONG LAI =====")
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
    Auth: /api/mom/audio?token=JWT_ACCESS_TOKEN
    """
    global _mom_talking

    token = websocket.query_params.get("token", "")
    try:
        from src_brain.network.auth import verify_access_token
        verify_access_token(token)
    except Exception:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _mom_audio_clients.append(websocket)
    logger.info("[Me] Ket noi audio tu dien thoai me")

    # Khởi tạo pygame Sound channel riêng cho audio mẹ
    # Channel 7 — không đụng channel music của Bi (Bi dùng mixer.music)
    import pygame
    import numpy as np
    import io as _io
    import wave as _wave

    MOM_CHANNEL = 7  # Channel riêng, không xung đột TTS Bi

    def _get_mixer_freq():
        """Lấy sample rate thực tế của mixer (44100Hz nếu mouth_tts đã init)."""
        info = pygame.mixer.get_init()
        return info[0] if info else 44100

    # Fallback nếu mixer chưa init (mouth_tts chưa chạy)
    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.init()

    # Đảm bảo đủ channels
    if pygame.mixer.get_num_channels() <= MOM_CHANNEL:
        pygame.mixer.set_num_channels(MOM_CHANNEL + 1)

    mom_channel = pygame.mixer.Channel(MOM_CHANNEL)

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_bytes(), timeout=10.0
                )
                if not data or len(data) == 0:
                    continue
                if not _mom_talking:
                    continue

                # Parse float32 PCM từ browser (16000Hz mono)
                float_array = np.frombuffer(data, dtype=np.float32)
                if len(float_array) < 16:
                    continue
                float_array = np.clip(float_array, -1.0, 1.0)

                # Lấy sample rate mixer hiện tại (thường 44100Hz)
                mixer_freq = _get_mixer_freq()
                src_freq = 16000  # browser luôn gửi 16000Hz

                # Resample 16000 → mixer_freq nếu cần
                if mixer_freq != src_freq:
                    if _SCIPY_AVAILABLE:
                        num_samples = int(len(float_array) * mixer_freq / src_freq)
                        float_array = _scipy_signal.resample(float_array, num_samples)
                    else:
                        # numpy fallback khi không có scipy
                        num_samples = int(len(float_array) * mixer_freq / src_freq)
                        indices = np.linspace(0, len(float_array) - 1, num_samples)
                        float_array = np.interp(indices, np.arange(len(float_array)), float_array)

                # Convert float32 → int16
                int16_mono = (float_array * 32767).astype(np.int16)

                # Convert mono → stereo nếu mixer dùng stereo
                mixer_channels = pygame.mixer.get_init()[2] if pygame.mixer.get_init() else 2
                if mixer_channels == 2:
                    int16_stereo = np.column_stack([int16_mono, int16_mono])
                    pcm_bytes = int16_stereo.tobytes()
                else:
                    pcm_bytes = int16_mono.tobytes()

                # Tạo WAV trong memory với đúng sample rate — KHÔNG ghi file
                buf = _io.BytesIO()
                with _wave.open(buf, 'wb') as wf:
                    wf.setnchannels(mixer_channels)
                    wf.setsampwidth(2)
                    wf.setframerate(mixer_freq)
                    wf.writeframes(pcm_bytes)
                buf.seek(0)

                # Phát qua pygame Sound từ buffer
                sound = pygame.mixer.Sound(buf)
                sound.set_volume(1.0)
                mom_channel.play(sound)

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
                            print(_build_ascii_qr(public_url, invert=True))
                        except ImportError:
                            pass
        except Exception as e:
            print(f"[Tunnel] Loi: {e}")

    t = threading.Thread(target=_run, daemon=True, name="cloudflared-tunnel")
    t.start()


def _build_ascii_qr(data: str, border: int = 1, invert: bool = False) -> str:
    """Render QR code bang ky tu ASCII thuan va ANSI color de hien thi ro rang."""
    import os
    import qrcode

    # Bat ANSI escape codes tren Windows cmd/powershell
    if os.name == 'nt':
        os.system("")

    qr = qrcode.QRCode(border=border)
    qr.add_data(data)
    qr.make(fit=True)

    matrix = qr.get_matrix()
    
    # Su dung ANSI background colors (47=Trang, 40=Den)
    # Dung 2 dau cach (spaces) de tao thanh khoi vuong
    white = "\033[47m  \033[0m"
    black = "\033[40m  \033[0m"

    # Mac dinh in chu den nen trang de camera phone de dang nhan dien
    # Giam rui ro loi khi scan tu man hinh terminal
    # Tham so `invert` chi la thu tuc de khong bi crash voi nhung code goi ham cu.
    dark = black
    light = white

    return "\n".join(
        "".join(dark if cell else light for cell in row)
        for row in matrix
    )


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
    if not AUTH_PIN:
        raise Exception(
            "[Auth] FATAL: AUTH_PIN chưa được cấu hình trong .env. "
            "Server không thể khởi động. Thêm AUTH_PIN=<pin> vào file .env rồi thử lại."
        )

    # Validate JWT config tại startup — raise RuntimeError nếu thiếu
    from src_brain.network.auth import _get_jwt_config
    _get_jwt_config()  # Raise RuntimeError nếu JWT_SECRET_KEY thiếu hoặc sai algorithm

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
