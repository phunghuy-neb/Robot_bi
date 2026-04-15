# CLAUDE.md — Robot Bi (Gia sư AI cho trẻ em)
> Cập nhật: 2026-04-15 | Session N hoàn thành | 54+ automated tests PASS

## Mission
Robot gia sư thông minh cho trẻ em 5-12 tuổi. Chạy trên PC/Laptop Windows.
AI backend: Groq (primary) + Gemini (fallback) — không cần Ollama.
Tài liệu đầy đủ: @docs/SRS_Robot_Bi.md | Lộ trình: @docs/kehoach.md

---

## Stack hiện tại — KHÔNG thay đổi nếu không có lệnh rõ ràng

| Layer | Thư viện | Ghi chú |
|---|---|---|
| LLM Primary | Groq API — `llama-3.3-70b-versatile` | ~400 token/giây, 14.400 req/ngày free |
| LLM Fallback | Gemini API — `gemini-2.5-flash-lite` | 1.000 req/ngày free, tự động xoay vòng |
| STT | `faster-whisper` | GPU: large-v2 float16 / CPU: small int8 (auto-detect) |
| TTS | `edge-tts` + `pygame` | giọng vi-VN-HoaiMyNeural |
| TTS Fallback | `pyttsx3` | offline fallback khi edge-tts mất internet |
| Safety | regex blacklist + pattern matching | `safety_filter.py` — post-LLM, pre-TTS (NFR-12) |
| RAG | `chromadb` + `sentence-transformers` | model: paraphrase-multilingual-MiniLM-L12-v2 |
| Vision | `opencv-python` (CAP_DSHOW) | `eye_vision.py` — LBPH face + MOG2 motion |
| Cry Detection | YAMNet TFLite + energy fallback | `cry_detector.py` |
| Network | `fastapi` + `uvicorn` + `websockets` | HTTPS port 8443 (self-signed SSL) |
| Tunnel | `cloudflared` | URL public https://xxx.trycloudflare.com |
| Config | `.env` + `config.json` | API keys + robot settings |
| Language | Python 3.10+ | |

---

## Kiến trúc file

```
Robot_Bi_Project/
├── CLAUDE.md                          ← File này
├── requirements.txt                   ← Sync với stack thực tế
├── config.json                        ← Cấu hình robot (model, limits...)
├── .env                               ← API keys — KHÔNG commit lên git
├── generate_ssl.py                    ← Tạo SSL certificate (chạy 1 lần)
├── ssl/                               ← cert.pem + key.pem (tự tạo)
├── run_tests.py                       ← 54+ automated tests
├── start_robot.bat                    ← Auto-restart + tạo SSL tự động
├── stress_test.py                     ← RAM/latency benchmark
├── HUONG_DAN_CHAY.md                  ← Hướng dẫn sử dụng
├── .gitignore                         ← Bao gồm .env, ssl/, __pycache__
├── docs/
│   ├── SRS_Robot_Bi.md
│   └── kehoach.md
├── .claude/
│   └── handoff.md                     ← ĐỌC ĐẦU MỖI SESSION, GHI KHI KẾT THÚC
└── src_brain/
    ├── main_loop.py                   ← ENTRY POINT CHÍNH
    ├── train_text.py                  ← Chat text (không cần mic/loa)
    ├── ai_core/
    │   ├── core_ai.py                 ← stream_chat(messages) → generator
    │   │                                 Groq primary → Gemini fallback
    │   │                                 BiAI stub (backward compat)
    │   ├── safety_filter.py           ← SafetyFilter.check(text) → (bool, str)
    │   └── prompts.py                 ← SYSTEM_PROMPT, REFUSAL_RESPONSE, GREETING
    ├── senses/
    │   ├── ear_stt.py                 ← EarSTT.listen() → str
    │   │                                 Auto-detect GPU/CPU Whisper
    │   ├── mouth_tts.py               ← MouthTTS.speak(text) + pyttsx3 fallback
    │   ├── eye_vision.py              ← EyeVision — CAP_DSHOW, rate-limited logs
    │   ├── cry_detector.py            ← CryDetector — YAMNet + energy fallback
    │   └── models/                    ← yamnet.tflite
    ├── network/
    │   ├── __init__.py
    │   ├── api_server.py              ← FastAPI HTTPS:8443
    │   │                                 MJPEG camera + audio WebSocket
    │   │                                 Mom direct talk endpoints
    │   │                                 Cloudflare Tunnel auto-start
    │   ├── notifier.py                ← EventNotifier + WebSocket
    │   ├── task_manager.py            ← TaskManager + sao thưởng
    │   └── static/
    │       ├── index.html             ← Parent App PWA
    │       │                             Tab: Trạng thái/Chat/Sự kiện/Trí nhớ/Nhiệm vụ/Nhập vai
    │       │                             Camera live + auto-audio khi bật cam
    │       │                             Nút mic mẹ nói trực tiếp với bé
    │       ├── manifest.json          ← PWA manifest
    │       ├── sw.js                  ← Service Worker
    │       └── icon-192/512.png
    └── memory_rag/
        ├── rag_manager.py             ← RAGManager — 10 methods
        ├── bi_memory.json
        └── chroma_db/
```

---

## Vấn đề đã biết

