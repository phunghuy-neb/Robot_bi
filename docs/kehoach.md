> TAI LIEU NAY DA LOI THOI
> Stack thuc te: Groq (`llama-3.3-70b-versatile`) + Gemini fallback.
> Khong dung Ollama/Qwen local. Xem `PROJECT.md` de biet trang thai hien tai.

🚀 LỘ TRÌNH THỰC THI DỰ ÁN ROBOT BI (MASTER PLAN)
📌 Giai đoạn 1: Thiết lập nền móng (Đã hoàn thành)
[x] Phác thảo ý tưởng và chốt danh sách tính năng.

[x] Xây dựng cấu trúc thư mục dự án chuẩn (Robot_Bi_Project/).

[x] Hoàn thiện tài liệu Đặc tả yêu cầu hệ thống (SRS 1.0).

[x] Thiết lập hệ thống quản lý mã nguồn (Git & GitHub).

👂 Giai đoạn 2: Hệ thống Giao tiếp (Sprint 1)
Mục tiêu: Robot có thể Nghe và Nói một cách tự nhiên.

[x] Module Đôi tai (Ear STT): - Cài đặt Whisper và SpeechRecognition.

Hoàn thiện file ear_stt.py (Nhận diện tiếng Việt, lọc tạp âm).

[x] Module Cái miệng (Mouth TTS): - Cài đặt Edge-TTS và Pygame.

Hoàn thiện file mouth_tts.py (Giọng HoaiMyNeural, phát âm thanh offline).

[x] Tích hợp Não bộ (AI Core):

Kết nối core_ai.py với Ollama (Qwen 2.5 7B).

Viết main_loop.py phiên bản 1.0: Nghe -> Nghĩ -> Nói.

🧠 Giai đoạn 3: Trí nhớ & Ngữ cảnh (Sprint 2)
Mục tiêu: Bi nhận ra "người quen" và nhớ được sở thích của bé.

[ ] Thiết lập Vector Database: Cài đặt ChromaDB để lưu trữ trí nhớ dài hạn.

[ ] Module RAG (Memory Manager): - Viết code trích xuất thông tin quan trọng từ cuộc hội thoại.

Code truy vấn ký ức để đưa vào Prompt cho AI.

[ ] Personalization: Test khả năng ghi nhớ tên bé, món ăn yêu thích và các sự kiện trong ngày.

👁️ Giai đoạn 4: Thị giác & An ninh (Sprint 3)
Mục tiêu: Bi có thể quan sát và bảo vệ không gian của bé.

[ ] Module Camera cơ bản: Sử dụng OpenCV để stream hình ảnh từ Webcam.

[ ] Xử lý hình ảnh thông minh:

Phát hiện chuyển động (Motion Detection).

Nhận diện khuôn mặt (Face Recognition) các thành viên trong nhà.

Nhận diện thẻ Flashcard (Học tập).

[ ] Hệ thống cảnh báo: Code tự động gửi thông báo khi phát hiện tiếng khóc hoặc người lạ.

🚗 Giai đoạn 5: Cơ khí & Vận động (Sprint 4)
Mục tiêu: Bi thoát khỏi bàn làm việc và có thể di chuyển quanh nhà.

[ ] Lập trình Vi điều khiển: Viết code C++ cho ESP32 điều khiển động cơ qua module L298N.

[ ] Giao tiếp Robot-PC: Sử dụng WebSocket để máy tính gửi lệnh di chuyển (Tiến/Lùi/Trái/Phải) xuống Robot.

[ ] Tính năng cao cấp: - Code bám đuôi bé (Follow me) bằng OpenCV.

Chế độ tự động tìm đường tránh vật cản.

📱 Giai đoạn 6: Trung tâm Điều khiển (Sprint 5)
Mục tiêu: Phụ huynh làm chủ hoàn toàn Robot qua điện thoại.

[ ] Xây dựng App di động: Thiết kế giao diện Dashboard, Live Camera và Joystick điều khiển.

[ ] Nhật ký Chat: Kết nối App với cơ sở dữ liệu để phụ huynh xem lại toàn bộ nội dung bé đã nói chuyện với Bi.

[ ] Tính năng Puppet (Nhập vai): Phụ huynh gõ chữ trên App, Bi ở nhà phát âm thanh ngay lập tức.

[ ] Quản lý Nhiệm vụ: Hệ thống tặng sao và nhắc nhở bé làm việc nhà.

🧪 Giai đoạn 7: Tối ưu & Đóng gói (Sprint 6)
[ ] Stress Test: Kiểm tra hiệu năng RAM (đảm bảo không vượt quá 13GB/16GB).

[ ] Tối ưu độ trễ: Đảm bảo thời gian phản hồi dưới 2.5 giây.

[ ] Bảo mật: Mã hóa dữ liệu trí nhớ và hình ảnh cục bộ.

[ ] Hoàn thiện báo cáo: Chốt tài liệu hướng dẫn sử dụng và vận hành.
