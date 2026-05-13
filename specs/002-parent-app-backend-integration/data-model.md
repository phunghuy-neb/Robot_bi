# Data Model: Parent App Backend Integration

**Feature**: 002-parent-app-backend-integration | **Date**: 2026-05-13

This model is proposed for future backend implementation. It does not modify the runtime database in this specification-only phase.

## Existing Tables Reused

| Table | Use |
|---|---|
| `families` | Existing family ownership root. |
| `users` | User identity, admin flag, and `family_name`. |
| `events` | Journal events, advanced filtering, report data source. |
| `conversations` | Existing child/robot conversation history and report data source. |
| `turns` | Existing child conversation detail and report data source. |
| `tasks` | Existing tasks/star data and report data source. |
| `learning_schedules` | Existing education schedule storage. |
| `game_scores` | Existing game score storage. |
| `emotion_logs` | Emotion analyzer records for monthly stats. |
| `emotion_journal` | Emotion journal records for weekly/monthly stats. |

## New Tables

### parent_event_notes

Stores parent notes attached to existing events.

```sql
note_id TEXT PRIMARY KEY,
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
event_id TEXT NOT NULL,
user_id TEXT NOT NULL,
note TEXT NOT NULL,
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL
```

Indexes:

- `idx_parent_event_notes_family_event(family_id, event_id)`
- `idx_parent_event_notes_family_updated(family_id, updated_at)`

Validation:

- `note` trimmed length 1-2000.
- `event_id` must match an event in the same family.

### child_profiles

Stores children associated with a family.

```sql
child_id TEXT PRIMARY KEY,
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
name TEXT NOT NULL,
birth_date TEXT,
grade TEXT,
avatar TEXT,
interests_json TEXT NOT NULL DEFAULT '[]',
notes TEXT,
is_active INTEGER NOT NULL DEFAULT 0,
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL
```

Indexes:

- `idx_child_profiles_family(family_id)`
- `idx_child_profiles_family_active(family_id, is_active)`

Validation:

- `name` length 1-80.
- `birth_date` ISO date when present.
- `interests_json` is an array of strings.
- Only one active child per family; enforce in service logic or with transaction.

### child_content_settings

Stores age/topic controls by family and optionally by child.

```sql
setting_id TEXT PRIMARY KEY,
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
child_id TEXT,
enabled INTEGER NOT NULL DEFAULT 0,
min_age INTEGER,
max_age INTEGER,
blocked_topics_json TEXT NOT NULL DEFAULT '[]',
allowed_topics_json TEXT NOT NULL DEFAULT '[]',
strict_mode INTEGER NOT NULL DEFAULT 1,
updated_at TEXT NOT NULL
```

Indexes:

- `idx_child_content_settings_family_child(family_id, child_id)`

Validation:

- `min_age` and `max_age` must be within 5-12 when present.
- `min_age <= max_age`.
- `child_id`, when present, must belong to the same family.

### interaction_limit_settings

Stores daily time limit preferences.

```sql
setting_id TEXT PRIMARY KEY,
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
child_id TEXT,
enabled INTEGER NOT NULL DEFAULT 0,
daily_limit_minutes INTEGER NOT NULL DEFAULT 60,
warning_minutes INTEGER NOT NULL DEFAULT 10,
reset_time TEXT NOT NULL DEFAULT '00:00',
updated_at TEXT NOT NULL
```

Indexes:

- `idx_interaction_limit_settings_family_child(family_id, child_id)`

Validation:

- `daily_limit_minutes` range 1-480.
- `warning_minutes` range 0-120 and not greater than `daily_limit_minutes`.
- `reset_time` format `HH:MM`.

### daily_interaction_usage

Tracks daily usage counters for limit display/enforcement.

```sql
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
child_id TEXT,
usage_date TEXT NOT NULL,
seconds_used INTEGER NOT NULL DEFAULT 0,
sessions_count INTEGER NOT NULL DEFAULT 0,
updated_at TEXT NOT NULL,
PRIMARY KEY (family_id, child_id, usage_date)
```

Validation:

- `seconds_used >= 0`.
- `sessions_count >= 0`.

### sleep_schedule_settings

Stores family sleep schedule settings.

```sql
family_id TEXT PRIMARY KEY REFERENCES families(family_id) ON DELETE CASCADE,
enabled INTEGER NOT NULL DEFAULT 0,
start_time TEXT NOT NULL DEFAULT '21:00',
end_time TEXT NOT NULL DEFAULT '06:30',
days_json TEXT NOT NULL DEFAULT '["mon","tue","wed","thu","fri","sat","sun"]',
timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
updated_at TEXT NOT NULL
```

Validation:

- `start_time` and `end_time` format `HH:MM`.
- `days_json` only contains `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`.
- Overnight schedules are valid.

### notification_settings

Stores family notification preferences.

```sql
family_id TEXT PRIMARY KEY REFERENCES families(family_id) ON DELETE CASCADE,
enabled INTEGER NOT NULL DEFAULT 1,
event_types_json TEXT NOT NULL DEFAULT '{}',
quiet_hours_json TEXT NOT NULL DEFAULT '{}',
channels_json TEXT NOT NULL DEFAULT '{}',
updated_at TEXT NOT NULL
```

Validation:

- Event type keys must be known event classes.
- Channel keys initially: `in_app`, `web_push`.

### push_subscriptions

Stores optional browser push subscription data.

```sql
subscription_id TEXT PRIMARY KEY,
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
user_id TEXT NOT NULL,
endpoint_hash TEXT NOT NULL,
subscription_json TEXT NOT NULL,
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL,
revoked_at TEXT
```

