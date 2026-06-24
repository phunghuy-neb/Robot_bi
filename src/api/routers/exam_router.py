"""
exam_router.py — Phase 1 exam & question-bank system for Robot Bi Learning Hub.

Catalog & discovery:
  GET  /api/learning/subjects                  — subjects that have content + counts
  GET  /api/learning/tracks                    — track/roadmap catalog + paper counts

Exams (timed tests assembled from the question bank):
  GET  /api/learning/exams                      — list published papers (filterable)
  GET  /api/learning/exams/{paper_id}           — paper + questions (answers hidden)
  POST /api/learning/exams/{paper_id}/submit    — grade, store attempt, return report
  GET  /api/learning/exams/sessions             — family attempt history
  GET  /api/learning/exams/sessions/{id}        — attempt detail

Admin content pipeline (is_admin only):
  POST /api/learning/admin/generate             — AI-generate questions -> review queue
  GET  /api/learning/admin/review               — list questions awaiting review
  POST /api/learning/admin/review/{question_id} — publish / reject a question
  POST /api/learning/admin/exams                — assemble an exam paper
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import get_db_connection, is_user_admin
from src.api.routers.conversation_router import _require_family

logger = logging.getLogger(__name__)
router = APIRouter()

TOEIC_SW_SUBJECT = "toeic_sw"
TOEIC_SPEAKING_TYPE = "toeic_speaking"
TOEIC_WRITING_TYPE = "toeic_writing"
TOEIC_SW_QUESTION_TYPES = {TOEIC_SPEAKING_TYPE, TOEIC_WRITING_TYPE}
TOEIC_ESTIMATE_DISCLAIMER = "điểm Robot Bi ước tính, không phải điểm ETS chính thức"
TOEIC_TASK_MAX_SCORES = {
    "read_aloud": 3,
    "email": 5,
    "respond_to_questions": 3,
    "describe_picture": 3,
    "express_opinion": 5,
    "opinion_essay": 5,
    "speaking": 3,
    "writing": 5,
}


# ── Display metadata (labels only; the available set is derived from the DB) ──
SUBJECT_LABELS = {
    "en":        {"label": "Tiếng Anh",        "emoji": "🔤"},
    "math":      {"label": "Toán",             "emoji": "🔢"},
    "science":   {"label": "Khoa học",         "emoji": "🔬"},
    "vietnamese":{"label": "Tiếng Việt",       "emoji": "🇻🇳"},
    "literature":{"label": "Ngữ văn",          "emoji": "📖"},
    "physics":   {"label": "Vật lý",           "emoji": "⚡"},
    "chemistry": {"label": "Hóa học",          "emoji": "⚗️"},
    "biology":   {"label": "Sinh học",         "emoji": "🧬"},
    "history":   {"label": "Lịch sử",          "emoji": "📜"},
    "geography": {"label": "Địa lý",           "emoji": "🌍"},
    "civics":    {"label": "Giáo dục công dân", "emoji": "🏛️"},
    "informatics":{"label": "Tin học",         "emoji": "💻"},
    "programming":{"label": "Lập trình",       "emoji": "🐍"},
    "music":     {"label": "Âm nhạc",          "emoji": "🎵"},
    "art":       {"label": "Mỹ thuật",         "emoji": "🎨"},
    "economics": {"label": "Kinh tế học",      "emoji": "📊"},
    "health":    {"label": "Dinh dưỡng & Sức khỏe", "emoji": "🍎"},
    "life_skills":{"label": "Kỹ năng sống",    "emoji": "🧭"},
    "logic":     {"label": "Tư duy logic",     "emoji": "🧩"},
    "chinese":   {"label": "Tiếng Trung",      "emoji": "🀄"},
    "japanese":  {"label": "Tiếng Nhật",       "emoji": "🗾"},
    "korean":    {"label": "Tiếng Hàn",        "emoji": "🇰🇷"},
    "ielts":     {"label": "IELTS",            "emoji": "📗"},
    "toeic_lr":  {"label": "TOEIC L&R",        "emoji": "🎧"},
    "toeic_sw":  {"label": "TOEIC S&W",        "emoji": "🗣️"},
}

# track_id -> label, kind (exam|competition|roadmap|practice), age hint
TRACK_CATALOG = {
    "practice":       {"label": "Luyện theo chủ đề", "kind": "practice"},
    "hsg_school":     {"label": "HSG cấp trường",    "kind": "competition"},
    "hsg_district":   {"label": "HSG cấp huyện",     "kind": "competition"},
    "hsg_province":   {"label": "HSG cấp tỉnh",      "kind": "competition"},
    "hsg_national":   {"label": "HSG cấp quốc gia",  "kind": "competition"},
    "exam_grade6":    {"label": "Thi vào lớp 6",     "kind": "exam"},
    "exam_grade10":   {"label": "Thi vào lớp 10",    "kind": "exam"},
    "exam_thpt":      {"label": "Thi THPT & Đại học", "kind": "exam"},
    "ielts":          {"label": "Lộ trình IELTS",    "kind": "roadmap"},
    "toeic_lr":       {"label": "Lộ trình TOEIC L&R", "kind": "roadmap"},
    "toeic_sw":       {"label": "Lộ trình TOEIC S&W", "kind": "roadmap"},
}

# Ordered levels for roadmap-style tracks (used by the frontend roadmap view).
ROADMAP_LEVELS = {
    "ielts": [
        "band_4.0", "band_4.5", "band_5.0", "band_5.5",
        "band_6.0", "band_6.5", "band_7.0", "band_7.5", "band_8.0",
    ],
    "toeic_lr": [
        "toeic_300", "toeic_400", "toeic_450", "toeic_500", "toeic_600",
        "toeic_700", "toeic_750", "toeic_800", "toeic_850", "toeic_990",
    ],
    "toeic_sw": [
        "toeic_sw_100", "toeic_sw_120", "toeic_sw_140",
        "toeic_sw_160", "toeic_sw_180", "toeic_sw_200",
    ],
}


# Subject -> topics the AI generation pipeline targets (Phase 2 blueprint).
# Drives /api/learning/curriculum and the admin batch-generate UI.
CURRICULUM_BLUEPRINT = {
    "en":         ["vocabulary", "grammar", "numbers", "family", "verbs", "school"],
    "math":       ["arithmetic", "fractions", "geometry", "algebra", "equations",
                   "derivatives", "probability", "logarithm"],
    "science":    ["nature", "human_body", "solar_system", "water_air", "plants_animals"],
    "physics":    ["force", "electricity", "optics", "heat", "energy"],
    "chemistry":  ["elements", "reactions", "acid_base", "compounds"],
    "biology":    ["cell", "human_organs", "genetics", "ecosystem", "plants"],
    "vietnamese": ["vocabulary", "word_class", "punctuation", "idioms", "reading"],
    "literature": ["authors_works", "rhetoric", "genres", "analysis"],
    "history":    ["vietnam_history", "world_history", "dynasties", "events"],
    "geography":  ["vietnam_geography", "world_geography", "climate", "capitals"],
    "civics":     ["rights_duties", "traffic_safety", "ethics", "life_skills"],
    "informatics":["hardware", "software_internet", "online_safety", "office"],
    "programming":["python_basics", "algorithms", "data_structures"],
    "music":      ["instruments", "vietnamese_folk", "genres"],
    "art":        ["color_mixing", "art_styles", "famous_artists"],
    "economics":  ["supply_demand", "personal_finance", "vietnam_economy"],
    "health":     ["food_groups", "healthy_habits", "vitamins"],
    "life_skills":["personal_safety", "communication", "emotions"],
    "logic":      ["patterns", "reasoning", "puzzles"],
    "chinese":    ["greetings", "numbers", "colors", "daily_words"],
    "japanese":   ["greetings", "hiragana", "numbers", "daily_words"],
    "korean":     ["greetings", "hangul", "numbers", "daily_words"],
    "ielts":      ["reading", "listening", "grammar", "vocab"],
    "toeic_lr":   ["part5_grammar", "part6_text", "part7_reading", "listening"],
    "toeic_sw":   ["speaking", "writing"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _subject_meta(subject: str) -> dict:
    meta = SUBJECT_LABELS.get(subject, {"label": subject, "emoji": "📚"})
    return {"subject": subject, "label": meta["label"], "emoji": meta["emoji"]}


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not is_user_admin(str(current_user.get("user_id", ""))):
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


# ── Catalog ──────────────────────────────────────────────────────────────────
@router.get("/api/learning/subjects")
async def list_subjects(current_user: dict = Depends(get_current_user)):
    """Subjects that have at least one published exam paper, with paper counts."""
    _require_family(current_user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT subject, COUNT(*) AS paper_count
               FROM exam_papers WHERE status = 'published'
               GROUP BY subject ORDER BY subject"""
        ).fetchall()
        qrows = conn.execute(
            """SELECT subject, COUNT(*) AS question_count
               FROM question_bank WHERE status = 'published'
               GROUP BY subject"""
        ).fetchall()
    qmap = {r["subject"]: r["question_count"] for r in qrows}
    subjects = []
    for r in rows:
        meta = _subject_meta(r["subject"])
        meta["paper_count"] = r["paper_count"]
        meta["question_count"] = qmap.get(r["subject"], 0)
        subjects.append(meta)
    return {"subjects": subjects}


