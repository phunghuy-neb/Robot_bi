# SYSTEM_MAP.md - Robot Bi Current System Map

> Purpose: mô tả hệ thống Robot Bi hiện tại để human/AI hiểu nhanh project.
> This file is descriptive, not authoritative.
> PROJECT.md is the source of truth for rules, protected fixes, workflow, and constraints.
> This file must match the current repository state.
> Do not add planned features, future roadmap items, or unverified capabilities as current.
> Update this file only when features, modules, APIs, screens, firmware capabilities, database schema, runtime ownership, or architecture change.
> Do not update this file for pure bugfixes that do not change system behavior or structure.

## 1. Project Summary

Robot Bi is a Python/FastAPI AI tutor robot project with a voice conversation loop, Parent App web UI, Robot Display web UI, SQLite runtime storage, ChromaDB memory storage, and optional ESP32 motor firmware. The current source root is `src/`; static frontend files live under `frontend/`; firmware lives under `firmware/Robot_BI/`. Some modules are implemented and some placeholder files exist; verify a specific file before treating a capability as runtime-complete.

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
| Firmware | `firmware/Robot_BI/Robot_BI.ino` |
| Test command | `python tests/run_tests.py` |
| Sync generated agent docs | `python sync.py` |

## 4. Backend Module Map

| Folder | Current contents and responsibility |
|---|---|
| `src/ai/` | LLM streaming/fallback, prompts, and family persona settings; `language_detector.py` exists as a small placeholder file. |
| `src/api/` | FastAPI app assembly in `server.py` and route modules in `src/api/routers/`. |
| `src/audio/` | STT input, wake-word hook, speaker heuristics, TTS output, music state, cry detection, and pronunciation scoring; several small placeholder files exist. |
| `src/communication/` | In-memory video call manager and simulated robot-to-robot communication helpers. |
| `src/config/` | Placeholder config module files exist; runtime completeness not verified. |
| `src/display/` | Robot face state events and flashcard renderer; reward/sleep files exist as placeholders. |
| `src/education/` | Curriculum schedule, flashcard sessions, progress tracking, homework classification, and basic language tutor; grammar checker is a placeholder. |
| `src/emotion/` | Emotion analyzer, emotion journal, and emotion alert state. |
| `src/entertainment/` | Story engine, music library, word quiz, and voice quiz logic backed by local resources. |
| `src/infrastructure/` | Auth/JWT helpers, SQLite database helpers, logging setup, notifier, session state/naming, and task manager. |
| `src/living/` | Runtime-only Living State Engine for Bi's inner state; integrated into `src/main.py` text/voice loops and passed to LLM through internal `system_context`. |
| `src/memory/` | ChromaDB RAG manager plus smaller memory/progress placeholder or support files. |
| `src/motion/` | Motor controller with simulation/serial/WebSocket paths plus navigation, follow-me, and dock helper modules. |
| `src/safety/` | Safety filter for LLM/puppet text before TTS. |
| `src/vision/` | Camera stream module; face/fall/motion/smoke detector files exist as placeholders. |

## 5. API Router Map

| Router file | Current responsibility |
|---|---|
| `admin_router.py` | Admin family create/list/delete endpoints under `/api/admin/families` and sanitized admin system logs under `/api/admin/logs`. |
| `analytics_router.py` | Weekly/daily analytics and camera clip list/delete endpoints. |
| `auth_router.py` | Legacy PIN login/logout, username/password registration/login, JWT refresh/logout, account lookup, and password change routes. |
| `control_router.py` | Robot status, device connection QR metadata, robot room/location metadata, report export, events with advanced filters, parent event notes, child profiles, parent settings, chat logs, RAG memory CRUD/export, puppet text queue, tasks, and star counters. |
| `conversation_router.py` | Conversation list/detail/delete, homework conversation routes, and parent-to-Bi chat history routes. |
| `education_router.py` | Flashcard session routes, learning summary, vocabulary, and learning schedule routes. |
| `emotion_router.py` | Current-day, weekly, and monthly emotion summary routes. |
| `game_router.py` | Word quiz, voice quiz, game score routes, and Parent App radio/video/game metadata routes. |
| `motor_router.py` | Motor movement, joystick, dock/home, spin, and status routes. |
| `music_router.py` | Music play/stop/pause/next/previous/shuffle/repeat/volume/status/playlist/lullaby routes. |
| `ops_router.py` | Health check, Parent App root page, MJPEG camera stream, and tunnel helper code. |
| `persona_router.py` | Persona read/update routes. |
| `story_router.py` | Story list/tell/personalized/bedtime routes. |
| `streaming_router.py` | Event WebSocket, browser audio WebSocket, mom-talk start/stop/status, and mom audio WebSocket. |
| `video_call_router.py` | Video call start/end, contacts, and history routes. |
| `webrtc_router.py` | WebRTC camera offer and peer close routes mounted with `/api/webrtc`. |
| `wifi_router.py` | ESP32 motor registration, WiFi status, and WiFi credential forwarding routes. |

