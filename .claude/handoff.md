# 📋 Handoff — Robot Bi

> Snapshot rút gọn theo phương pháp Single Source of Truth.
> Lịch sử cũ đã chuyển sang thư mục `changelog/`.

## TRẠNG THÁI HIỆN TẠI

- Phase 1 — Security & Data Layer: Đã hoàn thành đến Step 1.6 (JWT middleware bảo vệ tất cả endpoints).
- Dự án đang chạy theo mô hình `PROJECT.md` là nguồn chuẩn duy nhất.
- `CLAUDE.md` và `AGENTS.md` được sinh tự động từ `python sync.py`.
- Entry point chính vẫn là `src_brain/main_loop.py`.
- LLM vẫn đi qua `stream_chat(messages)` trong `src_brain/ai_core/core_ai.py`.
- Backend AI hiện tại: Groq primary, Gemini fallback.
- STT vẫn là `faster-whisper` với auto-detect GPU/CPU.
- TTS vẫn là `edge-tts` với fallback `pyttsx3`.
- SafetyFilter vẫn phải chạy sau LLM và trước mọi đường TTS.
- Parent App vẫn phục vụ qua HTTPS `8443` với Cloudflare Tunnel tùy chọn.
- Hệ thống audio streaming, mom-talk path và camera low-latency đều đang ở trạng thái protected.
- `start_robot.bat` đã được chỉnh để chạy `python sync.py` trước khi khởi động robot.
- Lịch sử session dài không còn nằm trong file này; xem thư mục `changelog/`.
- `CLAUDE.md` và `AGENTS.md` không còn là nơi ghi quy tắc thủ công.
- Tài liệu vận hành giờ tách thành 2 tầng: snapshot ngắn trong file này, lịch sử dài trong `changelog/`.
- Không có thay đổi nào tới logic AI, audio, vision, network hay memory ngoài warning suppression và logging hygiene.
- Các file archive được giữ nguyên mục đích tra cứu, không phải nguồn chuẩn để chỉnh tay.
- `run_tests.py` hiện sạch 3 warning mục tiêu: pygame `pkg_resources`, Hugging Face cache permission và YAMNet fallback warning spam.
- `run_tests.py` hiện cũng đã sạch banner `pygame`, progress/model-load output của `sentence-transformers`, và log headless `no-camera`.
- `EarSTT` hiện tự dò microphone input khả dụng theo mono rồi stereo; nếu không mở được mic sẽ vào silent mode thay vì crash PortAudio.
- `sync.py` hiện đã an toàn với Windows CP1252: ép `stdout` sang UTF-8 và bỏ emoji trong output.
- QR của Parent App hiện render bằng ASCII thuần trong terminal nên đã hiện lại ổn định sau bước sync/khởi động trên Windows console.
- `CryDetector` hiện chỉ log `info` một lần khi không có microphone hợp lệ rồi tự dừng, không còn spam `Error querying device -1`.

## VIỆC CẦN LÀM TIẾP

- Test thực tế end-to-end với mic, loa, camera trên máy Windows thật.
- Xác nhận lại parent audio route trên mobile browser sau các fix volume và `setSinkId`.
- Cân nhắc named Cloudflare Tunnel nếu cần URL cố định cho phụ huynh.
- Giảm độ nhạy energy fallback trong `cry_detector.py` nếu còn báo giả.
- Kiểm tra tải model YAMNet/TFLite trên môi trường chưa có TensorFlow.
- Tiếp tục chỉ sửa `PROJECT.md` khi cập nhật quy tắc hoặc trạng thái chuẩn của dự án.
- Khi có session mới, cập nhật cuối `PROJECT.md`, cập nhật file này, tạo changelog mới rồi chạy `sync.py`.
- Tránh đưa lịch sử dài quay trở lại `handoff.md`.

## BUG ĐANG MỞ

