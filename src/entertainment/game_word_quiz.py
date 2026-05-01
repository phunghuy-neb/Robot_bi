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

    def start_game(self, family_id: str) -> dict:
        self._family_id = family_id
        self._score = 0
        self._total_questions = 0
        self._correct_answers = 0
        self._current_question = None
        return {
            'status': 'started',
            'family_id': family_id,
            'game_type': 'word_quiz'
        }

    def get_question(self) -> dict:
        q = self.get_random_question()
        if not q:
            return {}
        self._current_question = q
        return {
            "question_text": q.get("question_text", ""),
            "options": q.get("options", []),
        }

    def submit_answer(self, answer_idx: int) -> dict:
        self._total_questions += 1
        correct = self.check_answer(self._current_question, answer_idx)
        if correct:
            self._correct_answers += 1
            self._score += 10
        return {
            "correct": correct,
            "score": self._score,
            "correct_answer_text": self._current_question["options"][self._current_question["correct"]] if self._current_question else ""
        }

    def end_game(self) -> dict:
        return {
            "status": "ended",
            "score": self._score,
            "correct_answers": self._correct_answers,
            "total_questions": self._total_questions
        }
