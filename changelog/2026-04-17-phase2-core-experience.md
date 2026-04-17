# Phase 2 - Core Experience

## Tóm tắt

Phase 2 hoàn tất các phần lõi cho trải nghiệm hội thoại của Robot Bi: wake-word dev/test path, session UUID theo mỗi lần wake, auto-title cho session, conversation threads API, tab Hội thoại trong Parent App, và tối ưu latency STT trên máy CPU-only.

## Steps hoàn thành

- Step 2.1-2.2: wake-word dev/test path trong `ear_stt.py`, beep feedback, import-fail safe path, và `WAKEWORD_THRESHOLD`.
- Step 2.3: session UUID tracking với bảng `conversations` + `turns` và tích hợp lưu turns trong `main_loop.py`.
- Step 2.4: auto-naming session từ lượt user đầu tiên bằng `src_brain/network/session_namer.py`.
- Step 2.5: conversation threads REST API trong `api_server.py`.
- Step 2.6: Whisper CPU auto-downgrade qua `WHISPER_CPU_MODEL=medium`, giữ nguyên GPU path.
- Step 2.7: Parent App tab `Hội thoại` trong `src_brain/network/static/index.html`.

## Files thay đổi

- `src_brain/senses/ear_stt.py`
- `src_brain/network/db.py`
- `src_brain/main_loop.py`
- `src_brain/network/api_server.py`
- `src_brain/network/session_namer.py`
- `src_brain/network/static/index.html`
- `run_tests.py`
- `.env.example`
- `requirements.txt`

## Test results

- Final regression result: `89/89 PASS`
- Phase 2 was closed only after rerunning the full suite.

## Quyết định kỹ thuật quan trọng

- `openwakeword` mặc định để `WAKEWORD_ENABLED=False` vì model tùy biến `bi_oi` chưa sẵn sàng; điều này tránh tạo cảm giác production-ready giả trong khi vẫn giữ đường dev/test để tích hợp và kiểm thử.
- Session naming dùng Groq non-streaming thay vì `stream_chat()` vì đây là fire-and-forget nền, không thuộc luồng hội thoại chính và không cần audio/TTS streaming; timeout 5 giây giữ cho background task không treo lâu.
- Beep dùng `pygame.Channel(6)` để tách khỏi các channel audio protected khác và giữ hành vi non-blocking khi wake-word được phát hiện.
- `WHISPER_CPU_MODEL` mặc định là `medium` vì `large-v2` trên CPU-only gây độ trễ quá cao; GPU path vẫn giữ `large-v2 + float16` để không ảnh hưởng chất lượng khi có CUDA.
