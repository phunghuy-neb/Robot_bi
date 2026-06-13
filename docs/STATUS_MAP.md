# STATUS_MAP.md — Trạng Thái Thực Tế Từng Tính Năng

> Phiên bản: 1.5 | Cập nhật: 2026-06-13
> File này là bức tranh trung thực về code hiện có — không phải docs, không phải kế hoạch.
> Cập nhật khi code thực sự thay đổi trạng thái, không khi docs thay đổi.
>
> **Legend:**
> - 🟢 Done — có code thực, hoạt động
> - 🟡 Partial — có code nhưng chưa đầy đủ / mock fallback / chưa nối API
> - 🔴 Stub — file tồn tại nhưng chỉ là placeholder, không có logic thật
> - ⚪ Zero — không có code, chỉ có docs/backlog

---

## 1. Backend Brain (`src/`)

| Tính năng | Status | File chính | Ghi chú |
|---|---|---|---|
| Main conversation loop | 🟢 | `src/main.py` | Hoạt động |
| FastAPI + WebSocket server | 🟢 | `src/api/server.py` | Production-ready |
| LLM 5-provider chain | 🟢 | `src/ai/ai_engine.py` | Cerebras `gpt-oss-120b` → Groq → Sambanova → Gemini → Cloudflare; cooldown mechanism |
| System prompt / persona | 🟢 | `src/ai/prompts.py` | Personality rules đầy đủ |
| RAG memory (ChromaDB) | 🟢 | `src/memory/rag_manager.py` | threshold 0.62, 12 fact types, max 500/family |
| Session naming tự động | 🟢 | `src/ai/session_namer.py` | Groq non-streaming, fallback text[:30] |
| Safety filter 3 layers | 🟢 | `src/safety/safety_filter.py` | topic (5 patterns) + blacklist (11 words) + sentence cap |
| PII filter | 🟢 | `src/safety/pii_filter.py` | 8 types: phone/email/CCCD/address/school/password/financial/fullname; gentle redirect; dual-pattern (có/không dấu) |
| Emotion risk detector | 🟢 | `src/safety/emotion_risk_detector.py` | HIGH/MEDIUM/LOW; escalation HIGH→override; log_event flag; dual-pattern |
| Manipulation guard | 🟢 | `src/safety/manipulation_guard.py` | LLM output + user input; blocks grooming signals + secret-keeping + parent replacement |
| STT faster-whisper | 🟢 | `src/audio/input/ear_stt.py` | GPU large-v2, CPU medium; mic fallback to silent |
| TTS edge-tts chunked | 🟢 | `src/audio/output/mouth_tts.py` | **Yêu cầu internet**; fallback pyttsx3 local |
| Mom talk audio | 🟢 | `src/audio/output/mouth_tts.py` | `pygame.Channel(7)`, 16k→44.1k resample; **Protected Fix** |
| Cry detection YAMNet | 🟢 | `src/audio/input/cry_detector.py` | Optional TFLite runtime; fallback RMS/ZCR |
| Wake word | 🟡 | `src/wakeword/` | Sprint 0.4: synthetic dataset pipeline + MFCC+SVM classifier (custom_mfcc backend); train: `scripts/train_wakeword.py`; test: `scripts/test_wakeword.py`; target 75–85% accuracy; **model file needs training run** |
| Persona manager | 🟡 | `src/ai/persona_manager.py` | Static persona + Sprint 1.3 context modifiers đã có; long-term behavioral profile chưa có |
| Emotion analyzer | 🟡 | `src/emotion/emotion_analyzer.py` | Basic sentiment; không phải ML model thật |
| Emotion journal | 🟡 | `src/emotion/emotion_journal.py` | SQLite log; no real analysis |
| Emotion alerts | 🟡 | `src/emotion/emotion_alert.py` | Rule-based; threshold check |
| Living State System | 🟢 | `src/living/living_state.py` | Sprint 1.1: runtime-only 7-state engine integrated into text/voice loop |
| Micro Moments Engine | 🟢 | `src/living/micro_moments.py` | Sprint 1.2: 8 idle moments, rate limit, homework + sleep-hour guards |
| Proactive Behaviors Engine | 🟢 | `src/living/proactive_behaviors.py` | Sprint 1.4: child-present idle prompt after silence; anti-spam, homework + sleep-hour guards |

---

## 2. Parent App (`frontend/parent_app/`)

