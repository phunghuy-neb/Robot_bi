# Feature Specification: TOEIC Speaking & Writing
**Feature dir**: `.specify/specs/004-toeic-sw/`   **Status**: Draft (Clarifications resolved 2026-06-24)   **Date**: 2026-06-24

## Summary
Add non-MCQ TOEIC Speaking & Writing practice and scoring to the existing Learning Hub exam system. Speaking uses existing microphone/STT infrastructure to capture an answer, transcribe it, and grade by rubric; Writing accepts typed text and grades by rubric using the existing LLM fallback chain without changing provider order.

## User Scenarios
- As a learner, I want to answer TOEIC Speaking prompts by voice and receive a rubric-based score so that I can practice speaking fluency and content.
- As a learner, I want to type TOEIC Writing responses and receive structured feedback so that I know what to improve.
- As a parent, I want TOEIC S&W attempts to appear in the same exam history as other Learning Hub work so that progress stays visible.
- As an admin/content author, I want TOEIC S&W prompts to use the existing `toeic_sw` track and levels so that the roadmap remains consistent.

## User Stories (prioritized)
MVP = US1 (read-aloud Speaking) + US2 (email Writing): the two cover both skills end-to-end. Remaining task types (respond-to-questions, describe-picture, express-opinion, opinion essay) follow in the rollout order below.

- US1 (P1, MVP): Read-aloud Speaking — learner records audio in the browser; it is uploaded temporarily, transcribed server-side (faster-whisper), and graded by rubric. Independent test: inject a transcript directly (test-only path, no real microphone) to a read-aloud paper and receive per-task rubric score, estimated 0-200 conversion, feedback, and a persisted `exam_sessions` row.
- US2 (P1, MVP): Email Writing — learner types an email response and it is graded by rubric. Independent test: submit a text response to an email-writing paper with mocked LLM grader and receive rubric score, estimated 0-200 conversion, feedback, and persisted session.
- US3 (P2): Remaining task types in rollout order — respond-to-questions (Speaking), describe-picture (Speaking), express-opinion (Speaking), opinion essay (Writing). Independent test: each task type grades through the same submit + rubric pipeline.
- US4 (P2): TOEIC S&W papers are discoverable under existing `/api/learning/tracks` and `/api/learning/exams` filters. Independent test: `toeic_sw` track exposes levels from `ROADMAP_LEVELS["toeic_sw"]` and papers with `skill=speaking|writing` are returned.
- US5 (P2): Admin can generate/review TOEIC S&W prompts with full task metadata (prompt, model answer, rubric anchor, prep/response time, difficulty); generated items enter a review queue and require admin approval before publish. Independent test: admin-generated `question_type` values for speaking/writing enter review queue with metadata and can be published only after approval.
- US6 (P3): Age-gating and child mode — feature is for teens 13+ and adults; under-18 requires a parent to enable it; children 5-12 get a simple English-practice mode WITHOUT TOEIC 0-200 scores shown. Independent test: a 5-12 profile cannot see TOEIC 0-200 output; an under-18 profile is blocked until a parent enables the feature.
- US7 (P3): Parent App can render the non-MCQ TOEIC S&W flow (record/upload audio for Speaking, text box for Writing, rubric + estimated-score result). Independent test: Vite build succeeds and API service functions can submit audio/text payloads.

## Functional Requirements
- FR-001: The feature MUST reuse existing `subject="toeic_sw"`, `track="toeic_sw"`, and levels `toeic_sw_100`, `toeic_sw_120`, `toeic_sw_140`, `toeic_sw_160`, `toeic_sw_180`, `toeic_sw_200` from `exam_router.py`.
- FR-002: The existing MCQ endpoint `POST /api/learning/exams/{paper_id}/submit` MUST remain backward compatible for MCQ papers.
- FR-003: Non-MCQ questions MUST use existing `question_bank.question_type` values or narrowly add documented values such as `toeic_speaking` and `toeic_writing` without breaking `mcq` and `essay_key`.
- FR-004: Writing submission MUST accept typed text per question and return per-question rubric score, max score, feedback, and improvement tips.
- FR-005: Speaking submission MUST accept a temporary browser audio upload that is transcribed server-side. It MUST also support a transcript-injection path that is TEST-ONLY (no real microphone). Robot-STT capture is explicitly deferred (robot audio transport not ready) and out of scope for this feature.
- FR-006: Server-side Speaking STT MUST reuse the existing `faster-whisper` stack and MUST NOT regress microphone fallback/silent mode or native-rate resampling behavior.
- FR-015: Raw uploaded audio MUST NOT be stored by default — it is processed for STT, then deleted immediately after grading; on error it MAY be retained at most 1 hour then purged. A parent MAY opt in (per-family flag) to retain audio up to 7 days for replay, and MUST be able to delete it at any time. Audio paths/retention policy MUST be family-scoped.
- FR-016: Scoring MUST be two-layer: (a) a per-task TOEIC-compatible rubric scored 0-3 / 0-4 / 0-5 depending on task type; (b) a separate Speaking-and-Writing conversion to an ESTIMATED 0-200 score. Percent is display-only (progress tracking). Any 0-200 output MUST be labelled "điểm Robot Bi ước tính, không phải điểm ETS chính thức".
- FR-017: Audience gating — the TOEIC S&W feature targets teens 13+ and adults. For any under-18 profile it MUST be disabled until a parent explicitly enables it. Children 5-12 MUST only receive a simple English-practice mode and MUST NOT be shown TOEIC 0-200 scores.
- FR-018: Admin-generated TOEIC S&W items MUST include prompt, model answer, rubric anchor, preparation/response time, difficulty, and task metadata; AI-generated items MUST enter the review queue (status='review') and require admin approval before publish.
- FR-007: Grading MUST call existing `stream_chat(...)` from `src.ai.ai_engine` and MUST NOT reorder, remove, or replace LLM providers.
- FR-008: Grading prompts MUST request strict JSON and implementation MUST validate/normalize malformed LLM output.
- FR-009: `exam_sessions.answers_json` MUST persist learner responses, transcript, rubric feedback, and LLM grader metadata without leaking API keys.
- FR-010: `exam_sessions.family_id` MUST be populated from authenticated current user via `_require_family()`.
- FR-011: If LLM is unavailable or `SKIP_LLM=true`, grading MUST have deterministic offline fallback for tests and local demo.
- FR-012: Scoring MUST be bounded to the paper/question max points and percent computation MUST work when questions are non-MCQ.
- FR-013: Existing route ordering MUST preserve `/api/learning/exams/sessions` before `/api/learning/exams/{paper_id}`.
- FR-014: Child-safety behavior MUST remain unchanged; SafetyFilter remains post-LLM/pre-TTS for robot speech and generated feedback must avoid unsafe content.

