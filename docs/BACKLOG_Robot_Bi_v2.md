# BACKLOG Robot Bi — Danh Sách Tính Năng

> Phiên bản: 2.0 | Cập nhật: 2026-05-15
> Đây là living document — thêm ý tưởng mới bất cứ lúc nào, không có timeline cứng.
> Status: ✅ Done | 🔧 In progress / partial | ⬜ Not started | 💡 Idea / exploring
> Thứ tự trong mỗi nhóm không phản ánh priority — priority được quyết định theo từng session.

---

## 1. Core Infrastructure

| Status | Feature | Ghi chú |
|---|---|---|
| ✅ | Main conversation loop | `src/main.py` |
| ✅ | FastAPI + WebSocket API server | `src/api/server.py` |
| ✅ | SQLite runtime storage | `runtime/robot_bi.db` |
| ✅ | ChromaDB RAG memory | Family-scoped |
| ✅ | Multi-family isolation | Tất cả data scope theo family_id |
| ✅ | Sync generated agent docs | `python sync.py` |
| ✅ | Automated test suite | `python tests/run_tests.py` |
| ✅ | Cloudflare Tunnel support | Remote access phụ huynh |
| ✅ | HTTPS self-signed | LAN access |

---

## 2. AI và Ngôn Ngữ

| Status | Feature | Ghi chú |
|---|---|---|
| ✅ | LLM: Groq primary + Gemini fallback | `llama-3.3-70b-versatile` / `gemini-2.5-flash-lite` |
| ✅ | STT: faster-whisper GPU/CPU auto-detect | `large-v2` GPU, `medium` CPU |
| ✅ | TTS: edge-tts + pyttsx3 fallback | Chunked streaming |
| ✅ | Safety filter post-LLM pre-TTS | Không bao giờ bỏ qua |
| ✅ | RAG memory với threshold 0.50 | Deduplication, family-scoped |
| ✅ | Session naming tự động | Groq non-streaming, 5s timeout |
| 🔧 | Wake word "Bi ơi" | Dev/test path hiện tại, chưa có custom model |
| ⬜ | Train wake word model tùy chỉnh | Cần 30+ audio samples |
| ⬜ | Ngôn ngữ: hỗ trợ tiếng Anh song song | Bé có thể nói cả Anh lẫn Việt |
| ⬜ | Pronunciation scoring tiếng Anh | Đánh giá phát âm của bé |
| ⬜ | Language auto-detect | Tự nhận biết bé đang nói ngôn ngữ nào |

---

## 3. Tính Cách và Cảm Xúc

| Status | Feature | Ghi chú |
|---|---|---|
| ✅ | Personality prompts cơ bản | `src/ai/prompts.py` |
| ⬜ | Adaptive personality theo ngữ cảnh | Hồn nhiên khi chơi, nhẹ nhàng khi dạy, ấm áp khi dỗ |
| ⬜ | Cảm xúc giận dỗi khi bị bỏ mặc | Di chuyển vòng quanh + mặt hầm hầm + câu nói trẻ con |
| ⬜ | Idle behavior khi không có ai | Tự chơi, ngáp, nhìn quanh |
| ⬜ | Chủ động tương tác khi bé im lặng lâu | Hỏi thăm, rủ chơi |
| ⬜ | Nhớ sở thích và dùng trong hội thoại | "Hôm qua bạn kể thích khủng long..." |
| ⬜ | Tên robot tùy chỉnh theo gia đình | Mặc định "Bi", phụ huynh đổi được |
| ⬜ | Chọn giọng nam hoặc nữ | Cài trong Parent App |
| ⬜ | Emotion journal | Ghi lại cảm xúc bé theo ngày |
| ⬜ | Cảnh báo phụ huynh khi bé buồn kéo dài | Thông báo qua app |

---

## 4. Màn Hình Robot Display

| Status | Feature | Ghi chú |
|---|---|---|
| 🔧 | Robot display UI cơ bản | `frontend/robot_display/index.html` |
| 🔧 | Face modes (vui, buồn, ngủ...) | `face.html` placeholder |
| 🔧 | Flashcard display | `flashcard.html` placeholder |
| ⬜ | Màn hình thật trên phần cứng | LCD/OLED gắn trên thân robot |
| ⬜ | Animation biểu cảm mượt mà | Lip sync, eye movement |
| ⬜ | Screensaver khi idle | Chuyển động nhẹ, không tắt màn |
| ⬜ | Đổi giao diện theo ngày lễ | Tết, Giáng sinh, sinh nhật bé |
| ⬜ | Animation khen thưởng | Khi bé làm tốt |
| ⬜ | Video call UI trên màn hình robot | Hiển thị video người gọi |

