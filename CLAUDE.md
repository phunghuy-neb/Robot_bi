# CLAUDE.md — Robot Bi (Gia sư AI Offline)
> Cập nhật: 2026-04-13 | Dựa trên codebase thực tế (Sprint 2 hoàn thành)

## Mission
Robot gia sư thông minh cho trẻ em (Bo). Chạy 100% Offline trên PC/Laptop i5, 16GB RAM.
Tài liệu đầy đủ: @docs/SRS_Robot_Bi.md | Lộ trình: @docs/kehoach.md

---

## Stack cố định — KHÔNG thay đổi nếu không có lệnh rõ ràng

| Layer | Thư viện | Ghi chú |
|---|---|---|
| LLM | `ollama` → model `qwen2.5:7b` | BẮT BUỘC stream=True khi refactor |
| STT | `speech_recognition` (Google STT) | File: `ear_stt.py` — đây là chuẩn hiện tại |
| TTS | `edge-tts` + `pygame` | File: `mouth_tts.py` — giọng vi-VN-HoaiMyNeural |
| RAG | `chromadb` + `sentence-transformers` | File: `rag_manager.py` — model: paraphrase-multilingual-MiniLM-L12-v2 |
| Vision | `opencv-python` | Chưa implement — Sprint 3 |
| Language | Python 3.10+ | |

---

## Kiến trúc file — ĐỌC TRƯỚC KHI CHẠM VÀO BẤT KỲ FILE NÀO

```
Robot_Bi_Project/
├── CLAUDE.md                          ← File này
├── requirements.txt                   ← Cần sync với stack thực tế
├── .claudeignore                      ← Bỏ qua: __pycache__, .venv, *.mp3
├── .gitignore
├── docs/
│   ├── SRS_Robot_Bi.md                ← Đặc tả đầy đủ
│   └── kehoach.md                     ← Lộ trình 7 giai đoạn
├── .claude/
│   └── handoff.md                     ← ĐỌC ĐẦU MỖI SESSION, GHI KHI KẾT THÚC
└── src_brain/
    ├── main_loop.py                   ← ENTRY POINT CHÍNH (dùng cái này)
    ├── main.py                        ← CŨ/LEGACY — không dùng nữa
    ├── ai_core/
    │   ├── core_ai.py                 ← Class BiAI, hàm: chat(text) → str
    │   └── prompts.py                 ← Rỗng, chưa dùng
    ├── senses/
    │   ├── ear_stt.py                 ← Class EarSTT, hàm: listen() → str
    │   ├── mouth_tts.py               ← Class MouthTTS, hàm: speak(text)
    │   ├── voice_io.py                ← LEGACY (faster-whisper + gTTS) — không dùng
    │   └── eye_vision.py              ← Rỗng, Sprint 3
    └── memory_rag/
        ├── bi_memory.json             ← Log hội thoại thô
        ├── rag_manager.py             ← Class RAGManager, 6 methods: extract_and_save, retrieve, list_memories, delete_memory, get_stats
        └── chroma_db/                 ← ChromaDB persistent storage (tự tạo khi chạy)
```

---

## Vấn đề đã biết — xử lý trước khi làm việc khác

| # | Vấn đề | File | Mức độ |
|---|---|---|---|
| 1 | ~~`core_ai.py` dùng `ollama.chat()` blocking~~ | ~~`core_ai.py`~~ | ✅ Đã fix Sprint 1 |
| 2 | ~~`requirements.txt` liệt kê `gTTS` + `faster-whisper`~~ | ~~`requirements.txt`~~ | ✅ Đã fix Sprint 1 |
| 3 | `main.py` + `voice_io.py` là legacy, dùng stack khác — dễ gây nhầm lẫn | `main.py`, `voice_io.py` | Trung bình |
| 4 | `ear_stt.py` dùng Google STT (cần internet) — vi phạm offline constraint | `ear_stt.py` | Trung bình |
| 5 | `edge-tts` cần internet để generate — tạm thời chấp nhận | `mouth_tts.py` | Thấp |

---

## Quy tắc BẮT BUỘC

1. Đọc `.claude/handoff.md` TRƯỚC KHI viết bất kỳ dòng code nào trong session mới
2. Đọc file đích TRƯỚC KHI sửa — KHÔNG bịa tên class/hàm
3. Entry point chính là `src_brain/main_loop.py` — KHÔNG dùng `main.py`
4. Stack chuẩn: `ear_stt.py` + `mouth_tts.py` + `core_ai.py` — KHÔNG dùng `voice_io.py`
5. Time-to-First-Audio PHẢI < 2 giây — luôn dùng kiến trúc streaming + audio queue
6. KHÔNG gọi API ngoài cho hình ảnh/âm thanh/dữ liệu cá nhân (edge-tts tạm thời chấp nhận)
7. KHÔNG thêm thư viện mới nếu không có trong bảng Stack ở trên
8. Ghi kết quả vào `.claude/handoff.md` khi kết thúc session

---

## Lệnh hay dùng

```bash
# Kiểm tra Ollama đang chạy
ollama list
ollama serve   # nếu chưa chạy

# Chạy hệ thống chính
python -m src_brain.main_loop

# Test từng module độc lập
python src_brain/senses/ear_stt.py
python src_brain/senses/mouth_tts.py
python src_brain/ai_core/core_ai.py

# Chat text (không cần mic/loa)
python src_brain/train_text.py

# Cài dependencies đúng
pip install ollama edge-tts pygame speechrecognition chromadb sentence-transformers

# Test RAG độc lập
python src_brain/memory_rag/rag_manager.py
```

---

## Trạng thái Sprint

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| Sprint 1 | STT + TTS + LLM + main_loop | ✅ Hoàn thành (cần fix lỗi ở bảng trên) |
| Sprint 2 | ChromaDB RAG | ✅ Hoàn thành |
| Sprint 3 | OpenCV Camera | ⏳ Chưa bắt đầu |
| Sprint 4 | ESP32 / Cơ khí | 🚫 Chưa có phần cứng — BỎ QUA |
| Sprint 5 | App phụ huynh | ⏳ Chưa bắt đầu |
| Sprint 6 | Tối ưu & đóng gói | ⏳ Chưa bắt đầu |

**Việc tiếp theo (Sprint 3):** Implement `eye_vision.py` với OpenCV — xem @docs/SRS_Robot_Bi.md Phần 3.4 (Nhóm 4 — Giám sát an ninh)

---

## Phần cứng hiện tại

Chỉ có PC/Laptop. KHÔNG có robot vật lý.
Bỏ qua hoàn toàn mọi task liên quan đến: GPIO, ESP32, servo, L298N, NFC reader, LED matrix, cảm biến siêu âm, SLAM.