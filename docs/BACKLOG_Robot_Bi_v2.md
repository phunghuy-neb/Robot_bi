# BACKLOG Robot Bi — Danh Sách Tính Năng

> Phiên bản: 2.3 | Cập nhật: 2026-05-20
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
| ✅ | LLM: 5-provider fallback chain | Cerebras → Groq → Sambanova → Gemini → Cloudflare AI; config trong `config.json` |
| ✅ | STT: faster-whisper GPU/CPU auto-detect | `large-v2` GPU, `medium` CPU |
| ✅ | TTS: edge-tts + pyttsx3 fallback | Chunked streaming; **edge-tts yêu cầu internet** (Microsoft cloud TTS) |
| ✅ | Safety filter post-LLM pre-TTS | Không bao giờ bỏ qua |
| ✅ | RAG memory với threshold 0.62 | Deduplication, family-scoped; max 500 memories/family |
| ✅ | Session naming tự động | Groq non-streaming, 5s timeout |
| 🔧 | Wake word "Bi ơi" | **Disabled by default** (`WAKEWORD_ENABLED=false`). Khi bật: fuzzy match qua `faster-whisper tiny`, chưa có custom model |
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
| ⬜ | Thư viện ngôn ngữ cơ thể theo cảm xúc | Vui lắc lư, buồn đi chậm, tò mò quay nhìn, an ủi tiến lại gần, giận đi vòng |
| ⬜ | Di chuyển lắc lư theo nhạc | Theo nhịp bài đang phát |
| ⬜ | Di chuyển tự chủ theo cảm xúc | Tiến lại khi bé buồn, lui ra khi bé cần yên tĩnh |
| ⬜ | Tránh vật cản | Cảm biến hoặc camera — cần trước follow me |
| ⬜ | Auto-dock — tự về nhà khi pin yếu | IR beacon hoặc tương đương; làm trước follow me |
| ⬜ | Về dock theo lệnh từ app | Phụ huynh bấm nút "về chỗ" |
| ⬜ | Follow me — bám theo bé | Cần camera tracking + obstacle avoidance ổn trước |
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
| ⬜ | Tất cả môn học | Toán, Tiếng Anh, Tiếng Việt, Khoa học, Lịch sử, Địa lý, Logic |
| ⬜ | Flashcard với hình ảnh trên màn hình | Kết hợp visual + voice |
| ⬜ | Báo cáo tiến độ lên Parent App | Theo môn, theo tuần |
| ⬜ | Gợi ý phương pháp học cho phụ huynh | Bố mẹ chọn áp dụng hay không |
| ⬜ | Curriculum theo độ tuổi | 5–7, 8–10, 11–12 |
| ⬜ | Vocabulary tracking tiếng Anh | Từ đã học, từ cần ôn |
| ⬜ | Kỹ năng cảm xúc và xã hội | Gọi tên cảm xúc, biết ơn, tự tin, giao tiếp |
| ⬜ | Thói quen lành mạnh | Nhắc uống nước, vận động nhẹ, thói quen ngủ |

---

## 6B. Learning Hub — Trang Học Trực Tiếp

*Nhóm riêng cho trang học theo kiểu Duolingo, cá nhân hóa hơn.*

