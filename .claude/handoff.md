# Handoff - Robot Bi

> Current-state handoff only. Historical details belong in `changelog/`.
> Older "Last Completed Task" entries (pre-2026-06-24) archived in `changelog/2026-06-24-handoff-archive.md`.

## In Progress / Stopped Here

> THE resume anchor. When opening a new chat, read this first. Keep it honest and short:
> what is mid-flight, where it stopped, what is next. Clear it when the work lands.
> One opener covers everything: "Đọc PROJECT.md và .claude/handoff.md rồi tiếp tục."
> If a Spec Kit feature is active, the **Active spec** line below points to its folder —
> reading this file then leads straight to `tasks.md` (the real progress tracker).

- 🧹 **REPO CLEANUP + SKILL (2026-06-25, ✅ ĐÃ MERGE + PUSH lên `origin/main` = `14aeec6`)**:
  - `chore/repo-cleanup`: `900b3ce` (untrack ngrok.exe 32MB, xóa scratch_generate_games.py,
    run_tests.py tự quét rác `runtime/_*_test_db_*`/`_debug_rag_tmp*` lúc khởi động) +
    `70ebfc6` (gỡ `notebooklm_export/` khỏi git + gitignore, xóa `.env.bak`). Test **716/716 PASS**.
    Đã dọn ~3.4GB rác `runtime/` trên đĩa.
  - `chore/lean-code-discipline`: `9793a62` thêm mục "Lean Code — thang quyết định 7 bậc" vào
    `robot-bi-dev/SKILL.md` (Protected Fixes & child-safety override). Chỉ sửa skill, không đụng code.
  - Đã merge cả 2 vào `main` (ff `main`=`4c19a84` trước) + **push `origin/main`=`14aeec6`**. Suite **716/716 PASS**.
    Branch `chore/repo-cleanup` + `chore/lean-code-discipline` đã merge xong (có thể xóa local nếu muốn).
- 🚀 **ĐÃ MERGE LÊN MAIN (2026-06-25)**: PR #2 merged → `main` HEAD `4c19a84` (merge commit, giữ nguyên
  141 commit). `origin/main` nay chứa toàn bộ work. Branch `003-web-search-integration` đã land. Việc mới
  nên nhánh từ `main`. CÒN LẠI: phần cứng + kiểm thử thiết bị thật (xem cuối resume anchor).
- 👉 **RESUME NGAY TẠI ĐÂY (2026-06-24)**: **Admin UI ĐÃ XONG TOÀN BỘ 6 PHASE** —
  Phase 1/2/3 (`8cd0cd5`), Phase 4 Kênh YouTube (`363a6ce`), Phase 5 An toàn (`0dcba21`),
  **Phase 6** (`27994b3`).
  Cả 8 mục sidebar AdminApp nay đều `ready`. Test `tests/run_tests.py` (chạy bằng `.venv/bin/python`)
  = **716/716 PASS**; Vite build OK. PROJECT.md đã dọn + sync (`4b3fc56`); `.gitignore` đã chuẩn hóa LF
  (`9ab8ae5`). **Working tree SẠCH HOÀN TOÀN** (không còn file dirty). **LƯU Ý MÔI TRƯỜNG**: dep trong `.venv/`
  — chạy test bằng `.venv/bin/python tests/run_tests.py` (python3 hệ thống KHÔNG có fastapi/chromadb).
  **TOÀN BỘ BACKLOG NON-HARDWARE ĐÃ XONG** (user duyệt làm hết nhóm 2, tự chọn phương án an toàn):
  Knowledge UI Parent App ✅, TOEIC audio server ✅, lọc title YouTube ✅, Persona admin-global ✅,
  gỡ mock fallback ✅, **Stage 2 Special Memories ✅** (user bật đèn xanh), **Radio Browser ✅** (helper
  admin tìm đài), **TTS offline ✅** (công tắc), **Stage 2 proactive (due_today) ✅**, **CI bump ✅**,
  **FIX bug từ review loop round 34/35/36 ✅** (H-NEW-4 + 5 issue khác — xem bullet bên dưới).
  **CÒN LẠI**: (a) PHẦN CỨNG (ESP32-S3 audio/firmware, motor/camera, wake-word mic thật); (b) vài review
  residual NHỎ đã defer có lý do (M-NEW-8 admin-log, M2 CWD audio, round-35 LOWs) + review loop mới phủ
  ~5%/554 file (còn db.py/state.py/audio/firmware/frontend chưa review sâu).
  - **Robot Display gọi Knowledge = BỎ có chủ đích**: `index.html` là màn hình MẶT robot (output-only,
    animation do runtime điều khiển), không phải nơi gõ truy vấn → tri thức đã trả qua giọng/hội thoại.
  - **Settings save stubs = không có stub thực**: settings tuổi/giờ/ngủ đã persist; phần `disabled`/
    coming-soon (lọc thiết bị, game tương tác) là placeholder cố ý.
- **Nhóm 2 backlog (2026-06-24) — ✅ DONE phiên này:**
  - **Stage 2 — Special Memories**: bảng `special_memories` (family-scoped) + helper db.py
    (list/add/delete); routes `GET/POST/DELETE /api/memories/special` trong `control_router.py` (đặt
    TRƯỚC `/{memory_id}`), POST nạp thêm vào RAG qua `add_manual_memory(source="special")` (best-effort).
    FE `components/SpecialMemories.jsx` trong JournalPage (thêm/xóa, 4 loại: birthday/milestone/favorite/
    other). Test **Group 92** (2): CRUD+cô lập, kind chuẩn hóa + thiếu title 422.
  - **Radio Browser**: `kc.radio_search()` (radio-browser.info, lọc tên qua SafetyFilter, bỏ đài thiếu
    URL, never raise) + `GET /api/admin/radio/search` (`require_admin`). FE: panel "🔎 Tìm đài" trong
    ContentAdminPage → click "Dùng" điền form radio (admin duyệt & lưu thủ công — KHÔNG phơi radio mở
    cho trẻ). Test **Group 93.1/93.2**.
  - **TTS offline**: `mouth_tts._tts_offline_only()` (env `TTS_OFFLINE`/`TTS_ENGINE=pyttsx3`) → `_generate_audio`
    short-circuit sang pyttsx3, KHÔNG đụng playback/streaming/channel (Protected Fix giữ nguyên). Thêm
    toggle `TTS_OFFLINE` vào `env_admin.TOGGLES` (needs_restart). Test **Group 93.3**.
  - Suite **698/698 PASS** (trước 693); Vite build OK; SYSTEM_MAP cập nhật.
- **Dọn backlog non-hardware (2026-06-24) — ✅ DONE phiên này:**
  - **Lọc title YouTube qua SafetyFilter** (`youtube_lessons.py`): `_title_is_safe()` (lazy SafetyFilter,
    lỗi→coi an toàn) trong `_fetch_channel` → bỏ video có tiêu đề bị chặn. Test **82.6**.
  - **Persona admin-global** (`persona_manager.py` + `admin_router.py` + FE): khóa `__global__` lưu persona
    mặc định; `_load` fallback sang `__global__` khi gia đình CHƯA cấu hình (gia đình đã tùy chỉnh giữ
    nguyên). Endpoint `GET/POST /api/admin/persona` (`require_admin`, validate qua PersonaManager.save).
    FE `pages/admin/PersonaAdminPage.jsx` + sidebar 'persona' (🤖, AdminApp 9 mục). Role = contextual,
    không có cấu hình global. Test **Group 91** (3).
  - **Gỡ mock fallback Parent App** (`api.js` + `MorePage.jsx`): radio/video/games/emotions trả dữ liệu
    THẬT (rỗng nếu chưa có), bỏ import `mockData`. MorePage thêm cờ `loaded` → rỗng-thật hiện empty state
    thay vì "đang tải" mãi (seed DB vẫn có 2 radio/2 video/2 game nên thực tế không rỗng).
  - Suite **693/693 PASS** (trước 689); Vite build OK; SYSTEM_MAP cập nhật.
