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

- 2026-05-23: **Sprint 1.1 — Living State Engine (all review fixes applied, 497/497 PASS)**:
  - `src/living/living_state.py` — runtime-only 7-state engine; **bug fix**: `_CURIOUS_TO_SLEEPY_SECS` was `20 * 60` matching `_HAPPY_TO_CURIOUS_SECS`, causing `ACTIVE_HAPPY` to skip `IDLE_CURIOUS` and jump directly to `IDLE_SLEEPY` at 20 min. Fixed to cumulative `40 * 60` so the 20-min `IDLE_CURIOUS` window is preserved.
  - `src/living/__init__.py` — package exports for `BiState` and `LivingStateEngine`
  - `src/ai/ai_engine.py` — backward-compatible `system_context` keeps living hints out of user/RAG history
  - `src/main.py` — integrated living hooks in text + voice loops; safety early-returns complete living/wakeword lifecycle
  - `tests/run_tests.py` — Group 68 expanded to 24 tests: 68.23 (regression: ACTIVE_HAPPY 25 min → IDLE_CURIOUS, not IDLE_SLEEPY), 68.24 (behavioral integration: full turn cycle); test 68.11 updated to 45 min threshold; Windows fallback temp DB cleanup added
  - Docs updated: `docs/CODE_REVIEW_STATE.md`, `docs/EXECUTION_STATE.md`, `.claude/handoff.md`
  - Status: ready for final commit; next execution target is Sprint 1.2 — Micro Moments Engine

- 2026-05-20: **Sprint 0.4 — Wake Word Training Pipeline (4 scripts + custom_mfcc backend + 19 tests)**:
  - `scripts/generate_wakeword_dataset.py` — synthetic dataset via edge-tts (300 positive / 150 negative); requires ffmpeg + internet; ~10-20 min run
  - `scripts/augment_audio.py` — 18 augmentation types: noise (SNR 8/15/25 dB), fan/TV/kitchen BG, speed (0.85x-1.2x), pitch (±2/+4 semitones), gain, small/large reverb, phone mic, far mic, combined
  - `scripts/train_wakeword.py` — MFCC (scipy/numpy, no librosa) + SVM RBF classifier; output: `runtime/wakeword/bi_oi_classifier.pkl`; 5-fold CV; target F1 ≥ 0.75
  - `scripts/test_wakeword.py` — `--check-dataset`, `--file`, `--backend`, `--threshold`, `--timeout`; real-time mic test with sounddevice
  - `src/wakeword/config.py` — added `WAKEWORD_CUSTOM_MODEL_PATH` env var
  - `src/wakeword/wakeword_service.py` — added `custom_mfcc` backend: `_detect_custom_mfcc()` + `_get_mfcc_payload()` lazy loader; gracefully returns False when model absent
  - `requirements.txt` — added `scikit-learn>=1.4.0`
  - `tests/run_tests.py` — Group 67 (19 tests): scripts exist, config, service backend, MFCC shape, augmentation functions, directory structure, requirements
  - Status: scripts ready; **model not yet trained** (no dataset yet); run pipeline below to get usable prototype

- 2026-05-20: **Sprint 0.3 — Wake Word Foundation (6 new files + main.py integration + 24 tests)**. 454/455 PASS (28.9 pre-existing):
  - `src/wakeword/config.py` — all config from env (backend/threshold/cooldown/model path)
  - `src/wakeword/audio_listener.py` — background mic stream, stops on detection (EarSTT handoff)
  - `src/wakeword/wakeword_service.py` — 4-state machine (IDLE/LISTENING/PROCESSING/COOLDOWN), 3 backends (openwakeword/whisper/placeholder), double-trigger protection, auto-cooldown + restart
  - `src/wakeword/wakeword_router.py` — thin shim: wait_for_wakeword / on_stt_start / on_reply_done / on_error
  - `src/main.py` — WakeWordService + WakeWordRouter wired; gate in run(), cooldown after reply, reset on error, stop on shutdown; no-op when disabled
  - `docs/WAKEWORD_DATASET_GUIDE.md` — complete dataset spec (50–150 positive, 100–200 negative, recording guide, format, naming, training commands)
  - Tech stack decision: openWakeWord (primary, lazy-load when model exists) → faster-whisper tiny (fallback) → placeholder (testing)
  - No new hard dependencies
  - Model NOT trained — ready to collect dataset per WAKEWORD_DATASET_GUIDE.md
  - Commit: `c8fe264`

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

## Sprint 0.4 — Wake Word Training Pipeline (HOW TO USE)

```bash
# 1. Generate synthetic dataset (~300 positive, ~150 negative)
#    Yêu cầu: internet + ffmpeg trong PATH
python scripts/generate_wakeword_dataset.py

# 2. Augment dataset (×4 expansion → ~1800+ positive, ~900+ negative)
python scripts/augment_audio.py

# 3. Train MFCC+SVM classifier (cần scikit-learn)
pip install scikit-learn
python scripts/train_wakeword.py
# → runtime/wakeword/bi_oi_classifier.pkl

# 4. Test ngay
python scripts/test_wakeword.py

# 5. Kiểm tra dataset trước khi train
python scripts/test_wakeword.py --check-dataset

# 6. Kích hoạt trong .env
WAKEWORD_ENABLED=true
WAKEWORD_BACKEND=custom_mfcc
WAKEWORD_CUSTOM_MODEL_PATH=runtime/wakeword/bi_oi_classifier.pkl
WAKEWORD_THRESHOLD=0.5
```

