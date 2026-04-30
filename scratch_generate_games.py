import json
import os

os.makedirs("resources/games", exist_ok=True)

def generate_word_quiz(difficulty, count, filename):
    questions = []
    for i in range(1, count + 1):
        questions.append({
            "id": f"q{i:03d}",
            "question": f"Câu hỏi {difficulty} số {i}?",
            "options": ["A", "B", "C", "D"],
            "correct": 0,
            "explanation": "Vì A là đáp án đúng.",
            "difficulty": difficulty
        })
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"questions": questions}, f, ensure_ascii=False, indent=2)

def generate_voice_riddles(count, filename):
    riddles = []
    for i in range(1, count + 1):
        riddles.append({
            "id": f"r{i:03d}",
            "riddle": f"Câu đố số {i} là gì?",
            "answer": "đáp án",
            "hints": ["Gợi ý 1", "Gợi ý 2"],
            "accept_variants": ["đáp án", "câu trả lời"]
        })
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"riddles": riddles}, f, ensure_ascii=False, indent=2)

generate_word_quiz("easy", 20, "resources/games/word_quiz_easy.json")
generate_word_quiz("medium", 20, "resources/games/word_quiz_medium.json")
generate_voice_riddles(15, "resources/games/voice_riddles.json")