- **Stage 2 proactive + CI bump + FIX theo review loop (2026-06-25) — ✅ DONE phiên này (UNCOMMITTED → commit):**
  - **Stage 2 nhắc chủ động**: `control_router` thêm `_memory_due_today()` + endpoint list special memories
    nay gắn cờ `due_today` (khớp DD/MM hôm nay) + trả `due_today` list. FE SpecialMemories: banner 🔔 +
    highlight kỷ niệm hôm nay. Test **92.3**. (Robot tự NÓI khi tới ngày = hook runtime, để sau.)
  - **CI**: `.github/workflows/test.yml` bump `actions/checkout@v4→v5` + `setup-python@v5→v6` (hết Node20 deprecated).
  - **Đọc review loop `.claude-review/` round 34/35/36** → verify trên code hiện tại → FIX bug thật:
    - **H-NEW-4 (HIGH/child-safety)**: PII advisory chạy TRƯỚC EmotionRiskDetector ở cả text+voice path
      → utterance vừa có PII vừa có tín hiệu khủng hoảng bị PII redirect nuốt, BỎ QUA crisis override +
      cảnh báo phụ huynh. **ĐÃ ĐẢO**: risk.check chạy trước pii.check ở cả 2 path. Test **94.1**.
    - **L-NEW-10 (privacy)**: text-mode chạy web search TRƯỚC PII gate → rò PII trẻ ra Tavily/Brave.
      **ĐÃ DỜI** web search xuống sau PII gate (giống voice). Test **94.2**.
    - **M-NEW-9**: `/api/eval/chat` raw LLM passthrough → **gate admin-only**. Test **94.3**.
    - **M-NEW-10**: TOEIC `feedback`/`tips` (free-text LLM cho trẻ) → lọc qua SafetyFilter. Test **94.4**.
    - **L-NEW-9**: bỏ DEBUG log nội dung `rag_context` (PII) → chỉ log độ dài.
    - **L-NEW-8**: CSV report chống formula injection (`_csv_safe`). Test **94.5**.
  - **ĐÃ XÁC MINH KHÔNG CÒN LÀ BUG**: M-NEW-5 (safety_filter đã có `_SENSITIVE_PATTERNS_NORM_ONLY` bắt
    không-dấu+English), L-NEW-5 ("không được" đã bị loại khỏi blacklist), H-NEW-1/M2/L-NEW-6 (round 36 đã
    POSSIBLY_FIXED).
  - Suite **704/704 PASS** (trước 698); Vite build OK; SYSTEM_MAP cập nhật.
- **Review THỦ CÔNG 5 file lõi (2026-06-25, "review luôn đi") — ✅ DONE phiên này (UNCOMMITTED → commit):**
  Mình giao 5 agent đọc-only (main/server, rag/ai_engine/role, db.py, knowledge_client, state/notifier),
  verify từng finding trên code thật rồi FIX bug thật:
  - **db.py `delete_family_record` (HIGH/isolation)**: bỏ sót dọn `special_memories, youtube_channels,
    exam_sessions, exam_papers, question_bank, learning_progress, learning_streaks` → orphan, gia đình
    mới trùng `family_id` kế thừa data trẻ cũ. **ĐÃ thêm vào allowlist + loop dọn**. Test 97.1.
  - **rag_manager (HIGH+MED, Protected Fix)**: `add_manual_memory` KHÔNG enforce `_MAX_MEMORIES`; prune
    xóa entry TÙY Ý không phải cũ nhất. **ĐÃ thêm `_prune_to_capacity` (xóa cũ nhất theo timestamp) +
    gọi ở mọi đường thêm + collapse-whitespace fact (anti prompt-injection)**. Test 97.6.
  - **state.py WS (HIGH/isolation)**: `broadcast` FAIL-OPEN khi thiếu family_id → gửi mọi nhà; key bằng
    `id(ws)` (id-reuse). **ĐÃ fail-closed + key bằng object WebSocket**. (connect dùng JWT family — đã ổn).
    Test 97.4.
  - **auth (HIGH/security)**: refresh token reuse → chỉ 401, không thu hồi. **ĐÃ thêm reuse-detection**:
    replay token đã xoay → `revoke_all_tokens_for_user` (bump token_version, vô hiệu cả access). Test 97.5.
  - **knowledge_client (HIGH child-safety)**: `number_fact/poem/apod/dictionary` trả text KHÔNG qua
    SafetyFilter (trái docstring). **ĐÃ bọc `_clean`** + **cache cap `_CACHE_MAX=500`** (chống OOM) +
    **không log `str(e)`** (tránh rò NASA key trong URL). Test 97.3.
  - **role_manager (MED)**: `task_goal` chèn vào system context không strip newline. **ĐÃ collapse**. Test 97.2.
  - **✅ VERIFIED ỔN (không fix)**: cô lập gia đình RAG + IDOR guard; SQL injection (db.py parameterized +
    table-name allowlist); SSRF knowledge (host hardcoded); math (mathjs remote, không eval); WS connect
    dùng JWT family; pipeline an toàn input (risk trước PII), web search sau PII, chunk lock, static mount,
    HTTPS autogen. HIGH-1 (main.py is_safe) = FAIL-SAFE vì `check()` trả refusal khi unsafe.
  - **CÒN OPEN (defer/minor)**: ConnectionManager chưa có lock thật (rủi ro thấp, 1 loop); chat transcript
    lưu đầy đủ trong `events.metadata_json` (by-design, có 500-row cap — quyết định product); main.py
    branch-on-is_safe (defense-in-depth, hiện fail-safe); puppet chưa qua ManipulationGuard (nguồn parent).
  - Suite **716/716 PASS** (trước 710); SYSTEM_MAP cập nhật.
- **Round 36 review (06:48) + FIX 2 issue mới — ✅ DONE phiên này (committed cùng đợt trước):**
  - Review loop chạy xong round 36 (vẫn parse-error nên report không merge, nhưng stdout
    `failures/round-36-…064824…stdout.txt` là bản review CHÍNH XÁC trên code hiện tại).
  - **Round 36 XÁC NHẬN 6 fix của mình ĐÚNG → POSSIBLY_FIXED**: H-NEW-1, M-NEW-1, L-NEW-1, M1, H-NEW-3, L-NEW-7.
  - **M-NEW-8 (MEDIUM/concurrency) — FIXED**: `stream_chat`/faster-whisper đồng bộ chạy trong `async def`
    handler → block event loop. Bọc `run_in_threadpool`: `eval_router` (collect), `parent_chat_router`
    (collect), `exam_router` (`_grade_toeic_sw_attempt`, `_transcribe_audio`, `_llm_generate_questions`×2).
  - **L-NEW-8 (LOW) — FIXED**: `/auth/refresh` counter rate-limit nay RESET khi refresh thành công
    (`DELETE login_attempts WHERE ip=refresh:{ip}`) → không khóa nhầm session NAT/nhiều thiết bị.
  - Test **Group 96** (2): blocking calls bọc threadpool (source guard); 22 refresh hợp lệ liên tiếp
    không bị 429. Suite **710/710 PASS** (trước 708).
  - **Coverage review: 24/554 DEEP (~4.3%)** — round 36 next priorities: `server.py` + `main.py`
    (NEEDS_RECHECK), `role_manager.py`, `rag_manager.py`, `db.py` (110KB), `knowledge_client.py` (SSRF),
    `notifier.py`, `state.py`, audio internals, firmware, frontend — đều CHƯA review sâu.
  - **CÒN OPEN nhỏ**: round-36 không thêm gì khác; round-35 LOWs (prune/quota/embed/notifier/dup) +
    L-NEW-2 (pickle wakeword) vẫn để (minor). M-NEW-8 INFO residual: chưa có `safe_stream_chat()` dùng chung.