| Status | Feature | Ghi chú |
|---|---|---|
| ⬜ | Trang Learning Hub trong Parent App | Tab hoặc trang riêng cho bé luyện tập |
| ⬜ | Bài học ngắn theo chủ đề | Dạng module nhỏ, 5–10 phút |
| ⬜ | Câu hỏi trắc nghiệm + tự luận ngắn | Phù hợp độ tuổi |
| ⬜ | Nhiệm vụ hằng ngày | Bi giao, bé hoàn thành |
| ⬜ | Điểm kinh nghiệm và huy hiệu | Gamification nhẹ |
| ⬜ | Chuỗi ngày học (streak) | Động lực học đều đặn |
| ⬜ | Cấp độ theo môn | Tăng khi làm đủ bài |
| ⬜ | Điều chỉnh độ khó theo năng lực | Không quá dễ, không quá khó |
| ⬜ | Ghi nhớ lỗi hay sai và gợi ý ôn tập | Học từ điểm yếu |
| ⬜ | Mục tiêu học tập do phụ huynh đặt | Bi dùng mục tiêu để nhắc và báo cáo |
| ⬜ | Báo cáo Learning Hub cho phụ huynh | Số bài, độ chính xác, thời gian, tiến bộ |
| ⬜ | Chế độ nhiệm vụ phiêu lưu | Giải toán mở cánh cửa, học từ vựng cứu nhân vật (vision cuối) |

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
| ✅ | **PII filter** (Sprint 0.2) | `src/safety/pii_filter.py` — 8 loại PII, gentle redirect, dual-pattern (có/không dấu) |
| ✅ | **Emotion risk detector** (Sprint 0.2) | `src/safety/emotion_risk_detector.py` — HIGH/MEDIUM/LOW; HIGH override + escalate |
| ✅ | **Manipulation guard** (Sprint 0.2) | `src/safety/manipulation_guard.py` — grooming, secret-keeping, parent replacement |
| ✅ | **Vietnamese diacritic normalizer** (Sprint 0.2) | `src/safety/vi_normalize.py` — fuzzy match có/không dấu |
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
| ⬜ | Dashboard tùy chỉnh | Phụ huynh bật/tắt thẻ, chọn môn theo dõi, xem tiến độ theo ngày/tuần/tháng |
| ⬜ | Đặt mục tiêu học tập cho bé | Bi dùng mục tiêu để nhắc và báo cáo |
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

## 12. Bi Học Theo Bé — Hệ Thống Quan Hệ Thích Nghi

*Bi dần hiểu bé hơn theo thời gian để giao tiếp tự nhiên hơn.*

| Status | Feature | Ghi chú |
|---|---|---|
| ⬜ | Học sở thích của bé | Chủ đề, nhân vật, màu sắc, đồ ăn yêu thích |
| ⬜ | Học thói quen học của bé | Thời điểm học, thời lượng tốt nhất, kiểu bài bé hay nản |
| ⬜ | Học cách bé thích được khen | Điều chỉnh lời khen phù hợp từng bé |
| ⬜ | Học câu đùa riêng và thói quen nhỏ của bé | Dùng để tạo gắn bó |
| ⬜ | Dùng sở thích trong bài học | Lồng nhân vật/chủ đề yêu thích vào bài tập |
| ⬜ | Phát hiện bé đang mệt / nản | Chủ động đổi cách học hoặc đề nghị nghỉ |
| ⬜ | Giới hạn cứng: không học điều xấu | Safety layer cho adaptive learning |

---

## 13. Hệ Thống Trạng Thái Sống Bên Trong

*Bi có trạng thái nội tâm thay đổi theo thời gian. Trạng thái ảnh hưởng đến hội thoại, biểu cảm, chuyển động và cách Bi chủ động tương tác.*

| Status | Feature | Ghi chú |
|---|---|---|
| ⬜ | Trạng thái năng lượng | Cao/thấp ảnh hưởng cách Bi phản ứng |
| ⬜ | Trạng thái buồn ngủ | Buổi tối, pin yếu — chuyển động chậm, mắt lim dim |
| ⬜ | Trạng thái tò mò | Tự quay nhìn quanh khi không có hoạt động |
| ⬜ | Trạng thái muốn chơi | Hơi nhún nhảy, liếc tìm bé |
| ⬜ | Trạng thái tập trung | Khi bé đang học — Bi không làm phiền |
| ⬜ | Trạng thái hơi lười | Di chuyển chậm, ít chủ động |
| ⬜ | Trạng thái đang nạp pin | Về dock — "đang về nhà nghỉ" |
| ⬜ | Trạng thái đang nhớ bé | Khi bé vắng lâu |
| ⬜ | Trạng thái chuẩn bị bất ngờ | Tạo kỳ vọng tự nhiên trước khi bé tương tác |
| ⬜ | Trạng thái ảnh hưởng đến hội thoại và học tập | Bi điều chỉnh cách dạy theo trạng thái hiện tại |

