# SYSTEM_MAP.md - Robot Bi Current System Map

> Purpose: mô tả hệ thống Robot Bi hiện tại để human/AI hiểu nhanh project.
> This file is descriptive, not authoritative.
> PROJECT.md is the source of truth for rules, protected fixes, workflow, and constraints.
> This file must match the current repository state.
> Do not add planned features, future roadmap items, or unverified capabilities as current.
> Update this file only when features, modules, APIs, screens, firmware capabilities, database schema, runtime ownership, or architecture change.
> Do not update this file for pure bugfixes that do not change system behavior or structure.

## 1. Project Summary

Robot Bi is a Python/FastAPI AI tutor robot project with a voice conversation loop, Parent App web UI, Robot Display web UI, SQLite runtime storage, ChromaDB memory storage, and optional ESP32 firmware. The current local hardware profile is one speaker and two INMP441 microphones connected to an ESP32-S3, with no camera connected. The current source root is `src/`; static frontend files live under `frontend/`; firmware lives under `firmware/`.

## 2. Source of Truth Files

| File | Role |
|---|---|
| `PROJECT.md` | Rules, protected fixes, workflow, constraints, and AI context policy. |
| `SYSTEM_MAP.md` | Descriptive map of current repository structure and capabilities. |
| `.claude/handoff.md` | Latest current-state handoff for AI sessions. |
| `CLAUDE.md` | Generated instructions for Claude Code. Do not edit manually. |
| `AGENTS.md` | Generated instructions for Codex CLI. Do not edit manually. |

## 3. Current Entry Points

| Entry point | Path |
|---|---|
| Main app | `src/main.py` |
| API server module | `src/api/server.py` |
| Parent App | `frontend/parent_app/` (React+Vite SPA — Vite shell at `index.html`, source in `src/`, build in `dist/`) |
| Robot Display | `frontend/robot_display/index.html` |
| Motor firmware | `firmware/Robot_BI/Robot_BI.ino` |
| ESP32-S3 audio hardware test | `firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino` |
| ESP32-S3 speaker-only test | `firmware/ESP32S3_Speaker_Test/ESP32S3_Speaker_Test.ino` |
| Test command | `python tests/run_tests.py` |
| Sync generated agent docs | `python sync.py` |

## 4. Backend Module Map