| # | Vấn đề | File | Mức độ |
|---|---|---|---|
| 1 | Wake-word "Bi ơi" chưa có model thật (chỉ stub) | `ear_stt.py` | Thấp — chờ phần cứng |
| 2 | Cry detector energy fallback nhạy — báo nhầm | `cry_detector.py` | Thấp |
| 3 | URL Cloudflare thay đổi mỗi lần restart | `api_server.py` | Thấp — cần named tunnel |
| 4 | iOS Safari cần HTTPS để dùng mic mẹ | `index.html` | Đã có HTTPS fix |
| 5 | Tiếng từ robot phát qua earpiece thay loa ngoài trên mobile | `index.html` | Đang fix |
| 6 | YAMNet TFLite chưa load được (thiếu tensorflow) | `cry_detector.py` | Thấp — dùng fallback |

---

## Quy tắc BẮT BUỘC

1. Đọc `.claude/handoff.md` TRƯỚC KHI viết bất kỳ dòng code nào
2. Đọc file đích TRƯỚC KHI sửa — KHÔNG bịa tên class/hàm
3. Entry point chính là `src_brain/main_loop.py`
4. LLM backend: `stream_chat(messages)` từ `core_ai.py` — KHÔNG dùng ollama
5. STT: `ear_stt.py` với faster-whisper auto GPU/CPU — KHÔNG dùng Google STT
6. Time-to-First-Audio PHẢI < 2 giây — luôn dùng streaming + audio queue
7. SafetyFilter PHẢI chạy TRƯỚC khi text đưa vào TTS
8. API keys PHẢI lấy từ `.env` — KHÔNG hardcode trong code
9. KHÔNG commit `.env` hoặc `ssl/` lên git
10. Ghi kết quả vào `.claude/handoff.md` khi kết thúc session

---

## Lệnh hay dùng

```bash
# Lần đầu — tạo SSL certificate
python generate_ssl.py

# Chạy robot (khuyến nghị — có auto-restart)
start_robot.bat

# Hoặc chạy trực tiếp
python -m src_brain.main_loop

# Chat text không cần mic/loa
python src_brain/train_text.py

# Chạy toàn bộ automated tests
python run_tests.py

# Test RAM/latency
python stress_test.py

# Test từng module
python src_brain/senses/ear_stt.py
python src_brain/senses/mouth_tts.py
python src_brain/ai_core/core_ai.py
python src_brain/memory_rag/rag_manager.py

# Cài/cập nhật dependencies
pip install requests python-dotenv faster-whisper edge-tts pygame \
    sounddevice numpy chromadb sentence-transformers pyttsx3 \
    opencv-python fastapi uvicorn websockets qrcode cryptography \
    --break-system-packages

# Xóa ký ức cũ của robot
python -c "
from src_brain.memory_rag.rag_manager import RAGManager
RAGManager().clear_all_memories()
print('Đã xóa toàn bộ ký ức')
"
```

---

## Kết nối Parent App

| Tình huống | URL | Ghi chú |
|---|---|---|
| Cùng WiFi | `https://192.168.1.22:8443` | Lần đầu bấm Advanced → Proceed |
| Khác WiFi / từ xa | `https://xxx.trycloudflare.com` | Xem URL in ra terminal khi khởi động |
| Localhost | `https://localhost:8443` | Trên máy chạy robot |

---

## Config robot (`config.json`)

```json
{
  "robot_name": "Bi",
  "child_name": "",
  "language_mode": "auto",
  "english_practice_mode": false,
  "max_history_turns": 10,
  "primary_api": "groq",
  "groq_model": "llama-3.3-70b-versatile",
  "gemini_model": "gemini-2.5-flash-lite-preview-06-17",
  "groq_cooldown_seconds": 60,
  "daily_limit_warning": 13000
}
```

Mỗi robot gia đình khác → tạo API key riêng tại:
- Groq: `console.groq.com`
- Gemini: `aistudio.google.com`

---

## Trạng thái Sessions

| Session | Nội dung | Trạng thái |
|---|---|---|
| Sprint 1 | STT + TTS + LLM + main_loop streaming | ✅ |
| Sprint 2 | ChromaDB RAG | ✅ |
| Sprint 3 | OpenCV Camera | ✅ |
| Session C | Safety Filter + Wake-word stub + TTS fallback | ✅ |
| Session D | RAG nâng cấp — threshold, patterns, methods | ✅ |
| Session E | CryDetector + EventNotifier + LBPH face | ✅ |
| Sprint 6 | PIN auth + Camera MJPEG + TaskManager + sao thưởng | ✅ |
| Session H | PWA + QR code + auto-restart + stress test | ✅ |
| Session AUDIT | Code quality + 51 automated tests | ✅ |
| Session I | Whisper large-v2 GPU + language lock + camera DSHOW | ✅ |
| Session J | Migrate Ollama → Groq + Gemini + config.json + .env | ✅ |
| Session K | Audio monitoring WebSocket (nghe tiếng phòng qua browser) | ✅ |
| Session L | Mom direct talk — bật mic mẹ nói trực tiếp với bé | ✅ |
| Session M | HTTPS self-signed + Cloudflare Tunnel kết nối từ xa | ✅ |
| Session N | Fix bugs: audio playback + mom pause + camera log | ✅ |
| Sprint 4 | ESP32 / Cơ khí | 🚫 Chờ phần cứng |

**Tests hiện tại: 54+/54+ PASS**

---

## Phần cứng

Laptop test: không có GPU → Whisper small CPU (tự động)
PC production: RTX 2060 Super 8GB → Whisper large-v2 CUDA (tự động)
Robot vật lý: chưa có — chờ mua phần cứng (ESP32, motor, khung...)