# CODE_REVIEW_STATE.md — Robot Bi

> Dùng cho Codex / ChatGPT / Gemini review task vừa implement.
> Claude PHẢI tự update file này sau mỗi task trước khi final commit.
> Reviewer chỉ review CURRENT TASK — không scan cả repo.
> Updated: 2026-05-23

---

## SECTION 1 — TASK REVIEW INFO

| Field | Value |
|---|---|
| **Task name** | Sprint 1.1 — Living State Engine |
| **Sprint** | Sprint 1.1 (Stage 1 — Bi Có Hồn) |
| **Branch** | `002-parent-app-backend-integration` |
| **Commit hash** | _(pending — ready for final commit)_ |
| **Commit range** | `6855a58..working tree` |
| **Files changed** | `src/living/__init__.py` (new), `src/living/living_state.py` (new), `src/ai/ai_engine.py`, `src/main.py`, `tests/run_tests.py`, docs state files |
| **Short summary** | Thêm `LivingStateEngine` — state machine 7 trạng thái runtime-only cho "hồn" của Bi. Tích hợp vào cả text mode và voice mode của `main.py`, truyền living hint qua `system_context` thay vì nhét vào user/RAG text. 24 tests Group 68 (thêm 68.23 regression + 68.24 behavioral); tổng 497/497 PASS. |

---

## SECTION 2 — REVIEW TARGET

> Claude phải tự populate section này sau mỗi task.

**Changed files**:
- `src/living/__init__.py` — package exports (new)
- `src/living/living_state.py` — `BiState` enum (7 states) + `LivingStateEngine` class (new)
- `src/ai/ai_engine.py` — backward-compatible `system_context` argument for internal prompt context
- `src/main.py` — import + `__init__` init block + lifecycle helpers + hooks in `run_text_mode()` and `run()` (modified)
- `tests/run_tests.py` — Group 68 (22 tests) + Windows rmtree fix (modified)

**Affected logic**:
- New: `LivingStateEngine` — lazy idle-decay state machine, no threads, no DB
- Modified: `ai_engine.py` — optional internal context is appended to system prompt and not stored in `BiAI.history`
- Modified: `main.py` text mode pipeline — `on_interaction_start()` after `add_turn`, living context passed to `stream_chat(system_context=...)`, `on_reply_done()` after reply persisted
- Modified: `main.py` voice mode pipeline — same hooks at equivalent positions; direct safety responses complete living/wakeword lifecycle before `continue`
- Modified: `tests/run_tests.py` — `shutil.rmtree` wrapped in try/except for Windows ChromaDB lock

**Risk areas fixed**:
- State hint no longer prepends to `user_text`; it goes through `system_context`, outside user/RAG history.
- Safety early-return responses now call `_complete_direct_response_turn()`, so `LivingStateEngine` and wakeword cooldown are completed before `continue`.
- `_living` init is no longer silently optional; init failures surface during startup.

**Review scope**:
> Reviewer ONLY reviews the implementation files listed above.
> DO NOT scan the full repo. DO NOT review pre-existing code outside the changed files.

---

## SECTION 3 — REVIEW CHECKLIST

Reviewer xác nhận từng mục:

- [x] Scope đúng với MASTER_PLAN.md cho sprint này — chỉ state machine, không Micro Moments, không motor
- [x] Không over-engineer — lazy evaluation, no threads, no DB, ~90 lines total
- [x] Không architecture drift — pure Python class, không thêm dependency mới
- [x] Tests pass — 495/495 PASS (473 cũ + 22 mới Group 68)
- [x] Không regression trên test groups cũ — 473/473 giữ nguyên
- [x] Không fake implementation — tests thực sự kiểm tra behavior qua public interface
- [x] Naming consistency — snake_case, `BiState`, `LivingStateEngine`, `on_*` hook pattern
- [x] Child safety maintained — safety pipeline không bị chạm; living hint là System Instruction thêm vào, không bypass bất kỳ filter nào
- [x] Performance acceptable — `get_state()` là O(1) time.time() subtraction, không blocking

---

## SECTION 4 — REVIEW REQUEST

Dùng prompt này để gửi cho Codex / ChatGPT / Gemini:

