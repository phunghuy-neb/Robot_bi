"""
FlashcardEngine - Engine hoc flashcard da mon, da ngon ngu.

Engine nay chi doc data JSON cuc bo trong resources/flashcards va giu session
ngan han trong memory. Khong goi LLM va khong dung network.
"""

from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SUBJECTS = ["english", "math", "science", "history", "geography"]
LANGUAGES = ["en", "ja", "ko", "zh", "fr", "de", "es"]


class FlashcardEngine:
    """Quan ly mot session flashcard cho mot family."""

    def __init__(self, family_id: str, resources_dir="resources/flashcards"):
        """Khoi tao engine voi family_id va thu muc resources."""
        self.family_id = family_id
        self.resources_dir = Path(resources_dir)
        self.session: dict | None = None
        self.cards: list[dict] = []
        self.current_index = -1
        self.answers: list[dict] = []
        self.review_queue: list[dict] = []

    def _load_deck(self, subject: str, topic: str) -> dict:
        """Doc deck JSON theo subject/topic."""
        try:
            path = self.resources_dir / subject / f"{topic}.json"
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data.get("cards"), list):
                raise ValueError("Deck missing cards list")
            return data
        except Exception:
            logger.exception("[FlashcardEngine] Khong the load deck %s/%s", subject, topic)
            return {"subject": subject, "topic": topic, "language": "en", "cards": []}

    def start_session(
        self,
        subject: str,
        topic: str | None = None,
        language: str = "en",
        difficulty: str = "easy",
    ) -> dict:
        """Bat dau session hoc. Returns session info."""
        try:
            if subject not in SUBJECTS:
                subject = "english"
            if language not in LANGUAGES:
                language = "en"
            topic = topic or ("animals" if subject == "english" else "addition")
            deck = self._load_deck(subject, topic)
            self.cards = list(deck.get("cards", []))
            self.cards.sort(key=lambda card: int(card.get("difficulty", 1)))
            self.current_index = -1
            self.answers = []
            self.review_queue = []
            self.session = {
                "family_id": self.family_id,
                "subject": subject,
                "topic": topic,
                "language": language,
                "difficulty": difficulty,
                "started_at": time.time(),
                "total_cards": len(self.cards),
            }
            return dict(self.session)
        except Exception:
            logger.exception("[FlashcardEngine] start_session failed")
            self.session = None
            return {"family_id": self.family_id, "subject": subject, "topic": topic, "total_cards": 0}

    def get_next_card(self) -> dict:
        """Tra ve card tiep theo theo heuristic spaced repetition don gian."""
        try:
            if not self.session or not self.cards:
                return {}
            if self.review_queue:
                card = self.review_queue.pop(0)
            else:
                self.current_index = (self.current_index + 1) % len(self.cards)
                card = self.cards[self.current_index]
            result = dict(card)
            result["current"] = min(len(self.answers) + 1, len(self.cards))
            result["total"] = len(self.cards)
            return result
        except Exception:
            logger.exception("[FlashcardEngine] get_next_card failed")
            return {}

    def submit_answer(
        self,
        card_id: str,
        is_correct: bool,
        pronunciation_score: float | None = None,
    ) -> dict:
        """Nop cau tra loi. Returns feedback va next action."""
        try:
            card = next((item for item in self.cards if item.get("id") == card_id), None)
            answer = {
                "card_id": card_id,
                "correct": bool(is_correct),
                "pronunciation_score": pronunciation_score,
                "timestamp": time.time(),
            }
            self.answers.append(answer)
            if card and not is_correct:
                self.review_queue.append(card)
            feedback = "Dung roi!" if is_correct else "Chua dung, minh on lai nhe."
            return {
                "correct": bool(is_correct),
                "feedback": feedback,
                "next_action": "continue" if len(self.answers) < len(self.cards) else "review",
                "score": sum(1 for item in self.answers if item["correct"]),
            }
        except Exception:
            logger.exception("[FlashcardEngine] submit_answer failed")
            return {"correct": False, "feedback": "Co loi khi cham bai.", "next_action": "continue", "score": 0}

    def end_session(self) -> dict:
        """Ket thuc session. Returns summary."""
        try:
            correct = sum(1 for item in self.answers if item["correct"])
            incorrect = len(self.answers) - correct
            duration = 0
            if self.session:
                duration = int(time.time() - float(self.session.get("started_at", time.time())))
            summary = {
                "family_id": self.family_id,
                "subject": self.session.get("subject") if self.session else None,
                "topic": self.session.get("topic") if self.session else None,
                "total_answered": len(self.answers),
                "correct": correct,
                "incorrect": incorrect,
                "duration_sec": duration,
            }
            self.session = None
            return summary
        except Exception:
            logger.exception("[FlashcardEngine] end_session failed")
            return {"total_answered": 0, "correct": 0, "incorrect": 0, "duration_sec": 0}

    def get_review_cards(self) -> list:
        """Tra ve cac cards can on tap do da sai trong session."""
        try:
            return [dict(card) for card in self.review_queue]
        except Exception:
            logger.exception("[FlashcardEngine] get_review_cards failed")
            return []
