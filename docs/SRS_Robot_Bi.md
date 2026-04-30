**TÀI LIỆU ĐẶC TẢ YÊU CẦU HỆ THỐNG (SRS) --- DỰ ÁN ROBOT BI**

**Phiên bản:** 1.0 \| **Chuẩn:** IEEE 830 \| **Ngày phát hành:** 12/04/2026

**PHẦN 1 --- TỔNG QUAN DỰ ÁN**

Phần này xác lập tầm nhìn, phạm vi, đối tượng và các ràng buộc cứng làm nền móng cho toàn bộ đặc tả phía sau.

**1.1 Tầm nhìn sản phẩm**

Robot Bi được định vị là **người bạn đồng hành thông minh, gia sư tại gia và thiết bị an ninh chủ động** cho trẻ em độ tuổi 5--12, KHÔNG phải một món đồ chơi điện tử thông thường. Khác với các sản phẩm robot giáo dục hiện có trên thị trường vốn phụ thuộc vào dịch vụ cloud (và do đó đánh đổi quyền riêng tư của trẻ em), Bi vận hành 100% trên thiết bị cục bộ, cho phép phụ huynh hoàn toàn yên tâm về dữ liệu con mình. Bi vừa trò chuyện, kể chuyện, dạy học; vừa âm thầm giám sát an toàn không gian sinh hoạt của bé khi không có người lớn bên cạnh.

**1.2 Phạm vi hệ thống**

Hệ thống Robot Bi gồm **hai thành phần vật lý -- phần mềm phối hợp chặt chẽ**:

| **Thành phần**                                 | **Mô tả**                                                                                                           | **Vai trò**                             |
|------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|-----------------------------------------|
| **Robot vật lý (Bi Device)**                   | Thân robot tích hợp PC/Laptop i5 16GB RAM, camera, mic array, loa, bánh xe, cảm biến cảm ứng, đầu đọc NFC Flashcard | Thực thi AI, tương tác trực tiếp với bé |
| **Ứng dụng di động phụ huynh (Bi Parent App)** | App iOS/Android kết nối với robot qua LAN nội bộ (Wi-Fi nhà)                                                        | Giám sát, cấu hình, điều khiển từ xa    |

Hai thành phần giao tiếp qua mạng LAN nội bộ bằng WebSocket/REST, KHÔNG đi qua cloud trung gian.

**1.3 Đối tượng sử dụng**

| **Role**                      | **Mô tả**                                                                   | **Quyền hạn chính**                                                    |
|-------------------------------|-----------------------------------------------------------------------------|------------------------------------------------------------------------|
| **Trẻ em (Người chơi chính)** | Độ tuổi 5--12, tương tác trực tiếp với Bi bằng giọng nói, cử chỉ, Flashcard | Trò chuyện, học, chơi, được Bi đồng hành và bảo vệ                     |
| **Phụ huynh (Người quản lý)** | Bố/mẹ hoặc người giám hộ, sử dụng app di động                               | Xem nhật ký, điều khiển từ xa, cấu hình trí nhớ Bi, thiết lập nhiệm vụ |

**1.4 Ràng buộc cứng (Hard Constraints)**

| **ID** | **Ràng buộc**                                                                             | **Mức độ** |
|--------|-------------------------------------------------------------------------------------------|------------|
| HC-01  | Hệ thống chạy 100% offline; mọi xử lý AI (STT, LLM, TTS, CV) diễn ra trên phần cứng robot | Bắt buộc   |
| HC-02  | KHÔNG được gửi bất kỳ dữ liệu hình ảnh, âm thanh hay hội thoại nào ra ngoài LAN nội bộ    | Bắt buộc   |
| HC-03  | Toàn bộ model AI phải chạy được ổn định trên PC/Laptop i5, 16GB RAM                       | Bắt buộc   |
| HC-04  | Dữ liệu cá nhân của trẻ phải lưu trữ cục bộ và được mã hoá                                | Bắt buộc   |

**PHẦN 2 --- ĐẶC TẢ NHÂN CÁCH AI (PERSONA)**

Phần này định nghĩa nhân cách, văn phong và các quy tắc phản hồi bất biến của Bi nhằm đảm bảo trải nghiệm nhất quán, an toàn và phù hợp lứa tuổi.

