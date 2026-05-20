# ARCHITECTURE.md — Kiến Trúc Hệ Thống Robot Bi

> Phiên bản: 1.2 | Cập nhật: 2026-05-20
> File này mô tả kiến trúc tổng thể, data flow, và các quyết định thiết kế quan trọng.
> Đây là tài liệu descriptive — implementation details nằm trong `PROJECT.md` và `SYSTEM_MAP.md`.
> Cập nhật khi có thay đổi về kiến trúc, không cập nhật cho bugfix thông thường.

---

## 1. Tổng Quan

Robot Bi gồm 3 khối chính phối hợp với nhau.

### Kiến Trúc Hiện Tại (Prototype)

```
┌──────────────────────────────────────────────────────────────────┐
│                     Brain Server (PC / Laptop)                   │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  AI Engine  │  │  API Server  │  │     Storage            │  │
│  │  Groq LLM   │  │  FastAPI     │  │  SQLite (runtime)      │  │
│  │  Gemini FB  │  │  WebSocket   │  │  ChromaDB (memory)     │  │
│  │  Whisper    │  │  HTTPS       │  │  File system           │  │
│  │  edge-tts   │  │              │  │                        │  │
│  │  Safety     │  └──────────────┘  └────────────────────────┘  │
│  └─────────────┘                                                 │
└──────────────────────┬───────────────────────────────────────────┘
                       │ WiFi (LAN)
          ┌────────────┴─────────────────────┐
          │                                  │
          ▼                                  ▼
┌─────────────────────┐          ┌───────────────────────┐
│    Thân Robot        │          │    Người Dùng         │
│                     │          │                       │
│  ESP32 #1 (Motor)   │          │  Browser (Parent App) │
│  ESP32-S3 (Audio    │          │  Mobile / Desktop     │
│    + Display)       │          │                       │
│  USB Webcam (test)  │          └───────────────────────┘
│  Màn hình TFT       │
│  Mic + Loa          │
└─────────────────────┘
```

### Kiến Trúc Sản Xuất (Hướng Tương Lai)

```
┌──────────────────────────────────────────────────────────────────┐
│                     Brain Server (PC / Laptop)                   │
│  AI, STT, TTS, LLM, Safety, API Server, Storage                  │
└──────────────────────┬───────────────────────────────────────────┘
                       │ WiFi (LAN)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                Gateway (Orange Pi hoặc tương đương)              │
│  Body Manager — WebRTC — OTA — Health — WiFi — Bridge            │
└─────┬─────────────────┬────────────────────────────┬─────────────┘
      │                 │                            │
      ▼                 ▼                            ▼
ESP32 Motor       ESP32-S3                      Camera IMX219
(di chuyển,      (mặt/audio/                  → WebRTC về
 safety)          cảm ứng)                      Brain Server
```

**Lưu ý quan trọng**:
- USB webcam chỉ dùng cho prototype và test nhanh — không phải hướng sản phẩm
- N100 mini PC là tùy chọn tương lai cho local-brain độc lập — không thuộc kế hoạch chính hiện tại
- Não AI vẫn luôn ở Brain Server — Gateway chỉ làm I/O, điều phối, không làm AI

---

## 2. Khối PC — Brain

PC là trung tâm xử lý của toàn bộ hệ thống. Tất cả AI, logic, storage đều chạy trên PC.

### 2.1 Main Loop (`src/main.py`)

Vòng lặp chính điều phối toàn bộ conversation flow:

```
Wake word detected
       │
       ▼
  Listen (STT)
  faster-whisper
       │
       ▼
  Safety pre-check
       │
       ▼
  RAG Memory Query
  ChromaDB lookup
       │
       ▼
  LLM Processing
  5-provider chain: Cerebras → Groq → Sambanova → Gemini → Cloudflare AI
       │
       ▼
  Safety Filter (POST-LLM)
  src/safety/safety_filter.py
       │
       ▼
  TTS Generation
  edge-tts → pyttsx3 fallback
       │
       ▼
  Audio Playback
  pygame chunked streaming
       │
       ▼
  Memory Update
  RAG + SQLite
```

**Quy tắc bất biến**: Safety Filter luôn chạy sau LLM và trước TTS — không bao giờ bỏ qua.

### 2.2 API Server (`src/api/server.py`)

FastAPI server phục vụ 3 loại client:

| Client | Giao thức | Mục đích |
|---|---|---|
| Parent App (browser) | HTTPS + WSS | Dashboard phụ huynh |
| Robot Display (màn hình robot) | HTTPS | UI mặt biểu cảm, flashcard, video call |
| ESP32 devices | WebSocket | Lệnh motor, audio commands |

