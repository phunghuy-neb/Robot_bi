# API_CONTRACT.md — Robot Bi API Reference

> Phiên bản: 1.0 | Cập nhật: 2026-05-15
> Source of truth cho tất cả REST endpoints và WebSocket events.
> Tất cả endpoints (trừ whitelist) đều yêu cầu JWT Bearer token.
> Cập nhật file này khi thêm/xóa/thay đổi bất kỳ endpoint nào.

---

## Authentication

### Token flow
```
POST /auth/login/v2          → { access_token, refresh_token }
Authorization: Bearer <access_token>   ← gửi kèm mọi request
POST /auth/refresh           → { access_token, refresh_token }  ← khi access hết hạn
POST /api/auth/logout        → { ok: true }
```

### Whitelist (không cần token)
`/health`, `/`, `/static/*`, `/api/status`, `/api/mom/status`,
`/api/auth/login`, `/api/auth/logout`, `/auth/register`, `/auth/login/v2`, `/auth/refresh`

### WebSocket auth
Query param: `?token=<access_token>` hoặc `?auth=<access_token>`

### Camera auth
Header `Authorization: Bearer <token>` hoặc query param `?auth=<token>`

---

## 1. Auth — `/api/auth/` và `/auth/`

| Method | Path | Body | Response | Ghi chú |
|---|---|---|---|---|
| POST | `/api/auth/login` | `{pin}` | `{ok, token, family_name}` | Legacy PIN login |
| POST | `/api/auth/logout` | — | `{ok}` | Logout (no auth required) |
| POST | `/auth/register` | `{username, password, family_name}` | `{ok, user_id}` | Tạo tài khoản mới |
| POST | `/auth/login/v2` | `{username, password}` | `{access_token, refresh_token, token_type, user}` | Username/password login |
| POST | `/auth/refresh` | `{refresh_token}` | `{access_token, refresh_token, token_type}` | Rotate refresh token |
| GET | `/auth/me` | — | `{user_id, username, family_name, is_admin}` | Thông tin user hiện tại |
| POST | `/auth/change-password` | `{current_password, new_password}` | `{ok}` | Đổi mật khẩu |

**Rate limit**: `/api/auth/login` — 5 lần sai → khóa 15 phút theo IP

---

## 2. Admin — `/api/admin/`

> Yêu cầu `is_admin = true`

| Method | Path | Body / Query | Response |
|---|---|---|---|
| POST | `/api/admin/families` | `{family_id, display_name?}` | `{family_id, display_name, created_at}` |
| GET | `/api/admin/families` | — | `{families: [...]}` |
| DELETE | `/api/admin/families/{family_id}` | — | `{ok, family_id}` |
| GET | `/api/admin/logs` | `?level&component&since&limit&offset` | `{logs, total, limit, offset}` |

**Lưu ý**: Không thể xóa family của admin đang đăng nhập.

---

## 3. Analytics — `/api/analytics/`

| Method | Path | Response |
|---|---|---|
| GET | `/api/analytics/weekly` | `{family_id, period_days, conversations, turns, tasks_completed, emotion, learning, hours, words, stories, avg_emotion, daily_activity}` |
| GET | `/api/analytics/daily` | `{family_id, date, conversations, events, tasks_completed}` |
| GET | `/api/clips/list` | `{clips: [{event_id, timestamp, type, message, clip_path}]}` |
| DELETE | `/api/clips/{clip_id}` | `{ok}` |

**`daily_activity`**: Array 24 items `[{hour: 0-23, count: N}]`

---

## 4. Conversations — `/api/conversations/`

| Method | Path | Query / Body | Response |
|---|---|---|---|
| GET | `/api/conversations` | `?limit&offset` | `{conversations: [{session_id, title, started_at, ended_at, turn_count}], total}` |
| GET | `/api/conversations/homework` | `?limit&offset` | `{sessions: [...], total}` |
| GET | `/api/conversations/{session_id}` | — | `{session: {...}, turns: [{turn_id, role, content, timestamp}]}` |
| DELETE | `/api/conversations/{session_id}` | — | `{ok}` |
| POST | `/api/conversations/{session_id}/homework` | — | `{ok}` |
| GET | `/api/conversations/parent` | `?limit&offset` | `{sessions: [...], total}` |
| GET | `/api/conversations/parent/{session_id}` | — | `{session: {...}, messages: [...]}` |
| POST | `/api/conversations/parent/messages` | `{session_id?, role, content}` | `{session, messages}` |