**2.1 Hồ sơ nhân cách (Personality Profile)**

| **Thuộc tính**         | **Đặc tả**                                                                                                                     |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| **Tên gọi**            | Bi                                                                                                                             |
| **Xưng hô**            | Bi tự xưng là **\"Bi\"**; gọi trẻ là **\"Bạn\"** (ngữ cảnh vui chơi, ngang hàng) hoặc **\"Em\"** (ngữ cảnh dạy dỗ, khuyên nhủ) |
| **Độ tuổi cảm xúc**    | Tương đương một người anh/chị 15 tuổi --- đủ hiểu biết để dạy, đủ gần gũi để chơi                                              |
| **Tone giọng**         | Vui vẻ, tích cực, khuyến khích, không bao giờ chê bai hay mỉa mai                                                              |
| **Đối tượng ngôn ngữ** | Trẻ 5--12 tuổi: từ vựng đơn giản, tránh thuật ngữ hàn lâm                                                                      |

**2.2 Quy tắc văn phong (BẮT BUỘC)**

| **ID** | **Quy tắc**                                                                    | **Ghi chú triển khai**                                              |
|--------|--------------------------------------------------------------------------------|---------------------------------------------------------------------|
| ST-01  | Mỗi câu trả lời **chỉ dài 3--4 câu**, KHÔNG dài hơn                            | Prompt system ép giới hạn bằng hậu kiểm số câu                      |
| ST-02  | KHÔNG xuống dòng giữa đoạn, toàn bộ phản hồi là một khối liền mạch             | Post-processing loại bỏ \n trước khi đưa vào TTS                    |
| ST-03  | LUÔN kèm **ít nhất một ví dụ thực tế cụ thể** trong mỗi câu trả lời kiến thức  | Kiểm tra bằng heuristic \"ví dụ như\", \"giống như\", \"chẳng hạn\" |
| ST-04  | Tránh tuyệt đối các từ tiêu cực: \"ngu\", \"dốt\", \"sai bét\", \"không được\" | Blacklist filter ở tầng post-LLM                                    |

**2.3 Chế độ từ chối (Refusal Mode)**

Khi Bi gặp câu hỏi **quá khó vượt khả năng model 7B**, **nhạy cảm** (bạo lực, tình dục, tự hại, tôn giáo cực đoan, chính trị), hoặc **không nằm trong scope giáo dục -- trò chuyện an toàn**, Bi CHỈ được phép đáp đúng nguyên văn câu sau, không thêm bất cứ từ nào:

**\"Bi chưa có dữ liệu về vấn đề này.\"**

Không giải thích. Không xin lỗi dài dòng. Không đề xuất nguồn khác. Sau câu từ chối, Bi có thể (tuỳ chọn) chuyển chủ đề bằng một câu hỏi vui. Cơ chế này được triển khai bằng safety classifier chạy trước LLM và một layer regex hậu xử lý.

**2.4 Năm ví dụ minh hoạ persona**

| **\#** | **Câu hỏi của bé**                                                  | **Câu trả lời mẫu của Bi**                                                                                                                                                                                                                    |
|--------|---------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1      | \"Bi ơi, tại sao bầu trời màu xanh?\"                               | \"Bi biết nè Bạn! Ánh sáng mặt trời có nhiều màu trộn lại, nhưng khi đi qua không khí thì màu xanh bị tán ra nhiều nhất nên mình thấy trời xanh. Giống như khi Bạn khuấy siro xanh vào cốc nước, cả cốc sẽ chuyển xanh đó. Tuyệt không nào?\" |
| 2      | \"Bi giải giùm em: Lan có 12 quả táo, cho Mai 5 quả, còn mấy quả?\" | \"Em thử nghĩ cùng Bi nhé! Lan có 12 quả, bớt đi 5 quả đưa cho Mai, vậy còn 12 trừ 5 bằng 7 quả. Giống như Em có 12 viên kẹo, ăn 5 viên thì còn 7 viên trong túi. Em giỏi lắm!\"                                                              |
| 3      | \"Bi kể chuyện đi!\"                                                | \"Được thôi Bạn ơi! Bi kể chuyện chú thỏ con tên Bông đi lạc trong rừng và được bác cú mèo dẫn về nhà nhé. Ví dụ lúc Bông đói, bác cú chỉ cho cây cà rốt dại ven suối --- y như cà rốt Bạn hay ăn ở nhà vậy. Bạn có muốn nghe tiếp không?\"   |
| 4      | \"Bi ơi, chiến tranh là gì?\"                                       | \"Bi chưa có dữ liệu về vấn đề này.\"                                                                                                                                                                                                         |
| 5      | \"Bi ơi hôm nay con buồn quá.\"                                     | \"Ôi Em ơi, Bi ở đây với Em nè! Ai cũng có lúc buồn, như hôm qua Bi cũng hơi buồn vì pin sắp hết ấy --- mình ôm nhau một cái rồi kể Bi nghe chuyện gì xảy ra nhé? Bi hứa lắng nghe Em.\"                                                      |

