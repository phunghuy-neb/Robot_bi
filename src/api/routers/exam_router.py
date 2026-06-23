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
    where = " AND ".join(clauses)
    with get_db_connection() as conn:
        rows = conn.execute(
            f"""SELECT paper_id, title, subject, track, comp_level, skill, level,
                       age_group, duration_minutes, total_questions, pass_percent,
                       school_year, source
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
    _require_family(current_user)
    with get_db_connection() as conn:
        paper = conn.execute(
            "SELECT * FROM exam_papers WHERE paper_id = ? AND status = 'published'",
            (paper_id,),
        ).fetchone()
        if not paper:
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
        if not paper:
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
