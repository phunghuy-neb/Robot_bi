# Changelog — Phase 1 Bugfix (2026-04-17)

## Tóm tắt

Hai bugfix nhỏ sau khi Phase 1 hoàn thành, phát hiện qua review kỹ lại.

## Bug 1 — Schema bảng `tasks` không khớp với task_manager.py

- **File**: `src_brain/network/db.py`
- **Vấn đề**: Schema CREATE TABLE tasks dùng cột `family_id, title, status` — không khớp với các cột mà `task_manager.py` thực sự dùng.
- **Fix**: Sửa schema thành `task_id, name, remind_time, completed_today, stars, created_at, last_reminded, import_key`.

## Bug 2 — .gitignore sai format, runtime files bị git track

- **File**: `.gitignore`
- **Vấn đề**: 4 rule cuối file bị dính trên cùng 1 dòng + bao bọc bởi dấu ngoặc kép — git không hiểu, bỏ qua hoàn toàn. Hậu quả: `event_queue.json`, `tasks.json`, `robot_bi.db` đang bị git track.
- **Fix**: Tách thành 4 dòng riêng, bỏ dấu ngoặc kép. Chạy `git rm --cached` cho 3 file đang bị track.

## Test

- 71/71 PASS

## Trạng thái

**Phase 1 hoàn chỉnh 100%.** Sẵn sàng bắt đầu Phase 2 — Core Experience.
