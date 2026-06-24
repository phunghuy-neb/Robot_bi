# Implementation Plan: TOEIC Speaking & Writing
> Clarifications resolved 2026-06-24 (see spec.md "Resolved Decisions").

## Technical Context
- Backend: FastAPI routers in `src/api/routers/`, SQLite via `src/infrastructure/database/db.py`.
- Existing exam system: `question_bank`, `exam_papers`, `exam_paper_questions`, `exam_sessions` in `runtime/robot_bi.db`.
- Existing TOEIC S&W catalog: `SUBJECT_LABELS["toeic_sw"]`, `TRACK_CATALOG["toeic_sw"]`, `ROADMAP_LEVELS["toeic_sw"]`, and `CURRICULUM_BLUEPRINT["toeic_sw"]` in `src/api/routers/exam_router.py`.
- Existing STT: `src/audio/input/ear_stt.py` uses faster-whisper with protected GPU/CPU fallback, native-rate mic capture, and resampling to 16 kHz.
- Existing LLM grader path should use `stream_chat(...)` from `src.ai.ai_engine` without modifying the provider chain.
- Frontend: React/Vite Parent App Learning Hub currently assumes exam questions can be rendered with options for MCQ; non-MCQ UI needs minimal extension later.

## Constitution / Protected-Fixes Check
- Do not modify LLM fallback order or model stack.
- Do not regress faster-whisper GPU/CPU auto-detect, `WHISPER_CPU_MODEL`, mic fallback, native-rate capture, or resampling.
- Do not change SQLite DB path `runtime/robot_bi.db`.
- Preserve family isolation for exam sessions via `_require_family()`.
- Preserve route order so `/api/learning/exams/sessions` is not shadowed by `/api/learning/exams/{paper_id}`.
- Do not touch `resources/learning/*.json` in this workstream.
- Do not bypass child safety for robot-spoken feedback.

## Architecture & Affected Files
- MODIFY `src/api/routers/exam_router.py`: add non-MCQ question support, grading DTOs, two-layer scorer (rubric + estimated 0-200), grader helpers, age-gating checks, and submit route(s). Audio-upload Speaking endpoint (multipart) + transcript-injection (test-only) path.
- MODIFY `src/infrastructure/database/db.py`: add a per-family audio-retention opt-in flag (small settings row/column) for FR-015; otherwise prefer storing non-MCQ details in `exam_sessions.answers_json` (no per-question schema change).
- NEW server-side STT helper that calls the existing `faster-whisper` model on an uploaded temp file (reuse the loaded model from the STT stack; do NOT modify `src/audio/input/ear_stt.py` beyond a narrow reusable transcribe-file helper if needed).
- Temp audio handling: write upload to a temp path, transcribe, then delete; on error keep ≤1h then purge; honor parent 7-day opt-in retention with replay + delete endpoints.
- MODIFY `frontend/parent_app/src/services/api.js`: add submit helpers (audio multipart for Speaking, text for Writing) after backend contract is stable.
- MODIFY `frontend/parent_app/src/pages/LearningHubPage.jsx`: add record/upload UI for Speaking, text box for Writing, rubric + estimated-score result; hide 0-200 for 5-12 child mode.
- NEW `tests/test_toeic_sw.py`: offline tests using the transcript-injection path and mocked `stream_chat` grader (no real microphone, no LLM).
- Do not modify `src/audio/input/ear_stt.py` beyond an optional narrow transcribe-from-file helper; prefer dependency injection/mocking for tests.

## Data / Schema changes
- Preferred: no schema change. Store non-MCQ response details inside `exam_sessions.answers_json`:
```json
{
  "responses": {"question_id": "learner text"},
  "transcripts": {"question_id": "recognized speech"},
  "rubric": {"question_id": {"score": 3, "max_score": 5, "feedback": "..."}},
  "grader": {"mode": "llm"}
}
```
- Persist two-layer scoring in `answers_json`: per-task `rubric` (with its 0-3/0-4/0-5 max) plus `estimated_200` for Speaking and Writing, and a `disclaimer` field ("điểm Robot Bi ước tính, không phải điểm ETS chính thức").
- If future analytics require per-question attempts, add a new family-scoped `exam_session_items` table in a separate migration task.
- Existing `question_bank.question_type` can hold `toeic_speaking` and `toeic_writing` values without migration. Admin-generated items carry model answer + rubric anchor + prep/response time + difficulty in existing fields/metadata and start at status='review'.
- Add a per-family audio-retention opt-in flag (default off); store optional retained audio under a family-scoped temp area with a ≤7-day expiry, deletable on demand.

## API / Contracts
- Option A, extend existing endpoint: `POST /api/learning/exams/{paper_id}/submit` accepts both `answers` and `responses/transcripts` depending on question type.
- Option B, explicit endpoint: `POST /api/learning/exams/{paper_id}/submit-toeic-sw` for non-MCQ only.
- Suggested request shape:
```json
{
  "responses": {"q1": "typed writing answer"},
  "transcripts": {"q2": "spoken answer transcript"},
  "time_spent_seconds": 300
}
```
- Suggested response shape:
```json
{
  "ok": true,
  "session_id": "...",
  "score": 12,
  "max_score": 20,
  "percent": 60.0,
  "passed": true,
  "review": [
    {"question_id": "q1", "score": 4, "max_score": 5, "feedback": "...", "rubric": {}}
  ]
}
```
- Speaking audio-upload endpoint (decided): `POST /api/learning/exams/{paper_id}/submit-speaking` as `multipart/form-data` with an audio file per question + `time_spent_seconds`; server transcribes then grades. Response shape matches the submit response above plus `estimated_200` and `disclaimer`. A test-only variant accepts `transcripts` directly.
- Audio replay/management endpoints (only meaningful when parent opt-in is on): `GET /api/learning/audio/{session_id}` (replay), `DELETE /api/learning/audio/{session_id}` (delete now), `PATCH /api/learning/settings/audio-retention` (per-family opt-in toggle).

## Phases
- Phase 0 research: (resolved) task types, scoring scale, audio path confirmed — see Resolved Decisions.
- Phase 1 backend design: Define question types, request/response DTOs, two-layer rubric+0-200 JSON, age-gating, and persistence in `answers_json`.
- Phase 2 backend implementation (MVP): read-aloud Speaking (upload+STT) and email Writing — tests, grader helper, submission path, session persistence, temp-audio delete.
- Phase 3 content/admin: prompt generation/review with full metadata (model answer, rubric anchor, prep/response time, difficulty) gated by admin approval.
- Phase 4 remaining task types: respond-to-questions, describe-picture, express-opinion, essay.
- Phase 5 frontend: record/upload + text UI, rubric + estimated-score result, child-mode hiding of 0-200.
- Phase 6 verification: Run TOEIC S&W tests, existing exam tests, Vite build, and full regression where dependencies are available.

## Risks & Open Questions
- LLM scoring may be inconsistent without strict rubric and JSON validation.
- Browser audio capture has permission/format risks; the transcript-injection path keeps backend tests deterministic and microphone-free.
- Age-gating must integrate with the existing user/profile model; how a "child profile" vs "teen/adult" is distinguished is an implementation detail to confirm against the auth/profile schema.
- Existing exam UI may assume `options` exist for every question — non-MCQ rendering must branch.
- Estimated 0-200 is heuristic; the disclaimer is mandatory wherever it is shown.
