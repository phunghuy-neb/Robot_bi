# Implementation Plan: Learning Hub Redesign (tab Học tập)

> Spec: [spec.md](./spec.md) · Created 2026-06-28 · Feature dir `.specify/specs/007-learning-hub/`
> Convention plan gọn (như 004/005/006). Build theo LÁT, mỗi lát commit + review.

## Technical Context

- **FE**: React 18 + Vite, CSS thuần + design token (`:root`), không React Router. `LearningHubPage.jsx` (1007 dòng) là file chính sẽ tái cấu trúc lớn → tách thành nhiều component.
- **BE**: FastAPI + SQLite. Endpoint học tập đã có trong `exam_router.py` (`/api/learning/*`) + `learning_hub_router.py` (`/api/learning/modules`).
- **Khả thi Lớp 1 (đã xác minh từ code)**:
  - `exam_sessions.answers_json` lưu `{question_id: answer}` per phiên → suy được **câu sai** (so với `question_bank.answer`) cho **Sổ lỗi**; join `question_bank.topic` → **Mastery theo chủ đề**. **KHÔNG cần bảng mới.**
  - `question_bank` có cột `topic` (nguồn chủ đề cho mastery + nhóm sổ lỗi).
  - Đề detail **ẩn đáp án** (integrity) → "Luyện theo bài" cần **chấm phía server** (không chấm client được).
  - **Chưa có** endpoint LLM giải thích child-safe → "Hỏi Bi vì sao sai" cần **1 endpoint mới** (LLM + SafetyFilter).
  - "Bi đọc đề" dùng **browser SpeechSynthesis** (client, đã dùng ở JournalPage playback) → không cần BE. "Trả lời bằng giọng" tái dùng STT TOEIC khi cần.
- **Lớp 1 KHÔNG thuần FE** (đính chính spec): cần thêm **vài endpoint BE mỏng, read/LLM, không schema mới** (mistakes, mastery, practice-grade, explain). Rủi ro thấp.

## Constitution / Protected-Fixes Check

Không có `.specify/memory/constitution.md`; ràng buộc = Protected Fixes (PROJECT.md).

| Protected Fix | Ảnh hưởng | Cách giữ |
|---|---|---|
| Cô lập đa gia đình | Endpoint mistakes/mastery/practice mới | BẮT BUỘC scope `family_id` (lấy từ JWT) như exam_router hiện tại |
| Chấm đề / TOEIC S&W | "Luyện theo đề" tái dùng | KHÔNG sửa luồng chấm hiện có; chỉ thêm "luyện theo bài" (chấm từng câu) song song |
| SafetyFilter post-LLM/pre-TTS | "Hỏi Bi vì sao sai" | Output LLM **đi qua SafetyFilter** trước khi tới trẻ (giống TOEIC feedback/tips) |
| Chuỗi 5 LLM | endpoint explain | Tái dùng `stream_chat`/role teacher hiện có; bọc `run_in_threadpool` trong async handler |
| DB path/schema (tasks/conversations/turns) | Không đụng | Sổ lỗi/mastery DERIVE từ exam_sessions+question_bank, **không tạo/sửa bảng** |
| Child-safety | leaderboard/social | Lớp 1 không có leaderboard; Lớp 2 family-scoped only |

→ **Không vi phạm.** Rủi ro chính = tái cấu trúc FE lớn (giảm bằng build từng lát, giữ luồng exam cũ).

## Architecture & Affected Files