@router.get("/api/learning/tracks")
async def list_tracks(current_user: dict = Depends(get_current_user)):
    """Track / roadmap catalog with published paper counts per track."""
    _require_family(current_user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT track, COUNT(*) AS paper_count
               FROM exam_papers WHERE status = 'published'
               GROUP BY track"""
        ).fetchall()
    counts = {r["track"]: r["paper_count"] for r in rows}
    tracks = []
    for track_id, meta in TRACK_CATALOG.items():
        tracks.append({
            "track": track_id,
            "label": meta["label"],
            "kind": meta["kind"],
            "paper_count": counts.get(track_id, 0),
            "levels": ROADMAP_LEVELS.get(track_id, []),
        })
    return {"tracks": tracks}


# ── Exams ────────────────────────────────────────────────────────────────────
@router.get("/api/learning/exams")
async def list_exams(
    subject: Optional[str] = Query(default=None, max_length=40),
    track: Optional[str] = Query(default=None, max_length=40),
    level: Optional[str] = Query(default=None, max_length=40),
    skill: Optional[str] = Query(default=None, max_length=40),
    age_group: Optional[str] = Query(default=None, max_length=20),
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    clauses = ["status = 'published'"]
    params: list = []
    for col, val in (("subject", subject), ("track", track),
                     ("level", level), ("skill", skill), ("age_group", age_group)):
        if val:
            clauses.append(f"{col} = ?")
            params.append(val)
    # Cô lập gia đình: đề global (family_id NULL) cho mọi người + đề riêng của family.
    clauses.append("(family_id IS NULL OR family_id = ?)")
    params.append(family_id)
    where = " AND ".join(clauses)
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""SELECT paper_id, title, subject, track, comp_level, skill, level,
                       age_group, duration_minutes, total_questions, pass_percent,
                       school_year, source, family_id
                FROM exam_papers WHERE {where}
                ORDER BY subject, track, level, title""",
            params,
        ).fetchall()
        # Best attempt per paper for this family (for progress badges).
        best = conn.execute(
            """SELECT paper_id, MAX(CASE WHEN max_score > 0
                       THEN score * 100.0 / max_score ELSE 0 END) AS best_pct,
                      COUNT(*) AS attempts
               FROM exam_sessions WHERE family_id = ? AND status = 'completed'
               GROUP BY paper_id""",
            (family_id,),
        ).fetchall()
    best_map = {r["paper_id"]: r for r in best}
    exams = []
    for r in rows:
        d = dict(r)
        b = best_map.get(r["paper_id"])
        d["best_percent"] = round(b["best_pct"], 1) if b else None
        d["attempts"] = b["attempts"] if b else 0
        exams.append(d)
    return {"exams": exams}