- **FIX review wave-2 (2026-06-25, theo lệnh "sửa nốt non-hardware") — ✅ DONE phiên này (committed cùng đợt):**
  - **L-NEW-7 (an toàn trẻ)**: thêm từ KHÔNG DẤU an toàn vào `_SENSITIVE_PATTERNS_NORM_ONLY`
    (`giet, danh nhau, khieu dam, noi dung nguoi lon`) — CHỦ Ý loại `ban/bom/sung/tu dao` vì collision
    với bạn/bơm/sưng (false-positive). (Lưu ý: `bom`=bomb đã bị accented-set chặn sẵn → bơm-không-dấu
    là false-positive CŨ, ngoài phạm vi.) Test **95.1**.
  - **M1 (motor)**: `MotorController._send` nay **fast-fail** — không gọi `_try_connect_ws` inline khi giữ
    lock (tránh block ~19s nuốt lệnh `stop`); background thread reconnect. Test **95.2**.
  - **H-NEW-3 residual**: thêm `_clamp_duration()` (trần 5s) tập trung trong forward/backward/spin →
    mọi caller bị clamp, không chỉ router. Test **95.2**.
  - **M2 (CWD)**: file `voice_chunk_*` ghi vào `mouth_tts.CHUNK_DIR` (temp dir riêng), KHÔNG còn CWD;
    `main._cleanup_chunks` quét đúng dir đó (+ CWD cũ để dọn rác cũ). Test **95.3**.
  - **L-NEW-4 (SSL)**: thực ra `ssl/*.pem` **chưa từng track trong git** (tracker stale). Đã thêm
    `ssl/*.pem` vào `.gitignore` (chặn commit nhầm) + `server.py` tự sinh self-signed khi thiếu
    (giữ HTTPS-by-default cho fresh clone, dùng `generate_ssl.generate_ssl()`).
  - **round-35 L-NEW-7**: `delete_family` trả thêm cờ `rag_cleaned` để admin biết memory mồ côi. Test **95.4**.
  - **ĐÃ XÁC MINH ĐÃ FIX TỪ TRƯỚC** (tracker stale): M-NEW-1 (auth/refresh đã có rate-limit), M4
    (/health đã probe DB), L9 (setup_logging đã guard bằng lock).
  - **M-NEW-8 (admin logs free-text)**: user CHỌN ĐỂ NGUYÊN (admin-only, rủi ro thấp, đã giảm nhờ L-NEW-9).
  - **CÒN OPEN (minor, defer)**: round-35 LOWs còn lại (prune-arbitrary, manual-add bỏ quota, blocking
    embed perf, notifier cache default-family, duplicate broadcast); L-NEW-2 (pickle.load model wake-word —
    wake-word path). **Review loop mới phủ ~5%/554 file** — còn db.py/state.py/rag sâu/audio/firmware/
    frontend chưa review sâu → danh sách "vấn đề" CHƯA đầy đủ.
  - Suite **708/708 PASS** (trước 704); Vite build OK; SYSTEM_MAP cập nhật.
- **TOEIC Speaking audio server (multipart + STT) — ✅ DONE + committed `b38ec25`:**
  - `src/audio/input/transcribe_file.py` (MỚI): STT cho FILE (không import sounddevice như ear_stt) —
    lazy faster-whisper, GPU(cuda float16)→fallback CPU(`WHISPER_CPU_MODEL`, int8) giữ đúng Protected
    Fix; `transcribe_file(path, language)` không raise (lỗi→"").
  - `exam_router.py`: endpoint MỚI `POST /api/learning/exams/{paper_id}/submit-speaking-audio`
    (multipart: `question_ids[]` + `files[]` khớp index + `time_spent_seconds` + `language`), transcribe
    từng clip qua helper module-level `_transcribe_audio` (monkeypatch được trong test) rồi tái dùng
    `submit_toeic_sw`. Giới hạn 25MB/clip; mismatch→422, STT rỗng→422, quá lớn→413. `/submit-speaking`
    (JSON transcript) GIỮ làm fallback.
  - `requirements.txt`: thêm `python-multipart==0.0.20` (CI tự cài; ĐÃ cài vào `.venv` phiên này theo
    approval của user — endpoint multipart cần nó).
  - **Frontend** `LearningHubPage.jsx`: Speaking nay ghi âm THẬT bằng MediaRecorder (song song Web Speech
    API để xem trước transcript); `finishExam` ưu tiên gửi audio qua `submitToeicSpeakingAudio`
    (`api.js` MỚI, FormData), fallback transcript nếu server STT lỗi/không ghi được. Reset blob mỗi đề.
  - **Test Group 90** (4): multipart→STT(stub)→chấm có estimated_200; mismatch 422; STT rỗng 422; đề
    không phải toeic_sw 422. Suite **689/689 PASS** (trước 685). SYSTEM_MAP cập nhật.
- **Phase 6 (Nội dung + Nhật ký + Thống kê + công tắc tri thức) — ✅ DONE + committed `27994b3`:**
  - **Nội dung GLOBAL** (`admin_router`): `/api/admin/content` GET(list, lọc type)/POST(tạo global
    family_id NULL)/`/{id}` POST(sửa)/DELETE — radio/video/game trên bảng `content_items`, validate
    type∈{radio,video,game} & age_min≤age_max. Nội dung global enabled hiện cho MỌI gia đình qua
    `/api/entertainment/*` (đã có `(family_id IS NULL OR =?)`). FE `ContentAdminPage.jsx` (form + bảng
    + toggle bật/tắt + sửa/xóa, lọc theo loại).
  - **Thống kê** (`/api/admin/stats`): đếm users/admin/active, families, conversations, exams
    (papers/global/sessions/questions), content theo loại, kênh YouTube global+family, tóm tắt safety.
    FE `StatsAdminPage.jsx` (thẻ số liệu nhóm).
  - **Nhật ký**: FE `LogsAdminPage.jsx` dùng endpoint `/api/admin/logs` SẴN CÓ (Phase 1, đã redact
    secret + child_text) + lọc level/component. `api.js` thêm `adminGetLogs` có tham số.
  - **Công tắc tri thức**: thêm `KNOWLEDGE_ENABLED` vào `env_admin.TOGGLES` (hiện ở trang API key) +
    gate `knowledge_router` (dependency, mặc định BẬT; tắt → 503).
  - AdminApp: bật ready cho content/logs/stats; bỏ placeholder "sắp có". `api.js` thêm helper
    adminListContent/Create/Update/Delete + adminGetStats + adminGetLogs.
  - **Test Group 89** (5): content CRUD+RBAC, validate 422, global content hiện cho family, stats+RBAC,
    knowledge toggle→503. Suite **685/685 PASS** (trước 680). SYSTEM_MAP cập nhật.
  - **DEFER có chủ đích — Persona/Role admin-global**: persona đã per-family (parent chỉnh qua
    `/api/persona`), lưu trong bảng `persona` keyed family_id. Biến thành "mặc định global" đòi đổi
    logic fallback nạp persona (đụng prompt AI lõi — cần pass riêng cẩn thận). KHÔNG làm trong phase này.
