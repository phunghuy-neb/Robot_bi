# Handoff — Robot Bi

> Snapshot ngắn theo mô hình Single Source of Truth.
> Chi tiết lịch sử nằm trong `changelog/`.

## TRẠNG THÁI HIỆN TẠI

- Phase 1 — Security & Data Layer: hoàn thành.
- Phase 2 — Core Experience: hoàn thành ngày 2026-04-17.
- `PROJECT.md` tiếp tục là nguồn sự thật duy nhất.
- `CLAUDE.md` và `AGENTS.md` được sinh từ `python sync.py`.
- Entry point chính vẫn là `src_brain/main_loop.py`.
- LLM chính vẫn đi qua `stream_chat(messages)` trong `src_brain/ai_core/core_ai.py`.
- Backend AI vẫn là Groq primary, Gemini fallback.
- STT vẫn là `faster-whisper`; GPU giữ `large-v2 + float16`, CPU fallback dùng `WHISPER_CPU_MODEL`.
- Parent App hiện đã có tab `Hội thoại` để xem conversation threads qua JWT-protected API.

## VIỆC CẦN LÀM TIẾP

- Bắt đầu Phase 3: WebRTC camera cho Parent App.
- Thiết kế push notification flow cho phụ huynh.
- Bổ sung account settings và quản lý hồ sơ phụ huynh.
- Test end-to-end trên máy Windows thật với mic, loa, camera và mobile browser.
- Cân nhắc named Cloudflare Tunnel nếu cần URL cố định.

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
- Groq primary `llama-3.3-70b-versatile` + Gemini fallback phải giữ nguyên.
- JWT auth, refresh rotation, middleware guard, và rate limiting phải giữ nguyên.
- Wake-word/session/conversation threads additions của Phase 2 hiện là protected; xem `PROJECT.md` để biết danh sách chuẩn.

## SESSION GẦN NHẤT — Phase 2 complete

- Date: 2026-04-17
- Phase 2 hoàn tất: wake-word dev/test path, session UUID tracking, auto session naming, conversation threads API, Parent App conversation UI, và Whisper CPU fallback tuning.
- Final regression result: 89/89 PASS.
- Chi tiết đầy đủ: `changelog/2026-04-17-phase2-core-experience.md`.
