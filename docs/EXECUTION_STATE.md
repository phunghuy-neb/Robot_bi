# EXECUTION_STATE.md — Robot Bi

> Source of truth cho Claude execution.
> Không phụ thuộc chat history. Đọc file này để biết current position, completed work, deferred items, và next task.
> Updated: 2026-05-23

---

## SECTION 1 — CURRENT POSITION

| Field | Value |
|---|---|
| **Current Stage** | Stage 1 — Bi Có Hồn (Living Engine) |
| **Current Sprint** | Sprint 1.3 — Adaptive Persona + Giận Dỗi Mode |
| **Current Status** | Sprint 1.2 committed. `python tests/run_tests.py` PASS 517/517. Next: Sprint 1.3. |
| **Project Mode** | Software-First. Hardware sau Stage 4+. |
| **Active Branch** | `002-parent-app-backend-integration` |
| **Test command** | `python tests/run_tests.py` |
| **Last commit** | _(Sprint 1.2 — Micro Moments Engine, all review fixes applied)_ |

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

**Sprint 1.1** — Living State Engine ✅ DONE
- Goal: Runtime-only state machine để Bi có trạng thái bên trong khi trò chuyện.
- Outcome: `src/living/living_state.py` với 7 states, tích hợp vào text mode + voice mode. Living hint đi qua `system_context`, không pollute user/RAG history. Safety early-response paths hoàn tất living/wakeword lifecycle. Bug fix: `ACTIVE_HAPPY→IDLE_SLEEPY` skip (`_CURIOUS_TO_SLEEPY_SECS` cumulative threshold 40 min). Windows fallback temp DB cleanup added. 24 tests (Group 68), tổng 497/497 PASS. Commit: `a4c4978`.

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

### Sprint 1.3 — Adaptive Persona + Giận Dỗi Mode

**Stage**: Stage 1 — Bi Có Hồn (Living Engine)

**Goal**: Tone Bi thay đổi theo context (play/teach/comfort/idle). Bi giận dỗi khi bị bỏ mặc quá lâu — không guilt-trip.

**Scope (from MASTER_PLAN.md Sprint 1.3)**:
- `detect_context(user_text, recent_history)` in `src/ai/persona_manager.py` — 4 context: play / teach / comfort / idle
- 4 system prompt modifier khác nhau cho từng context
- Wire context detection vào main loop trước khi build prompt
- Giận dỗi trigger: bé vắng X phút, Bi chào nhưng không trả lời → `MISSING_KID`
- Giận dỗi sequence: voice hờn nhẹ (không guilt-trip) + state reset khi bé quay lại
- Verify mọi câu giận dỗi pass emotional safety filter
- Tests: Group 70 (≥ 12 tests)

**What NOT to build**:
- Motor movement / body expression (Stage 1.5)
- SQLite schema mới (runtime-only)
- Advanced behavioral profile (Stage 2)
- Micro Moments thêm (đã xong Sprint 1.2)

**Definition of Done**:
- 4 context cho ra 4 reply khác biệt rõ
- Giận dỗi sequence không có câu guilt-trip (kiểm tra qua ManipulationGuard)
- Tests pass: ≥ 12 tests
- `python tests/run_tests.py` 100% pass
- `CODE_REVIEW_STATE.md` updated

---

### Sprint 1.2 — Micro Moments Engine ✅ DONE

**Outcome**: `src/living/micro_moments.py` — `MomentId` (8 moments, YAWN renamed) + `MicroMomentsEngine`. Rate limit 15 phút, guardrails homework + sleep hours 22:00–07:00. Wire vào `main.py` idle path with `_micro_speaking` guard and puppet overlap fix. 20 tests (Group 69), tổng 517/517 PASS.

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
13. **Claude MUST stop after implementation and update CODE_REVIEW_STATE.md** — không tiếp tục commit trước khi file được điền đầy đủ.
14. **Claude MUST wait for external review before final commit** — Codex/ChatGPT/Gemini phải review trước. Claude không tự approve.

---

## SECTION 6 — EXECUTION LOG

| Date | Done | Commit | Next |
|---|---|---|---|
| 2026-05-20 | Sprint 0.1: Sync docs | `479d850` | Sprint 0.2 |
| 2026-05-20 | Sprint 0.2: Child Safety Foundation | `1ba66ec`, `12113d2` | Sprint 0.3 |
| 2026-05-20 | Sprint 0.3: Wake Word Foundation | `c8fe264` | Sprint 0.4 |
| 2026-05-20 | Sprint 0.4: Wake Word Training Pipeline | `aad6072` | Sprint 1.1 |
| 2026-05-23 | Created EXECUTION_STATE.md + CODE_REVIEW_STATE.md | _(this commit)_ | Sprint 1.1 — Living State Engine |
| 2026-05-23 | Sprint 1.1: Living State Engine + all review fixes; 497/497 PASS | `a4c4978` | Sprint 1.2 — Micro Moments Engine |
| 2026-05-23 | Sprint 1.2: Micro Moments Engine — all review fixes applied; 517/517 PASS | _(this commit)_ | Sprint 1.3 — Adaptive Persona + Giận Dỗi Mode |
