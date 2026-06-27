# Tasks: Learning Hub Redesign (tab Học tập)

> Spec: [spec.md](./spec.md) · Plan: [plan.md](./plan.md) · Created 2026-06-28
> Build theo LÁT (L1-A→L1-I), mỗi lát = 1 increment độc lập: commit riêng + `npm run build` + (nếu chạm BE) `python tests/run_tests.py` + cập nhật `.claude/handoff.md`.
> Chỉ làm **Lớp 1** (US1-US10) đợt này. Lớp 2 (US11-US14) đợt sau.

## Quyết định chốt tại tasks
- **Endpoint mới đặt trong `src/api/routers/learning_hub_router.py`** (tái dùng helper exam_router), đều `Depends(get_current_user)` + scope `family_id`, output LLM qua SafetyFilter.
- KHÔNG bảng/cột mới: Sổ lỗi + Mastery suy từ `exam_sessions.answers_json` × `question_bank` (cột `topic`, `answer`).
- Hằng số FE (`CATEGORY_MAP`, `BO_GD_SUBJECTS`, `IELTS_TOEIC_MOCK`) ở `components/learning/constants.js` — dễ chỉnh.
- "Bi đọc đề" = browser `SpeechSynthesis` (client); "trả lời giọng" tái dùng STT TOEIC (tùy chọn).
- Mastery band: <60 Cần cố gắng · 60-79 Khá · 80-89 Thạo · ≥90 Làm chủ (accuracy theo topic).

---

## Phase 1: Setup
- [x] T001 Baseline `python tests/run_tests.py` = PASS (722/722)
- [x] T002 [P] Hằng số FE: `CATEGORIES` (môn→danh mục), `BO_GD_SUBJECTS`, `MOCK_EXAM_SUBJECTS`, `TIMER_OPTIONS`, `categoryOf()`, `masteryBand()` — file: `frontend/parent_app/src/components/learning/constants.js`
- [x] T003 [P] `styles.css`: `.learn-browse{max-width:1280}` / `.learn-quiz{max-width:640}` + `.subject-grid` (auto-fill minmax140, 132 ở ≤360) + `.subject-card` + `.subject-cat-title` clamp + 4 mã màu mastery — file: `frontend/parent_app/src/styles.css`

## Phase 2: Foundational (blocking)
- [x] T004 `services/api.js`: `getLearningSubjects()` + helpers `getMistakes/getTopicMastery/getPracticeQuestions/gradePractice/askBiExplain` (dùng ở US4-US7) — file: `frontend/parent_app/src/services/api.js`
- [x] T005 `LearningHubPage.jsx`: state `hubView` ('subjects' default); early-return lưới môn; GIỮ NGUYÊN luồng learn/exam cũ phía sau (US2 sẽ thay bằng SubjectDetail) — file: `frontend/parent_app/src/pages/LearningHubPage.jsx`

---

## Phase 3: US1 (L1-A) — Lưới môn subject-first · Test: mở tab thấy mọi môn nhóm danh mục + search lọc đúng, full-width không co giữa
- [x] T006 [P] [US1] `components/learning/SubjectCard.jsx` — thẻ môn (emoji+tên+số đề), tap mở môn — file: `frontend/parent_app/src/components/learning/SubjectCard.jsx`
- [x] T007 [US1] `components/learning/SubjectGrid.jsx` — lưới trong `.learn-browse`, nhóm theo `CATEGORIES` (+ "Khác"), search lọc, loading/empty/error — file: `frontend/parent_app/src/components/learning/SubjectGrid.jsx`
- [x] T008 [US1] Gắn SubjectGrid làm cửa trước LearningHubPage; `pickSubject` → set activeSubject + mode (learn cho en/math/science, exam cho còn lại) + hubView='detail'; nút "← Môn" trong ModeToggle về lưới — file: `frontend/parent_app/src/pages/LearningHubPage.jsx`
- [x] T009 [US1] `npm run build` OK (1.43s); baseline 722/722 PASS (FE-only, không đụng Python) — file: `frontend/parent_app/`