| Folder | Current contents and responsibility |
|---|---|
| `src/ai/` | LLM streaming/fallback, prompts, and family persona settings; `language_detector.py` exists as a small placeholder file. |
| `src/api/` | FastAPI app assembly in `server.py` and route modules in `src/api/routers/`. |
| `src/audio/` | STT input, callback/native-rate microphone utilities, wake-word hook, TTS output, music state, separate-mic cry detection, and pronunciation scoring. `output/mouth_tts.py` defaults to edge-tts with a pyttsx3 fallback; `TTS_OFFLINE=true` (or `TTS_ENGINE=pyttsx3`) forces fully-offline pyttsx3, skipping edge-tts (does not change the protected playback/streaming/channel logic). `input/transcribe_file.py` transcribes uploaded audio files (no microphone/sounddevice import). TTS chunk files are written to a dedicated temp dir (`mouth_tts.CHUNK_DIR`), not the CWD. |
| `src/communication/` | In-memory video call manager and simulated robot-to-robot communication helpers. |
| `src/config/` | Placeholder config module files exist; runtime completeness not verified. |
| `src/display/` | Robot face state events and flashcard renderer; reward/sleep files exist as placeholders. |
| `src/education/` | Curriculum schedule, flashcard sessions, progress tracking, homework classification, and basic language tutor; grammar checker is a placeholder. |
| `src/emotion/` | Emotion analyzer, emotion journal, and emotion alert state. |
| `src/entertainment/` | Story engine, music library, word quiz, and voice quiz logic backed by local resources. `youtube_lessons.py` fetches video lessons from a GLOBAL allowlist of educational YouTube channels (`resources/youtube_channels.json`, admin-editable) PLUS per-family channels (`youtube_channels` table, parent-managed) via YouTube Data API; off unless `YOUTUBE_API_KEY` is set, degrades to DB content. `available` (has key) is decoupled from `enabled` (has global channels) so family channels still work when the global allowlist is empty. Video titles are filtered through SafetyFilter — clips with a blocked title are dropped. |
| `src/knowledge/` | `knowledge_client.py` — shared client for kid-safe external public APIs (no-key except NASA APOD which falls back to DEMO_KEY). Shared HTTP+timeout, TTL cache, and SafetyFilter on text output; never raises (errors → `ok:false`). Backs `knowledge_router.py`. Also exposes `radio_search()` (radio-browser.info) used by the admin-only `/api/admin/radio/search` helper — returns curation candidates (names filtered through SafetyFilter); admins add chosen stations via `/api/admin/content`. |
| `src/infrastructure/` | Auth/JWT helpers, SQLite database helpers, logging setup, notifier, session state/naming, and task manager. |
| `src/living/` | Runtime-only Stage 1 living layer: state machine, micro moments, and audio-first proactive prompts. A recognized interaction creates a short recent-presence window; optional camera events may extend it. |
| `src/memory/` | ChromaDB RAG manager plus smaller memory/progress placeholder or support files. Every op is family-scoped with an IDOR ownership check on mutate; the `_MAX_MEMORIES` cap is enforced on ALL add paths (auto + manual) via `_prune_to_capacity`, which evicts the OLDEST entries by timestamp; manual facts are whitespace-collapsed before storage to defuse multi-line prompt injection. |
| `src/motion/` | Motor controller with simulation/serial/WebSocket paths plus navigation, follow-me, and dock helper modules. `MotorController._send` fast-fails (no inline reconnect holding the lock — a `stop` is never starved); `forward/backward/spin` clamp duration centrally to `_MAX_DURATION_MS` (5 s) so all callers share the physical safety cap. |
| `src/safety/` | Safety filter for LLM/puppet text before TTS. `safety_filter.py` keeps its 3 hardcoded layers (topic classifier + blacklist + sentence cap) and ADDS an admin-configurable GLOBAL layer (`resources/safety_config.json`): extra blocklist words, extra blocked topics (refusal), default age/time/sleep policy, plus an in-memory block-monitoring buffer (counts + recent triggers, no child text stored). Module-level config is shared across all SafetyFilter instances and reloads on admin save without restart. |
| `src/vision/` | Optional camera stream module, disabled by default with `CAMERA_ENABLED=false`; current machine has no camera. |

## 5. API Router Map

