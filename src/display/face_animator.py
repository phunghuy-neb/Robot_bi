"""
FaceAnimator — Quản lý trạng thái hiển thị mặt robot Bi.
Gửi events để frontend robot_display/index.html cập nhật UI.
"""

import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

VALID_MODES = ['idle', 'listening', 'thinking', 'talking', 'sleeping']
VALID_EMOTIONS = ['happy', 'sad', 'excited', 'angry', 'surprised', 'neutral']


class FaceAnimator:
    def __init__(self, notifier=None):
        self._lock = threading.Lock()
        self.current_mode = 'idle'
        self.current_emotion = 'neutral'
        self.last_changed = datetime.now().isoformat()
        self.notifier = notifier  # optional EventNotifier

    def set_mode(self, mode: str) -> bool:
        """
        Chuyển mode hiển thị.
        Returns True nếu thành công, False nếu mode không hợp lệ.
        """
        if mode not in VALID_MODES:
            logger.warning("[FaceAnimator] Mode không hợp lệ: %s", mode)
            return False
        with self._lock:
            old_mode = self.current_mode
            self.current_mode = mode
            self.last_changed = datetime.now().isoformat()
        logger.info("[FaceAnimator] Mode: %s → %s", old_mode, mode)
        self._notify("face_mode", {"mode": mode, "emotion": self.current_emotion})
        return True

    def set_emotion(self, emotion: str) -> bool:
        """
        Đặt cảm xúc hiển thị.
        Returns True nếu thành công, False nếu emotion không hợp lệ.
        """
        if emotion not in VALID_EMOTIONS:
            logger.warning("[FaceAnimator] Emotion không hợp lệ: %s", emotion)
            return False
        with self._lock:
            self.current_emotion = emotion
            self.last_changed = datetime.now().isoformat()
        logger.info("[FaceAnimator] Emotion → %s", emotion)
        self._notify("face_emotion", {"mode": self.current_mode, "emotion": emotion})
        return True

    def get_state(self) -> dict:
        """Trả về trạng thái hiện tại."""
        with self._lock:
            return {
                "mode": self.current_mode,
                "emotion": self.current_emotion,
                "last_changed": self.last_changed,
            }

    def _notify(self, event_type: str, data: dict):
        """Gửi event qua notifier nếu có."""
        if self.notifier:
            try:
                self.notifier.push_event(event_type, str(data))
            except Exception as e:
                logger.debug("[FaceAnimator] Notify error: %s", e)