**Route structure**:
```
src/api/routers/
├── auth_router.py        — Login, JWT, refresh
├── admin_router.py       — Family management
├── analytics_router.py   — Báo cáo, thống kê
├── control_router.py     — Core: events, tasks, puppet, RAG
├── conversation_router.py — Lịch sử trò chuyện
├── education_router.py   — Flashcard, lịch học
├── emotion_router.py     — Cảm xúc bé
├── game_router.py        — Đố vui, quiz
├── motor_router.py       — Điều khiển robot
├── music_router.py       — Nhạc
├── ops_router.py         — Health, camera stream, tunnel
├── persona_router.py     — Tính cách Bi
├── story_router.py       — Kể chuyện
├── streaming_router.py   — WebSocket events, mom-talk
├── video_call_router.py  — Video call
├── webrtc_router.py      — WebRTC signaling
└── wifi_router.py        — ESP32 registration, WiFi
```

### 2.3 Storage

| Store | Path | Dùng cho |
|---|---|---|
| SQLite | `runtime/robot_bi.db` | Users, auth, conversations, tasks, events, settings |
| ChromaDB | `runtime/chroma_db/` | RAG memory — long-term memory của Bi về bé |
| HF Cache | `runtime/.hf_cache/` | Sentence-transformer models |
| Vision data | `runtime/vision_data/` | Camera clips, vision artifacts |

**Nguyên tắc storage**:
- Tất cả data scope theo `family_id` — không lẫn lộn giữa các gia đình
- Runtime files không được git-track
- DB path cố định tại `runtime/robot_bi.db` — không thay đổi

### 2.4 AI Stack

```
Input (voice)
    │
    ▼
faster-whisper (STT)
    GPU: large-v2
    CPU fallback: WHISPER_CPU_MODEL (default: medium)
    │
    ▼
Groq API — llama-3.3-70b-versatile (Primary LLM)
    │ (nếu fail)
    ▼
Gemini API — gemini-2.5-flash-lite (Fallback LLM)
    │
    ▼
Safety Filter — regex/pattern (post-LLM)
    │
    ▼
edge-tts (TTS primary)
    │ (nếu fail)
    ▼
pyttsx3 (TTS fallback)
```

---

## 3. Khối Robot — Body

### 3.0 Gateway — Body Manager (Kiến Trúc Sản Xuất)

**Vai trò**: Đứng giữa Brain Server và các ESP32, quản lý toàn bộ thân robot.

Gateway **không phải AI brain**. Gateway chỉ làm:

| Chức năng | Mô tả |
|---|---|
| Body manager | Điều phối ESP32 Motor và ESP32-S3 |
| WebRTC | Nhận camera stream, stream về Brain Server |
| OTA (cập nhật từ xa) | Cập nhật firmware ESP32 không cần tháo thiết bị |
| Health monitor | Theo dõi trạng thái các component trong robot |
| WiFi reconnect | Tự kết nối lại khi mất mạng |
| Bridge | Chuyển tiếp lệnh từ Brain Server xuống đúng ESP32 |
| Phản xạ nhanh | Xử lý vài tình huống đơn giản không cần đợi Brain Server |

**Hardware khuyến nghị**: Orange Pi hoặc tương đương — Linux board nhỏ gọn, chạy được WebRTC.

### 3.1 ESP32 Motor — Di Chuyển và An Toàn

**Vai trò**: Nhận lệnh di chuyển từ Brain Server (qua Gateway trong sản xuất), điều khiển L298N.

```
PC WebSocket Server
        │
        │ WebSocket (WiFi)
        ▼
   ESP32 #1
        │
        ▼
      L298N
     /     \
Motor T  Motor P
(trái)   (phải)
```

**Firmware**: `firmware/Robot_BI/Robot_BI.ino`

**Commands nhận từ PC**:
- Forward, Backward, Left, Right, Stop
- Speed control
- Dock/Home sequence

**Autonomous behaviors** (xử lý trên PC, gửi lệnh xuống ESP32):
- Lắc lư theo nhạc — PC gửi pattern di chuyển theo nhịp
- Di chuyển biểu đạt cảm xúc — PC gửi sequence
- Follow me — PC xử lý OpenCV, gửi lệnh hướng
- Về dock — PC gửi sequence dock

### 3.2 ESP32-S3 — Audio + Display Hub

**Vai trò**: Xử lý I2S audio (mic và loa), render UI lên màn hình TFT.

```
PC
 │
 │ WebSocket (WiFi)
 ▼
ESP32-S3
 ├── I2S IN  ←── INMP441 x2 (Mic) → stream audio về PC để STT
 ├── I2S OUT ───► MAX98357 (Loa) ← nhận audio từ PC để TTS
 └── SPI     ───► Màn hình TFT
                   └── Render robot_display UI
                       (face, flashcard, video call)
```

