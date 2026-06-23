# Handoff - Robot Bi

> Current-state handoff only. Historical details belong in `changelog/`.

## Current State

- `PROJECT.md` is the source of truth for rules, protected fixes, workflow, and AI context policy.
- Current source root is `src/`; `src_brain/` is deprecated and must not be used.
- Main entry point: `src/main.py`.
- API server: `src/api/server.py`.
- Parent App: `frontend/parent_app/`.
- Robot Display: `frontend/robot_display/`.
- Motor firmware: `firmware/Robot_BI/Robot_BI.ino`.
- ESP32-S3 audio hardware test: `firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino`.
- ESP32-S3 speaker-only test: `firmware/ESP32S3_Speaker_Test/ESP32S3_Speaker_Test.ino`.
- Runtime DB: `runtime/robot_bi.db`.
- Generated agent docs: `CLAUDE.md` and `AGENTS.md`, regenerated with `python sync.py` after `PROJECT.md` changes.
- Current test command: `python tests/run_tests.py`.

## Last Completed Task

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

- 2026-06-23: **Deferred 6 Audit Fixes — no-hardware code fixes**:
  - H1 (Robot_BI.ino): Replaced blocking `delay()` in motor handlers with non-blocking `millis()` state machine. `_timedMotorCmd()` helper; `motorStopAt` checked in `loop()`. stop/go_home also clear `motorStopAt`.
  - L3 (Robot_BI.ino): Added `motorStop()` + `motorStopAt = 0` before `ESP.restart()` in add_wifi handler.
  - L4 (ESP32S3_Mic_Test.ino): Replaced silent `while(true){delay(1000);}` after I2S init failure with repeating Serial printf every 5 s.
  - L5 (ESP32S3_Mic_Test.ino): Added return-value check on all `audioI2S.write()` calls in `writeSilence`, `playTone`, `playRecordedChannel`; logs WARN when written ≠ expected.
  - M-NEW-3 (wakeword_service.py): Fixed clear-before-wait race. `_restart_listener()` now clears `_detected_event` before starting the listener. `wait_for_detection()` no longer calls `clear()`. `enter_cooldown()` and `reset_to_idle()` delegate clearing to `_restart_listener()`.
  - M-NEW-4 (microphone_utils.py): Added `time.sleep(0.15)` after probe stream close in `probe_input_device()` to let WDM-KS fully release before the caller opens the device again.
  - Baseline unchanged: 13 PASS / 6 FAIL (6 fail = missing optional libs, pre-existing).
  - Changelog: `changelog/2026-06-23-deferred-6-code-fixes.md`.

- 2026-06-23: **Audit Fix Sprint — 23/30 issues from Round 34**:
  - Phase 01 (Security & Safety — 9 fixes): C1, H-NEW-1, H-NEW-2, H-NEW-3, M-NEW-5, M-NEW-6, L-NEW-6, L1, L2.
  - Phase 02 (Correctness & Resources — 5 fixes): M-NEW-7, M1+L8, M2, M3.
  - Phase 03 (Low Priority — 9 fixes): M4, M-NEW-1, L-NEW-1, L-NEW-2, L-NEW-3, L6, L7, L9. L-NEW-4 already OK.
  - Deferred (6 issues): H1, M-NEW-3, M-NEW-4, L3, L4, L5 — all require hardware.
  - Key changes: safety_filter now diacritic-normalized (two-group approach), motor WS auth enforced, provider streams closed, _chunk_counter thread-safe, motor reconnect lock fixed, /health has DB probe, /auth/refresh rate limited.
  - Baseline unchanged: 13 PASS / 6 FAIL (6 fail = missing optional libs, pre-existing).
  - Changelog: `changelog/2026-06-23-audit-fix-sprint.md`.