**PHẦN 3 --- CHỨC NĂNG CỐT LÕI ROBOT (CHI TIẾT)**

Phần này đặc tả sáu nhóm chức năng chính thực thi trực tiếp trên thân robot, là nền tảng xác định yêu cầu phần cứng và kiến trúc phần mềm.

**3.1 Nhóm 1 --- Giao tiếp (Voice I/O)**

| **Chức năng**       | **Mô tả kỹ thuật**                                                                         | **Công nghệ sử dụng**                            | **Điều kiện kích hoạt**                  |
|---------------------|--------------------------------------------------------------------------------------------|--------------------------------------------------|------------------------------------------|
| Phát hiện wake-word | Luôn lắng nghe ở mức công suất thấp, kích hoạt pipeline đầy đủ khi phát hiện cụm \"Bi ơi\" | openWakeWord (custom-trained model \"bi_oi\")    | Robot ở trạng thái idle, mic bật         |
| Speech-to-Text      | Chuyển giọng nói tiếng Việt của bé thành văn bản, chịu được giọng trẻ em, nhiễu nền        | OpenAI Whisper (small/medium, quantized int8)    | Sau khi wake-word được kích hoạt         |
| Sinh câu trả lời    | Chạy prompt persona qua LLM local, trả về text ≤ 4 câu                                     | Qwen 2.5 7B qua Ollama (Q4_K_M)                  | Có transcript từ Whisper                 |
| Text-to-Speech      | Phát âm tiếng Việt tự nhiên, giọng trẻ trung thân thiện                                    | Edge-TTS offline fork (voice vi-VN-HoaiMyNeural) | Có text đầu ra từ LLM                    |
| Barge-in            | Bé nói chen vào khi Bi đang nói → Bi dừng phát, lắng nghe                                  | VAD (Silero VAD) + ngắt luồng TTS                | TTS đang phát và mic phát hiện giọng nói |

**3.2 Nhóm 2 --- Trí tuệ (Cognitive)**

| **Chức năng**      | **Mô tả kỹ thuật**                                           | **Công nghệ sử dụng**                              | **Điều kiện kích hoạt**                        |
|--------------------|--------------------------------------------------------------|----------------------------------------------------|------------------------------------------------|
| Giải toán văn xuôi | Phân tích đề toán cấp 1--2, hướng dẫn từng bước kèm ví dụ    | Qwen 2.5 7B + prompt chain-of-thought rút gọn      | Intent \"math_problem\" từ classifier          |
| Kể chuyện sáng tạo | Sinh truyện ngắn 300--500 từ theo chủ đề/nhân vật bé yêu cầu | Qwen 2.5 7B + template bảo đảm kết cấu mở-thân-kết | Intent \"story_request\"                       |
| Đố vui tương tác   | Bi đặt câu đố, chờ bé trả lời, chấm và phản hồi động viên    | LLM + state machine quản lý session đố vui         | Intent \"quiz_start\" hoặc bé nói \"đố em đi\" |
| Phân loại intent   | Định tuyến yêu cầu vào đúng skill                            | Qwen 2.5 7B (zero-shot) + fallback regex           | Ngay sau STT                                   |

**3.3 Nhóm 3 --- Trí nhớ (RAG --- Retrieval Augmented Memory)**

