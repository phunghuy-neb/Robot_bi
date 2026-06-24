# Tasks: Stage 2 Special Memories
> Clarifications resolved 2026-06-24. Parent-only approval; three axes; encrypted at rest.

## Phase 1: Setup
- [ ] T001 Read placeholder + data sources; verify `EmotionJournal` id column name — file: `src/memory/family_memory.py`, `src/emotion/emotion_journal.py`, `src/infrastructure/database/db.py`
- [ ] T002 [P] Add temp-DB test skeleton for special memories — file: `tests/test_special_memories.py`
- [ ] T003 [P] Add fixtures for families, `events` rows (using `db_id`), and EmotionJournal entries — file: `tests/test_special_memories.py`

## Phase 2: Foundational (blocking)
- [ ] T004 Add `special_memories` schema + indexes (three axes, created_by, encrypted content cols, source soft-ref) — file: `src/infrastructure/database/db.py`
- [ ] T005 Add schema test verifying table/columns/indexes in temp DB — file: `tests/test_special_memories.py`
- [ ] T006 Add app-level encryption helper (encrypt/decrypt content; key sourced outside SQLite) — file: NEW small module under `src/memory/`
- [ ] T007 Add encryption-at-rest test: stored content cells are ciphertext — file: `tests/test_special_memories.py`
- [ ] T008 Define enums/constants: memory_type, status, visibility, recall_policy, created_by — file: `src/memory/family_memory.py`
- [ ] T009 Implement `SpecialMemoryManager` core: create/list/get/update/archive (encrypt on write, decrypt on read) — file: `src/memory/family_memory.py`
- [ ] T010 Add manager CRUD tests with family isolation — file: `tests/test_special_memories.py`

## Phase 3: US1 (P1) — Parent CRUD + propose/approve; Independent test: family B cannot read A; child/Bi proposal lands as pending
- [ ] T011 Add API router skeleton with authenticated routes — file: `src/api/routers/special_memory_router.py`
- [ ] T012 Register special memory router — file: `src/api/server.py`
- [ ] T013 Add create/list API tests + proposal-as-pending test — file: `tests/test_special_memories.py`
- [ ] T014 Implement `POST /api/special-memories`, `POST /api/special-memories/propose`, `GET /api/special-memories` — file: `src/api/routers/special_memory_router.py`
- [ ] T015 Implement `POST /api/special-memories/{memory_id}/approve` (pending→active, parent only) — file: `src/api/routers/special_memory_router.py`
- [ ] T016 Add update/delete API tests — file: `tests/test_special_memories.py`
- [ ] T017 Implement `PATCH` and hard `DELETE /api/special-memories/{memory_id}` — file: `src/api/routers/special_memory_router.py`

## Phase 4: US2 + US4 (P1/P2) — Recall honoring three axes; Independent test: parent_only/never_to_child/pending never reach child prompt
- [ ] T018 Add recall filtering tests (active + child_safe + approved + recall_policy) — file: `tests/test_special_memories.py`
- [ ] T019 Implement `get_recall_context(family_id, limit=3, max_chars=600)` enforcing three axes, labelling text as data — file: `src/memory/family_memory.py`
- [ ] T020 Add prompt-injection-as-data test for recall context — file: `tests/test_special_memories.py`
- [ ] T021 Add test that recall context is bounded (count + chars) — file: `tests/test_special_memories.py`
- [ ] T022 Integrate recall context into runtime before LLM — file: `src/main.py`
- [ ] T023 Add API validation for invalid status/visibility/recall_policy values — file: `src/api/routers/special_memory_router.py`
- [ ] T024 Enforce `concern` type default (parent_only + never_to_child) — file: `src/memory/family_memory.py`