## Key Entities / Data
- Existing `question_bank`: reuse `subject`, `track`, `skill`, `level`, `question_type`, `question`, `question_vi`, `answer`, `explanation` fields for TOEIC S&W prompts and model/rubric notes.
- Existing `exam_papers`: TOEIC S&W paper with `subject="toeic_sw"`, `track="toeic_sw"`, `skill="speaking"` or `"writing"`, `level` from `ROADMAP_LEVELS["toeic_sw"]`.
- Existing `exam_paper_questions`: ordered prompts and point values.
- Existing `exam_sessions`: persist attempt-level score, max score, counts, time, status, and JSON payload containing non-MCQ details.
- New request DTOs in `exam_router.py`: `SubmitToeicSW` (writing/transcript path) plus a multipart audio-upload endpoint for Speaking; payload carries `responses`, optional `transcripts` (test-only), and an uploaded audio file for Speaking.
- Audio handling: temporary file processed then deleted post-grading (max 1h on error); optional per-family opt-in retention up to 7 days with replay + delete. Not stored by default.

## Success Criteria
- Writing grade endpoint returns a rubric report in under 5 seconds with mocked LLM and under 20 seconds with real LLM under normal network conditions.
- Speaking grade endpoint can be tested fully offline by supplying a transcript or mocked STT output.
- `GET /api/learning/exams?subject=toeic_sw&track=toeic_sw&skill=writing` lists published writing papers.
- Completed TOEIC S&W attempts appear in `GET /api/learning/exams/sessions` and detail endpoint with family isolation.
- Existing MCQ tests continue to pass.

## Edge Cases & Safety
- Empty writing response: return score 0 with supportive feedback, do not call LLM unnecessarily.
- Empty/failed STT transcript: return a recoverable validation error or score 0 per clarified UX.
- LLM returns malformed JSON: fall back to deterministic parser/default feedback and do not crash.
- Audio upload too large or unsupported type: reject with 422/413 before STT.
- User tries to submit to a paper from another family or unpublished paper: return 404/403 according to existing patterns.
- Existing faster-whisper GPU/CPU fallback, microphone silent mode, and resampling must not be changed.
- TOEIC is for older learners: under-18 requires parent enablement; children 5-12 get simple English practice only with no 0-200 score (see FR-017).

## Out of Scope
- Changing LLM provider order or adding a new grading provider.
- Full TOEIC official score certification or ETS-equivalent scoring claims.
- Production ESP32-S3 network audio transport.
- Storing raw audio long term unless clarified.
- Large frontend redesign beyond minimal non-MCQ flow support.
- Modifying `resources/learning/*.json` exam-pack workstream.

## Resolved Decisions (2026-06-24)
- **Speaking input**: browser records → uploads audio temporarily → server-side faster-whisper STT. Writing = typed text. Transcript-injection path is TEST-ONLY. Robot STT deferred. (FR-005/006)
- **Raw audio**: not stored by default; processed then deleted after grading (max 1h on error). Parent opt-in retention up to 7 days with replay + delete. (FR-015)
- **Scoring**: two layers — per-task rubric 0-3/0-4/0-5 + estimated 0-200 conversion (Speaking and Writing separately); percent display-only; must label "điểm Robot Bi ước tính, không phải điểm ETS chính thức". (FR-016)
- **Rollout order**: 1) read-aloud, 2) email, 3) respond-to-questions, 4) describe-picture, 5) express-opinion, 6) essay. MVP = read-aloud + email. (US1-US3)
- **Audience**: teens 13+ and adults; under-18 needs parent enablement; 5-12 get simple English practice without 0-200 scores. (FR-017)
- **Admin generation**: must include prompt, model answer, rubric anchor, prep/response time, difficulty, task metadata; AI items go to review queue and need admin approval. (FR-018)
