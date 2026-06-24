"""
role_manager.py — Quản lý vai trò và chuyển đổi Friend ↔ Teacher cho Robot Bi.

Bốn vai trò:
  ROLE_FRIEND          — Bé nói chuyện: bạn bè (mặc định)
  ROLE_TEACHER         — Bé nói chuyện: học tập có cấu trúc
  ROLE_PARENT_CHILD    — Phụ huynh nói chuyện qua voice: ấm áp như người thân
  ROLE_PARENT_ADVISOR  — Phụ huynh web chat: phân tích chuyên sâu

Chỉ ROLE_FRIEND ↔ ROLE_TEACHER tự động chuyển theo lời bé.
Hai vai trò phụ huynh được set từ ngoài (API layer biết auth của user).
"""

import time
from dataclasses import dataclass, field
from typing import Optional

ROLE_FRIEND = "friend"
ROLE_TEACHER = "teacher"
ROLE_PARENT_CHILD = "parent_child"
ROLE_PARENT_ADVISOR = "parent_advisor"

# Sự kiện chuyển vai — trả về từ RoleManager.process_message()
TRANSITION_TO_TEACHER = "to_teacher"
TRANSITION_TO_FRIEND = "to_friend"
TRANSITION_DISTRESS = "distress"          # cảm xúc tiêu cực → friend ngay
TRANSITION_TIME_UP = "time_up"            # hết giờ → friend
TRANSITION_TASK_DONE = "task_done"        # hoàn thành task → friend
TEACHER_HOLD = "teacher_hold"             # bé đòi thoát nhưng chưa đủ 3 lần
TEACHER_HOLD_FINAL = "teacher_hold_final" # lần 2, sắp thả

# ── Keyword lists ─────────────────────────────────────────────────────────────

_TEACHER_KEYWORDS = [
    "học bài", "học toán", "học tiếng", "học văn", "học anh", "học lý",
    "học hóa", "học sinh", "học sử", "học địa", "học nhé", "học nào",
    "học đi", "làm bài", "làm toán", "bài tập", "ôn bài", "ôn tập",
    "ôn thi", "giải toán", "giải bài", "kiểm tra", "thi thử", "luyện tập",
    "luyện đọc", "luyện viết", "luyện tính", "dạy bi", "bi dạy tôi",
    "bi dạy con", "học cùng bi", "giúp con học", "giúp tôi học",
    "giúp em học", "chỉ bài", "chữa bài", "soát bài", "kiểm tra đáp án",
    "công thức", "cách làm", "bài này", "đề này",
]

_FRIEND_KEYWORDS = [
    "thôi chơi", "nghỉ thôi", "mệt rồi", "chán rồi",
    "không học nữa", "không làm nữa", "chơi thôi", "chơi đi", "chơi nào",
    "nghỉ đi", "không muốn học", "thôi nghỉ", "học sau đi",
    "stop học", "dừng lại",
]

_DISTRESS_KEYWORDS = [
    "buồn", "khóc", "tức quá", "giận", "sợ lắm", "lo lắm",
    "cô đơn", "bị bắt nạt", "bị đánh", "bị chửi", "bị la",
    "điểm kém", "thi trượt", "buồn lắm", "khóc lắm",
    "không muốn sống", "muốn chết", "ghét trường", "con sợ",
    "em sợ", "tôi sợ", "con buồn", "em buồn", "tôi buồn",
    "không ai chơi", "bị bỏ rơi", "bị trêu", "bị mắng",
]


def _normalize(text: str) -> str:
    return text.lower().strip()


def detect_teacher_trigger(text: str) -> bool:
    t = _normalize(text)
    return any(kw in t for kw in _TEACHER_KEYWORDS)


def detect_friend_trigger(text: str) -> bool:
    t = _normalize(text)
    return any(kw in t for kw in _FRIEND_KEYWORDS)


def detect_distress(text: str) -> bool:
    t = _normalize(text)
    return any(kw in t for kw in _DISTRESS_KEYWORDS)


def extract_task_goal(text: str) -> Optional[str]:
    """Trích goal từ câu trigger. Ví dụ: 'học 5 bài toán' → '5 bài toán'."""
    t = _normalize(text)
    for kw in _TEACHER_KEYWORDS:
        if kw in t:
            idx = t.find(kw) + len(kw)
            rest = text[idx:].strip(" ,.")
            if rest and len(rest) > 1:
                return rest[:80]
    return None


# ── State ─────────────────────────────────────────────────────────────────────

