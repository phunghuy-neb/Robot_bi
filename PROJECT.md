# PROJECT.md — Hướng dẫn Dự án Robot Bi (Single Source of Truth)

> Cập nhật: 2026-04-30 | Dự án Robot Bi — Gia sư AI cho trẻ em 5-12 tuổi  
> Đây là file **NGUỒN DUY NHẤT**. CLAUDE.md và AGENTS.md là bản sao tự động.

## QUY TẮC BẮT BUỘC CHO CẢ CLAUDE CODE CLI VÀ CODEX CLI

1. **PROJECT.md là file nguồn sự thật duy nhất**. Chỉ được sửa file này.
2. Không bao giờ sửa trực tiếp CLAUDE.md hoặc AGENTS.md.
3. Trước khi sửa bất kỳ code nào: Đọc phần **PROTECTED FIXES** và **handoff.md**.
4. Sau khi sửa xong: **BẮT BUỘC chạy `python tests/run_tests.py`**. Nếu có test fail → phải fix trước khi kết thúc session.
5. Khi kết thúc session: Cập nhật PROJECT.md → cập nhật handoff.md → tạo file trong thư mục `changelog/` → chạy `python sync.py`.
6. CLAUDE.md và AGENTS.md là file AUTO-GENERATED. Bất kỳ thay đổi tay nào cũng sẽ bị ghi đè.

## ⚠️ PROTECTED FIXES — TUYỆT ĐỐI KHÔNG ĐƯỢC PHÁ (Regression Protection)

- Audio mom talk + resample 16k→44.1k + pygame Channel(7) + in-memory WAV (Session N/O/P)
- Mom pause logic + `is_mom_talking()` (Session L/M)
- Camera delay fix: thread riêng + queue + `CAP_PROP_BUFFERSIZE=1` (Session Q)
- SafetyFilter (post-LLM, pre-TTS)
- RAG threshold 0.50 + deduplication
- Groq primary (`llama-3.3-70b-versatile`) + Gemini fallback
- faster-whisper GPU/CPU auto-detect + large-v2
- HTTPS self-signed + Cloudflare Tunnel
- Audio queue + chunked TTS streaming (Time-to-First-Audio < 2s)
- PIN auth + TaskManager + sao thưởng
- Microphone fallback (silent mode khi không có mic)
- CryDetector logging (chỉ log 1 lần khi không có mic)
- Rate limiting cho `/api/auth/login` (5 lần sai → lock 15 phút, bảng `login_attempts`) + `AUTH_PIN` đọc từ `.env` (Step 1.3)
- Username + Password auth system với Argon2id (Step 1.4) — chạy song song với PIN cũ. Module `auth.py`, endpoint `/auth/register` + `/auth/login/v2`, rate limit theo `user:<username>`
- JWT access token + refresh token với rotation (Step 1.5) — `create_access_token` (HS256, 60 phút), `create_refresh_token`/`store_refresh_token` (sha256, 30 ngày), `verify_access_token`, `rotate_refresh_token` (atomic revoke+insert). Endpoint `/auth/refresh` + `/auth/logout`. `JWT_SECRET_KEY` + `JWT_ALGORITHM` từ `.env`. `python-jose[cryptography]` thêm vào requirements. Bảng `auth_tokens` tạo trong `db.py`.
- JWT middleware bảo vệ tất cả endpoints (Step 1.6) — `get_current_user()` dùng `HTTPBearer(auto_error=False)` trong `auth.py`, raise 401 + `WWW-Authenticate: Bearer`. Áp dụng `Depends(get_current_user)` lên 17 REST routes. Camera dùng `_camera_auth` (header + `?auth=` query param). 3 WebSocket handlers xác thực JWT qua `?token=` query param, đóng code 1008 nếu invalid. Thêm `GET /health` (no auth). Whitelist: `/health`, `/api/status`, `/api/mom/status`, `/api/auth/login`, `/api/auth/logout`, `/auth/register`, `/auth/login/v2`, `/auth/refresh`, `/`, `/static/*`.
- `JWT_SECRET_KEY` phải luôn đọc từ `.env` — không có default value, không hardcode.
- SQLite DB path cố định: `runtime/robot_bi.db` (từ Phase 5.1) — không đổi path, không đổi tên file.
- `verify_access_token()` và `rotate_refresh_token()` trong `auth.py` — không thay đổi logic xác thực.
- Rate limiting bảng `login_attempts` — không bypass, không xóa bảng này.
- SQLite schema bảng `tasks`: `task_id, name, remind_time, completed_today, stars, created_at, last_reminded, import_key` — phải khớp với `task_manager.py`, không được đổi tên cột.
- conversations + turns table schema in `db.py` — không đổi tên cột
- `create_session()`, `add_turn()`, `close_session()`, `get_session_turns()` trong `db.py`
- `update_session_title()` trong `db.py`
- `session_namer.py`: `_generate_session_title()` — Groq non-streaming, timeout 5s, fallback `user_text[:30]`
- `BEEP_WAV_BYTES` + `_play_beep()` trong `ear_stt.py` — `pygame.Channel(6)`, non-blocking
- `WAKEWORD_THRESHOLD` env var (default `0.5`) trong `ear_stt.py`
- `listen_for_wakeword()` — trả `False` nếu `WAKEWORD_ENABLED=False` hoặc import `openwakeword` fail
- Whisper CPU auto-downgrade: `WHISPER_CPU_MODEL` env var, GPU path giữ nguyên
- `/api/conversations`, `/api/conversations/{id}`, `/api/conversations/{id}/homework` endpoints
- `index.html`: tab `Hội thoại`, `loadThreads()`, `showThreadDetail()` — không remove
- `.gitignore`: runtime files (`event_queue.json`, `tasks.json`, `robot_bi.db`) không có dấu ngoặc kép, không bị git track.
- Task 4.4 multi-family isolation: ChromaDB query phải có `where={"family_id": family_id}`; conversations/events/tasks phải scope theo `family_id`; admin family endpoints phải require `is_admin`.

