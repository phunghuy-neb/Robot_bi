# Handoff - Robot Bi

> Current-state handoff only. Historical details belong in `changelog/`.

## Current State

- `PROJECT.md` is the source of truth for rules, protected fixes, workflow, and AI context policy.
- Current source root is `src/`; `src_brain/` is deprecated and must not be used.
- Main entry point: `src/main.py`.
- API server: `src/api/server.py`.
- Parent App: `frontend/parent_app/`.
- Robot Display: `frontend/robot_display/`.
- Firmware: `firmware/Robot_BI/Robot_BI.ino`.
- Runtime DB: `runtime/robot_bi.db`.
- Generated agent docs: `CLAUDE.md` and `AGENTS.md`, regenerated with `python sync.py`.

## Last Completed Task

- 2026-05-18: **AI engine overhaul (390/390 PASS)**. Fixed Gemini model name (`gemini-2.0-flash` in `config.json`). Extended fallback chain: Groq → Gemini → Cerebras → Sambanova → Cloudflare Workers AI. New API keys needed in `.env`: `CEREBRAS_API_KEY`, `SAMBANOVA_API_KEY`, `CLOUDFLARE_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`. Fixed emotional tone in `MAIN_SYSTEM_PROMPT` (no "Oa!" on sad inputs, listen before advising, no character-name carryover). Split `REFUSAL_RESPONSE` (safety filter) from `ERROR_RESPONSE` (connection errors) in `prompts.py`; synced `safety_filter._REFUSAL_RESPONSE` to match.

- 2026-05-14: **Goal 4 — wire Parent App mock adapters to backend APIs (390/390 PASS)**. `frontend/parent_app/src/services/api.js` rewritten with transform functions for 6 adapters: `getChildProfiles` (GET /api/children, child_id→id, age already computed by backend), `getRadioChannels` / `getVideoLessons` / `getInteractiveGames` (content_items schema, content_id→id, fallback to mock when backend has no seeded data), `getMonthlyEmotions` (GET /api/emotions/monthly, weekly count→percentage transform), `getSystemLogs` (GET /api/admin/logs, component→source). All six use mock fallback when backend returns empty or 403. BLOCKED adapters (`getRoomLocation`, `getParentChatHistory`) return null — no component renders their data. Save-button stubs in SettingsOverlay unchanged (show toast, no api.js call). Encoding artifacts cleaned. 390/390 PASS, `npm run build` passes (196KB JS, 25KB CSS).

- 2026-05-14: **Goal 3 — runtime hardening (390/390 PASS)**. `stopCamera()` now dispatches `bi:stopcamera` CustomEvent; `MonitorPage` listens and sets `camOn=false`. Motor forward/backward/spin capped at 5 000 ms in `motor_router.py`. Dashboard field mapping corrected: `loadTodaySummary` switched from `/api/status` to `/api/analytics/daily`; emotion reads `emotionData.dominant`; weekly stats now fall back to `conversations/hours/tasks_completed`.

- 2026-05-14: **Goal 2 — remaining test failures fixed (390/390 PASS)**. Updated 8 outdated test functions to check React source files instead of legacy `index.html` (React+Vite migration moved code). Added `stopCamera` / `stopAudioMonitor` exports to `api.js`; wired them in `handleTabChange` and `handleLogout` in `App.jsx`; added `beforeunload` cleanup handler; added `notif-banner` class to `Toast.jsx`; added music volume control with `level` field to `MorePage.jsx`; created `docs/kehoach.md` with outdated banner; fixed test 47.4 to use `sys.executable` instead of `python3` on Windows. All Goal 1 fixes preserved.

- 2026-05-13: **Parent App backend integration Phase 4 implemented (spec 002-parent-app-backend-integration)**. Added family-scoped QR device connection metadata (`/api/device/connection-qr`), robot room/location metadata (`/api/robot/location`), and admin-only sanitized system logs (`/api/admin/logs`). Added migration-safe SQLite tables for pairing metadata and robot location metadata; admin logs intentionally return controlled sanitized operational entries rather than parsing raw log files. Full `python tests/run_tests.py` ran with new Group 63 passing; remaining failures are pre-existing frontend/docs/Windows helper checks outside this backend Phase 4 scope.

- 2026-05-13: **Parent App backend integration Phase 3 implemented (spec 002-parent-app-backend-integration)**. Added family-scoped CSV/PDF report export (`/api/reports/export`), radio/video/game metadata APIs (`/api/entertainment/radio`, `/api/entertainment/videos`, `/api/games/interactive`), and separate parent-to-Bi chat history endpoints (`/api/conversations/parent*`). Added migration-safe SQLite tables for report export audit metadata, content metadata, and parent chat sessions/messages. Full `python tests/run_tests.py` ran with new Group 62 passing; remaining failures are pre-existing frontend/docs/Windows helper checks outside this backend Phase 3 scope.

- 2026-05-13: **Parent App backend integration Phase 2 implemented (spec 002-parent-app-backend-integration)**. Added family-scoped child profile CRUD/activation, age-based content settings, daily interaction limit storage with usage lookup, sleep schedule settings, and push notification settings storage. Added migration-safe SQLite tables and focused tests in `tests/run_tests.py`. Full `python tests/run_tests.py` ran with new Group 61 passing; remaining failures are pre-existing frontend/docs/Windows helper checks outside this backend Phase 2 scope.