Indexes:

- `idx_push_subscriptions_family_user(family_id, user_id)`
- `idx_push_subscriptions_endpoint_hash(endpoint_hash)`

Security:

- Log only `subscription_id` and family/user IDs, never full endpoint or keys.

### report_exports

Optional audit table for report export metadata. The report file itself is generated on demand and is not stored.

```sql
export_id TEXT PRIMARY KEY,
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
user_id TEXT NOT NULL,
format TEXT NOT NULL,
start_date TEXT NOT NULL,
end_date TEXT NOT NULL,
sections_json TEXT NOT NULL,
created_at TEXT NOT NULL,
status TEXT NOT NULL
```

Validation:

- `format` in `csv`, `pdf`.
- Date range valid.

### content_items

Stores metadata for radio, videos, and interactive games.

```sql
content_id TEXT PRIMARY KEY,
family_id TEXT,
type TEXT NOT NULL,
title TEXT NOT NULL,
description TEXT,
source_url TEXT,
thumbnail_url TEXT,
age_min INTEGER,
age_max INTEGER,
language TEXT NOT NULL DEFAULT 'vi',
tags_json TEXT NOT NULL DEFAULT '[]',
enabled INTEGER NOT NULL DEFAULT 1,
sort_order INTEGER NOT NULL DEFAULT 0,
created_at TEXT NOT NULL,
updated_at TEXT NOT NULL
```

Indexes:

- `idx_content_items_type_enabled(type, enabled, sort_order)`
- `idx_content_items_family_type(family_id, type)`
- `idx_content_items_age(age_min, age_max)`

Rules:

- `family_id IS NULL` means global catalog row.
- Current-family rows may override or supplement global rows.
- Other-family rows are never returned.

### device_pairing_codes

Stores short-lived QR pairing records.

```sql
pairing_id TEXT PRIMARY KEY,
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
purpose TEXT NOT NULL,
code_hash TEXT NOT NULL,
expires_at TEXT NOT NULL,
used_at TEXT,
created_at TEXT NOT NULL,
created_by_user_id TEXT NOT NULL
```

Indexes:

- `idx_device_pairing_family_expires(family_id, expires_at)`

Security:

- Store only hash of one-time code.
- Raw code appears only in the immediate response payload.
- Never log raw code or QR payload URL.

### robot_location_metadata

Stores room/location metadata for the robot.

```sql
family_id TEXT PRIMARY KEY REFERENCES families(family_id) ON DELETE CASCADE,
room_name TEXT,
location_label TEXT,
source TEXT NOT NULL DEFAULT 'parent',
confidence REAL NOT NULL DEFAULT 1.0,
updated_at TEXT NOT NULL,
updated_by_user_id TEXT
```

Validation:

- `room_name` max 120 chars.
- `location_label` max 200 chars.
- `source` in `parent`, `robot`, `system`.
- `confidence` range 0.0-1.0.

### parent_chat_sessions

Stores parent-to-Bi chat sessions separately from child conversation sessions.

```sql
session_id TEXT PRIMARY KEY,
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
user_id TEXT NOT NULL,
title TEXT,
started_at TEXT NOT NULL,
ended_at TEXT,
message_count INTEGER NOT NULL DEFAULT 0
```

Indexes:

- `idx_parent_chat_sessions_family_started(family_id, started_at)`

### parent_chat_messages

Stores messages for parent-to-Bi chat sessions.

```sql
message_id TEXT PRIMARY KEY,
session_id TEXT NOT NULL REFERENCES parent_chat_sessions(session_id) ON DELETE CASCADE,
family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
role TEXT NOT NULL,
content TEXT NOT NULL,
timestamp TEXT NOT NULL
```

Indexes:

- `idx_parent_chat_messages_session_time(session_id, timestamp)`
- `idx_parent_chat_messages_family_time(family_id, timestamp)`

Validation:

- `role` in `parent`, `bi`.
- `content` length 1-4000.

## Tables Not Required

### Admin System Logs

No new table is required in Phase 4 if implementation reads sanitized application log output through a controlled service.

If log file parsing proves fragile, a future DB-backed `system_log_entries` table may be added:

```sql
log_id TEXT PRIMARY KEY,
timestamp TEXT NOT NULL,
level TEXT NOT NULL,
component TEXT NOT NULL,
message_redacted TEXT NOT NULL,
source TEXT NOT NULL,
created_at TEXT NOT NULL
```

This table must not store raw child text, parent notes, secrets, tokens, API keys, or environment values.

## Family Isolation Rules

- Every new family-owned table includes `family_id`.
- All endpoint writes use JWT-derived family only.
- `child_id` must be resolved through `child_profiles` with matching `family_id`.
- Content metadata returns global rows plus current-family rows only.
- Admin logs are system-level and admin-only; they do not expose arbitrary family selectors in Phase 4.

## Deletion and Cleanup

Future implementation of `delete_family_record()` should clean up the new family-owned tables:

- `parent_event_notes`
- `child_profiles`
- `child_content_settings`
- `interaction_limit_settings`
- `daily_interaction_usage`
- `sleep_schedule_settings`
- `notification_settings`
- `push_subscriptions`
- `report_exports`
- `content_items` rows where `family_id` matches
- `device_pairing_codes`
- `robot_location_metadata`
- `parent_chat_sessions`
- `parent_chat_messages`

Cleanup must use an allowlist, matching the current protected deletion pattern.
