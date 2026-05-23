# EXECUTION_STATE.md — Robot Bi

> Source of truth cho Claude execution.
> Không phụ thuộc chat history. Đọc file này để biết current position, completed work, deferred items, và next task.
> Updated: 2026-05-23

---

## SECTION 1 — CURRENT POSITION

| Field | Value |
|---|---|
| **Current Stage** | Stage 1 — Bi Có Hồn (Living Engine) |
| **Current Sprint** | Sprint 1.1 — Living State Engine (CHƯA BẮT ĐẦU) |
| **Current Status** | Stage 0 hoàn thành. Sẵn sàng bắt đầu Stage 1. |
| **Project Mode** | Software-First. Hardware sau Stage 4+. |
| **Active Branch** | `002-parent-app-backend-integration` |
| **Test command** | `python tests/run_tests.py` |
| **Last commit** | `d844d62` — test: make embedding tests deterministic |

---

## SECTION 2 — COMPLETED

### Stage 0 — Foundation Truth Reset ✅ DONE

**Goal**: Docs khớp code, safety upgrade, wake word decision, test pass 100%.

---

**Sprint 0.1** — Sync Docs to Code Reality
- Goal: Đảm bảo tất cả doc file phản ánh đúng code thực tế.
- Outcome: `PROJECT.md` updated với 5-provider LLM chain, RAG threshold 0.62, edge-tts internet note, wake word disabled by default, firmware stubs flagged. `ARCHITECTURE.md`, `SRS_Robot_Bi_v2.md`, `BACKLOG_Robot_Bi_v2.md` sửa. `docs/STATUS_MAP.md` tạo mới (93-item feature map). `CLAUDE.md` + `AGENTS.md` regenerated. Commit: `479d850`.

**Sprint 0.2** — Child Safety Foundation
- Goal: PII filter + emotional safety + manipulation guard trước LLM và sau LLM.
- Outcome: 4 module mới (`vi_normalize.py`, `pii_filter.py`, `emotion_risk_detector.py`, `manipulation_guard.py`), 37 tests (Group 65), tích hợp vào `main.py` cả TEXT mode + VOICE mode. 430/431 PASS. Commits: `1ba66ec`, `12113d2`.

**Sprint 0.3** — Wake Word Foundation
- Goal: Wake word infrastructure, state machine, 3 backends, tích hợp `main.py`.
- Outcome: 6 file mới trong `src/wakeword/`, state machine (IDLE/LISTENING/PROCESSING/COOLDOWN), 3 backends (openwakeword/whisper/placeholder), 24 tests (Group 66). Model CHƯA train — đây là foundation. Commit: `c8fe264`.

**Sprint 0.4** — Wake Word Training Pipeline
- Goal: Pipeline hoàn chỉnh để train wake word model từ synthetic dataset.
- Outcome: 4 scripts mới (`generate_wakeword_dataset.py`, `augment_audio.py`, `train_wakeword.py`, `test_wakeword.py`), `custom_mfcc` backend trong `wakeword_service.py`, 19 tests (Group 67), `scikit-learn>=1.4.0` trong `requirements.txt`. Pipeline SẴNG SÀNG — dataset chưa generate, model chưa train. Commit: `aad6072`.

---

## SECTION 3 — DEFERRED

### Human Mic Validation for Wake Word

| Field | Detail |
|---|---|
| **Status** | 🟡 Partial — Pipeline sẵn sàng, chưa validate bằng mic thật |
| **Reason deferred** | Chưa có thời gian; cần người ngồi nói "Bi ơi" trực tiếp |
| **Must complete before** | Stage 1.5 hoặc trước khi deploy robot thật với user |
| **Wake Word overall** | 🟡 Partial / Ready for Human Validation |
| **How to run** | `python scripts/generate_wakeword_dataset.py` → `augment_audio.py` → `train_wakeword.py` → `test_wakeword.py` |
| **Target** | 8/10 "Bi ơi" detections trong môi trường bình thường |
| **Enable in .env** | `WAKEWORD_ENABLED=true`, `WAKEWORD_BACKEND=custom_mfcc`, `WAKEWORD_CUSTOM_MODEL_PATH=runtime/wakeword/bi_oi_classifier.pkl` |

