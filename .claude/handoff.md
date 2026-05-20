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

- 2026-05-20: **Sprint 0.2 — Child Safety Foundation (4 new modules + main.py integration + 37 tests)**. 430/431 PASS (28.9 pre-existing, unrelated):
  - `src/safety/vi_normalize.py` — strip Vietnamese diacritics for fuzzy matching (no external deps)
  - `src/safety/pii_filter.py` — 8 PII types (phone/email/CCCD/address/school/password/financial/fullname), dual-pattern (có/không dấu), gentle redirect
  - `src/safety/emotion_risk_detector.py` — HIGH/MEDIUM/LOW risk; HIGH overrides LLM + logs event; MEDIUM comforts + logs; LOW passes through
  - `src/safety/manipulation_guard.py` — LLM output check (secret-keeping, dependency, parent replacement, guilt-trip) + user input check (grooming signals, secret requests, parent replacement)
  - `src/main.py` — 6 targeted edits: imports, `__init__`, TEXT mode input checks, TEXT mode output check, VOICE mode input checks, VOICE mode output check
  - `tests/run_tests.py` — Group 65 (37 tests): PII (10) + EmotionRisk (11) + ManipulationGuard (12) + imports/integration (4)
  - Pipeline: user_text → PII check → EmotionRisk check → ManipulationGuard input → RAG → LLM stream → SafetyFilter + ManipulationGuard output → TTS
  - Commits: `1ba66ec` (code), `12113d2` (docs)
  - Docs updated: `STATUS_MAP.md` v1.1, `BACKLOG_Robot_Bi_v2.md` v2.3, `SRS_Robot_Bi_v2.md` v2.3

- 2026-05-20: **Sprint 0.1 — Sync docs to code reality (docs-only, no code changed, no tests needed)**. 4 tasks:
  - Task 0.1.1: `PROJECT.md` updated — 5-provider LLM chain (Cerebras→Groq→Sambanova→Gemini→Cloudflare), RAG threshold 0.62, edge-tts internet requirement, wake word disabled by default, firmware stubs flagged, Parent App path corrected.
  - Task 0.1.2: Docs drift fixed — `ARCHITECTURE.md` LLM chain corrected, `SRS_Robot_Bi_v2.md` fallback section updated, `prompts.py` stale comment fixed.
  - Task 0.1.3: `BACKLOG_Robot_Bi_v2.md` v2.2 — LLM row reflects 5-provider chain, RAG 0.50→0.62, edge-tts internet note, wake word status note.
  - Task 0.1.4: `docs/STATUS_MAP.md` created — 93-item feature reality map (🟢/🟡/🔴/⚪) across 7 domains, critical gaps section.
  - `CLAUDE.md` + `AGENTS.md` regenerated via `python sync.py`. Commit: `479d850`.

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

- Wake word **disabled by default** (`WAKEWORD_ENABLED=false`). Uses `faster-whisper tiny` fuzzy match when enabled — not a trained model.
- `edge-tts` (primary TTS) **requires internet** — not fully offline.
- ESP32-S3 (audio board) has **no firmware** — INMP441 + MAX98357 hardware is silent.
- `follow_me.py`, `dock_charger.py`, `face_recognizer.py`, `fall_detector.py` are **stubs** — no real logic.
- Motor firmware has **hardcoded IP** `192.168.40.107:8443` — must change per deployment.
- Cloudflare quick tunnel URL may change after restart unless a named tunnel is configured.
- YAMNet TFLite support depends on optional runtime dependencies.
- Parent App: radio/videos/games/logs use mock fallbacks; 4 saveSettings() stubs return null.
- Test 28.9: `docs/kehoach.md` missing — pre-existing, unrelated to Sprint 0.2.
- See `docs/STATUS_MAP.md` for complete feature reality map.

## Next Recommended Action

Sprint 0.2 is complete. Next up per MASTER_PLAN: **Sprint 0.3 — Code Cleanup** (remove dead stubs, fix hardcoded IP in firmware, clean TODOs) OR **Sprint 1.1 — Living Conversation** (conversation state machine, topic tracking, context-aware responses).

Safety layer is now: safety_filter (post-LLM) + pii_filter (pre-LLM) + emotion_risk_detector (pre-LLM) + manipulation_guard (pre-LLM input + post-LLM output).

For code changes: read `PROJECT.md`, this handoff, and relevant source files.
For large feature/API/schema/cross-module work: use Spec Kit or write a clear plan first.

## Current Test Command

```bash
python tests/run_tests.py
```

## Files Recently Touched (Sprint 0.2)

- `src/safety/vi_normalize.py` (new — Vietnamese diacritic normalizer)
- `src/safety/pii_filter.py` (new — PII detection + gentle redirect)
- `src/safety/emotion_risk_detector.py` (new — HIGH/MEDIUM/LOW risk + escalation)
- `src/safety/manipulation_guard.py` (new — LLM output + user input manipulation check)
- `src/main.py` (modified — integrated 3 safety modules into text + voice pipelines)
- `tests/run_tests.py` (modified — Group 65, 37 new safety tests)
- `docs/STATUS_MAP.md` (updated — Sprint 0.2 items marked Done, gap resolved)
- `docs/BACKLOG_Robot_Bi_v2.md` (updated — section 9 Sprint 0.2 items)
- `docs/SRS_Robot_Bi_v2.md` (updated — section 9.3 expanded with 5 safety rules)
- `.claude/handoff.md`

## Files Recently Touched (Sprint 0.1 and earlier)

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