| Tính năng | Status | File chính | Ghi chú |
|---|---|---|---|
| Auth: login/logout/JWT/refresh | 🟢 | `src/components/` + `/api/auth/` | Hoạt động với backend |
| Xem lịch sử hội thoại | 🟢 | `loadThreads()`, `showThreadDetail()` | **Protected Fix** |
| Events real-time (WebSocket) | 🟢 | `/ws?token=` | |
| Camera live stream | 🟢 | `/api/camera` | MJPEG |
| Weekly analytics | 🟢 | `/api/analytics/weekly` | |
| Emotion today/monthly | 🟢 | `/api/emotion/` | |
| Task management + stars | 🟢 | `/api/tasks/` | |
| Puppet (gõ chữ → Bi nói) | 🟢 | `/api/puppet` | |
| Mom talk (mic → Bi phát) | 🟢 | `/api/mom/` | |
| Joystick điều khiển motor | 🟢 | `/api/motor/` | |
| Admin family management | 🟢 | `/api/admin/families` | |
| React+Vite SPA build | 🟡 | `frontend/parent_app/src/` | Build passes; một số API call dùng mock fallback |
| Radio / nhạc | 🟡 | `src/` | Mock fallback trong api.js |
| Videos | 🟡 | `src/` | Mock fallback |
| Games | 🟡 | `src/` | Mock fallback |
| System logs | 🟡 | `src/` | Mock fallback |
| Settings (child profile, age filter, time limits) | 🟡 | `src/` | 4 `saveSettings()` stubs return null |
| Dashboard tùy chỉnh | ⚪ | — | Không có code |
| Báo cáo tuần email | ⚪ | — | Không có code |
| Push notification PWA | ⚪ | — | Không có code |

---

## 3. Voice System

| Tính năng | Status | File chính | Ghi chú |
|---|---|---|---|
| STT GPU/CPU auto-detect | 🟢 | `src/audio/input/ear_stt.py` | |
| STT mic fallback to silent | 🟢 | `src/audio/input/ear_stt.py` | **Protected Fix** |
| Beep khi lắng nghe | 🟢 | `ear_stt.py` `_play_beep()` | `pygame.Channel(6)` non-blocking |
| TTS edge-tts streaming | 🟢 | `src/audio/output/mouth_tts.py` | Chunked, low time-to-first-audio |
| TTS pyttsx3 fallback | 🟢 | `src/audio/output/mouth_tts.py` | Local, không cần internet |
| Mom pause logic | 🟢 | `is_mom_talking()` | **Protected Fix** |
| Cry detection | 🟢 | `src/audio/input/cry_detector.py` | Log missing mic only once |
| Wake word detection | 🟡 | `src/audio/input/wake_word.py` | Disabled default; dùng faster-whisper tiny |
| Tiếng Anh song song | ⚪ | — | Không có code |
| Pronunciation scoring | ⚪ | — | Không có code |
| Language auto-detect | ⚪ | — | Không có code |

---

## 4. Robot Control (Hardware)

| Tính năng | Status | File chính | Ghi chú |
|---|---|---|---|
| ESP32 motor firmware | 🟢 | `firmware/Robot_BI/Robot_BI.ino` | 407 lines, L298N, WebSocket port 81, watchdog |
| Motor controller Python | 🟢 | `src/motion/motor_controller.py` | Simulation mode mặc định; WebSocket hoặc serial |
| API endpoints motor | 🟢 | `src/api/routers/motor_router.py` | Forward, backward, left, right, stop |
| Body language library | ⚪ | — | Không có code |
| Idle behavior | ⚪ | — | Không có code |
| Di chuyển theo cảm xúc | ⚪ | — | Không có code |
| Follow me (camera tracking) | 🔴 | `src/motion/follow_me.py` | **Stub placeholder only** — 5 lines, không có CV |
| Auto-dock / charging dock | 🔴 | `src/motion/dock_charger.py` | **Stub placeholder only** |
| Navigation | 🔴 | `src/motion/navigation.py` | Stub |
| Obstacle avoidance | ⚪ | — | Không có code |
| ESP32-S3 audio firmware | ⚪ | — | Hardware có (INMP441+MAX98357) nhưng **firmware chưa viết** |
| ESP32-S3 display firmware | ⚪ | — | Hardware chưa mua (TFT SPI); firmware chưa viết |

---

## 5. Learning & Education (`src/education/`)

| Tính năng | Status | File chính | Ghi chú |
|---|---|---|---|
| Flashcard engine | 🟢 | `src/education/flashcard_engine.py` | Toán, Tiếng Anh, địa lý |
| Homework classifier | 🟢 | `src/education/homework_classifier.py` | |
| Conversation homework marking | 🟢 | `/api/conversations/{id}/homework` | **Protected Fix** |
| Learning schedule | 🟡 | `src/education/` | Partial — basic scheduler |
| Progress tracking | 🟡 | `src/education/learning_progress.py` | Partial |
| Curriculum engine | 🟡 | `src/education/curriculum.py` | Partial |
| Language tutor | 🟡 | `src/education/language_tutor.py` | Partial |
| Learning Hub (Duolingo-style) | ⚪ | — | Không có code |
| Vocabulary tracking tiếng Anh | ⚪ | — | Không có code |
| Pronunciation scoring | ⚪ | — | Không có code |