- 2026-05-13: **Parent App backend integration Phase 1 implemented (spec 002-parent-app-backend-integration)**. Added family-scoped parent notes on events, advanced `/api/events` filters, and monthly emotion statistics endpoints (`/api/emotion/monthly`, `/api/emotions/monthly`). Added migration-safe `parent_event_notes` SQLite schema and focused tests in `tests/run_tests.py`. Full `python tests/run_tests.py` ran with new Group 60 passing; remaining failures are pre-existing frontend/docs/Windows helper checks outside this backend Phase 1 scope.

- 2026-05-13: **Parent App React + Vite migration — IMPLEMENTED (spec 001-parent-app-redesign, T001–T072)**. Full React + Vite SPA built under `frontend/parent_app/src/`. Legacy `index.html` replaced with Vite mount shell. `npm run build` passes (191KB JS, 20KB CSS). All Tier 1 backend APIs preserved in `src/services/api.js`. Tier 2 features use mock data with badges. 5-tab navigation, sidebar, settings overlay, admin section, and all 5 pages implemented. SYSTEM_MAP.md updated.

- 2026-05-13: **Parent App UI Redesign — spec artifacts updated for React + Vite target (spec 001-parent-app-redesign)**. All spec files updated. SYSTEM_MAP.md was reverted then correctly updated after implementation.

- 2026-05-13: AI context and instruction docs were normalized so PROJECT remains authoritative, SYSTEM_MAP is descriptive only, Spec Kit is conditional, and generated agent docs sync from PROJECT.

## Known Issues

- Wake-word custom `bi_oi` model is not confirmed; current repo contains dev/test wake-word paths.
- Cloudflare quick tunnel URL may change after restart unless a named tunnel is configured.
- YAMNet TFLite support depends on optional runtime dependencies.
- Camera, browser audio, mobile behavior, and motor hardware still require real-device verification.

## Next Recommended Action

- **Manual browser test recommended**: login with real credentials, verify WebSocket status, open Settings overlay (child profiles), open More tab (radio/video/games), open Journal tab (emotion chart), open Admin panel (system logs). Check Network tab that calls hit real backend, not mock.
- Seed content data in SQLite (`content_items` table) if radio/video/game sections show mock data — backend returns empty array when no rows exist, triggering mock fallback.
- Remaining BLOCKED items: `getRoomLocation` (no component renders it), `getParentChatHistory` (LearningPage shows coming-soon), SettingsOverlay save buttons (show toast, backend endpoints exist but buttons don't call them yet).
- If backend serves Parent App via `ops_router.py` StaticFiles, point it to `frontend/parent_app/dist/` instead of the root `frontend/parent_app/`.
- For other code changes, read `PROJECT.md`, this handoff, and relevant source files.
- For large feature/API/schema/cross-module work, use Spec Kit or write a clear plan first.

## Current Test Command

```bash
python tests/run_tests.py
```

## Files Recently Touched

- `frontend/parent_app/index.html` (replaced legacy 4000-line HTML with Vite mount shell)
- `frontend/parent_app/package.json` (new — React 18 + Vite 5)
- `frontend/parent_app/vite.config.js` (new)
- `frontend/parent_app/src/main.jsx` (new — React entry)
- `frontend/parent_app/src/App.jsx` (new — auth gate + routing + layout)
- `frontend/parent_app/src/styles.css` (new — full design system)
- `frontend/parent_app/src/services/api.js` (new — all Tier 1 + Tier 2 mock adapters)
- `frontend/parent_app/src/data/mockData.js` (new — Vietnamese mock data)
- `frontend/parent_app/src/components/` (new — Sidebar, BottomNav, RobotStatusCard, UserCard, SettingsOverlay, FeatureBadge, SectionState, Toast)
- `frontend/parent_app/src/pages/` (new — LoginPage, HomePage, MonitorPage, LearningPage, JournalPage, MorePage)
- `frontend/parent_app/dist/` (build output — not git-tracked)
- `src/api/routers/control_router.py` (Phase 1 event filters and parent event note endpoints)
- `src/api/routers/control_router.py` (Phase 2 child profiles and parent settings endpoints)
- `src/api/routers/control_router.py` (Phase 3 report export endpoint)
- `src/api/routers/control_router.py` (Phase 4 device QR and robot location endpoints)
- `src/api/routers/admin_router.py` (Phase 4 sanitized admin logs endpoint)
- `src/api/routers/conversation_router.py` (Phase 3 parent-to-Bi chat history endpoints)
- `src/api/routers/game_router.py` (Phase 3 radio/video/game metadata endpoints)
- `src/api/routers/emotion_router.py` (monthly emotion endpoints)
- `src/emotion/emotion_analyzer.py` (monthly aggregation)
- `src/infrastructure/database/db.py` (`parent_event_notes` schema and helpers)
- `src/infrastructure/database/db.py` (Phase 2 child/settings/usage/notification schema)
- `src/infrastructure/database/db.py` (Phase 3 report/content/parent-chat schema)
- `src/infrastructure/database/db.py` (Phase 4 device pairing and robot location schema)
- `src/infrastructure/sessions/state.py` (advanced event query filters)
- `tests/run_tests.py` (Groups 60-63 backend tests for spec 002 phases 1-4)
- `SYSTEM_MAP.md` (Section 6 updated to describe React+Vite implementation)
- `.claude/handoff.md`
