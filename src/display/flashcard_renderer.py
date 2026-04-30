"""
FlashcardRenderer — Quản lý flashcard data cho Robot Bi.
Load từ resources/flashcards/ hoặc dùng sample deck built-in.
"""

import json
import os
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SAMPLE_DECK = [
    {"emoji": "🐱", "word": "CAT", "phonetic": "/kæt/", "meaning": "Con mèo"},
    {"emoji": "🐶", "word": "DOG", "phonetic": "/dɒɡ/", "meaning": "Con chó"},
    {"emoji": "🐟", "word": "FISH", "phonetic": "/fɪʃ/", "meaning": "Con cá"},
    {"emoji": "🐦", "word": "BIRD", "phonetic": "/bɜːrd/", "meaning": "Con chim"},
    {"emoji": "🌸", "word": "FLOWER", "phonetic": "/ˈflaʊər/", "meaning": "Bông hoa"},
    {"emoji": "🌳", "word": "TREE", "phonetic": "/triː/", "meaning": "Cái cây"},
    {"emoji": "🍎", "word": "APPLE", "phonetic": "/ˈæpəl/", "meaning": "Quả táo"},
    {"emoji": "🍌", "word": "BANANA", "phonetic": "/bəˈnɑːnə/", "meaning": "Quả chuối"},
    {"emoji": "📚", "word": "BOOK", "phonetic": "/bʊk/", "meaning": "Cuốn sách"},
    {"emoji": "✏️", "word": "PENCIL", "phonetic": "/ˈpensəl/", "meaning": "Cây bút chì"},
]


class FlashcardRenderer:
    def __init__(self, resources_dir: str = "resources/flashcards"):
        self.resources_dir = Path(resources_dir)
        self.current_deck = []
        self.current_index = 0
        self.score = 0
        self.correct_count = 0
        self.incorrect_count = 0

    def load_deck(self, subject: str, topic: str = None) -> int:
        """
        Load flashcard deck từ resources/ hoặc sample built-in.
        Returns số lượng cards đã load.
        """
        # Thử load từ file JSON
        if topic:
            json_path = self.resources_dir / subject / f"{topic}.json"
        else:
            json_path = self.resources_dir / subject / "basic.json"

        if json_path.exists():
            try:
                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)
                self.current_deck = data.get("cards", data)
                logger.info("[Flashcard] Loaded %d cards từ %s",
                            len(self.current_deck), json_path)
            except Exception as e:
                logger.warning("[Flashcard] Lỗi load file: %s → dùng sample", e)
                self.current_deck = SAMPLE_DECK.copy()
        else:
            logger.info("[Flashcard] Không có file → dùng sample deck")
            self.current_deck = SAMPLE_DECK.copy()

        random.shuffle(self.current_deck)
        self.current_index = 0
        self.score = 0
        self.correct_count = 0
        self.incorrect_count = 0
        return len(self.current_deck)

    def get_current_card(self) -> dict:
        """
        Trả về card hiện tại với đầy đủ metadata.
        Format: {emoji, word, phonetic, meaning, current, total}
        """
        if not self.current_deck:
            self.load_deck("english")

        card = self.current_deck[self.current_index].copy()
        card["current"] = self.current_index + 1
        card["total"] = len(self.current_deck)
        return card

    def next_card(self) -> dict:
        """Chuyển sang card tiếp theo, quay vòng."""
        if self.current_deck:
            self.current_index = (self.current_index + 1) % len(self.current_deck)
        return self.get_current_card()

    def prev_card(self) -> dict:
        """Quay lại card trước."""
        if self.current_deck:
            self.current_index = (self.current_index - 1) % len(self.current_deck)
        return self.get_current_card()

    def mark_correct(self) -> int:
        """Đánh dấu đúng, cộng điểm, trả về score mới."""
        self.correct_count += 1
        self.score += 10
        logger.info("[Flashcard] Đúng! Score: %d", self.score)
        return self.score

    def mark_incorrect(self):
        """Đánh dấu sai."""
        self.incorrect_count += 1
        logger.info("[Flashcard] Sai. Correct: %d, Incorrect: %d",
                    self.correct_count, self.incorrect_count)

    def get_progress(self) -> dict:
        """Trả về tiến độ học hiện tại."""
        total = len(self.current_deck)
        answered = self.correct_count + self.incorrect_count
        return {
            "correct": self.correct_count,
            "incorrect": self.incorrect_count,
            "remaining": max(0, total - answered),
            "score": self.score,
            "total": total,
            "answered": answered,
        }

    def reset(self):
        """Reset về đầu deck."""
        self.current_index = 0
        self.score = 0
        self.correct_count = 0
        self.incorrect_count = 0
        if self.current_deck:
            random.shuffle(self.current_deck)