- 2026-06-20: **Claude Ultra Full-System Audit Loop operational hardening**:
  - Replaced `/home/huyphung/bin/claude-deep-review-loop` with a fail-closed Python wrapper and installed the review charter at `/home/huyphung/bin/claude-deep-review-charter.md`.
  - The wrapper now creates `.claude-review/PROJECT_MANIFEST.md` before Claude runs, detects repository drift, validates Opus 4.8 routing, parses required output markers, merges stable-ID/group deltas, backs up managed reports, and preserves prior reports on parse/model/quota failures.
  - Updated the user systemd unit for `ANTHROPIC_MODEL=claude-opus-4-8`, 250 max turns, 5-second round interval, and 120-second quota retry. Claude remains restricted to plan mode with Read/Glob/Grep and no session persistence.
  - Verification: wrapper self-test 6/6 PASS; fake-Claude success/failure integration PASS; systemd unit verification PASS; runtime PID environment matches all required values; project regression baseline PASS 560/560.
  - Current service state is `OPUS_LIMIT_HIT` for round 32. The generated manifest contains 377 relevant files; the service will retry without replacing the prior backlog.

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

- 2026-06-13: **Sprint 1.4 Audio-Only Hardware Hardening ✅ 560/560 PASS (uncommitted follow-up after `f2d4738`)**:
  - Proactive presence no longer depends on a camera. A recognized voice interaction marks recent presence for 12 minutes, allowing one prompt after 10 minutes of silence; optional camera events only extend presence.
  - Camera startup is optional and disabled by default with `CAMERA_ENABLED=false`.
  - Added `src/audio/input/microphone_utils.py`: real-mic ranking, callback-frame verification, native sample-rate capture, and resampling to 16 kHz.
  - EarSTT and wake-word capture now support callback/native-rate Windows devices.
  - CryDetector excludes the active STT mic and may use `CRY_MIC_DEVICE` for the second microphone.
  - Removed decorative `primary_api`; provider order remains fixed and protected. Added Cerebras quota cooldown.
  - Proactive TTS phrases now use proper Vietnamese accents.
  - Verification: changed-file `py_compile` PASS; `python tests/run_tests.py` PASS 560/560.
  - Hardware finding: Windows listed microphone endpoints, but none returned callback audio frames during validation. Runtime now correctly enters silent mode instead of reporting a false-positive mic.

- 2026-06-13: **Sprint 1.4 — Proactive Behaviors + Stage 1 Polish ✅ COMMITTED (`f2d4738`, 545/545 PASS)**:
  - Cerebras model updated from stale Qwen settings to `cerebras_model=gpt-oss-120b`.
  - Confirmed configured Cerebras API key can call `/v1/models` and stream with `gpt-oss-120b`; full suite later saw quota 429 warnings but fallback chain continued successfully.
  - New `src/living/proactive_behaviors.py` — `ProactiveBehaviorsEngine` runtime-only child-present idle prompt gate.
  - Proactive rules: 10-minute silence threshold, child-present requirement, 30-minute anti-spam, blocked during homework, blocked during sleep hours 22:00–07:00, blocked in active engaged/thinking states.
  - Initial wiring used `motion`/`known_face` vision events; the later hardening entry above supersedes this with audio-first presence.
  - Review fixes applied: same-tick proactive+pouting overlap blocked; `proactive_fired` initialized before puppet branch; `_start_idle_phrase_thread()` sets `_micro_speaking` before starting idle TTS thread to avoid overlap races.
  - `tests/run_tests.py` Group 71 added (13 tests).
  - Full verification: `python tests/run_tests.py` PASS 545/545.
  - Docs updated: `PROJECT.md`, generated `CLAUDE.md`/`AGENTS.md`, `.env.example`, `HUONG_DAN_CHAY.md`, `docs/ARCHITECTURE.md`, `docs/STATUS_MAP.md`, `docs/BACKLOG_Robot_Bi_v2.md`, `docs/EXECUTION_STATE.md`, `docs/CODE_REVIEW_STATE.md`, `SYSTEM_MAP.md`.

