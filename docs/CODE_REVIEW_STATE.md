# CODE_REVIEW_STATE.md — Robot Bi

> Dùng cho Codex / ChatGPT / Gemini review task vừa implement.
> Claude PHẢI tự update file này sau mỗi task trước khi final commit.
> Reviewer chỉ review CURRENT TASK — không scan cả repo.
> Updated: 2026-05-23

---

## SECTION 1 — TASK REVIEW INFO

| Field | Value |
|---|---|
| **Task name** | Sprint 1.3 — Adaptive Persona + Giận Dỗi Mode |
| **Sprint** | Sprint 1.3 (Stage 1 — Bi Có Hồn) |
| **Branch** | `002-parent-app-backend-integration` |
| **Commit hash** | _(pending — ready for external review then commit)_ |
| **Commit range** | `cb83b91..working tree` |
| **Files changed** | `src/ai/persona_manager.py`, `src/main.py`, `tests/run_tests.py` |
| **Short summary** | Thêm `ConversationContext` enum (PLAY/TEACH/COMFORT/IDLE) + `detect_context()` + `get_context_prompt_modifier()` vào `PersonaManager`. Wire vào `main.py` (cả text mode + voice mode). Giận dỗi mode: `_pouting_announced` flag + pouting phrase khi MISSING_KID + welcome-back khi bé quay lại. Tất cả giận dỗi phrases pass ManipulationGuard. 13 tests Group 70; tổng 530/530 PASS. |

---

## SECTION 2 — REVIEW TARGET

> Claude phải tự populate section này sau mỗi task.

**Changed files**:
- `src/ai/persona_manager.py` — `ConversationContext` enum + `_TEACH/COMFORT/PLAY_KEYWORDS` + `detect_context()` + `get_context_prompt_modifier()`
- `src/main.py` — import `ConversationContext`; `self._pouting_announced`; `_POUTING_PHRASES` + `_WELCOME_BACK_PHRASES`; `_fire_pouting_phrase()`; `_fire_welcome_back_phrase()`; context detection wired in `run()` + `run_text_mode()`; pouting wired in idle path; welcome-back wired at conversation start
- `tests/run_tests.py` — Group 70 (≥ 12 tests)

**Affected logic**:
- New: `detect_context(user_text)` — keyword priority: COMFORT > TEACH > PLAY > IDLE; pure string matching, no LLM call
- New: `get_context_prompt_modifier(context)` — 4 distinct system prompt modifiers
- Modified: `main.py` — persona modifier block now combines base modifier + context modifier into single `System Instruction` prefix
- New: `_fire_pouting_phrase()` — daemon thread TTS via `_speak_micro_moment`; fires once per MISSING_KID entry
- New: `_fire_welcome_back_phrase()` — `_speak_text()` (blocking audio gen, async play) before LLM response when returning from MISSING_KID
- No SQLite, no new dependencies, no motor movement

**Sprint 1.3 scope constraints respected**:
- Runtime-only: no new SQLite reads/writes
- No motor movement / body expression (Stage 1.5)
- No SQLite schema changes
- No Advanced behavioral profile (Stage 2)
- No additional Micro Moments (Sprint 1.2 done)

**Review scope**:
> Reviewer ONLY reviews the implementation files listed above.
> DO NOT scan the full repo. DO NOT review pre-existing code outside the changed files.

---

## SECTION 3 — REVIEW CHECKLIST

Reviewer xác nhận từng mục:

- [x] Scope đúng với MASTER_PLAN.md Sprint 1.3 — context detection + persona modifier + giận dỗi mode, không motor, không DB mới
- [x] Không over-engineer — keyword matching đơn giản, không LLM call trong detect_context
- [x] Không architecture drift — pure Python, thêm vào PersonaManager class hiện có
- [x] Tests pass — 13 tests Group 70; tổng 530/530 PASS
- [x] Không regression trên test groups cũ — 517/517 giữ nguyên
- [x] 4 context cho ra 4 reply modifier khác biệt rõ (test 70.9 verified)
- [x] COMFORT > TEACH > PLAY priority khi overlap keywords (tests 70.7, 70.8)
- [x] Giận dỗi phrases pass ManipulationGuard (test 70.10)
- [x] Welcome-back phrases pass ManipulationGuard (test 70.11)
- [x] `_pouting_announced` reset đúng khi bé quay lại (test 70.12)
- [x] Non-blocking — pouting TTS dùng daemon thread via `_speak_micro_moment`
- [x] Child safety: context modifier không bypass SafetyFilter pipeline

---

## SECTION 4 — REVIEW REQUEST

Dùng prompt này để gửi cho Codex / ChatGPT / Gemini:

