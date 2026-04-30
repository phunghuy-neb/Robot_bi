"""Simple word quiz game engine."""

from __future__ import annotations

import logging
import random
import time

logger = logging.getLogger(__name__)

_LEADERBOARD: dict[str, list[dict]] = {}


class WordQuizGame:
    """Game trac nghiem tu vung cho tre em."""

    _QUESTIONS = [
        {"question": "CAT nghia la gi?", "answer": "Con meo", "options": ["Con meo", "Con cho", "Con ca", "Con chim"], "explanation": "CAT la con meo."},
        {"question": "DOG nghia la gi?", "answer": "Con cho", "options": ["Con cho", "Con bo", "Con vit", "Con rua"], "explanation": "DOG la con cho."},
        {"question": "RED la mau nao?", "answer": "Mau do", "options": ["Mau do", "Mau xanh", "Mau vang", "Mau den"], "explanation": "RED la mau do."},
        {"question": "ONE la so may?", "answer": "So mot", "options": ["So mot", "So hai", "So ba", "So bon"], "explanation": "ONE la so mot."},
    ]

    def __init__(self):
        """Khoi tao game rong."""
        self.family_id = "default"
        self.difficulty = "easy"
        self.active = False
        self.score = 0
        self.correct = 0
        self.incorrect = 0
        self._current: dict | None = None
        self._started_at = 0.0

    def start_game(self, family_id: str, difficulty: str = "easy") -> dict:
        """Bat dau game moi."""
        try:
            self.family_id = family_id
            self.difficulty = difficulty
            self.active = True
            self.score = 0
            self.correct = 0
            self.incorrect = 0
            self._started_at = time.time()
            self._current = None
            return {"family_id": family_id, "difficulty": difficulty, "status": "started"}
        except Exception:
            logger.exception("[WordQuizGame] start_game failed")
            return {"family_id": family_id, "difficulty": difficulty, "status": "error"}

    def get_question(self) -> dict:
        """Returns `{question, options: [4 choices], time_limit_sec}`."""
        try:
            if not self.active:
                self.start_game(self.family_id, self.difficulty)
            self._current = random.choice(self._QUESTIONS)
            options = list(self._current["options"])
            random.shuffle(options)
            return {"question": self._current["question"], "options": options, "time_limit_sec": 20}
        except Exception:
            logger.exception("[WordQuizGame] get_question failed")
            return {"question": "", "options": [], "time_limit_sec": 20}

    def submit_answer(self, answer: str) -> dict:
        """Returns `{correct, score, explanation}`."""
        try:
            if not self._current:
                self.get_question()
            expected = str(self._current.get("answer", "")) if self._current else ""
            ok = str(answer).strip().lower() == expected.lower()
            if ok:
                self.correct += 1
                self.score += 10
            else:
                self.incorrect += 1
            return {
                "correct": ok,
                "score": self.score,
                "explanation": self._current.get("explanation", "") if self._current else "",
            }
        except Exception:
            logger.exception("[WordQuizGame] submit_answer failed")
            return {"correct": False, "score": self.score, "explanation": ""}

    def end_game(self) -> dict:
        """Returns `{total_score, correct, incorrect, high_score}`."""
        try:
            self.active = False
            entry = {"score": self.score, "correct": self.correct, "incorrect": self.incorrect}
            board = _LEADERBOARD.setdefault(self.family_id, [])
            board.append(entry)
            board.sort(key=lambda item: item["score"], reverse=True)
            del board[10:]
            high_score = board[0]["score"] if board else self.score
            return {
                "total_score": self.score,
                "correct": self.correct,
                "incorrect": self.incorrect,
                "high_score": high_score,
            }
        except Exception:
            logger.exception("[WordQuizGame] end_game failed")
            return {"total_score": self.score, "correct": self.correct, "incorrect": self.incorrect, "high_score": self.score}

    def get_leaderboard(self, family_id: str) -> list:
        """Lay leaderboard cua family."""
        try:
            return list(_LEADERBOARD.get(family_id, []))
        except Exception:
            logger.exception("[WordQuizGame] get_leaderboard failed")
            return []
