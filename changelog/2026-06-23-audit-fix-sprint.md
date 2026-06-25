# Audit Fix Sprint — 2026-06-23

## Summary

Fix 23/30 issues từ Claude Ultra Audit Loop Round 34. Toàn bộ Phase 01 (Security & Safety), Phase 02 (Correctness & Resources), và Phase 03 (Low Priority Cleanup) đã được implement. 6 issues còn lại là Firmware/Hardware (deferred — cần hardware thật).

Baseline sau fix: `python3 tests/run_tests.py` — 13 PASS, 6 FAIL (6 fail do thiếu optional libs cv2/edge_tts/sounddevice/dotenv/chromadb trong môi trường này, không liên quan đến code thay đổi).

---

## Phase 01 — Security & Safety (9 fixes)

### C1 — `/api/motor/register` thêm auth + IP validation
**File:** `src/api/routers/wifi_router.py:17`
- Thêm `Depends(get_current_user)` vào `motor_register`.
- Thêm helper `_is_private_ip()` — reject public IP, chỉ cho phép LAN (10.x, 172.16.x, 192.168.x, 127.x).

### H-NEW-1 — `/api/status` thêm auth + family scope
**File:** `src/api/routers/control_router.py:641`
- Thêm `Depends(get_current_user)` + `_require_family`.
- `get_total_stars()` gọi với `family_id` — không leak cross-family data.
- Xóa `rag_stats` và `notifier_stats` khỏi response (không scope được, không cần expose).

### H-NEW-2 — Xóa raw wifi passthrough trong WS
**File:** `src/api/routers/streaming_router.py:116`
- Xóa `elif msg.get("type") == "wifi"` block — không còn path cho arbitrary `_send_raw()`.

### H-NEW-3 — `/ws type=motor` clamp `duration_ms` ≤ 5000 ms
**File:** `src/api/routers/streaming_router.py:94`
- Thêm `_MAX_DURATION_MS = 5000` (mirrors `motor_router.py`).
- `duration_ms = min(int(msg.get("duration_ms", 800)), _MAX_DURATION_MS)`.

### M-NEW-5 — `safety_filter.py` diacritic normalization
**File:** `src/safety/safety_filter.py`
- Tách patterns thành 2 nhóm:
  - `_SENSITIVE_PATTERNS_VI_ACCENTED`: có dấu → chỉ match text gốc (tránh bắn→ban collision).
  - `_SENSITIVE_PATTERNS_NORM_ONLY`: không dấu + English → match trên `normalize_vi(text)`.
- Thêm English terms: kill, weapon, shoot, murder, suicide, terrorism, etc.
- Bắt được: `"tu tu"`, `"cat tay"`, `"giet nguoi"` (không dấu), `"tự tử"`, `"cắt tay"` (có dấu).

### L-NEW-5 — Safety blacklist không còn substitute từ chức năng phổ biến
**File:** `src/safety/safety_filter.py:26`
- Xóa `"không được"`, `"tệ"`, `"thất bại"` khỏi blacklist.
- Giữ lại chỉ từ xúc phạm thật sự: ngu ngốc, xấu xa, ngu, dốt, ngốc, khùng, điên.

### M-NEW-6 — `story_engine` apply SafetyFilter + ManipulationGuard
**File:** `src/entertainment/story_engine.py:134`
- `tell_personalized_story()` giờ run `SafetyFilter.check()` + `ManipulationGuard.check_llm_output()` trên LLM content trước khi return.

### L-NEW-6 — Trailing-buffer flush thêm ManipulationGuard
**File:** `src/main.py:637, 887`
- Trailing-buffer branch trong cả text mode và voice mode giờ apply `self._manip.check_llm_output()` (mirror per-sentence path).

### L1 — `/api/wifi/status` thêm auth
**File:** `src/api/routers/wifi_router.py:53`
- Thêm `Depends(get_current_user)`.

### L2 — `/api/mom/status` thêm auth
**File:** `src/api/routers/streaming_router.py:222`
- Thêm `Depends(get_current_user)`, xóa comment "không cần auth".

---

## Phase 02 — Correctness & Resources (5 fixes)

