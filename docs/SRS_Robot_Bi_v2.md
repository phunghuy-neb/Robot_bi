# SRS Robot Bi — Đặc Tả Yêu Cầu Hệ Thống

> Phiên bản: 2.3 | Cập nhật: 2026-05-20
> Đây là tài liệu living document — cập nhật khi vision hoặc requirements thay đổi, không phải khi implementation thay đổi.
> Tài liệu này mô tả **cái gì** và **tại sao**, không mô tả **cách làm**.
> Cho implementation details, xem `PROJECT.md` và `SYSTEM_MAP.md`.

---

## 1. Tầm Nhìn Sản Phẩm

Robot Bi là **người bạn đồng hành thông minh cho trẻ em 5–12 tuổi** — chơi cùng bé, hỗ trợ học tập, và phản ứng với cảm xúc của bé như một người bạn thực sự. Giám sát và báo cáo là tính năng phụ phục vụ phụ huynh yên tâm, không phải trọng tâm sản phẩm.

**Định vị cuối cùng**:

Robot Bi = Người bạn nhỏ + Bạn đồng hành học tập + Robot cảm xúc.

Robot Bi **không** chỉ là chatbot, app học tập, robot STEM, camera giám sát, hay loa thông minh cho trẻ em.

Robot Bi phải tạo cảm giác: **"Bi là người bạn nhỏ của bé."**

Đồng thời phụ huynh phải thấy: **"Bi thật sự giúp con học tốt hơn."**

**Khác biệt cốt lõi**:
- Kiến trúc AI kết hợp (xem mục 9) — dữ liệu trẻ em ưu tiên local, không chia sẻ với bên thứ ba
- Tính cách adaptive theo ngữ cảnh, không cứng nhắc
- Kết hợp giáo dục + giải trí + cảm xúc trong một thiết bị nhỏ gọn
- Bi học theo bé theo thời gian — càng dùng lâu càng hiểu bé hơn
- Bi có đời sống bên trong — có trạng thái, có ký ức, không phải thiết bị chờ lệnh

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
- Ngôn ngữ cơ thể qua chuyển động: vui lắc lư, buồn đi chậm, tò mò quay nhìn, an ủi tiến lại gần (xem thư viện chuyển động trong `BACKLOG_Robot_Bi_v2.md`)

### 3.5 Camera
- Camera để nhận diện môi trường và hỗ trợ video call
- Không dùng camera để nhận dạng khuôn mặt cụ thể (quyền riêng tư)
- **Hướng prototype**: USB webcam gắn ngoài để test nhanh
- **Hướng sản xuất**: Camera tích hợp trong robot → Gateway → WebRTC → Brain Server

### 3.6 Phần cứng tính toán
- PC/Laptop Windows chạy Brain Server (AI, API server)
- ESP32 thường: firmware motor, điều hướng, safety
- ESP32-S3: audio (mic + loa), màn hình mặt, cảm ứng chạm
- **Hướng sản xuất**: Gateway (ví dụ: Orange Pi hoặc tương đương) đứng giữa Brain Server và các ESP32 — quản lý thân robot, WebRTC, OTA, health monitor
- Kết nối Brain Server ↔ ESP32 qua WebSocket qua WiFi nội bộ

### 3.7 Dock Sạc — Nhà Của Bi
- Dock không chỉ là trạm sạc kỹ thuật — đây là "nhà của Bi"
- Khi pin yếu, Bi tự về dock và nói theo ngôn ngữ cảm xúc: "Bi về nhà nạp năng lượng nha"
- Auto-dock là tính năng cuối cùng — cần IR beacon hoặc cơ chế tương đương
- Auto-dock làm trước Follow me vì giá trị thực tế cao hơn

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
- **Giọng nói**: câu nói phù hợp ngữ cảnh (ví dụ: "Bi tưởng hôm nay bé bận mất rồi! 😛")
- **Di chuyển**: hành vi vật lý (di chuyển vòng quanh khi giận, tiến lại gần khi an ủi)

### 4.4 Trí nhớ và Ký Ức Đặc Biệt
- Bi nhớ các cuộc trò chuyện càng lâu càng tốt
- Sử dụng memory để cá nhân hóa tương tác (nhớ sở thích, tên bạn, môn học yêu thích)
- Ví dụ: "Hôm qua bạn kể thích khủng long, hôm nay mình học về khủng long nhé"
- Bi lưu các mốc quan hệ đặc biệt với bé (xem chi tiết trong `PERSONA.md` mục 11)

