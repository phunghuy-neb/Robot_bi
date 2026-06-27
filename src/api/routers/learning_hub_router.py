"""
learning_hub_router.py — Duolingo-style Learning Hub for Robot Bi.

GET  /api/learning/modules                   — list modules + progress
GET  /api/learning/lessons/{lesson_id}       — lesson detail with items
POST /api/learning/lessons/{lesson_id}/submit — submit answers, earn XP
GET  /api/learning/progress                  — streak + total XP + per-module
GET  /api/learning/streak                    — current streak info
"""

import json
import logging
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import get_db_connection
from src.api.routers.conversation_router import _require_family

logger = logging.getLogger(__name__)
router = APIRouter()

MODULE_META = {
    # English
    "colors":       {"label": "Colors",         "label_vi": "Màu sắc",      "emoji": "🎨", "subject": "en"},
    "animals":      {"label": "Animals",        "label_vi": "Động vật",     "emoji": "🐾", "subject": "en"},
    "numbers":      {"label": "Numbers",        "label_vi": "Số đếm",       "emoji": "🔢", "subject": "en"},
    "family":       {"label": "Family",         "label_vi": "Gia đình",     "emoji": "👨‍👩‍👧", "subject": "en"},
    # Math
    "math_shapes":  {"label": "Hình dạng",      "label_vi": "Shapes",       "emoji": "🔺", "subject": "math"},
    "math_add":     {"label": "Phép cộng",      "label_vi": "Addition",     "emoji": "➕", "subject": "math"},
    "math_count":   {"label": "Đếm số",         "label_vi": "Counting",     "emoji": "🔢", "subject": "math"},
    # Science
    "sci_weather":  {"label": "Thiên nhiên",    "label_vi": "Nature",       "emoji": "☀️", "subject": "science"},
    "sci_body":     {"label": "Cơ thể người",   "label_vi": "Human Body",   "emoji": "🧠", "subject": "science"},
    "sci_plant":    {"label": "Thực vật",       "label_vi": "Plants",       "emoji": "🌱", "subject": "science"},
}


def _today() -> str:
    return date.today().isoformat()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_or_create_streak(conn, family_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM learning_streaks WHERE family_id = ?", (family_id,)
    ).fetchone()
    if row:
        return dict(row)
    streak_id = uuid4().hex
    conn.execute(
        """INSERT INTO learning_streaks (streak_id, family_id, current_streak,
           longest_streak, last_activity_date, total_xp)
           VALUES (?, ?, 0, 0, NULL, 0)""",
        (streak_id, family_id),
    )
    return {
        "streak_id": streak_id, "family_id": family_id,
        "current_streak": 0, "longest_streak": 0,
        "last_activity_date": None, "total_xp": 0,
    }


def _update_streak(conn, family_id: str, xp_delta: int) -> dict:
    streak = _get_or_create_streak(conn, family_id)
    today = _today()
    last = streak["last_activity_date"]
    current = streak["current_streak"]

    if last is None:
        current = 1
    elif last == today:
        pass  # already active today, don't increment
    else:
        try:
            delta = (date.fromisoformat(today) - date.fromisoformat(last)).days
            current = current + 1 if delta == 1 else 1
        except ValueError:
            current = 1

    longest = max(streak["longest_streak"], current)
    total_xp = streak["total_xp"] + xp_delta

    conn.execute(
        """UPDATE learning_streaks
           SET current_streak = ?, longest_streak = ?,
               last_activity_date = ?, total_xp = ?
           WHERE family_id = ?""",
        (current, longest, today, total_xp, family_id),
    )
    return {**streak, "current_streak": current, "longest_streak": longest,
            "last_activity_date": today, "total_xp": total_xp}