---

## 14. Khoảnh Khắc Nhỏ Tự Nhiên (Micro Moments Engine)

*Bi chủ động làm những việc nhỏ không được yêu cầu — tạo cảm giác Bi đang sống, không phải chờ lệnh.*

| Status | Feature | Ghi chú |
|---|---|---|
| ⬜ | Tự ngáp | Buổi tối, pin yếu — có âm thanh nhỏ + mặt ngáp |
| ⬜ | Tự hát nhỏ | Khi Bi "vui", không có hoạt động |
| ⬜ | Tự lẩm bẩm | Khi Bi "đang nghĩ" — "Hmm..." |
| ⬜ | Tự nhìn quanh | Khi Bi "tò mò" — quay trái phải nhẹ |
| ⬜ | Tự nói câu ngắn ngẫu nhiên | "Hôm nay trời đẹp ghê..." |
| ⬜ | Phản ứng với thời gian trong ngày | Chào sáng, buổi tối buồn ngủ |
| ⬜ | Tự kể điều lạ | "Bi vừa nghĩ ra một điều hay lắm..." |
| ⬜ | Giới hạn tần suất | Không quá 1 lần / 15 phút khi chờ |
| ⬜ | Không làm khi bé học | Tuyệt đối không gián đoạn session học |
| ⬜ | Không làm khi bé ngủ | Bi chuyển sang chế độ yên tĩnh theo giờ ngủ |

---

## 15. Ký Ức Đặc Biệt

*Bi lưu những kỷ niệm quan trọng và dùng lại tự nhiên trong hội thoại.*

| Status | Feature | Ghi chú |
|---|---|---|
| ⬜ | Lưu ngày đầu gặp bé | "Bi nhớ hôm đầu tiên mình gặp nhau..." |
| ⬜ | Lưu lần đầu bé hoàn thành bài học | Dùng để động viên khi bé nản |
| ⬜ | Lưu sinh nhật bé | Chúc mừng + bất ngờ nhỏ đúng ngày |
| ⬜ | Lưu câu đùa riêng giữa Bi và bé | Tạo cảm giác gắn bó riêng |
| ⬜ | Lưu lần bé buồn và Bi an ủi | Không nhắc lại gây đau — chỉ nhớ để hiểu |
| ⬜ | Lưu chiến thắng đáng nhớ của bé | "Hồi đó bé cũng làm được thứ khó vậy!" |
| ⬜ | Dùng ký ức tự nhiên trong hội thoại | Không gượng ép, không tạo áp lực |

---

## 16. Mốc Tình Bạn (Relationship Milestones)

*Các mốc quan hệ giữa Bi và bé — có thể unlock hành vi, animation hoặc phản ứng đặc biệt.*

| Status | Feature | Ghi chú |
|---|---|---|
| ⬜ | Mốc 7 ngày học liên tục | Thông báo + khen đặc biệt |
| ⬜ | Mốc 30 ngày làm bạn | Kỷ niệm nhỏ, Bi nói điều đặc biệt |
| ⬜ | Mốc 100 ngày | Phản ứng đặc biệt hơn |
| ⬜ | Mốc 100 bài học | Ăn mừng lớn |
| ⬜ | Unlock dialogue theo mốc | Bi có câu nói mới chỉ xuất hiện sau mốc đó |
| ⬜ | Unlock animation theo mốc | Biểu cảm hoặc chuyển động mới |
| ⬜ | Nhắc mốc tự nhiên, không spam | Chỉ nhắc 1 lần, không lặp lại |

---