**`role`** trong parent chat: `"parent"` hoặc `"bi"`

---

## 5. Education — `/api/education/`

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/education/flashcard/start` | `{subject, topic, language, difficulty}` | Session info |
| GET | `/api/education/flashcard/next` | — | `{card_id, front, back, image_url?, ...}` |
| POST | `/api/education/flashcard/answer` | `{card_id, is_correct, pronunciation_score?}` | `{correct, score, ...}` |
| POST | `/api/education/flashcard/end` | — | Session summary |
| GET | `/api/education/summary` | — | `{streak, words_learned, math_solved, questions_answered, subject_progress}` |
| GET | `/api/education/vocabulary` | — | `{words: [...]}` |
| GET | `/api/education/schedule` | — | `{schedule: {day: {subject, time}}}` |
| POST | `/api/education/schedule` | `{schedule}` hoặc `{day, subject, time}` | `{ok, schedule}` |

**`subject_progress`**: `{english: 0-100, math: 0-100, science: 0-100}`

---

## 6. Emotion — `/api/emotion/`

| Method | Path | Query | Response |
|---|---|---|---|
| GET | `/api/emotion/today` | — | `{dominant, counts: {happy, sad, neutral, stressed}, timestamp}` |
| GET | `/api/emotion/summary` | — | `{days: [{date, dominant, counts}], alert, alert_message}` |
| GET | `/api/emotion/monthly` | `?month=YYYY-MM` | `{month, breakdown: {...}}` |
| GET | `/api/emotions/monthly` | `?month=YYYY-MM` | (alias của endpoint trên) |

**`alert`**: true nếu bé buồn/stressed 3+ ngày liên tiếp

---

## 7. Games và Entertainment — `/api/game/`, `/api/entertainment/`, `/api/games/`

### Game metadata
| Method | Path | Query | Response |
|---|---|---|---|
| GET | `/api/entertainment/radio` | `?language&min_age&max_age&enabled_only&child_id` | `{items, channels, total}` |
| GET | `/api/entertainment/videos` | `?language&min_age&max_age&enabled_only&child_id` | `{items, videos, total}` |
| GET | `/api/games/interactive` | `?language&min_age&max_age&enabled_only&child_id` | `{items, games, total}` |

### Word Quiz
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/game/word-quiz/start` | `{difficulty}` | `{game_id, total_questions, ...}` |
| GET | `/api/game/word-quiz/question` | — | `{question, options, question_number}` |
| POST | `/api/game/word-quiz/answer` | `{answer}` | `{correct, score, next_available}` |
| POST | `/api/game/word-quiz/end` | — | `{total_score, correct, incorrect}` |

### Voice Quiz
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/game/voice-quiz/start` | — | `{game_id, ...}` |
| GET | `/api/game/voice-quiz/riddle` | — | `{riddle, hint?, ...}` |
| POST | `/api/game/voice-quiz/answer` | `{spoken}` | `{correct, answer, score}` |

### Scores
| Method | Path | Response |
|---|---|---|
| GET | `/api/game/scores` | `{word_quiz: [...], voice_quiz: [], math_quiz: []}` |

---

## 8. Motor — `/api/motor/`

> Tất cả motor commands có safety cap: `duration_ms` tối đa 5000ms

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/motor/forward` | `{speed?, duration_ms?}` | `{ok}` |
| POST | `/api/motor/backward` | `{speed?, duration_ms?}` | `{ok}` |
| POST | `/api/motor/left` | `{degrees?}` | `{ok}` |
| POST | `/api/motor/right` | `{degrees?}` | `{ok}` |
| POST | `/api/motor/stop` | — | `{ok}` |
| POST | `/api/motor/home` | — | `{ok}` |
| POST | `/api/motor/drive` | `{vx: -100..100, omega: -100..100}` | `{ok}` |
| POST | `/api/motor/joystick` | `{left: -100..100, right: -100..100}` | `{ok}` |
| POST | `/api/motor/spin` | `{speed?, duration_ms?}` | `{ok}` |
| GET | `/api/motor/status` | — | `{mode, connected, ws_url, ...}` |
| POST | `/api/motor/register` | `{ip, port?}` | `{ok, message, motor_mode}` |

