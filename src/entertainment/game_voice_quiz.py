import json
import random
from pathlib import Path

class VoiceQuizGame:
    def __init__(self):
        self.riddles = []
        self._load()
        
    def _load(self):
        path = Path("resources/games/voice_riddles.json")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.riddles = data.get("riddles", [])
                
    def get_random_riddle(self):
        if not self.riddles:
            return None
        return random.choice(self.riddles)
        
    def check_answer(self, riddle, user_answer):
        if not riddle or not user_answer:
            return False
        user_norm = user_answer.lower().strip()
        answer_norm = riddle.get("answer", "").lower().strip()
        variants = [v.lower().strip() for v in riddle.get("accept_variants", [])]
        return (
            user_norm == answer_norm
            or user_norm in variants
            or (answer_norm and answer_norm in user_norm)
            or (user_norm and user_norm in answer_norm)
        )

    def start_game(self, family_id: str) -> dict:
        self._family_id = family_id
        self._score = 0
        self._current_riddle = None
        return {
            'status': 'started',
            'family_id': family_id,
            'game_type': 'voice_quiz'
        }

    def get_riddle(self) -> dict:
        riddle = self.get_random_riddle()
        if not riddle:
            riddle = {"riddle_text": "Không có câu đố", "hint": "", "answer": "", "accept_variants": []}
        self._current_riddle = riddle
        hints = riddle.get("hints") or []
        hint = hints[0] if hints else riddle.get("hint", "")
        return {
            "riddle_text": riddle.get("riddle_text") or riddle.get("riddle", ""),
            "hint": hint,
            "answer": riddle.get("answer", "")
        }

    def check_voice_answer(self, user_answer: str) -> dict:
        if not self._current_riddle or not user_answer:
            return {"correct": False, "score": 0}

        def norm(value: str) -> str:
            return value.lower().strip()

        user_norm = norm(user_answer)
        answer_norm = norm(self._current_riddle.get("answer", ""))
        variants = [
            norm(variant)
            for variant in self._current_riddle.get("accept_variants", [])
        ]

        exact = user_norm == answer_norm or user_norm in variants
        fuzzy = bool(answer_norm and user_norm) and (
            answer_norm in user_norm or user_norm in answer_norm
        )
        correct = exact or fuzzy
        score = 10 if exact else (5 if fuzzy else 0)

        if hasattr(self, '_score'):
            self._score += score
        return {
            "correct": correct,
            "score": score
        }
