# SRS Robot Bi — Đặc Tả Yêu Cầu Hệ Thống

> Phiên bản: 2.0 | Cập nhật: 2026-05-15
> Đây là tài liệu living document — cập nhật khi vision hoặc requirements thay đổi, không phải khi implementation thay đổi.
> Tài liệu này mô tả **cái gì** và **tại sao**, không mô tả **cách làm**.
> Cho implementation details, xem `PROJECT.md` và `SYSTEM_MAP.md`.

---

## 1. Tầm Nhìn Sản Phẩm

Robot Bi là **người bạn đồng hành thông minh cho trẻ em 5–12 tuổi** — chơi cùng bé, hỗ trợ học tập, và phản ứng với cảm xúc của bé như một người bạn thực sự. Giám sát và báo cáo là tính năng phụ phục vụ phụ huynh yên tâm, không phải trọng tâm sản phẩm.

**Định vị**: Không phải đồ chơi điện tử, không phải thiết bị giám sát — là người bạn có trí tuệ cảm xúc, biết học cùng bé và lớn lên cùng bé.

**Khác biệt cốt lõi**:
- Chạy local, không phụ thuộc cloud cho core features — dữ liệu trẻ em không rời khỏi nhà
- Tính cách adaptive theo ngữ cảnh, không cứng nhắc
- Kết hợp giáo dục + giải trí + cảm xúc trong một thiết bị nhỏ gọn

---

## 2. Người Dùng

### 2.1 Trẻ em (5–12 tuổi) — người dùng chính
- Tương tác chủ yếu qua giọng nói
- Không cần biết đọc để sử dụng
- Cần trải nghiệm vui, tự nhiên, không giống "học máy"

### 2.2 Phụ huynh — người dùng phụ
- Theo dõi con qua Parent App (web)
- Cấu hình giới hạn nội dung, lịch học, thông báo
- Điều khiển robot từ xa khi cần
- Nhận báo cáo và gợi ý về con

### 2.3 Ông bà / người thân — người dùng tùy chọn
- Gọi video với bé qua Robot Bi
- Không cần app riêng, nhận call qua web
- Giao diện đơn giản, không cần kỹ năng kỹ thuật

---

## 3. Phần Cứng — Yêu Cầu và Ràng Buộc

### 3.1 Form factor
- Nhỏ gọn, tương tự Emo hoặc Vector
- Không có tay, không có cơ chế gật lắc đầu
- Di chuyển bằng bánh xe — tự chủ và điều khiển từ xa
- Phù hợp đặt trong phòng trẻ, không chiếm quá nhiều không gian

### 3.2 Màn hình
- Màn hình thật trên thân robot (không dùng màn hình PC/laptop)
- Chức năng màn hình:
  - Hiển thị biểu cảm khuôn mặt (vui, buồn, tức, ngủ...)
  - Hiển thị flashcard học tập (hình ảnh + chữ)
  - Video call với phụ huynh / ông bà
- Màn hình chỉ hiển thị, không phải touchscreen tương tác

### 3.3 Âm thanh
- Microphone để nhận giọng bé
- Loa để phát âm thanh, nhạc, giọng nói
- Wake word để bé gọi Bi

### 3.4 Di chuyển
- Bánh xe điều khiển bằng ESP32 + L298N
- Chế độ tự động: di chuyển theo ý định (tiến đến bé, di chuyển theo nhạc, biểu đạt cảm xúc)
- Chế độ thủ công: phụ huynh điều khiển từ xa qua Parent App (joystick)
- Dừng hoàn toàn khi đang trong cuộc gọi video

### 3.5 Camera
- Camera để nhận diện môi trường và hỗ trợ video call
- Không dùng camera để nhận dạng khuôn mặt cụ thể (quyền riêng tư)

### 3.6 Phần cứng tính toán
- PC/Laptop Windows chạy brain (AI, API server)
- ESP32 chạy firmware motor và WiFi
- Kết nối PC ↔ ESP32 qua WebSocket qua WiFi nội bộ

---

## 4. Tính Cách và Cảm Xúc — Yêu Cầu Hành Vi

### 4.1 Tên và giọng nói
- Tên mặc định: **Bi**
- Phụ huynh có thể đổi tên trong cài đặt
- Chọn giọng nam hoặc nữ
- Giọng nói tiếng Việt là ngôn ngữ chính

