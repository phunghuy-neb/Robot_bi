# Tasks: Parent App Backend Integration

**Input**: Design documents from `specs/002-parent-app-backend-integration/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Scope**: Future backend implementation only. Do not execute these tasks during the specification-only phase.

**Tests**: Required for every capability. Use `python tests/run_tests.py` after code changes.

**Hard boundaries**: Preserve auth/JWT/rate-limit, family isolation, protected conversation/task/event schemas, runtime DB path, and existing API contracts.

## Phase 1: Setup and Foundation

- [ ] T001 Read `PROJECT.md`, `.claude/handoff.md`, `SYSTEM_MAP.md`, `specs/002-parent-app-backend-integration/spec.md`, and `specs/002-parent-app-backend-integration/plan.md` before implementation.
- [ ] T002 Add idempotent migration helpers for new 002 tables in `src/infrastructure/database/db.py`.
- [ ] T003 Add cleanup allowlist entries for new family-owned 002 tables in `src/infrastructure/database/db.py`.
- [ ] T004 Register new routers in `src/api/server.py` only after the router files and tests exist.
- [ ] T005 Add shared validation helpers for ISO dates, HH:MM times, pagination bounds, and current-family child lookup in `src/api/routers/settings_router.py`.

## Phase 2: Phase 1 Feature - Parent Notes and Event Filters

- [ ] T006 [P] Add tests for `parent_event_notes` schema creation and family cleanup in `tests/run_tests.py`.
- [ ] T007 [P] Add FastAPI tests for event note create/list/update/delete in `tests/run_tests.py`.
- [ ] T008 [P] Add FastAPI tests proving event notes cannot cross family boundaries in `tests/run_tests.py`.
- [ ] T009 Add `parent_event_notes` table creation and indexes in `src/infrastructure/database/db.py`.
- [ ] T010 Implement event note helpers in `src/infrastructure/database/db.py`.
- [ ] T011 Implement `GET /api/events/{event_id}/notes` in `src/api/routers/parent_events_router.py`.
- [ ] T012 Implement `POST /api/events/{event_id}/notes` in `src/api/routers/parent_events_router.py`.
- [ ] T013 Implement `PUT /api/events/{event_id}/notes/{note_id}` in `src/api/routers/parent_events_router.py`.
- [ ] T014 Implement `DELETE /api/events/{event_id}/notes/{note_id}` in `src/api/routers/parent_events_router.py`.
- [ ] T015 [P] Add tests for existing `/api/events` default behavior in `tests/run_tests.py`.
- [ ] T016 [P] Add tests for `/api/events` advanced filters in `tests/run_tests.py`.
- [ ] T017 Extend `GET /api/events` filter handling in `src/api/routers/control_router.py` or move compatible logic into `src/api/routers/parent_events_router.py`.
- [ ] T018 Add `note_count` join for event list responses without breaking existing fields in `src/api/routers/control_router.py`.

## Phase 3: Phase 1 Feature - Monthly Emotion Statistics

- [ ] T019 [P] Add tests for `GET /api/emotion/monthly` and `GET /api/emotions/monthly` route registration in `tests/run_tests.py`.
- [ ] T020 [P] Add tests for monthly aggregation, zero-filled days, invalid month, and family isolation in `tests/run_tests.py`.
- [ ] T021 Implement monthly aggregation helper in `src/emotion/emotion_analyzer.py`.
- [ ] T022 Implement `GET /api/emotion/monthly` in `src/api/routers/emotion_router.py`.
- [ ] T023 Implement compatibility alias `GET /api/emotions/monthly` in `src/api/routers/emotion_router.py`.

## Phase 4: Phase 2 Feature - Child Profiles

- [ ] T024 [P] Add tests for `child_profiles` schema and active-child invariant in `tests/run_tests.py`.
- [ ] T025 [P] Add FastAPI tests for child profile CRUD and family isolation in `tests/run_tests.py`.
- [ ] T026 Add `child_profiles` table, indexes, and cleanup in `src/infrastructure/database/db.py`.
- [ ] T027 Implement child profile DB helpers in `src/infrastructure/database/db.py`.
- [ ] T028 Implement `GET /api/children` and `POST /api/children` in `src/api/routers/settings_router.py`.
- [ ] T029 Implement `GET/PATCH/DELETE /api/children/{child_id}` in `src/api/routers/settings_router.py`.
- [ ] T030 Implement `PUT /api/children/{child_id}/activate` transaction in `src/api/routers/settings_router.py`.

## Phase 5: Phase 2 Feature - Settings Storage

- [ ] T031 [P] Add tests for age filter save/load, validation, and family isolation in `tests/run_tests.py`.
- [ ] T032 [P] Add tests for time limit save/load and usage default response in `tests/run_tests.py`.
- [ ] T033 [P] Add tests for sleep schedule save/load and overnight validation in `tests/run_tests.py`.
- [ ] T034 [P] Add tests for notification settings save/load and push endpoint non-logging in `tests/run_tests.py`.
- [ ] T035 Add `child_content_settings`, `interaction_limit_settings`, `daily_interaction_usage`, `sleep_schedule_settings`, `notification_settings`, and `push_subscriptions` tables in `src/infrastructure/database/db.py`.
- [ ] T036 Implement `GET/POST /api/settings/age-filter` in `src/api/routers/settings_router.py`.
- [ ] T037 Implement `GET/POST /api/settings/time-limits` and `GET /api/usage/today` in `src/api/routers/settings_router.py`.
- [ ] T038 Implement `GET/POST /api/settings/sleep` in `src/api/routers/settings_router.py`.
- [ ] T039 Implement `GET/POST /api/settings/notifications` in `src/api/routers/settings_router.py`.

## Phase 6: Phase 3 Feature - CSV/PDF Reports

- [ ] T040 [P] Add tests for `POST /api/reports/export` CSV content type and family scoping in `tests/run_tests.py`.
- [ ] T041 [P] Add tests for PDF content type, invalid format, invalid date range, and no sensitive logging in `tests/run_tests.py`.
- [ ] T042 Add optional `report_exports` audit table in `src/infrastructure/database/db.py`.
- [ ] T043 Implement family-scoped report data collector in `src/api/routers/reports_router.py`.
- [ ] T044 Implement CSV report renderer using Python standard library in `src/api/routers/reports_router.py`.
- [ ] T045 Implement minimal PDF report renderer or request approval before adding a PDF dependency in `src/api/routers/reports_router.py`.
- [ ] T046 Implement `POST /api/reports/export` file response in `src/api/routers/reports_router.py`.

## Phase 7: Phase 3 Feature - Content Metadata APIs

- [ ] T047 [P] Add tests for `content_items` schema and seed behavior in `tests/run_tests.py`.
- [ ] T048 [P] Add tests for radio/video/game metadata filtering by type, age, language, enabled state, and family in `tests/run_tests.py`.
- [ ] T049 Add `content_items` table and indexes in `src/infrastructure/database/db.py`.
- [ ] T050 Implement content metadata DB helpers and seed defaults in `src/infrastructure/database/db.py` or `src/api/routers/content_router.py`.
- [ ] T051 Implement `GET /api/entertainment/radio` in `src/api/routers/content_router.py`.
- [ ] T052 Implement `GET /api/entertainment/videos` in `src/api/routers/content_router.py`.
- [ ] T053 Implement `GET /api/games/interactive` in `src/api/routers/content_router.py`.

## Phase 8: Phase 3 Feature - Parent Chat History

- [ ] T054 [P] Add tests for parent chat tables and cascade cleanup in `tests/run_tests.py`.
- [ ] T055 [P] Add FastAPI tests for parent chat list/create/detail and cross-family isolation in `tests/run_tests.py`.
- [ ] T056 Add `parent_chat_sessions` and `parent_chat_messages` tables in `src/infrastructure/database/db.py`.
- [ ] T057 Implement parent chat DB helpers in `src/infrastructure/database/db.py`.
- [ ] T058 Implement `GET /api/conversations/parent` in `src/api/routers/parent_chat_router.py`.
- [ ] T059 Implement `POST /api/conversations/parent/messages` in `src/api/routers/parent_chat_router.py`.
- [ ] T060 Implement `GET /api/conversations/parent/{session_id}` in `src/api/routers/parent_chat_router.py`.

## Phase 9: Phase 4 Feature - QR and Robot Location Metadata

- [ ] T061 [P] Add tests for pairing code TTL, hashing, and family isolation in `tests/run_tests.py`.
- [ ] T062 [P] Add tests for robot location save/load, validation, and family isolation in `tests/run_tests.py`.
- [ ] T063 Add `device_pairing_codes` and `robot_location_metadata` tables in `src/infrastructure/database/db.py`.
- [ ] T064 Implement QR pairing metadata generation in `src/api/routers/device_router.py`.
- [ ] T065 Implement `GET /api/device/connection-qr` in `src/api/routers/device_router.py`.
- [ ] T066 Implement `GET/POST /api/robot/location` in `src/api/routers/device_router.py`.

## Phase 10: Phase 4 Feature - Admin System Logs

- [ ] T067 [P] Add tests for non-admin 403 and admin 200 on `GET /api/admin/logs` in `tests/run_tests.py`.
- [ ] T068 [P] Add tests for log limit bounds and secret/token redaction in `tests/run_tests.py`.
- [ ] T069 Implement sanitized log reader service in `src/api/routers/admin_logs_router.py`.
- [ ] T070 Implement `GET /api/admin/logs` using existing admin guard in `src/api/routers/admin_logs_router.py`.

## Phase 11: Final Verification and Documentation

- [ ] T071 Run `python tests/run_tests.py` and fix regressions before ending implementation work.
- [ ] T072 Update `SYSTEM_MAP.md` after backend implementation is complete, listing new current APIs accurately.
- [ ] T073 Update `.claude/handoff.md` after backend implementation is complete.
- [ ] T074 Update frontend mock adapters in `frontend/parent_app/src/services/api.js` only after the relevant backend phase passes tests.

## Dependency Graph

```text
Foundation -> Phase 1 notes/filters/emotion
Foundation -> Phase 2 child/settings
Foundation -> Phase 3 reports/content/chat
Foundation -> Phase 4 device/admin

Reports depend on Phase 1 notes only if notes are included in report sections.
Content metadata can be implemented independently after content_items exists.
Parent chat is independent from child conversation tables.
Admin logs can be implemented independently after admin guard reuse is verified.
```

## MVP Scope

Phase 1 is the MVP:

- Parent notes on events.
- Advanced event filters.
- Monthly emotion statistics.

MVP is independently testable and unlocks the highest-value mock features in the journal/monitoring flow.
