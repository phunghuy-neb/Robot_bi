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
- Generated agent docs: `CLAUDE.md` and `AGENTS.md`, regenerated with `python sync.py` after `PROJECT.md` changes.
- Current test command: `python tests/run_tests.py`.

## Last Completed Task

- 2026-06-13: **Sprint 1.4 — Proactive Behaviors + Stage 1 Polish ✅ COMMITTED (this commit, 545/545 PASS)**:
  - Cerebras primary config updated from stale Groq/Qwen settings to `primary_api=cerebras` and `cerebras_model=gpt-oss-120b`.
  - Confirmed configured Cerebras API key can call `/v1/models` and stream with `gpt-oss-120b`; full suite later saw quota 429 warnings but fallback chain continued successfully.
  - New `src/living/proactive_behaviors.py` — `ProactiveBehaviorsEngine` runtime-only child-present idle prompt gate.
  - Proactive rules: 10-minute silence threshold, child-present requirement, 30-minute anti-spam, blocked during homework, blocked during sleep hours 22:00–07:00, blocked in active engaged/thinking states.
  - `src/main.py` wiring: recent child presence from `motion`/`known_face` vision events; proactive timer resets on interaction; proactive prompt checked before micro moments.
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
- Stage 1 software: complete through Sprint 1.4.
- Stage 1 manual validation: pending human/device observation.
- Stage 1.5 body expression: not started.
- Stage 2 Special Memories: not started.

## Known Issues / Deferred Work

- Wake word disabled by default (`WAKEWORD_ENABLED=false`). Training pipeline exists, but real mic validation and trained custom model are pending.
- `edge-tts` primary TTS requires internet; pyttsx3 fallback remains local.
- ESP32-S3 audio/display firmware does not exist.
- `follow_me.py`, `dock_charger.py`, `face_recognizer.py`, `fall_detector.py` are stubs/placeholders.
- Motor firmware has hardcoded IP `192.168.40.107:8443`; deployment-specific change needed.
- Cloudflare quick tunnel URL can change after restart unless a named tunnel is configured.
- Parent App radio/videos/games/system logs use mock fallbacks; several settings save buttons remain stubs.
- Provider quota can throttle Cerebras/Groq; fallback chain handled observed quota 429 warnings during tests.

## Next Recommended Action

Stage 1 software is done. Choose one of:

- **Manual validation**: run Robot Bi with real mic/camera and observe Stage 1 behavior over 1–3 days.
- **Stage 1.5 — Body Expression**: add motor movement mappings for Living State, Micro Moments, and giận dỗi mode.
- **Stage 2 — Special Memories**: only after user explicitly asks to start Stage 2.

Do not start Stage 2 automatically just because Stage 1 software is complete.

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