- Wake-word "Bi ơi" vẫn là stub, chưa có model đánh thức thật.
- Cloudflare URL vẫn thay đổi sau mỗi lần restart khi dùng tunnel miễn phí.
- YAMNet TFLite có thể không tải được nếu thiếu TensorFlow.
- Hành vi audio trên mobile browser vẫn cần xác nhận thủ công trên thiết bị thật.
- Các luồng mic/loa/camera phụ thuộc phần cứng nên chưa thể xác nhận hoàn toàn bằng test tự động.
- Chưa ghi nhận bug mở nào mới cho `sync.py` sau khi bỏ emoji output và ép `stdout` sang UTF-8.

## PROTECTED FIXES

- Audio mom talk: resample 16k -> 44.1k, in-memory WAV, `pygame.Channel(7)`.
- Mom pause logic: `is_mom_talking()` phải giữ nguyên hành vi chặn robot nghe khi mẹ nói.
- Camera delay fix: thread riêng, queue bridge, `CAP_PROP_BUFFERSIZE=1`.
- SafetyFilter: luôn post-LLM và pre-TTS.
- RAG threshold 0.50 và deduplication hiện tại không được phá regression.
- Groq primary `llama-3.3-70b-versatile` + Gemini fallback phải được giữ nguyên.
- `faster-whisper` GPU/CPU auto-detect + large-v2 vẫn là chuẩn STT hiện tại.
- HTTPS self-signed + Cloudflare Tunnel phải tiếp tục hoạt động.
- Audio queue + chunked TTS streaming phải giữ mục tiêu Time-to-First-Audio thấp.
- PIN auth, TaskManager và cơ chế sao thưởng là các khu vực cần tránh chạm nếu không có yêu cầu rõ.
- Rate limiting `/api/auth/login`: 5 lần sai → lock 15 phút (bảng `login_attempts`), `AUTH_PIN` từ `.env` (Step 1.3).
- Username + Password auth (Step 1.4): module `auth.py`, endpoint `/auth/register` + `/auth/login/v2`, rate limit theo `user:<username>`. PIN cũ vẫn chạy song song.
- JWT access + refresh token (Step 1.5): `create_access_token` (HS256/60min), `create_refresh_token` + `store_refresh_token` (sha256/30 ngày), `verify_access_token`, `rotate_refresh_token` (atomic revoke+insert). Endpoint `/auth/refresh` + `/auth/logout`. Bảng `auth_tokens` trong DB. `JWT_SECRET_KEY` từ `.env`.
- JWT middleware toàn app (Step 1.6): `get_current_user()` dùng `HTTPBearer(auto_error=False)`, raise 401 + `WWW-Authenticate: Bearer`. Áp dụng `Depends(get_current_user)` lên 17 REST routes. Camera dùng `_camera_auth` (header + `?auth=`). 3 WS handlers xác thực qua `?token=`, đóng 1008 nếu invalid. `GET /health` không cần auth. Whitelist: `/health`, `/api/status`, `/api/mom/status`, `/api/auth/login`, `/api/auth/logout`, `/auth/register`, `/auth/login/v2`, `/auth/refresh`, `/`, `/static/*`.
- Nếu sửa vào các vùng protected này thì phải chạy full test và kiểm tra regression thủ công.

## SESSION GẦN NHẤT — Phase 1 hoàn thành

- Ngày: 2026-04-17
- Mục tiêu: Hoàn thành toàn bộ Phase 1 — Security & Data Layer (Steps 1.1–1.7).
- SQLite migration thay thế event_queue.json + tasks.json (Step 1.1).
- Loại runtime JSON files khỏi git tracking (Step 1.2).
- PIN auth + rate limiting 5 lần sai/lock 15 phút, `AUTH_PIN` từ `.env` (Step 1.3).
- Username/Password auth với Argon2id, module `auth.py` (Step 1.4).
- JWT access token (60 phút) + refresh token với rotation (30 ngày) (Step 1.5).
- JWT middleware toàn app: 17 REST routes + 3 WebSocket + camera (Step 1.6).
- requirements.txt pin đủ các dependency Phase 1 (Step 1.7).
- Test: `71/71 PASS`.
- Files mới: `db.py`, `auth.py`. Files sửa: `api_server.py`, `task_manager.py`, `notifier.py`, `requirements.txt`, `.env.example`.
