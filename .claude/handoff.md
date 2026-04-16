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
- `sync.py` phụ thuộc console encoding khi in emoji; trên Windows CP1252 có thể cần `PYTHONIOENCODING=utf-8`.

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
- Mục tiêu: làm sạch console khi chạy `python run_tests.py` mà không đổi logic protected.
- Đã đọc `PROJECT.md`, `handoff.md` và toàn bộ file đích trước khi chỉnh sửa.
- Đã thêm warning filter cho `pygame` trong `mouth_tts.py`, `api_server.py`, `main_loop.py`.
- Đã cấu hình Hugging Face env/cache trong `rag_manager.py` và `ear_stt.py`.
- `RAGManager` hiện ưu tiên snapshot embedding local sẵn có để tránh warning cache/network khi test.
- Đã đổi thông báo thiếu YAMNet trong `cry_detector.py` sang 1 dòng info sạch và chỉ in một lần.
- Đã ẩn `PYGAME_HIDE_SUPPORT_PROMPT` trước các import `pygame` liên quan.
- Đã redirect stdout/stderr khi load `SentenceTransformer` để bỏ progress bar và load report khỏi console.
- Đã chuyển log no-camera headless trong `eye_vision.py` xuống `DEBUG`.
- Đã suppress output test headless của `EyeVision`, `CryDetector` và `EventNotifier` trong `run_tests.py`.
- Đã chạy `python run_tests.py`: kết quả vẫn `54/54 PASS`.
- Console test hiện chỉ còn output quan trọng: tiêu đề nhóm test, `PASS`, và kết quả tổng.
- Các file được chỉnh trong session này: `PROJECT.md`, `.claude/handoff.md`, `run_tests.py`, `src_brain/senses/mouth_tts.py`, `src_brain/network/api_server.py`, `src_brain/main_loop.py`, `src_brain/memory_rag/rag_manager.py`, `src_brain/senses/ear_stt.py`, `src_brain/senses/cry_detector.py`, `src_brain/senses/eye_vision.py`.
- Cần chạy `python sync.py` sau khi cập nhật tài liệu để đồng bộ file auto-generated.
