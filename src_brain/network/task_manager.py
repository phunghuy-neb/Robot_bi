"""
task_manager.py — Quản lý nhiệm vụ hằng ngày và sao thưởng (SRS 4.4)
=====================================================================
Phụ huynh tạo nhiệm vụ qua Parent App, robot nhắc bé qua loa đúng giờ,
bé hoàn thành được cộng sao.

Class: TaskManager
  add_task(name, remind_time) → dict
  complete_task(task_id) → bool
  reset_daily()
  get_all() → list
  delete_task(task_id) → bool
  get_total_stars() → int
  stop()
"""

import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

TASKS_FILE = Path(__file__).parent / "tasks.json"


class TaskManager:
    def __init__(self, tts_callback=None):
        """
        tts_callback: callable(text) — gọi để Bi phát âm nhắc nhở.
        Nếu None, vẫn hoạt động — chỉ không phát TTS.
        """
        self.tts_callback = tts_callback
        self._tasks: list = self._load()
        self._lock = threading.Lock()
        # Daemon thread kiểm tra giờ nhắc mỗi 30 giây
        self._running = True
        threading.Thread(target=self._reminder_loop, daemon=True,
                         name="task-reminder").start()

    def _load(self) -> list:
        try:
            if TASKS_FILE.exists():
                return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save(self):
        TASKS_FILE.write_text(
            json.dumps(self._tasks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_task(self, name: str, remind_time: str) -> dict:
        """
        Thêm nhiệm vụ mới.
        name:        tên nhiệm vụ, ví dụ "Đánh răng"
        remind_time: "HH:MM", ví dụ "07:30"
        Returns: task dict mới tạo
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
            self._tasks.append(task)
            self._save()
        return task

    def complete_task(self, task_id: str) -> bool:
        """
        Đánh dấu nhiệm vụ hoàn thành, cộng 1 sao.
        Returns True nếu thành công, False nếu không tìm thấy / đã hoàn thành.
        """
        with self._lock:
            for t in self._tasks:
                if t["id"] == task_id and not t["completed_today"]:
                    t["completed_today"] = True
                    t["stars"] = t.get("stars", 0) + 1
                    self._save()
                    return True
        return False

    def reset_daily(self):
        """Gọi mỗi đầu ngày để reset completed_today. (Dùng cron ngoài nếu cần.)"""
        with self._lock:
            for t in self._tasks:
                t["completed_today"] = False
            self._save()

    def get_all(self) -> list:
        """Trả về danh sách tất cả nhiệm vụ (bản copy)."""
        with self._lock:
            return list(self._tasks)

    def delete_task(self, task_id: str) -> bool:
        """Xóa nhiệm vụ theo ID. Returns True nếu thành công."""
        with self._lock:
            before = len(self._tasks)
            self._tasks = [t for t in self._tasks if t["id"] != task_id]
            if len(self._tasks) < before:
                self._save()
                return True
        return False

    def get_total_stars(self) -> int:
        """Tổng số sao tích lũy từ tất cả nhiệm vụ."""
        with self._lock:
            return sum(t.get("stars", 0) for t in self._tasks)

    def _reminder_loop(self):
        """Daemon thread: kiểm tra giờ nhắc mỗi 30 giây, phát TTS nếu đến giờ."""
        while self._running:
            now = datetime.now().strftime("%H:%M")
            with self._lock:
                for t in self._tasks:
                    if (
                        t["remind_time"] == now
                        and not t["completed_today"]
                        and t.get("last_reminded") != now
                    ):
                        t["last_reminded"] = now
                        self._save()
                        if self.tts_callback:
                            msg = f"Bi nhắc bạn: {t['name']} nhé! Bạn đã làm chưa?"
                            threading.Thread(
                                target=self.tts_callback,
                                args=(msg,),
                                daemon=True,
                            ).start()
            time.sleep(30)

    def stop(self):
        """Dừng reminder loop."""
        self._running = False


# ── Standalone test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    tm = TaskManager()
    t = tm.add_task("Đánh răng", "07:30")
    assert t["name"] == "Đánh răng", "add_task fail"
    ok = tm.complete_task(t["id"])
    assert ok is True, "complete_task fail"
    assert tm.get_total_stars() == 1, "stars fail"
    tm.delete_task(t["id"])
    assert len(tm.get_all()) == 0, "delete fail"
    print("TASK MANAGER TEST PASSED")
