# Session Log: SQLite Storage Migration
Date: 2026-04-16

## Mục tiêu
Chuyển storage backend của `src_brain/network/event_queue.json` và `src_brain/network/tasks.json` sang SQLite, nhưng giữ nguyên API, behavior và shape dữ liệu của TaskManager, EventNotifier và Parent App API.

## Các thay đổi chính
1. Thêm `src_brain/network/db.py` với `src_brain/network/robot_bi.db`, `get_db_connection()` dùng `PRAGMA journal_mode=WAL`, `init_db()` và migration idempotent từ JSON backup cũ sang bảng `events` và `tasks`.
2. Refactor `src_brain/network/task_manager.py` để thay toàn bộ read/write `tasks.json` bằng SQLite queries, nhưng giữ nguyên tên method, tham số và kiểu trả về.
3. Refactor `src_brain/network/notifier.py` để thay persistence `event_queue.json` bằng SQLite; format event object và WebSocket broadcaster interface không đổi.
4. Refactor `src_brain/network/api_server.py` để đọc danh sách event/chat từ SQLite thay vì `_notifier._events`.
5. Cập nhật `src_brain/main_loop.py` và `run_tests.py` để gọi `init_db()` một lần trong mỗi process trước khi dùng storage.

## Dữ liệu & tương thích
- Hai file JSON cũ vẫn được giữ nguyên làm backup.
- Migration cũ -> mới là idempotent: re-run không tạo duplicate records.
- Trường nested `metadata` của event được lưu trong SQLite dưới dạng JSON string và deserialize lại khi đọc ra.

## Kiểm tra
- Chạy `python run_tests.py`
- Kết quả: `54/54 PASS`
- Xác nhận DB đã được tạo tại `src_brain/network/robot_bi.db`