**Audio flow - STT**:
```
Bé nói → INMP441 → I2S → ESP32-S3 → WebSocket → PC → faster-whisper
```

**Audio flow - TTS**:
```
PC → edge-tts → audio chunks → WebSocket → ESP32-S3 → I2S → MAX98357 → Loa
```

**Display flow**:
```
PC API Server serves robot_display/index.html
        │
        │ HTTPS (WiFi)
        ▼
ESP32-S3 opens webview / browser
        │
        ▼
Màn hình TFT hiển thị UI
(face animations, flashcard, video call)
```

**Display commands từ PC**:
- Set emotion (happy, sad, angry, sleep, thinking...)
- Show flashcard (image + text)
- Start/end video call UI
- Show reward animation

### 3.3 Camera

**Prototype**: USB webcam gắn ngoài PC, đủ để test nhanh các tính năng vision.

**Sản xuất**: Camera tích hợp trong thân robot, stream qua Gateway.

```
Prototype:
USB Webcam → PC → OpenCV processing

Sản xuất:
Camera IMX219 (trong robot)
      │
      ▼
Gateway (WebRTC)
      │ WebRTC stream (WiFi)
      ▼
Brain Server — OpenCV processing
 ├── Motion detection
 ├── Follow me tracking
 ├── Cry detection support
 └── Video call stream → Parent App
```

**Lý do chọn IMX219**: Chất lượng tốt, phổ biến với Linux board, hỗ trợ WebRTC qua libcamera.

---

## 4. Khối Người Dùng — Interfaces

### 4.1 Parent App (`frontend/parent_app/`)

**Stack**: React 18 + Vite 5 SPA

**Kết nối**:
```
Parent App (Browser)
      │
      ├── HTTPS REST ──────► PC FastAPI
      ├── WebSocket (WSS) ──► PC (robot status, events real-time)
      └── MJPEG stream ─────► PC (camera relay từ robot)
```

**Remote access**: Cloudflare Tunnel cho phép phụ huynh truy cập từ ngoài mạng LAN.

**5 tabs chính**:
1. Trang chủ — Robot status, quick controls
2. Giám sát — Camera live, events
3. Học tập — Báo cáo, lịch học, flashcard
4. Nhật ký — Lịch sử trò chuyện, cảm xúc
5. Thêm — Cài đặt, tasks, music, stories

### 4.2 Robot Display (`frontend/robot_display/`)

**Stack**: HTML/CSS/JS thuần (không React)

**Mục đích**: UI hiển thị trên màn hình TFT của robot — mặt biểu cảm, flashcard, video call.

**Kết nối**:
```
ESP32-S3 webview
      │ HTTPS (WiFi LAN)
      ▼
PC serves robot_display/index.html
      │
      ├── WebSocket ──► Nhận lệnh emotion, flashcard từ PC
      └── WebRTC ─────► Video call với Parent App
```

**Pages**:
- `index.html` — Main face display với emotion animations
- `face.html` — Face modes
- `flashcard.html` — Flashcard display

---

## 5. Data Flow — Luồng Dữ Liệu Chính

### 5.1 Conversation Flow (Happy Path)

```
1. Bé nói "Bi ơi [câu hỏi]"
2. INMP441 → ESP32-S3 → PC (audio stream)
3. faster-whisper → text
4. RAG query ChromaDB → relevant memories
5. Safety pre-check
6. Groq LLM (text + memories + system prompt) → response
7. Safety Filter post-LLM → safe response
8. edge-tts → audio chunks
9. PC → ESP32-S3 → MAX98357 → Loa (phát âm thanh)
10. PC → ESP32-S3 → Màn hình (update face emotion)
11. SQLite save conversation turn
12. ChromaDB update memory nếu có thông tin quan trọng
```

### 5.2 Video Call Flow

```
1. Bé nói "Bi ơi, gọi cho mẹ"
2. LLM nhận diện intent → gọi video call API
3. PC gửi push notification đến Parent App (mẹ)
4. ESP32-S3 → Màn hình chuyển sang video call UI
5. ESP32 Motor dừng hoàn toàn
6. WebRTC signaling qua PC
7. Video stream: ESP32-CAM → PC → Parent App
8. Audio: INMP441 ↔ PC ↔ Parent App browser mic/speaker
9. Khi kết thúc: Màn hình về face mode, motor hoạt động lại
```

### 5.3 Cry Detection Flow

