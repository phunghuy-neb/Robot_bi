"""Fuzzy pronunciation checker for spoken text transcripts."""

from __future__ import annotations

import logging
import re
import unicodedata
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class PronunciationChecker:
    """So sanh transcript STT voi tu/cum muc tieu bang fuzzy matching."""

    def check(self, spoken_text: str, target_word: str, language: str = "en") -> dict:
        """
        So sanh spoken_text voi target_word.

        Returns `{score, feedback, is_correct}`.
        """
        try:
            spoken = self.normalize_text(spoken_text, language)
            target = self.normalize_text(target_word, language)
            similarity = self.calculate_similarity(spoken, target)
            score = int(round(similarity * 100))
            is_correct = score >= 80
            if is_correct:
                feedback = "Phat am tot."
            elif score >= 55:
                feedback = "Gan dung, thu noi cham hon."
            else:
                feedback = "Chua giong tu muc tieu, minh thu lai nhe."
            return {"score": score, "feedback": feedback, "is_correct": is_correct}
        except Exception:
            logger.exception("[PronunciationChecker] check failed")
            return {"score": 0, "feedback": "Khong the kiem tra phat am.", "is_correct": False}

    def normalize_text(self, text: str, language: str) -> str:
        """Chuan hoa text: lowercase, bo dau, bo punctuation."""
        try:
            lowered = (text or "").strip().lower()
            decomposed = unicodedata.normalize("NFD", lowered)
            no_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
            return re.sub(r"[^a-z0-9\s]", "", no_marks).strip()
        except Exception:
            logger.exception("[PronunciationChecker] normalize_text failed")
            return ""

    def calculate_similarity(self, a: str, b: str) -> float:
        """Tinh similarity 0-1 giua hai chuoi."""
        try:
            if not a and not b:
                return 1.0
            if not a or not b:
                return 0.0
            return SequenceMatcher(None, a, b).ratio()
        except Exception:
            logger.exception("[PronunciationChecker] calculate_similarity failed")
            return 0.0
