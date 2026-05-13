# Feature Specification: Parent App Backend Integration

**Feature Branch**: `002-parent-app-backend-integration`

**Created**: 2026-05-13

**Status**: Draft - backend specification only

**Input**: Define real backend APIs for Parent App React + Vite Tier 2 features from `001-parent-app-redesign`. Do not implement backend code in this phase.

## Scope

This feature specifies additive backend APIs for Parent App features that are currently mock-only or placeholder-only in `frontend/parent_app/`.

No source code is implemented by this specification. Future implementation must preserve all protected behavior from `PROJECT.md`, especially auth/JWT/rate limits, family isolation, existing conversation/task/event contracts, SQLite runtime path, and current LLM/safety behavior.

## User Scenarios & Testing

### User Story 1 - Parent reviews the journal with notes and stronger filters (Priority: P1)

A parent opens the journal, filters events by date/type/read state/clip/note/text, and adds a private note to an event so future review has context.

**Why this priority**: Journal review is one of the Parent App's core supervision flows. Notes and filtering turn raw events into usable supervision history.

**Independent Test**: With authenticated family A and family B users, create events for both families. Family A can filter only its own events, add a note to its own event, update/delete that note, and cannot see or modify family B notes or events.

### User Story 2 - Parent sees monthly emotion statistics (Priority: P1)

A parent opens the monthly emotion chart and sees real aggregated emotion data for the selected month instead of mock data.

**Why this priority**: Emotion monitoring is child safety adjacent and currently visible in the Parent App as sample data.

**Independent Test**: Seed emotion logs for a family across multiple days in one month. The monthly endpoint returns day and week buckets, totals, dominant emotion, and zero-filled days for dates without data.

### User Story 3 - Parent manages child profiles and household settings (Priority: P2)

A parent manages child profiles and saves settings for age-based content, daily limits, sleep schedule, and notifications.

**Why this priority**: These settings personalize Robot Bi for children ages 5-12 and must persist across sessions before the frontend can remove mock badges.

**Independent Test**: A parent creates two child profiles, saves settings for one child, reloads them, updates them, and cannot access a child profile or settings from another family.

### User Story 4 - Parent exports reports and browses metadata-backed content (Priority: P3)

A parent exports CSV/PDF reports and sees real metadata lists for radio, videos, interactive games, and parent-to-Bi chat history.

**Why this priority**: These features improve usefulness but are less urgent than monitoring and safety settings.

**Independent Test**: A parent requests a report for a date range and receives only current-family data. Metadata endpoints return real configured items filtered by age/language where requested. Parent chat history is separated from child conversation history.

### User Story 5 - Admin manages device metadata and system logs (Priority: P4)

An admin views device connection metadata, robot room/location metadata, and sanitized system logs without exposing secrets or raw runtime files.

**Why this priority**: These are technical/admin flows and should stay behind admin or authenticated boundaries.

**Independent Test**: A non-admin user receives 403 from admin logs. An admin receives sanitized log entries with limit bounds. Device QR metadata is short-lived and family-scoped.

## Global Requirements

- **GB-001**: All new endpoints must require the existing JWT auth guard unless explicitly stated otherwise. No new auth mechanism is introduced.
- **GB-002**: All family-owned data must derive `family_id` from the authenticated user's JWT/current user context. Request bodies must not be trusted for family selection.
- **GB-003**: Admin-only endpoints must use the existing admin check pattern (`is_user_admin` via `require_admin`) and must return 403 to non-admin users.
- **GB-004**: Existing endpoint paths and response shapes must remain backward-compatible. Optional query parameters may be added to existing routes only if default behavior remains unchanged.
- **GB-005**: New SQLite tables must live in `runtime/robot_bi.db` through the existing database helper path. Runtime database files must not be read or edited manually during implementation.
- **GB-006**: New write endpoints must validate string lengths, enum values, date/time formats, and pagination bounds.
- **GB-007**: No API may log child text, parent notes, JWTs, refresh tokens, pairing codes, push endpoints, `.env` values, or full report contents at INFO/WARNING/ERROR level.
- **GB-008**: Test coverage for each capability must include route registration, happy path, validation failure, auth failure where relevant, and family isolation.