```
1. Cry detector (PC) phát hiện tiếng khóc từ audio stream
2. PC gửi notification lên Parent App
3. PC trigger Bi phản hồi: "Bé có làm sao không? Sao bé khóc vậy?"
4. ESP32-S3 → Màn hình hiển thị concerned face
5. ESP32 Motor tiến lại gần bé (nếu không đang call)
6. Conversation flow bình thường tiếp tục
```

### 5.4 Safety Escalation Flow

```
1. Safety Filter phát hiện vi phạm nghiêm trọng
2. Block response — không phát âm thanh vi phạm
3. Thay bằng response mặc định an toàn
4. Log event với timestamp + content
5. Gửi alert notification lên Parent App
```

---

## 6. Authentication và Security Architecture

```
Client Request
      │
      ▼
JWT Middleware (tất cả routes)
      │
      ├── Valid token → proceed
      └── Invalid → 401 Unauthorized
              │
              ▼
         /api/auth/login (whitelist — không cần token)
              │
              ├── Rate limit: 5 sai → lock 15 phút
              ├── Argon2id password verify
              └── Return JWT access + refresh tokens
```

**Token lifecycle**:
- Access token: 60 phút (HS256)
- Refresh token: 30 ngày (sha256, stored in SQLite)
- Rotation: mỗi lần refresh → revoke cũ, issue mới

**WebSocket auth**: Token qua `?token=` query param
**Camera auth**: Token qua header hoặc `?auth=` query param

**Whitelist (không cần token)**:
`/health`, `/api/status`, `/api/mom/status`, `/api/auth/login`, `/api/auth/logout`, `/auth/register`, `/auth/login/v2`, `/auth/refresh`, `/`, `/static/*`

---

## 7. Multi-Family Isolation

Mọi data đều scope theo `family_id`:

```
Request → JWT decode → extract family_id
                │
                ▼
        ChromaDB: where={"family_id": family_id}
        SQLite: WHERE family_id = ?
        Events: family_id filter
        Tasks: family_id filter
        Conversations: family_id filter
```

Admin endpoints (`/api/admin/families`) chỉ accessible với `is_admin = True`.

---

## 8. Quyết Định Kiến Trúc Quan Trọng

| Quyết định | Lý do |
|---|---|
| Brain Server làm toàn bộ AI, ESP32/Gateway chỉ làm I/O | ESP32 không đủ sức chạy LLM/STT; tách biệt rõ vai trò |
| 2 ESP32 riêng biệt cho motor và audio | Tránh nhiễu, motor noise ảnh hưởng audio |
| WebSocket cho Brain Server ↔ ESP32 | Độ trễ thấp, hai chiều, đơn giản hơn MQTT |
| Gateway layer trong sản xuất | Giảm tải WebSocket trực tiếp, hỗ trợ OTA, WebRTC, health monitor |
| Camera sản xuất qua Gateway WebRTC | Chất lượng stream tốt hơn MJPEG, hỗ trợ video call real-time |
| USB webcam chỉ cho prototype | Đơn giản, test nhanh, không cần phần cứng robot |
| SQLite thay vì PostgreSQL | Đơn giản, không cần server riêng, đủ cho scale hiện tại |
| ChromaDB cho RAG | Local, không cần cloud, privacy-first |
| 5-provider LLM fallback chain (Cerebras → Groq → Sambanova → Gemini → Cloudflare AI) | Không bao giờ mất AI kể cả khi 4/5 provider lỗi; Groq có cooldown mechanism |
| edge-tts + pygame chunked | Time-to-first-audio < 2s, không cần đợi full audio |
| Robot Display là web app | Dễ update UI không cần reflash ESP32; Brain Server serve, ESP32-S3 render |
| Cloudflare Tunnel | Remote access không cần port forwarding, secure |
| N100 chỉ là tùy chọn tương lai | Cho phép local-brain độc lập không cần PC, nhưng không thuộc kế hoạch hiện tại |

---

## 9. Giới Hạn Hiện Tại và Hướng Giải Quyết

| Giới hạn | Impact | Hướng giải quyết |
|---|---|---|
| Wake word dùng dev path | Bé phải nói đúng keyword | Train custom model "Bi ơi" |
| Cloudflare quick tunnel URL thay đổi sau restart | Remote URL không ổn định | Named tunnel sau |
| Safety filter chỉ dùng regex | LLM có thể bypass bằng từ lắt léo | Thêm secondary AI classifier |
| Camera stream độ trễ | Video call không real-time hoàn hảo | Tối ưu WebRTC, giảm resolution |
| Motor và audio cùng nguồn pin | Motor noise ảnh hưởng chất lượng audio | Tách nguồn, thêm tụ lọc |
