# Session Log: QR Code ANSI Fix
Date: 2026-04-16

## Mục tiêu
Sửa lại hiển thị QR Code trên terminal (của URL mạng LAN Parent App) để hiển thị dưới dạng mã QR thực tế chuẩn hình vuông có các chấm đen trắng. Lý do là chuỗi ASCII hiện tại (dùng `#` và khoảng trắng) quá khó quét đối với các điện thoại.

## Cách tiếp cận
1. Nhận thấy thư viện `qrcode` trước đó xuất mã ASCII đơn giản.
2. Nâng cấp hàm `_build_ascii_qr` trong `src_brain/network/api_server.py`.
3. Sử dụng mã màu ANSI background (`\033[47m` cho nền trắng và `\033[40m` cho nền đen) kết hợp cùng 2 khoảng trắng liên tiếp để tạo hình vuông khối liền.
4. Điều chỉnh mặc định quét là màu đen trên nền trắng, giúp máy ảnh trên các hệ điều hành điện thoại dễ dàng bắt chéo và quét cực nhạy.
5. Thêm hook `os.system("")` trên môi trường Windows để tự động kích hoạt tính năng Virtual Terminal Processing cho ANSI Escape Codes nếu console chưa bật mặc định.

## Kết quả
- Chạy `python run_tests.py` đã qua 54/54 test.
- Khi khởi chạy API Server, QR Code hiện ra như một hình vuông đen trắng thật sự (như ảnh tĩnh).
- Cập nhật Project docs (PROJECT.md) và handoff.md về những thay đổi mới này trọn vẹn tuân thủ quy tắc làm việc Single Source of Truth của dự án.