## Existing Endpoints Reused

- Auth/JWT: `/api/auth/me`, `/auth/login/v2`, `/auth/refresh`, `/auth/logout`, `/api/auth/logout-all`
- Events: `GET /api/events`, `POST /api/events/read_all`
- Conversations: `GET /api/conversations`, `GET /api/conversations/{session_id}`, `GET /api/conversations/homework`, `POST /api/conversations/{session_id}/homework`
- Analytics: `GET /api/analytics/weekly`, `GET /api/analytics/daily`
- Emotion: `GET /api/emotion/today`, `GET /api/emotion/summary`
- Education: `/api/education/*`
- Games: `/api/game/*`
- Music: `/api/music/*`
- Device/WiFi/camera: `/api/wifi/status`, `/api/camera`, `/api/webrtc/*`
- Admin families: `/api/admin/families`

## Capability Requirements

### C1. Parent Notes on Events - Phase 1

**Endpoints**

- `GET /api/events/{event_id}/notes`
- `POST /api/events/{event_id}/notes`
- `PUT /api/events/{event_id}/notes/{note_id}`
- `DELETE /api/events/{event_id}/notes/{note_id}`

**Request Body**

```json
{
  "note": "Parent-visible note, 1-2000 chars"
}
```

`GET` and `DELETE` have no body.

**Response Shape**

```json
{
  "ok": true,
  "note": {
    "note_id": "uuid",
    "event_id": "event-id",
    "note": "Parent-visible note",
    "created_at": "2026-05-13T10:00:00Z",
    "updated_at": "2026-05-13T10:00:00Z"
  }
}
```

`GET` returns `{"notes": [...], "total": 1}`. `DELETE` returns `{"ok": true}`.

**DB**

New table `parent_event_notes`: `note_id`, `family_id`, `event_id`, `user_id`, `note`, `created_at`, `updated_at`.

**Family Rule**

The referenced event must exist where `events.family_id == current_user.family_name`. Notes must also store the same `family_id`.

**Admin Rule**

Not admin-only. Any authenticated user in the family can manage notes for that family.

**Required Tests**

Route registration; create/list/update/delete; note length validation; 404 for missing event; 404/403 for cross-family event/note; auth required.

### C2. Advanced Event Filters - Phase 1

**Endpoint**

- `GET /api/events`

This extends the existing endpoint with optional query parameters while preserving current defaults.

**Request Query**

```text
type=chat
types=chat,cry,homework
start_date=2026-05-01
end_date=2026-05-31
unread_only=false
has_clip=true
has_note=false
q=keyword
limit=20
offset=0
sort=desc
```

**Response Shape**

```json
{
  "events": [
    {
      "id": "event-id",
      "family_id": "family-a",
      "timestamp": "2026-05-13T10:00:00",
      "type": "chat",
      "message": "event summary",
      "clip_path": null,
      "metadata": {},
      "read": false,
      "note_count": 1
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0,
  "filters": {}
}
```

**DB**

No new table beyond C1. Add indexes if needed: `events(family_id, timestamp)`, `events(family_id, type, timestamp)`, `parent_event_notes(family_id, event_id)`.

**Family Rule**

Always filter `events.family_id` by current family before applying user-provided filters.

**Admin Rule**

Not admin-only. Admins still see only their authenticated family unless a separate future admin-family parameter is explicitly specified.

**Required Tests**

Default `GET /api/events` response unchanged; limit/offset bounds; date range filtering; `types` filtering; `has_note` join scoped to family; text query does not bypass family scope.

### C3. Monthly Emotion Statistics - Phase 1

**Endpoints**

- `GET /api/emotion/monthly`
- `GET /api/emotions/monthly` as a compatibility alias for frontend TODOs from spec 001.

**Request Query**

```text
month=2026-05
child_id=optional-child-id
```

**Response Shape**

