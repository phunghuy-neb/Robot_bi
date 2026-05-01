"""Curriculum schedule persistence for Robot Bi education features."""

from __future__ import annotations

import copy
import logging
import threading
import time
from datetime import datetime, timezone

from src.infrastructure.database.db import (
    get_db_connection,
    get_learning_schedule,
    save_learning_schedule,
)

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
        """Lay lich hoc cua family tu learning_schedules, fallback default."""
        try:
            merged = copy.deepcopy(self.DEFAULT_SCHEDULE)
            saved = get_learning_schedule(str(family_id))
            if saved:
                merged.update(saved)
            return merged
        except Exception:
            logger.exception("[Curriculum] get_schedule failed")
            return copy.deepcopy(self.DEFAULT_SCHEDULE)

    def update_schedule(self, family_id, schedule) -> bool:
        """Luu lich hoc moi vao learning_schedules."""
        try:
            if not isinstance(schedule, dict):
                return False
            for value in schedule.values():
                if value is not None and not isinstance(value, dict):
                    return False
            return save_learning_schedule(str(family_id), schedule)
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

    def start_scheduler(self, notifier=None, tts_callback=None) -> None:
        """Bat dau background thread kiem tra lich hoc moi phut."""
        self.notifier = notifier
        self.tts_callback = tts_callback
        self._running = True
        self._reminded = {}
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="curriculum-scheduler"
        )
        self._scheduler_thread.start()

    def stop_scheduler(self) -> None:
        """Dung scheduler loop."""
        self._running = False

    def _scheduler_loop(self) -> None:
        """Kiem tra gio hoc moi 30 giay."""
        while getattr(self, '_running', False):
            try:
                # Use local time for reminders
                from datetime import datetime as dt_local
                now_local = dt_local.now()
                today_str = now_local.strftime("%Y-%m-%d")
                now_time = now_local.strftime("%H:%M")
                
                families = [{"family_id": "default"}]
                try:
                    with get_db_connection() as conn:
                        rows = conn.execute("SELECT family_id FROM families").fetchall()
                        if rows:
                            families = [{"family_id": str(r["family_id"])} for r in rows]
                except Exception:
                    pass

                for f in families:
                    family_id = f["family_id"]
                    schedule = self.get_schedule(family_id)
                    day_name = now_local.strftime("%A").lower()
                    lesson = schedule.get(day_name)
                    
                    if lesson and isinstance(lesson, dict):
                        lesson_time = str(lesson.get("time", "19:00"))
                        subject = str(lesson.get("subject", "english"))
                        
                        remind_key = f"{family_id}_{today_str}_{lesson_time}"
                        
                        if now_time == lesson_time and not self._reminded.get(remind_key):
                            self._reminded[remind_key] = True
                            
                            subject_vn = {
                                "english": "Tiếng Anh", 
                                "math": "Toán", 
                                "science": "Khoa học", 
                                "history": "Lịch sử"
                            }.get(subject, subject)
                            
                            message = f"Bây giờ là giờ học {subject_vn} rồi nhé! Hôm nay mình học về con vật nào?"
                            
                            if hasattr(self, 'tts_callback') and self.tts_callback:
                                threading.Thread(
                                    target=self.tts_callback,
                                    args=(message,),
                                    daemon=True
                                ).start()
                                
                            if hasattr(self, 'notifier') and self.notifier:
                                self.notifier.push_event(
                                    "education", 
                                    message=f"Đã đến giờ học môn {subject_vn}",
                                    family_id=family_id
                                )
                                
            except Exception as e:
                logger.error("[Curriculum] Lỗi scheduler: %s", e)
                
            time.sleep(30)