- **Phase 5 (An toàn trẻ — admin global) — ✅ DONE + committed `0dcba21`:** user chọn cả 4 mảng.
  - **Backend** `src/safety/safety_filter.py`: GIỮ NGUYÊN 3 lớp hardcode (Protected Fix), THÊM lớp
    global module-level đọc `resources/safety_config.json` (MỚI): `blocklist_words` (thay bằng "…"),
    `blocked_topics` (refusal, khớp cả có dấu/không dấu qua normalize_vi), `policy` (age/time/sleep).
    Helper module: `load/reload_safety_config`, `get_global_policy`, `get_safety_config_full`,
    `set_blocklist_words/set_blocked_topics/set_global_policy`, monitoring `get_safety_stats/reset_safety_stats`
    (đếm + ring buffer 200, CHỈ lưu trigger word/topic — KHÔNG lưu nội dung trẻ). `check()` ghi monitoring
    + dùng `_first_topic_trigger` (trả chuỗi trigger). Hiệu lực NGAY sau khi admin lưu (reload), mọi
    SafetyFilter instance dùng chung state module.
  - `control_router.py`: `_default_age_filter/_default_time_limits/_default_sleep_settings` nay lấy từ
    `get_global_policy()` → gia đình CHƯA tự cấu hình thấy mặc định global của admin (fallback giá trị cũ).
  - `admin_router.py`: `/api/admin/safety/config` (GET), `/blocklist` `/topics` `/policy` (POST),
    `/stats` (GET) `/stats/reset` (POST) — `require_admin`, validate min≤max / warning≤daily / HH:MM.
  - **Frontend**: `pages/admin/SafetyAdminPage.jsx` (TagEditor cho blocklist+topics, form policy,
    bảng theo dõi + reset); mục 'safety' trong AdminApp = ready; `api.js` thêm 6 helper adminSafety*.
  - **Test Group 88** (6): RBAC, blocklist hiệu lực ngay, topic refusal (có/không dấu), policy default
    + validate 422, stats đếm/recent/reset, regression lớp hardcode. Suite **680/680 PASS** (trước 674).
    Test redirect `_SAFETY_CONFIG_PATH` sang temp → KHÔNG đụng file thật. SYSTEM_MAP cập nhật.
- **Phase 4 (Kênh YouTube) — ✅ DONE + committed `363a6ce`:** admin sửa allowlist GLOBAL + parent
  thêm kênh cho GIA ĐÌNH mình.
  - **Backend**: bảng DB mới `youtube_channels` (family-scoped) + helper trong `db.py`
    (`list_family_youtube_channels`/`add_family_youtube_channel` upsert/`delete_family_youtube_channel`).
    `youtube_lessons.py`: tách `available` (có key, không bị tắt) khỏi `enabled` (có kênh global) →
    kênh family chạy được dù allowlist global rỗng; `fetch_videos(..., extra_channels=...)` merge
    global+family dedup theo channel_id; thêm `list_global_channels/add_global_channel/remove_global_channel/reload`
    (ghi `resources/youtube_channels.json` an toàn, giữ `_doc`/`_schema`). `admin_router.py`:
    `/api/admin/youtube/channels` GET/POST/DELETE (`require_admin`). `game_router.py`:
    `/api/entertainment/youtube/channels` GET/POST/DELETE (family, max 30/family, validate UC…),
    `_augment_with_youtube` nay gate trên `available` + nạp kênh family.
  - **Frontend**: component dùng chung `components/YouTubeChannelManager.jsx`; admin
    `pages/admin/YouTubeAdminPage.jsx` (mục 'youtube' trong AdminApp = ready); parent: card "Kênh
    YouTube của gia đình" trong `MorePage.jsx` (nút Quản lý). `api.js` thêm 6 helper (admin* + my*).
  - **Test Group 87** (5): cô lập family, channel_id sai→422, xóa+upsert, admin global CRUD+RBAC
    (redirect `_CHANNELS_PATH` sang temp để KHÔNG đụng file thật), fetch merge family khi global rỗng.
    Suite **674/674 PASS** (trước 669). SYSTEM_MAP cập nhật.
- **Active branch**: `003-web-search-integration`.
- **Active spec**: none yet. When a Spec Kit feature is running, set this to its path,
  e.g. `.specify/specs/004-toeic-sw/` — read its `tasks.md` and continue from the first
  unticked task. (Spec Kit `.specify/` structure is created on the first `/speckit-specify`.)
- **Admin UI riêng (đang làm theo phase) — Phase 1 ✅ DONE + committed phiên này:**
  Kiến trúc đã chốt với user: cùng web; đăng nhập tài khoản `is_admin` (admin trong `.env`)
  → render **AdminApp** riêng; tài khoản thường → Parent App như cũ. API key: chỉ xem/sửa
  key PUBLIC (YouTube/NASA/Tavily/Brave), **KHÔNG hiển thị key LLM**. Đề/kênh: admin thêm =
  global (mọi tài khoản thấy), parent thêm = chỉ gia đình mình. "Quản lý gia đình" gộp thành
  cột trong trang tài khoản (không làm module riêng trừ khi cần multi-tenant).
  - **Phase 1 (DONE)**: `admin_router.py` thêm `/api/admin/users` (list, lock/unlock,
    grant/revoke admin, reset-password, delete — `require_admin`, chặn tự-thao-tác chính mình).
    FE: `pages/admin/AdminApp.jsx` (shell sidebar 8 mục, 7 mục "sắp có") + `UsersAdminPage.jsx`;
    `App.jsx` rẽ nhánh `if user.isAdmin`; `api.js` thêm admin* helper. Test **Group 84** (5).
    Suite **658/658 PASS**, build OK.
  - **Phase 2 (DONE + committed)**: `src/config/env_admin.py` (MỚI) — đọc/ghi `.env` an toàn,
    **whitelist nghiêm ngặt** (chỉ YOUTUBE/NASA/TAVILY/BRAVE + 6 toggle), không bao giờ đụng/lộ
    key LLM/JWT/admin; masked giá trị; test key sống/chết. `admin_router.py` thêm
    `/api/admin/config/keys` (GET/POST/DELETE/test) + `/api/admin/config/toggles` (GET/POST).
    FE: `ApiKeysPage.jsx` (key public: set/test/xóa + masked; toggle bật/tắt, đánh dấu cần-restart);
    mục 'apikeys' trong AdminApp = ready. Test **Group 85** (5, dùng `_TempEnv` không đụng .env thật,
    verify không lộ giá trị). Suite **663/663 PASS**. Lưu ý: ghi .env cập nhật os.environ ngay,
    nhưng singleton (youtube/websearch) + biến đọc lúc start (camera/cry/wakeword) cần RESTART.
  - **Phase 3 (DONE + committed)**: Đề thi tự tạo. `exam_router.py`: `POST /api/learning/exams/custom`
    (parent = đề riêng family-scoped; admin `is_global=true` = đề chung), `DELETE /api/learning/exams/{id}`
    (admin xóa bất kỳ; parent chỉ xóa đề custom của family mình; không xóa pack), `GET /api/learning/admin/papers`.
    **Cô lập gia đình** thêm vào list/detail/submit/submit-toeic-sw: `(family_id IS NULL OR family_id=?)`
    — đề riêng chỉ family đó thấy, đề global mọi người thấy (backward-compatible vì pack đều family_id NULL).
    FE: `components/ExamBuilder.jsx` (form MCQ dùng chung), `pages/admin/ExamsAdminPage.jsx` (list mọi đề +
    tạo đề chung + xóa), và LearningHubPage exam mode thêm "➕ Tạo đề của tôi" + nút 🗑️ trên đề custom của mình.
    Test **Group 86** (6): cô lập family, admin global hiện cho mọi nhà, non-admin không tạo global,
    422 đáp-án-sai, quyền xóa, admin list RBAC. Suite **669/669 PASS**, build OK.
  - **Phase 4 (DONE + committed `363a6ce`)**: Kênh YouTube (admin global + parent gia đình) —
    xem bullet "Phase 4 (Kênh YouTube)" ở trên.
  - **Phase 5 (DONE + committed `0dcba21`)**: An toàn trẻ (admin global blocklist/topics/policy/stats)
    — xem bullet "Phase 5 (An toàn trẻ)" ở trên.
  - **Phase 6 (DONE + committed `27994b3`)**: Nội dung global + Nhật ký + Thống kê + công tắc tri
    thức — xem bullet "Phase 6" ở trên. Persona/Role admin-global DEFER có chủ đích.
  - **✅ HẾT PHASE Admin UI**: cả 6 phase đã hoàn tất, 8 mục sidebar đều ready.
