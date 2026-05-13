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

- Wire the React Parent App mock adapters to the new Phase 1 and Phase 2 backend APIs when frontend work resumes. Continue spec 002 Phase 3 backend work: CSV/PDF report export, radio/video/game metadata APIs, and parent-Bi chat history.
- **Parent App React+Vite migration is complete**. Manual browser test remains recommended: login with real credentials, verify WebSocket status, and check each tab's API calls in Network tab. If backend serves Parent App via `ops_router.py` StaticFiles, point it to `frontend/parent_app/dist/` instead of the root `frontend/parent_app/`.
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
- `src/api/routers/emotion_router.py` (monthly emotion endpoints)
- `src/emotion/emotion_analyzer.py` (monthly aggregation)
- `src/infrastructure/database/db.py` (`parent_event_notes` schema and helpers)
- `src/infrastructure/database/db.py` (Phase 2 child/settings/usage/notification schema)
- `src/infrastructure/sessions/state.py` (advanced event query filters)
- `tests/run_tests.py` (Group 60 Phase 1 and Group 61 Phase 2 backend tests)
- `SYSTEM_MAP.md` (Section 6 updated to describe React+Vite implementation)
- `.claude/handoff.md`