@router.get("/api/learning/exams/sessions")
async def list_exam_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT s.session_id, s.paper_id, s.completed_at, s.score, s.max_score,
                      s.correct_count, s.total_questions, s.time_spent_seconds,
                      p.title, p.subject, p.track
               FROM exam_sessions s
               LEFT JOIN exam_papers p ON p.paper_id = s.paper_id
               WHERE s.family_id = ? AND s.status = 'completed'
               ORDER BY s.completed_at DESC LIMIT ?""",
            (family_id, limit),
        ).fetchall()
    sessions = []
    for r in rows:
        d = dict(r)
        d["percent"] = round(r["score"] * 100.0 / r["max_score"], 1) if r["max_score"] else 0.0
        sessions.append(d)
    return {"sessions": sessions}


@router.get("/api/learning/exams/sessions/{session_id}")
async def get_exam_session(session_id: str, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """SELECT s.*, p.title, p.subject, p.track
               FROM exam_sessions s
               LEFT JOIN exam_papers p ON p.paper_id = s.paper_id
               WHERE s.session_id = ? AND s.family_id = ?""",
            (session_id, family_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    d = dict(row)
    d["answers"] = json.loads(d.pop("answers_json", "{}") or "{}")
    d["percent"] = round(row["score"] * 100.0 / row["max_score"], 1) if row["max_score"] else 0.0
    return {"session": d}


@router.get("/api/learning/exams/{paper_id}")
async def get_exam(paper_id: str, current_user: dict = Depends(get_current_user)):
    """Return the paper with its questions — answers/explanations are hidden."""
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        paper = conn.execute(
            "SELECT * FROM exam_papers WHERE paper_id = ? AND status = 'published'",
            (paper_id,),
        ).fetchone()
        if not paper or paper["family_id"] not in (None, family_id):
            raise HTTPException(status_code=404, detail="Exam paper not found")
        items = conn.execute(
            """SELECT q.question_id, q.question, q.question_vi, q.emoji,
                      q.options_json, q.question_type, q.topic, q.difficulty,
                      pq.order_index, pq.points
               FROM exam_paper_questions pq
               JOIN question_bank q ON q.question_id = pq.question_id
               WHERE pq.paper_id = ?
               ORDER BY pq.order_index""",
            (paper_id,),
        ).fetchall()
    return {
        "paper": {
            "paper_id": paper["paper_id"],
            "title": paper["title"],
            "subject": paper["subject"],
            "track": paper["track"],
            "comp_level": paper["comp_level"],
            "skill": paper["skill"],
            "level": paper["level"],
            "age_group": paper["age_group"],
            "duration_minutes": paper["duration_minutes"],
            "total_questions": paper["total_questions"],
            "pass_percent": paper["pass_percent"],
            "school_year": paper["school_year"],
        },
        "questions": [
            {
                "question_id": r["question_id"],
                "order_index": r["order_index"],
                "question": r["question"],
                "question_vi": r["question_vi"],
                "emoji": r["emoji"],
                "question_type": r["question_type"],
                "topic": r["topic"],
                "difficulty": r["difficulty"],
                "points": r["points"],
                "options": json.loads(r["options_json"] or "[]"),
            }
            for r in items
        ],
    }


class SubmitExam(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    time_spent_seconds: int = Field(default=0, ge=0)


class SubmitToeicSW(BaseModel):
    responses: dict[str, str] = Field(default_factory=dict)
    transcripts: dict[str, str] = Field(default_factory=dict)
    time_spent_seconds: int = Field(default=0, ge=0)
    test_mode: bool = False


def _rubric_max_for(item, skill: str) -> int:
    topic = (item["topic"] or "").strip().lower()
    qtype = (item["question_type"] or "").strip().lower()
    if topic in TOEIC_TASK_MAX_SCORES:
        return TOEIC_TASK_MAX_SCORES[topic]
    if qtype == TOEIC_WRITING_TYPE or skill == "writing":
        return TOEIC_TASK_MAX_SCORES["writing"]
    return TOEIC_TASK_MAX_SCORES["speaking"]


def _safe_json_object(raw: str) -> dict:
    text = _FENCE_RE.sub("", raw or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("grader did not return JSON object")
    return data


def _estimate_200(score: float, max_score: float) -> int:
    if max_score <= 0:
        return 0
    return max(0, min(200, int(round((score / max_score) * 200))))


def _offline_toeic_grade(text: str, max_score: int, skill: str) -> dict:
    clean = (text or "").strip()
    if not clean:
        return {
            "score": 0,
            "max_score": max_score,
            "feedback": "Chưa có câu trả lời để chấm. Hãy thử nói hoặc viết một câu ngắn trước nhé.",
            "tips": ["Trả lời đủ ý chính.", "Dùng câu ngắn, rõ ràng."],
        }
    words = len(clean.split())
    if skill == "writing":
        score = min(max_score, max(1, round(words / 18)))
    else:
        score = min(max_score, max(1, round(words / 10)))
    return {
        "score": float(score),
        "max_score": max_score,
        "feedback": "Bài làm đã có nội dung rõ. Đây là chấm điểm offline để luyện tập.",
        "tips": ["Nói/viết đủ ý hơn.", "Kiểm tra phát âm hoặc ngữ pháp ở câu chính."],
    }


def _llm_toeic_grade(prompt: str, answer_text: str, max_score: int, skill: str) -> dict:
    if os.getenv("SKIP_LLM", "").strip().lower() in ("1", "true", "yes"):
        return _offline_toeic_grade(answer_text, max_score, skill)
    if not answer_text.strip():
        return _offline_toeic_grade(answer_text, max_score, skill)
    try:
        from src.ai.ai_engine import stream_chat

        sys_ctx = (
            "Bạn là giám khảo TOEIC Speaking & Writing cho luyện tập. "
            "Chỉ trả về JSON hợp lệ, không markdown. "
            f"Điểm tối đa của task là {max_score}."
        )
        user_prompt = (
            f"Skill: {skill}. Prompt: {prompt}\n"
            f"Learner answer/transcript: {answer_text}\n"
            "Trả về JSON object dạng: "
            '{"score": number, "max_score": number, "feedback": "...", "tips": ["..."]}. '
            "score phải nằm trong 0..max_score."
        )
        raw = "".join(stream_chat([{"role": "user", "content": user_prompt}], system_context=sys_ctx, role="teacher"))
        data = _safe_json_object(raw)
        score = float(data.get("score", 0))
        score = max(0.0, min(float(max_score), score))
        tips = data.get("tips") if isinstance(data.get("tips"), list) else []
        return {
            "score": score,
            "max_score": max_score,
            "feedback": str(data.get("feedback") or "Bi đã chấm xong bài luyện tập."),
            "tips": [str(t)[:200] for t in tips[:3]],
        }
    except Exception as e:
        logger.warning("[toeic_sw] grader fallback: %s", e)
        return _offline_toeic_grade(answer_text, max_score, skill)


def _load_paper_items(conn, paper_id: str):
    paper = conn.execute(
        "SELECT * FROM exam_papers WHERE paper_id = ? AND status = 'published'",
        (paper_id,),
    ).fetchone()
    if not paper:
        raise HTTPException(status_code=404, detail="Exam paper not found")
    items = conn.execute(
        """SELECT q.question_id, q.answer, q.explanation, q.question_type,
                  q.question, q.question_vi, q.topic, pq.points, pq.order_index
           FROM exam_paper_questions pq
           JOIN question_bank q ON q.question_id = pq.question_id
           WHERE pq.paper_id = ? ORDER BY pq.order_index""",
        (paper_id,),
    ).fetchall()
    return paper, items


def _grade_toeic_sw_attempt(paper, items, body: SubmitToeicSW, skill: str) -> dict:
    review = []
    score = 0.0
    max_score = 0.0
    responses = body.responses or {}
    transcripts = body.transcripts or {}
    for it in items:
        qid = it["question_id"]
        qtype = (it["question_type"] or "").strip().lower()
        if qtype not in TOEIC_SW_QUESTION_TYPES:
            continue
        answer_text = (transcripts.get(qid) if skill == "speaking" else responses.get(qid)) or ""
        answer_text = answer_text.strip()
        task_max = _rubric_max_for(it, skill)
        prompt_text = it["question_vi"] or it["question"] or ""
        grade = _llm_toeic_grade(prompt_text, answer_text, task_max, skill)
        q_score = float(grade["score"])
        q_max = float(grade["max_score"])
        score += q_score
        max_score += q_max
        review.append({
            "question_id": qid,
            "order_index": it["order_index"],
            "question_type": qtype,
            "skill": skill,
            "given": answer_text,
            "score": q_score,
            "max_score": q_max,
            "estimated_200": _estimate_200(q_score, q_max),
            "feedback": grade["feedback"],
            "tips": grade.get("tips", []),
            "auto_graded": True,
        })
    percent = round(score * 100.0 / max_score, 1) if max_score > 0 else 0.0
    return {
        "score": score,
        "max_score": max_score,
        "percent": percent,
        "passed": percent >= paper["pass_percent"] if max_score > 0 else False,
        "review": review,
        "estimated_200": _estimate_200(score, max_score),
        "disclaimer": TOEIC_ESTIMATE_DISCLAIMER,
        "answers_payload": {
            "responses": responses,
            "transcripts": transcripts,
            "rubric": {r["question_id"]: r for r in review},
            "estimated_200": _estimate_200(score, max_score),
            "disclaimer": TOEIC_ESTIMATE_DISCLAIMER,
            "grader": {"mode": "offline" if os.getenv("SKIP_LLM", "").strip().lower() in ("1", "true", "yes") else "llm_or_fallback"},
        },
    }


@router.post("/api/learning/exams/{paper_id}/submit")
async def submit_exam(
    paper_id: str,
    body: SubmitExam,
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        paper = conn.execute(
            "SELECT * FROM exam_papers WHERE paper_id = ? AND status = 'published'",
            (paper_id,),
        ).fetchone()
        if not paper or paper["family_id"] not in (None, family_id):
            raise HTTPException(status_code=404, detail="Exam paper not found")
        items = conn.execute(
            """SELECT q.question_id, q.answer, q.explanation, q.question_type,
                      q.question, q.question_vi, pq.points, pq.order_index
               FROM exam_paper_questions pq
               JOIN question_bank q ON q.question_id = pq.question_id
               WHERE pq.paper_id = ? ORDER BY pq.order_index""",
            (paper_id,),
        ).fetchall()

        score = 0.0
        max_score = 0.0
        correct_count = 0
        graded_total = 0
        review = []
        for it in items:
            qid = it["question_id"]
            given = (body.answers.get(qid) or "").strip()
            qtype = it["question_type"]
            expected = (it["answer"] or "").strip()
            if qtype == "essay_key":
                # Cannot auto-grade free text — show model answer, don't score.
                review.append({
                    "question_id": qid, "order_index": it["order_index"],
                    "given": given, "expected": expected,
                    "explanation": it["explanation"], "correct": None,
                    "auto_graded": False,
                })
                continue
            graded_total += 1
            max_score += it["points"]
            is_correct = given.lower() == expected.lower()
            if is_correct:
                score += it["points"]
                correct_count += 1
            review.append({
                "question_id": qid, "order_index": it["order_index"],
                "given": given, "expected": expected,
                "explanation": it["explanation"], "correct": is_correct,
                "auto_graded": True,
            })

        percent = round(score * 100.0 / max_score, 1) if max_score > 0 else 0.0
        passed = percent >= paper["pass_percent"]
        session_id = uuid4().hex
        now = _utc_now()
        conn.execute(
            """INSERT INTO exam_sessions
               (session_id, family_id, paper_id, started_at, completed_at,
                score, max_score, correct_count, total_questions,
                time_spent_seconds, answers_json, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')""",
            (session_id, family_id, paper_id, now, now,
             score, max_score, correct_count, graded_total,
             int(body.time_spent_seconds),
             json.dumps(body.answers, ensure_ascii=False)),
        )
        conn.commit()

    return {
        "ok": True,
        "session_id": session_id,
        "score": score,
        "max_score": max_score,
        "percent": percent,
        "correct_count": correct_count,
        "total_questions": graded_total,
        "passed": passed,
        "pass_percent": paper["pass_percent"],
        "review": review,
    }