- **Lớp Knowledge — 15 API ngoài an toàn (no-key) — ✅ DONE + committed `6766ebd`:**
  User chọn 15 API (4 nhóm; KHÔNG chọn Radio Browser). Gom thành 1 lớp thống nhất:
  - `src/knowledge/knowledge_client.py` (MỚI): HTTP+timeout+cache TTL dùng chung, lọc text
    qua `SafetyFilter`, **không bao giờ raise** (lỗi → `{"ok": false}`). Provider: dictionary,
    country, number_fact, math (MathJS), trivia (OpenTDB, html-unescape, KHÔNG auto-seed),
    books (Open Library), gutenberg (Gutendex), poem (PoetryDB), wiki, weather (Open-Meteo
    geocode+forecast), iss (Open Notify), apod (NASA — `NASA_API_KEY` hoặc DEMO_KEY),
    animal_fact (cat/dog), fun_fact, joke (JokeAPI **safe-mode + blacklist**), pokemon, disney.
    Mọi call qua `_get_json`/`_get_text` (module-level) → test monkeypatch chạy offline.
  - `src/api/routers/knowledge_router.py` (MỚI) + đăng ký trong `server.py`: 17 endpoint
    `GET /api/knowledge/*` (+ `/api/entertainment/jokes`), đều `Depends(get_current_user)`.
  - Test **Group 83** (6 test, stub HTTP): status, dictionary parse, joke safe-mode params,
    graceful (lỗi→ok:false không 500), math eval, yêu-cầu-auth. Suite **652/652 PASS**.
  - SYSTEM_MAP cập nhật. **Env tùy chọn**: `NASA_API_KEY` (mặc định DEMO_KEY),
    `KNOWLEDGE_CACHE_TTL_SECONDS` (mặc định 1800). 16/17 nguồn no-key, dùng được ngay.
  - **UI Parent App — ✅ DONE + committed `d1399ac`**: `components/KnowledgeExplorer.jsx`
    (chọn danh mục: từ điển/wiki/thời tiết/pokémon/số/toán/động vật/điều thú vị/truyện cười/ISS/APOD,
    input động + render từng loại, degrade ok:false → thông báo nhẹ) nhúng trong `MorePage.jsx` (card
    "🔎 Khám phá tri thức", mở rộng khi cần). `api.js` thêm helper generic `knowledgeQuery(name, params)`
    (xử lý cả `/api/entertainment/jokes`). Build OK; suite 689/689 (frontend không đụng Python).
  - **CÒN LẠI (tùy chọn)**: Robot Display gọi các endpoint này; pipeline dịch + nạp `trivia` vào
    `question_bank` (admin); Radio Browser (user chưa chọn — cần allowlist).
- **Video lessons qua YouTube (allowlist kênh) — ✅ DONE + committed `338796b` (+ fix cache/seed `d532796`):**
  Thay mock `mockVideoLessons` bằng nguồn thật từ YouTube nhưng AN TOÀN: chỉ lấy video từ
  DANH SÁCH KÊNH ĐÃ DUYỆT, không search mở.
  - `src/entertainment/youtube_lessons.py` (MỚI): class `YouTubeLessons` + singleton. Đọc
    `YOUTUBE_API_KEY` từ `.env` + allowlist `resources/youtube_channels.json`. Lấy video qua
    playlist "uploads" của kênh (UC…→UU…, rẻ quota 1 unit/kênh) + `videos.list` lấy duration.
    Cache TTL (mặc định 6h), graceful: thiếu key/allowlist/lỗi → trả `[]` (no-op). Không raise.
  - `resources/youtube_channels.json` (MỚI): allowlist `channels: []` + schema/ví dụ. **Cần user
    điền channel_id (UC…) các kênh giáo dục tin cậy + đặt `YOUTUBE_API_KEY` trong `.env` để bật.**
  - `src/api/routers/game_router.py`: `/api/entertainment/videos` gọi `_augment_with_youtube`
    merge video YouTube vào kết quả DB (dedup theo source_url, áp cùng bộ lọc chủ đề
    blocked/allowed + family scope). Tắt YouTube → endpoint giữ nguyên hành vi cũ.
  - `frontend/.../api.js`: `getVideoLessons` map `duration` từ YouTube.
  - Test **Group 82** (4 test, không cần mạng — dùng stub): `_fmt_duration`, tắt-mặc-định,
    allowlist chỉ nhận UC…, và HTTP merge+dedup. Suite **646/646 PASS**. FE build OK.
  - SYSTEM_MAP.md cập nhật (entertainment + game_router rows).
  - **2026-06-24 (cuối)**: user đã thêm `YOUTUBE_API_KEY` thật (check_keys: sống). Allowlist
    `resources/youtube_channels.json` nay có **7 kênh** (channel_id verify qua API): POPS Kids,
    Bút chì TV, Học Tiếng Anh Cùng Emma, Thầy Mùa Toán Tư Duy, Dr.Binocs, Chun Chin, Cảnh Sát
    Trưởng Labrador. Verify thật: `fetch_videos()` trả 28 video (4×7), duration/tags đúng, cache OK.
  - **BUG đã sửa**: `fetch_videos` gọi `_get_cached/_set_cached` mà chưa định nghĩa → sẽ 500 khi
    bật key thật. Đã thêm 2 method cache + bọc try/except trong `_augment_with_youtube` (game_router)
    + test regression **82.5** (đi đường thật, stub `_fetch_channel`). 82.2/82.4 sửa để độc lập `.env`
    (vì `.env` thật giờ có key, `load_dotenv` nạp vào process test). Suite **653/653 PASS**.
  - Tooling mới: `scripts/check_keys.py` (kiểm tra key sống/chết), `scripts/resolve_youtube_channels.py`
    (tra channel_id thật từ tên), `scripts/merge_env.py` (trộn .env cũ vào template).
  - **CÒN LẠI**: user restart server để thấy video; (tùy chọn) UI hiện tên kênh; lọc tiêu đề qua SafetyFilter.