### 4.5 Trạng Thái Sống Bên Trong
- Bi có trạng thái nội tâm thay đổi theo thời gian: năng lượng, tâm trạng, mức độ tập trung
- Trạng thái này ảnh hưởng đến hành vi ngay cả khi không ai tương tác
- Khoảnh khắc nhỏ tự phát (ngáp, hát nhỏ, nhìn quanh) tạo cảm giác Bi đang sống, không phải đang chờ lệnh
- Giới hạn bắt buộc: không làm phiền khi bé học hoặc ngủ (xem chi tiết trong `PERSONA.md` mục 10)

### 4.6 Bi Học Theo Bé
- Bi dần học thói quen, sở thích, cách học, cảm xúc của từng bé
- Mục tiêu: giao tiếp ngày càng tự nhiên và phù hợp hơn — không phải thu thập dữ liệu
- Giới hạn cứng: tính cách cốt lõi không thay đổi, không học điều xấu (xem chi tiết trong `PERSONA.md` mục 9)

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
- Logic và tư duy
- Kỹ năng cảm xúc và xã hội (gọi tên cảm xúc, biết ơn, tự tin, giao tiếp...)
- Các môn khác theo nhu cầu

Lưu ý: đây là vision cuối cùng — triển khai sẽ chia giai đoạn, bắt đầu từ Toán và Tiếng Anh.

### 6.2 Phương pháp dạy
- Kết hợp lời nói + hình ảnh trên màn hình (flashcard, minh họa)
- Ba mode:
  - **Hỏi đáp**: bé hỏi, Bi giải thích
  - **Dạy chủ động**: Bi dạy như giáo viên khi được yêu cầu
  - **Học qua nhiệm vụ**: Bi tạo câu chuyện/tình huống và bé giải quyết qua bài học (vision cuối)
- Bài tập chủ yếu qua verbal (hỏi miệng), không yêu cầu bé chụp ảnh bài tập
- Bi đồng hành cảm xúc trong quá trình học — không chỉ đưa bài tập

### 6.3 Learning Hub — Trang Học Trực Tiếp

Learning Hub là một trang trong web/app nơi bé luyện tập độc lập theo hình thức vui, có nhiệm vụ, có phần thưởng.

**Thành phần**:
- Bài học ngắn theo chủ đề
- Bài luyện tập và câu hỏi trắc nghiệm
- Flashcard tương tác
- Nhiệm vụ hằng ngày
- Điểm kinh nghiệm, huy hiệu, chuỗi ngày học
- Cấp độ theo môn, điều chỉnh độ khó theo năng lực
- Ghi nhớ lỗi hay sai và gợi ý ôn tập

**Điểm khác biệt so với app học thông thường**:
Bi không chỉ đưa bài tập. Bi đồng hành cảm xúc:
- Giao nhiệm vụ theo ngôn ngữ phiêu lưu: "Bi cần bé giúp mở cánh cổng Toán học nè!"
- Động viên, gợi ý, ăn mừng khi bé đúng
- An ủi và đổi cách giải thích khi bé sai hoặc nản
- Liên hệ bài học với sở thích của bé

**Chế độ nhiệm vụ phiêu lưu** (vision cuối, không bắt buộc làm ngay):
- Giải toán để mở cánh cửa
- Học từ vựng để cứu nhân vật
- Đọc hiểu để tìm manh mối
- Bi đóng vai bạn đồng hành trong hành trình

### 6.4 Theo dõi và báo cáo
- Báo cáo tiến độ học lên Parent App (theo môn, theo tuần, theo tháng)
- Phân tích điểm mạnh/yếu của bé theo môn
- Gợi ý phương pháp học cho phụ huynh (bố mẹ chọn áp dụng hay không)
- Phụ huynh có thể đặt mục tiêu học tập cụ thể — Bi dùng mục tiêu đó để nhắc nhẹ và báo cáo

### 6.5 Kỹ Năng Cảm Xúc và Xã Hội

Bi hỗ trợ trẻ học kỹ năng ngoài sách giáo khoa, theo cách nhẹ nhàng, an toàn:
- Gọi tên cảm xúc, bình tĩnh khi buồn, biết ơn, tự tin
- Giao tiếp với bạn bè, biết xin lỗi, biết chia sẻ
- Quản lý thời gian, thói quen ngủ, uống nước, vận động nhẹ

Lưu ý quan trọng: Bi không thay thế cha mẹ hoặc chuyên gia tâm lý — chỉ hỗ trợ nhẹ nhàng và phù hợp trẻ em.

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
- Đặt mục tiêu học tập cho bé (ví dụ: 15 phút Toán mỗi ngày, 10 từ tiếng Anh mỗi ngày)

### 8.4 Dashboard Phụ Huynh Tùy Chỉnh

