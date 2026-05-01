import json
import random
from pathlib import Path


class WordQuizGame:
    def __init__(self, difficulty: str = "easy"):
        self._family_id = "default"
        self._difficulty = difficulty
        self._score = 0
        self._correct = 0
        self._incorrect = 0
        self._questions_answered = 0
        self._total_questions = 0
        self._correct_answers = 0
        self._current = None
        self._current_question = None
        self.questions = []
        self._questions = self.questions
        self._load(difficulty)

    def _load(self, difficulty: str):
        self._difficulty = difficulty
        path = Path(f"resources/games/word_quiz_{difficulty}.json")
        self.questions = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.questions = data.get("questions", [])
        except Exception:
            self.questions = []
        self._questions = self.questions

    def _prepare_question(self, question: dict) -> dict:
        prepared = dict(question or {})
        options = list(prepared.get("options") or [])
        prepared["options"] = options
        try:
            correct_idx = int(prepared.get("correct", 0))
        except (TypeError, ValueError):
            correct_idx = 0
        prepared["correct"] = correct_idx
        if "answer" not in prepared and 0 <= correct_idx < len(options):
            prepared["answer"] = options[correct_idx]
        return prepared

    def _answer_to_index(self, question: dict, answer) -> int:
        options = question.get("options", [])
        if isinstance(answer, str):
            if answer in options:
                return options.index(answer)
            try:
                return int(answer)
            except (TypeError, ValueError):
                return -1
        try:
            return int(answer)
        except (TypeError, ValueError):
            return -1

    def get_random_question(self) -> dict:
        questions = getattr(self, "_questions", self.questions)
        if not questions:
            return {}
        return self._prepare_question(random.choice(questions))

    def check_answer(self, question, answer_idx) -> bool:
        if not question:
            return False
        prepared = self._prepare_question(question)
        return self._answer_to_index(prepared, answer_idx) == prepared.get("correct", 0)

    def start_game(self, family_id: str, difficulty: str = "easy") -> dict:
        self._family_id = family_id
        self._difficulty = difficulty
        self._score = 0
        self._correct = 0
        self._incorrect = 0
        self._questions_answered = 0
        self._total_questions = 0
        self._correct_answers = 0
        self._current = None
        self._current_question = None
        self._load(difficulty)
        return {
            "status": "started",
            "family_id": family_id,
            "difficulty": difficulty,
            "game_type": "word_quiz",
        }

    def get_question(self) -> dict:
        q = self.get_random_question()
        if not q:
            return {}
        self._current = q
        self._current_question = q
        question_text = q.get("question", q.get("question_text", ""))
        return {
            "question": question_text,
            "question_text": question_text,
            "options": q.get("options", []),
            "time_limit_sec": q.get("time_limit_sec", 30),
        }

    def submit_answer(self, answer) -> dict:
        q = getattr(self, "_current", None) or getattr(self, "_current_question", None)
        if not q:
            return {"correct": False, "score": self._score}

        q = self._prepare_question(q)
        correct_idx = q.get("correct", 0)
        answer_idx = self._answer_to_index(q, answer)
        correct = answer_idx == correct_idx
        self._questions_answered += 1
        self._total_questions = self._questions_answered

        if correct:
            self._correct += 1
            self._correct_answers = self._correct
            self._score += 10
        else:
            self._incorrect += 1

        options = q.get("options", [])
        correct_text = ""
        if 0 <= correct_idx < len(options):
            correct_text = options[correct_idx]

        return {
            "correct": correct,
            "score": self._score,
            "explanation": q.get("explanation", f"Đáp án đúng: {correct_text}"),
        }

    def end_game(self) -> dict:
        high_score = self._get_high_score()
        if self._score > high_score:
            self._save_high_score(self._score)
            high_score = self._score
        return {
            "total_score": self._score,
            "correct": self._correct,
            "incorrect": self._incorrect,
            "high_score": high_score,
            "questions_answered": self._questions_answered,
        }

    def get_leaderboard(self, family_id: str) -> list:
        try:
            from src.infrastructure.database.db import get_db_connection

            with get_db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT '' AS username, score, created_at
                    FROM game_scores
                    WHERE family_id = ?
                    ORDER BY score DESC LIMIT 10
                    """,
                    (family_id,),
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception:
            return []

    def _get_high_score(self) -> int:
        try:
            from src.infrastructure.database.db import get_db_connection

            with get_db_connection() as conn:
                row = conn.execute(
                    """
                    SELECT MAX(score) FROM game_scores
                    WHERE family_id = ?
                    """,
                    (self._family_id,),
                ).fetchone()
                return int(row[0] or 0)
        except Exception:
            return 0

    def _save_high_score(self, score: int):
        try:
            from datetime import datetime, timezone

            from src.infrastructure.database.db import get_db_connection

            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO game_scores
                    (family_id, score, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        self._family_id,
                        score,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
        except Exception:
            pass