```json
{
  "family_id": "family-a",
  "child_id": null,
  "month": "2026-05",
  "timezone": "UTC",
  "total_entries": 12,
  "dominant": "happy",
  "days": [
    {"date": "2026-05-01", "happy": 0, "neutral": 1, "sad": 0, "stressed": 0, "dominant": "neutral", "count": 1}
  ],
  "weeks": [
    {"week_start": "2026-04-27", "happy": 3, "neutral": 2, "sad": 1, "stressed": 0, "dominant": "happy", "count": 6}
  ]
}
```

**DB**

No new table required. Read from existing `emotion_logs` and `emotion_journal`. If child-specific emotion logging is added later, add nullable `child_id` to emotion rows only through a backward-compatible migration.

**Family Rule**

Always aggregate rows where `family_id == current_user.family_name`. If `child_id` is provided, it must belong to the same family.

**Admin Rule**

Not admin-only.

**Required Tests**

Route registration for primary and alias paths; valid/invalid month parsing; zero-filled month; aggregation correctness; cross-family data exclusion.

### C4. Child Profiles - Phase 2

**Endpoints**

- `GET /api/children`
- `POST /api/children`
- `GET /api/children/{child_id}`
- `PATCH /api/children/{child_id}`
- `DELETE /api/children/{child_id}`
- `PUT /api/children/{child_id}/activate`

**Request Body**

```json
{
  "name": "Minh",
  "birth_date": "2018-04-20",
  "age": 8,
  "grade": "2",
  "avatar": "boy",
  "interests": ["math", "animals"],
  "notes": "Optional parent-only notes"
}
```

`birth_date` is preferred. `age` may be accepted for frontend convenience and converted to an approximate age display, but the backend should store `birth_date` when available.

**Response Shape**

```json
{
  "children": [
    {
      "child_id": "uuid",
      "name": "Minh",
      "birth_date": "2018-04-20",
      "age": 8,
      "grade": "2",
      "avatar": "boy",
      "interests": ["math", "animals"],
      "is_active": true,
      "created_at": "2026-05-13T10:00:00Z",
      "updated_at": "2026-05-13T10:00:00Z"
    }
  ],
  "active_child_id": "uuid"
}
```

**DB**

New table `child_profiles`: `child_id`, `family_id`, `name`, `birth_date`, `grade`, `avatar`, `interests_json`, `notes`, `is_active`, `created_at`, `updated_at`.

**Family Rule**

All reads/writes must include `family_id == current_user.family_name`.

**Admin Rule**

Not admin-only.

**Required Tests**

CRUD; activate exactly one child per family; validation of name/age/date; deleting a child must not delete family data; cross-family child access denied.

### C5. Age-Based Topic Filter - Phase 2

**Endpoints**

- `GET /api/settings/age-filter`
- `POST /api/settings/age-filter`

**Request Body**

```json
{
  "child_id": "optional-child-id",
  "enabled": true,
  "min_age": 5,
  "max_age": 8,
  "blocked_topics": ["violence", "scary"],
  "allowed_topics": ["math", "animals", "english"],
  "strict_mode": true
}
```

**Response Shape**

```json
{
  "ok": true,
  "settings": {
    "child_id": "optional-child-id",
    "enabled": true,
    "min_age": 5,
    "max_age": 8,
    "blocked_topics": ["violence"],
    "allowed_topics": ["math"],
    "strict_mode": true,
    "updated_at": "2026-05-13T10:00:00Z"
  }
}
```

**DB**

New table `child_content_settings`: `setting_id`, `family_id`, `child_id`, `enabled`, `min_age`, `max_age`, `blocked_topics_json`, `allowed_topics_json`, `strict_mode`, `updated_at`.

**Family Rule**

If `child_id` is supplied, it must belong to the current family. Otherwise settings apply family-wide.

**Admin Rule**

Not admin-only.

**Required Tests**

Save/load family-wide settings; save/load child-specific settings; invalid age ranges rejected; cross-family child rejected; future content metadata respects age filter.

### C6. Daily Interaction Limit - Phase 2

**Endpoints**

- `GET /api/settings/time-limits`
- `POST /api/settings/time-limits`
- `GET /api/usage/today`

