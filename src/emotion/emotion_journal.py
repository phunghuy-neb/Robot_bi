"""Emotion journal storage and weekly reports."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from src.infrastructure.database.db import get_db_connection

logger = logging.getLogger(__name__)


class EmotionJournal:
    """Luu nhat ky cam xuc va tao bao cao don gian cho phu huynh."""

    def __init__(self):
        """Khoi tao journal va tao schema phu neu can."""
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Tao bang emotion_journal neu chua ton tai."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS emotion_journal (
                        entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        family_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        emotion TEXT NOT NULL,
                        note TEXT DEFAULT ''
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_emotion_journal_family_time
                    ON emotion_journal (family_id, timestamp)
                    """
                )
                conn.commit()
        except Exception:
            logger.exception("[EmotionJournal] Khong the tao schema")

    def add_entry(self, family_id, emotion, note="") -> bool:
        """Them mot entry cam xuc cho family."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO emotion_journal (family_id, timestamp, emotion, note)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        str(family_id),
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        str(emotion),
                        str(note or "")[:500],
                    ),
                )
                conn.commit()
            return True
        except Exception:
            logger.exception("[EmotionJournal] add_entry failed")
            return False

    def get_entries(self, family_id, days=7) -> list[dict]:
        """Lay entries trong so ngay gan nhat."""
        try:
            days = max(1, min(365, int(days)))
            since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
            with get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT entry_id, family_id, timestamp, emotion, note
                    FROM emotion_journal
                    WHERE family_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    """,
                    (str(family_id), since),
                ).fetchall()
            return [dict(row) for row in rows]
        except Exception:
            logger.exception("[EmotionJournal] get_entries failed")
            return []

    def get_streak(self, family_id, emotion) -> int:
        """Tra ve so ngay lien tiep co emotion tu hom nay tro ve truoc."""
        try:
            target = str(emotion)
            today = datetime.now(timezone.utc).date()
            streak = 0
            with get_db_connection() as conn:
                for offset in range(0, 365):
                    day = (today - timedelta(days=offset)).isoformat()
                    row = conn.execute(
                        """
                        SELECT 1
                        FROM emotion_journal
                        WHERE family_id = ? AND emotion = ? AND date(timestamp) = ?
                        LIMIT 1
                        """,
                        (str(family_id), target, day),
                    ).fetchone()
                    if not row:
                        break
                    streak += 1
            return streak
        except Exception:
            logger.exception("[EmotionJournal] get_streak failed")
            return 0

    def export_report(self, family_id, week_offset=0) -> dict:
        """Bao cao tuan gom emotion counts, dominant va streak."""
        try:
            week_offset = max(0, int(week_offset))
            end_day = datetime.now(timezone.utc).date() - timedelta(days=week_offset * 7)
            start_day = end_day - timedelta(days=6)
            with get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT emotion
                    FROM emotion_journal
                    WHERE family_id = ?
                      AND date(timestamp) BETWEEN ? AND ?
                    """,
                    (str(family_id), start_day.isoformat(), end_day.isoformat()),
                ).fetchall()
            counts = Counter(row["emotion"] for row in rows)
            dominant = counts.most_common(1)[0][0] if counts else "neutral"
            return {
                "family_id": str(family_id),
                "week_start": start_day.isoformat(),
                "week_end": end_day.isoformat(),
                "emotion_counts": dict(counts),
                "dominant": dominant,
                "sad_streak": self.get_streak(family_id, "sad"),
                "stressed_streak": self.get_streak(family_id, "stressed"),
            }
        except Exception:
            logger.exception("[EmotionJournal] export_report failed")
            return {
                "family_id": str(family_id),
                "emotion_counts": {},
                "dominant": "neutral",
                "sad_streak": 0,
                "stressed_streak": 0,
            }