## Phase 4: US2 + US8 (L1-B) — Trang chi tiết môn + thẻ chế độ + gating · Test: thẻ chế độ đúng theo môn (Bộ GD có HSG/chuyển cấp; IELTS/TOEIC có "đề thật"; còn lại Nâng cao)
- [x] T010 [P] [US2] `components/learning/ModeCard.jsx` — thẻ chế độ lớn (icon+nhãn+sub) — file: `frontend/parent_app/src/components/learning/ModeCard.jsx`
- [x] T011 [US2] `components/learning/SubjectDetail.jsx` — header môn (back) + dải ModeCard + 2 thẻ "Câu hay sai"/"Chủ đề cần ôn" (placeholder, số thật ở US5/US6); 2 cột ≥1024 — file: `frontend/parent_app/src/components/learning/SubjectDetail.jsx`
- [x] T012 [US8] Gating: Lộ trình (en/math/science thật, còn lại "Sắp có") · Luyện theo bài (toast interim, US4) · Luyện theo đề (mọi môn) · Bộ GD→HSG+Chuyển cấp · IELTS/TOEIC→"Thi thử như thật" · còn lại→Nâng cao. LearningHubPage: hubView 3 trạng thái subjects/subjectMenu/inMode; pickSubject→subjectMenu; chọn chế độ→switchMode+inMode; "← Môn"→subjectMenu — file: `SubjectDetail.jsx`, `pages/LearningHubPage.jsx`
- [x] T013 [US2] `npm run build` OK (69 modules, 1.18s; fix trùng tên state subjectInfo→pickedSubject) — file: `frontend/parent_app/`

## Phase 5: US3 (L1-C) — Luyện theo đề (tái dùng) + cấu hình timer · Test: chọn đề + giờ → làm trọn đề → chấm cuối (như cũ), trong cột hẹp
- [x] T014 [US3] Cấu hình timer làm INLINE trong list view (chips "Theo đề/Không giờ/15/30/45/60" — `examTimerMin`) thay vì tách `ModeConfig.jsx` (gọn hơn; tách sau nếu US4 cần) — file: `frontend/parent_app/src/pages/LearningHubPage.jsx`
- [x] T015 [US3] `openSubjectExams()` lọc đề theo môn (`getExams({subject})`); "Luyện theo đề" + HSG/Chuyển cấp/Nâng cao/Thi-thử route qua đây (examFromSubject); startExam áp timer override + `examNoTimer` (bỏ đếm giờ + ẩn auto-submit); nút back về subjectMenu; playing giữ cột hẹp 560 — file: `frontend/parent_app/src/pages/LearningHubPage.jsx`
- [x] T016 [US3] `npm run build` OK (69 modules, 1.22s); FE-only (baseline 722 giữ) — file: `frontend/parent_app/`

## Phase 6: US4 (L1-D) — Luyện theo bài (chấm từng câu) · Test: làm câu đơn lẻ, server chấm + giải thích ngay, mọi môn
- [ ] T017 [US4] `learning_hub_router.py`: `GET /api/learning/practice?subject=&topic=&limit=` (lấy câu từ question_bank, family-scope) + `POST /api/learning/practice/grade` (chấm 1 câu, trả đúng/sai + đáp án + explanation; giữ đáp án ở server) — file: `src/api/routers/learning_hub_router.py`
- [ ] T018 [US4] `services/api.js`: `getPracticeQuestions`, `gradePractice` — file: `frontend/parent_app/src/services/api.js`
- [ ] T019 [US4] `components/learning/QuestionRunner.jsx` — chạy câu hỏi: hiện câu + đáp án; sau trả lời → phản hồi + giải thích ngay; timer tùy chọn; nút "Câu tiếp" — file: `frontend/parent_app/src/components/learning/QuestionRunner.jsx`
- [ ] T020 [US4] Test **Group mới**: practice trả câu theo môn (cô lập family); grade chấm đúng + không lộ đáp án ở list — file: `tests/run_tests.py`
- [ ] T021 [US4] `npm run build` OK + `python tests/run_tests.py` PASS — file: `frontend/parent_app/`, `tests/`