**Request Body**

```json
{
  "child_id": "optional-child-id",
  "enabled": true,
  "daily_limit_minutes": 60,
  "warning_minutes": 10,
  "reset_time": "00:00"
}
```

**Response Shape**

```json
{
  "ok": true,
  "settings": {
    "enabled": true,
    "daily_limit_minutes": 60,
    "warning_minutes": 10,
    "reset_time": "00:00"
  },
  "usage_today": {
    "date": "2026-05-13",
    "seconds_used": 1200,
    "remaining_seconds": 2400,
    "limit_reached": false
  }
}
```

**DB**

New tables:

- `interaction_limit_settings`: `setting_id`, `family_id`, `child_id`, `enabled`, `daily_limit_minutes`, `warning_minutes`, `reset_time`, `updated_at`
- `daily_interaction_usage`: `family_id`, `child_id`, `usage_date`, `seconds_used`, `sessions_count`, `updated_at`

**Family Rule**

All rows are scoped by current family. `child_id`, if present, must belong to that family.

**Admin Rule**

Not admin-only.

**Required Tests**

Save/load settings; invalid limits rejected; usage response defaults to zero; family isolation; no change to existing conversation creation helpers.

### C7. Sleep Schedule Settings - Phase 2

**Endpoints**

- `GET /api/settings/sleep`
- `POST /api/settings/sleep`

**Request Body**

```json
{
  "enabled": true,
  "start_time": "21:00",
  "end_time": "06:30",
  "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
  "timezone": "Asia/Ho_Chi_Minh"
}
```

**Response Shape**

```json
{
  "ok": true,
  "settings": {
    "enabled": true,
    "start_time": "21:00",
    "end_time": "06:30",
    "days": ["mon", "tue"],
    "timezone": "Asia/Ho_Chi_Minh",
    "updated_at": "2026-05-13T10:00:00Z"
  }
}
```

**DB**

New table `sleep_schedule_settings`: `family_id`, `enabled`, `start_time`, `end_time`, `days_json`, `timezone`, `updated_at`.

**Family Rule**

One row per family.

**Admin Rule**

Not admin-only.

**Required Tests**

Save/load; HH:MM validation; overnight schedule accepted; invalid days rejected; family isolation.

### C8. Push Notification Settings Storage - Phase 2

**Endpoints**

- `GET /api/settings/notifications`
- `POST /api/settings/notifications`

**Request Body**

```json
{
  "enabled": true,
  "event_types": {
    "cry": true,
    "homework": true,
    "system": false
  },
  "quiet_hours": {"enabled": true, "start_time": "21:00", "end_time": "07:00"},
  "channels": {"in_app": true, "web_push": false},
  "push_subscription": null
}
```

**Response Shape**

```json
{
  "ok": true,
  "settings": {
    "enabled": true,
    "event_types": {},
    "quiet_hours": {},
    "channels": {},
    "updated_at": "2026-05-13T10:00:00Z"
  }
}
```

**DB**

New tables:

- `notification_settings`: `family_id`, `enabled`, `event_types_json`, `quiet_hours_json`, `channels_json`, `updated_at`
- `push_subscriptions`: `subscription_id`, `family_id`, `user_id`, `endpoint_hash`, `subscription_json`, `created_at`, `updated_at`, `revoked_at`

**Family Rule**

Subscriptions and settings are scoped by family and current user.

**Admin Rule**

Not admin-only.

**Required Tests**

Save/load settings; invalid event type rejected; endpoint not logged; family/user scoping; web push disabled by default.

### C9. CSV/PDF Report Export - Phase 3

**Endpoint**

- `POST /api/reports/export`

**Request Body**

```json
{
  "format": "csv",
  "start_date": "2026-05-01",
  "end_date": "2026-05-31",
  "sections": ["events", "conversations", "emotions", "education", "tasks"],
  "child_id": null
}
```

`format` supports `csv` and `pdf`.

**Response Shape**

Binary file response:

- CSV: `Content-Type: text/csv; charset=utf-8`
- PDF: `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="robot-bi-report-2026-05-01-2026-05-31.csv"`