@router.post("/api/learning/exams/{paper_id}/submit-toeic-sw")
async def submit_toeic_sw(
    paper_id: str,
    body: SubmitToeicSW,
    current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(current_user)
    with get_db_connection() as conn:
        paper, items = _load_paper_items(conn, paper_id)
        if paper["family_id"] not in (None, family_id):
            raise HTTPException(status_code=404, detail="Exam paper not found")
        if paper["subject"] != TOEIC_SW_SUBJECT:
            raise HTTPException(status_code=422, detail="Paper is not TOEIC S&W")
        skill = (paper["skill"] or "writing").strip().lower()
        if skill not in {"speaking", "writing"}:
            skill = "speaking" if any((it["question_type"] or "") == TOEIC_SPEAKING_TYPE for it in items) else "writing"
        graded = _grade_toeic_sw_attempt(paper, items, body, skill)
        if not graded["review"]:
            raise HTTPException(status_code=422, detail="No TOEIC S&W questions to grade")
        session_id = uuid4().hex
        now = _utc_now()
        conn.execute(
            """INSERT INTO exam_sessions
               (session_id, family_id, paper_id, started_at, completed_at,
                score, max_score, correct_count, total_questions,
                time_spent_seconds, answers_json, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')""",
            (
                session_id,
                family_id,
                paper_id,
                now,
                now,
                graded["score"],
                graded["max_score"],
                0,
                len(graded["review"]),
                int(body.time_spent_seconds),
                json.dumps(graded["answers_payload"], ensure_ascii=False),
            ),
        )
        conn.commit()
    return {
        "ok": True,
        "session_id": session_id,
        "score": graded["score"],
        "max_score": graded["max_score"],
        "percent": graded["percent"],
        "correct_count": 0,
        "total_questions": len(graded["review"]),
        "passed": graded["passed"],
        "pass_percent": paper["pass_percent"],
        "estimated_200": graded["estimated_200"],
        "disclaimer": graded["disclaimer"],
        "review": graded["review"],
    }


@router.post("/api/learning/exams/{paper_id}/submit-speaking")
async def submit_toeic_speaking(
    paper_id: str,
    body: SubmitToeicSW,
    current_user: dict = Depends(get_current_user),
):
    # MVP testable path: callers provide transcripts. Browser multipart upload is
    # intentionally deferred until python-multipart is added to the dependency set.
    if not body.transcripts:
        raise HTTPException(status_code=422, detail="Transcript is required for speaking submission")
    return await submit_toeic_sw(paper_id, body, current_user)


# ── Custom exams (admin = global, parent = riêng gia đình) ────────────────────
class CustomQuestion(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    question_vi: str = Field(default="", max_length=500)
    emoji: str = Field(default="", max_length=8)
    options: list[str] = Field(..., min_length=2, max_length=6)
    answer: str = Field(..., min_length=1, max_length=200)
    explanation: str = Field(default="", max_length=1000)
    difficulty: int = Field(default=2, ge=1, le=5)


class CreateCustomExam(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    subject: str = Field(default="custom", max_length=40)
    track: str = Field(default="practice", max_length=40)
    duration_minutes: int = Field(default=20, ge=1, le=240)
    pass_percent: int = Field(default=60, ge=0, le=100)
    is_global: bool = False  # chỉ admin mới được tạo đề global
    questions: list[CustomQuestion] = Field(..., min_length=1, max_length=100)


@router.post("/api/learning/exams/custom")
async def create_custom_exam(body: CreateCustomExam, current_user: dict = Depends(get_current_user)):
    """Parent: tạo đề riêng (chỉ gia đình mình thấy). Admin: is_global=true → đề chung."""
    family_id = _require_family(current_user)
    is_admin = is_user_admin(str(current_user.get("user_id", "")))
    make_global = bool(body.is_global and is_admin)
    owner_family = None if make_global else family_id

    valid = []
    for q in body.questions:
        opts = [str(o).strip() for o in q.options if str(o).strip()]
        ans = q.answer.strip()
        if len(opts) >= 2 and ans in opts:
            valid.append((q, opts, ans))
    if not valid:
        raise HTTPException(status_code=422, detail="Cần ít nhất 1 câu hợp lệ (đáp án phải nằm trong lựa chọn)")

    now = _utc_now()
    paper_id = f"custom_{'global' if make_global else family_id}_{uuid4().hex[:10]}"
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO exam_papers
               (paper_id, title, subject, track, comp_level, skill, level, age_group,
                duration_minutes, total_questions, pass_percent, school_year, source,
                status, family_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, '', '', '', 'all', ?, ?, ?, '', 'custom', 'published', ?, ?, ?)""",
            (paper_id, body.title, body.subject, body.track, body.duration_minutes,
             len(valid), body.pass_percent, owner_family, now, now),
        )
        for idx, (q, opts, ans) in enumerate(valid):
            qid = f"{paper_id}_q{idx + 1}"
            conn.execute(
                """INSERT INTO question_bank
                   (question_id, subject, topic, age_group, track, skill, level, difficulty,
                    question_type, question, question_vi, emoji, options_json, answer,
                    explanation, school_year, source, is_ai_generated, status, family_id,
                    created_at, updated_at)
                   VALUES (?, ?, '', 'all', ?, '', '', ?, 'mcq', ?, ?, ?, ?, ?, ?, '', 'custom', 0, 'published', ?, ?, ?)""",
                (qid, body.subject, body.track, q.difficulty, q.question, q.question_vi,
                 q.emoji, json.dumps(opts, ensure_ascii=False), ans, q.explanation,
                 owner_family, now, now),
            )
            conn.execute(
                "INSERT INTO exam_paper_questions (paper_id, question_id, order_index, points) VALUES (?, ?, ?, 1)",
                (paper_id, qid, idx),
            )
        conn.commit()
    return {"ok": True, "paper_id": paper_id, "total_questions": len(valid), "is_global": make_global}


@router.delete("/api/learning/exams/{paper_id}")
async def delete_exam(paper_id: str, current_user: dict = Depends(get_current_user)):
    """Admin xóa bất kỳ; parent chỉ xóa đề custom của gia đình mình."""
    family_id = _require_family(current_user)
    is_admin = is_user_admin(str(current_user.get("user_id", "")))
    with get_db_connection() as conn:
        paper = conn.execute(
            "SELECT family_id, source FROM exam_papers WHERE paper_id = ?", (paper_id,)
        ).fetchone()
        if not paper:
            raise HTTPException(status_code=404, detail="Exam paper not found")
        if not is_admin:
            if paper["family_id"] != family_id:
                raise HTTPException(status_code=403, detail="Không có quyền xóa đề này")
            if paper["source"] != "custom":
                raise HTTPException(status_code=403, detail="Chỉ xóa được đề tự tạo")
        qids = [r["question_id"] for r in conn.execute(
            "SELECT question_id FROM exam_paper_questions WHERE paper_id = ?", (paper_id,)
        ).fetchall()]
        conn.execute("DELETE FROM exam_paper_questions WHERE paper_id = ?", (paper_id,))
        for qid in qids:
            conn.execute("DELETE FROM question_bank WHERE question_id = ? AND source = 'custom'", (qid,))
        conn.execute("DELETE FROM exam_sessions WHERE paper_id = ?", (paper_id,))
        conn.execute("DELETE FROM exam_papers WHERE paper_id = ?", (paper_id,))
        conn.commit()
    return {"ok": True, "paper_id": paper_id}


@router.get("/api/learning/admin/papers")
async def admin_list_papers(_admin: dict = Depends(require_admin)):
    """Admin: liệt kê TẤT CẢ đề (mọi family + mọi status) để quản lý."""
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT paper_id, title, subject, track, total_questions, pass_percent,
                      source, status, family_id, created_at
               FROM exam_papers ORDER BY created_at DESC"""
        ).fetchall()
    return {"papers": [dict(r) for r in rows]}


# ── Admin: AI generation + review pipeline ────────────────────────────────────
class GenerateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=40)
    topic: str = Field(default="", max_length=80)
    age_group: str = Field(default="all", max_length=20)
    track: str = Field(default="practice", max_length=40)
    skill: str = Field(default="", max_length=40)
    level: str = Field(default="", max_length=40)
    difficulty: int = Field(default=2, ge=1, le=5)
    count: int = Field(default=5, ge=1, le=20)
    school_year: str = Field(default="2025-2026", max_length=20)


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _stub_questions(req: GenerateRequest) -> list[dict]:
    """Deterministic offline generator (SKIP_LLM / no provider). Keeps the
    pipeline testable without burning LLM quota."""
    out = []
    for i in range(req.count):
        out.append({
            "question": f"[{req.subject}] Câu hỏi mẫu {i + 1} ({req.topic or 'chung'})?",
            "question_vi": f"Câu hỏi luyện tập số {i + 1}.",
            "options": ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"],
            "answer": "Đáp án A",
            "explanation": "Đây là câu hỏi mẫu sinh tự động (chế độ offline).",
        })
    return out


def _llm_generate_questions(req: GenerateRequest) -> list[dict]:
    """Call the LLM fallback chain to produce MCQ JSON. Raises on parse failure."""
    from src.ai.ai_engine import stream_chat

    sys_ctx = (
        "Bạn là chuyên gia biên soạn câu hỏi giáo dục cho học sinh Việt Nam. "
        "Chỉ trả về JSON hợp lệ, không thêm lời dẫn."
    )
    prompt = (
        f"Tạo {req.count} câu hỏi trắc nghiệm môn '{req.subject}'"
        + (f", chủ đề '{req.topic}'" if req.topic else "")
        + f", độ tuổi '{req.age_group}', độ khó {req.difficulty}/5"
        + (f", kỹ năng '{req.skill}'" if req.skill else "")
        + (f", trình độ '{req.level}'" if req.level else "")
        + ". Mỗi câu có đúng 4 lựa chọn, 1 đáp án đúng, kèm giải thích ngắn. "
        "Trả về JSON array, mỗi phần tử dạng: "
        '{"question": "...", "question_vi": "...", "options": ["..","..","..",".."], '
        '"answer": "đáp án đúng (trùng 1 trong options)", "explanation": "..."}. '
        "Chỉ in JSON array, không markdown."
    )
    raw = "".join(stream_chat([{"role": "user", "content": prompt}],
                              system_context=sys_ctx, role="teacher"))
    text = _FENCE_RE.sub("", raw).strip()
    # Extract first JSON array if the model added stray text.
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("LLM did not return a JSON array")
    return data


@router.post("/api/learning/admin/generate")
async def admin_generate_questions(
    req: GenerateRequest,
    admin: dict = Depends(require_admin),
):
    """Generate questions via the LLM (or offline stub) into the review queue."""
    family_id = _require_family(admin)
    skip_llm = os.getenv("SKIP_LLM", "").strip().lower() in ("1", "true", "yes")
    try:
        items = _stub_questions(req) if skip_llm else _llm_generate_questions(req)
    except Exception as e:
        logger.warning("[exam] AI generation failed (%s) — falling back to stub", e)
        items = _stub_questions(req)

    now = _utc_now()
    inserted = []
    with get_db_connection() as conn:
        for it in items:
            options = it.get("options") or []
            answer = (it.get("answer") or "").strip()
            question = (it.get("question") or "").strip()
            if not question or not answer or len(options) < 2:
                continue  # skip malformed
            qid = uuid4().hex
            conn.execute(
                """INSERT INTO question_bank
                   (question_id, subject, topic, age_group, track, skill, level,
                    difficulty, question_type, question, question_vi, emoji,
                    options_json, answer, explanation, school_year, source,
                    is_ai_generated, status, family_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'mcq', ?, ?, '', ?, ?, ?, ?, 'ai', 1, 'review', ?, ?, ?)""",
                (qid, req.subject, req.topic, req.age_group, req.track, req.skill,
                 req.level, req.difficulty, question, it.get("question_vi", ""),
                 json.dumps(options, ensure_ascii=False), answer,
                 it.get("explanation", ""), req.school_year, family_id, now, now),
            )
            inserted.append({"question_id": qid, "question": question,
                             "options": options, "answer": answer})
        conn.commit()

    return {
        "ok": True,
        "generated": len(inserted),
        "status": "review",
        "offline": skip_llm,
        "questions": inserted,
    }


class GenerateBatchRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=40)
    topics: list[str] = Field(default_factory=list)
    age_group: str = Field(default="all", max_length=20)
    track: str = Field(default="practice", max_length=40)
    skill: str = Field(default="", max_length=40)
    level: str = Field(default="", max_length=40)
    difficulty: int = Field(default=2, ge=1, le=5)
    per_topic: int = Field(default=5, ge=1, le=20)
    school_year: str = Field(default="2025-2026", max_length=20)


