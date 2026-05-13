# Implementation Plan: Parent App Backend Integration

**Branch**: `002-parent-app-backend-integration` | **Date**: 2026-05-13 | **Spec**: [spec.md](spec.md)

## Summary

Implement additive FastAPI + SQLite backend support for Parent App Tier 2 features from `001-parent-app-redesign`. The implementation must keep existing auth/JWT/rate-limit, family isolation, conversation APIs, event APIs, task schema, and protected fixes intact.

This plan is specification-only. It proposes future implementation work but does not modify `src/`, `frontend/`, `firmware/`, `runtime/`, `logs/`, or `.env`.

## Technical Context

**Backend stack**: FastAPI routers in `src/api/routers/`, SQLite helpers in `src/infrastructure/database/db.py`, JWT auth in `src/infrastructure/auth/auth.py`.

**Current API assembly**: `src/api/server.py` includes route modules directly.

**Current auth guard**: `get_current_user()` returns authenticated user context including `user_id` and `family_name`; routes use `_require_family()` for fail-closed family access.

**Current admin guard**: `admin_router.require_admin()` uses `is_user_admin()`.

**Current test runner**: `python tests/run_tests.py`.

**Storage**: SQLite at `runtime/robot_bi.db` through existing DB helper only.

**Constraints**:

- Additive endpoints only.
- Do not change existing API response shapes unless adding optional fields that are backward-compatible.
- New data must be family-scoped by JWT-derived family.
- No hardcoded secrets.
- No package install without approval.
- No runtime/log/env file edits.

## Constitution Check

| Gate | Status | Notes |
|---|---|---|
| PROJECT.md source of truth | PASS | Spec follows protected fixes and hard constraints. |
| Auth/JWT/rate-limit preserved | PASS | New routes use existing `get_current_user`; no auth route changes proposed. |
| Family isolation preserved | PASS | Every family entity includes `family_id`; admin logs are explicitly admin-only. |
| DB path/schema constraints | PASS | Existing protected tables are not changed incompatibly. |
| Existing contracts preserved | PASS | `/api/events` only gets optional filters; default shape remains compatible. |
| Child safety/privacy | PASS | Notes, reports, chat, logs include no-sensitive-logging requirements. |
| File creation policy | PASS | Only files under `specs/002-parent-app-backend-integration/` are created. |

## Proposed Router Ownership

Future implementation may add focused routers instead of expanding already large routers:

| Area | Proposed file | Endpoints |
|---|---|---|
| Event notes and filters | `src/api/routers/parent_events_router.py` or extend `control_router.py` carefully | `/api/events`, `/api/events/{event_id}/notes` |
| Monthly emotion stats | `src/api/routers/emotion_router.py` | `/api/emotion/monthly`, `/api/emotions/monthly` |
| Child profiles/settings | `src/api/routers/settings_router.py` | `/api/children`, `/api/settings/*`, `/api/usage/today` |
| Reports | `src/api/routers/reports_router.py` | `/api/reports/export` |
| Content metadata | `src/api/routers/content_router.py` | `/api/entertainment/*`, `/api/games/interactive` |
| Device/location metadata | `src/api/routers/device_router.py` | `/api/device/connection-qr`, `/api/robot/location` |
| Parent chat | `src/api/routers/parent_chat_router.py` | `/api/conversations/parent*` |
| Admin logs | `src/api/routers/admin_logs_router.py` or extend `admin_router.py` | `/api/admin/logs` |

Router registration must be added in `src/api/server.py` only during implementation.

## Existing Endpoints Reused

- `GET /api/events`: reused and extended for advanced filters.
- `GET /api/analytics/weekly`, `GET /api/analytics/daily`: report export data source.
- `GET /api/emotion/today`, `GET /api/emotion/summary`: monthly emotion aggregation companion.
- `GET /api/conversations`, `GET /api/conversations/{session_id}`: report data source and protected child history baseline.
- `GET /api/education/*`, `GET /api/game/scores`, `GET /api/tasks`: report data sources.
- `GET /api/wifi/status`: device metadata companion.
- `GET /api/admin/families`: existing admin-only pattern.

## New Endpoints Proposed

| Phase | Capability | Method and path |
|---|---|---|
| 1 | Parent notes | `GET/POST /api/events/{event_id}/notes`, `PUT/DELETE /api/events/{event_id}/notes/{note_id}` |
| 1 | Advanced event filters | `GET /api/events` optional query expansion |
| 1 | Monthly emotion stats | `GET /api/emotion/monthly`, alias `GET /api/emotions/monthly` |
| 2 | Child profiles | `GET/POST /api/children`, `GET/PATCH/DELETE /api/children/{child_id}`, `PUT /api/children/{child_id}/activate` |
| 2 | Age topic filter | `GET/POST /api/settings/age-filter` |
| 2 | Daily interaction limit | `GET/POST /api/settings/time-limits`, `GET /api/usage/today` |
| 2 | Sleep schedule | `GET/POST /api/settings/sleep` |
| 2 | Push settings | `GET/POST /api/settings/notifications` |
| 3 | Report export | `POST /api/reports/export` |
| 3 | Metadata APIs | `GET /api/entertainment/radio`, `GET /api/entertainment/videos`, `GET /api/games/interactive` |
| 3 | Parent chat history | `GET /api/conversations/parent`, `POST /api/conversations/parent/messages`, `GET /api/conversations/parent/{session_id}` |
| 4 | QR metadata | `GET /api/device/connection-qr` |
| 4 | Robot location | `GET/POST /api/robot/location` |
| 4 | Admin logs | `GET /api/admin/logs` |

