"""Emotion alert checks for repeated sad or stressed days."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.infrastructure.database.db import get_db_connection

logger = logging.getLogger(__name__)


class EmotionAlert:
    """Kiem tra va ghi nhan canh bao cam xuc."""

    ALERT_THRESHOLD = 3

    def __init__(self):
        """Khoi tao alert helper va tao schema phu neu can."""
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Tao bang emotion_alerts neu chua ton tai."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS emotion_alerts (
                        family_id TEXT PRIMARY KEY,
                        last_alert_at TEXT,
                        status TEXT NOT NULL,
                        message TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
        except Exception:
            logger.exception("[EmotionAlert] Khong the tao schema")

    def check_and_alert(self, family_id, journal, notifier) -> bool:
        """
        Kiem tra neu be buon/stress qua nguong va push event canh bao.

        Returns True neu da gui alert.
        """
        try:
            sad_streak = journal.get_streak(family_id, "sad")
            stressed_streak = journal.get_streak(family_id, "stressed")
            if sad_streak < self.ALERT_THRESHOLD and stressed_streak < self.ALERT_THRESHOLD:
                return False

            emotion = "sad" if sad_streak >= stressed_streak else "stressed"
            streak = max(sad_streak, stressed_streak)
            message = f"Be co dau hieu {emotion} {streak} ngay lien tiep. Phu huynh nen quan sat them."
            if notifier is not None and hasattr(notifier, "push_event"):
                notifier.push_event("emotion_alert", message, family_id=str(family_id))
            self._save_status(family_id, "active", message)
            return True
        except Exception:
            logger.exception("[EmotionAlert] check_and_alert failed")
            return False

    def _save_status(self, family_id, status: str, message: str) -> None:
        """Luu trang thai alert moi nhat."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO emotion_alerts
                        (family_id, last_alert_at, status, message)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(family_id) DO UPDATE SET
                        last_alert_at = excluded.last_alert_at,
                        status = excluded.status,
                        message = excluded.message
                    """,
                    (str(family_id), datetime.now(timezone.utc).isoformat(timespec="seconds"), status, message),
                )
                conn.commit()
        except Exception:
            logger.exception("[EmotionAlert] save status failed")

    def get_alert_status(self, family_id) -> dict:
        """Tra ve trang thai canh bao hien tai."""
        try:
            with get_db_connection() as conn:
                row = conn.execute(
                    """
                    SELECT family_id, last_alert_at, status, message
                    FROM emotion_alerts
                    WHERE family_id = ?
                    """,
                    (str(family_id),),
                ).fetchone()
            if not row:
                return {
                    "family_id": str(family_id),
                    "active": False,
                    "status": "ok",
                    "message": "",
                    "last_alert_at": None,
                }
            return {
                "family_id": row["family_id"],
                "active": row["status"] == "active",
                "status": row["status"],
                "message": row["message"],
                "last_alert_at": row["last_alert_at"],
            }
        except Exception:
            logger.exception("[EmotionAlert] get_alert_status failed")
            return {
                "family_id": str(family_id),
                "active": False,
                "status": "error",
                "message": "",
                "last_alert_at": None,
            }
