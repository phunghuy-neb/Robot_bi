# Session 2026-04-16 — EarSTT microphone fallback

## Mục tiêu
- Sửa lỗi microphone `Invalid number of channels [PaErrorCode -9998]` trong `src_brain/senses/ear_stt.py`.
- Không thay đổi logic protected ngoài phần khởi tạo và mở `InputStream`.

## Đã làm
- Thêm probe microphone khi khởi tạo `EarSTT`.
- Liệt kê input devices và thử mở theo thứ tự ưu tiên:
  - `MIC_DEVICE` hiện tại trước nếu còn hợp lệ.
  - Các input device còn lại sau đó.
  - Mỗi thiết bị thử `1` channel trước, fail mới thử `2` channels.
- Lưu cấu hình microphone đã probe thành công để `listen()` và `listen_for_wakeword()` dùng lại.
- Nếu không có cấu hình nào mở được, chuyển sang silent mode và để `listen()` trả `""` thay vì crash.
- Chặn spam lỗi microphone bằng cờ log-once nội bộ.
- Giữ nguyên `Whisper large-v2` và cơ chế GPU/CPU auto-detect hiện có.

## Kết quả kiểm tra
- `python run_tests.py` => `54/54 PASS`.
- Khởi động `src_brain.main_loop` trong môi trường hiện tại:
  - Log nhận được: `Đang tìm microphone...`
  - Log nhận được: `Không tìm thấy microphone hợp lệ, chuyển sang chế độ im lặng`
  - Không còn xuất hiện `Invalid number of channels [PaErrorCode -9998]`.

## File chỉnh sửa
- `src_brain/senses/ear_stt.py`
- `PROJECT.md`
- `.claude/handoff.md`