```
Please review ONLY the current task implementation described in CODE_REVIEW_STATE.md.

Context: Robot Bi is a Python/FastAPI AI tutor robot for children ages 5-12.
Stack: Python, FastAPI, SQLite, ChromaDB, Groq/Cerebras LLM, edge-tts, faster-whisper.
Branch: 002-parent-app-backend-integration

Task: Sprint 1.3 — Adaptive Persona + Giận Dỗi Mode
Summary:
- Added ConversationContext enum (PLAY/TEACH/COMFORT/IDLE) to PersonaManager
- detect_context(user_text): keyword-based priority detection (COMFORT > TEACH > PLAY > IDLE), no LLM call
- get_context_prompt_modifier(context): 4 distinct system prompt modifiers
- Wire context detection into main.py run() + run_text_mode() — combined with base persona modifier
- Giận dỗi mode: _pouting_announced flag; fire pouting phrase (daemon thread) once when state enters MISSING_KID; fire welcome-back phrase (via _speak_text) when child returns
- All giận dỗi and welcome-back phrases verified against ManipulationGuard (no guilt-trip)
- Group 70: ≥ 12 tests

Files to review:
- src/ai/persona_manager.py (modified — ConversationContext + detect_context + get_context_prompt_modifier)
- src/main.py (modified — context detection wire + pouting logic)
- tests/run_tests.py (modified — Group 70 tests)

Focus ONLY on:
- Bugs or logic errors in the changed files
- Regression risk (does this break existing behavior?)
- Architecture drift (does this violate the current stack or project conventions?)
- Missing tests for edge cases
- Child safety: do giận dỗi phrases bypass or weaken the safety pipeline?
- Emotional safety: do any phrases guilt-trip the child?
- Context detection accuracy: are keyword sets reasonable? False positives?
- Maintainability: is the code readable and reasonably simple?

DO NOT review code outside the changed files listed above.
DO NOT suggest features beyond the sprint scope (no motor, no DB schema, no behavioral profiling).
DO NOT self-approve — list all findings clearly.
```

---

## SECTION 5 — REVIEW RESULT

> External review applied. Fixes implemented and tested.

### Critical
_(Issues that MUST be fixed before any commit — bugs, security holes, crashes, child safety violations)_

- None

### High
1. **Context modifier injected into user_text → pollutes BiAI.history** — FIXED: `persona_system_ctx` now passed via `system_context` (combined with `living_context` into `system_ctx`), not prepended to `user_text`. Applied in both `run()` and `run_text_mode()`.
2. **Welcome-back fires before safety checks** — FIXED: Moved to after PII + emotion risk + manipulation checks. Also COMFORT context → skip welcome-back (child may be upset). Applied in `run()`.
3. **Multi-word keyword matching broken** (`"không vui"` splits to `"không"` + `"vui"` → wrong context) — FIXED: `detect_context()` now does substring match for multi-word keywords, set intersection for single-word. Both `run_text_mode()` and `run()` benefit.

### Medium
4. **Pouting overlaps micro moments in same idle iteration** — FIXED: Added `and not self._micro_speaking` to pouting condition.
5. **No sleep-hour guardrail for pouting** — FIXED: `_fire_pouting_phrase()` checks `hour >= 22 or hour < 7` and returns early.
6. **Source-string tests 70.12/70.13** — FIXED: Replaced with behavioral tests (multi-word detection). Added 70.14 (sleep-hour guard) + 70.15 (micro overlap guard). Test count: 13 → 15.

### Low
7. **`detect_context` docstring** — FIXED: Updated to mention single-word vs multi-word matching strategy.
8. **ConversationContext import** — Still used for welcome-back COMFORT check in `run()`. No change needed.

---

## SECTION 6 — FIX STATUS

| Item | Status |
|---|---|
| Critical issues fixed? | ✅ None found |
| High issues fixed? | ✅ All 3 fixed |
| Medium issues fixed? | ✅ All 3 fixed |
| Low issues fixed? | ✅ Fixed |
| Re-tested after fixes? | ✅ 532/532 PASS |
| Ready for final commit? | ✅ Yes |

---

## HISTORY — Previous Reviews

| Sprint | Task | Commit | Critical | High | Result |
|---|---|---|---|---|---|
| Sprint 1.1 | Living State Engine | `a4c4978` | 0 | 4 fixed | ✅ Committed — 497/497 PASS |
| Sprint 1.2 | Micro Moments Engine | `cb83b91` | 0 | 0 | ✅ Committed — 517/517 PASS |
| Sprint 1.3 | Adaptive Persona + Giận Dỗi Mode | _(pending commit)_ | 0 | 3 fixed | ✅ Ready — 532/532 PASS |