## Phase 1: Journal and Emotion MVP

**Goal**: Replace mock Parent App journal features that directly support monitoring.

Capabilities:

- Parent notes on events.
- Advanced event filters.
- Monthly emotion statistics.

Design points:

- Keep current `GET /api/events` defaults: `type`, `unread_only`, and `limit` keep working.
- Add `offset`, date range, multi-type, clip, note, and text search as optional filters.
- Add `note_count` to event rows as an optional field only.
- Store notes in a separate table to avoid changing protected event ingestion.
- Monthly emotions read existing emotion tables and expose both singular and plural route names.

Tests:

- Add tests to `tests/run_tests.py` near existing event/emotion groups.
- Include direct helper tests plus FastAPI `TestClient` tests.
- Include family A/B isolation for events, notes, and emotion logs.

## Phase 2: Child Profiles and Settings

**Goal**: Persist Parent App settings currently shown in the Settings overlay.

Capabilities:

- Child profiles.
- Age-based topic filter.
- Daily interaction limit.
- Sleep schedule settings.
- Push notification settings storage.

Design points:

- Use child profiles as optional owners of settings; each settings API must work family-wide when `child_id` is omitted.
- Do not enforce daily limit or sleep mode in the voice loop until separate integration work is explicitly planned. This phase stores and exposes settings plus usage summary.
- Push settings store preferences and optional browser push subscription data; they do not require web push delivery yet.
- Future content filters must consult the age filter before returning video/game/radio metadata.

Tests:

- CRUD and validation for child profiles.
- Settings save/load and cross-family isolation.
- Invalid time/age/limit payload rejection.
- Push endpoint/hash values not logged.

## Phase 3: Reports, Content Metadata, Parent Chat

**Goal**: Replace mock data in report export, entertainment metadata, and parent-to-Bi history.

Capabilities:

- CSV/PDF report export.
- Radio/video/game metadata APIs.
- Parent <-> Bi chat history.

Design points:

- CSV export should use Python standard library.
- PDF export should avoid adding dependencies unless approved; a minimal text/table PDF is acceptable.
- Report data must come from existing family-scoped APIs/tables.
- Content metadata can be stored in SQLite and seeded from local resources or static defaults.
- Parent chat is separate from child `conversations` and `turns`.

Tests:

- CSV and PDF content types.
- Date range validation.
- Report excludes other-family events/conversations/notes.
- Metadata endpoints filter by type, enabled state, age, and language.
- Parent chat cannot read/write another family's sessions.

## Phase 4: Device Metadata and Admin Operations

**Goal**: Implement technical/admin metadata endpoints after family-facing flows are stable.

Capabilities:

- QR device connection metadata.
- Robot room/location metadata.
- Admin system logs API.

Design points:

- QR payloads use short-lived one-time codes; only hashes are stored.
- Robot location is metadata only and does not require firmware changes.
- Admin logs expose sanitized operational entries, not arbitrary file access.
- Admin log filters must have strict limit bounds and redaction.

Tests:

- Pairing TTL bounds and no raw code persistence.
- Robot location save/load and family isolation.
- Admin logs non-admin 403, admin 200, redaction, pagination bounds.

## Database Migration Strategy

Add idempotent `CREATE TABLE IF NOT EXISTS` migrations in the existing `init_db()` flow or a helper called by it. Do not alter protected tables incompatibly.

Required new tables:

- `parent_event_notes`
- `child_profiles`
- `child_content_settings`
- `interaction_limit_settings`
- `daily_interaction_usage`
- `sleep_schedule_settings`
- `notification_settings`
- `push_subscriptions`
- `report_exports` (optional audit table)
- `content_items`
- `device_pairing_codes`
- `robot_location_metadata`
- `parent_chat_sessions`
- `parent_chat_messages`

No new table is required for admin logs in Phase 4 unless implementation chooses DB-backed sanitized logs.

## Validation Strategy

- IDs: use UUID strings for new primary IDs.
- Dates: accept ISO `YYYY-MM-DD`; reject invalid ranges where start is after end.
- Times: accept `HH:MM` 24-hour format.
- Pagination: `limit` minimum 1, maximum 200 unless a stricter endpoint-specific limit is listed.
- Text: trim inputs; reject empty values; enforce max lengths.
- Enums: reject unknown values with 422.
- Family IDs: never accept client-supplied `family_id` for family-owned writes.

## Verification Plan

Future implementation must run:

```bash
python tests/run_tests.py
```

Docs/spec-only creation does not require running tests now because no code was changed.

## Rollout Plan

1. Implement Phase 1 and run full tests.
2. Update frontend mock adapters for Phase 1 only after backend tests pass.
3. Implement Phase 2 and run full tests.
4. Update frontend Settings overlay adapters.
5. Implement Phase 3 and run full tests.
6. Update report/content/chat adapters.
7. Implement Phase 4 and run full tests.
8. Update `SYSTEM_MAP.md` only after actual backend implementation changes are complete.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Family leakage through filters or reports | High | Every query starts with JWT-derived `family_id`; add A/B isolation tests. |
| Event route regression | High | Preserve default `/api/events` behavior; add regression tests for existing query params. |
| Auth route confusion in frontend | Medium | Backend spec does not change auth; frontend integration must use actual JWT endpoints. |
| PDF export dependency creep | Medium | Use standard library minimal PDF or request approval before adding dependency. |
| Admin logs expose secrets | High | Redact JWTs, API keys, pairing codes, push endpoints; deny raw file paths. |
| Settings stored but not enforced | Medium | Make enforcement explicitly out of scope until integration task is planned. |

*Plan complete. No implementation performed.*
