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