---

## 5. Di Chuyển và Phần Cứng

| Status | Feature | Ghi chú |
|---|---|---|
| ✅ | ESP32 firmware cơ bản | L298N motor, WiFi, WebSocket |
| ✅ | Điều khiển từ xa qua Parent App | Joystick |
| ✅ | Motor registration + WiFi persistence | `firmware/Robot_BI/Robot_BI.ino` |
| ⬜ | Di chuyển tự chủ theo cảm xúc | Lắc lư theo nhạc, tiến lại khi bé buồn |
| ⬜ | Tránh vật cản | Cảm biến hoặc camera |
| ⬜ | Follow me — bám theo bé | OpenCV tracking |
| ⬜ | Dock sạc tự động | IR beacon, tự về dock khi pin yếu |
| ⬜ | Về dock theo lệnh từ app | Phụ huynh bấm nút "về chỗ" |
| ⬜ | Dừng hoàn toàn khi đang video call | Không di chuyển, không nói |
| ⬜ | Cảm biến xoa đầu / chạm | Phản ứng khi bé xoa đầu Bi |
| ⬜ | Nút SOS vật lý | Bé bấm để gọi bố mẹ ngay |

---

## 6. Học Tập

| Status | Feature | Ghi chú |
|---|---|---|
| ✅ | Flashcard engine cơ bản | Toán, Tiếng Anh, địa lý |
| ✅ | Homework classifier | Phát hiện bé đang hỏi bài tập |
| ✅ | Conversation homework marking | Lưu sessions là bài tập |
| 🔧 | Learning schedule | `src/education/` |
| 🔧 | Progress tracking | Tiến độ theo môn |
| ⬜ | Dạy học chủ động như giáo viên | Bi tự soạn bài, hỏi bé từng phần |
| ⬜ | Tất cả môn học | Khoa học, Lịch sử, Địa lý, Văn... |
| ⬜ | Flashcard với hình ảnh trên màn hình | Kết hợp visual + voice |
| ⬜ | Báo cáo tiến độ lên Parent App | Theo môn, theo tuần |
| ⬜ | Gợi ý phương pháp học cho phụ huynh | Bố mẹ chọn áp dụng hay không |
| ⬜ | Curriculum theo độ tuổi | 5–7, 8–10, 11–12 |
| ⬜ | Vocabulary tracking tiếng Anh | Từ đã học, từ cần ôn |

---

## 7. Giải Trí

| Status | Feature | Ghi chú |
|---|---|---|
| ✅ | Nhạc thiếu nhi offline | playlist.json Vietnamese/English/lullabies |
| ✅ | Kể chuyện có sẵn | Cổ tích, ngụ ngôn |
| ✅ | Word quiz + voice quiz | `resources/games/` |
| ⬜ | Kết nối Spotify | Phát nhạc theo yêu cầu |
| ⬜ | Kết nối YouTube | Phát nhạc theo yêu cầu |
| ⬜ | Bi lắc lư theo nhạc | Di chuyển nhẹ khi đang phát |
| ⬜ | Tự sáng tác câu chuyện theo yêu cầu | "Bi kể chuyện về khủng long đi" |
| ⬜ | Đố vui đa chủ đề và độ khó | Mở rộng từ quiz hiện tại |
| ⬜ | Sáng tác thơ cùng bé | Interactive |
| ⬜ | Hướng dẫn vẽ bằng lời | Mô tả từng bước |
| ⬜ | Hát cùng bé | Bi hát, bé hát theo |
| ⬜ | Nhạc ru ngủ giảm dần âm lượng | Tự tắt khi bé ngủ |

---

## 8. Video Call và Kết Nối Gia Đình

| Status | Feature | Ghi chú |
|---|---|---|
| 🔧 | WebRTC video call cơ bản | `src/api/routers/webrtc_router.py` |
| 🔧 | In-memory video call manager | `src/communication/` |
| ⬜ | Voice trigger gọi điện | "Bi ơi, gọi cho mẹ" → auto call tài khoản mẹ |
| ⬜ | Nhận call trên Parent App | Phụ huynh nhận trực tiếp trên web |
| ⬜ | Hiển thị call trên màn hình robot | Video người gọi hiện trên mặt Bi |
| ⬜ | Bi dừng mọi hoạt động khi đang call | Không nói, không di chuyển |
| ⬜ | Danh sách liên hệ | Mẹ, bố, ông, bà... |
| ⬜ | Lịch sử cuộc gọi | Parent App xem lại |
| ⬜ | Giao diện nhận call đơn giản cho ông bà | Không cần app riêng |
| ⬜ | Nhiều người cùng call | Ông bà + bố mẹ cùng lúc |

