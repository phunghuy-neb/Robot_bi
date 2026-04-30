# Changelog — 2026-04-17: Phase 1 Bugfix (index.html + run_tests isolation + DB cleanup)

## Tóm tắt

Bugfix sau khi hoàn thành Phase 1. Ba vấn đề được giải quyết trong session này.

## Chi tiết thay đổi

### 1. index.html — Thêm flow đăng nhập JWT

**Vấn đề:** JWT middleware bảo vệ tất cả endpoints, nhưng giao diện web (`index.html`) không có form đăng nhập và không attach Bearer token. Kết quả: toàn bộ giao diện bị chặn 401.

**Fix:** Thêm flow đăng nhập đầy đủ:
- Form login (username + password)
- Gọi `POST /auth/login/v2`, lưu `access_token` vào `localStorage`
- Tự động attach `Authorization: Bearer <token>` vào mọi API call và WebSocket connect

### 2. run_tests.py — DB riêng biệt cho test

**Vấn đề:** Test ghi thẳng vào production DB (`robot_bi.db`), tạo user rác mỗi lần chạy.

**Fix:** Dùng DB riêng biệt tại `src_brain/memory_rag/_audit_test_db/` (đã có sẵn trong cấu trúc). Production DB không bị động đến khi chạy test.

### 3. Cleanup production DB

**Vấn đề:** 58 user rác từ các lần test cũ tồn tại trong `robot_bi.db`.

**Fix:** Xóa toàn bộ user rác. DB hiện sạch: 1 user `admin`.

## Test

- 71/71 PASS

## Files thay đổi

- `src_brain/network/static/index.html` — thêm login flow JWT
- `run_tests.py` — dùng test DB riêng
