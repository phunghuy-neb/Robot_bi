"""
state.py — Shared module-level state cho tất cả API routers Robot Bi.
Import module này thay vì import trực tiếp từ api_server.py để tránh circular imports.
"""
import asyncio
import json
import logging
import os
import queue
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger("api_server")

# ── Injected singletons (set bởi init_server / init_task_manager) ───────────
_notifier = None        # EventNotifier
_rag = None             # RAGManager
_task_manager = None    # TaskManager

# ── Runtime state ────────────────────────────────────────────────────────────
_puppet_queue: queue.Queue = queue.Queue()
_api_loop: Optional[asyncio.AbstractEventLoop] = None
_mom_talking: bool = False
_mom_audio_clients: list = []
_camera_frame: Optional[bytes] = None  # latest JPEG bytes, updated by camera thread

# ── PIN auth ──────────────────────────────────────────────────────────────────
AUTH_PIN: str = os.getenv("AUTH_PIN", "").strip()
SESSION_TOKENS: set = set()


def _normalize_family_id(family_id: Optional[str] = None) -> str:
    fid = (family_id or os.getenv("FAMILY_ID", "default")).strip()
    return fid or "default"


# ── WebSocket Connection Manager ──────────────────────────────────────────────

class ConnectionManager:
    """Thread-safe manager cho danh sách WebSocket clients."""

    def __init__(self):
        self._clients: list[WebSocket] = []
        self._client_families: dict[int, str] = {}

    async def connect(self, ws: WebSocket, family_id: Optional[str] = None) -> None:
        await ws.accept()
        self._clients.append(ws)
        self._client_families[id(ws)] = _normalize_family_id(family_id)
        logger.info("[WS] Client kết nối. Tổng: %d", len(self._clients))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._clients:
            self._clients.remove(ws)
        self._client_families.pop(id(ws), None)
        logger.info("[WS] Client ngắt kết nối. Tổng: %d", len(self._clients))

    async def broadcast(self, data: dict, family_id: Optional[str] = None) -> None:
        """Gửi JSON tới tất cả clients; tự loại bỏ client chết."""
        dead = []
        target_family = _normalize_family_id(family_id or data.get("family_id")) if (
            family_id or data.get("family_id")
        ) else None
        for client in list(self._clients):
            if target_family and self._client_families.get(id(client)) != target_family:
                continue
            try:
                await client.send_json(data)
            except Exception:
                dead.append(client)
        for c in dead:
            if c in self._clients:
                self._clients.remove(c)
            self._client_families.pop(id(c), None)

    @property
    def count(self) -> int:
        return len(self._clients)


_ws_manager = ConnectionManager()


# ── DB event helpers ──────────────────────────────────────────────────────────

def _event_row_to_dict(row) -> dict:
    metadata = row["metadata_json"]
    try:
        parsed_metadata = json.loads(metadata) if metadata else {}
    except Exception:
        parsed_metadata = {}
        return {
            "id": row["event_id"],
            "family_id": row["family_id"],
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
    family_id: Optional[str] = None,
):
    from src.infrastructure.database.db import get_db_connection
    where_parts = ["family_id = ?"]
    params = [_normalize_family_id(family_id)]

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
        SELECT family_id, event_id, timestamp, type, message, clip_path, metadata_json, is_read
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
    family_id: Optional[str] = None,
) -> int:
    from src.infrastructure.database.db import get_db_connection
    where_parts = ["family_id = ?"]
    params = [_normalize_family_id(family_id)]

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


# ── Thread-safe broadcast ─────────────────────────────────────────────────────

def _broadcast_from_thread(event: dict) -> None:
    """Thread-safe broadcast event tới tất cả WebSocket clients."""
    if _api_loop and not _api_loop.is_closed():
        asyncio.run_coroutine_threadsafe(_ws_manager.broadcast(event), _api_loop)


# ── Public helper (imported bởi main_loop.py qua api_server.py) ──────────────

def is_mom_talking() -> bool:
    """Trả về trạng thái mẹ đang nói — main_loop.py dùng để check."""
    return _mom_talking
