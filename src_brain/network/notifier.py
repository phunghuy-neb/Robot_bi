"""
notifier.py - Robot Bi: WebSocket notification stub (Sprint 5 prep)
===================================================================
SRS 3.4: Gui notification kem thumbnail clip qua LAN den Parent App
SRS 4.2: Thu vien clip su kien + Nhat ky chat
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

from src_brain.network.db import get_db_connection

logger = logging.getLogger("notifier")

EventType = Literal["motion", "stranger", "known_face", "cry", "chat", "system"]

_MAX_EVENTS = 500
_WS_ENABLED = False

# Module-level WebSocket broadcaster (injects vào từ api_server.init_server)
_ws_broadcast_fn = None  # callable | None


def set_ws_broadcaster(fn) -> None:
    """Đăng ký coroutine function để broadcast notification qua WebSocket."""
    global _ws_broadcast_fn, _WS_ENABLED
    _ws_broadcast_fn = fn
    _WS_ENABLED = (fn is not None)


class EventNotifier:
    """
    Gui notifications ve events den Parent App.

    Persistence da duoc chuyen sang SQLite, nhung interface giu nguyen.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._connected_clients: list = []
        self._ws_broadcaster = None
        self._queue_file = Path(__file__).with_name("event_queue.json")
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[dict] = self._load_queue()
        mode = "WebSocket" if _WS_ENABLED else "SQLite persistence"
        logger.info(
            "[Notifier] Khoi tao (mode: %s) - %d events trong queue",
            mode,
            len(self._events),
        )

    @staticmethod
    def _row_to_event(row) -> dict:
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

    def push_event(
        self,
        event_type: EventType,
        message: str,
        clip_path: str | None = None,
        metadata: dict | None = None,
    ) -> bool:
        event = {
            "id": f"{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "clip_path": clip_path,
            "metadata": metadata or {},
            "read": False,
        }

        with self._lock:
            self._insert_event(event)
            self._events = self._load_queue()

        if _ws_broadcast_fn:
            try:
                import src_brain.network.state as _st
                loop = _st._api_loop
                if loop and not loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        _ws_broadcast_fn(
                            {"type": "notification", "event_type": event_type, "message": message}
                        ),
                        loop,
                    )
            except Exception:
                logger.debug("[Notifier] WS broadcast skip — loop chua san sang")

        icons = {
            "motion": "[MOT]",
            "stranger": "[STR]",
            "cry": "[CRY]",
            "known_face": "[FAC]",
            "chat": "[CHT]",
            "system": "[SYS]",
        }
        icon = icons.get(event_type, "[EVT]")
        if event_type == "chat":
            logger.debug("[Notifier] %s CHAT event stored", icon)
        else:
            logger.info("[Notifier] %s %s: %s", icon, event_type.upper(), message)
        self._send_ws(event)
        return True

    def push_chat_log(self, user_text: str, bi_response: str) -> bool:
        logger.info("[Chat] session=%s user_len=%d ai_len=%d", "unknown", len(user_text), len(bi_response))
        return self.push_event(
            event_type="chat",
            message=f"Be: {user_text[:100]}",
            metadata={
                "user_text": user_text,
                "bi_response": bi_response,
                "word_count": len(user_text.split()),
            },
        )

    def get_unread_events(self, event_type: EventType | None = None) -> list[dict]:
        with self._lock:
            query = """
                SELECT event_id, timestamp, type, message, clip_path, metadata_json, is_read
                FROM events
                WHERE is_read = 0
            """
            params = []
            if event_type:
                query += " AND type = ?"
                params.append(event_type)
            query += " ORDER BY db_id ASC"
            with get_db_connection() as conn:
                rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_event(row) for row in rows]

    def mark_all_read(self) -> None:
        with self._lock:
            with get_db_connection() as conn:
                conn.execute("UPDATE events SET is_read = 1 WHERE is_read = 0")
                conn.commit()
            for event in self._events:
                event["read"] = True

    def get_stats(self) -> dict:
        with self._lock:
            with get_db_connection() as conn:
                total_row = conn.execute(
                    "SELECT COUNT(*) AS total_events FROM events"
                ).fetchone()
                unread_row = conn.execute(
                    "SELECT COUNT(*) AS unread FROM events WHERE is_read = 0"
                ).fetchone()
            return {
                "total_events": int(total_row["total_events"]) if total_row else 0,
                "unread": int(unread_row["unread"]) if unread_row else 0,
                "ws_enabled": _WS_ENABLED,
                "queue_file": str(self._queue_file),
            }

    def _load_queue(self) -> list[dict]:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT event_id, timestamp, type, message, clip_path, metadata_json, is_read
                FROM events
                ORDER BY db_id ASC
                """
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def _insert_event(self, event: dict) -> None:
        import_key = f"{event['id']}|{event['timestamp']}"
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id, timestamp, type, message, clip_path,
                    metadata_json, is_read, import_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["id"],
                    event["timestamp"],
                    event["type"],
                    event["message"],
                    event["clip_path"],
                    json.dumps(event["metadata"], ensure_ascii=False),
                    1 if event["read"] else 0,
                    import_key,
                ),
            )
            conn.execute(
                """
                DELETE FROM events
                WHERE db_id NOT IN (
                    SELECT db_id FROM events ORDER BY db_id DESC LIMIT ?
                )
                """,
                (_MAX_EVENTS,),
            )
            conn.commit()

    def set_ws_broadcaster(self, broadcaster_fn) -> None:
        self._ws_broadcaster = broadcaster_fn
        logger.info("[Notifier] WS broadcaster da dang ky.")

    def _send_ws(self, event: dict) -> None:
        if self._ws_broadcaster:
            try:
                self._ws_broadcaster(event)
            except Exception as exc:
                logger.debug("[Notifier] _send_ws loi: %s", exc)


_notifier_instance: EventNotifier | None = None


def get_notifier() -> EventNotifier:
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = EventNotifier()
    return _notifier_instance


if __name__ == "__main__":
    from src_brain.network.db import init_db

    init_db()
    notifier = get_notifier()
    notifier.push_event("motion", "Test motion event", clip_path="/tmp/test.mp4")
    notifier.push_event("stranger", "Phat hien nguoi la")
    notifier.push_chat_log("ten toi la An", "Bi nho roi, ban ten An!")
    print(f"Stats: {notifier.get_stats()}")
    print(f"Unread events: {len(notifier.get_unread_events())}")
    print("Test PASS")