**Default values**: `speed=50`, `duration_ms=1000`, `degrees=90`

---

## 9. Music — `/api/music/`

| Method | Path | Body / Query | Response |
|---|---|---|---|
| POST | `/api/music/play` | `{track_id?, category?}` | Player state |
| POST | `/api/music/stop` | — | `{ok}` |
| POST | `/api/music/pause` | — | `{ok}` |
| POST | `/api/music/next` | — | `{status, action}` |
| POST | `/api/music/previous` | — | `{status, action}` |
| POST | `/api/music/shuffle` | — | `{status, shuffle}` |
| POST | `/api/music/repeat` | — | `{status, repeat}` |
| POST | `/api/music/volume` | `{level: 0-100}` | `{ok, volume}` |
| GET | `/api/music/status` | — | `{playing, track, volume, shuffle, repeat}` |
| GET | `/api/music/playlist` | `?category=lullabies` | `{category, tracks: [...]}` |
| POST | `/api/music/lullaby` | `{fade_minutes?}` | Lullaby session info |

**Categories**: `lullabies`, `vietnamese`, `english`

---

## 10. Ops — Health, Camera, Dashboard

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/health` | ❌ Không cần | `{status: "ok"}` |
| GET | `/` | ❌ Không cần | HTML — Parent App hoặc 503 |
| GET | `/api/camera` | ✅ Token qua `?auth=` hoặc Header | MJPEG stream |

**Camera MJPEG**: `multipart/x-mixed-replace;boundary=frame`
Dùng trong `<img src="/api/camera?auth=TOKEN">` hoặc `<video>`.

---

## 11. Persona — `/api/persona/`

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/persona` | — | `{persona: {name, voice_gender, personality, ...}}` |
| POST | `/api/persona/update` | `{name?, voice_gender?, personality?, ...}` | `{ok, persona}` |

---

## 12. Stories — `/api/story/`

| Method | Path | Body / Query | Response |
|---|---|---|---|
| GET | `/api/story/list` | `?category` | `{stories: [{story_id, title, category, ...}]}` |
| POST | `/api/story/tell` | `{story_id?, custom_request?, character_name?}` | `{title, content, ...}` |
| POST | `/api/story/personalized` | `{child_name?, interests?}` | Story content |
| POST | `/api/story/bedtime` | — | Bedtime story content |

---

## 13. Streaming — WebSocket và Mom Talk

### WebSocket Events (`/ws?token=TOKEN`)

**Kết nối**: Sau khi connect, server push các unread events (tối đa 20).

**Events server → client**:
```json
{"type": "cry_detected", "family_id": "...", "timestamp": "..."}
{"type": "motion_detected", "family_id": "...", "timestamp": "..."}
{"type": "homework", "session_id": "...", "family_id": "..."}
{"type": "robot_status", "status": "online|offline|connecting"}
{"type": "notification", "message": "...", "level": "info|warning|alert"}
```

**Commands client → server** (qua WebSocket):
```json
{"type": "motor", "cmd": "forward", "speed": 50, "duration_ms": 800}
{"type": "motor", "cmd": "drive", "vx": 50, "omega": 0}
{"type": "motor", "cmd": "stop"}
{"type": "wifi", "cmd": "add_wifi:{...}"}
```

### Audio Monitor WebSocket (`/api/audio/stream?token=TOKEN`)
- Server → Client: PCM 16-bit LE, 16kHz, mono (binary frames)
- Một chiều: server stream audio mic phòng về browser

### Mom Talk REST
| Method | Path | Auth | Response |
|---|---|---|---|
| POST | `/api/mom/start` | ✅ | `{status: "mom_talking", message}` |
| POST | `/api/mom/stop` | ✅ | `{status: "bi_active", message}` |
| GET | `/api/mom/status` | ❌ | `{mom_talking: bool}` |

### Mom Audio WebSocket (`/api/mom/audio?token=TOKEN`)
- Client → Server: PCM float32, 16000Hz, mono (Web Audio API format)
- Server phát qua loa robot (pygame Channel 7)
- Chỉ phát khi `mom_talking = true`

---