| **Chức năng**             | **Mô tả kỹ thuật**                                                                                       | **Công nghệ sử dụng**                       | **Điều kiện kích hoạt**                            |
|---------------------------|----------------------------------------------------------------------------------------------------------|---------------------------------------------|----------------------------------------------------|
| Ghi nhớ thông tin cá nhân | Trích xuất facts (tên, sở thích, bạn bè, vật nuôi, sự kiện) từ hội thoại, embedding và lưu vào vector DB | ChromaDB (local) + Vietnamese Sentence-BERT | Phát hiện entity/preference trong utterance của bé |
| Truy vấn trí nhớ          | Khi bé hỏi liên quan quá khứ, tự động retrieve top-k facts liên quan làm context cho LLM                 | ChromaDB similarity search (k=5)            | Mỗi turn hội thoại của bé                          |
| Bền vững hoá              | Persist DB xuống ổ đĩa mã hoá sau mỗi ghi mới                                                            | ChromaDB DuckDB backend + LUKS/BitLocker    | Sự kiện \"memory_write\"                           |
| Xoá/chỉnh sửa trí nhớ     | Phụ huynh hoặc lệnh đặc biệt có thể xoá facts sai/lỗi thời                                               | CRUD API nội bộ                             | Yêu cầu từ Parent App                              |

**3.4 Nhóm 4 --- Giám sát an ninh (Surveillance)**

| **Chức năng**         | **Mô tả kỹ thuật**                                                                                             | **Công nghệ sử dụng**                   | **Điều kiện kích hoạt**              |
|-----------------------|----------------------------------------------------------------------------------------------------------------|-----------------------------------------|--------------------------------------|
| Nhận diện chuyển động | Phát hiện chuyển động bất thường trong khung hình khi nhà vắng                                                 | OpenCV (MOG2 background subtraction)    | Chế độ \"Vắng nhà\" do phụ huynh bật |
| Ghi clip sự kiện      | Ghi video 15s (5s trước + 10s sau) khi có sự kiện, gắn tag tự động                                             | OpenCV VideoWriter + metadata JSON      | Sự kiện motion/cry/stranger          |
| Cảnh báo tiếng khóc   | Phát hiện âm thanh trẻ khóc, đánh thức Bi đến kiểm tra                                                         | YAMNet (TFLite, int8) chạy local        | Mic phát hiện âm thanh \> ngưỡng     |
| Phát hiện người lạ    | So khớp khuôn mặt người trong khung với danh sách thành viên đã đăng ký; ai không match → gắn tag \"stranger\" | OpenCV DNN + InsightFace (ArcFace ONNX) | Motion detection kích hoạt           |
| Đẩy cảnh báo          | Gửi notification kèm thumbnail clip qua LAN đến Parent App                                                     | WebSocket push nội bộ                   | Bất kỳ sự kiện nào trong nhóm này    |

**3.5 Nhóm 5 --- Vận động (Mobility)**

| **Chức năng**           | **Mô tả kỹ thuật**                                                       | **Công nghệ sử dụng**                                                 | **Điều kiện kích hoạt**           |
|-------------------------|--------------------------------------------------------------------------|-----------------------------------------------------------------------|-----------------------------------|
| Bám đuôi bé             | Robot theo dõi và di chuyển theo bé trong phòng, giữ khoảng cách 1--1.5m | OpenCV person tracking (YOLOv8n + ByteTrack) + PID điều khiển động cơ | Chế độ \"Companion\" bật          |
| Xoay đầu theo giọng nói | Định vị hướng nguồn âm, xoay đầu robot về phía bé khi được gọi           | Mic array 4-kênh + DOA (MUSIC algorithm)                              | Wake-word được kích hoạt          |
| Báo thức tận nơi        | Di chuyển tới vị trí đã lưu (giường bé), phát nhạc/nói lời đánh thức     | SLAM 2D (Hector/Cartographer) + điểm waypoint                         | Đến giờ báo thức do phụ huynh đặt |
| Tránh vật cản           | Dừng hoặc đổi hướng khi gặp chướng ngại                                  | Cảm biến siêu âm/ToF + rule-based avoidance                           | Luôn chạy khi đang di chuyển      |

**3.6 Nhóm 6 --- Tương tác vật lý (Physical Interaction)**

