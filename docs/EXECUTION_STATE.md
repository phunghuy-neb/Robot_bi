# EXECUTION_STATE.md — Robot Bi

> Source of truth cho execution state.
> Không phụ thuộc chat history. Đọc file này để biết current position, completed work, deferred items, và next task.
> Updated: 2026-06-13

---

## SECTION 1 — CURRENT POSITION

| Field | Value |
|---|---|
| **Current Stage** | Stage 1 — Bi Có Hồn (Living Engine) |
| **Current Sprint** | Stage 1.4 hardening complete in code; microphone hardware validation remains before Stage 1.5 |
| **Current Status** | Audio-only proactive presence, optional camera startup, native-rate mic capture, dual-mic isolation, and Cerebras cooldown implemented. `python tests/run_tests.py` PASS 560/560. |
| **Project Mode** | Software-First. Hardware/body movement remains separate. |
| **Active Branch** | `002-parent-app-backend-integration` |
| **Test command** | `python tests/run_tests.py` |
| **Last commit** | `f2d4738` — feat: complete Sprint 1.4 proactive behaviors |
| **Working tree** | Sprint 1.4 hardening is implemented but not committed; unrelated local files remain |

---

## SECTION 2 — COMPLETED

### Stage 0 — Foundation Truth Reset ✅ DONE

- **Sprint 0.1 — Sync Docs to Code Reality**: `PROJECT.md`, architecture/SRS/backlog/status docs normalized; generated agent docs synced. Commit: `479d850`.
- **Sprint 0.2 — Child Safety Foundation**: PII filter, emotion risk detector, manipulation guard, main loop integration. Commits: `1ba66ec`, `12113d2`.
- **Sprint 0.3 — Wake Word Foundation**: wake-word service/router/listener and main loop gating. Commit: `c8fe264`.
- **Sprint 0.4 — Wake Word Training Pipeline**: synthetic dataset, augmentation, MFCC+SVM training/test scripts; model still requires human training run. Commit: `aad6072`.

### Stage 1 — Bi Có Hồn ✅ SOFTWARE COMPLETE

- **Sprint 1.1 — Living State Engine**: `src/living/living_state.py` runtime-only 7-state machine, text/voice integration, `system_context` hints, 497/497 PASS. Commit: `a4c4978`.
- **Sprint 1.2 — Micro Moments Engine**: `src/living/micro_moments.py` with 8 idle moments, 15-minute rate limit, homework/sleep guards, idle TTS overlap guard, 517/517 PASS. Commit: `cb83b91`.
- **Sprint 1.3 — Adaptive Persona + Giận Dỗi Mode**: context detection/modifiers, pouting and welcome-back flow, review fixes for prompt routing/safety/guards, 532/532 PASS. Commit: `6be68d8`.
- **Sprint 1.4 — Proactive Behaviors + Stage 1 Polish**: initial implementation committed as `f2d4738`; follow-up hardening changed presence to audio-first, made camera optional, added native-rate callback mic capture/resampling, separated CryDetector from STT mic, added Cerebras quota cooldown, and reached 560/560 PASS.

---

## SECTION 3 — DEFERRED / HUMAN VALIDATION

### Wake Word Human Mic Validation

| Field | Detail |
|---|---|
| **Status** | 🟡 Partial — pipeline ready, model not trained/validated by real mic |
| **How to run** | `python scripts/generate_wakeword_dataset.py` → `python scripts/augment_audio.py` → `python scripts/train_wakeword.py` → `python scripts/test_wakeword.py` |
| **Target** | 8/10 "Bi ơi" detections in normal room conditions |
| **Enable in .env** | `WAKEWORD_ENABLED=true`, `WAKEWORD_BACKEND=custom_mfcc`, `WAKEWORD_CUSTOM_MODEL_PATH=runtime/wakeword/bi_oi_classifier.pkl` |

### Stage 1 Manual Product Validation

| Field | Detail |
|---|---|
| **Status** | Blocked on microphone access, then pending 1–3 day observation |
| **Reason** | Current machine has no camera and Windows lists microphone endpoints but returned no callback audio frames on 2026-06-13 |
| **Suggested check** | Fix Windows microphone privacy/driver/device access, verify STT receives speech, then run 1–3 day home test for prompt frequency and homework/sleep guards |

### Provider Quota

| Field | Detail |
|---|---|
| **Status** | Code OK; runtime quota may throttle |
| **Observed** | Full test passed even when Cerebras/Groq returned quota 429 warnings; fallback chain continued |
| **Action** | Monitor quota/billing on provider dashboards; no `.env` changes by agent |

---

## SECTION 4 — NEXT TASK

### Stage 1 Hardware Validation, Then Stage 1.5 — Body Expression

**Gate before Stage 1.5**: microphone callback capture must work on both intended devices and Stage 1 must pass a short real-room observation. No camera is required.

**Why Stage 1.5 after that**: the remaining "feels alive" gap is physical expression: motor movement mapped to living state, micro moments, and giận dỗi.

**Scope**:
- `src/motion/movement_emotion.py` wire layer.
- Map Living State → motor command when motor is enabled.
- Map Micro Moments `LOOK_AROUND` → light turn.
- Update giận dỗi movement from stub/log to real motor command.
- Add safety guards: sleep mode, video call active, motor simulation mode.
- Tests for mappings and guards.

**Do not start automatically unless user asks**:
- Special Memories / Stage 2.
- New DB schema for memories/milestones.
- Advanced behavioral profile.

---

## SECTION 5 — EXECUTION RULES

1. Read `PROJECT.md`, `.claude/handoff.md`, and relevant source files before code changes.
2. Use Spec Kit only for large features/API/schema/cross-module/major UI work or when explicitly requested.
3. Do not edit `CLAUDE.md` or `AGENTS.md` manually; edit `PROJECT.md` then run `python sync.py`.
4. Do not read/edit `.env`, runtime DB, logs, cache/model/media files, or generated artifacts by default.
5. After code changes, run `python tests/run_tests.py`; fix failures caused by the change.
6. Keep `SYSTEM_MAP.md` current when system structure/capability changes.
7. Do not fake pass; record any manual/hardware validation gap honestly.

---

## SECTION 6 — EXECUTION LOG

| Date | Done | Commit | Next |
|---|---|---|---|
| 2026-05-20 | Sprint 0.1: Sync docs | `479d850` | Sprint 0.2 |
| 2026-05-20 | Sprint 0.2: Child Safety Foundation | `1ba66ec`, `12113d2` | Sprint 0.3 |
| 2026-05-20 | Sprint 0.3: Wake Word Foundation | `c8fe264` | Sprint 0.4 |
| 2026-05-20 | Sprint 0.4: Wake Word Training Pipeline | `aad6072` | Sprint 1.1 |
| 2026-05-23 | Sprint 1.1: Living State Engine + review fixes; 497/497 PASS | `a4c4978` | Sprint 1.2 |
| 2026-05-23 | Sprint 1.2: Micro Moments Engine; 517/517 PASS | `cb83b91` | Sprint 1.3 |
| 2026-05-23 | Sprint 1.3: Adaptive Persona + Giận Dỗi Mode review fixes; 532/532 PASS | `6be68d8` | Sprint 1.4 |
| 2026-06-13 | Sprint 1.4 initial implementation; 545/545 PASS | `f2d4738` | Audio-only hardening |
| 2026-06-13 | Audio-only presence, mic hardening, optional camera, provider cooldown; 560/560 PASS | uncommitted | Fix Windows mic access, manual validation |