- **Learning Hub Phase 3 — TOEIC Speaking & Writing (đang làm, 2026-06-24):**
  - opencode đã làm + COMMIT backend chấm điểm (`1952a4e feat(learning): add toeic sw backend grading`):
    `src/api/routers/exam_router.py` — model `SubmitToeicSW`, rubric `TOEIC_TASK_MAX_SCORES`,
    quy đổi thang 200 (`_estimate_200`), `_llm_toeic_grade` (qua `stream_chat` role teacher,
    trả JSON) + fallback offline khi `SKIP_LLM`/lỗi (`_offline_toeic_grade`), helper
    `_load_paper_items`/`_grade_toeic_sw_attempt`, 2 endpoint `POST /exams/{id}/submit-toeic-sw`
    và `/submit-speaking` (nhận transcript; multipart audio hoãn đến khi thêm `python-multipart`).
    Test riêng `tests/test_toeic_sw.py` (7 case, chạy `python tests/test_toeic_sw.py`, 7/7 PASS).
  - **PHIÊN NÀY — ✅ committed (`4397669`):** vá khoảng trống loader + thêm content pack:
    - `src/infrastructure/database/db.py`: mở rộng `_seed_learning_packs` để hỗ trợ câu TỰ LUẬN.
      Trước đây loader hard-code `question_type='mcq'` và bắt buộc `answer ∈ options` → KHÔNG seed
      được S&W. Nay: câu có `question_type` `toeic_speaking`/`toeic_writing` (hoặc suy ra từ
      `skill: speaking/writing`) bỏ qua kiểm tra options/answer và seed đúng `question_type`;
      MCQ giữ nguyên hành vi cũ (backward-compatible). Hằng số mới `_FREE_TEXT_QUESTION_TYPES`,
      `_SKILL_TO_FREE_TEXT_TYPE`; docstring cập nhật.
    - `resources/learning/toeic_sw.json` (MỚI): 6 đề / 14 task theo roadmap `toeic_sw_100→200`,
      phủ cả Speaking & Writing và đủ 6 topic rubric (read_aloud, describe_picture,
      respond_to_questions, email, express_opinion, opinion_essay).
    - `tests/run_tests.py`: test 80.2 (data-integrity answer∈options) nay lọc `question_type='mcq'`
      để không bắt nhầm câu tự luận S&W.
    - Đã verify: `init_db()` seed 6 paper / 14 câu S&W (0 câu lọt thành mcq); `_grade_toeic_sw_attempt`
      chấm end-to-end trên item seed thật OK; `python tests/run_tests.py` **637/637 PASS**, fresh DB.
  - **Frontend UI — ✅ DONE + committed `4c7a8e0`:** `frontend/parent_app/src/services/api.js`
    thêm `submitToeicSW(paperId, {responses, transcripts, timeSpentSeconds})`.
    `frontend/parent_app/src/pages/LearningHubPage.jsx`: trong exam mode, paper `subject==='toeic_sw'`
    rẽ sang luồng tự luận — playing-SW (1 task/màn, nav dots, textarea + đếm từ; Speaking có nút
    🎤 ghi âm dùng Web Speech API `webkitSpeechRecognition` đổ transcript vào textarea, fallback
    gõ tay nếu trình duyệt không hỗ trợ) và result-SW (hiển thị `~estimated_200/200`, %/điểm,
    Đạt/Chưa đạt, disclaimer, feedback + tips từng task). `finishExam` route sang `submitToeicSW`
    (responses cho writing, transcripts cho speaking). Vite build OK; verify HTTP roundtrip qua
    TestClient: list 6 đề → detail (qtypes đúng, options rỗng) → submit writing & speaking đều 200
    (estimated_200 + disclaimer) → submit-speaking rỗng = 422.
  - **Test trong `run_tests.py` — ✅ DONE + committed `a6facda`:** thêm **Group 81** (5 test)
    — loader seed ≥6 đề toeic_sw đúng question_type & 0 câu mcq; grader offline bounds; HTTP
    submit-toeic-sw writing (est200 + disclaimer); HTTP speaking + submit-speaking rỗng=422;
    đề không phải toeic_sw bị từ chối 422. Suite: **642/642 PASS** (trước 637). `test_toeic_sw.py`
    standalone vẫn giữ (unit helper), Group 81 lo phần CI/seed/HTTP.
  - **✅ ĐÃ XONG**: Speaking audio THẬT phía server (multipart + faster-whisper STT) — xem bullet
    "TOEIC Speaking audio server" ở đầu file. Không còn hạng mục dở cho TOEIC S&W.
- **OpenCode repo cleanup (DONE, 2026-06-24)**: verified `opencode.json`,
  `scripts/setup_opencode_bluesminds.sh`, and `scripts/test_bluesminds_api.sh` are absent
  from both `HEAD` and the working tree. Aider's temporary commit `31495c9` is not an
  ancestor of the active branch. The remaining OpenCode binary is outside the repo at
  `~/.nvm/versions/node/v22.19.0/bin/opencode` and was intentionally left untouched.
- **AI prompt-quality pass (opencode) — ✅ DONE + committed (`9f69cae feat(ai): improve prompt pedagogy`):**
  `src/ai/prompts.py`, `persona_manager.py`, `role_manager.py` + standalone test
  `tests/test_prompt_invariants.py` (9 cases, `python tests/test_prompt_invariants.py`, 9/9 PASS).
  Age-tiering (5-6 / 7-9 / 10-12), clearer kid examples, stronger TEACHER 4-step pedagogy,
  `PROMPT_VERSION` v1.0→v1.1. All core guardrails (no auto-naming child, distress-first,
  danger refusal, lang-match) + exported names retained; FRIEND/TEACHER no-diacritics,
  PARENT_* diacritics. (Trước đây ghi là UNCOMMITTED + có "ghi chú giữ dirty cố ý" — nay đã
  commit, các ghi chú đó đã bỏ.)