@router.post("/api/learning/admin/generate-batch")
async def admin_generate_batch(
    body: GenerateBatchRequest,
    admin: dict = Depends(require_admin),
):
    """Generate questions for many topics in one call. Each topic produces
    `per_topic` questions into the review queue. Honors SKIP_LLM. Bounded so a
    single batch cannot exceed 200 questions."""
    family_id = _require_family(admin)
    topics = [t.strip() for t in (body.topics or [""]) if t is not None] or [""]
    if len(topics) * body.per_topic > 200:
        raise HTTPException(status_code=422, detail="Batch too large (max 200 questions)")

    skip_llm = os.getenv("SKIP_LLM", "").strip().lower() in ("1", "true", "yes")
    now = _utc_now()
    per_topic_results = []
    total_inserted = 0
    with get_db_connection() as conn:
        for topic in topics:
            req = GenerateRequest(
                subject=body.subject, topic=topic, age_group=body.age_group,
                track=body.track, skill=body.skill, level=body.level,
                difficulty=body.difficulty, count=body.per_topic,
                school_year=body.school_year,
            )
            try:
                items = _stub_questions(req) if skip_llm else _llm_generate_questions(req)
            except Exception as e:
                logger.warning("[exam] batch topic '%s' failed (%s) — stub", topic, e)
                items = _stub_questions(req)
            inserted = 0
            for it in items:
                options = it.get("options") or []
                answer = (it.get("answer") or "").strip()
                question = (it.get("question") or "").strip()
                if not question or not answer or len(options) < 2:
                    continue
                if answer not in [str(o).strip() for o in options]:
                    continue
                conn.execute(
                    """INSERT INTO question_bank
                       (question_id, subject, topic, age_group, track, skill, level,
                        difficulty, question_type, question, question_vi, emoji,
                        options_json, answer, explanation, school_year, source,
                        is_ai_generated, status, family_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'mcq', ?, ?, '', ?, ?, ?, ?, 'ai', 1, 'review', ?, ?, ?)""",
                    (uuid4().hex, body.subject, topic, body.age_group, body.track,
                     body.skill, body.level, body.difficulty, question,
                     it.get("question_vi", ""),
                     json.dumps(options, ensure_ascii=False), answer,
                     it.get("explanation", ""), body.school_year, family_id, now, now),
                )
                inserted += 1
            total_inserted += inserted
            per_topic_results.append({"topic": topic, "generated": inserted})
        conn.commit()

    return {
        "ok": True,
        "total_generated": total_inserted,
        "status": "review",
        "offline": skip_llm,
        "topics": per_topic_results,
    }