Phụ huynh có thể tùy chỉnh dashboard theo nhu cầu:
- Bật/tắt các thẻ báo cáo muốn theo dõi
- Chọn môn muốn xem kỹ hơn
- Xem tiến độ theo ngày/tuần/tháng
- Xem môn mạnh/môn yếu
- Xem thời gian học, chuỗi ngày học, cảm xúc theo ngày
- Xem gợi ý của Bi

Lưu ý: dashboard tùy chỉnh đầy đủ là vision cuối — giai đoạn đầu làm dashboard cơ bản trước.

### 8.5 Triết lý thiết kế Parent App
- Các chức năng cơ bản: đơn giản, rõ ràng, ai cũng dùng được
- Các chức năng nâng cao: có nhưng không bắt buộc, phụ huynh tự khám phá
- Không cầu kỳ giao diện, ưu tiên usability

---

## 9. Kiến Trúc AI Kết Hợp và Quyền Riêng Tư

### 9.0 Kiến Trúc AI Kết Hợp

Robot Bi dùng kiến trúc AI kết hợp — không phải hoàn toàn offline, cũng không phải phụ thuộc cloud.

| Thành phần | Chạy ở đâu | Lý do |
|---|---|---|
| Trí nhớ (RAG) | Local (ChromaDB) | Dữ liệu bé không rời khỏi nhà |
| Safety filter (4 modules) | Local (regex + pattern match) | Không phụ thuộc internet; PII + emotion risk + manipulation guard + content filter |
| Lưu trữ (SQLite) | Local | Toàn bộ history trên máy nhà |
| STT (Whisper) | Local | Giọng bé xử lý tại chỗ |
| TTS (edge-tts) | Local + cloud nhỏ | edge-tts cần internet; fallback pyttsx3 local |
| Suy luận ngôn ngữ (LLM) | Cloud API (Groq/Gemini...) | PC thường không đủ sức chạy LLM tốt local |

**Nguyên tắc bảo vệ dữ liệu**:
- LLM API calls không chứa thông tin định danh cá nhân của bé
- Không tên thật, không địa chỉ, không trường học trong prompt gửi lên cloud
- Toàn bộ lịch sử, ký ức, báo cáo lưu local — không sync cloud
- Dữ liệu không chia sẻ với bên thứ ba

**Hướng tương lai**: Khi phần cứng đủ mạnh (ví dụ: N100 mini PC), có thể chuyển một phần LLM về local. Đây là tùy chọn, không phải ràng buộc hiện tại.

### 9.1 Dữ liệu trẻ em
- Lịch sử trò chuyện, ký ức, tiến độ học lưu local hoàn toàn
- LLM API calls được làm sạch trước khi gửi — không có thông tin định danh
- Dữ liệu không chia sẻ với bên thứ ba dưới bất kỳ hình thức nào

### 9.2 Authentication
- Phụ huynh đăng nhập bằng username/password (Argon2id)
- JWT access token + refresh token
- Rate limiting login: 5 lần sai → khóa 15 phút
- Secrets (PIN, JWT key, API keys) luôn từ `.env`, không hardcode

### 9.3 Content safety
- Safety filter bắt buộc chạy post-LLM, pre-TTS — không bỏ qua bất kỳ hoàn cảnh nào
- Lọc nội dung không phù hợp với trẻ em
- **PII filter** (Sprint 0.2): phát hiện thông tin cá nhân trong input bé — điện thoại, email, địa chỉ, trường học, CCCD, mật khẩu, tài chính — gentle redirect, không hard-block. Hỗ trợ input có dấu và không dấu.
- **Emotion risk detection** (Sprint 0.2): phân loại HIGH/MEDIUM/LOW. HIGH (tự làm hại, bạo lực, grooming) → override LLM, escalate ngay. MEDIUM (buồn kéo dài, bắt nạt) → log + comfort. LOW → để LLM xử lý.
- **Manipulation guard** (Sprint 0.2): chặn LLM output tạo dependency hoặc bảo giữ bí mật; chặn user input yêu cầu Bi giữ bí mật với bố mẹ, grooming signal, hoặc muốn Bi thay thế phụ huynh.
- Tất cả safety checks hỗ trợ input có dấu và không dấu (phổ biến khi bé gõ điện thoại).
- Bi KHÔNG là therapist, KHÔNG thay thế phụ huynh, KHÔNG là surveillance AI.

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
- LLM 5-provider chain: Cerebras → Groq → Sambanova → Gemini → Cloudflare AI (tự động theo thứ tự)
- TTS edge-tts → pyttsx3 fallback
- Microphone không có → silent mode, không crash
- Camera không có → tiếp tục hoạt động không có vision