## 6. Frontend Structure

| Folder | Files |
|---|---|
| `frontend/parent_app/` | React + Vite SPA. Source in `src/`; build output in `dist/`; `package.json`, `vite.config.js`, `index.html` (Vite mount shell), `manifest.json`, `sw.js`, `icon-192.png`, `icon-512.png`. |
| `frontend/robot_display/` | `index.html`, `face.html`, `flashcard.html`, `.codex`. |

### Parent App — React + Vite SPA (spec 001-parent-app-redesign, implemented 2026-05-13)

`frontend/parent_app/` contains a React 18 + Vite 5 SPA serving as the parent-facing management interface.

**Navigation**: 5-tab sidebar (Trang chủ, Giám sát, Học tập, Nhật ký, Thêm) on desktop ≥768px; mobile bottom navigation bar (5 tabs) on smaller screens. Sidebar bottom order (locked): RobotStatusCard → UserCard → Cài đặt → Đăng xuất.

**Design system**: "Công nghệ ấm áp" — Be Vietnam Pro font, 16px body, 48px tap targets, WCAG AA contrast, card radius 22px, primary #2563eb.

**Settings overlay**: full-screen panel with Hồ sơ trẻ, Thông báo, Giờ hoạt động, Nội dung & An toàn, Kết nối thiết bị, Chế độ kỹ thuật (admin only).

**Tier 1 APIs active (real backend)**: auth (`/api/auth/login`, `/logout`, `/refresh`, `/me`), WebSocket robot status (`/ws?token=`), camera MJPEG (`/api/camera`), conversations (`/api/conversations`, `/{id}`), parent chat (`/api/conversations/parent`), events with filters (`/api/events`), parent event notes (`/api/events/{event_id}/notes`), reports (`/api/reports/export`), weekly analytics (`/api/analytics/weekly`), emotion today/monthly (`/api/emotion/today`, `/api/emotion/monthly`, `/api/emotions/monthly`), child profiles (`/api/children`), parent settings (`/api/settings/age-filter`, `/api/settings/time-limits`, `/api/settings/sleep`, `/api/settings/notifications`), daily usage (`/api/usage/today`), device connection QR metadata (`/api/device/connection-qr`), robot location (`/api/robot/location`), music (`/api/music/*`), quiz games (`/api/game/*`), content metadata (`/api/entertainment/radio`, `/api/entertainment/videos`, `/api/games/interactive`), education vocabulary/summary/schedule (`/api/education/*`), stories (`/api/stories`), tasks (`/api/tasks/*`), motor joystick/stop (`/api/motor/*`), puppet (`/api/puppet`), persona (`/api/persona`), admin families (`/api/admin/families`), admin logs (`/api/admin/logs`), mom-talk start/stop/WS (`/api/mom/*`).

**Tier 2 UI placeholders still awaiting frontend wiring**: all spec 002 backend APIs now exist for monthly emotion stats, parent event notes, advanced event filters, child profiles, age filter, daily time limits, sleep schedule, push notification settings, report export, content metadata, parent-Bi chat history, room/location tracking, QR device connection, and admin system logs.

**Source structure**:
```
src/
  main.jsx           — React entry point
  App.jsx            — Auth gate + tab routing + layout + WebSocket
  styles.css         — Design tokens, base styles, responsive layout
  services/api.js    — All API/WebSocket/auth behavior (Tier 1 real + Tier 2 mock)
  data/mockData.js   — Vietnamese mock data for Tier 2 features
  components/        — Sidebar, BottomNav, RobotStatusCard, UserCard,
                       SettingsOverlay, FeatureBadge, SectionState, Toast
  pages/             — LoginPage, HomePage, MonitorPage, LearningPage,
                       JournalPage, MorePage
```

`frontend/robot_display/index.html` contains the child-facing display UI with face modes and flashcard/reward/pronunciation display functions. `face.html` and `flashcard.html` are placeholder redirect-style pages.

## 7. Firmware

| File | Current responsibility |
|---|---|
| `firmware/Robot_BI/Robot_BI.ino` | ESP32 Arduino firmware for L298N motor pins, WiFi setup/persistence, WebSocket motor commands, server registration, and watchdog stop behavior. |

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
