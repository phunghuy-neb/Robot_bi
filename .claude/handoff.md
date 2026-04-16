# 📋 Handoff — Robot Bi

> Snapshot rút gọn theo phương pháp Single Source of Truth.
> Lịch sử cũ đã chuyển sang thư mục `changelog/`.

## TRẠNG THÁI HIỆN TẠI
- Dự án đang chạy theo mô hình `PROJECT.md` là nguồn chuẩn duy nhất.
- `CLAUDE.md` và `AGENTS.md` được sinh tự động từ `python sync.py`.
- Entry point chính vẫn là `src_brain/main_loop.py`.
- LLM vẫn đi qua `stream_chat(messages)` trong `src_brain/ai_core/core_ai.py`.
- Backend AI hiện tại: Groq primary, Gemini fallback.
- STT vẫn là `faster-whisper` với auto-detect GPU/CPU.
- TTS vẫn là `edge-tts` với fallback `pyttsx3`.
- SafetyFilter vẫn phải chạy sau LLM và trước mọi đường TTS.
- Parent App vẫn phục vụ qua HTTPS `8443` với Cloudflare Tunnel tùy chọn.
- Hệ thống audio streaming, mom-talk path và camera low-latency đều đang ở trạng thái protected.
- `start_robot.bat` đã được chỉnh để chạy `python sync.py` trước khi khởi động robot.
- Lịch sử session dài không còn nằm trong file này; xem thư mục `changelog/`.
- `CLAUDE.md` và `AGENTS.md` không còn là nơi ghi quy tắc thủ công.
- Tài liệu vận hành giờ tách thành 2 tầng: snapshot ngắn trong file này, lịch sử dài trong `changelog/`.
- Không có thay đổi nào tới logic AI, audio, vision, network hay memory ngoài warning suppression và logging hygiene.
- Các file archive được giữ nguyên mục đích tra cứu, không phải nguồn chuẩn để chỉnh tay.
- `run_tests.py` hiện sạch 3 warning mục tiêu: pygame `pkg_resources`, Hugging Face cache permission và YAMNet fallback warning spam.
- `run_tests.py` hiện cũng đã sạch banner `pygame`, progress/model-load output của `sentence-transformers`, và log headless `no-camera`.
- `EarSTT` hiện tự dò microphone input khả dụng theo mono rồi stereo; nếu không mở được mic sẽ vào silent mode thay vì crash PortAudio.
- `sync.py` hiện đã an toàn với Windows CP1252: ép `stdout` sang UTF-8 và bỏ emoji trong output.
- QR của Parent App hiện render bằng ASCII thuần trong terminal nên đã hiện lại ổn định sau bước sync/khởi động trên Windows console.
- `CryDetector` hiện chỉ log `info` một lần khi không có microphone hợp lệ rồi tự dừng, không còn spam `Error querying device -1`.

## VIỆC CẦN LÀM TIẾP
- Test thực tế end-to-end với mic, loa, camera trên máy Windows thật.
- Xác nhận lại parent audio route trên mobile browser sau các fix volume và `setSinkId`.
- Cân nhắc named Cloudflare Tunnel nếu cần URL cố định cho phụ huynh.
- Giảm độ nhạy energy fallback trong `cry_detector.py` nếu còn báo giả.
- Kiểm tra tải model YAMNet/TFLite trên môi trường chưa có TensorFlow.
- Tiếp tục chỉ sửa `PROJECT.md` khi cập nhật quy tắc hoặc trạng thái chuẩn của dự án.
- Khi có session mới, cập nhật cuối `PROJECT.md`, cập nhật file này, tạo changelog mới rồi chạy `sync.py`.
- Tránh đưa lịch sử dài quay trở lại `handoff.md`.

## BUG ĐANG MỞ
- Wake-word "Bi ơi" vẫn là stub, chưa có model đánh thức thật.
- Cloudflare URL vẫn thay đổi sau mỗi lần restart khi dùng tunnel miễn phí.
- YAMNet TFLite có thể không tải được nếu thiếu TensorFlow.
- Hành vi audio trên mobile browser vẫn cần xác nhận thủ công trên thiết bị thật.
- Các luồng mic/loa/camera phụ thuộc phần cứng nên chưa thể xác nhận hoàn toàn bằng test tự động.
- Chưa ghi nhận bug mở nào mới cho `sync.py` sau khi bỏ emoji output và ép `stdout` sang UTF-8.

##  PROTECTED FIXES
- Audio mom talk: resample 16k -> 44.1k, in-memory WAV, `pygame.Channel(7)`.
- Mom pause logic: `is_mom_talking()` phải giữ nguyên hành vi chặn robot nghe khi mẹ nói.
- Camera delay fix: thread riêng, queue bridge, `CAP_PROP_BUFFERSIZE=1`.
- SafetyFilter: luôn post-LLM và pre-TTS.
- RAG threshold 0.50 và deduplication hiện tại không được phá regression.
- Groq primary `llama-3.3-70b-versatile` + Gemini fallback phải được giữ nguyên.
- `faster-whisper` GPU/CPU auto-detect + large-v2 vẫn là chuẩn STT hiện tại.
- HTTPS self-signed + Cloudflare Tunnel phải tiếp tục hoạt động.
- Audio queue + chunked TTS streaming phải giữ mục tiêu Time-to-First-Audio thấp.
- PIN auth, TaskManager và cơ chế sao thưởng là các khu vực cần tránh chạm nếu không có yêu cầu rõ.
- Nếu sửa vào các vùng protected này thì phải chạy full test và kiểm tra regression thủ công.

## SESSION GẦN NHẤT
- Ngày: 2026-04-16
- Mục tiêu: sửa lại phần hiển thị QR Code để hiển thị đúng dạng mã QR thật (hình vuông đen/trắng) dễ quét cho Parent App.
- Đã đọc `PROJECT.md`, `handoff.md` và file đích trước khi chỉnh sửa.
- Đã cập nhật `_build_ascii_qr` trong `src_brain/network/api_server.py` để sử dụng mã màu ANSI background (`\033[47m`, `\033[40m`) hiển thị thành khối vuông đặc đen/trắng thực thụ thay vì ký tự `#` và khoảng trắng.
- Cập nhật này giúp hiển thị thành QR Code chuẩn (chữ đen nền trắng), các thiết bị di động quét thẳng dễ dàng, không gặp lỗi "không nhận diện" hay sai màu.
- Thêm `os.system("")` để thiết lập kích hoạt console Windows/PowerShell hỗ trợ chuỗi ANSI mặc định.
- Đã chạy `python run_tests.py`: kết quả vẫn `54/54 PASS`.
- Các file được chỉnh trong session này: `src_brain/network/api_server.py`, `PROJECT.md`, `.claude/handoff.md`.
- Cần giữ bước `python sync.py` ở cuối để đồng bộ `CLAUDE.md` và `AGENTS.md`.
