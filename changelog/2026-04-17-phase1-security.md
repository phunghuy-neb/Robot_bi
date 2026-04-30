# Changelog: Phase 1 — Security & Data Layer (2026-04-17)

## Tóm tắt

Hoàn thành toàn bộ Phase 1 Security & Data Layer. Hệ thống auth được xây dựng từ đầu trên nền SQLite với JWT, Argon2id, rate limiting và middleware bảo vệ toàn bộ API.

## Steps đã hoàn thành

### Step 1.1 — SQLite Migration
- Tạo `src_brain/network/db.py`: quản lý SQLite `robot_bi.db`, schema `users`, `auth_tokens`, `login_attempts`, `events`, `tasks`.
- `task_manager.py` và `notifier.py` chuyển từ JSON file sang SQLite backend.

### Step 1.2 — Remove Runtime Files
- Cập nhật `.gitignore`: loại `event_queue.json`, `tasks.json`, `robot_bi.db` khỏi git tracking.
- Xóa các binary files test `_audit_test_db` khỏi tracking.

### Step 1.3 — PIN Auth + Rate Limiting
- `AUTH_PIN` đọc từ `.env`, không hardcode.
- Rate limiting endpoint `/api/auth/login`: 5 lần sai → lock 15 phút, lưu trong bảng `login_attempts`.

### Step 1.4 — Username/Password Auth (Argon2id)
- Module `auth.py` mới: `register_user()`, `authenticate_user()` dùng `argon2-cffi`.
- Endpoint `/auth/register` + `/auth/login/v2`.
- Rate limit theo `user:<username>`.
- Chạy song song với PIN cũ, không phá bất kỳ flow hiện tại.

### Step 1.5 — JWT Access + Refresh Token
- `create_access_token()` (HS256, 60 phút).
- `create_refresh_token()` + `store_refresh_token()` (sha256 hash, 30 ngày).
- `verify_access_token()`, `rotate_refresh_token()` (atomic revoke+insert).
- Endpoint `/auth/refresh` + `/auth/logout`.
- Bảng `auth_tokens` trong DB.
- `JWT_SECRET_KEY` + `JWT_ALGORITHM` từ `.env`. Thêm `python-jose[cryptography]` vào requirements.

### Step 1.6 — JWT Middleware Toàn App
- `get_current_user()` dùng `HTTPBearer(auto_error=False)` trong `auth.py`. Raise 401 + `WWW-Authenticate: Bearer`.
- Áp dụng `Depends(get_current_user)` lên 17 REST routes trong `api_server.py`.
- Camera dùng `_camera_auth` (hỗ trợ header + `?auth=` query param cho MJPEG stream).
- 3 WebSocket handlers (`/ws`, `/api/audio/stream`, `/api/mom/audio`) xác thực JWT qua `?token=`, đóng code 1008 nếu invalid.
- Thêm `GET /health` không cần auth.
- Whitelist: `/health`, `/api/status`, `/api/mom/status`, `/api/auth/login`, `/api/auth/logout`, `/auth/register`, `/auth/login/v2`, `/auth/refresh`, `/`, `/static/*`.

### Step 1.7 — Requirements Pin
- Pin đủ version cho `argon2-cffi`, `python-jose[cryptography]`, các dependency mới.

## Files thay đổi

| File | Loại thay đổi |
|------|--------------|
| `src_brain/network/db.py` | Mới |
| `src_brain/network/auth.py` | Mới |
| `src_brain/network/api_server.py` | Sửa (JWT guard, endpoints, camera auth, WS auth) |
| `src_brain/network/task_manager.py` | Sửa (SQLite backend) |
| `src_brain/network/notifier.py` | Sửa (SQLite backend) |
| `requirements.txt` | Sửa (thêm argon2-cffi, python-jose) |
| `.env.example` | Sửa (thêm AUTH_PIN, JWT_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD) |
| `run_tests.py` | Sửa (thêm Group 12 auth guard tests) |

## Test Results

**71/71 PASS**

## Quyết định kỹ thuật quan trọng

- **Argon2id** thay vì bcrypt: memory-hard hơn, chống GPU/ASIC brute force tốt hơn.
- **Refresh token dạng hash**: DB chỉ lưu sha256(token), token thô chỉ gửi cho client một lần.
- **atomic rotate**: revoke token cũ + insert token mới trong 1 transaction để tránh race condition.
- **HTTPBearer(auto_error=False)**: để custom error message 401 thay vì FastAPI mặc định 403.
- **JWT cho WebSocket qua query param**: browsers không support custom headers trong WS upgrade, dùng `?token=` là chuẩn.
- PIN cũ giữ nguyên song song để không phá backward compat với parent app hiện tại.