**Nếu đụng vào những phần này phải chạy full test và kiểm tra regression.**

## Mission & Ưu tiên

Robot gia sư thông minh cho trẻ em 5-12 tuổi, chạy trên Windows PC/Laptop.  
**Ưu tiên:** An toàn & privacy cho trẻ em, trải nghiệm tự nhiên, dễ sử dụng cho phụ huynh.

AI backend: Groq (primary) + Gemini (fallback). Không dùng Ollama.

## Stack hiện tại (KHÔNG thay đổi trừ khi có lệnh rõ ràng)

| Layer         | Thư viện                             | Ghi chú                                  |
|---------------|--------------------------------------|------------------------------------------|
| LLM Primary   | Groq `llama-3.3-70b-versatile`       | ~400 token/giây                          |
| LLM Fallback  | Gemini `gemini-2.5-flash-lite`       | Tự động fallback                         |
| STT           | `faster-whisper`                     | large-v2 GPU / small CPU auto-detect     |
| TTS           | `edge-tts` + `pygame`                | giọng vi-VN-HoaiMyNeural                 |
| TTS Fallback  | `pyttsx3`                            | offline                                  |
| Safety        | regex + pattern                      | `safety_filter.py`                       |
| RAG           | `chromadb` + `sentence-transformers` | paraphrase-multilingual-MiniLM-L12-v2    |
| Vision        | `opencv-python`                      | CAP_DSHOW                                |
| Cry Detection | YAMNet TFLite + energy fallback      | `cry_detector.py`                        |
| Network       | `fastapi` + `uvicorn` + `websockets` | HTTPS 8443                               |
| Storage       | SQLite                               | `runtime/robot_bi.db`                   |
| Auth          | `argon2-cffi` + `python-jose`        | JWT access(60m) + refresh(30d)           |
| Wake-word     | `openwakeword`                       | `WAKEWORD_ENABLED=False` mặc định, bật khi model sẵn sàng |
| Session tracking | SQLite `conversations` + `turns`  | Session UUID theo mỗi lần wake           |
| Session naming | Groq (non-streaming)                | Tự đặt tiêu đề từ lượt user đầu tiên     |
| Tunnel        | `cloudflared`                        | public URL                               |