## 14. Video Call — `/api/video/`

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/video/call/start` | — | `{call_id, family_id, caller_name, started_at}` |
| POST | `/api/video/call/end` | `{call_id}` | `{ok}` |
| GET | `/api/video/contacts` | — | `{contacts: [{name, ...}]}` |
| POST | `/api/video/contacts` | `{name}` | Contact object |
| GET | `/api/video/history` | — | `{history: []}` |

---

## 15. WebRTC — `/api/webrtc/`

| Method | Path | Body | Response | Ghi chú |
|---|---|---|---|---|
| POST | `/api/webrtc/offer` | `{sdp, type}` | `{sdp, type}` — SDP answer | 503 nếu aiortc không có |
| POST | `/api/webrtc/close` | — | `{closed: 0\|1}` | Đóng PC của user hiện tại |

**Fallback**: Nếu WebRTC không khả dụng (Windows dev), dùng MJPEG `/api/camera`.

---

## 16. WiFi — `/api/wifi/`

| Method | Path | Body | Auth | Response |
|---|---|---|---|---|
| POST | `/api/motor/register` | `{ip, port?}` | ❌ | `{ok, message, motor_mode}` |
| GET | `/api/wifi/status` | — | ❌ | `{ok, connected, ip, port, ssid, rssi, ...}` |
| POST | `/api/wifi/add` | `{ssid, password}` | ✅ | `{ok, message}` |

---

## 17. Control — `/api/` (core endpoints)

> Các endpoints nằm trong `control_router.py` — phần core của hệ thống

### Robot Status và Device
| Method | Path | Response |
|---|---|---|
| GET | `/api/status` | `{status, uptime, version}` |
| GET | `/api/robot/location` | `{room, location, ...}` |
| GET | `/api/device/connection-qr` | `{url, qr_data}` |

### Events
| Method | Path | Query / Body | Response |
|---|---|---|---|
| GET | `/api/events` | `?type&limit&offset&since&until` | `{events: [...], total}` |
| POST | `/api/events/{event_id}/notes` | `{note}` | `{ok}` |

### Puppet
| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/puppet` | `{text}` | `{ok, queued}` |

### Tasks và Stars
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/tasks` | — | `{tasks: [{task_id, name, remind_time, completed_today, stars}]}` |
| POST | `/api/tasks` | `{name, remind_time?, stars?}` | Task object |
| POST | `/api/tasks/{task_id}/complete` | — | `{ok, stars}` |
| DELETE | `/api/tasks/{task_id}` | — | `{ok}` |
| GET | `/api/stars` | — | `{total_stars, today_stars}` |

### RAG Memory
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/memory` | — | `{memories: [...]}` |
| POST | `/api/memory` | `{text, metadata?}` | `{ok, memory_id}` |
| DELETE | `/api/memory/{memory_id}` | — | `{ok}` |
| DELETE | `/api/memory/clear` | — | `{ok, cleared}` |
| GET | `/api/memory/export` | — | JSON export |

### Children và Settings
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/children` | — | `{children: [...]}` |
| GET | `/api/settings/age-filter` | — | `{min_age, max_age}` |
| POST | `/api/settings/age-filter` | `{min_age, max_age}` | `{ok}` |
| GET | `/api/settings/time-limits` | — | `{daily_limit_minutes, ...}` |
| POST | `/api/settings/time-limits` | `{daily_limit_minutes}` | `{ok}` |
| GET | `/api/settings/sleep` | — | `{sleep_time, wake_time}` |
| POST | `/api/settings/sleep` | `{sleep_time, wake_time}` | `{ok}` |
| GET | `/api/settings/notifications` | — | `{...settings}` |
| POST | `/api/settings/notifications` | `{...settings}` | `{ok}` |
| GET | `/api/usage/today` | — | `{minutes_used, limit, remaining}` |

### Reports
| Method | Path | Query | Response |
|---|---|---|---|
| GET | `/api/reports/export` | `?format=json\|csv&since&until` | Report data |

---

## Error Format

```json
{
  "detail": "Mô tả lỗi bằng tiếng Việt hoặc tiếng Anh"
}
```

| HTTP Code | Ý nghĩa |
|---|---|
| 400 | Bad request — sai tham số |
| 401 | Unauthorized — thiếu hoặc sai token |
| 403 | Forbidden — không có quyền (thiếu family, cần admin) |
| 404 | Not found |
| 409 | Conflict — đã tồn tại |
| 422 | Validation error — sai format |
| 500 | Internal server error |
| 503 | Service unavailable (ví dụ: WebRTC không có aiortc) |
