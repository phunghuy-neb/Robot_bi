"""Learning progress tracker for education sessions."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from src.infrastructure.database.db import get_db_connection

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Ghi nhan va tong hop tien do hoc tap theo family."""

    def __init__(self):
        """Khoi tao tracker va schema phu."""
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Tao bang education_sessions neu chua ton tai."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS education_sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        family_id TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        correct INTEGER NOT NULL,
                        incorrect INTEGER NOT NULL,
                        duration_sec INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_education_sessions_family_time
                    ON education_sessions (family_id, created_at)
                    """
                )
                conn.commit()
        except Exception:
            logger.exception("[ProgressTracker] Khong the tao schema")

    def record_session(self, family_id, subject, correct, incorrect, duration_sec):
        """Ghi nhan mot phien hoc."""
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO education_sessions
                        (family_id, subject, correct, incorrect, duration_sec, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(family_id),
                        str(subject),
                        max(0, int(correct)),
                        max(0, int(incorrect)),
                        max(0, int(duration_sec)),
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    ),
                )
                conn.commit()
            return True
        except Exception:
            logger.exception("[ProgressTracker] record_session failed")
            return False

    def get_subject_progress(self, family_id, subject) -> dict:
        """Tong hop tien do theo mon hoc."""
        try:
            with get_db_connection() as conn:
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS sessions,
                           COALESCE(SUM(correct), 0) AS correct,
                           COALESCE(SUM(incorrect), 0) AS incorrect,
                           COALESCE(SUM(duration_sec), 0) AS duration_sec
                    FROM education_sessions
                    WHERE family_id = ? AND subject = ?
                    """,
                    (str(family_id), str(subject)),
                ).fetchone()
            correct = int(row["correct"] or 0)
            incorrect = int(row["incorrect"] or 0)
            total = correct + incorrect
            return {
                "family_id": str(family_id),
                "subject": str(subject),
                "sessions": int(row["sessions"] or 0),
                "correct": correct,
                "incorrect": incorrect,
                "accuracy": round(correct / total, 3) if total else 0.0,
                "duration_sec": int(row["duration_sec"] or 0),
            }
        except Exception:
            logger.exception("[ProgressTracker] get_subject_progress failed")
            return {"family_id": str(family_id), "subject": str(subject), "sessions": 0, "correct": 0, "incorrect": 0, "accuracy": 0.0, "duration_sec": 0}

    def get_overall_progress(self, family_id) -> dict:
        """Tong hop tien do tat ca mon."""
        try:
            with get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT subject,
                           COUNT(*) AS sessions,
                           COALESCE(SUM(correct), 0) AS correct,
                           COALESCE(SUM(incorrect), 0) AS incorrect,
                           COALESCE(SUM(duration_sec), 0) AS duration_sec
                    FROM education_sessions
                    WHERE family_id = ?
                    GROUP BY subject
                    """,
                    (str(family_id),),
                ).fetchall()
            subjects = {}
            total_correct = total_incorrect = total_duration = total_sessions = 0
            for row in rows:
                correct = int(row["correct"] or 0)
                incorrect = int(row["incorrect"] or 0)
                total = correct + incorrect
                subjects[row["subject"]] = {
                    "sessions": int(row["sessions"] or 0),
                    "correct": correct,
                    "incorrect": incorrect,
                    "accuracy": round(correct / total, 3) if total else 0.0,
                    "duration_sec": int(row["duration_sec"] or 0),
                }
                total_correct += correct
                total_incorrect += incorrect
                total_duration += int(row["duration_sec"] or 0)
                total_sessions += int(row["sessions"] or 0)
            total_answers = total_correct + total_incorrect
            return {
                "family_id": str(family_id),
                "sessions": total_sessions,
                "correct": total_correct,
                "incorrect": total_incorrect,
                "accuracy": round(total_correct / total_answers, 3) if total_answers else 0.0,
                "duration_sec": total_duration,
                "subjects": subjects,
            }
        except Exception:
            logger.exception("[ProgressTracker] get_overall_progress failed")
            return {"family_id": str(family_id), "sessions": 0, "correct": 0, "incorrect": 0, "accuracy": 0.0, "duration_sec": 0, "subjects": {}}

    def get_weak_topics(self, family_id) -> list:
        """Tra ve cac mon co accuracy duoi 70%."""
        try:
            overall = self.get_overall_progress(family_id)
            weak = []
            for subject, data in overall.get("subjects", {}).items():
                if data.get("sessions", 0) > 0 and data.get("accuracy", 0.0) < 0.7:
                    weak.append({"subject": subject, "accuracy": data["accuracy"]})
            return weak
        except Exception:
            logger.exception("[ProgressTracker] get_weak_topics failed")
            return []

    def get_streak(self, family_id) -> int:
        """Tinh so ngay hoc lien tiep tu hom nay tro ve truoc."""
        try:
            today = datetime.now(timezone.utc).date()
            streak = 0
            with get_db_connection() as conn:
                for offset in range(0, 365):
                    day = (today - timedelta(days=offset)).isoformat()
                    row = conn.execute(
                        """
                        SELECT 1 FROM education_sessions
                        WHERE family_id = ? AND date(created_at) = ?
                        LIMIT 1
                        """,
                        (str(family_id), day),
                    ).fetchone()
                    if not row:
                        break
                    streak += 1
            return streak
        except Exception:
            logger.exception("[ProgressTracker] get_streak failed")
            return 0

    def generate_weekly_report(self, family_id) -> dict:
        """Tao report hoc tap 7 ngay gan nhat."""
        try:
            since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
            by_subject = defaultdict(lambda: {"sessions": 0, "correct": 0, "incorrect": 0, "duration_sec": 0})
            with get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT subject, correct, incorrect, duration_sec
                    FROM education_sessions
                    WHERE family_id = ? AND created_at >= ?
                    """,
                    (str(family_id), since),
                ).fetchall()
            for row in rows:
                item = by_subject[row["subject"]]
                item["sessions"] += 1
                item["correct"] += int(row["correct"])
                item["incorrect"] += int(row["incorrect"])
                item["duration_sec"] += int(row["duration_sec"])
            return {
                "family_id": str(family_id),
                "days": 7,
                "subjects": dict(by_subject),
                "streak": self.get_streak(family_id),
                "weak_topics": self.get_weak_topics(family_id),
            }
        except Exception:
            logger.exception("[ProgressTracker] generate_weekly_report failed")
            return {"family_id": str(family_id), "days": 7, "subjects": {}, "streak": 0, "weak_topics": []}