## Kiến trúc file & Quy tắc chỉnh sửa

(Đọc trước khi sửa bất kỳ file nào — không bịa tên class/hàm)

- **Entry point chính**: `src/main.py` (từ Phase 5.1, trước đây là `src_brain/main_loop.py`)
- **LLM**: phải qua `stream_chat(messages)` trong `src/ai/ai_engine.py`
- **STT**: `src/audio/input/ear_stt.py` (faster-whisper)
- **TTS**: `src/audio/output/mouth_tts.py` (edge-tts + pyttsx3 fallback)
- **Safety**: `src/safety/safety_filter.py` — phải chạy trước TTS
- **API server**: `src/api/server.py` + `src/api/routers/`
- **DB**: `src/infrastructure/database/db.py` — lưu tại `runtime/robot_bi.db`
- **Frontend**: `frontend/parent_app/` (index.html, manifest.json, sw.js)
- **API keys**: lấy từ `.env` (không hardcode)

## Vấn đề đã biết

1. Wake-word "Bi ơi" đã có dev/test path qua openWakeWord built-in "hey_jarvis"; model tùy biến `bi_oi` vẫn chưa được train
2. Cloudflare URL thay đổi mỗi lần restart (cần named tunnel sau)
3. YAMNet TFLite có thể fail nếu thiếu tensorflow (dùng fallback)
4. Auth: JWT access/refresh token, rate limiting, Argon2id — Phase 1 complete. PIN cũ vẫn chạy song song.

## Ghi chú vận hành (Warning Hygiene)

- Pygame `pkg_resources` warning được suppress
- Hugging Face cache được cấu hình an toàn để tránh warning quyền ghi
- CryDetector khi thiếu YAMNet chỉ in 1 dòng info gọn
- CryDetector khi không có microphone chỉ log info 1 lần rồi dừng
- `EarSTT` tự động dò microphone (thử mono trước, sau đó stereo); không mở được thì chuyển silent mode
- `sync.py` ép UTF-8 và dùng ASCII-safe log (`[OK]`, `WARNING`)
- QR Code dùng ANSI background colors để hiển thị rõ ràng, dễ quét bằng điện thoại

## Roadmap — 4 Phases

**Phase 1 — Security & Data Layer [HOÀN THÀNH 2026-04-17] ✅** (1.1 SQLite migration, 1.2 remove runtime JSON files khỏi git, 1.3 PIN + Rate limiting, 1.4 Username/Password auth với Argon2id, 1.5 JWT access + refresh token với rotation, 1.6 JWT middleware bảo vệ tất cả endpoints, 1.7 requirements.txt pin đủ) — Bugfix: schema tasks fixed, .gitignore fixed (2026-04-17)

**Phase 2 — Core Experience [HOÀN THÀNH 2026-04-17] ✅**  
Wake-word dev/test path, session UUID, auto-title, conversation threads API + Parent App UI

**Phase 3 — Parent Features [HOAN THANH 2026-04-27]**  
WebRTC camera, push notification, account settings, frontend cleanup, backend hardening, docs freeze.

**Phase 4 — Advanced [ĐANG LÀM]**  
Multi-family isolation và homework system hoàn thành 2026-04-28; còn motor control, AEC.

**Phase 5 — Màn hình Robot [ĐANG LÀM]**  
5.1 Refactor thư mục HOÀN THÀNH 2026-04-29 (src_brain/ → src/, 197/197 PASS); 5.2 Giao diện màn hình robot (todo).