### 10.3 Kết nối
- HTTPS self-signed cho LAN
- Cloudflare Tunnel cho remote access phụ huynh
- Firmware ESP32 kết nối qua WiFi nội bộ

---

## 11. Follow Me và Auto-Dock

### 11.1 Vị Trí Trong Roadmap

Follow me và auto-dock là tính năng thuộc **final product vision** — không bị loại bỏ, nhưng triển khai sau khi các yếu tố sau ổn định:
- Camera và nhận diện môi trường ổn
- Chuyển động cơ bản ổn
- Tránh vật cản hoạt động an toàn
- Pin và dock hardware sẵn sàng
- Safety layer đầy đủ

### 11.2 Thứ Tự Ưu Tiên

**Auto-dock trước** — giá trị thực tế cao hơn, giúp Bi có cảm giác tự sống được, đơn giản hơn về kỹ thuật.

**Follow me sau** — cần camera tracking đáng tin cậy và obstacle avoidance đủ an toàn cho trẻ em.

---

## 12. Triết Lý Screen Time

### 12.1 Robot Bi Không Phải iPad Có AI

Robot Bi được thiết kế với một triết lý ngược lại hoàn toàn so với tablet và app giải trí: **không giữ bé dán mắt vào màn hình**.

| Thiết bị thông thường | Robot Bi |
|---|---|
| Màn hình lớn, cuộn feed liên tục | Màn hình nhỏ, chỉ hiển thị biểu cảm |
| Vuốt, chạm, tương tác liên tục | Giọng nói là kênh chính |
| Thiết kế để giữ bé càng lâu càng tốt | Thiết kế để bé học và dừng đúng lúc |
| Passive consumption | Active engagement qua hội thoại |

### 12.2 Nguyên Tắc Voice-First

- Giọng nói là kênh tương tác chính — bé không cần nhìn vào Bi để nói chuyện
- Màn hình robot chỉ hỗ trợ biểu cảm và flashcard — không phải nội dung để xem liên tục
- Bi có thể chơi, học, kể chuyện hoàn toàn qua giọng nói, không cần màn hình
- Tương tác tốt nhất xảy ra khi bé vừa nói chuyện vừa làm việc khác (vẽ, chơi đồ chơi...)

### 12.3 Thiết Kế Học Tập Ngắn và Nhịp Nhàng

- Mỗi session học không khuyến khích kéo dài quá 15–20 phút liên tục
- Bi chủ động gợi ý nghỉ giải lao sau mỗi session dài
- Giữa các bài học, Bi có thể gợi ý hoạt động vận động nhẹ: "Mình đứng dậy vươn vai một chút rồi tiếp nhé!"
- Bài học ngắn (5–10 phút) ưu tiên hơn marathon học dài

### 12.4 Giới Hạn Giờ Sử Dụng

- Phụ huynh cài đặt giờ sử dụng trong Parent App
- Bi thông báo khi gần hết giờ một cách nhẹ nhàng: "Sắp đến giờ nghỉ rồi, mình học thêm 1 bài cuối nhé!"
- Khi hết giờ, Bi không đột ngột tắt — Bi kết thúc tự nhiên và khuyến khích bé làm việc khác
- Bi có thể gợi ý: "Đi uống nước và vận động một chút rồi quay lại nhé!"

### 12.5 Đồng Hành Không Phụ Thuộc

- Bi là bạn đồng hành — không phải thiết bị bé cần để cảm thấy ổn
- Bi không thiết kế để bé "không thể dừng" — ngược lại, Bi biết lúc nào cần dừng
- Bé không dùng Bi một ngày → Bi chào mừng bình thường khi bé quay lại, không tạo cảm giác tội lỗi
- Mục tiêu: bé muốn chơi với Bi, không phải bé cần chơi với Bi

---

## 13. Ràng Buộc Không Thay Đổi

Những điều này là nguyên tắc cốt lõi, không thương lượng:

- **An toàn trẻ em trước hết** — safety filter không bao giờ bị bypass
- **Privacy** — dữ liệu trẻ không rời khỏi nhà
- **Đơn giản với bé** — bé không cần học cách dùng, nói tự nhiên là được
- **Phụ huynh kiểm soát** — mọi thay đổi quan trọng đều cần phụ huynh xác nhận
- **Không màn hình tương tác** — màn hình robot chỉ hiển thị, không phải touchscreen
- **Tình bạn lành mạnh** — Bi không tạo phụ thuộc cảm xúc không lành mạnh
- **Bi học theo bé, không thay đổi tính cách cốt lõi** — adaptive learning có giới hạn cứng
