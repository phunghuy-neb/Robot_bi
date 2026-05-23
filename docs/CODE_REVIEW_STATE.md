# CODE_REVIEW_STATE.md — Robot Bi

> Dùng cho Codex / ChatGPT / Gemini review task vừa implement.
> Claude PHẢI tự update file này sau mỗi task trước khi final commit.
> Reviewer chỉ review CURRENT TASK — không scan cả repo.
> Updated: 2026-05-23

---

## SECTION 1 — TASK REVIEW INFO

| Field | Value |
|---|---|
| **Task name** | Sprint 1.2 — Micro Moments Engine |
| **Sprint** | Sprint 1.2 (Stage 1 — Bi Có Hồn) |
| **Branch** | `002-parent-app-backend-integration` |
| **Commit hash** | `cb83b91` |
| **Commit range** | `a4c4978..working tree` |
| **Files changed** | `src/living/micro_moments.py` (new), `src/living/__init__.py`, `src/main.py`, `tests/run_tests.py` |
| **Short summary** | Thêm `MicroMomentsEngine` — 8 hành vi tự phát runtime-only (ngáp, lẩm bẩm, hát nhỏ, nhìn quanh, tự nói, kể điều lạ, phản ứng thời gian, chuẩn bị bất ngờ). Rate limit 15 phút, guardrails homework + sleep hours. Wire nhẹ vào `main.py` idle path (không block conversation). 18 tests Group 69; tổng 515/515 PASS. |

---

## SECTION 2 — REVIEW TARGET

> Claude phải tự populate section này sau mỗi task.

**Changed files**:
- `src/living/micro_moments.py` — `MomentId` enum (8 moments) + `MicroMomentsEngine` class (new)
- `src/living/__init__.py` — added `MicroMomentsEngine` + `MomentId` exports
- `src/main.py` — import + `self._micro` + `self._last_homework_at` + `_fire_micro_moment_if_ready()` + homework tracking + idle path wire
- `tests/run_tests.py` — Group 69 (18 tests)

**Affected logic**:
- New: `MicroMomentsEngine.maybe_trigger()` — lazy selection + rate-limit check + guardrail check; caller drives timing, no background threads, no DB
- New: `_hour_to_period()` + `_is_sleep_hours()` — time-of-day helpers
- Modified: `main.py` — `_mark_homework_if_ready` updates `self._last_homework_at`; idle path (`not user_text`) calls `_fire_micro_moment_if_ready()` which fires TTS via background thread
- No SQLite, no new deps, no new threads in the engine itself

**Sprint 1.2 scope constraints respected**:
- Runtime-only: no SQLite, no DB reads/writes
- No motor movement (Stage 1.5)
- No Adaptive Persona / context detection (Sprint 1.3)
- No UI
- No proactive conversation beyond micro moment TTS phrase

**Review scope**:
> Reviewer ONLY reviews the implementation files listed above.
> DO NOT scan the full repo. DO NOT review pre-existing code outside the changed files.

---

## SECTION 3 — REVIEW CHECKLIST

Reviewer xác nhận từng mục:

- [x] Scope đúng với MASTER_PLAN.md cho sprint này — chỉ micro moments, không motor, không persona, không UI
- [x] Không over-engineer — ~120 lines engine, no threads in engine itself, no DB
- [x] Không architecture drift — pure Python class, caller drives timing
- [x] Tests pass — 517/517 PASS (497 cũ + 20 mới Group 69)
- [x] Không regression trên test groups cũ — 497/497 giữ nguyên
- [x] Không fake implementation — tests kiểm tra behavior qua public interface
- [x] Naming consistency — snake_case, `MomentId`, `MicroMomentsEngine`, `maybe_trigger()`; YAW→YAWN renamed
- [x] Child safety maintained — engine không bypass bất kỳ safety pipeline nào; TTS phrase qua `_speak_text()` giống TaskManager reminder
- [x] Rate limit chống spam hoạt động — max 1 lần / 15 phút; None result không consume rate limit
- [x] Guardrails đúng — không phát khi homework, không phát khi sleep hours (22:00–07:00)
- [x] Non-blocking — micro moment TTS dùng daemon thread, không block `run()` conversation loop; puppet guard prevents overlap

