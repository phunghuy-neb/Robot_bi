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
        user_answer = user_answer.lower()
        variants = [v.lower() for v in riddle.get("accept_variants", [])]
        return user_answer in variants or user_answer == riddle.get("answer", "").lower()

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
        return {
            "riddle_text": riddle.get("riddle_text", "Không có câu đố"),
            "hint": riddle.get("hint", ""),
            "answer": riddle.get("answer", "")
        }

    def check_voice_answer(self, user_answer: str) -> dict:
        correct = self.check_answer(self._current_riddle, user_answer)
        score = 10 if correct else 0
        if hasattr(self, '_score'):
            self._score += score
        return {
            "correct": correct,
            "score": score
        }