### Frontend (tái cấu trúc `LearningHubPage.jsx` → nhiều component)
- `pages/LearningHubPage.jsx`: đổi thành **router nội bộ theo view** (subjectGrid → subjectDetail → mode config → playing → result). Bỏ wrapper `maxWidth:480/560 căn giữa` ở view duyệt; chỉ giữ cột hẹp 640 ở view làm bài.
- `components/learning/SubjectGrid.jsx` (MỚI): lưới môn nhóm danh mục + search; gọi `getLearningSubjects()`. Container ≤1280 căn giữa.
- `components/learning/SubjectCard.jsx` (MỚI): thẻ môn + vòng mastery nhỏ.
- `components/learning/SubjectDetail.jsx` (MỚI): header môn + dải thẻ chế độ + 2 thẻ (Sổ lỗi/Chủ đề yếu) + MasteryByTopic (accordion). 2 cột ≥1024.
- `components/learning/ModeConfig.jsx` (MỚI): chọn đề/cấp (dropdown) + timer (Không/15/30/45/60) → Bắt đầu. Bottom sheet mobile / modal desktop.
- `components/learning/QuestionRunner.jsx` (MỚI hoặc tách từ logic cũ): chạy câu hỏi cho "luyện theo bài" (chấm từng câu) + tái dùng cho "luyện đề"; nút 🔊 Bi đọc (SpeechSynthesis) + "🤖 Hỏi Bi".
- `components/learning/ErrorBook.jsx` (MỚI): Sổ lỗi — list câu sai nhóm theo môn/chủ đề + luyện lại.
- `components/learning/MasteryByTopic.jsx` (MỚI): thanh % + mã màu + chữ (dùng `CollapsibleSection`).
- `components/learning/AskBi.jsx` (MỚI): gọi explain endpoint, hiển thị giải thích Socratic.
- `services/api.js`: thêm `getLearningSubjects, getPracticeQuestions/gradePractice, getMistakes, getTopicMastery, askBiExplain` (+ tái dùng getExamTracks/getExams/getExam/submitExam).
- `styles.css`: **hệ responsive** (breakpoints sm640/md768/lg1024/xl1280/2xl1536; container `.learn-browse{max-width:1280px;margin:0 auto}`, `.learn-quiz{max-width:640px;margin:0 auto}`); class lưới môn, thẻ chế độ, mastery bar, mã màu mastery; clamp() tiêu đề. Áp toàn app sau (đợt này dùng trong tab).
- Hằng số FE: `CATEGORY_MAP` (môn→danh mục, theo Resolved Decisions), `BO_GD_SUBJECTS` (danh sách HSG/chuyển cấp), `IELTS_TOEIC_MOCK` (cấu trúc+giờ đề thật).

### Backend (mỏng, read/LLM — không schema mới)
- `learning_hub_router.py` (hoặc exam_router) THÊM:
  - `GET /api/learning/mistakes?subject=` — suy câu sai từ `exam_sessions.answers_json` × `question_bank` (family-scoped), nhóm theo môn/chủ đề.
  - `GET /api/learning/mastery?subject=` — tính % đúng theo `topic` → band SmartScore (<60/60-79/80-89/≥90).
  - `GET /api/learning/practice?subject=&topic=&limit=` + `POST /api/learning/practice/grade` — câu hỏi luyện theo bài + chấm từng câu (giữ đáp án ở server).
  - `POST /api/learning/explain` — `{question, child_answer, correct_answer}` → `stream_chat` (role teacher, Socratic) → **SafetyFilter** → trả lời. `run_in_threadpool`.
- `server.py`: đăng ký nếu tạo router mới (hoặc gắn vào exam_router sẵn).
- KHÔNG đụng: schema, luồng chấm đề/TOEIC, exam_sessions structure.

## Data / Schema changes

**KHÔNG có bảng mới / cột mới.** Suy dẫn từ dữ liệu hiện có:
- **Sổ lỗi** = các `(question_id)` trong `answers_json` của phiên family mà `answer != question_bank.answer`.
- **Mastery theo chủ đề** = gom theo `question_bank.topic`: `accuracy = đúng/tổng` (trên lịch sử phiên), map band: <60 Cần cố gắng · 60-79 Khá · 80-89 Thạo · ≥90 Làm chủ.
- `CATEGORY_MAP`, `BO_GD_SUBJECTS`, cấu trúc IELTS/TOEIC mock = **hằng số FE** (có thể chuyển BE sau).
- (Lớp 2 mới cần schema: review_schedule, daily_goal/badge/streak, family_leaderboard.)

## API / Contracts