For JSON error responses, use existing FastAPI error format.

**DB**

Optional new table `report_exports` for audit metadata only: `export_id`, `family_id`, `user_id`, `format`, `start_date`, `end_date`, `sections_json`, `created_at`, `status`.

**Family Rule**

All report queries must use the current family. `child_id`, if provided, must belong to the current family.

**Admin Rule**

Not admin-only.

**Required Tests**

CSV content type; PDF content type and nonempty bytes; date validation; invalid format rejected; report excludes other-family data; no raw notes/chat content in logs.

### C10. Radio/Video/Game Metadata APIs - Phase 3

**Endpoints**

- `GET /api/entertainment/radio`
- `GET /api/entertainment/videos`
- `GET /api/games/interactive`

**Request Query**

```text
language=vi
min_age=5
max_age=8
enabled_only=true
```

**Response Shape**

```json
{
  "items": [
    {
      "content_id": "radio-vov2",
      "type": "radio",
      "title": "VOV2",
      "description": "Culture and education",
      "source_url": "https://example.invalid/stream",
      "thumbnail_url": null,
      "age_min": 5,
      "age_max": 12,
      "language": "vi",
      "tags": ["education"],
      "enabled": true
    }
  ],
  "total": 1
}
```

**DB**

New table `content_items`: `content_id`, `family_id`, `type`, `title`, `description`, `source_url`, `thumbnail_url`, `age_min`, `age_max`, `language`, `tags_json`, `enabled`, `sort_order`, `created_at`, `updated_at`.

Rows may be global when `family_id` is null, or family-specific overrides when `family_id` is set.

**Family Rule**

Return global rows plus current-family rows. Never return rows for another family.

**Admin Rule**

Read endpoints are not admin-only. Future create/update/delete catalog endpoints should be admin-only.

**Required Tests**

Route registration; type filtering; age filtering; disabled rows hidden by default; family-specific rows isolated; existing `/api/game/*` quiz endpoints unchanged.

### C11. QR Device Connection Metadata - Phase 4

**Endpoint**

- `GET /api/device/connection-qr`

**Request Query**

```text
purpose=parent_app
ttl_seconds=300
```

Allowed `purpose`: `parent_app`, `robot_display`, `esp32`.

**Response Shape**

```json
{
  "qr": {
    "pairing_id": "uuid",
    "payload_url": "https://host/connect?pairing_id=uuid&code=one-time-code",
    "expires_at": "2026-05-13T10:05:00Z",
    "ttl_seconds": 300
  },
  "network": {
    "local_url": "http://192.168.1.10:8000",
    "tunnel_url": null,
    "https_enabled": false
  }
}
```

**DB**

New table `device_pairing_codes`: `pairing_id`, `family_id`, `purpose`, `code_hash`, `expires_at`, `used_at`, `created_at`, `created_by_user_id`.

**Family Rule**

Pairing rows are scoped to current family. Raw one-time codes are never stored, only hashes.

**Admin Rule**

Not admin-only for generating parent app connection metadata. Future device registration write actions may require admin.

**Required Tests**

TTL bounds; code hash stored but raw code not stored/logged; family isolation; expired codes rejected in future consume flow; response does not expose `.env` values.

### C12. Robot Room/Location Metadata - Phase 4

**Endpoints**

- `GET /api/robot/location`
- `POST /api/robot/location`

**Request Body**

```json
{
  "room_name": "Living room",
  "location_label": "Near bookshelf",
  "source": "parent",
  "confidence": 1.0
}
```

**Response Shape**

```json
{
  "ok": true,
  "location": {
    "family_id": "family-a",
    "room_name": "Living room",
    "location_label": "Near bookshelf",
    "source": "parent",
    "confidence": 1.0,
    "updated_at": "2026-05-13T10:00:00Z"
  }
}
```

**DB**

New table `robot_location_metadata`: `family_id`, `room_name`, `location_label`, `source`, `confidence`, `updated_at`, `updated_by_user_id`.

**Family Rule**

One current location row per family.

**Admin Rule**