---

## SECTION 4 — REVIEW REQUEST

Dùng prompt này để gửi cho Codex / ChatGPT / Gemini:

```
Please review ONLY the current task implementation described in CODE_REVIEW_STATE.md.

Context: Robot Bi is a Python/FastAPI AI tutor robot for children ages 5-12.
Stack: Python, FastAPI, SQLite, ChromaDB, Groq/Cerebras LLM, edge-tts, faster-whisper.
Branch: 002-parent-app-backend-integration

Task: Sprint 1.2 — Micro Moments Engine
Summary: Added MicroMomentsEngine (8 spontaneous idle behaviors fired via TTS).
Runtime-only: no DB, no background threads in the engine itself.
Rate limit: 1 per 15 minutes. Guardrails: skip during homework and sleep hours (22:00–07:00).
Wire: main.py idle path calls _fire_micro_moment_if_ready() via daemon thread.
18 tests (Group 69).

Files to review:
- src/living/micro_moments.py (new — MomentId enum + MicroMomentsEngine class)
- src/living/__init__.py (modified — added exports)
- src/main.py (modified — import, _micro init, homework tracking, idle path wire)
- tests/run_tests.py (modified — Group 69 tests)

Focus ONLY on:
- Bugs or logic errors in the changed files
- Regression risk (does this break existing behavior?)
- Architecture drift (does this violate the current stack or project conventions?)
- Missing tests for edge cases
- Child safety: does anything bypass or weaken the safety pipeline?
- Maintainability: is the code readable and reasonably simple?
- Overengineering: is there unnecessary abstraction or complexity?
- Spam risk: is the rate limit implementation correct?

DO NOT review code outside the changed files listed above.
DO NOT suggest features beyond the sprint scope (no motor, no persona, no UI).
DO NOT self-approve — list all findings clearly.
```

---

## SECTION 5 — REVIEW RESULT

> Source: External review (Codex/ChatGPT/Gemini). Reviewed commit range `a4c4978..working tree`.

### Critical
_(Issues that MUST be fixed before any commit — bugs, security holes, crashes, child safety violations)_

- None

### High
_(Issues that should be fixed before merge — incorrect behavior, missing required tests, regression risk)_

- None

### Medium
_(Issues to fix if time permits — naming, minor edge cases, readability)_

- ✅ FIXED: Micro moment overlaps with STT listen cycle — added `_micro_speaking` flag; `_speak_micro_moment()` sets/clears it; `run()` skips `ear.listen()` with `_time.sleep(0.3); continue` when `self._micro_speaking` is True.
- ✅ FIXED: Micro moments fire immediately after puppet audio — `_handle_puppet_queue()` now returns `bool`; idle path captures `puppet_played` and skips `_fire_micro_moment_if_ready()` if True.
- ✅ FIXED: Weak source-string tests replaced — test 69.18 now verifies `None` result does not advance `_last_fired_at` (behavioral); 69.19 verifies puppet guard exists in idle path; 69.20 verifies hour validation raises `ValueError`.

### Low
_(Nice-to-have improvements — style, doc comments, future-proofing)_

- ✅ FIXED: `MomentId.YAW` → `MomentId.YAWN` renamed consistently in `micro_moments.py` and `run_tests.py` (test 69.10).
- ✅ FIXED: Hour range validation added to `maybe_trigger()` — raises `ValueError` for values outside 0–23.

---

## SECTION 6 — FIX STATUS

| Item | Status |
|---|---|
| Critical issues fixed? | ✅ No critical issues |
| High issues fixed? | ✅ No high issues |
| Medium issues fixed? | ✅ All 3 fixed |
| Low issues fixed? | ✅ Both fixed |
| Re-tested after fixes? | ✅ 517/517 PASS |
| Ready for final commit? | ✅ Yes |

---

## HISTORY — Previous Reviews

| Sprint | Task | Commit | Critical | High | Result |
|---|---|---|---|---|---|
| Sprint 1.1 | Living State Engine | `a4c4978` | 0 | 4 fixed | ✅ Committed — 497/497 PASS |
| Sprint 1.2 | Micro Moments Engine | `cb83b91` | 0 | 0 | ✅ Committed — 517/517 PASS |