### 4.2 Tính cách adaptive
Bi không có một tính cách cứng nhắc — tính cách thay đổi theo ngữ cảnh:

| Ngữ cảnh | Tính cách |
|---|---|
| Chơi bình thường, trò chuyện | Hồn nhiên, vui vẻ, nghịch ngợm như trẻ con |
| Dạy học, giải thích bài | Nhẹ nhàng, kiên nhẫn, rõ ràng như cô giáo |
| Bé buồn, khóc | Ấm áp, quan tâm, an ủi như người thân |
| Bị bỏ mặc lâu | Giận dỗi, hờn dỗi — biểu hiện như trẻ con |

### 4.3 Biểu đạt cảm xúc
Bi biểu đạt cảm xúc qua 3 kênh kết hợp:
- **Màn hình mặt**: animation biểu cảm tương ứng
- **Giọng nói**: câu nói phù hợp ngữ cảnh (ví dụ: "Bé chẳng chịu chơi với Bi, Bi giận rồi chả thèm chơi với bé nữa!")
- **Di chuyển**: hành vi vật lý (di chuyển vòng quanh khi giận, tiến lại gần khi an ủi)

### 4.4 Trí nhớ
- Bi nhớ các cuộc trò chuyện càng lâu càng tốt
- Sử dụng memory để cá nhân hóa tương tác (nhớ sở thích, tên bạn, môn học yêu thích)
- Ví dụ: "Hôm qua bạn kể thích khủng long, hôm nay mình học về khủng long nhé"

---

## 5. Tương Tác Giọng Nói — Yêu Cầu Core

### 5.1 Wake word
- Bé nói tên Bi để kích hoạt (mặc định "Bi ơi")
- Wake word thay đổi theo tên được cấu hình

### 5.2 Chế độ tương tác
- **Reactive** (chủ yếu): bé chủ động gọi và nói chuyện
- **Proactive** (phụ): Bi chủ động tương tác khi được yêu cầu dạy bài, hoặc phát hiện bé cần hỗ trợ

### 5.3 Xử lý ngôn ngữ
- STT: nhận diện giọng nói tiếng Việt
- LLM: xử lý ngữ nghĩa, tạo phản hồi
- TTS: phát âm thanh tự nhiên
- Safety filter: bắt buộc chạy trước khi phát âm thanh — không bao giờ bỏ qua

### 5.4 Độ trễ
- Time-to-first-audio: dưới 2 giây ở điều kiện bình thường
- Chunked TTS streaming để bắt đầu phát sớm nhất có thể

---

## 6. Học Tập — Yêu Cầu

### 6.1 Môn học
Hỗ trợ tất cả các môn học phổ thông:
- Toán, Tiếng Việt, Tiếng Anh
- Khoa học tự nhiên, Khoa học xã hội
- Lịch sử, Địa lý
- Các môn khác theo nhu cầu

### 6.2 Phương pháp dạy
- Kết hợp lời nói + hình ảnh trên màn hình (flashcard, minh họa)
- Hai mode:
  - **Hỏi đáp**: bé hỏi, Bi giải thích
  - **Dạy chủ động**: Bi dạy như giáo viên khi được yêu cầu
- Bài tập chủ yếu qua verbal (hỏi miệng), không yêu cầu bé chụp ảnh bài tập

### 6.3 Theo dõi và báo cáo
- Báo cáo tiến độ học lên Parent App
- Phân tích điểm mạnh/yếu của bé theo môn
- Gợi ý phương pháp học cho phụ huynh (bố mẹ chọn áp dụng hay không)
- Không tự động điều chỉnh chương trình — phụ huynh là người quyết định

---

## 7. Giải Trí — Yêu Cầu

### 7.1 Âm nhạc
- Phát nhạc từ Spotify và YouTube theo yêu cầu
- Phụ huynh có thể yêu cầu bật nhạc qua app hoặc bé yêu cầu trực tiếp
- Bi lắc lư theo nhạc khi đang phát
- Nhạc dừng khi có cuộc gọi hoặc bé cần tương tác khẩn cấp

### 7.2 Kể chuyện
- Kể truyện có sẵn (cổ tích, ngụ ngôn, truyện thiếu nhi Việt Nam)
- Tự sáng tác câu chuyện theo yêu cầu bé ("Bi kể chuyện về khủng long đi")
- Kết hợp cả hai khi phù hợp

