"""Curriculum schedule persistence for Robot Bi education features."""

from __future__ import annotations

import copy
import json
import logging
from datetime import datetime, timezone

from src.infrastructure.database.db import get_db_connection

logger = logging.getLogger(__name__)


class Curriculum:
    """Quan ly lich hoc mac dinh va lich hoc tuy bien theo family."""

    DEFAULT_SCHEDULE = {
        "monday": {"subject": "english", "time": "19:00"},
        "tuesday": {"subject": "math", "time": "19:00"},
        "wednesday": {"subject": "science", "time": "19:00"},
        "thursday": {"subject": "english", "time": "19:00"},
        "friday": {"subject": "history", "time": "19:00"},
        "saturday": {"subject": "english", "time": "09:00"},
        "sunday": None,
    }

    def __init__(self):
        """Khoi tao curriculum va schema phu."""
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Tao bang curriculum_schedules neu chua ton tai."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS curriculum_schedules (
                        family_id TEXT PRIMARY KEY,
                        data TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
        except Exception:
            logger.exception("[Curriculum] Khong the tao schema")

    def get_schedule(self, family_id) -> dict:
        """Lay lich hoc cua family, fallback default 7 ngay."""
        try:
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT data FROM curriculum_schedules WHERE family_id = ?",
                    (str(family_id),),
                ).fetchone()
            if not row:
                return copy.deepcopy(self.DEFAULT_SCHEDULE)
            data = json.loads(row["data"])
            if not isinstance(data, dict):
                return copy.deepcopy(self.DEFAULT_SCHEDULE)
            merged = copy.deepcopy(self.DEFAULT_SCHEDULE)
            merged.update(data)
            return merged
        except Exception:
            logger.exception("[Curriculum] get_schedule failed")
            return copy.deepcopy(self.DEFAULT_SCHEDULE)

    def update_schedule(self, family_id, schedule) -> bool:
        """Luu lich hoc moi cho family."""
        try:
            if not isinstance(schedule, dict):
                return False
            merged = copy.deepcopy(self.DEFAULT_SCHEDULE)
            for day in merged:
                if day in schedule:
                    value = schedule[day]
                    if value is not None and not isinstance(value, dict):
                        return False
                    merged[day] = value
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO curriculum_schedules (family_id, data, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(family_id) DO UPDATE SET
                        data = excluded.data,
                        updated_at = excluded.updated_at
                    """,
                    (
                        str(family_id),
                        json.dumps(merged, ensure_ascii=False),
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    ),
                )
                conn.commit()
            return True
        except Exception:
            logger.exception("[Curriculum] update_schedule failed")
            return False

    def get_today_subject(self, family_id) -> dict:
        """Lay mon hoc hom nay theo lich."""
        try:
            day = datetime.now(timezone.utc).strftime("%A").lower()
            item = self.get_schedule(family_id).get(day)
            return {"day": day, "lesson": item, "rest_day": item is None}
        except Exception:
            logger.exception("[Curriculum] get_today_subject failed")
            return {"day": "", "lesson": None, "rest_day": True}

    def get_reminder_time(self, family_id) -> str:
        """Lay gio nhac hoc hom nay."""
        try:
            today = self.get_today_subject(family_id)
            lesson = today.get("lesson")
            if isinstance(lesson, dict):
                return str(lesson.get("time", "19:00"))
            return ""
        except Exception:
            logger.exception("[Curriculum] get_reminder_time failed")
            return ""