---

## SECTION 4 — NEXT TASK

### Sprint 1.1 — Living State Engine

**Stage**: Stage 1 — Bi Có Hồn (Living Engine)

**Goal**: Build hệ thống trạng thái bên trong của Bi. Bi không còn là chatbot chờ lệnh — Bi có cuộc sống bên trong với 7+ trạng thái, transition rules, và context-aware response tone.

**Scope**:
- `src/living/living_state.py` — state machine với ≥ 7 states: IDLE_CURIOUS, IDLE_SLEEPY, ACTIVE_HAPPY, ACTIVE_ENGAGED, POUTING, THINKING, MISSING_KID
- Transition rules: idle time → sleepy, interaction → happy, long no-contact → missing kid, bad reply → pouting
- Living state exposed tới `main.py` để prompt context thay đổi theo state
- `src/living/__init__.py`
- Tests: Group 68 — state creation, transitions, invalid transitions, get_current_state, state metadata
- Tích hợp nhẹ vào `main.py`: state update sau mỗi turn, state context vào system prompt

**What NOT to build**:
- Micro Moments Engine (Sprint 1.2)
- Giận dỗi mode với motor movement (Stage 1.5)
- Emotional Safety runtime check (Sprint 1.3)
- Bất kỳ UI nào
- Không thêm database schema mới

**Definition of Done**:
- `LivingState` class với ≥ 7 states và transition rules
- State persists in-memory (không cần SQLite — state là runtime)
- `main.py` inject state context vào system prompt khi build messages
- Tests pass: ≥ 12 tests cho state machine (transitions, get_state, idle_timer, state_metadata)
- `python tests/run_tests.py` 100% pass
- `CODE_REVIEW_STATE.md` updated sau khi implement

---

## SECTION 5 — EXECUTION RULES

1. **Đọc MASTER_PLAN.md trước** — xác nhận task đang làm đúng với plan.
2. **Chỉ execute current task** — không jump sang sprint tiếp theo.
3. **Tối đa 2 tasks mỗi run** — nếu task lớn, tách ra.
4. **Không feature creep** — nếu thấy cần thêm, ghi vào deferred, không build.
5. **Small commits** — commit sau mỗi unit hoàn chỉnh, không commit blob lớn.
6. **Test trước khi commit** — `python tests/run_tests.py` phải pass.
7. **Update CODE_REVIEW_STATE.md sau implement** — trước khi commit final.
8. **Stop for review trước final commit** — để reviewer (Codex/ChatGPT/Gemini) check.
9. **Không fake pass** — nếu test fail, fix trước, không skip/mock để pass.
10. **Không commit broken tests** — kể cả pre-existing failures phải được ghi chú rõ.
11. **Respect deferred items** — không build deferred item trừ khi user yêu cầu.
12. **Cập nhật EXECUTION_STATE.md** khi sprint kết thúc.

---

## SECTION 6 — EXECUTION LOG

| Date | Done | Commit | Next |
|---|---|---|---|
| 2026-05-20 | Sprint 0.1: Sync docs | `479d850` | Sprint 0.2 |
| 2026-05-20 | Sprint 0.2: Child Safety Foundation | `1ba66ec`, `12113d2` | Sprint 0.3 |
| 2026-05-20 | Sprint 0.3: Wake Word Foundation | `c8fe264` | Sprint 0.4 |
| 2026-05-20 | Sprint 0.4: Wake Word Training Pipeline | `aad6072` | Sprint 1.1 |
| 2026-05-23 | Created EXECUTION_STATE.md + CODE_REVIEW_STATE.md | _(this commit)_ | Sprint 1.1 — Living State Engine |
