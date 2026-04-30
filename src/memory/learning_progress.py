"""Compatibility wrapper around education progress tracking."""

from __future__ import annotations

import logging

from src.education.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class LearningProgress:
    """Facade de cac module memory truy cap tien do hoc tap."""

    def __init__(self, family_id: str):
        """Khoi tao facade cho mot family."""
        self.family_id = family_id
        self.tracker = ProgressTracker()

    def record_flashcard_session(self, subject: str, correct: int, incorrect: int, duration_sec: int) -> bool:
        """Ghi nhan ket qua flashcard vao progress tracker."""
        try:
            return self.tracker.record_session(self.family_id, subject, correct, incorrect, duration_sec)
        except Exception:
            logger.exception("[LearningProgress] record_flashcard_session failed")
            return False

    def summary(self) -> dict:
        """Tra ve summary tien do tong the."""
        try:
            return self.tracker.get_overall_progress(self.family_id)
        except Exception:
            logger.exception("[LearningProgress] summary failed")
            return {"family_id": self.family_id, "sessions": 0, "subjects": {}}
