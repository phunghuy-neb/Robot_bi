"""Voice riddle quiz game engine."""

from __future__ import annotations

import logging
import re
import unicodedata
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class VoiceQuizGame:
    """Game do vui tra loi bang giong noi."""

    _RIDDLES = [
        {"riddle_text": "Con gi keu meo meo?", "hint": "Vat nuoi trong nha", "answer": "con meo"},
        {"riddle_text": "Qua gi mau vang, khi boc vo co mui thom?", "hint": "Khi an co the thay nhieu mui", "answer": "qua chuoi"},
        {"riddle_text": "Cai gi dung de viet bai?", "hint": "Do dung hoc tap", "answer": "but chi"},
    ]

    def __init__(self):
        """Khoi tao game rong."""
        self.family_id = "default"
        self.active = False
        self.score = 0
        self._index = -1
        self._current: dict | None = None

    def start_game(self, family_id: str) -> dict:
        """Bat dau voice quiz."""
        try:
            self.family_id = family_id
            self.active = True
            self.score = 0
            self._index = -1
            self._current = None
            return {"family_id": family_id, "status": "started"}
        except Exception:
            logger.exception("[VoiceQuizGame] start_game failed")
            return {"family_id": family_id, "status": "error"}

    def get_riddle(self) -> dict:
        """Returns `{riddle_text, hint, answer}`."""
        try:
            if not self.active:
                self.start_game(self.family_id)
            self._index = (self._index + 1) % len(self._RIDDLES)
            self._current = self._RIDDLES[self._index]
            return dict(self._current)
        except Exception:
            logger.exception("[VoiceQuizGame] get_riddle failed")
            return {"riddle_text": "", "hint": "", "answer": ""}

    def _normalize(self, text: str) -> str:
        """Normalize Vietnamese-ish transcript for fuzzy matching."""
        try:
            lowered = (text or "").strip().lower()
            decomposed = unicodedata.normalize("NFD", lowered)
            no_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
            return re.sub(r"[^a-z0-9\s]", "", no_marks).strip()
        except Exception:
            logger.exception("[VoiceQuizGame] normalize failed")
            return ""

    def check_voice_answer(self, spoken_text: str) -> dict:
        """Fuzzy match spoken_text voi answer."""
        try:
            if not self._current:
                self.get_riddle()
            expected = self._normalize(self._current.get("answer", "") if self._current else "")
            spoken = self._normalize(spoken_text)
            score = int(round(SequenceMatcher(None, spoken, expected).ratio() * 100)) if expected else 0
            correct = score >= 70
            if correct:
                self.score += 10
            return {"correct": correct, "score": score, "total_score": self.score, "answer": expected}
        except Exception:
            logger.exception("[VoiceQuizGame] check_voice_answer failed")
            return {"correct": False, "score": 0, "total_score": self.score, "answer": ""}

    def end_game(self) -> dict:
        """Ket thuc voice quiz va tra summary."""
        try:
            self.active = False
            return {"family_id": self.family_id, "total_score": self.score}
        except Exception:
            logger.exception("[VoiceQuizGame] end_game failed")
            return {"family_id": self.family_id, "total_score": self.score}