@router.get("/api/learning/curriculum")
async def get_curriculum(current_user: dict = Depends(get_current_user)):
    """Curriculum blueprint: the subject → topics map the generation pipeline
    targets. Drives the admin 'generate content' UI and batch jobs."""
    _require_family(current_user)
    return {"curriculum": CURRICULUM_BLUEPRINT}


@router.get("/api/learning/admin/review")
async def admin_review_queue(
    status: str = Query(default="review", max_length=20),
    subject: Optional[str] = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
    admin: dict = Depends(require_admin),
):
    clauses = ["status = ?"]
    params: list = [status]
    if subject:
        clauses.append("subject = ?")
        params.append(subject)
    where = " AND ".join(clauses)
    params.append(limit)
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""SELECT question_id, subject, topic, age_group, track, skill, level,
                       difficulty, question, question_vi, options_json, answer,
                       explanation, is_ai_generated, status, created_at
                FROM question_bank WHERE {where}
                ORDER BY created_at DESC LIMIT ?""",
            params,
        ).fetchall()
    questions = []
    for r in rows:
        d = dict(r)
        d["options"] = json.loads(d.pop("options_json", "[]") or "[]")
        questions.append(d)
    return {"questions": questions, "count": len(questions)}


class ReviewAction(BaseModel):
    action: str = Field(..., pattern=r"^(publish|reject)$")
    question: Optional[str] = Field(default=None, max_length=2000)
    answer: Optional[str] = Field(default=None, max_length=500)
    explanation: Optional[str] = Field(default=None, max_length=2000)
    options: Optional[list[str]] = None


@router.post("/api/learning/admin/review/{question_id}")
async def admin_review_question(
    question_id: str,
    body: ReviewAction,
    admin: dict = Depends(require_admin),
):
    now = _utc_now()
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT question_id FROM question_bank WHERE question_id = ?",
            (question_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Question not found")
        if body.action == "reject":
            conn.execute(
                "UPDATE question_bank SET status = 'archived', updated_at = ? WHERE question_id = ?",
                (now, question_id),
            )
            conn.commit()
            return {"ok": True, "status": "archived"}
        # publish — apply optional edits then mark published
        sets = ["status = 'published'", "updated_at = ?"]
        params: list = [now]
        if body.question is not None:
            sets.append("question = ?"); params.append(body.question)
        if body.answer is not None:
            sets.append("answer = ?"); params.append(body.answer)
        if body.explanation is not None:
            sets.append("explanation = ?"); params.append(body.explanation)
        if body.options is not None:
            sets.append("options_json = ?")
            params.append(json.dumps(body.options, ensure_ascii=False))
        params.append(question_id)
        conn.execute(
            f"UPDATE question_bank SET {', '.join(sets)} WHERE question_id = ?",
            params,
        )
        conn.commit()
    return {"ok": True, "status": "published"}


class AssembleExam(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    subject: str = Field(..., min_length=1, max_length=40)
    track: str = Field(default="practice", max_length=40)
    comp_level: str = Field(default="", max_length=40)
    skill: str = Field(default="", max_length=40)
    level: str = Field(default="", max_length=40)
    age_group: str = Field(default="all", max_length=20)
    duration_minutes: int = Field(default=30, ge=1, le=300)
    pass_percent: int = Field(default=60, ge=0, le=100)
    school_year: str = Field(default="2025-2026", max_length=20)
    question_ids: Optional[list[str]] = None
    auto_count: int = Field(default=0, ge=0, le=200)


@router.post("/api/learning/admin/exams")
async def admin_assemble_exam(
    body: AssembleExam,
    admin: dict = Depends(require_admin),
):
    """Create an exam paper from explicit question_ids, or auto-select published
    questions matching the subject/track/level/difficulty filters."""
    family_id = _require_family(admin)
    now = _utc_now()
    with get_db_connection() as conn:
        if body.question_ids:
            qids = body.question_ids
        elif body.auto_count > 0:
            clauses = ["status = 'published'", "subject = ?"]
            params: list = [body.subject]
            if body.track:
                clauses.append("track = ?"); params.append(body.track)
            if body.level:
                clauses.append("level = ?"); params.append(body.level)
            if body.skill:
                clauses.append("skill = ?"); params.append(body.skill)
            params.append(body.auto_count)
            rows = conn.execute(
                f"""SELECT question_id FROM question_bank
                    WHERE {' AND '.join(clauses)}
                    ORDER BY difficulty, question_id LIMIT ?""",
                params,
            ).fetchall()
            qids = [r["question_id"] for r in rows]
        else:
            raise HTTPException(status_code=422, detail="Provide question_ids or auto_count>0")

        if not qids:
            raise HTTPException(status_code=422, detail="No matching questions to assemble")

        paper_id = f"exam_{uuid4().hex[:12]}"
        conn.execute(
            """INSERT INTO exam_papers
               (paper_id, title, subject, track, comp_level, skill, level,
                age_group, duration_minutes, total_questions, pass_percent,
                school_year, source, status, family_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'admin', 'published', ?, ?, ?)""",
            (paper_id, body.title, body.subject, body.track, body.comp_level,
             body.skill, body.level, body.age_group, body.duration_minutes,
             len(qids), body.pass_percent, body.school_year, family_id, now, now),
        )
        for idx, qid in enumerate(qids):
            conn.execute(
                """INSERT OR IGNORE INTO exam_paper_questions
                   (paper_id, question_id, order_index, points) VALUES (?, ?, ?, 1)""",
                (paper_id, qid, idx),
            )
        conn.commit()
    return {"ok": True, "paper_id": paper_id, "total_questions": len(qids)}