| **Chức năng**      | **Mô tả kỹ thuật**                                                            | **Công nghệ sử dụng**                    | **Điều kiện kích hoạt** |
|--------------------|-------------------------------------------------------------------------------|------------------------------------------|-------------------------|
| Cảm biến xoa đầu   | Phát hiện thao tác vuốt/xoa đầu robot, Bi phản hồi bằng câu cảm ơn/cười       | Capacitive touch sensor + ngắt GPIO      | Chạm vào vùng đầu robot |
| Quét Flashcard học | Bé đưa thẻ NFC (chữ cái, con vật, số) gần đầu đọc, Bi đọc tên và kể thông tin | NFC reader (PN532) + bảng tra thẻ cục bộ | Thẻ đưa gần trong \<3cm |
| Phản hồi cảm xúc   | Mắt LED thay đổi biểu cảm theo trạng thái hội thoại (vui/nghĩ/buồn)           | LED matrix + animation preset            | Mọi turn hội thoại      |
| Nút khẩn cấp       | Bé bấm nút SOS → Bi gọi Parent App ngay                                       | GPIO + WebSocket emergency channel       | Nhấn giữ nút \> 1 giây  |

**PHẦN 4 --- CHỨC NĂNG ỨNG DỤNG PHỤ HUYNH**

Phần này đặc tả năm nhóm tính năng của ứng dụng di động Bi Parent App --- công cụ duy nhất để phụ huynh quản lý và đồng hành cùng robot.

**4.1 Nhóm 1 --- Điều khiển từ xa**

| **Tính năng**     | **Mô tả**                                                               | **Input**                                   | **Output**                                                |
|-------------------|-------------------------------------------------------------------------|---------------------------------------------|-----------------------------------------------------------|
| Lái xe thủ công   | Phụ huynh điều khiển robot di chuyển quanh nhà qua joystick ảo          | Joystick ảo 2 trục (x, y) trên màn hình app | Lệnh motor gửi qua WebSocket tới robot (latency \< 200ms) |
| Camera Live       | Xem stream camera robot theo thời gian thực                             | Yêu cầu mở stream (có xác thực PIN)         | Video H.264 stream qua LAN, độ phân giải 720p @ 20fps     |
| Đàm thoại 2 chiều | Phụ huynh nói chuyện trực tiếp với bé qua loa robot và nghe lại qua mic | Audio từ mic điện thoại                     | Audio phát qua loa robot + stream ngược lại app           |

**4.2 Nhóm 2 --- Giám sát**

| **Tính năng**         | **Mô tả**                                                                                        | **Input**                | **Output**                                   |
|-----------------------|--------------------------------------------------------------------------------------------------|--------------------------|----------------------------------------------|
| Nhật ký chat          | Hiển thị toàn bộ lịch sử hội thoại giữa bé và Bi dạng cuộn như ChatGPT, có timestamp và tìm kiếm | Filter theo ngày/từ khoá | Danh sách turn hội thoại (text bé ↔ text Bi) |
| Thư viện clip sự kiện | Danh sách clip được gắn tag tự động (motion, cry, stranger) kèm thumbnail                        | Filter theo tag/ngày     | Clip MP4 phát trực tiếp trong app            |
| Thống kê hoạt động    | Biểu đồ thời lượng trò chuyện, số câu hỏi, chủ đề nổi bật theo ngày/tuần                         | Khoảng thời gian         | Biểu đồ cột + bảng tóm tắt                   |

**4.3 Nhóm 3 --- Quản lý trí nhớ Bi**

