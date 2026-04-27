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

from src_brain.network.db import get_db_connection


class TaskManager:
    def __init__(self, tts_callback=None):
        """
        tts_callback: callable(text) - goi de Bi phat am nhac nho.
        Neu None, van hoat dong - chi khong phat TTS.
        """
        self.tts_callback = tts_callback
        self._tasks: list = self._load()
        self._lock = threading.Lock()
        self._running = True
        threading.Thread(
            target=self._reminder_loop,
            daemon=True,
            name="task-reminder",
        ).start()

    @staticmethod
    def _row_to_task(row) -> dict:
        return {
            "id": row["task_id"],
            "name": row["name"],
            "remind_time": row["remind_time"],
            "completed_today": bool(row["completed_today"]),
            "stars": int(row["stars"]),
            "created_at": row["created_at"],
            "last_reminded": row["last_reminded"],
        }

    def _load(self) -> list:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT task_id, name, remind_time, completed_today,
                       stars, created_at, last_reminded
                FROM tasks
                ORDER BY db_id ASC
                """
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def _refresh_tasks(self) -> None:
        self._tasks = self._load()

    def add_task(self, name: str, remind_time: str) -> dict:
        """
        Them nhiem vu moi.
        name: ten nhiem vu, vi du "Danh rang"
        remind_time: "HH:MM", vi du "07:30"
        Returns: task dict moi tao
        """
        task = {
            "id": str(uuid.uuid4()),
            "name": name,
            "remind_time": remind_time,
            "completed_today": False,
            "stars": 0,
            "created_at": datetime.now().isoformat(),
            "last_reminded": None,
        }
        with self._lock:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO tasks (
                        task_id, name, remind_time, completed_today,
                        stars, created_at, last_reminded, import_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task["id"],
                        task["name"],
                        task["remind_time"],
                        0,
                        task["stars"],
                        task["created_at"],
                        task["last_reminded"],
                        task["id"],
                    ),
                )
                conn.commit()
            self._refresh_tasks()
        return task

    def complete_task(self, task_id: str) -> bool:
        """
        Danh dau nhiem vu hoan thanh, cong 1 sao.
        Returns True neu thanh cong, False neu khong tim thay / da hoan thanh.
        """
        with self._lock:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE tasks
                    SET completed_today = 1,
                        stars = COALESCE(stars, 0) + 1
                    WHERE task_id = ? AND completed_today = 0
                    """,
                    (task_id,),
                )
                conn.commit()
            if cursor.rowcount > 0:
                self._refresh_tasks()
                return True
        return False

    def get_all(self) -> list:
        """Tra ve danh sach tat ca nhiem vu (ban copy)."""
        with self._lock:
            self._refresh_tasks()
            return list(self._tasks)

    def delete_task(self, task_id: str) -> bool:
        """Xoa nhiem vu theo ID. Returns True neu thanh cong."""
        with self._lock:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM tasks WHERE task_id = ?",
                    (task_id,),
                )
                conn.commit()
            if cursor.rowcount > 0:
                self._refresh_tasks()
                return True
        return False

    def get_total_stars(self) -> int:
        """Tong so sao tich luy tu tat ca nhiem vu."""
        with self._lock:
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT COALESCE(SUM(stars), 0) AS total_stars FROM tasks"
                ).fetchone()
            return int(row["total_stars"]) if row else 0

    def _reminder_loop(self):
        """Daemon thread: kiem tra gio nhac moi 30 giay, phat TTS neu den gio."""
        while self._running:
            now = datetime.now().strftime("%H:%M")
            messages_to_speak = []
            with self._lock:
                self._refresh_tasks()
                for task in self._tasks:
                    if (
                        task["remind_time"] == now
                        and not task["completed_today"]
                        and task.get("last_reminded") != now
                    ):
                        with get_db_connection() as conn:
                            conn.execute(
                                """
                                UPDATE tasks
                                SET last_reminded = ?
                                WHERE task_id = ?
                                """,
                                (now, task["id"]),
                            )
                            conn.commit()
                        task["last_reminded"] = now
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
    from src_brain.network.db import init_db

    init_db()
    tm = TaskManager()
    task = tm.add_task("Danh rang", "07:30")
    assert task["name"] == "Danh rang", "add_task fail"
    ok = tm.complete_task(task["id"])
    assert ok is True, "complete_task fail"
    assert tm.get_total_stars() >= 1, "stars fail"
    tm.delete_task(task["id"])
    print("TASK MANAGER TEST PASSED")