## Schema Database mục tiêu (SQLite — `runtime/robot_bi.db`)

- `families`: family_id, display_name, created_at
- `users`: user_id, username, password_hash, family_name, created_at, is_active, is_admin
- `auth_tokens`: token_id, user_id, refresh_token_hash, expires_at, created_at
- `login_attempts`: ip_address, attempt_count, first_attempt_at, locked_until
- `conversations`: session_id, family_id, started_at, ended_at, title, turn_count, is_homework, homework_marked_at
- `turns`: turn_id, session_id, role, content, timestamp
- `events`: event_id, family_id, type, data, created_at (migrate từ event_queue.json)
- `tasks`: task_id, family_id, name, remind_time, completed_today, stars, created_at, last_reminded, import_key (schema khớp task_manager.py)

## Lệnh hay dùng

```bash
python sync.py                    # Đồng bộ CLAUDE.md + AGENTS.md
start_robot.bat                   # Khởi động robot (tự chạy sync.py)
python tests/run_tests.py         # BẮT BUỘC sau mọi thay đổi
python src/main.py                # Chạy trực tiếp
```

## Session gần nhất — Phase 2 hoàn thành: Core Experience

- Ngày: 2026-04-17
- Wake-word dev/test path hoàn tất trong `ear_stt.py`: `listen_for_wakeword()`, beep feedback, `WAKEWORD_THRESHOLD`, và import-fail path an toàn.
- Session tracking hoàn tất: bảng `conversations` + `turns`, các hàm session trong `db.py`, và `main_loop.py` lưu đầy đủ user/assistant turns theo session UUID.
- Session naming hoàn tất: `src_brain/network/session_namer.py` tạo title ngắn từ lượt user đầu tiên bằng Groq non-streaming, chạy nền, có fallback an toàn.
- Conversation Threads API hoàn tất: list/detail/delete/homework endpoints trong `api_server.py`, đều dùng JWT guard hiện có.
- Parent App hoàn tất tab `Hội thoại` trong `src_brain/network/static/index.html`, hiển thị danh sách thread và transcript chi tiết.
- CPU-only STT latency được giảm bằng `WHISPER_CPU_MODEL=medium` trong CPU fallback, GPU path `large-v2 + float16` giữ nguyên.
- Test result cuối Phase 2: 89/89 PASS.
- Files chính đã chạm: `ear_stt.py`, `db.py`, `main_loop.py`, `api_server.py`, `src_brain/network/session_namer.py`, `index.html`, `run_tests.py`, `.env.example`, `requirements.txt`.

## Session 2026-04-26 — Phase 3 Final Fix Sprint

- Hoan thanh 23 fixes audit pass 3: XSS task validation, registration gate, memory family guard, logout cleanup order, protected fetch refresh, WebRTC cleanup/user scoping, audio queue backpressure, JWT user existence check, change-password rate limit, bounded list limits, DB migration error handling, token_version single increment, WS logout reconnect guard, checkAuth retry, privacy logging, shutdown cleanup, TaskManager-before-API ordering, logging setup idempotence, Ubuntu aiortc requirements, ear_stt env drift, notifier WS stats, ops_router import cleanup.
- Them Group 24 vao `run_tests.py` voi 17 verification tests.
- Final sprint test result: 138/138 PASS.

## Session 2026-04-27 — Phase 1-3 Freeze Sprint

- Hoan thanh Sprint A-D: safety/logic, auth hardening, runtime stability, frontend cleanup, operations docs, va cleanup cuoi.
- Phase 3 COMPLETE; du an san sang chuyen sang Ubuntu PC co GPU.
- Final regression target sau Sprint D: 164/164 PASS.
- Known deferred debt: WebRTC frame source can Ubuntu + aiortc, wake-word model training can dataset, Phase 4 features, ChromaDB multi-family isolation.

## Session 2026-04-27 — Final Pre-Phase 4 Fix Sprint

