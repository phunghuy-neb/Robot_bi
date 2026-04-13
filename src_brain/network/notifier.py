"""
notifier.py — Robot Bi: WebSocket Notification Stub (Sprint 5 prep)
====================================================================
SRS 3.4: "Gui notification kem thumbnail clip qua LAN den Parent App"
SRS 4.2: "Thu vien clip su kien" + "Nhat ky chat"

TRANG THAI HIEN TAI: STUB
  - Luu events vao local JSON queue (src_brain/network/event_queue.json)
  - Khi Sprint 5 implement WebSocket server → chi can thay _send_ws() method
  - Interface khong thay doi → main_loop.py khong can sua khi upgrade

Upgrade path (Sprint 5):
  - Them: asyncio WebSocket server (websockets lib)
  - Thay: _send_ws() gui that thay vi luu file
  - Giu nguyen: push_event() interface
"""

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger("notifier")

# ── Types ─────────────────────────────────────────────────────────────────────
EventType = Literal["motion", "stranger", "known_face", "cry", "chat", "system"]

# ── Cấu hình ─────────────────────────────────────────────────────────────────
_QUEUE_FILE  = Path("src_brain/network/event_queue.json")
_MAX_EVENTS  = 500    # Giữ tối đa 500 events trong queue
_WS_ENABLED  = False  # Set True khi Sprint 5 implement WebSocket server


class EventNotifier:
    """
    Gửi notifications về events đến Parent App.

    Stub mode: lưu vào local JSON queue (event_queue.json).
    Production mode (Sprint 5): gửi qua WebSocket LAN.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._connected_clients: list = []  # Placeholder cho Sprint 5
        self._ws_broadcaster = None         # Set bởi api_server.init_server()
        self._queue_file = _QUEUE_FILE
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing queue
        self._events: list[dict] = self._load_queue()
        mode = "WebSocket" if _WS_ENABLED else "Local JSON stub"
        logger.info(
            "[Notifier] Khoi tao (mode: %s) — %d events trong queue",
            mode,
            len(self._events),
        )

    def push_event(
        self,
        event_type: EventType,
        message: str,
        clip_path: str | None = None,
        metadata: dict | None = None,
    ) -> bool:
        """
        Gửi notification về một sự kiện.

        Args:
            event_type: Loại sự kiện ("motion", "stranger", "cry", etc.)
            message:    Mô tả ngắn gọn
            clip_path:  Đường dẫn clip MP4 (nếu có)
            metadata:   Data bổ sung (tùy chọn)

        Returns:
            True nếu đã xử lý thành công
        """
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
            self._events.append(event)
            # Giữ tối đa _MAX_EVENTS
            if len(self._events) > _MAX_EVENTS:
                self._events = self._events[-_MAX_EVENTS:]
            self._save_queue()

        _ICONS = {
            "motion": "[MOT]", "stranger": "[STR]", "cry": "[CRY]",
            "known_face": "[FAC]", "chat": "[CHT]", "system": "[SYS]",
        }
        icon = _ICONS.get(event_type, "[EVT]")
        print(f"[Notifier] {icon} {event_type.upper()}: {message}")

        # Gửi WebSocket nếu broadcaster đã được đăng ký (Sprint 5)
        self._send_ws(event)

        return True

    def push_chat_log(self, user_text: str, bi_response: str) -> bool:
        """
        Lưu lịch sử hội thoại cho Parent App xem (SRS 4.2 — Nhật ký chat).
        """
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
        """Trả về các events chưa đọc, có thể filter theo type."""
        with self._lock:
            events = [e for e in self._events if not e["read"]]
            if event_type:
                events = [e for e in events if e["type"] == event_type]
            return events

    def mark_all_read(self) -> None:
        """Đánh dấu tất cả events đã đọc."""
        with self._lock:
            for e in self._events:
                e["read"] = True
            self._save_queue()

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "total_events": len(self._events),
                "unread": sum(1 for e in self._events if not e["read"]),
                "ws_enabled": _WS_ENABLED,
                "queue_file": str(self._queue_file),
            }

    # ── Private ───────────────────────────────────────────────────────────────

    def _load_queue(self) -> list[dict]:
        try:
            if self._queue_file.exists():
                with open(self._queue_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def _save_queue(self) -> None:
        try:
            with open(self._queue_file, 'w', encoding='utf-8') as f:
                json.dump(self._events, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("[Notifier] Khong luu duoc queue: %s", e)

    def set_ws_broadcaster(self, broadcaster_fn) -> None:
        """
        Đăng ký function broadcast WebSocket (gọi từ api_server.init_server()).
        Sau khi đăng ký, mọi push_event() sẽ tự broadcast đến app phụ huynh.
        """
        self._ws_broadcaster = broadcaster_fn
        logger.info("[Notifier] WS broadcaster đã đăng ký.")

    def _send_ws(self, event: dict) -> None:
        """Gửi event tới tất cả WebSocket clients qua broadcaster đã đăng ký."""
        if self._ws_broadcaster:
            try:
                self._ws_broadcaster(event)
            except Exception as e:
                logger.debug("[Notifier] _send_ws lỗi: %s", e)


# ── Singleton ─────────────────────────────────────────────────────────────────
_notifier_instance: EventNotifier | None = None


def get_notifier() -> EventNotifier:
    """Trả về singleton EventNotifier instance."""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = EventNotifier()
    return _notifier_instance


# ── Test độc lập ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=== EventNotifier standalone test ===")

    notifier = get_notifier()
    notifier.push_event("motion", "Test motion event", clip_path="/tmp/test.mp4")
    notifier.push_event("stranger", "Phat hien nguoi la")
    notifier.push_chat_log("ten toi la An", "Bi nho roi, ban ten An!")
    stats = notifier.get_stats()
    print(f"Stats: {stats}")
    unread = notifier.get_unread_events()
    print(f"Unread events: {len(unread)}")
    print("Test PASS")
