# Research: Parent App Backend Integration

**Feature**: 002-parent-app-backend-integration | **Date**: 2026-05-13

## Decision: Additive API Integration

**Decision**: All backend integration work must add endpoints or optional query parameters. Existing endpoint defaults and response shapes remain compatible.

**Rationale**: `PROJECT.md` marks auth/JWT, family isolation, conversations, events, tasks, and DB path/schema as protected. The React Parent App already consumes Tier 1 endpoints. Backward-compatible additions reduce regression risk.

**Alternatives considered**:

- Replace existing endpoints with new versioned endpoints: rejected because it increases frontend churn and risks protected behavior.
- Add a general `/api/parent-app/*` proxy: rejected because it hides ownership and makes tests less direct.

## Decision: JWT-Derived Family Scoping

**Decision**: New routes derive family ownership from `get_current_user()` and `_require_family()`. Request bodies never accept trusted `family_id`.

**Rationale**: Existing protected behavior requires multi-family isolation. Current routers already use this pattern for conversations, events, memories, tasks, education, emotion, and games.

**Alternatives considered**:

- Accept `family_id` query/body for admin convenience: rejected for Phase 1-4 because it increases leakage risk.
- Use frontend-selected family state: rejected because frontend state is not authoritative.

## Decision: Notes Use a Separate Table

**Decision**: Store parent notes in `parent_event_notes` rather than adding a note column to `events`.

**Rationale**: Event ingestion is used by notifier/runtime paths and should stay stable. A separate table supports multiple notes later, audit metadata, and note count joins without changing event write code.

**Alternatives considered**:

- Add `parent_note` to `events`: simpler but less flexible and risks touching protected event behavior.
- Store notes in event metadata JSON: rejected because metadata shape varies by event source and is harder to query.

## Decision: Extend `/api/events` Carefully

**Decision**: Keep `GET /api/events` as the event list endpoint and add optional advanced filters.

**Rationale**: The frontend already calls `/api/events`; preserving this endpoint avoids a parallel event list. Existing query parameters (`type`, `unread_only`, `limit`) remain valid.

**Alternatives considered**:

- Add `/api/events/search`: cleaner separation but duplicates list behavior.
- Add POST search: unnecessary for current filter size.

## Decision: Monthly Emotion Alias

**Decision**: Use primary path `GET /api/emotion/monthly` and provide alias `GET /api/emotions/monthly`.

**Rationale**: Existing backend convention is singular `/api/emotion/*`, but the frontend TODO from the React migration references plural `/api/emotions/monthly`. An alias keeps integration low-friction while preserving backend naming style.

**Alternatives considered**:

- Only singular: requires frontend TODO adjustment.
- Only plural: inconsistent with current backend routes.

## Decision: Settings Are Stored Before They Are Enforced

**Decision**: Phase 2 stores child profiles and settings, but enforcement in the main robot loop is not part of this backend integration spec.

**Rationale**: Daily limits, sleep schedules, and age filters affect runtime voice/content behavior. Enforcing them safely requires a separate cross-module plan touching `src/main.py`, education/entertainment modules, and possibly safety logic. The Parent App first needs persistence APIs to remove mock state.

**Alternatives considered**:

- Enforce immediately in all modules: too broad for this feature and risks protected voice/safety behavior.
- Keep settings frontend-only: fails the backend objective.

## Decision: Content Metadata Stored in SQLite

**Decision**: Store radio/video/game metadata in a generic `content_items` table with `type`, age range, language, tags, and enabled state.

**Rationale**: The frontend needs consistent metadata cards for multiple content types. A single table keeps filtering and family overrides consistent. Existing quiz endpoints continue to serve gameplay.

**Alternatives considered**:

- Separate tables for radio, videos, games: more schema and duplicate filters.
- Static JSON only: easier at first but does not support family overrides or admin curation later.

## Decision: Report Export Is Generated On Demand

**Decision**: Generate CSV/PDF reports on demand from family-scoped tables. Store only optional export audit metadata, not files.

**Rationale**: Runtime files must not be tracked or manipulated by default, and reports may contain sensitive child/family data. On-demand generation avoids file lifecycle/security issues.

**Alternatives considered**:

- Persist report files under runtime: rejected unless later explicitly requested.
- Require a PDF package immediately: rejected because package installation requires user approval. A minimal standard-library PDF is acceptable for Phase 3.

## Decision: Parent Chat Is Separate From Child Conversation History

**Decision**: Use `parent_chat_sessions` and `parent_chat_messages`, not existing `conversations` and `turns`.

**Rationale**: Existing conversation tables are protected and represent child/robot sessions. Parent-to-Bi chat has different actor roles, privacy expectations, and UI placement.

**Alternatives considered**:

- Reuse `conversations` with extra role values: rejected because `turns.role` has a protected constraint.
- Store parent chat as events: rejected because message history needs ordered session detail.

## Decision: QR Codes Store Hashes Only

**Decision**: Generate short-lived pairing metadata and store only `code_hash`, never the raw pairing code.

**Rationale**: Pairing codes function like temporary secrets. The project forbids hardcoded or leaked secrets. Raw codes should only exist in the response for immediate QR rendering.

**Alternatives considered**:

- Store raw code for troubleshooting: rejected due to security risk.
- No DB record: rejected because expiration/use tracking needs persistence.

## Decision: Admin Logs Are Sanitized, Not Raw File Access

**Decision**: `GET /api/admin/logs` exposes sanitized entries through a controlled service, not arbitrary file reads.

**Rationale**: The project forbids reading logs by default, and logs can contain operational detail. This feature explicitly requests an admin logs API, so the future implementation must constrain scope, redact sensitive values, and enforce admin-only access.

**Alternatives considered**:

- Return raw `logs/` file content: rejected.
- Make logs available to all parents: rejected; admin-only is required.

## Open Items for Implementation

- Decide whether Phase 3 PDF uses a minimal internal PDF writer or requests approval for a third-party PDF dependency.
- Decide whether content metadata should be seeded from local JSON resources during `init_db()` or lazily by endpoint helper.
- Decide whether parent notes are single-note UX in frontend while backend supports multiple notes.

No blocking clarification is required for the specification.