```
Please review ONLY the current task implementation described in CODE_REVIEW_STATE.md.

Context: Robot Bi is a Python/FastAPI AI tutor robot for children ages 5-12.
Stack: Python, FastAPI, SQLite, ChromaDB, Groq/Cerebras LLM, edge-tts, faster-whisper.
Branch: 002-parent-app-backend-integration

Task: Sprint 1.1 — Living State Engine
Summary: Added LivingStateEngine (7-state runtime state machine for Bi's inner life).
Integrated into main.py text mode and voice mode via 3 hooks each.
22 tests (Group 68), 495/495 total PASS.

Files to review:
- src/living/living_state.py (new — BiState enum + LivingStateEngine class)
- src/ai/ai_engine.py (modified — optional system_context for internal prompt context)
- src/main.py (modified — import, init, lifecycle helpers, hook calls)
- tests/run_tests.py (modified — Group 68 tests + Windows rmtree fix)

Focus ONLY on:
- Bugs or logic errors in the changed files
- Regression risk (does this break existing behavior?)
- Architecture drift (does this violate the current stack or project conventions?)
- Missing tests for edge cases
- Child safety: does anything bypass or weaken the safety pipeline?
- Maintainability: is the code readable and reasonably simple?
- Overengineering: is there unnecessary abstraction or complexity?

DO NOT review code outside the changed files listed above.
DO NOT suggest features beyond the sprint scope.
DO NOT self-approve — list all findings clearly.
```

---

## SECTION 5 — REVIEW RESULT

> Claude KHÔNG được self-approve. Kết quả phải đến từ Codex/ChatGPT/Gemini.

### Critical
_(Issues that MUST be fixed before any commit — bugs, security holes, crashes, child safety violations)_

- _(none)_

### High
_(Issues that should be fixed before merge — incorrect behavior, missing required tests, regression risk)_

- [fixed] Living state hint was prepended to `user_text`, which could pollute `BiAI.history` and interfere with RAG/persona context. Fix: added `system_context` to `ai_engine.py` and pass living context there.
- [fixed] Safety early returns (PII/risk/manipulation) could leave living state engaged/thinking and wakeword processing. Fix: `_complete_direct_response_turn()` now runs before those `continue` paths.
- [fixed] `ACTIVE_HAPPY → IDLE_SLEEPY` transition bug: `_CURIOUS_TO_SLEEPY_SECS` equalled `_HAPPY_TO_CURIOUS_SECS` (both 20 min), so fallthrough in `get_state()` jumped straight from ACTIVE_HAPPY to IDLE_SLEEPY, skipping IDLE_CURIOUS entirely. Fix: changed `_CURIOUS_TO_SLEEPY_SECS` to `40 * 60` (cumulative threshold); updated test 68.11 to 45 min; added regression test 68.23 + behavioral test 68.24.
- [fixed] Windows fallback temp DB cleanup: when `shutil.rmtree("runtime/_audit_test_db")` fails on Windows file-lock, the fallback temp dir is used but the original stale dir was never cleaned. Fix: cleanup block now also attempts to remove `runtime/_audit_test_db` when fallback was used.

### Medium
_(Issues to fix if time permits — naming, minor edge cases, readability)_

- [fixed] LivingState init was guarded by broad try/except and could silently disable the feature. Fix: initialize directly so startup failures are visible.

### Low
_(Nice-to-have improvements — style, doc comments, future-proofing)_

- [fixed] Added regression tests for package exports, system context isolation, direct response completion, and non-silent initialization.

---

## SECTION 6 — FIX STATUS

| Item | Status |
|---|---|
| Critical issues fixed? | ✅ N/A — none found |
| High issues fixed? | ✅ Yes (4 fixed including ACTIVE_HAPPY→IDLE_SLEEPY bug + Windows cleanup) |
| Re-tested after fixes? | ✅ Yes — `python tests/run_tests.py` → 497/497 PASS |
| Ready for final commit? | ✅ Yes |

---

## HISTORY — Previous Reviews

| Sprint | Task | Commit | Critical | High | Result |
|---|---|---|---|---|---|
| Sprint 1.1 | Living State Engine | _(pending)_ | 0 | 4 fixed | Ready for final commit — 497/497 PASS |