- Hoan thanh 12/12 fixes: WebRTC reconnect/state cleanup, frontend unload/logout cleanup, speech log privacy, SQLite foreign_keys, RAG prune error handling, MIC_DEVICE env, secure .env.example placeholder, logout double-verify cleanup, PWA icon verification, docs cleanup.
- Them Group 29 vao `run_tests.py` voi 12 verification tests.
- Final regression target: 176/176 PASS.
- San sang Phase 4 sau pre-flight fix sprint.

## Session 2026-04-28 — Phase 4 Task 4.4 Multi-family Isolation

- Hoan thanh Task 4.4: them bang `families`, `is_admin`, FK/cascade cho schema moi, va explicit cleanup khi xoa family.
- RAG ChromaDB da gan `family_id` metadata, query/list/export/update/delete/clear deu filter theo family; memory cu thieu metadata duoc backfill ve `default`.
- Conversations/events/tasks da scope theo family trong API, DB helpers, notifier, TaskManager, va WebSocket unread/broadcast.
- Them admin endpoints: `POST /api/admin/families`, `GET /api/admin/families`, `DELETE /api/admin/families/{family_id}` voi admin role check.
- Them Group 30 vao `run_tests.py` voi 6 isolation tests.
- Final regression target: 182/182 PASS.

## Session 2026-04-28 — Phase 4 Task 4.5 Homework System

- Hoan thanh Task 4.5: classifier local `classify_homework()` khong goi LLM, detect bai tap bang keyword/regex co normalize Unicode.
- Them schema `conversations.is_homework`, `homework_marked_at`, DB helpers `mark_session_homework()` va `get_homework_sessions()` co family scope.
- Main loop mark homework sau khi TTS xong va sau khi persist `sanitized_reply`, gui event `homework` cho Parent App.
- Them API `GET /api/conversations/homework` va cap nhat `POST /api/conversations/{session_id}/homework` de mark session.
- Parent App co tab `Bai tap`, list homework sessions, dung lai thread detail va reload khi nhan notification `homework`.
- Them Group 31 vao `run_tests.py` voi 8 tests.
- Final regression target: 190/190 PASS.

## Session 2026-04-29 — Phase 5.1 Refactor Thư Mục

- Hoan thanh refactor thuần túy: di chuyển toàn bộ `src_brain/` → `src/` với cấu trúc domain rõ ràng.
- Tao cau truc moi: `src/ai/`, `src/safety/`, `src/memory/`, `src/audio/input|output|analysis/`, `src/vision/`, `src/education/`, `src/api/`, `src/infrastructure/`.
- Di chuyen 27 Python files, 5 frontend files (frontend/parent_app/), 1 test file (tests/run_tests.py).
- Cap nhat toan bo import paths: `src_brain.X` → `src.X` theo mapping moi.
- Fix hardcoded paths: DB tai `runtime/robot_bi.db`, ChromaDB tai `runtime/chroma_db/`, HF cache tai `runtime/.hf_cache/`, static files tai `frontend/parent_app/`.
- Xoa `src_brain/` sau khi verify 197/197 PASS.
- Tao 40+ placeholder files cho Phase 5-10 roadmap.
- Tao docs/ROADMAP.md, .github/workflows/test.yml, config/env/, resources/, infra/, frontend/robot_display/.
- Final regression target: 197/197 PASS.

## Session 2026-04-30 — Review Fixes Phase 6-10

- Hoan thanh P0 frontend mismatch: persona GET nested response, emotion today `dominant`, persona save `personality`.
- Hoan thanh P1: music playlist `category/tracks`, emotion weekly `breakdown`, parent chart doc dung shape moi.
- Hoan thanh P2: dang ky video call routes va word/voice game routes.
- Hoan thanh P3: thay `datetime.utcnow()` bang timezone-aware `datetime.now(timezone.utc)` va persist learning schedule vao SQLite.
- Them Group 46 vao `tests/run_tests.py` voi 6 verification tests.
- Final regression target: 309/309 PASS.