- **Learning Hub Phase 3 — HSG/exam packs (strategy: one subject deep at a time):**
  - DONE + committed (`20b6042`): `resources/learning/math_exam.json` — Toán fully covered, 6 papers / 42 questions (exam_grade6, exam_grade10, exam_thpt, hsg_school, hsg_district, hsg_province). 0 bad answers, unique paper_ids.
  - DONE + committed (`4771802`): `resources/learning/vietnamese_exam.json` — Tiếng Việt, 6 papers / 42 questions (same 6 tracks; subject='vietnamese'; comp_level set for hsg_*). Hand-authored language-focused MCQ (chính tả, từ loại, từ láy/ghép, biện pháp tu từ, thành phần câu, phong cách ngôn ngữ, hàm ý…). Validated: 0 bad answers, unique paper_ids.
  - DONE + committed (`21ed9e2`): `resources/learning/literature_exam.json` — Ngữ văn, 6 papers / 42 questions (same 6 tracks; subject='literature'; comp_level set for hsg_*). Hand-authored văn học MCQ (tác giả–tác phẩm, thể loại, nội dung/nghệ thuật, giá trị nhân đạo, phong cách, từ dân gian tiểu học → THPT/HSG). Validated: 0 bad answers, unique paper_ids.
  - DONE + committed (`abadc5d`): `resources/learning/english_exam.json` — Tiếng Anh, 6 papers / 42 questions (same 6 tracks; subject='en'; comp_level set for hsg_*). MCQ ngữ pháp/từ vựng có question_vi + giải thích tiếng Việt (tenses, conditionals, passive, đảo ngữ, phrasal verbs, idioms… từ tiểu học → HSG). Validated: 0 bad answers, unique paper_ids.
  - DONE + committed (`03152cb`): `resources/learning/science_exam.json` — Khoa học, 6 papers / 42 questions (subject='science'). KHTN tổng hợp. Validated 0 bad, unique ids.
  - DONE + committed (`005e111`): `resources/learning/physics_exam.json` — Vật lý, 6 papers / 42 questions (subject='physics'). Validated 0 bad, unique ids.
  - DONE + committed (`5c6ce1d`): `resources/learning/chemistry_exam.json` — Hóa học, 6 papers / 42 questions (subject='chemistry'). Validated 0 bad, unique ids.
  - DONE + committed (`238518c`): `resources/learning/biology_exam.json` — Sinh học, 6 papers / 42 questions (subject='biology'). Validated 0 bad, unique ids.
  - DONE + committed (`71cf079`): `resources/learning/history_exam.json` — Lịch sử, 6 papers / 42 questions (subject='history'). Validated 0 bad, unique ids.
  - DONE + committed (`eceb9c4`): `resources/learning/geography_exam.json` — Địa lý, 6 papers / 42 questions (subject='geography'). Validated 0 bad, unique ids.
  - DONE + committed (`2c51b57`): `resources/learning/civics_exam.json` — GDCD, 6 papers / 42 questions (subject='civics'). Validated 0 bad, unique ids.
  - DONE + committed (`0b25fbc`): `resources/learning/informatics_exam.json` — Tin học, 6 papers / 42 questions (subject='informatics'). Validated 0 bad, unique ids.
  - DONE + committed (`715ac47`): `resources/learning/programming_exam.json` — Lập trình, 6 papers / 42 questions (subject='programming'). Validated 0 bad, unique ids.
  - DONE + committed (`c9a8dd7`): `resources/learning/logic_exam.json` — Tư duy logic, 6 papers / 42 questions (subject='logic'). Validated 0 bad, unique ids.
  - DONE + committed (`3500576`): `resources/learning/economics_exam.json` — Kinh tế học, 6 papers / 42 questions (subject='economics'). Validated 0 bad, unique ids.
  - DONE + committed (`9d55009`): `resources/learning/health_exam.json` — Dinh dưỡng & Sức khỏe, 6 papers / 42 questions (subject='health'). Validated 0 bad, unique ids.
  - DONE + committed (`25131a0`): `resources/learning/life_skills_exam.json` — Kỹ năng sống, 6 papers / 42 questions (subject='life_skills'). Validated 0 bad, unique ids.
  - DONE + committed (`7575c24`): `resources/learning/music_exam.json` — Âm nhạc, 6 papers / 42 questions (subject='music'). Validated 0 bad, unique ids.
  - DONE + committed (`220c45f`): `resources/learning/art_exam.json` — Mỹ thuật, 6 papers / 42 questions (subject='art'). Validated 0 bad, unique ids.
  - DONE + committed (`49d4aa8`): `resources/learning/chinese_exam.json` — Tiếng Trung, 6 papers / 42 questions (subject='chinese'). Validated 0 bad, unique ids.
  - DONE + committed (`aa4cffd`): `resources/learning/japanese_exam.json` — Tiếng Nhật, 6 papers / 42 questions (subject='japanese'). Validated 0 bad, unique ids.
  - DONE + committed (`3bc1529`): `resources/learning/korean_exam.json` — Tiếng Hàn, 6 papers / 42 questions (subject='korean'; comp_level set for hsg_*). Chào hỏi, Hangul/vua Sejong, số đếm thuần Hàn, trợ từ -이/-가 & -을/-를, kính ngữ, TOPIK… Validated: 0 bad answers, unique paper_ids. Aggregate now: 24 subjects / 220 papers / 1586 questions / 0 invalid.
  - **✅ HOÀN TẤT Phase 3 exam/HSG packs (22 môn)**: tất cả môn học/kỹ năng đã có đủ gói 6 đề/42 câu (6 track exam_grade6/10/thpt + hsg_school/district/province). Môn KHÔNG cần gói dạng này: `ielts`, `toeic_lr` (đã là roadmap pack 6 đề sẵn); `toeic_sw` (Speaking/Writing — workstream RIÊNG, xem bullet "TOEIC Speaking & Writing" ở đầu mục này: backend đã commit, content pack + loader đã xong phiên này). Build helper ở scratchpad (`build_exam_common.py` + `b_<subject>.py`). Lưu ý: ngưỡng `run_tests.py` Group 80 vẫn pass (hiện chỉ yêu cầu ≥85 papers/≥640 q/≥22 subjects; thực tế đã ~220/1586/24).
  - Pattern: new per-subject file `resources/learning/<subject>_exam.json`; `subject` field groups it (e.g. "vietnamese"/"literature"/"en"); unique paper_ids; tracks = exam_grade6/exam_grade10/exam_thpt/hsg_school/hsg_district/hsg_province (set `comp_level` for HSG). Seed = `_seed_learning_packs` (idempotent). ALWAYS validate answer∈options before committing (script in `changelog/`-style one-liner used 2026-06-24).
- **Tooling installed 2026-06-24** (separate from product code): codegraph MCP (local code knowledge graph; `.mcp.json` + `.codegraph/` index, telemetry off, loads on next Claude Code restart); new skills `taste-skill` (`design-taste-frontend`), `pdf`, `xlsx`; PROJECT.md UI-skill routing rule. Pre-existing dirty files (`speckit-git-*`, `settings.local.json`, `ui-ux-pro-max/scripts/search.py`) left untouched.
- **Next thread**: hoàn tất TOEIC S&W — (1) nối frontend UI (viết/nói + gọi 2 endpoint mới +
  hiển thị `estimated_200`/disclaimer); (2) gắn `test_toeic_sw.py` vào `run_tests.py`; (3) audio
  thật cho Speaking (multipart + STT, cần `python-multipart`). Chi tiết ở bullet TOEIC S&W đầu mục.

## Current State

- `PROJECT.md` is the source of truth for rules, protected fixes, workflow, and AI context policy.
- Current source root is `src/`; `src_brain/` is deprecated and must not be used.
- Main entry point: `src/main.py`.
- API server: `src/api/server.py`.
- Parent App: `frontend/parent_app/`.
- Robot Display: `frontend/robot_display/`.
- Motor firmware: `firmware/Robot_BI/Robot_BI.ino`.
- ESP32-S3 audio hardware test: `firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino`.
- ESP32-S3 speaker-only test: `firmware/ESP32S3_Speaker_Test/ESP32S3_Speaker_Test.ino`.
- Runtime DB: `runtime/robot_bi.db`.
- Generated agent docs: `CLAUDE.md` and `AGENTS.md`, regenerated with `python sync.py` after `PROJECT.md` changes.
- Current test command: `python tests/run_tests.py`.
- Spec Kit skills live in `.claude/skills/speckit-*/` (embedded templates, not the `specify` CLI). `speckit-converge` added 2026-06-24 to match upstream v0.11.x.

## Last Completed Task

- 2026-06-24: **Learning Hub Phase 2 — content packs + batch AI generation** (branch `003-web-search-integration`):
  - `resources/learning/*.json` (16 packs): real curriculum-accurate MCQ content (English, Math, Science/Physics/Chemistry/Biology, IELTS, TOEIC L&R, Tiếng Việt, Ngữ văn, History/Geography/Civics, Chinese/Japanese/Korean). Every `answer` is exactly one of its `options` (validated).
  - `src/infrastructure/database/db.py`: `_seed_learning_packs(conn)` loads all `resources/learning/*.json` into `question_bank` (status='published', source='pack') + assembles `exam_papers`; skips any question whose answer ∉ options; idempotent. Called from `init_db()` after `_seed_exam_content`. **Pack JSON schema is documented in the function docstring.**
  - `src/api/routers/exam_router.py`: added `CURRICULUM_BLUEPRINT` (subject→topics map), `GET /api/learning/curriculum`, and `POST /api/learning/admin/generate-batch` (loops single-generate per topic into review queue; honors SKIP_LLM; bounded ≤200 questions/batch).
  - **2026-06-24 follow-up (same branch)**: added 8 more subject packs — `informatics`, `programming`, `music`, `art`, `economics`, `health`, `life_skills`, `logic` (each 3 exams). Added their SUBJECT_LABELS + CURRICULUM_BLUEPRINT entries in `exam_router.py`. Total published now: **24 subjects / 91 papers / 677 questions / 0 invalid answers**.
  - `tests/run_tests.py`: Group 80 thresholds set (≥85 papers, ≥640 questions, ≥22 subjects) and required-subject list extended.
  - **How to add content**: drop a new `resources/learning/<subject>.json` following the schema → it auto-seeds on next `init_db()`. The AI pipeline (`generate` / `generate-batch`) writes to `question_bank` status='review' → admin publishes.
  - **Still not packed**: `toeic_sw` (Phase 3 territory) and dedicated HSG/exam-track papers (`hsg_*`, `exam_grade6/10`). See In Progress above.

