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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import get_db_connection
from src.api.routers.conversation_router import _require_family

logger = logging.getLogger(__name__)
router = APIRouter()

MODULE_META = {
    "colors":  {"label": "Colors",  "label_vi": "Màu sắc",  "emoji": "🎨"},
    "animals": {"label": "Animals", "label_vi": "Động vật", "emoji": "🐾"},
    "numbers": {"label": "Numbers", "label_vi": "Số đếm",   "emoji": "🔢"},
    "family":  {"label": "Family",  "label_vi": "Gia đình", "emoji": "👨‍👩‍👧"},
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
async def get_learning_modules(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
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
            meta = MODULE_META.get(mod, {"label": mod, "label_vi": mod, "emoji": "📚"})
            modules[mod] = {
                "module": mod,
                "label": meta["label"],
                "label_vi": meta["label_vi"],
                "emoji": meta["emoji"],
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