### M-NEW-7 — Provider streaming responses đảm bảo đóng
**File:** `src/ai/ai_engine.py`
- `_stream_openai_compat`: thêm `try/finally: resp.close()` bao quanh `iter_lines()`. Close sớm khi 4xx.
- `_stream_gemini`: tương tự.
- `_stream_cloudflare`: dùng `with requests.post(...) as resp:` (non-streaming).

### M1 + L8 — Motor reconnect lock + exponential backoff
**File:** `src/motion/motor_controller.py:48, 68`
- `_try_connect_ws()`: connect attempts chạy NGOÀI lock; chỉ lock khi swap socket. Giảm worst-case từ ~19s xuống <1ms.
- `_start_reconnect_thread()`: thêm exponential backoff (10s → 20s → 40s → max 120s), reset về 10s khi connect thành công.

### M2 — `_chunk_counter` thread-safe
**File:** `src/main.py`
- Thêm `self._chunk_lock = threading.Lock()` và method `_next_chunk_idx()`.
- Tất cả nơi dùng `chunk_index=self._chunk_counter; self._chunk_counter += 1` được replace bằng `chunk_index=self._next_chunk_idx()`.
- Xóa `self._chunk_counter = 0` reset per-turn — counter giờ monotonically increasing, không bao giờ collision.

### M3 — `wifi_add` inject-safe với `json.dumps`
**File:** `src/api/routers/wifi_router.py:83`
- `motor._send_raw("add_wifi:" + json.dumps({"ssid": ssid, "password": password}))` thay cho f-string.

---

## Phase 03 — Low Priority Cleanup (9 fixes)

### M4 — `/health` DB liveness probe
**File:** `src/api/routers/ops_router.py:181`
- Execute `SELECT 1` trong `get_db_connection()`; trả về 503 nếu DB fail.

### M-NEW-1 — `/auth/refresh` rate limiting
**File:** `src/api/routers/auth_router.py:310`
- Thêm per-IP rate limit dùng `login_attempts` table với key `"refresh:{ip}"`.
- Limit: 20 attempts/15 phút window → lock 15 phút.

### L-NEW-1 — `change-password` TOCTOU fix
**File:** `src/api/routers/auth_router.py:463`
- Password check và fail counter update giờ nằm trong cùng 1 DB connection/transaction.

### L-NEW-2 — Wake-word model hash verify trước pickle.load
**File:** `src/wakeword/wakeword_service.py:344`
- Nếu tồn tại `.sha256` sidecar, verify SHA-256 hash trước khi `pickle.load()`. Reject nếu mismatch.

### L-NEW-3 — `/static` chỉ serve `dist/`
**File:** `src/api/server.py:88`
- Mount `/static` trên `dist/` nếu tồn tại; skip nếu chưa build (không expose source tree).

### L-NEW-4 — `ssl/` gitignore (verified already OK)
- `ssl/` đã có trong `.gitignore`, không có file tracked. Không cần thay đổi.

### L6 — Xóa dead `WAKEWORD_ENABLED = False` constant
**File:** `src/audio/input/ear_stt.py:88`
- Xóa constant và `global WAKEWORD_ENABLED` trong `listen_for_wakeword()`.

### L7 — CI action versions bump
**File:** `.github/workflows/test.yml`
- `actions/checkout@v3` → `@v4`, `setup-python@v4` → `@v5`.

### L9 — `setup_logging()` race fix
**File:** `src/infrastructure/logging/log_config.py`
- Thêm `_setup_lock = threading.Lock()` và bao toàn bộ handler-setup trong `with _setup_lock:`.

---

## Deferred (6 issues — cần hardware)

- **H1**: Firmware blocking `delay()` — cần ESP32 hardware
- **M-NEW-3**: WakeWordService clear-before-wait race — cần WAKEWORD_ENABLED=true để verify
- **M-NEW-4**: Mic double-open WDM-KS — cần Windows hardware
- **L3**: Firmware motorStop before restart — cần ESP32 hardware
- **L4**: Mic-test firmware silent hang — cần ESP32 hardware
- **L5**: Mic-test I2S write return ignored — cần ESP32 hardware