@dataclass
class RoleState:
    current_role: str = ROLE_FRIEND
    task_goal: Optional[str] = None     # "5 bài toán nhân" / set từ parent app
    task_progress: int = 0
    time_limit_seconds: Optional[int] = None  # set từ parent app
    time_started: Optional[float] = None
    exit_attempts: int = 0              # số lần bé đòi thoát Teacher mode

    def is_time_expired(self) -> bool:
        if self.time_limit_seconds and self.time_started:
            return (time.time() - self.time_started) > self.time_limit_seconds
        return False

    def remaining_seconds(self) -> Optional[int]:
        if self.time_limit_seconds and self.time_started:
            r = self.time_limit_seconds - int(time.time() - self.time_started)
            return max(0, r)
        return None

    def to_system_context(self) -> Optional[str]:
        """Context string inject vào prompt để AI biết task goal + timer."""
        if self.current_role != ROLE_TEACHER:
            return None
        parts = [
            "[CHE DO GIAO VIEN] Day theo tung buoc nho, khong dua dap an ngay. "
            "Hay hoi be thu nghi hoac giai thich lai bang loi cua be."
        ]
        if self.task_goal:
            parts.append(
                f"Muc tieu hoc: {self.task_goal}."
                f" Da lam xong: {self.task_progress}."
            )
        remaining = self.remaining_seconds()
        if remaining is not None:
            mins, secs = divmod(remaining, 60)
            if mins > 0:
                parts.append(f"Thoi gian hoc con lai: {mins} phut {secs} giay.")
            else:
                parts.append(f"Thoi gian hoc con lai: {secs} giay. Sap het gio roi!")
        return " ".join(parts) if parts else "[CHE DO GIAO VIEN] Dang trong session hoc."


# ── Manager ───────────────────────────────────────────────────────────────────

class RoleManager:
    """
    Quản lý chuyển đổi Friend ↔ Teacher trong session của bé.
    Không dùng cho parent roles (set từ ngoài qua set_role()).
    """

    def __init__(self, default_role: str = ROLE_FRIEND):
        self.state = RoleState(current_role=default_role)

    def set_role(self, role: str, task_goal: Optional[str] = None,
                 time_limit_seconds: Optional[int] = None) -> None:
        """Set vai trò từ ngoài (phụ huynh qua Parent App hoặc API layer)."""
        self.state.current_role = role
        if task_goal:
            self.state.task_goal = task_goal
        if time_limit_seconds:
            self.state.time_limit_seconds = time_limit_seconds
            self.state.time_started = time.time()
        self.state.exit_attempts = 0

    def mark_task_progress(self, increment: int = 1) -> None:
        self.state.task_progress += increment

    def process_message(self, user_text: str) -> Optional[str]:
        """
        Phân tích lời bé, cập nhật state nếu cần chuyển vai.

        Returns:
            Transition event string hoặc None nếu không có gì thay đổi.
            Caller dùng event để chèn câu chuyển vai vào response.
        """
        role = self.state.current_role

        # Parent roles không tự động switch — chỉ set từ ngoài
        if role in (ROLE_PARENT_CHILD, ROLE_PARENT_ADVISOR):
            return None

        # 1. Distress override — luôn ưu tiên cao nhất
        if detect_distress(user_text) and role == ROLE_TEACHER:
            self.state.current_role = ROLE_FRIEND
            self.state.exit_attempts = 0
            return TRANSITION_DISTRESS

        # 2. Hết giờ
        if role == ROLE_TEACHER and self.state.is_time_expired():
            self.state.current_role = ROLE_FRIEND
            self.state.exit_attempts = 0
            return TRANSITION_TIME_UP

        # 3. Friend → Teacher
        if role == ROLE_FRIEND and detect_teacher_trigger(user_text):
            goal = extract_task_goal(user_text)
            self.state.current_role = ROLE_TEACHER
            self.state.task_goal = goal
            self.state.task_progress = 0
            self.state.time_started = time.time()
            self.state.exit_attempts = 0
            return TRANSITION_TO_TEACHER

        # 4. Teacher: bé đòi thoát
        if role == ROLE_TEACHER and detect_friend_trigger(user_text):
            self.state.exit_attempts += 1
            if self.state.exit_attempts >= 3:
                self.state.current_role = ROLE_FRIEND
                self.state.exit_attempts = 0
                return TRANSITION_TO_FRIEND
            if self.state.exit_attempts == 2:
                return TEACHER_HOLD_FINAL
            return TEACHER_HOLD

        return None

    @property
    def current_role(self) -> str:
        return self.state.current_role

    def get_system_context(self) -> Optional[str]:
        return self.state.to_system_context()


# ── Câu chuyển vai — inject vào đầu response của AI ─────────────────────────

TRANSITION_LINES = {
    TRANSITION_TO_TEACHER: "Oke minh hoc nao! Bi se di tung buoc nho, be thu nghi truoc roi Bi goi y nhe.",
    TRANSITION_TO_FRIEND: "Ok xong hoc roi! Gio choi thoi, be muon lam gi nao?",
    TRANSITION_DISTRESS: "",  # không nói gì — prompt sẽ xử lý cảm xúc
    TRANSITION_TIME_UP: "Het gio hoc roi! Be hoc tot lam hom nay. Gio nghi nhe!",
    TRANSITION_TASK_DONE: "Xong het roi! Be gioi lam! Gio choi khong?",
    TEACHER_HOLD: "Minh lam not mot buoc nho nua roi choi nhe, be thu noi cach nghi cua be xem!",
    TEACHER_HOLD_FINAL: "Gan xong roi be, neu met qua thi lam cau nay that ngan roi Bi cho nghi nhe!",
}
