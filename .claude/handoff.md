# Handoff — Robot Bi

> Snapshot ngắn theo mô hình Single Source of Truth.
> Chi tiết lịch sử nằm trong `changelog/`.

## TRẠNG THÁI HIỆN TẠI

- Phase 1-4: FROZEN hoàn toàn.
- Phase 5.1 Refactor thư mục: DONE 2026-04-29, **197/197 PASS**.
- Review Round 5 security fixes: DONE 2026-04-30, **338/338 PASS**.
- Phase B Tasks B1-B8: FULLY COMPLETE 2026-04-30.
- Backend Deep Review fixes: DONE 2026-05-01, **374/374 PASS**.
- `src_brain/` đã XÓA — không còn tồn tại. Dùng `src/` thay thế.
- `PROJECT.md` tiếp tục là nguồn sự thật duy nhất.
- `CLAUDE.md` và `AGENTS.md` được sinh từ `python sync.py`.
- Entry point chính: `src/main.py` (trước đây là `src_brain/main_loop.py`).
- LLM chính vẫn đi qua `stream_chat(messages)` trong `src/ai/ai_engine.py`.
- Backend AI vẫn là Groq primary, Gemini fallback.
- STT vẫn là `faster-whisper`; GPU giữ `large-v2 + float16`, CPU fallback dùng `WHISPER_CPU_MODEL`.
- DB: `runtime/robot_bi.db`; ChromaDB: `runtime/chroma_db/`; Static: `frontend/parent_app/`.
- Tests: `python tests/run_tests.py` (trước đây là `python run_tests.py`).

## VIỆC CẦN LÀM TIẾP

- Phase 5.2: Giao diện màn hình robot (mắt biểu cảm, trạng thái, screensaver).
- Sau Phase B: tiep tuc review/freeze theo roadmap hien tai.
- Chuyen sang Ubuntu PC co GPU de verify runtime thuc te.
- WebRTC frame source can Ubuntu + aiortc.
- Wake-word model training can dataset rieng.
- Phase 4 features con lai: motor control, AEC.

## BUG ĐANG MỞ

- Wake-word vẫn mới ở mức dev/test: đang proxy qua openWakeWord built-in `hey_jarvis`; model tùy biến `bi_oi` vẫn chưa được train.
- Cloudflare URL vẫn thay đổi sau mỗi lần restart khi dùng tunnel miễn phí.
- YAMNet TFLite có thể không tải được nếu thiếu TensorFlow.
- Audio, mobile browser, và camera vẫn cần xác nhận thủ công trên thiết bị thật.

## PROTECTED FIXES

- Audio mom talk: resample 16k -> 44.1k, in-memory WAV, `pygame.Channel(7)`.
- Mom pause logic: `is_mom_talking()` phải giữ nguyên.
- Camera delay fix: thread riêng, queue bridge, `CAP_PROP_BUFFERSIZE=1`.
- SafetyFilter: luôn post-LLM và pre-TTS.
- RAG threshold 0.50 và deduplication không được regress.
- Multi-family isolation: ChromaDB `where={"family_id": family_id}`, conversations/events/tasks family scope, admin family endpoints require `is_admin`.
- Homework system: classifier khong goi LLM, mark conversations bang `is_homework`, va API homework phai family-scoped.
- Groq primary `llama-3.3-70b-versatile` + Gemini fallback phải giữ nguyên.
- JWT auth, refresh rotation, middleware guard, và rate limiting phải giữ nguyên.
- Wake-word/session/conversation threads additions của Phase 2 hiện là protected; xem `PROJECT.md` để biết danh sách chuẩn.

## SESSION GẦN NHẤT — Phase 2 complete

- Date: 2026-04-17
- Phase 2 hoàn tất: wake-word dev/test path, session UUID tracking, auto session naming, conversation threads API, Parent App conversation UI, và Whisper CPU fallback tuning.
- Final regression result: 89/89 PASS.
- Chi tiết đầy đủ: `changelog/2026-04-17-phase2-core-experience.md`.

## SESSION 2026-04-26 — Phase 3 Final Fix Sprint

- Hoan thanh 23 fixes audit pass 3, khong them feature moi ngoai scope.
- Them Group 24 vao `run_tests.py` voi 17 tests; final result 138/138 PASS.
- Changelog: `changelog/2026-04-26-phase3-final-fix-sprint.md`.

## SESSION 2026-04-27 - Final Pre-Phase 4 Fix Sprint

- Hoan thanh 12/12 fixes truoc Phase 4: WebRTC cleanup, frontend stream cleanup, privacy logging, SQLite FK, RAG prune handling, MIC_DEVICE env, auth logout cleanup, docs/PWA verification.
- Them Group 29 vao `run_tests.py` voi 12 tests.
- Final result: 176/176 PASS.
- Changelog: `changelog/2026-04-27-final-pre-phase4-fix-sprint.md`.

## SESSION 2026-04-28 - Phase 4 Task 4.4 Multi-family Isolation

- Hoan thanh family registry/admin role, SQLite family scoping, RAG ChromaDB real family filters, notifier/TaskManager/API family isolation, va WebSocket family-scoped replay/broadcast.
- Them `/api/admin/families` POST/GET/DELETE voi `is_admin` check va explicit cleanup.
- Them Group 30 vao `run_tests.py` voi 6 tests.
- Final result: 182/182 PASS.
- Changelog: `changelog/2026-04-28-task-4-4-multifamily-isolation.md`.

## SESSION 2026-04-28 - Phase 4 Task 4.5 Homework System

