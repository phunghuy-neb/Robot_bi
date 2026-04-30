import json
import random
from pathlib import Path

class WordQuizGame:
    def __init__(self, difficulty="easy"):
        self.questions = []
        self._load(difficulty)
        
    def _load(self, difficulty):
        path = Path(f"resources/games/word_quiz_{difficulty}.json")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.questions = data.get("questions", [])
                
    def get_random_question(self):
        if not self.questions:
            return None
        return random.choice(self.questions)
        
    def check_answer(self, question, answer_idx):
        if not question:
            return False
        return question.get("correct") == answer_idx