@router.get("/api/learning/modules")
async def get_learning_modules(
    language: Optional[str] = Query(default=None, max_length=20),
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        if language:
            lessons = conn.execute(
                "SELECT lesson_id, module FROM learning_lessons WHERE language = ? ORDER BY order_index",
                (language,),
            ).fetchall()
        else:
            lessons = conn.execute(
                "SELECT lesson_id, module FROM learning_lessons ORDER BY order_index"
            ).fetchall()
        progress_rows = conn.execute(
            "SELECT lesson_id, completed, xp_earned FROM learning_progress WHERE family_id = ?",
            (family_id,),
        ).fetchall()
        streak = _get_or_create_streak(conn, family_id)
        conn.commit()

    progress_map = {r["lesson_id"]: dict(r) for r in progress_rows}
    modules: dict[str, dict] = {}
    for lesson in lessons:
        mod = lesson["module"]
        if mod not in modules:
            meta = MODULE_META.get(mod, {"label": mod, "label_vi": mod, "emoji": "📚", "subject": "en"})
            modules[mod] = {
                "module": mod,
                "label": meta["label"],
                "label_vi": meta["label_vi"],
                "emoji": meta["emoji"],
                "subject": meta.get("subject", "en"),
                "total_lessons": 0,
                "completed_lessons": 0,
                "module_xp": 0,
                "lessons": [],
            }
        p = progress_map.get(lesson["lesson_id"], {})
        modules[mod]["total_lessons"] += 1
        if p.get("completed"):
            modules[mod]["completed_lessons"] += 1
            modules[mod]["module_xp"] += p.get("xp_earned", 0)
        modules[mod]["lessons"].append({
            "lesson_id": lesson["lesson_id"],
            "completed": bool(p.get("completed")),
        })

    return {
        "modules": list(modules.values()),
        "streak": {
            "current": streak["current_streak"],
            "longest": streak["longest_streak"],
            "total_xp": streak["total_xp"],
        },
    }


@router.get("/api/learning/lessons/{lesson_id}")
async def get_lesson(lesson_id: str, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        lesson = conn.execute(
            "SELECT * FROM learning_lessons WHERE lesson_id = ?", (lesson_id,)
        ).fetchone()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        items = conn.execute(
            "SELECT * FROM learning_items WHERE lesson_id = ? ORDER BY order_index",
            (lesson_id,),
        ).fetchall()
        progress = conn.execute(
            "SELECT * FROM learning_progress WHERE family_id = ? AND lesson_id = ?",
            (family_id, lesson_id),
        ).fetchone()

    return {
        "lesson": dict(lesson),
        "items": [
            {
                "item_id": r["item_id"],
                "order_index": r["order_index"],
                "question": r["question"],
                "question_vi": r["question_vi"],
                "emoji": r["emoji"],
                "options": json.loads(r["options_json"] or "[]"),
            }
            for r in items
        ],
        "progress": dict(progress) if progress else None,
    }


class SubmitAnswers(BaseModel):
    answers: list[str]


@router.post("/api/learning/lessons/{lesson_id}/submit")
async def submit_lesson(
    lesson_id: str,
    body: SubmitAnswers,
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)

    with get_db_connection() as conn:
        lesson = conn.execute(
            "SELECT * FROM learning_lessons WHERE lesson_id = ?", (lesson_id,)
        ).fetchone()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        items = conn.execute(
            "SELECT item_id, answer FROM learning_items WHERE lesson_id = ? ORDER BY order_index",
            (lesson_id,),
        ).fetchall()

        answers = body.answers
        correct_map = {}
        score = 0
        for i, item in enumerate(items):
            given = answers[i].strip() if i < len(answers) else ""
            correct = item["answer"].strip()
            is_correct = given.lower() == correct.lower()
            correct_map[item["item_id"]] = {
                "correct": is_correct,
                "given": given,
                "expected": correct,
            }
            if is_correct:
                score += 1

        total = len(items)
        xp_earned = score * 2
        completed = score >= max(1, round(total * 0.8))

        existing = conn.execute(
            "SELECT progress_id, attempts FROM learning_progress WHERE family_id = ? AND lesson_id = ?",
            (family_id, lesson_id),
        ).fetchone()

        if existing:
            attempts = existing["attempts"] + 1
            conn.execute(
                """UPDATE learning_progress
                   SET score = ?, xp_earned = MAX(xp_earned, ?), completed = MAX(completed, ?),
                       completed_at = CASE WHEN ? = 1 AND completed = 0 THEN ? ELSE completed_at END,
                       attempts = ?
                   WHERE family_id = ? AND lesson_id = ?""",
                (score, xp_earned, 1 if completed else 0,
                 1 if completed else 0, _utc_now(),
                 attempts, family_id, lesson_id),
            )
            xp_earned = xp_earned if not existing else xp_earned
        else:
            attempts = 1
            conn.execute(
                """INSERT INTO learning_progress
                   (progress_id, family_id, lesson_id, completed, score, xp_earned, completed_at, attempts)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (uuid4().hex, family_id, lesson_id,
                 1 if completed else 0, score, xp_earned,
                 _utc_now() if completed else None, 1),
            )

        streak = _update_streak(conn, family_id, xp_earned)
        conn.commit()

    return {
        "ok": True,
        "score": score,
        "total": total,
        "xp_earned": xp_earned,
        "completed": completed,
        "correct_map": correct_map,
        "streak": {
            "current": streak["current_streak"],
            "total_xp": streak["total_xp"],
        },
    }


@router.get("/api/learning/progress")
async def get_progress(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        streak = _get_or_create_streak(conn, family_id)
        conn.commit()
        rows = conn.execute(
            """SELECT ll.module, lp.completed, lp.xp_earned
               FROM learning_progress lp
               JOIN learning_lessons ll ON ll.lesson_id = lp.lesson_id
               WHERE lp.family_id = ?""",
            (family_id,),
        ).fetchall()
        totals = conn.execute(
            "SELECT module, COUNT(*) as cnt FROM learning_lessons GROUP BY module"
        ).fetchall()

    module_totals = {r["module"]: r["cnt"] for r in totals}
    module_progress: dict[str, dict] = {}
    for r in rows:
        mod = r["module"]
        if mod not in module_progress:
            module_progress[mod] = {"completed": 0, "xp": 0,
                                    "total": module_totals.get(mod, 0)}
        if r["completed"]:
            module_progress[mod]["completed"] += 1
        module_progress[mod]["xp"] += r["xp_earned"]

    return {
        "streak": {
            "current": streak["current_streak"],
            "longest": streak["longest_streak"],
            "last_activity_date": streak["last_activity_date"],
            "total_xp": streak["total_xp"],
        },
        "modules": module_progress,
    }


@router.get("/api/learning/streak")
async def get_streak(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        streak = _get_or_create_streak(conn, family_id)
        conn.commit()
    return {
        "current": streak["current_streak"],
        "longest": streak["longest_streak"],
        "last_activity_date": streak["last_activity_date"],
        "total_xp": streak["total_xp"],
    }


# ── Luyện theo bài (spec 007 US4) — câu hỏi đơn lẻ, chấm từng câu ────────────────
# Giữ đáp án ở server (không trả trong /practice); chỉ lộ khi chấm (/practice/grade).

class PracticeGradeIn(BaseModel):
    question_id: str
    answer: str = ""


@router.get("/api/learning/practice")
async def practice_questions(
    subject: str = Query(..., max_length=40),
    topic: Optional[str] = Query(default=None, max_length=80),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    """Câu hỏi luyện theo bài cho 1 môn (family-scoped, chỉ MCQ). KHÔNG trả đáp án."""
    family_id = _require_family(current_user)
    params = [subject, family_id]
    topic_clause = ""
    if topic:
        topic_clause = " AND topic = ?"
        params.append(topic)
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""SELECT question_id, subject, topic, question, question_vi, emoji, options_json
                FROM question_bank
                WHERE subject = ? AND status = 'published' AND question_type = 'mcq'
                  AND (family_id IS NULL OR family_id = ?){topic_clause}
                ORDER BY RANDOM() LIMIT {int(limit)}""",
            tuple(params),
        ).fetchall()
    questions = []
    for r in rows:
        try:
            options = json.loads(r["options_json"] or "[]")
        except Exception:
            options = []
        questions.append({
            "question_id": r["question_id"], "subject": r["subject"], "topic": r["topic"],
            "question": r["question"], "question_vi": r["question_vi"],
            "emoji": r["emoji"], "options": options,
        })
    return {"questions": questions}


@router.get("/api/learning/mistakes")
async def learning_mistakes(
    subject: Optional[str] = Query(default=None, max_length=40),
    current_user: dict = Depends(get_current_user),
):
    """Sổ lỗi (spec 007 US5): câu trẻ trả lời SAI ở lần GẦN NHẤT (family-scoped, MCQ).
    Suy từ exam_sessions.answers_json × question_bank.answer. KHÔNG trả đáp án."""
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        sessions = conn.execute(
            """SELECT answers_json FROM exam_sessions
               WHERE family_id = ? AND status = 'completed'
               ORDER BY completed_at DESC""",
            (family_id,),
        ).fetchall()
        latest = {}
        for s in sessions:
            try:
                ans = json.loads(s["answers_json"] or "{}")
            except Exception:
                ans = {}
            for qid, a in ans.items():
                if qid not in latest:  # phiên mới nhất trước → giữ câu trả lời gần nhất
                    latest[qid] = a
        if not latest:
            return {"mistakes": [], "count": 0}
        qids = list(latest.keys())
        ph = ",".join("?" for _ in qids)
        params = qids + [family_id]
        subj_clause = ""
        if subject:
            subj_clause = " AND subject = ?"
            params.append(subject)
        rows = conn.execute(
            f"""SELECT question_id, subject, topic, question, question_vi, emoji, options_json, answer
                FROM question_bank
                WHERE question_id IN ({ph}) AND question_type = 'mcq'
                  AND (family_id IS NULL OR family_id = ?){subj_clause}""",
            tuple(params),
        ).fetchall()
    mistakes = []
    for r in rows:
        given = str(latest.get(r["question_id"], "")).strip()
        if given == (r["answer"] or "").strip():
            continue  # lần gần nhất đã đúng → không còn là lỗi
        try:
            options = json.loads(r["options_json"] or "[]")
        except Exception:
            options = []
        mistakes.append({
            "question_id": r["question_id"], "subject": r["subject"], "topic": r["topic"] or "Khác",
            "question": r["question"], "question_vi": r["question_vi"], "emoji": r["emoji"], "options": options,
        })
    return {"mistakes": mistakes, "count": len(mistakes)}


@router.post("/api/learning/practice/grade")
async def practice_grade(body: PracticeGradeIn, current_user: dict = Depends(get_current_user)):
    """Chấm 1 câu luyện tập, trả đúng/sai + đáp án đúng + giải thích (family-scoped)."""
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT answer, explanation FROM question_bank
               WHERE question_id = ? AND (family_id IS NULL OR family_id = ?)""",
            (body.question_id, family_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Khong tim thay cau hoi")
    correct_answer = (row["answer"] or "").strip()
    is_correct = body.answer.strip() == correct_answer
    return {
        "correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": row["explanation"] or "",
    }