## Phase 7: US5 (L1-E) — Sổ lỗi · Test: gom đúng câu từng sai theo family, ôn lại được, đếm khớp
- [ ] T022 [US5] `learning_hub_router.py`: `GET /api/learning/mistakes?subject=` — suy câu sai từ `exam_sessions.answers_json` × `question_bank.answer`, nhóm môn/chủ đề, scope family — file: `src/api/routers/learning_hub_router.py`
- [ ] T023 [US5] `services/api.js`: `getMistakes`; `components/learning/ErrorBook.jsx` — list câu sai + "Luyện lại" (đẩy vào QuestionRunner) — file: `frontend/parent_app/src/services/api.js`, `components/learning/ErrorBook.jsx`
- [ ] T024 [US5] Cập nhật thẻ "📕 Câu hay sai (n)" ở SubjectDetail dùng số thật — file: `frontend/parent_app/src/components/learning/SubjectDetail.jsx`
- [ ] T025 [US5] Test: mistakes cô lập family + đếm khớp answers_json; empty state khi không có — file: `tests/run_tests.py`
- [ ] T026 [US5] `npm run build` + `run_tests` PASS — file: `frontend/parent_app/`, `tests/`

## Phase 8: US6 (L1-F) — Mastery theo chủ đề · Test: điểm 0-100 + band màu+chữ; cô lập family; chủ đề yếu nổi lên
- [ ] T027 [US6] `learning_hub_router.py`: `GET /api/learning/mastery?subject=` — accuracy theo `topic` → band, scope family — file: `src/api/routers/learning_hub_router.py`
- [ ] T028 [US6] `services/api.js`: `getTopicMastery`; `components/learning/MasteryByTopic.jsx` — thanh % + band (màu KÈM chữ) trong `CollapsibleSection` — file: `frontend/parent_app/src/services/api.js`, `components/learning/MasteryByTopic.jsx`
- [ ] T029 [US6] Gắn MasteryByTopic + thẻ "🎯 Chủ đề cần ôn" (top yếu) vào SubjectDetail; vòng mastery môn trên SubjectCard — file: `frontend/parent_app/src/components/learning/SubjectDetail.jsx`, `SubjectCard.jsx`
- [ ] T030 [US6] Test: mastery band đúng ngưỡng + cô lập family — file: `tests/run_tests.py`
- [ ] T031 [US6] `npm run build` + `run_tests` PASS — file: `frontend/parent_app/`, `tests/`

## Phase 9: US7 (L1-G) — Hỏi Bi vì sao sai + Bi đọc đề · Test: explain qua SafetyFilter, Socratic; 🔊 đọc đề; con bị chặn? (explain child-safe)
- [ ] T032 [US7] `learning_hub_router.py`: `POST /api/learning/explain` — `{question, child_answer, correct_answer}` → `stream_chat` role teacher (Socratic, không cho đáp án thẳng) → **SafetyFilter** → trả; `run_in_threadpool`; fallback `question_bank.explanation` — file: `src/api/routers/learning_hub_router.py`
- [ ] T033 [US7] `services/api.js`: `askBiExplain`; `components/learning/AskBi.jsx` (nút "🤖 Hỏi Bi vì sao", hiển thị giải thích, trạng thái loading/error) — file: `frontend/parent_app/src/services/api.js`, `components/learning/AskBi.jsx`
- [ ] T034 [US7] QuestionRunner: nút 🔊 "Bi đọc đề" (SpeechSynthesis vi-VN) + tích hợp AskBi sau câu sai — file: `frontend/parent_app/src/components/learning/QuestionRunner.jsx`
- [ ] T035 [US7] Test: explain output đi qua SafetyFilter (không lộ nội dung chặn); fallback khi LLM lỗi — file: `tests/run_tests.py`
- [ ] T036 [US7] `npm run build` + `run_tests` PASS — file: `frontend/parent_app/`, `tests/`

