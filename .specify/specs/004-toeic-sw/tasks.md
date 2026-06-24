# Tasks: TOEIC Speaking & Writing
> Clarifications resolved 2026-06-24. MVP = read-aloud Speaking + email Writing.

## Phase 1: Setup
- [ ] T001 Read existing TOEIC S&W catalog and exam submission flow — file: `src/api/routers/exam_router.py`
- [ ] T002 Read STT protected behavior before designing server-side speaking path — file: `src/audio/input/ear_stt.py`
- [ ] T003 [P] Add backend test skeleton for TOEIC S&W non-MCQ submit — file: `tests/test_toeic_sw.py`
- [ ] T004 [P] Add fixture builders for TOEIC S&W paper/question/session rows — file: `tests/test_toeic_sw.py`

## Phase 2: Foundational (blocking)
- [ ] T005 Define constants for non-MCQ question types (`toeic_speaking`, `toeic_writing`) and per-task rubric scales (0-3/0-4/0-5) — file: `src/api/routers/exam_router.py`
- [ ] T006 Add test that existing MCQ submit behavior remains unchanged — file: `tests/test_toeic_sw.py`
- [ ] T007 Add request models: `SubmitToeicSW` (text/transcript) + multipart speaking-upload model — file: `src/api/routers/exam_router.py`
- [ ] T008 Add JSON parsing/validation helper for LLM grading output — file: `src/api/routers/exam_router.py`
- [ ] T009 Add deterministic offline grader fallback used under `SKIP_LLM=true` — file: `src/api/routers/exam_router.py`
- [ ] T010 Add two-layer scorer: per-task rubric + estimated 0-200 (Speaking & Writing) + mandatory disclaimer string — file: `src/api/routers/exam_router.py`
- [ ] T011 Add tests for malformed LLM JSON fallback and 0-200 conversion bounds — file: `tests/test_toeic_sw.py`

## Phase 3: US2 (P1, MVP) — Email Writing grading; Independent test: typed email returns rubric + estimated-200 + persisted session
- [ ] T012 Add writing submission test with mocked `stream_chat` grader — file: `tests/test_toeic_sw.py`
- [ ] T013 Implement writing rubric prompt builder (no LLM provider change) — file: `src/api/routers/exam_router.py`
- [ ] T014 Implement writing grading helper returning bounded rubric + estimated-200 + feedback — file: `src/api/routers/exam_router.py`
- [ ] T015 Persist writing scoring details (rubric, estimated_200, disclaimer) into `exam_sessions.answers_json` — file: `src/api/routers/exam_router.py`
- [ ] T016 Add test for empty writing response scoring safely (no LLM call) — file: `tests/test_toeic_sw.py`

## Phase 4: US1 (P1, MVP) — Read-aloud Speaking via upload+STT; Independent test: transcript-injection path needs no real microphone
- [ ] T017 Add speaking transcript-injection (test-only) submission test — file: `tests/test_toeic_sw.py`
- [ ] T018 Add narrow `transcribe_file(path)` helper reusing the faster-whisper model (no regression to mic/silent-mode/resample) — file: `src/audio/input/ear_stt.py`
- [ ] T019 Implement `POST /api/learning/exams/{paper_id}/submit-speaking` (multipart upload) + test-only transcript path — file: `src/api/routers/exam_router.py`
- [ ] T020 Implement speaking grading helper (transcript → rubric + estimated-200) — file: `src/api/routers/exam_router.py`
- [ ] T021 Implement temp-audio lifecycle: process then delete; keep ≤1h on error then purge — file: `src/api/routers/exam_router.py`
- [ ] T022 Add tests for missing/empty transcript and upload validation (size/type → 413/422) — file: `tests/test_toeic_sw.py`

## Phase 5: Audio retention opt-in (parent privacy, FR-015)
- [ ] T023 Add per-family audio-retention opt-in flag (default off) — file: `src/infrastructure/database/db.py`
- [ ] T024 Implement `PATCH /api/learning/settings/audio-retention`, `GET /api/learning/audio/{session_id}` (replay), `DELETE /api/learning/audio/{session_id}` — file: `src/api/routers/exam_router.py`
- [ ] T025 Add tests: opt-in retains ≤7 days, replay works, delete purges, default deletes immediately — file: `tests/test_toeic_sw.py`