## Phase 5: US3 (P2) — Promote events/emotions via soft reference; Independent test: source ref retained, source not mutated
- [ ] T025 Add test for creating memory from `events.db_id` (soft ref) — file: `tests/test_special_memories.py`
- [ ] T026 Implement event promotion manager method (reference `db_id`, no mutation) — file: `src/memory/family_memory.py`
- [ ] T027 Add `POST /api/special-memories/from-event/{db_id}` — file: `src/api/routers/special_memory_router.py`
- [ ] T028 Add test for creating memory from an EmotionJournal entry — file: `tests/test_special_memories.py`
- [ ] T029 Implement emotion promotion via `EmotionJournal` module (no schema change) — file: `src/memory/family_memory.py`, `src/emotion/emotion_journal.py`
- [ ] T030 Add `POST /api/special-memories/from-emotion/{entry_id}` — file: `src/api/routers/special_memory_router.py`

## Phase 6: US5 + US7 (P2/P3) — Encryption/retention/export/dedup
- [ ] T031 Implement draft auto-expiry (pending older than 30 days purged) — file: `src/memory/family_memory.py`
- [ ] T032 Add test: pending drafts expire at 30 days; approved persist — file: `tests/test_special_memories.py`
- [ ] T033 Implement hard-delete purge (row + embedding + derived data) — file: `src/memory/family_memory.py`
- [ ] T034 Add test that delete purges embedding/derived, not just the row — file: `tests/test_special_memories.py`
- [ ] T035 Implement `GET /api/special-memories/export` (JSON) — file: `src/api/routers/special_memory_router.py`
- [ ] T036 Implement dedup: normalized-text hash + source, then family-scoped embedding similarity; SUGGEST merge only — file: `src/memory/family_memory.py`
- [ ] T037 Add dedup test: near-duplicate suggests merge, never auto-merges — file: `tests/test_special_memories.py`
- [ ] T038 Verify no plaintext of sensitive memories in logs/ChromaDB — file: `tests/test_special_memories.py`

## Phase 7: US6 (P3) — Parent-enabled anniversaries/reminders; Independent test: due memory → candidate only, no TTS
- [ ] T039 Add per-family "reminders enabled" flag (default off) — file: `src/infrastructure/database/db.py`
- [ ] T040 Implement due-memory query helper (date-tagged, parent-enabled) — file: `src/memory/family_memory.py`
- [ ] T041 Implement `GET /api/special-memories/reminders` (candidates only, no TTS) — file: `src/api/routers/special_memory_router.py`
- [ ] T042 Add test: due memory creates reminder candidate; no proactive TTS; quiet-hours respected — file: `tests/test_special_memories.py`

## Phase 8: US7 UI (P3) — Parent review/manage
- [ ] T043 [P] Add memory CRUD/approve/export API helpers — file: `frontend/parent_app/src/services/api.js`
- [ ] T044 Add parent review/approve/manage UI — file: `frontend/parent_app/src/pages/JournalPage.jsx`

## Phase cuối: Polish & cross-cutting (tests, safety, docs)
- [ ] T045 Verify no raw runtime logs/media/cache files are read — file: `src/memory/family_memory.py`
- [ ] T046 Verify all SQL queries include `family_id` where required — file: `src/memory/family_memory.py`, `src/api/routers/special_memory_router.py`
- [ ] T047 Run special memory tests — file: `tests/test_special_memories.py`
- [ ] T048 Run full regression suite where dependencies are available — file: `tests/run_tests.py`
- [ ] T049 Update `SYSTEM_MAP.md` after implementation changes current schema/API/UI — file: `SYSTEM_MAP.md`

## Dependencies
- Foundational T004-T010 (schema + encryption + manager) block all user stories.
- US1 (T011-T017) depends on foundational.
- US2/US4 recall (T018-T024) depends on manager + axes constants T008-T009.
- US3 promotion (T025-T030) depends on US1 API + fixtures T003.
- US5/US7 privacy/retention (T031-T038) depends on manager + encryption.
- US6 reminders (T039-T042) depends on date semantics + parent-enable flag.
- UI (T043-T044) depends on stable backend contract.

## Parallel execution examples
- T002 and T003 can run in parallel.
- T013 and T016 can be authored in parallel after router skeleton T011.
- T025 and T028 can run in parallel after source fixtures exist.
- T032 and T037 can run in parallel (retention vs dedup are independent).
