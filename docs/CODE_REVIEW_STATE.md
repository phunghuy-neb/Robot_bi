# CODE_REVIEW_STATE.md — Robot Bi

> Dùng cho Codex / ChatGPT / Gemini review task vừa implement.
> Claude PHẢI tự update file này sau mỗi task trước khi final commit.
> Reviewer chỉ review CURRENT TASK — không scan cả repo.
> Updated: 2026-05-23

---

## SECTION 1 — TASK REVIEW INFO

| Field | Value |
|---|---|
| **Task name** | _(populate sau khi implement)_ |
| **Sprint** | _(e.g., Sprint 1.1 — Living State Engine)_ |
| **Branch** | `002-parent-app-backend-integration` |
| **Commit hash** | _(populate sau khi implement)_ |
| **Commit range** | _(e.g., `aad6072..HEAD`)_ |
| **Files changed** | _(populate sau khi implement)_ |
| **Short summary** | _(1–2 câu mô tả task vừa xong)_ |

---

## SECTION 2 — REVIEW TARGET

> Claude phải tự populate section này sau mỗi task.

**Changed files**:
- _(list file paths)_

**Affected logic**:
- _(e.g., main conversation loop, state machine, safety pipeline)_

**Risk areas**:
- _(e.g., new state transitions, prompt injection from state context, blocking code in async loop)_

**Review scope**:
> Reviewer ONLY reviews the files and logic listed above.
> DO NOT scan the full repo. DO NOT review pre-existing code outside the changed files.

---

## SECTION 3 — REVIEW CHECKLIST

Reviewer xác nhận từng mục:

- [ ] Scope đúng với MASTER_PLAN.md cho sprint này
- [ ] Không over-engineer (không thêm abstraction không cần thiết)
- [ ] Không architecture drift (không vi phạm stack hiện tại: FastAPI/SQLite/Groq/ChromaDB)
- [ ] Tests pass (`python tests/run_tests.py`)
- [ ] Không regression trên test groups cũ
- [ ] Không fake implementation (không mock để pass, không stub trả hardcoded)
- [ ] Naming consistency (snake_case Python, kebab-case routes, camelCase JS)
- [ ] Child safety maintained (safety pipeline không bị bypass)
- [ ] Performance acceptable (không blocking main loop, không memory leak rõ ràng)

---

## SECTION 4 — REVIEW REQUEST

Dùng prompt này để gửi cho Codex / ChatGPT / Gemini:

```
Please review ONLY the current task implementation described in CODE_REVIEW_STATE.md.

Context: Robot Bi is a Python/FastAPI AI tutor robot for children ages 5-12.
Stack: Python, FastAPI, SQLite, ChromaDB, Groq/Cerebras LLM, edge-tts, faster-whisper.
Branch: 002-parent-app-backend-integration

Task: [paste SECTION 1 task name and summary]

Files to review: [paste SECTION 2 changed files list]

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

- _(none yet — awaiting review)_

### High
_(Issues that should be fixed before merge — incorrect behavior, missing required tests, regression risk)_

- _(none yet — awaiting review)_

### Medium
_(Issues to fix if time permits — naming, minor edge cases, readability)_

- _(none yet — awaiting review)_

### Low
_(Nice-to-have improvements — style, doc comments, future-proofing)_

- _(none yet — awaiting review)_

---

## SECTION 6 — FIX STATUS

| Item | Status |
|---|---|
| Critical issues fixed? | _(N/A — no implementation yet)_ |
| High issues fixed? | _(N/A — no implementation yet)_ |
| Re-tested after fixes? | _(N/A — no implementation yet)_ |
| Ready for final commit? | ⬜ No |

---

## HISTORY — Previous Reviews

| Sprint | Task | Commit | Critical | High | Result |
|---|---|---|---|---|---|
| _(first review will appear here after Sprint 1.1)_ | — | — | — | — | — |
