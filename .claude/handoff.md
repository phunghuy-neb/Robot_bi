# Handoff — Robot Bi

> Snapshot ngắn theo mô hình Single Source of Truth.
> Chi tiết lịch sử nằm trong `changelog/`.

## TRẠNG THÁI HIỆN TẠI

- Phase 1 — Security & Data Layer: hoàn thành.
- Phase 2 — Core Experience: hoàn thành ngày 2026-04-17.
- Current phase: Phase 4 started; Tasks 4.4 multi-family isolation and 4.5 homework system COMPLETE.
- Phase 3 Final Fix Sprint: hoan thanh 2026-04-26, 23 fixes audit pass 3 va Group 24 verification.
- Final Pre-Phase 4 Fix Sprint: hoan thanh 2026-04-27, 12 fixes + Group 29 verification, 176/176 PASS.
- Task 4.4 Multi-family isolation: hoan thanh 2026-04-28, Group 30 isolation tests, 182/182 PASS.
- Task 4.5 Homework system: hoan thanh 2026-04-28, Group 31 homework tests, 190/190 PASS.
- `PROJECT.md` tiếp tục là nguồn sự thật duy nhất.
- `CLAUDE.md` và `AGENTS.md` được sinh từ `python sync.py`.
- Entry point chính vẫn là `src_brain/main_loop.py`.
- LLM chính vẫn đi qua `stream_chat(messages)` trong `src_brain/ai_core/core_ai.py`.
- Backend AI vẫn là Groq primary, Gemini fallback.
- STT vẫn là `faster-whisper`; GPU giữ `large-v2 + float16`, CPU fallback dùng `WHISPER_CPU_MODEL`.
- Parent App hiện đã có tab `Hội thoại` để xem conversation threads qua JWT-protected API.

## VIỆC CẦN LÀM TIẾP

- Chuyen sang Ubuntu PC co GPU de verify runtime thuc te.
- WebRTC frame source can Ubuntu + aiortc.
- Wake-word model training can dataset rieng.
- Phase 4 features con lai: motor control, AEC.
- Test end-to-end tren may that voi mic, loa, camera va mobile browser.
- Bat dau Phase 4 sau khi verify hardware Ubuntu PC co GPU.

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
