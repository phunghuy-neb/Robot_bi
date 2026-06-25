# Handoff Archive — 2026-06-24

> Historical "Last Completed Task" entries moved out of `.claude/handoff.md` so the handoff
> can serve as a lean current-state bridge. Entries below are preserved verbatim. Items that
> already had their own changelog file are listed as pointers only.

## Already in changelog (pointers)

- 2026-06-23 Audit Fix Sprint — `changelog/2026-06-23-audit-fix-sprint.md`
- 2026-06-23 Deferred 6 Audit Fixes — `changelog/2026-06-23-deferred-6-code-fixes.md`
- 2026-06-20 Claude Ultra Full-System Audit Loop hardening — `changelog/2026-06-20-claude-ultra-audit-loop.md`
- 2026-06-13 Stage 1 audio hardening — `changelog/2026-06-13-stage-1-audio-hardening.md`

## Archived entries (not previously in changelog)

- 2026-06-23: **Frontend wiring — robot location, notifications, device URL, drop mock** (branch `003-web-search-integration`, commit `c3039f1`):
  - `frontend/parent_app/src/pages/HomePage.jsx`: Wired `/api/robot/location` — shows `room_name` or "Chưa xác định"; removed coming-soon badge.
  - `frontend/parent_app/src/components/SettingsOverlay.jsx`: Notification section now loads from `/api/settings/notifications` and saves; toggle buttons call real API; removed coming-soon badge. Device connection section calls `/api/device/connection-qr` and shows URL + copy button; removed coming-soon badge. Removed mock-data badge from child profiles section.
  - `frontend/parent_app/src/services/api.js`: `getChildProfiles()` returns `[]` instead of mock when API has no children. Added `getDeviceConnectionUrl()` and `getRobotLocation()` helpers. Removed unused `mockChildProfiles` import.
  - All CI-passing tests unaffected (Python backend only; these are pure JSX/JS changes).

- 2026-06-23: **Frontend polish + Robot display animation** (branch `003-web-search-integration`):
  - `frontend/parent_app/src/services/api.js`: Fixed `exportReport` to do raw `fetch` + blob download (CSV/PDF, not JSON); added `url` field to `getRadioChannels` + `getVideoLessons` maps from `source_url`.
  - `frontend/parent_app/src/pages/JournalPage.jsx`: Wired export buttons (CSV + PDF) with blob download + toast feedback; removed stale `mock-data` badge from emotion chart.
  - `frontend/parent_app/src/pages/MorePage.jsx`: Removed stale `mock-data` badges from Radio/Video; ▶ buttons now open `source_url` in new tab (YouTube/VOV links from DB); video thumbnails render as `<img>` when URL available.
  - `frontend/robot_display/face.html`: Full animated robot face — CSS eyes with blink, iris tracking mouse/touch, mouth per expression, cheek blush, antenna pulse, 7 expression states (idle/happy/thinking/sleeping/pouting/curious/surprised), WebSocket listener for BiState events, demo loop when offline.
  - `frontend/robot_display/flashcard.html`: Full flashcard display — 3D flip animation, progress bar, keyboard shortcuts (←→ Space F), WebSocket listener for flashcard_deck/flashcard_show/next/prev/flip events, demo deck, URL ?deck=base64json param.

- 2026-06-23: **DeepSeek V3 + Frontend settings wiring + DB seed fix** (branch `003-web-search-integration`):
  - `src/ai/ai_engine.py`: Added DeepSeek V3 as 6th provider (after Cloudflare). `_stream_deepseek()` uses OpenAI-compatible endpoint `https://api.deepseek.com/v1/chat/completions`, model `deepseek-chat`. `_PROVIDER_ORDER` updated to 6 members. Protected original provider order unchanged.
  - `config.json`: Added `"deepseek_model": "deepseek-chat"`.
  - `.env.example`: Added `DEEPSEEK_API_KEY` with platform.deepseek.com comment.
  - `frontend/parent_app/src/services/api.js`: Replaced 4 TODO stubs: `saveSleepSchedule`, `saveTimeLimits`, `saveAgeFilter`, `savePushSettings` — all now call real backend APIs. Added GET wrappers: `getSleepSchedule`, `getTimeLimits`, `getAgeFilter`, `getNotificationSettings`. Wired `exportReport` to `POST /api/reports/export`.
  - `frontend/parent_app/src/components/SettingsOverlay.jsx`: Loads existing settings from backend on mount (sleep/time/age in parallel). Save buttons now call API and show ✅/❌ feedback. Removed stale `coming-soon` badges from sleep and content sections. Removed `no-backend` badge from system logs (already API-wired). Added loading states for save buttons (`sleepSaving`, `limitSaving`, `ageFilterSaving`).
  - `src/infrastructure/database/db.py`: Updated content_items seed data — proper Vietnamese names with diacritics, real educational URLs replacing `example.invalid` placeholders.
  - `tests/run_tests.py`: Fixed `test_71_cerebras_model_config_not_deprecated_qwen` to check 6-provider list without exact string match. Added Group 75 (8 tests) for DeepSeek V3.