- 2026-06-24: **Learning Hub Phase 1 — exam system + AI question-bank pipeline** (branch `003-web-search-integration`, commit `a0943a9`):
  - `src/infrastructure/database/db.py`: Added 4 tables in `init_db()` — `question_bank`, `exam_papers`, `exam_paper_questions`, `exam_sessions` (+ indexes). New `_seed_exam_content(conn)` is idempotent (`INSERT OR IGNORE`) and seeds 3 starter papers.
  - `src/api/routers/exam_router.py` (NEW): `GET /api/learning/subjects`, `/api/learning/tracks` (11 tracks: practice / hsg_* / exam_* / ielts / toeic_lr / toeic_sw); `GET /api/learning/exams`, `GET /api/learning/exams/{paper_id}` (**answers + explanations hidden**), `POST /api/learning/exams/{paper_id}/submit` (auto-grade MCQ, store `exam_sessions`, return report w/ explanations + pass/fail), `GET /api/learning/exams/sessions[/{id}]`. Admin (is_admin via `require_admin`): `POST /api/learning/admin/generate` (LLM via `stream_chat`, honors `SKIP_LLM`), `GET /api/learning/admin/review`, `POST /api/learning/admin/review/{question_id}`, `POST /api/learning/admin/exams`.
  - **Route-order gotcha**: `/api/learning/exams/sessions` is declared BEFORE `/api/learning/exams/{paper_id}` so it is not shadowed. Test 79.7 guards this.
  - `src/api/server.py`: registered `exam_router`.
  - `frontend/parent_app/src/services/api.js`: added `getExamSubjects/getExamTracks/getExams/getExam/submitExam/getExamSessions/getExamSession` + admin helpers.
  - `frontend/parent_app/src/pages/LearningHubPage.jsx`: added `ModeToggle` (📚 Học theo chủ đề / 📝 Làm đề & Thi thử); track catalog → exam list → playing (timer + nav dots) → graded result. Vite build OK.
  - `tests/run_tests.py`: added Group 79 (9 tests).
  - **User-approved scope**: full subject catalog across ages 3–18 incl. Chinese/Japanese/Korean + Ngữ văn. Phase 3 = IELTS/TOEIC Speaking via Robot Bi STT.

> Older completed work (frontend wiring/polish, DeepSeek V3, Stage 1.5 body expression + web search,
> audit sprints, ESP32-S3 tests, Sprints 1.1–1.4) → `changelog/2026-06-24-handoff-archive.md` and
> the dated `changelog/*.md` files.

## Stage Status

- Parent App Backend Phase 3: COMPLETE.
- Stage 0: complete.
- Stage 1 software: complete through Sprint 1.4 hardening.
- Stage 1 manual validation: robot audio is blocked until the ESP32-S3 microphone hardware test passes and production audio transport is implemented.
- Stage 1.5 body expression: software landed (`movement_emotion.py`); pending real motor-hardware validation.
- Learning Hub: Phase 1 + Phase 2 complete (24 subjects). Phase 3 — HSG/exam packs (22 môn) DONE + committed; TOEIC S&W backend + content pack DONE (frontend UI + audio STT còn lại).
- Stage 2 Special Memories: DONE (table + parent CRUD + RAG seeding + JournalPage UI + `due_today` nhắc chủ động). Còn lại: robot tự NÓI khi tới ngày (hook runtime), lịch nhắc nâng cao.

## Known Issues / Deferred Work

- Wake word disabled by default (`WAKEWORD_ENABLED=false`). Training pipeline exists, but real mic validation and trained custom model are pending.
- `edge-tts` primary TTS requires internet; pyttsx3 fallback remains local.
- ESP32-S3 mic/speaker hardware test exists; production network audio transport and display firmware do not.
- `follow_me.py`, `dock_charger.py`, `face_recognizer.py`, `fall_detector.py` are stubs/placeholders.
- Motor firmware has hardcoded IP `192.168.40.107:8443`; deployment-specific change needed.
- Cloudflare quick tunnel URL can change after restart unless a named tunnel is configured.
- Parent App radio/videos/games/emotions now return REAL backend data (empty state khi chưa có) — mock fallback đã gỡ. Một số nút lưu cài đặt vẫn là stub. (PROJECT.md "Known Current Gaps" còn ghi mock — sẽ tự cập nhật lần sync.py kế tiếp.)
- Provider quota can throttle Cerebras/Groq; fallback chain handled observed quota 429 warnings during tests.
- Current machine has no camera; this is supported and no longer blocks proactive behavior.
- Windows microphone diagnostics apply only to optional PC-connected microphones, not the two INMP441 modules on the robot.
- Learning Hub TOEIC S&W: HOÀN TẤT — backend chấm điểm, content pack, frontend UI, và audio STT thật server-side (multipart + faster-whisper) đều đã làm. Speaking audio thật cần `faster-whisper` model tải sẵn khi chạy production (test stub `_transcribe_audio`).

## Next Recommended Action

1. **Hoàn tất TOEIC S&W**: nối frontend UI (Speaking/Writing + 2 endpoint mới + `estimated_200`/disclaimer); gắn `test_toeic_sw.py` vào `run_tests.py`; làm audio STT thật (multipart, cần `python-multipart`). Backend + content pack đã xong (xem In Progress).
2. Commit the current `.claude/skills/` tooling edits (incl. new `speckit-converge`) if satisfied.
3. Hardware track (independent): upload `firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino`, verify the beep/record/playback cycle, then implement ESP32-S3 network audio transport.
4. Do not start Stage 2 automatically.

## Current Test Command

```bash
python tests/run_tests.py
```

## Files Recently Touched (Learning Hub Phase 1–2)

- `src/infrastructure/database/db.py`
- `src/api/routers/exam_router.py`
- `src/api/server.py`
- `resources/learning/*.json` (24 subject packs)
- `frontend/parent_app/src/services/api.js`
- `frontend/parent_app/src/pages/LearningHubPage.jsx`
- `tests/run_tests.py` (Groups 79 + 80)

## Files Recently Touched (Tooling — 2026-06-24)

- `.claude/skills/speckit-converge/SKILL.md` (new) — committed `0cc1c18`
- `.claude/skills/taste-skill/` (new, `design-taste-frontend`)
- `.claude/skills/pdf/`, `.claude/skills/xlsx/` (new, from anthropics/skills — proprietary license; scripts need Python deps NOT yet installed)
- `.claude/skills/karpathy-guidelines/` (new, MIT, SKILL.md only — behavioral guidelines: simplicity-first + surgical changes; additive, partial overlap with `robot-bi-dev`)
- `.mcp.json` (new, codegraph MCP server), `.gitignore` (+`.codegraph/`)
- `.claude/settings.json` (new) + `.claude/hooks/handoff-reminder.sh` (new) — Stop hook enforcing Rule 9: reminds to update handoff when src/frontend/resources/firmware changed but handoff.md wasn't. Read-only, self-clearing. **Needs `/hooks` reload or restart to activate** (project settings.json didn't exist at session start).
- `PROJECT.md` (UI-skill routing rule) → regenerated `CLAUDE.md` / `AGENTS.md` via `python3 sync.py`
- `changelog/2026-06-24-handoff-archive.md` (new) — committed `0cc1c18`
- `.claude/handoff.md`