## Known Issues

- Wake word **disabled by default** (`WAKEWORD_ENABLED=false`). Uses `faster-whisper tiny` fuzzy match when enabled — not a trained model.
- `edge-tts` (primary TTS) **requires internet** — not fully offline.
- ESP32-S3 (audio board) has **no firmware** — INMP441 + MAX98357 hardware is silent.
- `follow_me.py`, `dock_charger.py`, `face_recognizer.py`, `fall_detector.py` are **stubs** — no real logic.
- Motor firmware has **hardcoded IP** `192.168.40.107:8443` — must change per deployment.
- Cloudflare quick tunnel URL may change after restart unless a named tunnel is configured.
- YAMNet TFLite support depends on optional runtime dependencies.
- Parent App: radio/videos/games/logs use mock fallbacks; 4 saveSettings() stubs return null.
- Micro Moments Engine is not implemented yet; next target is Sprint 1.2.
- See `docs/STATUS_MAP.md` for complete feature reality map.

## Next Recommended Action

Sprint 1.1 is complete with all review fixes applied (497/497 PASS). Next execution target:
1. **Final commit Sprint 1.1** after human confirms commit/push workflow.
2. Start **Sprint 1.2 — Micro Moments Engine** from `docs/EXECUTION_STATE.md`.
3. Keep scope tight: 8 micro moments, rate limit, guardrails, non-blocking TTS; no motor movement or adaptive persona yet.

Deferred wake word validation remains available:
- Generate dataset: `python scripts/generate_wakeword_dataset.py` (needs internet + ffmpeg)
- Augment: `python scripts/augment_audio.py`
- Train: `pip install scikit-learn && python scripts/train_wakeword.py`
- Enable via `.env`: `WAKEWORD_ENABLED=true`, `WAKEWORD_BACKEND=custom_mfcc`

Safety layer (all active): safety_filter + pii_filter + emotion_risk_detector + manipulation_guard.
Wake word (disabled by default): `WAKEWORD_ENABLED=false`. Foundation complete; model still needs training.

For code changes: read `PROJECT.md`, this handoff, and relevant source files.
For large feature/API/schema/cross-module work: use Spec Kit or write a clear plan first.

## Current Test Command

```bash
python tests/run_tests.py
```

## Files Recently Touched (Sprint 1.1)

- `src/living/__init__.py` (new — package exports)
- `src/living/living_state.py` (new — runtime-only 7-state engine)
- `src/ai/ai_engine.py` (modified — `system_context` internal prompt hook)
- `src/main.py` (modified — text/voice living hooks and direct-response completion)
- `tests/run_tests.py` (modified — Group 68, 22 tests)
- `docs/CODE_REVIEW_STATE.md` (updated — review fixes and ready status)
- `docs/EXECUTION_STATE.md` (updated — next target Sprint 1.2)
- `docs/STATUS_MAP.md` (updated v1.4)
- `SYSTEM_MAP.md` (updated — `src/living/` module map)
- `.claude/handoff.md`

## Files Recently Touched (Sprint 0.4)

- `scripts/generate_wakeword_dataset.py` (new — edge-tts synthetic dataset generator)
- `scripts/augment_audio.py` (new — 18 augmentation types, scipy+numpy only)
- `scripts/train_wakeword.py` (new — MFCC+SVM training, output: bi_oi_classifier.pkl)
- `scripts/test_wakeword.py` (new — real-time mic test harness + dataset check)
- `src/wakeword/config.py` (modified — added WAKEWORD_CUSTOM_MODEL_PATH)
- `src/wakeword/wakeword_service.py` (modified — custom_mfcc backend + _detect_custom_mfcc + _get_mfcc_payload)
- `requirements.txt` (modified — added scikit-learn>=1.4.0)
- `tests/run_tests.py` (modified — Group 67, 19 tests)
- `docs/STATUS_MAP.md` (updated v1.3 — wake word status reflects Sprint 0.4)
- `.claude/handoff.md`

## Files Recently Touched (Sprint 0.3)

- `src/wakeword/__init__.py` (new)
- `src/wakeword/config.py` (new — all env config)
- `src/wakeword/audio_listener.py` (new — background mic capture)
- `src/wakeword/wakeword_service.py` (new — state machine + backends)
- `src/wakeword/wakeword_router.py` (new — main.py integration shim)
- `src/wakeword/README.md` (new — training instructions)
- `src/main.py` (modified — WakeWordService + WakeWordRouter integrated)
- `tests/run_tests.py` (modified — Group 66, 24 tests)
- `docs/WAKEWORD_DATASET_GUIDE.md` (new — full dataset recording guide)
- `docs/STATUS_MAP.md` (updated v1.2)
- `docs/BACKLOG_Robot_Bi_v2.md` (updated v2.4)

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