## Phase 6: US6 (P3) — Age-gating & child mode (FR-017)
- [ ] T026 Add age-gating: under-18 requires parent enablement; 5-12 → simple English mode, no 0-200 — file: `src/api/routers/exam_router.py`
- [ ] T027 Add tests: 5-12 profile gets no 0-200; under-18 blocked until parent enables — file: `tests/test_toeic_sw.py`

## Phase 7: US4 (P2) — Discoverability in existing exam catalog
- [ ] T028 Add tests for `ROADMAP_LEVELS["toeic_sw"]`, track metadata, and `skill=speaking|writing` filtering — file: `tests/test_toeic_sw.py`
- [ ] T029 Fix list/detail response only if non-MCQ metadata is missing — file: `src/api/routers/exam_router.py`

## Phase 8: US5 (P2) — Admin generation/review with full task metadata (FR-018)
- [ ] T030 Add admin generate tests for `subject=toeic_sw`, `skill=speaking|writing` with metadata — file: `tests/test_toeic_sw.py`
- [ ] T031 Extend generation to emit prompt + model answer + rubric anchor + prep/response time + difficulty + task metadata — file: `src/api/routers/exam_router.py`
- [ ] T032 Require admin approval (status='review' → 'published') for non-MCQ items without forcing 4 options — file: `src/api/routers/exam_router.py`
- [ ] T033 Add admin assemble test with non-MCQ question IDs — file: `tests/test_toeic_sw.py`

## Phase 9: US3 (P2) — Remaining task types (rollout order)
- [ ] T034 Add respond-to-questions (Speaking) prompt+rubric support — file: `src/api/routers/exam_router.py`
- [ ] T035 Add describe-picture (Speaking) support — file: `src/api/routers/exam_router.py`
- [ ] T036 Add express-opinion (Speaking) support — file: `src/api/routers/exam_router.py`
- [ ] T037 Add opinion-essay (Writing) support — file: `src/api/routers/exam_router.py`

## Phase 10: US7 (P3) — Parent App non-MCQ flow
- [ ] T038 [P] Add API service helpers (audio multipart for Speaking, text for Writing) — file: `frontend/parent_app/src/services/api.js`
- [ ] T039 Add text answer UI for writing questions — file: `frontend/parent_app/src/pages/LearningHubPage.jsx`
- [ ] T040 Add browser record/upload UI for speaking questions — file: `frontend/parent_app/src/pages/LearningHubPage.jsx`
- [ ] T041 Add result rendering for rubric + estimated-200 + disclaimer; hide 0-200 in 5-12 child mode — file: `frontend/parent_app/src/pages/LearningHubPage.jsx`

## Phase cuối: Polish & cross-cutting (tests, safety, docs)
- [ ] T042 Verify family isolation in all new session/audio queries — file: `src/api/routers/exam_router.py`
- [ ] T043 Verify route ordering keeps sessions routes before `{paper_id}` — file: `src/api/routers/exam_router.py`
- [ ] T044 Verify SafetyFilter coverage for generated/spoken feedback — file: `src/api/routers/exam_router.py`
- [ ] T045 Run TOEIC S&W tests — file: `tests/test_toeic_sw.py`
- [ ] T046 Run full regression suite where dependencies are available — file: `tests/run_tests.py`
- [ ] T047 Run Parent App build if frontend tasks are implemented — file: `frontend/parent_app/package.json`
- [ ] T048 Update `SYSTEM_MAP.md` after implementation changes current APIs/UI — file: `SYSTEM_MAP.md`

## Dependencies
- Foundational T005-T011 block all user stories.
- MVP (US2 Writing T012-T016, US1 Speaking T017-T022) depends on foundational; Writing and Speaking can proceed in parallel after T007.
- Audio retention (T023-T025) depends on the speaking upload path (T019-T021).
- Age-gating (T026-T027) depends on foundational + scoring (T010).
- US4 discoverability (T028-T029) depends on fixtures T004 + constants T005.
- US5 admin (T030-T033) depends on question-type constants T005.
- US3 remaining task types (T034-T037) depend on MVP grading pipeline.
- US7 frontend (T038-T041) depends on stable backend contract from MVP.

## Parallel execution examples
- T003 and T004 can run in parallel.
- T012 (writing test) and T017 (speaking transcript test) can run in parallel after request models T007.
- T028 and T030 can run in parallel (catalog vs admin generation are independent).
- T038 can run in parallel with T039 only after the final API contract is chosen.