## Session 2026-04-30 — API Contract Review Fixes

- Fix root dashboard route trong `ops_router.py` tro den `frontend/parent_app/index.html`.
- Fix Parent App music/story/game actions dung backend API contract.
- Fix `verify_db_clean.py` import DB module moi sau refactor.
- Them Group 47 vao `tests/run_tests.py` voi 6 verification tests.
- Final regression target: 315/315 PASS.

## Session 2026-04-30 — Review Round 3 Runtime Fixes

- Fix family delete cleanup cho cac bang scoped moi: `learning_schedules`, emotion tables, persona, education sessions, va curriculum schedules.
- Fix Parent App video call luu/gui `call_id` khi end call.
- Fix Parent App music volume gui field `level` dung contract backend.
- Fix Parent App education schedule load tu `/api/education/schedule` truoc khi render, localStorage chi la cache/fallback.
- Fix `stress_test.py` import paths tu `src_brain.*` sang `src.*`.
- Them Group 48 vao `tests/run_tests.py` voi 6 verification tests.
- Final regression target: 321/321 PASS.

## Session 2026-04-30 — Review Round 4 Fixes

- Fix DB upgrade migration: copy one-time tu DB cu `src_brain/network/robot_bi.db`, `src_brain/network/data/robot_bi.db`, hoac `robot_bi.db` sang `runtime/robot_bi.db` neu DB moi chua co data.
- Fix video call family isolation: `end_call()` verify call thuoc family cua user truoc khi ket thuc.
- Fix music transport 404: them routes `next/previous/shuffle/repeat`, methods trong `MusicPlayer`, va frontend map `prev` sang `previous`.
- Them Group 49 vao `tests/run_tests.py` voi 8 verification tests.
- Final regression target: 329/329 PASS.

## Session 2026-04-30 — Review Round 5 Security Fixes

- Fix SQL injection risk trong `delete_family_record()` bang table allowlist cho cleanup loop.
- Fix Gemini API key exposure: `GEMINI_API_KEY` khong con nam trong URL, chuyen sang header `x-goog-api-key`.
- Verify `verify_password()` argon2 order dung: `verify(hash, password)`; khong can sua `auth.py`.
- Fix PIN timing attack bang `hmac.compare_digest()`.
- Fix malformed JSON trong `auth_router.py` tra 422 thay vi 500.
- Fix thread safety cho Groq cooldown globals bang `_groq_lock`.
- Fix `main.py`: persist/check `sanitized_reply`, dispatch RAG thread truoc khi close session, va hoist `pygame.time.Clock()`.
- Fix analytics NULL count, SafetyFilter Unicode boundary, va homework conversation total count.
- Them Group 50 vao `tests/run_tests.py` voi 9 security/quality tests.
- Final regression target: 338/338 PASS.

## Session 2026-04-30 — Phase B Tasks B1-B8 Complete

- Phase B da hoan thanh day du 8/8 tasks: B1, B2, B3, B4, B5, B6, B7, B8.
- Cap nhat tai lieu trang thai de danh dau Phase B la fully complete.
- Changelog: `changelog/2026-04-30-phase-b-complete.md`.

## Session 2026-05-01 — Backend Deep Review Fixes

- Fix 13 group backend issues tu Deep Review: WordQuizGame contract/high score, VoiceQuiz schema/fuzzy match, state event parser, EmotionAlert analyzer compatibility, unified education schedule, education/analytics/game/video/emotion API contracts, PII-safe logging, va wake-word defaults.
- Them bang `game_scores` vao SQLite va cleanup family-scoped cho bang moi.
- Them Group 59 vao `tests/run_tests.py` voi 11 API contract tests.
- Final regression target: 374/374 PASS.
- Changelog: `changelog/2026-05-01-backend-deep-review-fixes.md`.