## Phase 10: US9 (L1-H) — Khung "Lộ trình" (shell) · Test: 3 môn (en/math/science) hiện module thật; môn khác "Sắp có"
- [ ] T037 [US9] View "Lộ trình" trong SubjectDetail: en/math/science tái dùng `getLearningModules`/module cũ; môn khác hiện trạng thái "Sắp có" rõ ràng — file: `frontend/parent_app/src/pages/LearningHubPage.jsx` (+ components/learning)
- [ ] T038 [US9] `npm run build` OK + kiểm 3 môn thật + 1 môn "Sắp có" — file: `frontend/parent_app/`

## Phase 11: Polish & Cross-Cutting (US10 + docs)
- [ ] T039 [P] [US10] Responsive sweep: rà 320/360/390/414/600/768/1024/1280/1440/1920 — không cuộn ngang, browse rộng/quiz hẹp, tablet 1 cột/≥1024 2 cột; a11y (tap≥48, contrast, focus, màu+chữ) — file: `frontend/parent_app/src/`
- [ ] T040 [P] Cập nhật `docs/DESIGN_SYSTEM.md` (breakpoints + container browse/quiz + mastery color) + `SYSTEM_MAP.md`/`docs/STATUS_MAP.md` (tab Học tập subject-first, endpoint learning mới, sổ lỗi/mastery/Hỏi-Bi) — file: `docs/`, `SYSTEM_MAP.md`
- [ ] T041 `python tests/run_tests.py` toàn bộ PASS (gồm Group learning mới) + đối chiếu Protected Fixes không hồi quy — file: `tests/`
- [ ] T042 Cập nhật `.claude/handoff.md` (Rule 9) — file: `.claude/handoff.md`

---

## Dependencies & thứ tự
- Phase 1 → 2 → các US theo L1-A→L1-I.
- US1 (grid) → US2 (detail) → US3 (luyện đề) là chuỗi nền.
- US4/US5/US6/US7 độc lập tương đối SAU khi có US2 (đều gắn vào SubjectDetail/QuestionRunner) — có thể đảo thứ tự, nhưng QuestionRunner (US4) nên xong trước US7 (AskBi gắn vào nó) và US5 "luyện lại" (dùng QuestionRunner).
- US9 (Lộ trình shell) độc lập, làm lúc nào cũng được sau US2.
- Polish cuối.

## Parallel opportunities
- T002 ∥ T003 (constants ∥ css). T006 ∥ (chuẩn bị T010). Các endpoint BE (T017/T022/T027/T032) khác nhau → có thể làm nối tiếp nhanh; FE component tương ứng [P] khi khác file.

## MVP / Independent test
- **MVP** = US1 + US2 + US3 (duyệt môn → vào môn → luyện theo đề) — đã là một tab học dùng được.
- Gia tăng giá trị "gia sư": US5 Sổ lỗi + US6 Mastery + US7 Hỏi Bi.
- US4 (luyện theo bài) + US9 (Lộ trình shell) hoàn thiện đủ chế độ.

## Independent test criteria (tóm tắt)
- US1: lưới mọi môn + search + full-width.
- US2/US8: thẻ chế độ đúng theo môn (HSG/Nâng cao/IELTS-TOEIC mock).
- US3: luyện đề có/không giờ, cột hẹp.
- US4: chấm từng câu + giải thích ngay (server chấm).
- US5: sổ lỗi đúng + cô lập family.
- US6: mastery band màu+chữ + cô lập family.
- US7: Hỏi Bi qua SafetyFilter + 🔊 đọc đề.
- US9: 3 môn Lộ trình thật + còn lại "Sắp có".
- US10: hoàn hảo mọi màn 320→1920.
