"""
task_manager.py - Quan ly nhiem vu hang ngay va sao thuong (SRS 4.4)
=====================================================================
Phu huynh tao nhiem vu qua Parent App, robot nhac be qua loa dung gio,
be hoan thanh duoc cong sao.

Class: TaskManager
  add_task(name, remind_time) -> dict
  complete_task(task_id) -> bool
  get_all() -> list
  delete_task(task_id) -> bool
  get_total_stars() -> int
  stop()
"""

import threading
import time
import uuid
from datetime import datetime

from src.infrastructure.database.db import _normalize_family_id, ensure_family_exists, get_db_connection


class TaskManager:
    def __init__(self, tts_callback=None, family_id: str | None = None):
        """
        tts_callback: callable(text) - goi de Bi phat am nhac nho.
        Neu None, van hoat dong - chi khong phat TTS.
        """
        self.tts_callback = tts_callback
        self.family_id = ensure_family_exists(_normalize_family_id(family_id))
        self._tasks: list = self._load(self.family_id)
        self._lock = threading.Lock()
        self._running = True
        threading.Thread(
            target=self._reminder_loop,
            daemon=True,
            name="task-reminder",
        ).start()

    @staticmethod
    def _row_to_task(row) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        completed_date = row["completed_date"]
        return {
            "id": row["task_id"],
            "family_id": row["family_id"],
            "name": row["name"],
            "remind_time": row["remind_time"],
            "completed_today": completed_date == today,
            "completed_date": completed_date,
            "stars": int(row["stars"]),
            "created_at": row["created_at"],
            "last_reminded": row["last_reminded"],
            "last_reminded_date": row["last_reminded_date"],
        }

    def _load(self, family_id: str | None = None) -> list:
        family_id = ensure_family_exists(_normalize_family_id(family_id or self.family_id))
        with get_db_connection() as conn:
            today = datetime.now().strftime("%Y-%m-%d")
            conn.execute(
                """
                UPDATE tasks
                SET completed_date = '2000-01-01'
                WHERE family_id = ?
                  AND completed_today = 1
                  AND (completed_date IS NULL OR completed_date = '')
                """,
                (family_id,),
            )
            conn.execute(
                """
                UPDATE tasks
                SET completed_today = 0
                WHERE family_id = ?
                  AND completed_today = 1
                  AND COALESCE(completed_date, '') != ?
                """,
                (family_id, today),
            )
            conn.commit()
            rows = conn.execute(
                """
                SELECT family_id, task_id, name, remind_time, completed_today,
                       completed_date, stars, created_at, last_reminded,
                       last_reminded_date
                FROM tasks
                WHERE family_id = ?
                ORDER BY db_id ASC
                """,
                (family_id,),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def _refresh_tasks(self, family_id: str | None = None) -> list:
        family_id = _normalize_family_id(family_id or self.family_id)
        tasks = self._load(family_id)
        if family_id == self.family_id:
            self._tasks = tasks
        return tasks

    def add_task(self, name: str, remind_time: str, family_id: str | None = None) -> dict:
        """
        Them nhiem vu moi.
        name: ten nhiem vu, vi du "Danh rang"
        remind_time: "HH:MM", vi du "07:30"
        Returns: task dict moi tao
        """
        family_id = ensure_family_exists(_normalize_family_id(family_id or self.family_id))
        task = {
            "id": str(uuid.uuid4()),
            "family_id": family_id,
            "name": name,
            "remind_time": remind_time,
            "completed_today": False,
            "completed_date": None,
            "stars": 0,
            "created_at": datetime.now().isoformat(),
            "last_reminded": None,
            "last_reminded_date": None,
        }
        with self._lock:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO tasks (
                        family_id, task_id, name, remind_time, completed_today,
                        completed_date, stars, created_at, last_reminded,
                        last_reminded_date, import_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task["family_id"],
                        task["id"],
                        task["name"],
                        task["remind_time"],
                        0,
                        task["completed_date"],
                        task["stars"],
                        task["created_at"],
                        task["last_reminded"],
                        task["last_reminded_date"],
                        task["id"],
                    ),
                )
                conn.commit()
            self._refresh_tasks(family_id)
        return task

    def complete_task(self, task_id: str, family_id: str | None = None) -> bool:
        """
        Danh dau nhiem vu hoan thanh, cong 1 sao.
        Returns True neu thanh cong, False neu khong tim thay / da hoan thanh.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE tasks
                    SET completed_today = 1,
                        completed_date = ?,
                        stars = COALESCE(stars, 0) + 1
                    WHERE task_id = ?
                      AND family_id = ?
                      AND COALESCE(completed_date, '') != ?
                    """,
                    (today, task_id, family_id, today),
                )
                conn.commit()
            if cursor.rowcount > 0:
                self._refresh_tasks(family_id)
                return True
        return False

    def get_all(self, family_id: str | None = None) -> list:
        """Tra ve danh sach tat ca nhiem vu (ban copy)."""
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            tasks = self._refresh_tasks(family_id)
            return list(tasks)

    def _save(self) -> None:
        """Persist in-memory task edits used by tests and migrations."""
        with self._lock:
            with get_db_connection() as conn:
                for task in self._tasks:
                    conn.execute(
                        """
                        UPDATE tasks
                        SET completed_today = ?,
                            completed_date = ?,
                            last_reminded = ?,
                            last_reminded_date = ?
                        WHERE task_id = ?
                          AND family_id = ?
                        """,
                        (
                            1 if task.get("completed_today") else 0,
                            task.get("completed_date"),
                            task.get("last_reminded"),
                            task.get("last_reminded_date"),
                            task["id"],
                            task.get("family_id") or self.family_id,
                        ),
                    )
                conn.commit()

    def delete_task(self, task_id: str, family_id: str | None = None) -> bool:
        """Xoa nhiem vu theo ID. Returns True neu thanh cong."""
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM tasks WHERE task_id = ? AND family_id = ?",
                    (task_id, family_id),
                )
                conn.commit()
            if cursor.rowcount > 0:
                self._refresh_tasks(family_id)
                return True
        return False

    def get_total_stars(self, family_id: str | None = None) -> int:
        """Tong so sao tich luy tu tat ca nhiem vu."""
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT COALESCE(SUM(stars), 0) AS total_stars FROM tasks WHERE family_id = ?",
                    (family_id,),
                ).fetchone()
            return int(row["total_stars"]) if row else 0

    def _mark_reminded(self, task_id: str, family_id: str | None = None) -> bool:
        """Mark a task as reminded at the current date and minute."""
        now_dt = datetime.now()
        today = now_dt.strftime("%Y-%m-%d")
        reminded_at = now_dt.strftime("%Y-%m-%d %H:%M")
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE tasks
                    SET last_reminded = ?,
                        last_reminded_date = ?
                    WHERE task_id = ?
                      AND family_id = ?
                    """,
                    (reminded_at, today, task_id, family_id),
                )
                conn.commit()
            if cursor.rowcount > 0:
                self._refresh_tasks(family_id)
                return True
        return False

    def _reminder_loop(self):
        """Daemon thread: kiem tra gio nhac moi 30 giay, phat TTS neu den gio."""
        while self._running:
            now_dt = datetime.now()
            today = now_dt.strftime("%Y-%m-%d")
            now = now_dt.strftime("%H:%M")
            messages_to_speak = []
            with self._lock:
                self._refresh_tasks(self.family_id)
                for task in self._tasks:
                    last_reminded = task.get("last_reminded") or ""
                    reminded_date = last_reminded[:10] if len(last_reminded) >= 10 else ""
                    reminded_time = last_reminded[11:] if len(last_reminded) >= 16 else last_reminded
                    already_reminded = reminded_date == today and reminded_time == now
                    already_done_today = task.get("completed_date") == today
                    if (
                        task["remind_time"] == now
                        and not already_done_today
                        and not already_reminded
                    ):
                        reminded_at = now_dt.strftime("%Y-%m-%d %H:%M")
                        with get_db_connection() as conn:
                            conn.execute(
                                """
                                UPDATE tasks
                                SET last_reminded = ?,
                                    last_reminded_date = ?
                                WHERE task_id = ?
                                  AND family_id = ?
                                """,
                                (reminded_at, today, task["id"], self.family_id),
                            )
                            conn.commit()
                        task["last_reminded"] = reminded_at
                        task["last_reminded_date"] = today
                        if self.tts_callback:
                            messages_to_speak.append(
                                f"Bi nhac ban: {task['name']} nhe! Ban da lam chua?"
                            )
            for message in messages_to_speak:
                threading.Thread(
                    target=self.tts_callback,
                    args=(message,),
                    daemon=True,
                ).start()
            time.sleep(30)

    def stop(self):
        """Dung reminder loop."""
        self._running = False


if __name__ == "__main__":
    from src.infrastructure.database.db import init_db

    init_db()
    tm = TaskManager()
    task = tm.add_task("Danh rang", "07:30")
    assert task["name"] == "Danh rang", "add_task fail"
    ok = tm.complete_task(task["id"])
    assert ok is True, "complete_task fail"
    assert tm.get_total_stars() >= 1, "stars fail"
    tm.delete_task(task["id"])
    print("TASK MANAGER TEST PASSED")