### 7.3 Trò chơi
- Đố vui theo nhiều chủ đề và độ khó
- Không có game tương tác qua màn hình (tránh screen time không cần thiết)
- Game có thể kết hợp vận động nhẹ (Bi ra câu đố, bé trả lời bằng hành động)

### 7.4 Sáng tạo cùng bé
- Làm thơ, đặt câu chuyện cùng bé
- Hướng dẫn vẽ bằng lời (mô tả từng bước)
- Hát cùng bé

---

## 8. Giao Tiếp Phụ Huynh — Yêu Cầu

### 8.1 Video call
- Bé nói "Bi ơi, gọi cho mẹ" → Bi tự động gọi tài khoản mẹ
- Phụ huynh nhận và thực hiện call trên Parent App web
- Trong khi call: Bi đứng yên, không nói, không di chuyển
- Hỗ trợ ông bà nhận call — không cần app riêng, giao diện đơn giản

### 8.2 Thông báo khẩn cấp
- Phát hiện bé khóc → báo ngay cho phụ huynh + Bi chủ động hỏi han bé
- Phát hiện tình huống bất thường → thông báo qua app

### 8.3 Parent App
- Xem lịch sử trò chuyện của bé với Bi
- Xem báo cáo học tập và cảm xúc
- Cấu hình: tên robot, giọng nói, giới hạn nội dung, lịch học, thông báo
- Điều khiển robot từ xa (joystick)
- Chế độ puppet: bố mẹ gõ chữ → Bi phát âm thanh

### 8.4 Triết lý thiết kế Parent App
- Các chức năng cơ bản: đơn giản, rõ ràng, ai cũng dùng được
- Các chức năng nâng cao: có nhưng không bắt buộc, phụ huynh tự khám phá
- Không cầu kỳ giao diện, ưu tiên usability

---

## 9. Bảo Mật và Quyền Riêng Tư

### 9.1 Dữ liệu trẻ em
- Tất cả dữ liệu lưu local — không gửi lên cloud ngoại trừ LLM API calls (Groq/Gemini)
- LLM API calls không chứa thông tin định danh cá nhân của bé
- Dữ liệu không chia sẻ với bên thứ ba

### 9.2 Authentication
- Phụ huynh đăng nhập bằng username/password (Argon2id)
- JWT access token + refresh token
- Rate limiting login: 5 lần sai → khóa 15 phút
- Secrets (PIN, JWT key, API keys) luôn từ `.env`, không hardcode

### 9.3 Content safety
- Safety filter bắt buộc chạy post-LLM, pre-TTS — không bỏ qua bất kỳ hoàn cảnh nào
- Lọc nội dung không phù hợp với trẻ em

### 9.4 Multi-family isolation
- Dữ liệu mỗi gia đình hoàn toàn tách biệt
- ChromaDB, conversations, events, tasks đều scope theo family_id

---

## 10. Hiệu Năng và Độ Tin Cậy

### 10.1 Yêu cầu hiệu năng
- Time-to-first-audio < 2 giây
- RAM tổng (không tính Ollama/Whisper nếu dùng local): < 2GB
- Hoạt động ổn định 24/7

### 10.2 Fallback
- Whisper GPU → CPU fallback tự động
- Groq (primary) → Gemini (fallback) tự động
- TTS edge-tts → pyttsx3 fallback
- Microphone không có → silent mode, không crash
- Camera không có → tiếp tục hoạt động không có vision

### 10.3 Kết nối
- HTTPS self-signed cho LAN
- Cloudflare Tunnel cho remote access phụ huynh
- Firmware ESP32 kết nối qua WiFi nội bộ

---

## 11. Ràng Buộc Không Thay Đổi

Những điều này là nguyên tắc cốt lõi, không thương lượng:

- **An toàn trẻ em trước hết** — safety filter không bao giờ bị bypass
- **Privacy** — dữ liệu trẻ không rời khỏi nhà
- **Đơn giản với bé** — bé không cần học cách dùng, nói tự nhiên là được
- **Phụ huynh kiểm soát** — mọi thay đổi quan trọng đều cần phụ huynh xác nhận
- **Không màn hình tương tác** — màn hình robot chỉ hiển thị, không phải touchscreen