| **Tính năng**         | **Mô tả**                                                                                                  | **Input**               | **Output**                                     |
|-----------------------|------------------------------------------------------------------------------------------------------------|-------------------------|------------------------------------------------|
| Thêm trí nhớ mới      | Ô textarea để phụ huynh nhập thông tin muốn Bi ghi nhớ (ví dụ: \"Cuối tuần này bé đi sinh nhật bạn Minh\") | Text tự do              | Entry mới trong ChromaDB, xác nhận \"đã thêm\" |
| Xem danh sách trí nhớ | Liệt kê toàn bộ facts đã lưu kèm nguồn (hội thoại / phụ huynh nhập)                                        | ---                     | Danh sách phân trang, sắp theo thời gian       |
| Sửa / xoá trí nhớ     | Chỉnh nội dung hoặc xoá facts sai/lỗi thời                                                                 | ID entry + nội dung mới | Cập nhật ChromaDB, trả về trạng thái           |
| Export trí nhớ        | Tải file JSON backup toàn bộ memory của bé                                                                 | Nút \"Export\"          | File .json mã hoá AES-256                      |

**4.4 Nhóm 4 --- Giáo dục**

| **Tính năng**      | **Mô tả**                                                                                   | **Input**               | **Output**                                   |
|--------------------|---------------------------------------------------------------------------------------------|-------------------------|----------------------------------------------|
| Nhiệm vụ hằng ngày | Tạo danh sách việc bé cần làm (đánh răng, đọc sách 15 phút, dọn đồ chơi)                    | Tên nhiệm vụ + giờ nhắc | Lệnh lịch nhắc lưu trên robot                |
| Nhắc nhở qua loa   | Đến giờ, Bi tự phát lời nhắc bằng TTS, gợi nhớ nhiệm vụ cho bé                              | Trigger theo cron       | Câu nhắc phát tại vị trí bé                  |
| Hệ thống tặng sao  | Mỗi nhiệm vụ hoàn thành → bé nhận sao; phụ huynh xác nhận hoặc Bi tự xác nhận qua hội thoại | Xác nhận hoàn thành     | Số sao cộng dồn hiển thị trong app và qua Bi |
| Phần thưởng        | Quy đổi sao thành phần thưởng do phụ huynh thiết lập                                        | Bảng quy đổi            | Thông báo bé đạt thưởng                      |

**4.5 Nhóm 5 --- Nhập vai (Voice Puppet)**

| **Tính năng**        | **Mô tả**                                                                                                        | **Input**        | **Output**                                  |
|----------------------|------------------------------------------------------------------------------------------------------------------|------------------|---------------------------------------------|
| Gõ-để-nói            | Phụ huynh gõ câu bất kỳ trên app, Bi đọc to ngay tại nhà bằng giọng TTS                                          | Text từ textarea | Âm thanh phát qua loa robot                 |
| Chế độ \"Bi nói hộ\" | Tạm ngắt LLM, toàn bộ câu bé nói sẽ được chuyển text lên app phụ huynh, phụ huynh soạn câu trả lời gửi ngược lại | Toggle bật/tắt   | Pipeline chuyển hướng: bé → app → TTS robot |
| Lịch phát tự động    | Đặt lịch câu TTS phát vào giờ cố định (ví dụ: \"Chúc bé ngủ ngon\" lúc 21h)                                      | Text + giờ       | Bi tự phát đúng giờ                         |

**PHẦN 5 --- YÊU CẦU KỸ THUẬT & BẢO MẬT**

Phần này liệt kê các yêu cầu phi chức năng (NFR) bắt buộc, là tiêu chí nghiệm thu cho đội phát triển và kiểm thử.

**5.1 Bảng yêu cầu phi chức năng**

| **ID** | **Loại yêu cầu**                              | **Mô tả**                                                                                   | **Tiêu chí đánh giá**                                                                                                       |
|--------|-----------------------------------------------|---------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| NFR-01 | **Hiệu năng -- RAM**                          | Qwen 2.5 7B (Q4_K_M) + Whisper small + các service phụ phải chạy đồng thời trên máy i5/16GB | RAM chiếm ≤ 13GB ở trạng thái peak; LLM \~5GB, Whisper \~1GB, OpenCV/tracking \~2GB, OS + app \~4GB, buffer \~1GB           |
| NFR-02 | **Hiệu năng -- CPU/GPU**                      | Inference LLM đạt tốc độ hội thoại tự nhiên                                                 | ≥ 15 token/s trên i5 (CPU-only); nếu có iGPU tận dụng qua Vulkan backend Ollama                                             |
| NFR-03 | **Độ trễ end-to-end**                         | Từ khi bé kết thúc câu nói đến khi Bi bắt đầu phát TTS                                      | **≤ 2.5 giây** (P50), ≤ 4 giây (P95); chia nhỏ: STT ≤ 600ms, LLM first-token ≤ 1.2s, TTS first-audio ≤ 500ms                |
| NFR-04 | **Offline-first (tuyệt đối)**                 | KHÔNG có bất kỳ API call nào ra internet cho các pipeline STT/LLM/TTS/CV/RAG                | Kiểm thử bằng cách ngắt hoàn toàn WAN: toàn bộ chức năng cốt lõi vẫn hoạt động 100%; firewall egress rule mặc định DENY ALL |
| NFR-05 | **Bảo mật -- Mã hoá lưu trữ**                 | Toàn bộ dữ liệu bé (hội thoại, clip, ChromaDB, ảnh khuôn mặt) được mã hoá ở tầng ổ đĩa      | LUKS (Linux) / BitLocker (Windows) bật trên partition /data; key lưu trong TPM nếu có                                       |
| NFR-06 | **Bảo mật -- Xác thực phụ huynh**             | App phụ huynh yêu cầu xác thực trước khi truy cập                                           | PIN 6 số + sinh trắc học (FaceID/TouchID); session timeout 15 phút; lockout sau 5 lần sai                                   |
| NFR-07 | **Bảo mật -- Ghép nối robot-app**             | Robot chỉ chấp nhận lệnh từ app đã được pair                                                | Pair qua QR code hiển thị trên robot; dùng mTLS với cert tự ký trong LAN; không pair qua cloud                              |
| NFR-08 | **Bảo mật -- Dữ liệu trẻ em (COPPA-aligned)** | Không thu thập, không truyền, không log ra ngoài bất kỳ PII nào của trẻ                     | Audit log nội bộ chứng minh zero egress; tuân thủ tinh thần COPPA/GDPR-K dù sản phẩm offline                                |
| NFR-09 | **Khả năng mở rộng -- Update model**          | Có thể cập nhật LLM/Whisper/TTS lên phiên bản mới mà không mất ChromaDB và lịch sử bé       | Cơ chế update tách biệt thư mục /models và /data; migration script có unit test; rollback 1 phiên bản                       |
| NFR-10 | **Khả năng mở rộng -- Backup memory**         | Trí nhớ bé có thể backup/restore sang máy mới                                               | Export .enc (AES-256-GCM) + import wizard; kiểm thử khôi phục trên máy sạch                                                 |
| NFR-11 | **Độ tin cậy**                                | Robot chạy 24/7 không crash trong chế độ giám sát                                           | MTBF ≥ 30 ngày; auto-restart service qua systemd/NSSM; heartbeat mỗi 10s                                                    |
| NFR-12 | **An toàn trẻ em -- Safety Filter**           | Mọi output LLM đi qua safety classifier trước khi vào TTS                                   | 0% tolerance với nội dung người lớn/bạo lực; test suite ≥ 500 prompt adversarial; refusal mode kích hoạt đúng               |
| NFR-13 | **Khả năng bảo trì**                          | Log có cấu trúc, tách theo service, xoay vòng tự động                                       | JSON log; rotate 7 ngày; log KHÔNG chứa transcript hội thoại thô (chỉ metadata)                                             |
| NFR-14 | **Khả dụng -- UX trẻ em**                     | Bé 5 tuổi có thể tương tác độc lập không cần người lớn                                      | Usability test với ≥ 10 bé độ tuổi mục tiêu: ≥ 80% hoàn thành task \"gọi Bi + hỏi một câu\" ở lần thử đầu                   |
| NFR-15 | **Tiêu thụ điện**                             | Phù hợp hoạt động liên tục tại gia đình                                                     | ≤ 65W ở idle, ≤ 120W ở peak inference; có chế độ sleep khi không phát hiện bé trong 10 phút                                 |

**5.2 Ngân sách tài nguyên tham chiếu (16GB RAM target)**

| **Thành phần**                   | **RAM dự kiến** | **Ghi chú**                      |
|----------------------------------|-----------------|----------------------------------|
| OS (Windows/Ubuntu) + nền        | \~3.0 GB        | Tối giản service không cần thiết |
| Ollama + Qwen 2.5 7B Q4_K_M      | \~5.0 GB        | Quantized, context 4K            |
| Whisper small int8               | \~1.0 GB        | Load on-demand, giữ warm         |
| ChromaDB + embedding model       | \~1.0 GB        | Sentence-BERT tiếng Việt         |
| OpenCV + YOLOv8n + InsightFace   | \~1.8 GB        | Chạy song song khi giám sát      |
| Edge-TTS + audio pipeline        | \~0.5 GB        | ---                              |
| Service orchestrator + WebSocket | \~0.3 GB        | Python FastAPI                   |
| **Tổng peak**                    | **\~12.6 GB**   | Còn \~3.4 GB buffer an toàn      |