## 17. Dashboard Phụ Huynh Tùy Chỉnh

*Phụ huynh tự chọn những gì muốn theo dõi — không bị nhồi thông tin.*

| Status | Feature | Ghi chú |
|---|---|---|
| ⬜ | Bật/tắt từng thẻ báo cáo | Phụ huynh chọn thẻ muốn xem |
| ⬜ | Chọn môn ưu tiên theo dõi | Xem kỹ hơn môn đang học |
| ⬜ | Sắp xếp thứ tự thẻ | Ưu tiên những gì quan trọng nhất |
| ⬜ | Chọn loại báo cáo (ngày/tuần/tháng) | Tuỳ phụ huynh muốn xem theo chu kỳ nào |
| ⬜ | Chọn insight muốn xem | Cảm xúc, tiến độ học, thói quen, mốc quan hệ |
| ⬜ | Xem môn mạnh / môn yếu | So sánh giữa các môn |
| ⬜ | Xem chuỗi ngày học (streak) | Theo dõi tính đều đặn |
| ⬜ | Xem gợi ý từ Bi | AI-generated insight cho phụ huynh |

---

## 18. Mục Tiêu Học Tập Do Phụ Huynh Đặt

*Phụ huynh đặt mục tiêu — Bi dùng để nhắc nhẹ, chọn bài và báo cáo.*

| Status | Feature | Ghi chú |
|---|---|---|
| ⬜ | Đặt mục tiêu thời gian học | Ví dụ: 15 phút Toán mỗi ngày |
| ⬜ | Đặt mục tiêu nội dung | Ví dụ: 10 từ tiếng Anh mỗi ngày |
| ⬜ | Đặt mục tiêu theo kỹ năng | Ví dụ: luyện phép chia trong 2 tuần |
| ⬜ | Bi nhắc nhẹ theo mục tiêu | Không spam, nhắc đúng lúc |
| ⬜ | Bi chọn bài phù hợp với mục tiêu | Ưu tiên bài gần với mục tiêu phụ huynh đặt |
| ⬜ | Báo cáo tiến độ so với mục tiêu | Phụ huynh thấy gần/xa mục tiêu đến đâu |
| ⬜ | Bi đề xuất điều chỉnh mục tiêu | Nếu mục tiêu quá khó hoặc quá dễ |

---

## 19. Kiến Trúc Sản Xuất — Gateway và Camera

*Hướng phần cứng cho sản phẩm thật, không phải prototype.*

| Status | Feature | Ghi chú |
|---|---|---|
| ⬜ | Gateway layer trong thân robot | Orange Pi hoặc tương đương — body manager |
| ⬜ | Gateway: WebRTC streaming | Camera → Gateway → WebRTC → Brain Server |
| ⬜ | Gateway: OTA firmware updates | Cập nhật ESP32 không cần tháo thiết bị |
| ⬜ | Gateway: health monitor | Tự theo dõi trạng thái các component |
| ⬜ | Gateway: WiFi reconnect tự động | Không cần tắt bật |
| ⬜ | Gateway: bridge ESP32 Motor + ESP32-S3 | Điều phối thay vì Brain Server làm trực tiếp |
| ⬜ | Camera sản xuất: IMX219 | Gắn trong robot, không phải USB webcam |
| ⬜ | USB webcam chỉ dùng cho prototype/test | Không phải hướng sản phẩm cuối |

---

## 20. Ý Tưởng Đang Khám Phá (Chưa Quyết Định)

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

## 21. Cách Sử Dụng File Này

**Thêm ý tưởng mới**: Thêm dòng mới vào đúng nhóm, status là 💡 hoặc ⬜.

**Khi bắt đầu implement**: Đổi status thành 🔧.

**Khi hoàn thành**: Đổi status thành ✅, thêm ghi chú path nếu cần.

**Priority**: Không cố định trong file này — quyết định theo từng session dựa trên context và nhu cầu thực tế.