| Router file | Current responsibility |
|---|---|
| `admin_router.py` | Admin family create/list/delete under `/api/admin/families`, sanitized system logs under `/api/admin/logs`, and user account management under `/api/admin/users` (list, lock/unlock, grant/revoke admin, reset password, delete — all `require_admin`, with self-action guards), config under `/api/admin/config/*` (view/set/clear/test PUBLIC API keys, view/set feature toggles) backed by `src/config/env_admin.py` — whitelist-only, never exposes LLM/JWT secrets — the GLOBAL YouTube allowlist under `/api/admin/youtube/channels` (list/add/delete; writes `resources/youtube_channels.json` + reloads singleton), GLOBAL child-safety under `/api/admin/safety/*` (config/blocklist/topics/policy/stats[/reset] — writes `resources/safety_config.json` + live-reloads SafetyFilter), GLOBAL content metadata under `/api/admin/content` (radio/video/game CRUD on `content_items`, family_id NULL = visible to all; Admin Content UI has presets for in-app Word Quiz and Voice Quiz), an overview dashboard under `/api/admin/stats` (user/family/exam/content/channel/safety counts), and the GLOBAL default persona under `/api/admin/persona` (name/gender/voice/language/personality that unconfigured families inherit), and a Radio Browser curation helper under `/api/admin/radio/search`; all `require_admin`. |
| `analytics_router.py` | Weekly/daily analytics and camera clip list/delete endpoints. |
| `auth_router.py` | Legacy PIN login/logout, username/password registration/login, JWT refresh/logout, account lookup, and password change routes. Refresh is per-IP rate-limited (counter resets on success); replaying an already-rotated refresh token triggers reuse-detection (`rotate_refresh_token` revokes ALL of the user's tokens + bumps token_version). JWT now carries a `role` claim (`owner`/`parent`/`child`); `/api/auth/me` and `/auth/login/v2` return `role` (+ family permissions on `me`). Child login: `GET /api/auth/child-profiles?family=` (public — id/name/avatar only) and `POST /api/auth/child-login` (`{family, child_profile_id, pin}` → JWT role=child, rate-limited via `login_attempts` key `child:{family}:{child_id}`). |
| `control_router.py` | Robot status, device connection QR metadata, robot room/location metadata, report export, events with advanced filters, parent event notes, child profiles, parent settings (age filter / time limits / sleep — their defaults for unconfigured families come from the admin GLOBAL safety policy), chat logs, RAG memory CRUD/export, special memories (`/api/memories/special` — Stage 2: structured family-scoped birthdays/milestones/favorites, also seeded into RAG so Bi recalls them; list flags `due_today` for date matches; `POST /api/memories/special/remind-due` writes idempotent unread `special_memory_due` events for today's matches), puppet text queue, tasks, and star counters. CSV report export neutralizes spreadsheet formula injection. The settings-mutation routes (age-filter / time-limits / sleep) are gated by `require_role('owner','parent')` so a child account cannot change parental controls even by calling the API directly. |
| `conversation_router.py` | Conversation list/detail/delete, homework conversation routes, and parent-to-Bi chat history routes. |
| `education_router.py` | Flashcard session routes, learning summary, vocabulary, and learning schedule routes. |
| `emotion_router.py` | Current-day, weekly, and monthly emotion summary routes. |
| `game_router.py` | Word quiz, voice quiz, game score routes, and Parent App radio/video/game metadata routes. `/api/games/interactive` metadata is actionable in Parent App: `/api/game/word-quiz/start` and `/api/game/voice-quiz/start` open an in-app modal; external URLs open in a new tab. `/api/entertainment/videos` merges live videos from the GLOBAL allowlist + the family's own channels into the DB content. Per-family channel management under `/api/entertainment/youtube/channels` (list/add/delete, family-scoped, max 30/family, upsert on duplicate). |
| `knowledge_router.py` | Read-only `/api/knowledge/*` (+ `/api/entertainment/jokes`) lookups over external public APIs — gated by the `KNOWLEDGE_ENABLED` admin toggle (default on; off → 503) — dictionary, country, number/math, trivia, books/gutenberg/poem/wiki, weather/ISS/APOD, animal & fun facts, jokes (safe-mode), Pokémon/Disney. Auth-gated; degrades to `ok:false` on source error. |
| `exam_router.py` | Learning Hub exams under `/api/learning/*`: subjects/tracks, exam list/detail (answers hidden), MCQ + TOEIC S&W grading, sessions, TOEIC Speaking via real server-side audio (`POST .../submit-speaking-audio` — multipart clips per question → faster-whisper STT in `audio/input/transcribe_file.py` → graded as transcripts; JSON `/submit-speaking` transcript path kept as fallback), custom exams (`POST /api/learning/exams/custom` — parent = family-scoped, admin `is_global` = global; `DELETE` with owner/admin guard), and admin generate/review/assemble + `GET /api/learning/admin/papers`. Exam papers are family-isolated (`family_id` NULL = global). LLM grading feedback/tips are run through SafetyFilter before reaching the child. |
| `eval_router.py` | `POST /api/eval/chat` — raw LLM eval over the 4 roles (no child SafetyFilter); **admin-only** (`is_user_admin`), used for prompt comparison/testing, not child-facing. |
| `motor_router.py` | Motor movement, joystick, dock/home, spin, and status routes. |
| `music_router.py` | Music play/stop/pause/next/previous/shuffle/repeat/volume/status/playlist/lullaby routes. |
| `ops_router.py` | Health check, Parent App root page, MJPEG camera stream, and tunnel helper code. |
| `persona_router.py` | Per-family persona read/update routes. Families without their own persona inherit the admin GLOBAL default (`PersonaManager` family key `__global__`). |
| `story_router.py` | Story list/tell/personalized/bedtime routes. |
| `streaming_router.py` | Event WebSocket, browser audio WebSocket, mom-talk start/stop/status, and mom audio WebSocket. |
| `video_call_router.py` | Video call start/end, contacts, and history routes. |
| `webrtc_router.py` | WebRTC camera offer and peer close routes mounted with `/api/webrtc`. |
| `wifi_router.py` | ESP32 motor registration, WiFi status, and WiFi credential forwarding routes. |
| `family_router.py` | Family roles & permissions (US7). Owner-only (`require_role('owner')`, scope from JWT family): `POST /api/family/create` (caller→owner), `GET /api/family/members`, `POST /api/family/members/add` (add a registered adult by username + role; blocks users already in another family), `POST /api/family/members/child` (create a child account from an existing child profile + PIN, 1↔1), `PUT /api/family/members/{id}/role`, `DELETE /api/family/members/{id}` (blocks self-delete + last owner), `GET/PUT /api/family/permissions` (granular `child_can_*`). |

## 6. Frontend Structure

| Folder | Files |
|---|---|
| `frontend/parent_app/` | React + Vite SPA. Source in `src/`; build output in `dist/`; `package.json`, `vite.config.js`, `index.html` (Vite mount shell), `manifest.json`, `sw.js`, `icon-192.png`, `icon-512.png`. |
| `frontend/robot_display/` | `index.html`, `face.html`, `flashcard.html`, `.codex`. |

### Parent App — React + Vite SPA (spec 001-parent-app-redesign, implemented 2026-05-13)

`frontend/parent_app/` contains a React 18 + Vite 5 SPA serving as the parent-facing management interface.

**Navigation**: 6-tab sidebar (Trang chủ, Giám sát, Theo dõi học tập, Học tập, Nhật ký, Thêm) on desktop ≥768px; mobile bottom navigation bar (6 tabs) on smaller screens. Tabs are **role-filtered**: owner/parent see all; a child account sees only Học tập + Thêm, plus Giám sát/Nhật ký if the owner enabled those in family permissions. Sidebar bottom order (locked): RobotStatusCard → UserCard → Cài đặt → Đăng xuất.

**Design system**: "Công nghệ ấm áp" — Be Vietnam Pro font, 16px body, 48px tap targets, WCAG AA contrast, card radius 22px, primary #2563eb.

**Settings overlay**: full-screen panel with Hồ sơ trẻ, Thông báo, Giờ hoạt động, Nội dung & An toàn, Kết nối thiết bị, Chế độ kỹ thuật (admin only).

**Tier 1 APIs active (real backend)**: auth (`/api/auth/login`, `/logout`, `/refresh`, `/me`), WebSocket robot status (`/ws?token=`), camera MJPEG (`/api/camera`), conversations (`/api/conversations`, `/{id}`), parent chat (`/api/conversations/parent`), events with filters (`/api/events`), parent event notes (`/api/events/{event_id}/notes`), reports (`/api/reports/export`), weekly analytics (`/api/analytics/weekly`), emotion today/monthly (`/api/emotion/today`, `/api/emotion/monthly`, `/api/emotions/monthly`), child profiles (`/api/children`), special memories (`/api/memories/special`, `/api/memories/special/remind-due`), parent settings (`/api/settings/age-filter`, `/api/settings/time-limits`, `/api/settings/sleep`, `/api/settings/notifications`), daily usage (`/api/usage/today`), device connection QR metadata (`/api/device/connection-qr`), robot location (`/api/robot/location`), music (`/api/music/*`), quiz games (`/api/game/*`), content metadata (`/api/entertainment/radio`, `/api/entertainment/videos`, `/api/games/interactive`), family YouTube channels (`/api/entertainment/youtube/channels`), admin global YouTube allowlist (`/api/admin/youtube/channels`), education vocabulary/summary/schedule (`/api/education/*`), stories (`/api/stories`), tasks (`/api/tasks/*`), motor joystick/stop (`/api/motor/*`), puppet (`/api/puppet`), persona (`/api/persona`), admin families (`/api/admin/families`), admin logs (`/api/admin/logs`), mom-talk start/stop/WS (`/api/mom/*`).

**Parent App content UI**: `MorePage` shows backend radio/video/game content. Word Quiz and Voice Quiz game metadata open a playable in-app modal (Voice Quiz accepts typed answers when mic/loa hardware is unavailable); external game URLs open in a new tab. Admin Content has game presets for these in-app modes.

**Parent App monitor UI**: `MonitorPage` groups Camera, mom-talk, motor controls, and recent events into collapsible sections. Weekly analytics remain on HomePage to avoid duplicate weekly-report content in the monitor view.

**Parent App journal/profile UI**: `JournalPage` has real client-side advanced conversation filters (search, minimum turns, sort), the "Trò chuyện" tab excludes homework sessions, and conversation detail playback uses browser `speechSynthesis` with stop/highlight controls. `SpecialMemories` can write today's due memories into the family event journal as idempotent `special_memory_due` events. The sidebar user card opens a real child-profile picker backed by `/api/children` and links to Settings for profile management.

**Remaining visible device-backed validation**: Camera, mom-talk audio, motor movement, and other hardware views can be opened in the UI but still need real devices for end-to-end validation.

**Source structure**:
```
src/
  main.jsx           — React entry point
  App.jsx            — Auth gate + tab routing + layout + WebSocket
                       (is_admin login → Admin UI instead of the parent tabs);
                       parent users can select the active child profile locally.
                       Role-aware: filters visible tabs + hides settings sections
                       for a child account based on family permissions
  pages/admin/       — AdminApp (sidebar shell, admin-only) + 9 sections:
                       UsersAdminPage, ApiKeysPage, ExamsAdminPage,
                       YouTubeAdminPage, SafetyAdminPage, PersonaAdminPage,
                       ContentAdminPage, LogsAdminPage, StatsAdminPage
  styles.css         — Design tokens, base styles, responsive layout
  services/api.js    — All API/WebSocket/auth behavior; radio/video/games/emotions return real backend data (empty when none) — no mock fallback. Knowledge explorer via knowledgeQuery(); in-app Word Quiz/Voice Quiz helpers back MorePage. WiFi (get/addWifi), family roles (createFamily/members/permissions), and child login (getChildProfilesPublic/childLogin) helpers; login/session expose role + permissions.
  data/mockData.js   — legacy Vietnamese mock data (no longer used as a runtime fallback)
  components/        — Sidebar, BottomNav (both role-filter tabs), RobotStatusCard,
                       UserCard, SettingsOverlay (WiFi section; hides parent-only
                       sections for child), FamilyMembers (owner-only: members +
                       child accounts + permission toggles), CollapsibleSection,
                       admin/Toggle, SpecialMemories, FeatureBadge, SectionState, Toast
  pages/             — LoginPage (parent username/pw + "child login" by family code →
                       profile grid → PIN), HomePage, MonitorPage (collapsible sections),
                       LearningPage,
                       LearningHubPage (học kiểu Duolingo: module en/math/science,
                       XP, streak, quiz, TOEIC S&W), JournalPage, MorePage
```

`frontend/robot_display/index.html` contains the child-facing display UI with face modes and flashcard/reward/pronunciation display functions. `face.html` and `flashcard.html` are placeholder redirect-style pages.

## 7. Firmware

| File | Current responsibility |
|---|---|
| `firmware/Robot_BI/Robot_BI.ino` | ESP32 Arduino firmware for L298N motor pins, WiFi setup/persistence, WebSocket motor commands, server registration, and watchdog stop behavior. |
| `firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino` | Standalone ESP32-S3 N16R8 hardware test for two INMP441 microphones and a MAX98357A speaker. Uses beep cues, records 5 seconds of stereo audio to PSRAM, then plays the left and right channels separately without live loopback. |
| `firmware/ESP32S3_Speaker_Test/ESP32S3_Speaker_Test.ino` | Standalone MAX98357A test with no microphones or PSRAM. Repeats counted tones and a rising frequency sweep on BCLK GPIO4, LRC GPIO5, and DIN GPIO7. |

Specific firmware behavior should be verified in the `.ino` file before changes.

## 8. Resources

| Folder | Current resource files |
|---|---|
| `resources/flashcards/english/` | `animals.json`, `colors.json`, `numbers.json`, `school_items.json`. |
| `resources/flashcards/math/` | `addition.json`, `shapes.json`. |
| `resources/flashcards/geography/`, `history/`, `science/` | `.gitkeep` placeholders only. |
| `resources/games/` | `voice_riddles.json`, `word_quiz_easy.json`, `word_quiz_medium.json`. |
| `resources/music/english/` | `playlist.json`. |
| `resources/music/lullabies/` | `playlist.json`. |
| `resources/music/vietnamese/` | `playlist.json`. |
| `resources/stories/bedtime/` | `ru_ngu.json`. |
| `resources/stories/fables/` | `ngu_ngon.json`. |
| `resources/stories/fairy_tales/` | `co_tich.json`. |

## 9. Runtime Data

Current runtime artifact locations include:

- `runtime/robot_bi.db`
- SQLite runtime schema includes family-scoped `parent_event_notes` for parent annotations on events.
- SQLite runtime schema includes Parent App settings tables for child profiles, age/content filters, daily interaction limits and usage, sleep schedules, notification settings, and push subscriptions.
- SQLite runtime schema includes Parent App Phase 3 tables for report export audit metadata, radio/video/game content metadata, and parent-to-Bi chat history.
- SQLite runtime schema includes Parent App Phase 4 tables for device pairing metadata and robot location metadata. Admin logs are a sanitized API response and do not read raw log files.
- SQLite runtime schema includes the `youtube_channels` table (per-family approved YouTube channels: `family_id`, `channel_id`, `label`, `language`, `age_min`, `age_max`, `tags_json`, unique per family+channel). The global allowlist stays in `resources/youtube_channels.json`.
- SQLite runtime schema includes the `special_memories` table (Stage 2 — per-family structured memories: `memory_id`, `family_id`, `kind`, `title`, `memory_date`, `note`, `created_at`). Due special-memory reminders are stored as `events.type='special_memory_due'` with a per-family/per-memory/per-day `import_key` so repeated reminders do not duplicate rows.
- Global child-safety config lives in `resources/youtube_channels.json`'s sibling `resources/safety_config.json` (admin blocklist words, blocked topics, default age/time/sleep policy) — not in SQLite. Safety block monitoring is in-memory only.
- SQLite `users` table carries a `role` column (`owner`/`parent`/`child`, default `parent`) and a nullable `child_profile_id` (set only for child accounts, 1↔1 with a `child_profiles` row). A child account's login credential is a PIN hashed with Argon2 in `password_hash`. `role` is separate from the system `is_admin` flag.
- SQLite runtime schema includes the `family_permissions` table (per-family, keyed by `family_name`): `child_can_monitor`, `child_can_journal`, `child_can_notifications`, `child_can_sleep`, `child_can_safety`, `child_can_device`, `child_can_members` (all default 0 = hidden from child). Owner edits via `/api/family/permissions`.
- `delete_family_record` purges ALL family-scoped tables (incl. `special_memories`, `youtube_channels`, `exam_sessions`, `exam_papers`, `question_bank`, `learning_progress`, `learning_streaks`, and `family_permissions` keyed by `family_name`) so a reused `family_id` can't inherit a deleted family's data.
- The WebSocket broadcaster (`state.ConnectionManager.broadcast`) is fail-closed: an event without a resolvable `family_id` is dropped, and clients are keyed by the WebSocket object (not `id()`); connection family is bound from the JWT claim only.
- `runtime/chroma_db/`
- `runtime/.hf_cache/`
- `runtime/vision_data/`
- `logs/`

These are runtime artifacts and should not be read or edited by default.

## 10. Tests and Verification

| Item | Path or command |
|---|---|
| Offline regression suite | `tests/run_tests.py` |
| Test command | `python tests/run_tests.py` |

Do not infer a current pass count from this file.

## 11. Deprecated Paths

- `src_brain/` is deprecated.
- Current source root is `src/`.
- Do not create or import from `src_brain/`.