Not admin-only.

**Required Tests**

Save/load; validation for string lengths and confidence range; family isolation; no dependency on robot firmware.

### C13. Parent <-> Bi Chat History - Phase 3

**Endpoints**

- `GET /api/conversations/parent`
- `POST /api/conversations/parent/messages`
- `GET /api/conversations/parent/{session_id}`

**Request Body**

```json
{
  "session_id": "optional-session-id",
  "role": "parent",
  "content": "Message text"
}
```

Allowed `role`: `parent`, `bi`.

**Response Shape**

```json
{
  "session": {
    "session_id": "uuid",
    "title": "Parent chat",
    "started_at": "2026-05-13T10:00:00Z",
    "ended_at": null,
    "message_count": 2
  },
  "messages": [
    {
      "message_id": "uuid",
      "role": "parent",
      "content": "Message text",
      "timestamp": "2026-05-13T10:00:00Z"
    }
  ]
}
```

**DB**

New tables:

- `parent_chat_sessions`: `session_id`, `family_id`, `user_id`, `title`, `started_at`, `ended_at`, `message_count`
- `parent_chat_messages`: `message_id`, `session_id`, `family_id`, `role`, `content`, `timestamp`

**Family Rule**

Parent chat is separate from child `conversations`/`turns` and always scoped by current family.

**Admin Rule**

Not admin-only.

**Required Tests**

List/create/detail; role validation; content length validation; cross-family isolation; existing `/api/conversations` child history unchanged.

### C14. Admin System Logs API - Phase 4

**Endpoint**

- `GET /api/admin/logs`

**Request Query**

```text
level=INFO
component=api_server
since=2026-05-13T00:00:00Z
limit=100
offset=0
```

**Response Shape**

```json
{
  "logs": [
    {
      "timestamp": "2026-05-13T10:00:00Z",
      "level": "INFO",
      "component": "api_server",
      "message": "FastAPI server started",
      "source": "application"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**DB**

No new table required for Phase 4 if reading sanitized application log output. If file parsing is too fragile, add `system_log_entries`: `log_id`, `timestamp`, `level`, `component`, `message_redacted`, `source`, `created_at`.

**Family Rule**

Admin logs are system-level and must not accept arbitrary `family_id` filters in Phase 4. Family data and child text must be redacted.

**Admin Rule**

Admin-only. Non-admin users receive 403.

**Required Tests**

Route registration; non-admin 403; admin 200; limit bounds; redaction of JWTs/secrets/child text patterns; no reading `.env`, runtime DB, or cache/model/media files.

## Success Criteria

- **SC-001**: Parent App Tier 2 mock features have documented backend endpoints and response shapes for all 14 required capabilities.
- **SC-002**: Phase 1 endpoints can be implemented without changing existing auth, conversation, event, or emotion contracts.
- **SC-003**: Every new persisted entity has a `family_id` scoping rule or an explicit reason why it is system/admin-only.
- **SC-004**: Every capability lists tests required before implementation can be considered done.
- **SC-005**: Report export, logs, notes, and chat history requirements explicitly prevent sensitive data from being logged.
- **SC-006**: Implementation phases are independently deliverable: Phase 1 monitoring, Phase 2 settings, Phase 3 reports/content/chat, Phase 4 device/admin metadata.

## Assumptions

- The frontend TODO paths from `frontend/parent_app/src/services/api.js` are preferred when compatible with backend naming.
- `GET /api/emotions/monthly` is included as an alias because the frontend TODO currently uses the plural path; the primary backend style remains `/api/emotion/monthly`.
- PDF export should avoid new third-party dependencies unless the user approves installing one later. A minimal standard-library PDF generator is acceptable for Phase 3.
- Child profile support is family-scoped, not globally shared.
- Parent-to-Bi chat history is a separate parent channel, not a replacement for protected child conversation storage.
- Admin logs expose sanitized operational messages only, not raw log files or secrets.

## Out of Scope

- No backend source implementation in this phase.
- No frontend changes in this phase.
- No firmware changes.
- No runtime database or log file changes.
- No git commit.