- 2026-05-23: **Sprint 1.3 — Adaptive Persona + Giận Dỗi Mode ✅ COMMITTED (`6be68d8`, 532/532 PASS)**:
  - `PersonaManager` context detection/modifiers for PLAY/TEACH/COMFORT/IDLE.
  - `main.py` routes persona/living context through `system_context`, not user history.
  - Giận dỗi and welcome-back phrases pass `ManipulationGuard`; sleep/overlap guards applied.

- 2026-05-23: **Sprint 1.2 — Micro Moments Engine ✅ COMMITTED (`cb83b91`, 517/517 PASS)**:
  - `src/living/micro_moments.py` — 8 idle moments, 15-minute rate limit, homework/sleep guards, no DB.
  - `main.py` idle path integrates micro moments and puppet guard.

- 2026-05-23: **Sprint 1.1 — Living State Engine ✅ COMMITTED (`a4c4978`, 497/497 PASS)**:
  - `src/living/living_state.py` — runtime-only 7-state engine.
  - Integrated into text/voice loops and LLM `system_context`.

## Stage Status

- Parent App Backend Phase 3: COMPLETE.
- Stage 0: complete.
- Stage 1 software: complete through Sprint 1.4 hardening.
- Stage 1 manual validation: robot audio is blocked until the ESP32-S3 microphone hardware test passes and production audio transport is implemented.
- Stage 1.5 body expression: not started.
- Stage 2 Special Memories: not started.

## Known Issues / Deferred Work

- Wake word disabled by default (`WAKEWORD_ENABLED=false`). Training pipeline exists, but real mic validation and trained custom model are pending.
- `edge-tts` primary TTS requires internet; pyttsx3 fallback remains local.
- ESP32-S3 mic/speaker hardware test exists; production network audio transport and display firmware do not.
- `follow_me.py`, `dock_charger.py`, `face_recognizer.py`, `fall_detector.py` are stubs/placeholders.
- Motor firmware has hardcoded IP `192.168.40.107:8443`; deployment-specific change needed.
- Cloudflare quick tunnel URL can change after restart unless a named tunnel is configured.
- Parent App radio/videos/games/system logs use mock fallbacks; several settings save buttons remain stubs.
- Provider quota can throttle Cerebras/Groq; fallback chain handled observed quota 429 warnings during tests.
- Current machine has no camera; this is supported and no longer blocks proactive behavior.
- Windows microphone diagnostics apply only to optional PC-connected microphones, not the two INMP441 modules on the robot.

## Next Recommended Action

1. Upload `firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino` and verify the autonomous beep/record/left-playback/right-playback cycle.
2. Implement ESP32-S3 network audio transport after the hardware test passes.
3. Run Robot Bi with speaker + microphones for 1–3 days; no camera is required.
4. Start Stage 1.5 Body Expression only after proactive frequency and audio stability are acceptable.
5. Do not start Stage 2 automatically.

## Current Test Command

```bash
python tests/run_tests.py
```

## Files Recently Touched (Sprint 1.4)

- `config.json`
- `.env.example`
- `HUONG_DAN_CHAY.md`
- `PROJECT.md`
- `CLAUDE.md` (generated)
- `AGENTS.md` (generated)
- `src/ai/ai_engine.py`
- `src/living/proactive_behaviors.py`
- `src/living/__init__.py`
- `src/main.py`
- `tests/run_tests.py`
- `docs/ARCHITECTURE.md`
- `docs/STATUS_MAP.md`
- `docs/BACKLOG_Robot_Bi_v2.md`
- `docs/EXECUTION_STATE.md`
- `docs/CODE_REVIEW_STATE.md`
- `SYSTEM_MAP.md`
- `.claude/handoff.md`

## Files Recently Touched (Sprint 1.4 Hardening)

- `src/audio/input/microphone_utils.py`
- `src/audio/input/ear_stt.py`
- `src/audio/analysis/cry_detector.py`
- `src/wakeword/audio_listener.py`
- `src/living/proactive_behaviors.py`
- `src/ai/ai_engine.py`
- `src/main.py`
- `tests/run_tests.py`
- `config.json`
- `.env.example`
- current-state docs and generated agent docs