| Method | Path | Trạng thái | Mô tả |
|---|---|---|---|
| GET | `/api/learning/subjects` | đã có | danh sách môn (label/emoji/paper_count) |
| GET | `/api/learning/exams?subject=&track=` | đã có | đề theo môn/track |
| GET | `/api/learning/exams/{id}` · POST submit | đã có | tái dùng "Luyện theo đề" |
| GET | `/api/learning/mistakes?subject=` | **MỚI** | sổ lỗi (family-scoped) |
| GET | `/api/learning/mastery?subject=` | **MỚI** | mastery theo chủ đề (band) |
| GET | `/api/learning/practice?subject=&topic=&limit=` | **MỚI** | câu luyện theo bài |
| POST | `/api/learning/practice/grade` | **MỚI** | chấm từng câu + trả đáp án/giải thích |
| POST | `/api/learning/explain` | **MỚI** | Hỏi Bi vì sao (LLM Socratic + SafetyFilter) |

Tất cả endpoint mới: `Depends(get_current_user)` + scope `family_id`; output LLM qua SafetyFilter.

## Phases (build từng lát, mỗi lát commit + `npm run build` + `python tests/run_tests.py`)

1. **L1-A Subject grid**: `getLearningSubjects` + `SubjectGrid`/`SubjectCard` + CATEGORY_MAP + search + responsive container. Thay màn đầu LearningHubPage.
2. **L1-B Subject detail + thẻ chế độ**: `SubjectDetail` + ModeCard + gating (Bộ GD vs Nâng cao; IELTS/TOEIC mock). 2 cột ≥1024.
3. **L1-C Luyện theo đề (tái dùng) + ModeConfig timer**: nối luồng exam cũ vào trong môn + cấu hình giờ.
4. **L1-D Luyện theo bài**: BE practice + grade; `QuestionRunner` phản hồi từng câu; timer tùy chọn.
5. **L1-E Sổ lỗi**: BE mistakes + `ErrorBook`.
6. **L1-F Mastery theo chủ đề**: BE mastery + `MasteryByTopic` (màu+chữ).
7. **L1-G Hỏi Bi + Bi đọc đề**: BE explain (LLM+SafetyFilter) + `AskBi` + nút 🔊 SpeechSynthesis.
8. **L1-H Khung Lộ trình (shell)**: tái dùng modules cho 3 môn; còn lại "Sắp có".
9. **L1-I Responsive pass + parity**: rà 320→1920, tablet/ultra-wide, a11y; cập nhật DESIGN_SYSTEM.md + SYSTEM_MAP/STATUS_MAP.
- **Lớp 2 (đợt sau)**: spaced repetition, adaptive, Lộ trình BE mọi môn, gamification đầy đủ, parent report nâng cao.

## Risks & Open Questions

- **Tái cấu trúc LearningHubPage lớn (1007 dòng)** → rủi ro vỡ luồng exam/TOEIC. Giảm: giữ logic exam cũ, bọc trong view mới từng lát; build chạy sau mỗi lát.
- **Đáp án ẩn ở đề** → "luyện theo bài" buộc chấm server (đã tính: endpoint practice/grade).
- **Công thức mastery**: Lớp 1 dùng accuracy-band đơn giản (không phải SmartScore adaptive đầy đủ — đó là Lớp 2). Cần đủ dữ liệu phiên; môn chưa làm → "chưa có dữ liệu".
- **LLM explain độ trễ/chi phí** → cache nhẹ theo (question_id, answer) nếu cần; luôn SafetyFilter; fallback giải thích tĩnh (`question_bank.explanation`).
- **IELTS/TOEIC "đề thật"**: cấu trúc/giờ chuẩn map ở FE từ nội dung đề có sẵn; TOEIC S&W tái dùng STT.
- **`topic` thưa ở vài môn** → mastery gộp coarse; chấp nhận, hiển thị "Khác" nếu thiếu topic.
- **OQ-plan**: đặt endpoint mới ở `learning_hub_router` hay `exam_router`? → đề xuất `learning_hub_router` (gom "learning"), tái dùng helper exam. Chốt khi `/speckit-tasks`.