---

## 6. Safety & Privacy

| Tính năng | Status | File chính | Ghi chú |
|---|---|---|---|
| Safety filter 3 layers | 🟢 | `src/safety/safety_filter.py` | Runs post-LLM, pre-TTS |
| Username/password Argon2id | 🟢 | `src/infrastructure/auth/auth.py` | |
| JWT access + refresh rotation | 🟢 | `src/infrastructure/auth/auth.py` | **Protected Fix** |
| Rate limit login (5→lock 15p) | 🟢 | SQLite `login_attempts` | **Protected Fix** |
| Secrets từ `.env` | 🟢 | `.env` | `AUTH_PIN`, `JWT_SECRET_KEY`, API keys |
| Multi-family data isolation | 🟢 | Tất cả queries | `where={"family_id": family_id}` |
| Camera stream auth | 🟢 | JWT middleware | |
| Face recognition | 🔴 | `src/vision/face_recognizer.py` | **Stub — 5 lines** |
| Fall detection | 🔴 | `src/vision/fall_detector.py` | **Stub — 5 lines** |
| PII detection | 🟢 | `src/safety/pii_filter.py` | ✅ Done — Sprint 0.2 |
| Grooming pattern detection | 🟢 | `src/safety/manipulation_guard.py` | ✅ Done — Sprint 0.2 |
| Emotion risk escalation | 🟢 | `src/safety/emotion_risk_detector.py` | ✅ Done — Sprint 0.2 |
| Vietnamese no-diacritic matching | 🟢 | `src/safety/vi_normalize.py` | ✅ Done — Sprint 0.2 |
| Encrypted local storage | ⚪ | — | SQLite không mã hóa |
| Audit log | ⚪ | — | Không có code |

---

## 7. Infrastructure

| Tính năng | Status | File chính | Ghi chú |
|---|---|---|---|
| SQLite runtime DB | 🟢 | `runtime/robot_bi.db` | Fixed path; **Protected Fix** |
| ChromaDB RAG | 🟢 | `runtime/chromadb/` | PersistentClient |
| HTTPS self-signed | 🟢 | `src/api/server.py` | **Protected Fix** |
| Cloudflare Tunnel | 🟢 | config | Quick tunnel; named tunnel ⚪ |
| Automated test suite | 🟢 | `tests/run_tests.py` | |
| `python sync.py` | 🟢 | `sync.py` | Generate CLAUDE.md + AGENTS.md từ PROJECT.md |
| Gateway layer (Orange Pi) | ⚪ | — | Không có code — planned for production |
| OTA firmware update | ⚪ | — | Không có code |
| Named Cloudflare Tunnel | ⚪ | — | URL hiện tại thay đổi mỗi restart |
| Health monitor | ⚪ | — | Không có code |
| WebRTC streaming | 🟡 | `src/api/routers/webrtc_router.py` | Router tồn tại, in-memory manager; chưa test thật |

---

## Summary — Honest Count

| Domain | 🟢 Done | 🟡 Partial | 🔴 Stub | ⚪ Zero |
|---|---|---|---|---|
| Backend Brain | 17 | 5 | 0 | 0 |
| Parent App | 11 | 6 | 0 | 3 |
| Voice System | 7 | 1 | 0 | 3 |
| Robot Control | 3 | 0 | 3 | 5 |
| Learning | 3 | 4 | 0 | 3 |
| Safety/Privacy | 11 | 0 | 2 | 2 |
| Infrastructure | 6 | 1 | 0 | 4 |
| **Tổng** | **58** | **17** | **5** | **20** |

**Tổng cộng: 100 items — 58% Done, 17% Partial, 5% Stub, 20% Zero**

---

## Critical Gaps (ưu tiên nhìn nhận)

| Gap | Mức độ | Ghi chú |
|---|---|---|
| ESP32-S3 audio firmware không tồn tại | 🔴 Hardware blocked | Phần cứng có sẵn, nhưng robot câm điếc trên hardware |
| edge-tts yêu cầu internet | 🟡 Product claim | Docs nói "local-first" nhưng TTS chính phụ thuộc cloud |
| Follow me / dock / navigation: stubs | 🟡 Expectation | Được nhắc nhiều nhưng 0% code thật |
| Wake word disabled by default | 🟡 Usability | "Bi ơi" không hoạt động trừ khi bật thủ công |
| ~~Grooming/PII detection: không có~~ | ✅ Đã giải quyết Sprint 0.2 | `pii_filter.py` + `manipulation_guard.py` + `emotion_risk_detector.py` |
| Motor IP hardcoded | 🟡 Deployment | `192.168.40.107:8443` trong firmware, phải sửa mỗi lần deploy |
| Parent App mock fallbacks | 🟡 Feature | Radio/videos/games/logs hiện dùng mock data |