- 2026-06-23: **Stage 1.5 Body Expression + Web Search + RAG improvements** (branch `003-web-search-integration`, commit `7e177e6`):
  - `src/motion/movement_emotion.py` (new): MovementEmotionEngine maps all 7 BiStates and 8 MomentIds to motor gestures; non-blocking daemon threads; sleep-hours (22:00–07:00) and 5s rate-limit guards; simulation mode transparent.
  - `src/main.py`: wired `_movement` into `_living_interaction_start`, `_living_reply_done`, `_fire_pouting_phrase`, `_fire_welcome_back_phrase`, `_fire_micro_moment_if_ready`.
  - `src/web_search/search_engine.py`: Tavily → Brave fallback; keyword-triggered; graceful degradation. Tavily live-tested OK.
  - `src/memory/rag_manager.py`: added RAG patterns for tuổi, màu sắc yêu thích, ước mơ, tên trường.
  - `.env.example`: reorganised BẮT BUỘC / KHUYẾN NGHỊ / TÙY CHỌN; Brave marked paid.
  - `tests/run_tests.py`: group 73 (11 tests) + group 74 (14 tests), all PASS.
  - `tests/test_web_search_live.py`: standalone live test, no robot startup needed.

- 2026-06-13: **ESP32-S3 MAX98357A speaker-only diagnostic (uncommitted)**:
  - Added `firmware/ESP32S3_Speaker_Test/ESP32S3_Speaker_Test.ino`.
  - Uses BCLK GPIO4, LRC GPIO5, and DIN GPIO7; no microphone or PSRAM dependency.
  - Repeats 440/880/1320 Hz counted tones and a 300-1800 Hz rising sweep.
  - Prints I2S initialization and write status over Serial at 115200 baud.

- 2026-06-13: **ESP32-S3 dual INMP441 + MAX98357A hardware test (uncommitted)**:
  - Added `firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino` for ESP32-S3 N16R8.
  - Uses BCLK GPIO4, WS GPIO5, shared microphone SD GPIO6, MAX98357A DIN GPIO7, 16 kHz stereo with 32-bit slots.
  - Runs without USB/Serial: beep cue, record 5 seconds to PSRAM, play left microphone, then play right microphone.
  - Does not use live loopback, avoiding direct acoustic feedback.
  - Compile verification passed with ESP32 Arduino Core 3.3.8, 16 MB flash, and OPI PSRAM.
  - Full software regression suite: `python tests/run_tests.py` PASS 560/560.

- 2026-06-13: **Sprint 1.4 Audio-Only Hardware Hardening (uncommitted follow-up after `f2d4738`, 560/560 PASS)**:
  - Proactive presence no longer depends on a camera. A recognized voice interaction marks recent presence for 12 minutes, allowing one prompt after 10 minutes of silence; optional camera events only extend presence.
  - Camera startup is optional and disabled by default with `CAMERA_ENABLED=false`.
  - Added `src/audio/input/microphone_utils.py`: real-mic ranking, callback-frame verification, native sample-rate capture, and resampling to 16 kHz.
  - EarSTT and wake-word capture now support callback/native-rate Windows devices.
  - CryDetector excludes the active STT mic and may use `CRY_MIC_DEVICE` for the second microphone.
  - Removed decorative `primary_api`; provider order remains fixed and protected. Added Cerebras quota cooldown.
  - Proactive TTS phrases now use proper Vietnamese accents.
  - Hardware finding: Windows listed microphone endpoints, but none returned callback audio frames during validation. Runtime now correctly enters silent mode instead of reporting a false-positive mic.

- 2026-06-13: **Sprint 1.4 — Proactive Behaviors + Stage 1 Polish (COMMITTED `f2d4738`, 545/545 PASS)**:
  - Cerebras model updated from stale Qwen settings to `cerebras_model=gpt-oss-120b`.
  - New `src/living/proactive_behaviors.py` — `ProactiveBehaviorsEngine` runtime-only child-present idle prompt gate.
  - Proactive rules: 10-minute silence threshold, child-present requirement, 30-minute anti-spam, blocked during homework, blocked during sleep hours 22:00–07:00, blocked in active engaged/thinking states.
  - `tests/run_tests.py` Group 71 added (13 tests).

- 2026-05-23: **Sprint 1.3 — Adaptive Persona + Giận Dỗi Mode (COMMITTED `6be68d8`, 532/532 PASS)**:
  - `PersonaManager` context detection/modifiers for PLAY/TEACH/COMFORT/IDLE.
  - `main.py` routes persona/living context through `system_context`, not user history.
  - Giận dỗi and welcome-back phrases pass `ManipulationGuard`; sleep/overlap guards applied.

- 2026-05-23: **Sprint 1.2 — Micro Moments Engine (COMMITTED `cb83b91`, 517/517 PASS)**:
  - `src/living/micro_moments.py` — 8 idle moments, 15-minute rate limit, homework/sleep guards, no DB.
  - `main.py` idle path integrates micro moments and puppet guard.

- 2026-05-23: **Sprint 1.1 — Living State Engine (COMMITTED `a4c4978`, 497/497 PASS)**:
  - `src/living/living_state.py` — runtime-only 7-state engine.
  - Integrated into text/voice loops and LLM `system_context`.