- Hoan thanh local homework classifier, schema flags tren conversations, DB helpers, main loop mark sau persist `sanitized_reply`, API homework list/mark, va Parent App tab `Bai tap`.
- Them Group 31 vao `run_tests.py` voi 8 tests.
- Final result: 190/190 PASS.
- Changelog: `changelog/2026-04-28-task-4-5-homework-system.md`.

## SESSION 2026-04-29 — Phase 5.1 Refactor Thư Mục

- Di chuyen toan bo `src_brain/` → `src/` theo cau truc domain moi.
- `src_brain/` da XOA. Khong con tham chieu den `src_brain` o bat ky dau.
- Import paths: `src_brain.X` → `src.X` theo mapping trong migration script.
- Paths moi: DB=`runtime/robot_bi.db`, ChromaDB=`runtime/chroma_db/`, Frontend=`frontend/parent_app/`.
- Tests di chuyen tu `run_tests.py` → `tests/run_tests.py`.
- Tao docs/ROADMAP.md, .github/workflows/test.yml, config/env/, resources/, infra/, frontend/robot_display/.
- Final regression: **197/197 PASS**.
- Changelog: `changelog/2026-04-29-phase5-1-refactor.md`.

## SESSION 2026-04-30 — Review Fixes Phase 6-10

- Fix P0-P1 frontend/backend mismatch cho persona, emotion, music playlist, va emotion chart breakdown.
- Them routes video call va game trong FastAPI, dang ky vao `src/api/server.py`.
- Loai bo `datetime.utcnow()` trong `src/`.
- Persist learning schedule vao SQLite bang bang `learning_schedules`.
- Them Group 46 vao `tests/run_tests.py`.
- Final regression: **309/309 PASS**.
- Changelog: `changelog/2026-04-30-review-fixes-phase6-10.md`.

## SESSION 2026-04-30 — API Contract Review Fixes

- Root dashboard route da tro den `frontend/parent_app`.
- Parent App music play gui `track_id/category`.
- Parent App story tell gui `story_id/custom_request` va chap nhan response `{title, content}`.
- Parent App game cards goi dung word/voice quiz routes; math quiz hien sap ra mat.
- `verify_db_clean.py` dung import `src.infrastructure.database.db`.
- Them Group 47 vao `tests/run_tests.py`.
- Final regression: **315/315 PASS**.
- Changelog: `changelog/2026-04-30-api-contract-review-fixes.md`.

## SESSION 2026-04-30 — Review Round 3 Runtime Fixes

- Family delete cleanup xoa them `learning_schedules`, emotion tables, persona, education sessions, va curriculum schedules.
- Parent App video call end gui dung `call_id`.
- Parent App music volume gui `level`.
- Parent App education schedule load tu API truoc render, localStorage la cache/fallback.
- `stress_test.py` dung import `src.*` sau refactor.
- Them Group 48 vao `tests/run_tests.py`.
- Final regression: **321/321 PASS**.
- Changelog: `changelog/2026-04-30-review-round3-runtime-fixes.md`.

## SESSION 2026-04-30 — Review Round 4 Fixes

- DB upgrade migration copy one-time tu cac DB path cu sang `runtime/robot_bi.db` neu DB moi chua co data.
- Video call `end_call()` enforce family isolation truoc khi ket thuc call.
- Music transport routes `next/previous/shuffle/repeat` da dang ky va `MusicPlayer` co methods tuong ung; Parent App map `prev` sang `previous`.
- Them Group 49 vao `tests/run_tests.py`.
- Final regression: **329/329 PASS**.
- Changelog: `changelog/2026-04-30-review-round4-fixes.md`.

## SESSION 2026-04-30 — Review Round 5 Security Fixes

- SQL cleanup table names trong `delete_family_record()` da co allowlist truoc khi interpolate vao SQL.
- Gemini fallback khong con dua API key vao URL; key gui qua header `x-goog-api-key`.
- `verify_password()` da duoc verify voi argon2-cffi: thu tu hien tai `verify(hash, password)` la dung, khong sua code.
- PIN login dung `hmac.compare_digest()`; malformed JSON trong auth routes tra 422.
- Groq fail/cooldown globals co `_groq_lock`; `main.py` dung `sanitized_reply`, dispatch RAG truoc khi close session, va hoist `pygame.time.Clock()`.
- Analytics count handle NULL, SafetyFilter dung Unicode-aware boundary, homework conversation total dung COUNT query.
- Them Group 50 vao `tests/run_tests.py`.
- Final regression: **338/338 PASS**.
- Changelog: `changelog/2026-04-30-review-round5-security-fixes.md`.

## SESSION 2026-04-30 — Phase B Tasks B1-B8 Complete

- Phase B da hoan thanh day du 8/8 tasks: B1, B2, B3, B4, B5, B6, B7, B8.
- Trang thai du an da duoc cap nhat de danh dau Phase B la fully complete.
- Changelog: `changelog/2026-04-30-phase-b-complete.md`.

## SESSION 2026-05-01 — Backend Deep Review Fixes

- Fix 13 group backend issues tu Deep Review: WordQuizGame contract/high score, VoiceQuiz schema/fuzzy match, state event parser, EmotionAlert analyzer compatibility, unified education schedule, education/analytics/game/video/emotion API contracts, PII-safe logging, va wake-word defaults.
- Them bang `game_scores` vao SQLite va cleanup family-scoped cho bang moi.
- Them Group 59 vao `tests/run_tests.py` voi 11 API contract tests.
- Final regression: **374/374 PASS**.
- Changelog: `changelog/2026-05-01-backend-deep-review-fixes.md`.
