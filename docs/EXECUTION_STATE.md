# EXECUTION_STATE.md — Robot Bi

> Source of truth cho execution state.
> Không phụ thuộc chat history. Đọc file này để biết current position, completed work, deferred items, và next task.
> Updated: 2026-06-13

---

## SECTION 1 — CURRENT POSITION

| Field | Value |
|---|---|
| **Current Stage** | Stage 1 — Bi Có Hồn (Living Engine) |
| **Current Sprint** | Stage 1 software complete; next recommended task is Stage 1.5 — Body Expression |
| **Current Status** | Sprint 1.4 Proactive Behaviors + Stage 1 Polish implemented and reviewed. `python tests/run_tests.py` PASS 545/545. |
| **Project Mode** | Software-First. Hardware/body movement remains separate. |
| **Active Branch** | `002-parent-app-backend-integration` |
| **Test command** | `python tests/run_tests.py` |
| **Last commit** | `6be68d8` — fix: Sprint 1.3 review fixes |
| **Working tree** | Sprint 1.4 committed; unrelated local files may still be dirty |

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
- **Sprint 1.4 — Proactive Behaviors + Stage 1 Polish**: `src/living/proactive_behaviors.py`, child-present idle prompt after 10 minutes silence, 30-minute anti-spam, homework/sleep/active-state guards, same-tick pouting guard, Cerebras model updated to `gpt-oss-120b`, 545/545 PASS. Commit: this commit.

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
| **Status** | Pending human/device validation |
| **Reason** | Requires real microphone/camera/child-present signals and observation over time |
| **Suggested check** | 1–3 day home test: idle moments not annoying, proactive prompt fires only when child is present and silent, no homework/sleep interruptions |

### Provider Quota

| Field | Detail |
|---|---|
| **Status** | Code OK; runtime quota may throttle |
| **Observed** | Full test passed even when Cerebras/Groq returned quota 429 warnings; fallback chain continued |
| **Action** | Monitor quota/billing on provider dashboards; no `.env` changes by agent |

---

## SECTION 4 — NEXT TASK

### Stage 1.5 — Body Expression

**Why next**: Stage 1 software illusion-of-life is complete. The remaining "feels alive" gap is physical expression: motor movement mapped to living state, micro moments, and giận dỗi.

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
| 2026-06-13 | Sprint 1.4: Proactive Behaviors + Stage 1 Polish; 545/545 PASS | _(this commit)_ | Stage 1.5 |