---

## 9. Giám Sát và An Toàn (Tính Năng Phụ)

| Status | Feature | Ghi chú |
|---|---|---|
| ✅ | Camera stream MJPEG | Phụ huynh xem live trên app |
| ✅ | Cry detection | YAMNet TFLite + fallback |
| ✅ | Event notifications | WebSocket real-time |
| ✅ | Motion detection cơ bản | `src/vision/` |
| ⬜ | Báo động khóc → thông báo phụ huynh + Bi hỏi han | Kết hợp 2 action |
| ⬜ | Phát hiện người lạ | Báo phụ huynh |
| ⬜ | Camera clip lưu lại sự kiện | Review sau |
| ⬜ | Smoke/fall detection | Tùy chọn, cần TFLite models |

---

## 10. Parent App

| Status | Feature | Ghi chú |
|---|---|---|
| ✅ | Auth: login/logout/JWT/refresh | `/api/auth/` |
| ✅ | WebSocket robot status real-time | `/ws?token=` |
| ✅ | Camera live stream | `/api/camera` |
| ✅ | Xem lịch sử trò chuyện | `/api/conversations` |
| ✅ | Events với filters | `/api/events` |
| ✅ | Weekly analytics | `/api/analytics/weekly` |
| ✅ | Emotion today/monthly | `/api/emotion/` |
| ✅ | Task management + stars | `/api/tasks/` |
| ✅ | Puppet (gõ chữ → Bi nói) | `/api/puppet` |
| ✅ | Mom talk (mẹ nói qua mic → Bi phát) | `/api/mom/` |
| ✅ | Joystick điều khiển motor | `/api/motor/` |
| ✅ | Admin family management | `/api/admin/families` |
| 🔧 | React + Vite SPA hoàn chỉnh | `frontend/parent_app/` |
| 🔧 | Settings: child profiles, age filter, time limits | Tier 2 — backend done, frontend wiring |
| 🔧 | Báo cáo học tập chi tiết | Tier 2 |
| ⬜ | Gợi ý phương pháp dạy cho phụ huynh | AI-generated, bố mẹ chọn |
| ⬜ | Push notification trên điện thoại | PWA push |
| ⬜ | Báo cáo tuần tự động gửi email | |
| ⬜ | Cài đặt tên và giọng robot | UI cho phụ huynh đổi |

---

## 11. Bảo Mật và Hạ Tầng

| Status | Feature | Ghi chú |
|---|---|---|
| ✅ | Username/password auth Argon2id | `src/infrastructure/auth/auth.py` |
| ✅ | JWT access + refresh token rotation | |
| ✅ | Rate limiting login (5 sai → khóa 15p) | SQLite `login_attempts` |
| ✅ | JWT middleware bảo vệ tất cả routes | Bao gồm WebSocket |
| ✅ | Secrets từ `.env` | Không hardcode |
| ✅ | Multi-family data isolation | |
| ⬜ | Encrypted local storage | Mã hóa SQLite |
| ⬜ | Audit log | Ai làm gì, khi nào |
| ⬜ | Named Cloudflare Tunnel | URL cố định, không đổi sau restart |

---

## 12. Ý Tưởng Đang Khám Phá (Chưa Quyết Định)

*Những ý tưởng này chưa được confirm, dùng để brainstorm và thảo luận.*

| Ý tưởng | Mô tả ngắn |
|---|---|
| Swarm 2 robots | Hai Bi kết nối WiFi, hành vi nhóm |
| Bi báo thức | Thay đồng hồ báo thức cho bé buổi sáng |
| Bi nhắc uống nước | Nhắc bé uống nước, vận động |
| Phát hiện bé đang học | Tự động chuyển chế độ học khi nhận ra bé ngồi vào bàn |
| Bi kể chuyện ngủ theo tên bé | Cá nhân hóa nhân vật trong truyện |
| Tích hợp lịch học trường | Bố mẹ nhập lịch → Bi nhắc bé |
| Chế độ "không làm phiền" | Bi tự hiểu khi nào bé cần yên tĩnh |
| Bi giới thiệu bạn bè | Kết nối 2 bé qua 2 Bi, chơi cùng |

---

## Cách Sử Dụng File Này

**Thêm ý tưởng mới**: Thêm dòng mới vào đúng nhóm, status là 💡 hoặc ⬜.

**Khi bắt đầu implement**: Đổi status thành 🔧.

**Khi hoàn thành**: Đổi status thành ✅, thêm ghi chú path nếu cần.

**Priority**: Không cố định trong file này — quyết định theo từng session dựa trên context và nhu cầu thực tế.
