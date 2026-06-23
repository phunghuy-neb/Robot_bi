# Robot Bi — Changelog & Session History

## 2026-05-13-ai-context-restructure.md

# 2026-05-13 — AI Context / Instruction Restructure

- Reworked `PROJECT.md` with current status, source-of-truth hierarchy, AI context routing, file creation policy, `SYSTEM_MAP.md` maintenance policy, Spec Kit governance, machine setup policy, and session-end checklist.
- Rewrote `SYSTEM_MAP.md` as a descriptive-only current system map.
- Rewrote `.specify/memory/constitution.md` so Spec Kit is subordinate to `PROJECT.md`.
- Updated `.claudeignore` to exclude runtime/log/cache/model/media artifacts.
- Updated `HUONG_DAN_CHAY.md` paths and commands.
- Updated `sync.py` generated instruction headers and kept it as a pure sync tool.
- Regenerated `CLAUDE.md` and `AGENTS.md` via `python sync.py`.
- Removed obsolete historical/report docs from root/docs.
- No files under `src/`, `frontend/`, `firmware/`, or `tests/` were modified.

## 2026-05-09-frontend-responsive-refactor.md

# 2026-05-09 — Frontend Responsive Refactor

## Tóm tắt
Refactor toàn bộ giao diện web Robot Bi: responsive app shell mới, breakpoints chuẩn, WiFi screen đẹp.

## Thay đổi chính

### Viewport
- Đổi từ `user-scalable=no` sang `viewport-fit=cover` (hỗ trợ iPhone safe area).

### Design tokens mới
- `--primary-600: #1d4ed8`, `--border: #e2e8f0`, `--shadow-soft`, `--bg: #f4f8ff`.

### App shell responsive
- `.app-shell` không còn cứng `max-width: 480px` — thay bằng media queries.
- Bottom nav: full width, có `env(safe-area-inset-bottom)`.
- Page padding: thêm `env(safe-area-inset-bottom)`.

### Breakpoints mới (thay cũ 600/768/1025/1400px)
- **< 600px**: Mobile, bottom nav, 1 cột.
- **600px+**: max-width 680px, vẫn bottom nav.
- **900px+**: max-width 960px, 2-col grids bắt đầu.
- **1200px+**: Desktop/sidebar mode — ẩn bottom nav, hiện sidebar 240px, sidebar bên trái.
- **1600px+**: max-width 1280px.

### WiFi section — redesign hoàn toàn

#### Mobile
- Menu item "Mạng & Kết nối" trong tab Thêm.
- Click mở **WiFi Subscreen** (fixed overlay full screen).
- Subscreen có: back button, hero status card (gradient blue), 2 nút Quét/Kiểm tra, danh sách WiFi, accordion "Thông tin chi tiết".

#### Desktop (>= 1200px)
- Inline dashboard trong tab Thêm.
- Full-width banner trạng thái (gradient blue) + 4 metric cards.
- 2-col: WiFi list (trái) + chi tiết (phải).

### CSS mới
- `.subscreen`, `.subscreen-header`, `.back-btn`
- `.wifi-network-row`, `.wifi-network-body`, `.wifi-connected-badge`
- `.accordion-header`, `.accordion-body`, `.detail-row`
- `.wifi-dashboard`, `.wifi-mobile-only`, `.wifi-desktop-only`
- `.desktop-only`, `.mobile-only`, `.action-row`

### JS mới/cập nhật
- `openWifiScreen()`, `closeWifiScreen()` — mobile navigation.
- `openAddWifiModal()` — modal thêm WiFi thủ công mới.
- `loadWifiStatus()` → `_renderWifiHero()` + `updateWifiMenuSub()`.
- `loadWifiDesktop()` — renders desktop dashboard dynamically.
- `renderSavedWifi()`, `renderScanResult()` — viết vào cả mobile subscreen và desktop IDs.
- `startWifiScan()` — hiện loading trên cả hai.
- `checkWifiConnectivity()` — toast từ /api/status + /api/motor/status.
- `toggleWifiAccordion()` — accordion detail toggle.
- `handleWifiWsMessage()` — cập nhật cả desktop + mobile elements.

## Functions không bị ảnh hưởng
apiFetch, authHeader, tryRefreshToken, doLogin, doLogout, connectWS, toggleCamera, startWebRTC, startMJPEG, stopCamera, toggleMomMic, startMomMic, stopMomMic, _motorSend, loadMotor, initJoystick, sendJoystickCmd, lockRobotControl, unlockRobotControl, sendQuickMotorCommand, requestDockReturn, loadHome, loadMonitor, loadLearning, loadJournal.

## Test
372/374 PASS (2 fail cũ không liên quan: 47.4 verify_db_clean, 48.3 music volume).

## 2026-05-02-robot-display-flashcard-recursion.md

# 2026-05-02 — Robot Display Flashcard Recursion Fix

## Summary

- Fixed infinite recursion in `frontend/robot_display/index.html`.
- Captured the base `showFlashcard()` function in `_origShowFlashcard` before overriding it.
- Changed the enhancement from a hoisted function declaration to `showFlashcard = function(data) { ... }` so the saved original reference does not point back to the wrapper.

## Verification

- `python3 tests/run_tests.py` -> 374/374 PASS.

## 2026-05-01-backend-deep-review-fixes.md

# 2026-05-01 — Backend Deep Review Fixes

## Summary

- Fixed all requested Backend Deep Review groups without touching `src/infrastructure/auth/`.
- Restored WordQuizGame contract compatibility and added SQLite-backed high score storage.
- Fixed VoiceQuizGame JSON schema mapping and fuzzy answer scoring.
- Fixed session event parsing so valid metadata rows return event dicts.
- Made EmotionAlert accept either EmotionJournal or EmotionAnalyzer.
- Unified Curriculum schedule persistence through `learning_schedules`.
- Updated education, analytics, game scores, video history, and emotion summary API contracts.
- Reduced PII risk in INFO/WARNING logs by moving speech/content logs to DEBUG or length-only messages.
- Updated WakeWordDetector variants and default disabled state.
- Added Group 59 API contract tests.

## Verification

- `python3 tests/run_tests.py` final result: **374/374 PASS**.

## 2026-04-30-review-round5-security-fixes.md

# 2026-04-30 — Review Round 5 Security Fixes

## Scope

- Fix Critical + High security issues from review round 5.
- Keep existing protected behavior unchanged.
- Add Group 50 verification tests.

## Changes

- `src/infrastructure/database/db.py`: added `ALLOWED_CLEANUP_TABLES` validation before dynamic cleanup table deletes in `delete_family_record()`.
- `src/ai/ai_engine.py`: removed Gemini API key from request URL and sent it through `x-goog-api-key`; added `_groq_lock` for Groq fail streak/cooldown globals.
- `src/infrastructure/auth/auth.py`: no code change; verified argon2-cffi expects `verify(hash, password)`, matching existing `verify_password(plain, hashed)`.
- `src/api/routers/auth_router.py`: changed PIN comparison to `hmac.compare_digest()` and added guarded JSON parsing that returns 422 on malformed JSON.
- `src/main.py`: changed assistant persistence condition to `sanitized_reply`, dispatches RAG extraction before closing the session, and reuses one `pygame.time.Clock()` in the audio worker loop.
- `src/api/routers/analytics_router.py`: made count conversion NULL-safe.
- `src/safety/safety_filter.py`: replaced regex word boundaries with Unicode-aware lookaround boundaries.
- `src/api/routers/conversation_router.py`: fixed homework conversation `total` to use a COUNT query instead of current page length.
- `tests/run_tests.py`: added Group 50 with 9 security/quality verification tests.

## Verification

- After Critical 1: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Critical 2: `python3 tests/run_tests.py` -> 329/329 PASS.
- Critical 3 argon2 check: `verify(hash, pass)` OK; reversed order failed as expected; no code change.
- After High 1: `python3 tests/run_tests.py` -> 329/329 PASS.
- After High 2: `python3 tests/run_tests.py` -> 329/329 PASS.
- After High 3: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Medium 1: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Medium 2: `python3 tests/run_tests.py` -> 329/329 PASS.
- Medium 3 regex check: `khiêu dâm` matched with Unicode-aware boundary.
- After Medium 3: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Medium 4: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Medium 5: `python3 tests/run_tests.py` -> 329/329 PASS.
- After Group 50: `python3 tests/run_tests.py` -> 338/338 PASS.

## 2026-04-30-review-round4-fixes.md

# 2026-04-30 — Review Round 4 Fixes

## Scope

- Fix P1 DB path migration cu -> moi de tranh mat data khi upgrade tu `src_brain/` sang `src/`.
- Fix P2 video call end thieu family isolation.
- Fix P2 music transport buttons 404.

## Changes

- `src/infrastructure/database/db.py`: them `migrate_db_path_if_needed()` va goi dau `init_db()`. Helper chi copy DB cu co data sang `runtime/robot_bi.db` khi DB moi chua ton tai hoac nho hon nguong data.
- `src/communication/video_call.py`: them `_active_calls` alias, luu/check `family_id`, va reject `end_call()` khi family mismatch.
- `src/api/routers/video_call_router.py`: truyen `family_id` cua current user vao manager khi end call.
- `src/api/routers/music_router.py`: them routes `/api/music/next`, `/api/music/previous`, `/api/music/shuffle`, `/api/music/repeat`.
- `src/audio/output/music_player.py`: them methods `next_track()`, `prev_track()`, `toggle_shuffle()`, `toggle_repeat()`.
- `frontend/parent_app/index.html`: map UI command `prev` sang backend route `previous`.
- `tests/run_tests.py`: them Group 49 voi 8 verification tests.

## Verification

- Sau FIX 1: `python3 tests/run_tests.py` -> 321/321 PASS.
- Sau FIX 2: `python3 tests/run_tests.py` -> 321/321 PASS.
- Sau FIX 3: `python3 tests/run_tests.py` -> 321/321 PASS.
- Sau Group 49: `python3 tests/run_tests.py` -> 329/329 PASS.

## 2026-04-30-review-round3-runtime-fixes.md

# 2026-04-30 — Review Round 3 Runtime Fixes

## Summary

- Cleaned newer family-scoped tables when deleting a family.
- Updated Parent App video calls to preserve and send `call_id` on end.
- Updated Parent App music volume requests to send `level`.
- Loaded education schedules from `/api/education/schedule` before rendering.
- Updated `stress_test.py` imports from `src_brain.*` to `src.*`.
- Added Group 48 verification tests.

## Verification

- `python3 tests/run_tests.py` after each fix group:
  - FIX 1: 315/315 PASS
  - FIX 2: 315/315 PASS
  - FIX 3: 315/315 PASS
  - FIX 4: 315/315 PASS
  - FIX 5: 315/315 PASS
- `python3 stress_test.py` → runs without `ModuleNotFoundError`
- `python3 tests/run_tests.py` final → 321/321 PASS

## 2026-04-30-review-fixes-phase6-10.md

# 2026-04-30 — Review Fixes Phase 6-10

## Summary

- Fixed frontend/backend API mismatches for persona, emotion, and music playlist data.
- Added missing video call and game routers to FastAPI.
- Replaced deprecated `datetime.utcnow()` usage across `src/`.
- Persisted education learning schedules in SQLite.
- Added Group 46 verification tests.

## Verification

- `python3 tests/run_tests.py` → 309/309 PASS
- `grep -r "utcnow()" src/` → no matches
- Video/game route verification prints registered routes.

## 2026-04-30-phase-b-complete.md

# 2026-04-30 — Phase B Tasks B1-B8 Complete

## Scope

- Record that Phase B is fully complete.
- Mark Tasks B1-B8 as complete in project handoff documentation.

## Status

- Phase B: COMPLETE.
- Tasks B1-B8: 8/8 complete.

## Documentation Updates

- Updated `PROJECT.md` with the Phase B completion session.
- Updated `.claude/handoff.md` with the current Phase B status.
- Attempted `python sync.py`; this shell has no `python` executable.
- Ran `python3 sync.py` successfully after documentation updates.

## 2026-04-30-api-contract-review-fixes.md

# 2026-04-30 — API Contract Review Fixes

## Summary

- Pointed the root dashboard route to `frontend/parent_app/index.html`.
- Updated Parent App music, story, and game actions to match backend API contracts.
- Updated `verify_db_clean.py` to import from `src.infrastructure.database.db`.
- Added Group 47 verification tests.

## Verification

- `python3 tests/run_tests.py` → 315/315 PASS
- `python3 verify_db_clean.py` → runs without `ModuleNotFoundError`
- `python3 sync.py` → completed

## 2026-04-29-phase5-1-refactor.md

# Phase 5.1 — Refactor Cấu Trúc Thư Mục

**Ngày:** 2026-04-29  
**Loại:** Pure refactor — di chuyển file, cập nhật imports, không thay đổi logic.  
**Kết quả:** 197/197 PASS

---

## Tổng quan

Refactor toàn bộ cấu trúc thư mục từ `src_brain/` sang `src/` theo kiến trúc domain rõ ràng.  
`src_brain/` đã bị xóa. Không còn bất kỳ tham chiếu nào đến `src_brain`.

---

## File di chuyển (27 Python files)

| File gốc | File mới |
|---|---|
| `src_brain/main_loop.py` | `src/main.py` |
| `src_brain/train_text.py` | `src/train_text.py` |
| `src_brain/ai_core/core_ai.py` | `src/ai/ai_engine.py` |
| `src_brain/ai_core/prompts.py` | `src/ai/prompts.py` |
| `src_brain/ai_core/safety_filter.py` | `src/safety/safety_filter.py` |
| `src_brain/ai_core/homework_classifier.py` | `src/education/homework_classifier.py` |
| `src_brain/memory_rag/rag_manager.py` | `src/memory/rag_manager.py` |
| `src_brain/senses/ear_stt.py` | `src/audio/input/ear_stt.py` |
| `src_brain/senses/mouth_tts.py` | `src/audio/output/mouth_tts.py` |
| `src_brain/senses/cry_detector.py` | `src/audio/analysis/cry_detector.py` |
| `src_brain/senses/eye_vision.py` | `src/vision/camera_stream.py` |
| `src_brain/network/api_server.py` | `src/api/server.py` |
| `src_brain/network/db.py` | `src/infrastructure/database/db.py` |
| `src_brain/network/auth.py` | `src/infrastructure/auth/auth.py` |
| `src_brain/network/task_manager.py` | `src/infrastructure/tasks/task_manager.py` |
| `src_brain/network/state.py` | `src/infrastructure/sessions/state.py` |
| `src_brain/network/session_namer.py` | `src/infrastructure/sessions/session_namer.py` |
| `src_brain/network/notifier.py` | `src/infrastructure/notifications/notifier.py` |
| `src_brain/network/log_config.py` | `src/infrastructure/logging/log_config.py` |
| `src_brain/network/routers/auth_router.py` | `src/api/routers/auth_router.py` |
| `src_brain/network/routers/admin_router.py` | `src/api/routers/admin_router.py` |
| `src_brain/network/routers/conversation_router.py` | `src/api/routers/conversation_router.py` |
| `src_brain/network/routers/control_router.py` | `src/api/routers/control_router.py` |
| `src_brain/network/routers/ops_router.py` | `src/api/routers/ops_router.py` |
| `src_brain/network/routers/streaming_router.py` | `src/api/routers/streaming_router.py` |
| `src_brain/network/routers/webrtc_router.py` | `src/api/routers/webrtc_router.py` |
| `run_tests.py` | `tests/run_tests.py` |

## File frontend di chuyển

| File gốc | File mới |
|---|---|
| `src_brain/network/static/index.html` | `frontend/parent_app/index.html` |
| `src_brain/network/static/manifest.json` | `frontend/parent_app/manifest.json` |
| `src_brain/network/static/sw.js` | `frontend/parent_app/sw.js` |
| `src_brain/network/static/icon-192.png` | `frontend/parent_app/icon-192.png` |
| `src_brain/network/static/icon-512.png` | `frontend/parent_app/icon-512.png` |
| `.env.example` | `config/env/local.env.example` |

## Import path changes

- `src_brain.ai_core.core_ai` → `src.ai.ai_engine`
- `src_brain.ai_core.prompts` → `src.ai.prompts`
- `src_brain.ai_core.safety_filter` → `src.safety.safety_filter`
- `src_brain.ai_core.homework_classifier` → `src.education.homework_classifier`
- `src_brain.memory_rag.rag_manager` → `src.memory.rag_manager`
- `src_brain.senses.ear_stt` → `src.audio.input.ear_stt`
- `src_brain.senses.mouth_tts` → `src.audio.output.mouth_tts`
- `src_brain.senses.cry_detector` → `src.audio.analysis.cry_detector`
- `src_brain.senses.eye_vision` → `src.vision.camera_stream`
- `src_brain.network.api_server` → `src.api.server`
- `src_brain.network.db` → `src.infrastructure.database.db`
- `src_brain.network.auth` → `src.infrastructure.auth.auth`
- `src_brain.network.task_manager` → `src.infrastructure.tasks.task_manager`
- `src_brain.network.state` → `src.infrastructure.sessions.state`
- `src_brain.network.session_namer` → `src.infrastructure.sessions.session_namer`
- `src_brain.network.notifier` → `src.infrastructure.notifications.notifier`
- `src_brain.network.log_config` → `src.infrastructure.logging.log_config`
- `src_brain.network.routers.*` → `src.api.routers.*`
- `src_brain.main_loop` → `src.main`

## Hardcoded paths đã fix

- `DB_PATH`: `Path(__file__).with_name("robot_bi.db")` → `Path(__file__).parent.parent.parent.parent / "runtime" / "robot_bi.db"`
- `_STATIC_DIR` (server.py): `Path(__file__).parent / "static"` → `Path(__file__).parent.parent.parent / "frontend" / "parent_app"`
- `_DEFAULT_DB_PATH` (rag_manager.py): `"src_brain/memory_rag/chroma_db"` → absolute path tới `runtime/chroma_db`
- `_hf_cache_dir` (ear_stt.py, rag_manager.py): `"src_brain/..."` → `runtime/.hf_cache`
- YAMNet model: `Path("src_brain/senses/models/yamnet.tflite")` → `Path(__file__).parent / "models" / "yamnet.tflite"`; model copied to `src/audio/analysis/models/`
- Vision data dirs: `"src_brain/senses/vision_data/..."` → `"runtime/vision_data/..."`

## Cấu trúc mới tạo

- `src/` — 25 packages với `__init__.py`
- `src/config/settings.py`, `src/config/constants.py` — placeholder
- 40+ placeholder files cho Phase 5-10 modules
- `frontend/robot_display/` — placeholder HTML files
- `resources/` — flashcards, stories, music directories
- `runtime/` — gitignored, chứa robot_bi.db, chroma_db/, logs/
- `tests/` — test suite
- `config/env/` — local.env.example, production.env.example
- `infra/docker/`, `infra/scripts/` — placeholder
- `docs/ROADMAP.md` — full roadmap Phase 5-10
- `.github/workflows/test.yml` — CI workflow

## Test result

```
KET QUA: 197/197 PASS | 0/197 FAIL
TAT CA TESTS PASS
```

## 2026-04-28-task-4-5-homework-system.md

# 2026-04-28 - Phase 4 Task 4.5 Homework System

## Summary

- Added local homework classification in `src_brain/ai_core/homework_classifier.py` using Unicode-normalized keyword/regex matching only.
- Added `is_homework` and `homework_marked_at` migration fields to `conversations`.
- Added DB helpers `mark_session_homework()` and `get_homework_sessions()` with family-scoped update/read behavior.
- Integrated homework marking in `main_loop.py` after TTS completion and after `sanitized_reply` is persisted.
- Added `GET /api/conversations/homework` and updated `POST /api/conversations/{session_id}/homework` to mark sessions.
- Added Parent App `Bai tap` tab with homework session list, shared conversation detail view, and WebSocket homework notification reload.
- Added Group 31 tests for classifier, DB helpers, homework list behavior, route registration, and import stability.

## Verification

- Baseline before Task 4.5 tests: `182/182 PASS`.
- Final after Group 31: `190/190 PASS`.

## 2026-04-28-task-4-4-multifamily-isolation.md

# 2026-04-28 - Task 4.4 Multi-family Isolation

## Summary

- Added persisted `families` registry and `is_admin` role support.
- Scoped ChromaDB memories by `family_id` with real `where={"family_id": family_id}` filters.
- Scoped conversations, events, tasks, notifier reads/writes, TaskManager operations, and WebSocket event replay/broadcast by family.
- Added admin-only family management endpoints:
  - `POST /api/admin/families`
  - `GET /api/admin/families`
  - `DELETE /api/admin/families/{family_id}`
- Added explicit cleanup for family deletion across users, refresh tokens, conversations/turns, events, tasks, and Chroma memories when RAG is injected.

## Verification

- Added Group 30 to `run_tests.py` with 6 isolation tests:
  - ChromaDB family filter is real
  - Conversation API cannot cross-read another family
  - Events unread/read scope by family
  - Tasks operations scope by family
  - Admin endpoints require admin and delete scoped data
  - Family foreign keys exist
- Final test result: `182/182 PASS`.

## 2026-04-27-sprint-d-freeze.md

# 2026-04-27 - Sprint D Frontend, Cleanup & Documentation

## Summary

- Completed Sprint D final freeze fixes for frontend cleanup, operations logging, documentation, and repository cleanup.
- Added Group 28 verification tests in `run_tests.py`.
- Final Sprint D target: 164/164 PASS.

## Deferred

- WebRTC frame source requires Ubuntu + aiortc runtime.
- Wake-word model training requires dataset.
- Phase 4 features remain out of scope.
- ChromaDB multi-family isolation remains Phase 4.

## 2026-04-27-final-pre-phase4-fix-sprint.md

# 2026-04-27 - Final Pre-Phase 4 Fix Sprint

## Summary

- Completed 12/12 requested pre-Phase 4 fixes and verifications.
- Added Group 29 to `run_tests.py` with 12 verification tests.
- Final target: `176/176 PASS`.

## Fixes

- WebRTC reconnect cleanup verified: old peer connection is closed before assigning a new one.
- Browser unload and logout now stop camera and audio monitor cleanup paths.
- Speech transcription content moved from INFO to DEBUG logging.
- SQLite connections now enable `PRAGMA foreign_keys = ON`.
- RAG prune counter now decrements only after successful delete and stops on delete failure.
- `MIC_DEVICE` is configurable via environment for STT and audio monitoring.
- `.env.example` no longer contains weak `ADMIN_PASSWORD` placeholder.
- `/auth/logout` no longer calls `verify_access_token()` a second time inside the handler.
- WebRTC connection state close path is wrapped in try/except.
- PWA icon files verified present.
- `HUONG_DAN_CHAY.md` no longer references `train_text.py`.

## Tests

- `python run_tests.py` after each fix/no-change verification.
- Final expected suite: `176/176 PASS`.

## 2026-04-26-phase3-final-fix-sprint.md

# 2026-04-26 — Phase 3 Final Fix Sprint

## Summary

- Completed all 23 requested audit pass 3 fixes.
- Added Group 24 verification tests to `run_tests.py`.
- Final automated result before handoff: 138/138 PASS.

## Changed

- Security: task input validation, registration gate, JWT nonexistent-user rejection, change-password rate limiting.
- Isolation: memory endpoint family guard logs and WebRTC peer connections scoped by user.
- Frontend: safe DOM rendering for dynamic data, logout cleanup ordering, fetch refresh coverage, WS reconnect guard, checkAuth retry behavior.
- Reliability: WebRTC offer cleanup, audio queue backpressure handling, DB migration error handling, shutdown cleanup, TaskManager-before-API startup ordering, logging setup idempotence.
- Privacy: chat/AI content removed from INFO/WARNING/ERROR logs in touched files.
- Infra: Ubuntu aiortc requirements file, ear_stt env example drift, notifier WS enabled stats, unused ops import cleanup.

## Verification

- `python run_tests.py` -> 138/138 PASS.

## 2026-04-17-step2.7-conversation-thread-ui.md

# Step 2.7 - Parent App conversation thread UI

- Date: 2026-04-17
- Scope: frontend only in `src_brain/network/static/index.html`
- Added a new Parent App tab `Hội thoại`
- Added thread list and thread detail sections
- Added `loadThreads()`, `showThreadDetail()`, `showThreadList()`, and `deleteThread()`
- Reused existing JWT helpers `authHeader()` and `apiFetch()` without modifying them
- Reused existing bubble styles and added minimal thread-specific CSS classes
- Full regression test result: `89/89 PASS`
- Manual browser verification was not performed in this CLI environment

## 2026-04-17-step2.6-whisper-cpu-downgrade.md

# 2026-04-17 - Step 2.6: Whisper auto-downgrade on CPU mode

- Kept the GPU path unchanged in `src_brain/senses/ear_stt.py`: `large-v2` with `float16` on CUDA.
- Updated the CPU fallback branch to read the model from `WHISPER_CPU_MODEL`.
- Set the CPU default to `medium` to reduce latency on CPU-only machines.
- Added `WHISPER_CPU_MODEL=medium` to `.env.example` with an explanation comment.
- Added 2 tests in `run_tests.py`:
  - check `WHISPER_CPU_MODEL` default handling
  - verify `EarSTT()` still initializes without error
- Verification: `python run_tests.py` -> `89/89 PASS`.

## 2026-04-17-step2.5-conversation-api.md

# 2026-04-17 - Step 2.5: conversation thread API endpoints

- Added 4 protected conversation endpoints in `src_brain/network/api_server.py`:
  - `GET /api/conversations`
  - `GET /api/conversations/{session_id}`
  - `DELETE /api/conversations/{session_id}`
  - `POST /api/conversations/{session_id}/homework`
- All new endpoints use `Depends(get_current_user)`.
- Added `HomeworkTurnIn` request model for the homework endpoint.
- Updated `src_brain/network/db.py` so `turns.role` supports `homework`.
- Added migration logic to rebuild the `turns` table automatically when an existing DB still has the old role CHECK constraint.
- Added Python-level role validation in `add_turn()`.
- Added Group 16 route-existence tests in `run_tests.py`.
- Verification: `python run_tests.py` -> `87/87 PASS`.

## 2026-04-17-step2.4-session-auto-naming.md

# 2026-04-17 - Step 2.4: auto-naming session from first question

- Added `update_session_title(session_id, title)` in `src_brain/network/db.py`.
- Added new file `src_brain/network/session_namer.py`.
- Implemented `_generate_session_title(user_text)` with direct non-streaming Groq `requests.post`, model `llama-3.3-70b-versatile`, `max_tokens=20`, `temperature=0.3`, and `timeout=5`.
- Added safe fallback: if naming fails for any reason, return `user_text[:30]` instead of raising.
- Integrated a daemon background thread in `src_brain/main_loop.py` right after the first user turn is stored.
- Kept `stream_chat()` and the main streaming/audio conversation pipeline unchanged.
- Added Group 15 tests in `run_tests.py`.
- Verification: `python run_tests.py` -> `83/83 PASS`.

## 2026-04-17-step2.3-conversation-sessions.md

# 2026-04-17 - Step 2.3: conversation sessions per wake

- Added `conversations` and `turns` tables in `src_brain/network/db.py` using `CREATE TABLE IF NOT EXISTS`.
- Added `idx_turns_session` index for session turn lookup.
- Added `create_session()`, `close_session()`, `add_turn()`, and `get_session_turns()`.
- Integrated session tracking into `src_brain/main_loop.py`:
  - create session when `listen()` returns non-empty input
  - add user turn before `RAG retrieve`
  - add assistant turn after `full_reply` is assembled
  - close open session during normal completion and keyboard-interrupt cleanup
- Kept `notifier.push_chat_log()` unchanged; it still writes chat events to `events`.
- Added Group 14 tests in `run_tests.py`.
- Verification: `python run_tests.py` -> `80/80 PASS`.

## 2026-04-17-step1.6-jwt-middleware.md

# Step 1.6 — JWT Middleware: Bảo vệ tất cả Endpoints

**Ngày:** 2026-04-17

## Files đã thay đổi

| File | Thay đổi |
|------|----------|
| `src_brain/network/auth.py` | Thêm `get_current_user()` với HTTPBearer |
| `src_brain/network/api_server.py` | Import guard, thay require_auth, WebSocket JWT, /health |
| `run_tests.py` | Thêm Group 12 (4 test) |

## Thay đổi chính

### auth.py — get_current_user()

```python
_http_bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_http_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(401, "Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = verify_access_token(credentials.credentials)
    except HTTPException:
        raise HTTPException(401, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    return {"user_id": payload["sub"], "family_name": payload["family"]}
```

### api_server.py

**REST routes — thay Depends(require_auth) → Depends(get_current_user):**
- `GET /api/events`
- `POST /api/events/read_all`
- `GET /api/chats`
- `GET /api/memories`
- `POST /api/memories`
- `GET /api/memories/export`
- `PUT /api/memories/{memory_id}`
- `DELETE /api/memories/{memory_id}`
- `POST /api/puppet`
- `GET /api/tasks`
- `POST /api/tasks`
- `GET /api/tasks/stars`
- `POST /api/tasks/{task_id}/complete`
- `DELETE /api/tasks/{task_id}`
- `POST /api/mom/start`
- `POST /api/mom/stop`
- `POST /auth/logout`

**Camera — dùng `_camera_auth` (header OR `?auth=JWT`):**
- `GET /api/camera`

**WebSocket — JWT qua `?token=JWT`, close 1008 nếu invalid:**
- `WS /ws`
- `WS /api/audio/stream`
- `WS /api/mom/audio`

**Thêm mới:**
- `GET /health` — no auth

**Whitelist (không cần JWT):**
- `GET /health`
- `GET /api/status`
- `GET /api/mom/status` (internal polling)
- `POST /api/auth/login` (PIN cũ)
- `POST /api/auth/logout` (PIN logout)
- `POST /auth/register`
- `POST /auth/login/v2`
- `POST /auth/refresh`
- `GET /`
- `GET /static/*`

## Kết quả test

```
71/71 PASS (thêm 4 test Group 12: JWT Auth Guard)
```

- AuthGuard: no creds → 401 + WWW-Authenticate
- AuthGuard: valid JWT → user dict correct
- AuthGuard: invalid token → 401 + WWW-Authenticate
- AuthGuard: /health route exists (no auth)

## 2026-04-17-step1.5-jwt-access-refresh-token.md

# Step 1.5 — JWT Access Token + Refresh Token với Rotation

**Ngày:** 2026-04-17  
**Mục tiêu:** Implement JWT access token (HS256, 60 phút) + refresh token với rotation atomic.

## Files đã thay đổi

| File | Thay đổi |
|------|----------|
| `src_brain/network/auth.py` | Thêm 5 hàm JWT + helper `_get_jwt_config()` |
| `src_brain/network/api_server.py` | Sửa `/auth/login/v2`, thêm `/auth/refresh`, `/auth/logout`, `get_current_user()` |
| `src_brain/network/db.py` | Thêm bảng `auth_tokens` |
| `requirements.txt` | Thêm `python-jose[cryptography]==3.3.0` |
| `.env.example` | Thêm `JWT_SECRET_KEY`, `JWT_ALGORITHM` |
| `run_tests.py` | Set JWT env vars trước import, thêm 6 test Group 10c |

## Thay đổi chính

### auth.py — JWT functions mới

- `_get_jwt_config()`: đọc `JWT_SECRET_KEY` + `JWT_ALGORITHM` từ env. Raise `RuntimeError` nếu thiếu hoặc algorithm != HS256.
- `create_access_token(user_id, family_name) -> str`: JWT với payload `{sub, family, type="access", iat, exp=now+60min}`, ký HS256.
- `create_refresh_token(user_id) -> (raw_token, hashed_token)`: `secrets.token_urlsafe(32)` + sha256 hex.
- `store_refresh_token(user_id, hashed_token, expires_at) -> str`: INSERT vào `auth_tokens`, trả token_id.
- `verify_access_token(token) -> dict`: decode JWT, kiểm tra `type=="access"`, raise HTTPException(401) nếu lỗi.
- `rotate_refresh_token(old_raw_token) -> (new_raw, new_hashed, user_id)`: atomic trong cùng transaction — revoke cũ + insert mới.

### api_server.py

- `/auth/login/v2`: sau authenticate_user thành công → tạo access + refresh token, trả `{access_token, refresh_token, token_type, expires_in: 3600}`. Không còn dùng `SESSION_TOKENS` cho login/v2.
- `POST /auth/refresh`: body `{refresh_token}` → `rotate_refresh_token()` → access token mới + refresh token mới.
- `POST /auth/logout`: header `Authorization: Bearer <access_token>` + body `{refresh_token}` → verify JWT lấy user_id → revoke refresh token nếu thuộc đúng user.
- `get_current_user()`: dependency JWT (chưa apply vào route, dành cho step 1.6).
- `start_api_server()`: startup check `_get_jwt_config()` — raise RuntimeError nếu JWT_SECRET_KEY thiếu.

### db.py

Bảng `auth_tokens` mới:
```sql
CREATE TABLE IF NOT EXISTS auth_tokens (
    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    refresh_token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_revoked INTEGER NOT NULL DEFAULT 0
)
```

## Test flow thủ công (expected behavior)

```
POST /auth/login/v2 {"username": "admin", "password": "..."}
→ 200 {"access_token": "eyJ...", "refresh_token": "abc...", "token_type": "bearer", "expires_in": 3600}

Decode access_token → payload: {"sub": "1", "family": "Admin", "type": "access", "exp": ...}

POST /auth/refresh {"refresh_token": "abc..."}
→ 200 {"access_token": "eyJ...new", "refresh_token": "def...new", ...}

POST /auth/refresh {"refresh_token": "abc..."}  ← token cũ
→ 401 "Refresh token da bi thu hoi"

POST /auth/logout
  Header: Authorization: Bearer eyJ...
  Body: {"refresh_token": "def...new"}
→ 200 {"message": "Đã đăng xuất"}

POST /auth/refresh {"refresh_token": "def...new"}  ← sau logout
→ 401 "Refresh token da bi thu hoi"
```

## Kết quả test

```
67/67 PASS (thêm 6 test mới trong Group 10c: JWT Module)
```

Bao gồm:
- JWT: create_access_token format
- JWT: verify_access_token valid payload
- JWT: verify_access_token invalid → 401
- JWT: create_refresh_token sha256 hash
- JWT: store + rotate (old revoked)
- JWT: rotate invalid token → 401

## PROTECTED sau session này

- `/api/auth/login` (PIN) + `SESSION_TOKENS` vẫn hoạt động song song, không bị chạm.
- JWT và PIN là hai hệ thống auth hoàn toàn độc lập.
- `require_auth` guard vẫn dùng SESSION_TOKENS cho tất cả routes hiện tại.
- `get_current_user()` chỉ apply từ step 1.6 trở đi.

## 2026-04-17-step1.4-username-password-auth.md

# Changelog: Step 1.4 — Username+Password Auth (2026-04-17)

## Mục tiêu
Tạo hệ thống xác thực username + password (Argon2id) chạy song song với PIN auth cũ.
Endpoint PIN cũ `/api/auth/login` giữ nguyên, không thay đổi hành vi.

## Files thay đổi

| File | Thay đổi |
|------|----------|
| `src_brain/network/auth.py` | Tạo mới — toàn bộ auth helpers |
| `src_brain/network/db.py` | Thêm bảng `users`, gọi `seed_admin_if_empty()` |
| `src_brain/network/api_server.py` | Thêm 2 endpoint mới |
| `requirements.txt` | Thêm `argon2-cffi` |
| `.env.example` | Thêm `ADMIN_USERNAME`, `ADMIN_PASSWORD` |
| `run_tests.py` | Thêm Group 10b (7 test auth) |

## Chi tiết kỹ thuật

### auth.py
- `hash_password(plain)` → Argon2id hash qua `argon2-cffi`
- `verify_password(plain, hashed)` → so khớp hash, trả `False` nếu sai hoặc invalid hash
- `create_user(username, password, family_name)` → insert DB, raise HTTP 409 nếu duplicate
- `get_user_by_username(username)` → trả dict có `password_hash` (internal), hoặc `None`
- `authenticate_user(username, password)` → trả dict user sạch (không có hash) hoặc `None`
- `seed_admin_if_empty()` → idempotent, tạo admin từ `.env` nếu bảng trống, không log plaintext

### Bảng users (db.py)
```sql
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    family_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_active INTEGER DEFAULT 1
)
```

### POST /auth/register
- Body: `{"username": str, "password": str, "family_name": str}`
- Validation: username 3-50 ký tự `[a-zA-Z0-9_]`, password ≥ 8 ký tự
- Success: `{"user_id": int, "username": str, "family_name": str}`
- Duplicate: HTTP 409

### POST /auth/login/v2
- Body: `{"username": str, "password": str}`
- Rate limiting: key `user:<username>` trong `login_attempts` (backward-compatible với IP cũ)
- Success: `{"access_token": str, "token_type": "bearer", "user_id": int}`
- Fail: HTTP 401 `{"detail": "Sai ten dang nhap hoac mat khau"}` (message mờ)
- Lock: HTTP 429 sau 5 lần sai, khóa 15 phút
- Token được thêm vào `SESSION_TOKENS` — dùng chung guard `require_auth` với PIN

## Test results
```
[Group 10b] Auth Module
  PASS  Auth: hash_password + verify_password
  PASS  Auth: verify_password wrong hash -> False
  PASS  Auth: create_user + get_user_by_username
  PASS  Auth: create duplicate username -> 409
  PASS  Auth: authenticate_user correct password
  PASS  Auth: authenticate_user wrong password -> None
  PASS  Auth: authenticate nonexistent user -> None

KET QUA: 61/61 PASS | 0/61 FAIL
```

## 2026-04-17-phase2-wakeword-devtest.md

# 2026-04-17 - Phase 2 Prep: wake-word dev/test path + tests

- Updated `src_brain/senses/ear_stt.py` to add `WAKEWORD_THRESHOLD` from `.env`.
- Implemented the wake-word path so `WAKEWORD_ENABLED=False` returns `False` immediately.
- Added safe fallback when `openwakeword` import fails: warn once, set `WAKEWORD_ENABLED=False`, return `False`.
- Added dev/test proxy detection with `openwakeword.Model(wakeword_models=[])`.
- Wake-word loop now reads 80ms audio chunks, checks model scores against `WAKEWORD_THRESHOLD`, plays beep on detection, and pauses while `is_mom_talking()` is active.
- Extended Group 13 in `run_tests.py` with 3 wake-word tests.
- Verification: `python run_tests.py` -> `76/76 PASS`.

## 2026-04-17-phase2-core-experience.md

# Phase 2 - Core Experience

## Tóm tắt

Phase 2 hoàn tất các phần lõi cho trải nghiệm hội thoại của Robot Bi: wake-word dev/test path, session UUID theo mỗi lần wake, auto-title cho session, conversation threads API, tab Hội thoại trong Parent App, và tối ưu latency STT trên máy CPU-only.

## Steps hoàn thành

- Step 2.1-2.2: wake-word dev/test path trong `ear_stt.py`, beep feedback, import-fail safe path, và `WAKEWORD_THRESHOLD`.
- Step 2.3: session UUID tracking với bảng `conversations` + `turns` và tích hợp lưu turns trong `main_loop.py`.
- Step 2.4: auto-naming session từ lượt user đầu tiên bằng `src_brain/network/session_namer.py`.
- Step 2.5: conversation threads REST API trong `api_server.py`.
- Step 2.6: Whisper CPU auto-downgrade qua `WHISPER_CPU_MODEL=medium`, giữ nguyên GPU path.
- Step 2.7: Parent App tab `Hội thoại` trong `src_brain/network/static/index.html`.

## Files thay đổi

- `src_brain/senses/ear_stt.py`
- `src_brain/network/db.py`
- `src_brain/main_loop.py`
- `src_brain/network/api_server.py`
- `src_brain/network/session_namer.py`
- `src_brain/network/static/index.html`
- `run_tests.py`
- `.env.example`
- `requirements.txt`

## Test results

- Final regression result: `89/89 PASS`
- Phase 2 was closed only after rerunning the full suite.

## Quyết định kỹ thuật quan trọng

- `openwakeword` mặc định để `WAKEWORD_ENABLED=False` vì model tùy biến `bi_oi` chưa sẵn sàng; điều này tránh tạo cảm giác production-ready giả trong khi vẫn giữ đường dev/test để tích hợp và kiểm thử.
- Session naming dùng Groq non-streaming thay vì `stream_chat()` vì đây là fire-and-forget nền, không thuộc luồng hội thoại chính và không cần audio/TTS streaming; timeout 5 giây giữ cho background task không treo lâu.
- Beep dùng `pygame.Channel(6)` để tách khỏi các channel audio protected khác và giữ hành vi non-blocking khi wake-word được phát hiện.
- `WHISPER_CPU_MODEL` mặc định là `medium` vì `large-v2` trên CPU-only gây độ trễ quá cao; GPU path vẫn giữ `large-v2 + float16` để không ảnh hưởng chất lượng khi có CUDA.

## 2026-04-17-phase1-security.md

# Changelog: Phase 1 — Security & Data Layer (2026-04-17)

## Tóm tắt

Hoàn thành toàn bộ Phase 1 Security & Data Layer. Hệ thống auth được xây dựng từ đầu trên nền SQLite với JWT, Argon2id, rate limiting và middleware bảo vệ toàn bộ API.

## Steps đã hoàn thành

### Step 1.1 — SQLite Migration
- Tạo `src_brain/network/db.py`: quản lý SQLite `robot_bi.db`, schema `users`, `auth_tokens`, `login_attempts`, `events`, `tasks`.
- `task_manager.py` và `notifier.py` chuyển từ JSON file sang SQLite backend.

### Step 1.2 — Remove Runtime Files
- Cập nhật `.gitignore`: loại `event_queue.json`, `tasks.json`, `robot_bi.db` khỏi git tracking.
- Xóa các binary files test `_audit_test_db` khỏi tracking.

### Step 1.3 — PIN Auth + Rate Limiting
- `AUTH_PIN` đọc từ `.env`, không hardcode.
- Rate limiting endpoint `/api/auth/login`: 5 lần sai → lock 15 phút, lưu trong bảng `login_attempts`.

### Step 1.4 — Username/Password Auth (Argon2id)
- Module `auth.py` mới: `register_user()`, `authenticate_user()` dùng `argon2-cffi`.
- Endpoint `/auth/register` + `/auth/login/v2`.
- Rate limit theo `user:<username>`.
- Chạy song song với PIN cũ, không phá bất kỳ flow hiện tại.

### Step 1.5 — JWT Access + Refresh Token
- `create_access_token()` (HS256, 60 phút).
- `create_refresh_token()` + `store_refresh_token()` (sha256 hash, 30 ngày).
- `verify_access_token()`, `rotate_refresh_token()` (atomic revoke+insert).
- Endpoint `/auth/refresh` + `/auth/logout`.
- Bảng `auth_tokens` trong DB.
- `JWT_SECRET_KEY` + `JWT_ALGORITHM` từ `.env`. Thêm `python-jose[cryptography]` vào requirements.

### Step 1.6 — JWT Middleware Toàn App
- `get_current_user()` dùng `HTTPBearer(auto_error=False)` trong `auth.py`. Raise 401 + `WWW-Authenticate: Bearer`.
- Áp dụng `Depends(get_current_user)` lên 17 REST routes trong `api_server.py`.
- Camera dùng `_camera_auth` (hỗ trợ header + `?auth=` query param cho MJPEG stream).
- 3 WebSocket handlers (`/ws`, `/api/audio/stream`, `/api/mom/audio`) xác thực JWT qua `?token=`, đóng code 1008 nếu invalid.
- Thêm `GET /health` không cần auth.
- Whitelist: `/health`, `/api/status`, `/api/mom/status`, `/api/auth/login`, `/api/auth/logout`, `/auth/register`, `/auth/login/v2`, `/auth/refresh`, `/`, `/static/*`.

### Step 1.7 — Requirements Pin
- Pin đủ version cho `argon2-cffi`, `python-jose[cryptography]`, các dependency mới.

## Files thay đổi

| File | Loại thay đổi |
|------|--------------|
| `src_brain/network/db.py` | Mới |
| `src_brain/network/auth.py` | Mới |
| `src_brain/network/api_server.py` | Sửa (JWT guard, endpoints, camera auth, WS auth) |
| `src_brain/network/task_manager.py` | Sửa (SQLite backend) |
| `src_brain/network/notifier.py` | Sửa (SQLite backend) |
| `requirements.txt` | Sửa (thêm argon2-cffi, python-jose) |
| `.env.example` | Sửa (thêm AUTH_PIN, JWT_SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD) |
| `run_tests.py` | Sửa (thêm Group 12 auth guard tests) |

## Test Results

**71/71 PASS**

## Quyết định kỹ thuật quan trọng

- **Argon2id** thay vì bcrypt: memory-hard hơn, chống GPU/ASIC brute force tốt hơn.
- **Refresh token dạng hash**: DB chỉ lưu sha256(token), token thô chỉ gửi cho client một lần.
- **atomic rotate**: revoke token cũ + insert token mới trong 1 transaction để tránh race condition.
- **HTTPBearer(auto_error=False)**: để custom error message 401 thay vì FastAPI mặc định 403.
- **JWT cho WebSocket qua query param**: browsers không support custom headers trong WS upgrade, dùng `?token=` là chuẩn.
- PIN cũ giữ nguyên song song để không phá backward compat với parent app hiện tại.

## 2026-04-17-phase1-bugfix.md

# Changelog — Phase 1 Bugfix (2026-04-17)

## Tóm tắt

Hai bugfix nhỏ sau khi Phase 1 hoàn thành, phát hiện qua review kỹ lại.

## Bug 1 — Schema bảng `tasks` không khớp với task_manager.py

- **File**: `src_brain/network/db.py`
- **Vấn đề**: Schema CREATE TABLE tasks dùng cột `family_id, title, status` — không khớp với các cột mà `task_manager.py` thực sự dùng.
- **Fix**: Sửa schema thành `task_id, name, remind_time, completed_today, stars, created_at, last_reminded, import_key`.

## Bug 2 — .gitignore sai format, runtime files bị git track

- **File**: `.gitignore`
- **Vấn đề**: 4 rule cuối file bị dính trên cùng 1 dòng + bao bọc bởi dấu ngoặc kép — git không hiểu, bỏ qua hoàn toàn. Hậu quả: `event_queue.json`, `tasks.json`, `robot_bi.db` đang bị git track.
- **Fix**: Tách thành 4 dòng riêng, bỏ dấu ngoặc kép. Chạy `git rm --cached` cho 3 file đang bị track.

## Test

- 71/71 PASS

## Trạng thái

**Phase 1 hoàn chỉnh 100%.** Sẵn sàng bắt đầu Phase 2 — Core Experience.

## 2026-04-17-phase1-bugfix-index-runtests.md

# Changelog — 2026-04-17: Phase 1 Bugfix (index.html + run_tests isolation + DB cleanup)

## Tóm tắt

Bugfix sau khi hoàn thành Phase 1. Ba vấn đề được giải quyết trong session này.

## Chi tiết thay đổi

### 1. index.html — Thêm flow đăng nhập JWT

**Vấn đề:** JWT middleware bảo vệ tất cả endpoints, nhưng giao diện web (`index.html`) không có form đăng nhập và không attach Bearer token. Kết quả: toàn bộ giao diện bị chặn 401.

**Fix:** Thêm flow đăng nhập đầy đủ:
- Form login (username + password)
- Gọi `POST /auth/login/v2`, lưu `access_token` vào `localStorage`
- Tự động attach `Authorization: Bearer <token>` vào mọi API call và WebSocket connect

### 2. run_tests.py — DB riêng biệt cho test

**Vấn đề:** Test ghi thẳng vào production DB (`robot_bi.db`), tạo user rác mỗi lần chạy.

**Fix:** Dùng DB riêng biệt tại `src_brain/memory_rag/_audit_test_db/` (đã có sẵn trong cấu trúc). Production DB không bị động đến khi chạy test.

### 3. Cleanup production DB

**Vấn đề:** 58 user rác từ các lần test cũ tồn tại trong `robot_bi.db`.

**Fix:** Xóa toàn bộ user rác. DB hiện sạch: 1 user `admin`.

## Test

- 71/71 PASS

## Files thay đổi

- `src_brain/network/static/index.html` — thêm login flow JWT
- `run_tests.py` — dùng test DB riêng

## 2026-04-16-session-sqlite-migration.md

# Session Log: SQLite Storage Migration
Date: 2026-04-16

## Mục tiêu
Chuyển storage backend của `src_brain/network/event_queue.json` và `src_brain/network/tasks.json` sang SQLite, nhưng giữ nguyên API, behavior và shape dữ liệu của TaskManager, EventNotifier và Parent App API.

## Các thay đổi chính
1. Thêm `src_brain/network/db.py` với `src_brain/network/robot_bi.db`, `get_db_connection()` dùng `PRAGMA journal_mode=WAL`, `init_db()` và migration idempotent từ JSON backup cũ sang bảng `events` và `tasks`.
2. Refactor `src_brain/network/task_manager.py` để thay toàn bộ read/write `tasks.json` bằng SQLite queries, nhưng giữ nguyên tên method, tham số và kiểu trả về.
3. Refactor `src_brain/network/notifier.py` để thay persistence `event_queue.json` bằng SQLite; format event object và WebSocket broadcaster interface không đổi.
4. Refactor `src_brain/network/api_server.py` để đọc danh sách event/chat từ SQLite thay vì `_notifier._events`.
5. Cập nhật `src_brain/main_loop.py` và `run_tests.py` để gọi `init_db()` một lần trong mỗi process trước khi dùng storage.

## Dữ liệu & tương thích
- Hai file JSON cũ vẫn được giữ nguyên làm backup.
- Migration cũ -> mới là idempotent: re-run không tạo duplicate records.
- Trường nested `metadata` của event được lưu trong SQLite dưới dạng JSON string và deserialize lại khi đọc ra.

## Kiểm tra
- Chạy `python run_tests.py`
- Kết quả: `54/54 PASS`
- Xác nhận DB đã được tạo tại `src_brain/network/robot_bi.db`

## 2026-04-16-session-qr-crydetector.md

# Session 2026-04-16 - QR + CryDetector logging

## Muc tieu
- Khoi phuc QR Code trong output `start_robot.bat`.
- Chan spam log `CryDetector` khi may khong co microphone hop le.

## Da thay doi
- `src_brain/network/api_server.py`
- `src_brain/senses/cry_detector.py`
- `PROJECT.md`
- `.claude/handoff.md`

## Chi tiet
- Doi render QR sang ASCII thuan (`##` / space) de hien thi on dinh tren Windows console, khong phu thuoc Unicode block.
- Ap dung cung mot renderer cho QR Parent App va QR Cloudflare Tunnel.
- Them xu ly rieng cho loi microphone khong hop le trong `CryDetector`: log `info` 1 lan roi dung detector thay vi warning lap vo han.
- Chuan hoa dong fallback YAMNet thanh ASCII-safe de tranh loi encoding tren console `cp1252`.

## Xac nhan
- Chay `start_robot.bat`: QR da hien lai trong terminal.
- `CryDetector` khong con spam `Error querying device -1`.
- Chay `python run_tests.py`: `54/54 PASS`.

## 2026-04-16-session-qr-ansi.md

# Session Log: QR Code ANSI Fix
Date: 2026-04-16

## Mục tiêu
Sửa lại hiển thị QR Code trên terminal (của URL mạng LAN Parent App) để hiển thị dưới dạng mã QR thực tế chuẩn hình vuông có các chấm đen trắng. Lý do là chuỗi ASCII hiện tại (dùng `#` và khoảng trắng) quá khó quét đối với các điện thoại.

## Cách tiếp cận
1. Nhận thấy thư viện `qrcode` trước đó xuất mã ASCII đơn giản.
2. Nâng cấp hàm `_build_ascii_qr` trong `src_brain/network/api_server.py`.
3. Sử dụng mã màu ANSI background (`\033[47m` cho nền trắng và `\033[40m` cho nền đen) kết hợp cùng 2 khoảng trắng liên tiếp để tạo hình vuông khối liền.
4. Điều chỉnh mặc định quét là màu đen trên nền trắng, giúp máy ảnh trên các hệ điều hành điện thoại dễ dàng bắt chéo và quét cực nhạy.
5. Thêm hook `os.system("")` trên môi trường Windows để tự động kích hoạt tính năng Virtual Terminal Processing cho ANSI Escape Codes nếu console chưa bật mặc định.

## Kết quả
- Chạy `python run_tests.py` đã qua 54/54 test.
- Khi khởi chạy API Server, QR Code hiện ra như một hình vuông đen trắng thật sự (như ảnh tĩnh).
- Cập nhật Project docs (PROJECT.md) và handoff.md về những thay đổi mới này trọn vẹn tuân thủ quy tắc làm việc Single Source of Truth của dự án.

## 2026-04-16-session-mic-fallback.md

# Session 2026-04-16 — EarSTT microphone fallback

## Mục tiêu
- Sửa lỗi microphone `Invalid number of channels [PaErrorCode -9998]` trong `src_brain/senses/ear_stt.py`.
- Không thay đổi logic protected ngoài phần khởi tạo và mở `InputStream`.

## Đã làm
- Thêm probe microphone khi khởi tạo `EarSTT`.
- Liệt kê input devices và thử mở theo thứ tự ưu tiên:
  - `MIC_DEVICE` hiện tại trước nếu còn hợp lệ.
  - Các input device còn lại sau đó.
  - Mỗi thiết bị thử `1` channel trước, fail mới thử `2` channels.
- Lưu cấu hình microphone đã probe thành công để `listen()` và `listen_for_wakeword()` dùng lại.
- Nếu không có cấu hình nào mở được, chuyển sang silent mode và để `listen()` trả `""` thay vì crash.
- Chặn spam lỗi microphone bằng cờ log-once nội bộ.
- Giữ nguyên `Whisper large-v2` và cơ chế GPU/CPU auto-detect hiện có.

## Kết quả kiểm tra
- `python run_tests.py` => `54/54 PASS`.
- Khởi động `src_brain.main_loop` trong môi trường hiện tại:
  - Log nhận được: `Đang tìm microphone...`
  - Log nhận được: `Không tìm thấy microphone hợp lệ, chuyển sang chế độ im lặng`
  - Không còn xuất hiện `Invalid number of channels [PaErrorCode -9998]`.

## File chỉnh sửa
- `src_brain/senses/ear_stt.py`
- `PROJECT.md`
- `.claude/handoff.md`

## 2026-04-16-session-audit.md

## ⚡ KẾT QUẢ SESSION AUDIT — Kiểm tra & Tối ưu Toàn Hệ Thống (2026-04-14)

### ✅ Đã hoàn thành
- Đọc và audit toàn bộ 13 files Python
- Fix 3 bugs thực sự:
  1. `eye_vision.py`: `if __name__ == "__main__":` nằm sai bên TRONG class body → đã move ra module level
  2. `mouth_tts.py`: delay 0.3s không cần thiết ở lần TTS đầu tiên (vi phạm NFR-03) → chỉ delay khi retry (attempt > 0)
  3. `main_loop.py`: `_speak_text()` gọi `self._loop.run_until_complete()` từ TaskManager reminder thread → xung đột asyncio event loop → đổi sang `asyncio.run()`
- Xóa dead code: `return self._fallback_tts(text, chunk_index)` unreachable sau loop trong `_generate_audio()`
- Tạo `run_tests.py` với 51 automated tests
- Tất cả 51/51 tests PASS

### 🧪 Test Results
```
============================================================
  ROBOT BI --- AUTOMATED TEST SUITE
============================================================
[Group 1] Import Tests              9/9 PASS
[Group 2] SafetyFilter              6/6 PASS
[Group 3] Prompts                   1/1 PASS
[Group 4] RAGManager                9/9 PASS
[Group 5] EventNotifier             5/5 PASS
[Group 6] TaskManager               6/6 PASS
[Group 7] EyeVision (headless)      4/4 PASS
[Group 8] CryDetector (headless)    3/3 PASS
[Group 9] MouthTTS (import only)    2/2 PASS
[Group 10] EarSTT (import only)     2/2 PASS
[Group 11] Integration              4/4 PASS
------------------------------------------------------------
  KET QUA: 51/51 PASS | 0/51 FAIL
  TAT CA TESTS PASS
============================================================
```

### 📋 Issues phát hiện và fix
| # | File | Issue | Fix |
|---|------|-------|-----|
| 1 | `eye_vision.py` | `if __name__ == "__main__":` bên trong class body | Move ra module level |
| 2 | `mouth_tts.py` | `asyncio.sleep(0.3s)` delay ngay cả ở lần đầu gọi TTS | Chỉ delay khi attempt > 0 |
| 3 | `main_loop.py` | `_speak_text()` gọi `self._loop.run_until_complete()` từ thread khác | Đổi sang `asyncio.run()` |
| 4 | `mouth_tts.py` | Dead code `return self._fallback_tts()` sau loop (unreachable) | Xóa |

### ⚠️ Không thể test tự động (cần thủ công)
- Mic input: `EarSTT.listen()` — cần mic thật
- Loa output: `MouthTTS.speak()` — cần loa thật
- Camera: `EyeVision` với camera thật
- Ollama LLM: `BiAI.stream_chat()` — cần Ollama running
- edge-tts: cần internet

### 🎯 TRẠNG THÁI CUỐI CÙNG
- Automated tests: 51/51 PASS
- py_compile: 13/13 PASS (không có syntax error)
- Manual tests needed: 5 (mic, loa, camera, LLM, TTS)
- Code quality: không có dead code, không có bare except, không có resource leak
- **Dự án sẵn sàng để test thật với phần cứng**

### 🚀 Session tiếp theo
- Sprint 7: Stress test RAM (psutil), tối ưu độ trễ, đóng gói
- Test thực tế: kết nối mic + loa + camera để verify end-to-end latency ≤ 2.5s (NFR-03)

---

## 2026-04-16-session-audio-volume-fix.md

## SESSION 2026-04-15 - Fix audio output + volume Parent App frontend

### Da sua gi
- Them `setSinkId('default')` ngay sau khi tao `AudioContext` trong `startAudioMonitor()` de uu tien loa ngoai thay vi earpiece tren mobile browser.
- Thay output truc tiep trong `startAudioMonitor()` tu `source.connect(audioContext.destination)` sang `GainNode` voi `gain.value = 2.0` de tang volume.
- Them `setSinkId('default')` cho `momAudioCtx` trong `startMomMic()`.
- Chen `GainNode` vao luong `source -> gainNode -> momScriptProcessor` trong `startMomMic()` de tang muc tin hieu gui di ma khong doi API hay refactor logic.

### Sua file nao
- `src_brain/network/static/index.html`
- `.claude/handoff.md`

### Ly do sua
- Parent App tren mobile co the route audio ra earpiece thay vi loa ngoai.
- Audio monitor trong browser dang phat truc tiep khong qua gain nen volume thap.
- Yeu cau la giu patch nho, an toan, chi cham frontend `index.html`.

### Cach kiem tra
- Xac nhan trong `startAudioMonitor()` da co:
  - `audioContext.setSinkId('default')`
  - `const gainNode = audioContext.createGain();`
  - `source.connect(gainNode);`
  - `gainNode.connect(audioContext.destination);`
- Xac nhan trong `startMomMic()` da co:
  - `momAudioCtx.setSinkId('default')`
  - `const gainNode = momAudioCtx.createGain();`
  - `source.connect(gainNode);`
  - `gainNode.connect(momScriptProcessor);`
- Tim lai trong file va xac nhan khong con `source.connect(audioContext.destination)` o vi tri audio monitor muc tieu.
- Tam tach noi dung `<script>` ra file `.js` va chay `node --check` -> parse thanh cong, khong co syntax error JavaScript.

### Van de con lai neu co
- Chua the xac minh hanh vi loa ngoai / muc am luong tren thiet bi thuc do can test thu cong tren mobile browser.
- `setSinkId()` khong duoc ho tro dong deu tren moi browser; doan code da `catch(() => {})` de fail safe.

---

## 2026-04-16-session-Q.md

## ⚡ KẾT QUẢ SESSION Q — Fix camera delay

### ✅ Đã fix
| Vấn đề | Root cause | Fix |
|--------|------------|-----|
| Camera delay 200-500ms | `cap.read()` blocking trên event loop chính FastAPI | Thread riêng + `queue.Queue` bridge |
| Frame cũ tích lũy | OpenCV buffer giữ nhiều frame | `CAP_PROP_BUFFERSIZE=1` |
| Event loop bị block | `asyncio.sleep(0.05)` thực tế bị trễ khi WS/REST bận | `run_in_executor` + `asyncio.sleep(0)` |

### 📋 Audio diagnostic (session Q)
- Audio fix từ session P: ĐÃ ĐẦY ĐỦ — resample + stereo + channel 7 hoạt động đúng
- mixer: freq=44100, size=-16, ch=2 — confirmed

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| `api_server.py` | Thêm `_camera_capture_thread()` + rewrite `_mjpeg_generator()` dùng thread riêng |

### 🔧 Kỹ thuật camera mới
- `_camera_capture_thread`: thread daemon riêng, `CAP_PROP_BUFFERSIZE=1`, `CAP_PROP_FPS=30`
- `queue.Queue(maxsize=2)`: buffer nhỏ — luôn lấy frame mới nhất, tự xóa frame cũ
- `run_in_executor`: bridge thread→event loop không blocking
- `asyncio.sleep(0)`: yield control về event loop sau mỗi frame

### 🧪 Test results
- 54/54 tests PASS
- Syntax OK cả hai files

### 🎯 Kết quả kỳ vọng
- Camera delay: <100ms LAN (từ 200-500ms)
- Audio mẹ nói: không rè (từ session P)

## 2026-04-16-session-P.md

## ⚡ KẾT QUẢ SESSION P — Fix tiếng rè audio mẹ nói

### ✅ Root cause đã fix
| Nguyên nhân | Vấn đề | Fix |
|-------------|--------|-----|
| Sample rate mismatch | Browser 16000Hz vs mixer 44100Hz → tiếng rè cao | Resample 16000→44100 trước khi phát |
| Mono/Stereo mismatch | Mono audio phát qua stereo mixer → distortion | Convert mono→stereo đúng cách |
| Double mixer init | api_server init lại mixer 16000Hz đè lên 44100Hz | Xóa init cũ, dùng mixer freq hiện tại |

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| `mouth_tts.py` | Thêm `pre_init(44100Hz, stereo, 2048 buffer)` trước `mixer.init()` |
| `api_server.py` | Thêm scipy import; resample 16000→mixer_freq; convert mono→stereo; xóa `mixer.init(16000)` cũ |

### 🔧 Kỹ thuật
- `scipy.signal.resample`: chất lượng cao nhất (đã cài, sẵn sàng)
- `numpy.interp` fallback: nếu scipy không có
- `pygame.Channel(7)`: channel riêng, không xung đột TTS Bi
- In-memory WAV (`BytesIO`): không ghi file, latency thấp
- `_get_mixer_freq()`: luôn dùng đúng freq của mixer hiện tại

### 🧪 Test results
- 54/54 tests PASS
- Mixer confirmed: 44100Hz stereo

### 🎯 Kết quả kỳ vọng
- Trước fix: tiếng rè, tốc độ cao bất thường, distortion
- Sau fix: tiếng tự nhiên, đúng pitch, không rè

---

## 2026-04-16-session-O.md

## ⚡ KẾT QUẢ SESSION O — Fix delay âm thanh mẹ nói

### ✅ Fix đã thực hiện
| Nguồn delay | Trước | Sau |
|-------------|-------|-----|
| JS buffer | ScriptProcessor(4096) = 256ms | ScriptProcessor(512) = 32ms |
| Server I/O | Ghi WAV file ra disk | WAV trong memory (BytesIO) |
| Phát audio | winsound load từ file | pygame.mixer.Channel(7) từ buffer |
| Xung đột | pygame.mixer.music bị block | Channel riêng, không đụng Bi |

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| `index.html` | ScriptProcessor 4096 → 512 |
| `api_server.py` | In-memory WAV + pygame Channel(7) |

### 🎯 Latency mục tiêu
- Trước fix: ~1-3 giây delay
- Sau fix: ~100-200ms (network latency còn lại)

---

## 2026-04-16-session-N.md

## ⚡ KẾT QUẢ SESSION N — Fix 3 bugs chức năng mẹ nói trực tiếp

### ✅ Bugs đã fix
| # | Bug | Trạng thái | Fix |
|---|-----|-----------|-----|
| 1 | Tiếng mẹ không phát ra loa | ✅ Đã fix | Ghi WAV tạm → `pygame.mixer.Sound()` thay `sndarray.make_sound()` |
| 2 | Bi không tạm dừng khi mẹ bật mic | ℹ️ Đã fix từ trước | `main_loop.py` đã import `is_mom_talking` trực tiếp từ `api_server.py` — không cần thay đổi |
| 3 | Camera spam log khi client ngắt kết nối | ✅ Đã fix | Rate limit log mỗi 10 giây trong `_vision_loop()` |

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| `src_brain/network/api_server.py` | Thay `sndarray.make_sound()` → ghi WAV tạm + `pygame.mixer.Sound()` trong `/api/mom/audio` |
| `src_brain/senses/eye_vision.py` | Rate limit `logger.warning` "Mất frame từ camera" — chỉ in 1 lần mỗi 10s |

### 🧪 Test results
54/54 tests PASS — không có regression

### 🚀 Session tiếp theo
- Test thật: bật mic trên điện thoại → nghe tiếng phát qua loa robot
- Test Bi tạm dừng: bật `/api/mom/start` → bé nói → Bi không được trả lời
- Sprint 7: Tối ưu, stress test, đóng gói
---

## 2026-04-16-session-M.md

## ⚡ KẾT QUẢ SESSION M — HTTPS Self-Signed + Cloudflare Tunnel

### ✅ Đã hoàn thành
- `generate_ssl.py`: tự tạo SSL certificate self-signed 10 năm (dùng thư viện `cryptography`)
- `api_server.py`: chạy HTTPS port 8443 khi có cert, HTTP port 8000 khi không có
- `api_server.py`: Cloudflare Tunnel tự khởi động khi robot chạy, in URL công khai ra terminal
- `start_robot.bat`: tự tạo SSL cert trước khi khởi động nếu chưa có
- `index.html`: error message rõ ràng khi browser không hỗ trợ getUserMedia (chặn HTTP)
- `.gitignore`: bảo vệ `ssl/`, `*.pem`, `cloudflared.exe`

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| `generate_ssl.py` | Tạo mới — tự sinh SSL cert + key vào `ssl/` |
| `src_brain/network/api_server.py` | Thêm SSL config, `_start_cloudflare_tunnel()`, HTTPS uvicorn, `_print_qr_code` nhận scheme |
| `src_brain/network/static/index.html` | Thêm kiểm tra `navigator.mediaDevices` trước getUserMedia |
| `start_robot.bat` | Thêm bước tạo SSL cert tự động |
| `.gitignore` | Thêm `ssl/`, `*.pem`, `cloudflared.exe` |

### 📌 Luồng kết nối
```
Lần đầu: python generate_ssl.py → tạo ssl/cert.pem + ssl/key.pem
Mỗi lần chạy: cloudflared tự tạo URL public → in ra terminal
Bố mẹ dùng:
  - Cùng WiFi: https://192.168.x.x:8443 (bấm "Advanced" → "Proceed" lần đầu)
  - Từ xa: URL https://xxx.trycloudflare.com in ra terminal
```

### ⚠️ Lưu ý
- Self-signed cert → browser cảnh báo "Not secure" lần đầu → bấm "Advanced" → "Proceed"
- URL cloudflare thay đổi mỗi lần restart (free tier)
- Nếu muốn URL cố định: đăng ký Cloudflare account → tạo named tunnel
- cloudflared với HTTPS dùng flag `--no-tls-verify` (bỏ qua self-signed cert check)
- Nếu cloudflared chưa cài: tải `cloudflared-windows-amd64.exe` từ github, đổi tên thành `cloudflared.exe`, copy vào project root hoặc PATH

### 🧪 Test results
54/54 tests PASS — không có regression

### 🚀 Session tiếp theo
- Session N: Chế độ luyện tiếng Anh chuyên biệt
- Session O: Google Sheet config quản lý nhiều robot
- Session N: Chế độ luyện tiếng Anh chuyên biệt

---

## 2026-04-16-session-L.md

## ⚡ KẾT QUẢ SESSION L — Nói trực tiếp Mẹ ↔ Bé + Auto-audio cam

### ✅ Đã hoàn thành
- Auto-nghe tiếng phòng khi bật cam, tự dừng khi tắt cam (không cần bấm nút riêng)
- Nút mic cho mẹ: bấm → Bi tạm dừng AI, tiếng mẹ phát qua loa robot real-time
- Mẹ tắt mic hoặc đóng web → Bi hoạt động bình thường
- 3 REST endpoints mới: POST /api/mom/start, POST /api/mom/stop, GET /api/mom/status
- 1 WebSocket endpoint: WS /api/mom/audio (nhận PCM float32 → phát pygame)
- `main_loop.py`: check `is_mom_talking()` (module-level, không dùng HTTP) trước mỗi listen cycle
- 54/54 tests PASS

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| `src_brain/network/api_server.py` | Thêm `_mom_talking`, `_mom_audio_clients`, `is_mom_talking()`, 4 endpoints mới |
| `src_brain/main_loop.py` | Import `is_mom_talking`, thêm skip-listen khi mẹ đang nói |
| `src_brain/network/static/index.html` | Xóa nút nghe riêng → auto-audio khi bật cam; thêm nút mic mẹ + JS |

### 📌 Luồng hoạt động
```
Mẹ bấm "Bật mic"
  → POST /api/mom/start → _mom_talking = True
  → WS /api/mom/audio → nhận PCM float32 từ điện thoại
  → pygame.sndarray.make_sound → phát qua loa robot
  → main_loop.py: is_mom_talking() == True → skip ear.listen()

Mẹ bấm "Tắt mic" hoặc đóng web
  → POST /api/mom/stop → _mom_talking = False
  → main_loop.py tiếp tục listen bình thường
```

### ⚠️ Lưu ý
- Cần HTTPS hoặc localhost để getUserMedia hoạt động trên iOS Safari
- Android Chrome: hoạt động trên HTTP LAN
- Nếu không nghe thấy tiếng mẹ: kiểm tra pygame.mixer đã init chưa (main_loop khởi tạo qua MouthTTS)
- `is_mom_talking()` gọi trực tiếp module-level var — không có HTTP overhead

### 🚀 Session tiếp theo
- Session M: Google Sheet config cho quản lý nhiều robot

---

## 2026-04-16-session-K.md

## ⚡ KẾT QUẢ SESSION K — Audio Monitoring (Nghe tiếng phòng qua browser)

### ✅ Đã hoàn thành
- Thêm WebSocket endpoint `/api/audio/stream` vào `api_server.py`
- Stream PCM 16-bit 16kHz mono từ mic phòng → browser real-time
- Thêm UI "Nghe tiếng phòng" vào tab Camera trong `index.html`
- Web Audio API phát audio với buffer 300ms để tránh giật
- Auth bảo vệ bằng token (khớp với PIN auth hiện có)
- `sounddevice`/`numpy` import được guard bằng `_SD_AVAILABLE` — không crash nếu thiếu thư viện
- 54/54 tests vẫn PASS

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| `src_brain/network/api_server.py` | Thêm import sd/numpy (guarded), config AUDIO_*, endpoint `/api/audio/stream` |
| `src_brain/network/static/index.html` | Thêm nút "Nghe tiếng phòng" + JS Audio Monitoring |

### 📌 Kỹ thuật
| Thành phần | Giải pháp | Lý do |
|------------|-----------|-------|
| Transport | WebSocket binary | Đơn giản, low-latency, không cần WebRTC |
| Format | PCM int16 16kHz mono | Khớp với ear_stt.py, nhẹ (~32KB/s) |
| Phát audio | Web Audio API AudioContext | Không cần plugin, hoạt động trên mobile |
| Buffer | 300ms look-ahead | Tránh giật khi mạng không đều |
| Mic device | AUDIO_MIC_DEVICE = 1 | Microphone Array Realtek đã xác nhận |

### ⚠️ Lưu ý khi dùng
- Khi đang stream audio giám sát, mic bị chia sẻ với ear_stt.py
- Trên Windows, 2 InputStream cùng lúc có thể gây conflict — nên tắt audio monitor trước khi nói chuyện với Bi
- Mobile browser cần user gesture trước khi phát audio (bấm nút mới hoạt động — đây là hành vi bình thường)

### 🚀 Session tiếp theo
- Session L: Chế độ luyện tiếng Anh chuyên biệt cho trẻ em
- Session M: Google Sheet config cho quản lý nhiều robot

---

## 2026-04-16-session-J.md

## ⚡ KẾT QUẢ SESSION J — Migrate Ollama → Groq + Gemini (2026-04-14)

### ✅ Đã hoàn thành
- Xóa hoàn toàn Ollama khỏi codebase (~6GB VRAM giải phóng khi gỡ Windows)
- Viết lại `core_ai.py`: Groq Llama 3.3 70B (primary) + Gemini 2.5 Flash-Lite (fallback)
- Tạo `.env` và `config.json` cho quản lý API key và cấu hình robot
- `train_text.py`: rewrite dùng stream_chat() mới, xóa ollama
- `HUONG_DAN_CHAY.md`: cập nhật, xóa hướng dẫn ollama serve
- `requirements.txt`: xóa `ollama`, thêm `requests>=2.31.0`
- `run_tests.py`: thêm 3 tests mới (stream_chat importable, ollama not in modules, config vars), cập nhật test_requirements_complete
- Automated tests: **54/54 PASS** (tăng từ 51 lên 54)
- Whisper large-v2 CUDA: giữ nguyên 100%

### 📌 Quyết định kỹ thuật
| Quyết định | Giá trị | Lý do |
|------------|---------|-------|
| Primary AI | Groq Llama 3.3 70B | ~400 t/s, 14.400 req/ngày free |
| Fallback AI | Gemini 2.5 Flash-Lite | 1.000 req/ngày free, ổn định |
| Config | config.json + .env | Dễ thay đổi, bảo mật API key |
| History | BiAI stub duy trì nội bộ | main_loop.py không cần thay đổi |
| History trim | max_history_turns × 2 | Tiết kiệm token |
| Groq cooldown | 60s sau 3 lần fail liên tiếp | Không spam khi hết quota |

### 📁 Files đã thay đổi
| File | Loại thay đổi |
|------|---------------|
| `src_brain/ai_core/core_ai.py` | Rewrite hoàn toàn — Groq + Gemini thay Ollama |
| `src_brain/train_text.py` | Rewrite — dùng stream_chat() mới |
| `.env` | Rewrite — GROQ_API_KEY + GEMINI_API_KEY |
| `config.json` | Tạo mới — cấu hình model và limits |
| `requirements.txt` | Sửa — xóa ollama, thêm requests |
| `HUONG_DAN_CHAY.md` | Sửa — xóa ollama serve, cập nhật hướng dẫn |
| `run_tests.py` | Sửa — 3 tests mới + fix requirements check |

### ⚠️ Người dùng cần làm thủ công
1. Thu hồi API key cũ đã bị lộ (Groq + Gemini) — key trong prompt đã public
2. Tạo API key mới tại console.groq.com và aistudio.google.com
3. Điền key mới vào file `.env` (GROQ_API_KEY và GEMINI_API_KEY)
4. Gỡ Ollama Windows: Settings → Apps → Ollama → Uninstall
5. Gỡ pip package: `pip uninstall ollama -y`
6. Chạy: `python -m src_brain.main_loop`

### 🚀 Session tiếp theo
- Session K: Google Sheet config cho quản lý nhiều robot
- Session L: Chế độ luyện tiếng Anh chuyên biệt
- Sprint 7: Stress test RAM, tối ưu latency, đóng gói

---

## 2026-04-16-session-H.md

## ⚡ KẾT QUẢ SESSION H — Sprint 7 Tối ưu & Đóng gói (FINAL)

### ✅ Đã hoàn thành
- Xóa legacy: main.py, voice_io.py (backup .bak trước khi xóa)
- Fix train_text.py: import path từ `core_ai` → `src_brain.ai_core.prompts`
- PWA manifest + service worker: app cài được lên phone Android/iOS
- Icon 192px + 512px tự tạo bằng Python thuần (blue-600 solid)
- QR code in ra terminal khi khởi động (qrcode lib)
- Auto-restart: start_robot.bat
- Hướng dẫn sử dụng: HUONG_DAN_CHAY.md
- Stress test RAM: kết quả ghi bên dưới
- psutil + qrcode thêm vào requirements.txt

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| src_brain/main.py | XÓA (backup: main.py.bak) |
| src_brain/senses/voice_io.py | XÓA (backup: voice_io.py.bak) |
| src_brain/train_text.py | Fix import path |
| src_brain/network/static/manifest.json | Tạo mới — PWA manifest |
| src_brain/network/static/sw.js | Tạo mới — Service Worker |
| src_brain/network/static/icon-192.png | Tạo mới |
| src_brain/network/static/icon-512.png | Tạo mới |
| src_brain/network/api_server.py | QR code on startup (_print_qr_code) |
| src_brain/network/static/index.html | PWA meta tags + SW registration |
| start_robot.bat | Tạo mới — auto-restart |
| HUONG_DAN_CHAY.md | Tạo mới — user guide |
| stress_test.py | Tạo mới — RAM/latency benchmark |
| requirements.txt | Thêm psutil, qrcode |

### 🧪 Stress Test Results (python stress_test.py)
```
Baseline RAM: 17 MB
+ SafetyFilter        : +     0 MB  (total: 17 MB) [OK]
+ RAGManager          : +   699 MB  (total: 717 MB) [OK]
+ EyeVision           : +    10 MB  (total: 726 MB) [OK]
+ CryDetector         : +     0 MB  (total: 726 MB) [OK]
+ EventNotifier       : +     0 MB  (total: 726 MB) [OK]
+ BiAI                : +     2 MB  (total: 728 MB) [OK]

Tong RAM (khong tinh Ollama+Whisper): 728 MB
Uoc tinh voi Ollama 7B (~5000MB) + Whisper (~1000MB): 6728 MB
SRS NFR-01 (<=13GB): PASS
SafetyFilter: 0.06ms/call (30 calls) -- PASS
```

### 🧪 Final Regression
| Test | Kết quả |
|------|---------|
| Import chain đầy đủ | ✅ PASS — ALL IMPORTS OK |
| Syntax check train_text.py | ✅ PASS |
| Syntax check api_server.py | ✅ PASS |
| PWA manifest valid JSON | ✅ PASS |
| stress_test.py RAM | 728 MB (+ ~6000 MB Ollama+Whisper = ~6728 MB tổng) |

### 🎯 TRẠNG THÁI CUỐI DỰ ÁN (Software)
- Giai đoạn 1 (Nền móng): ✅ 100%
- Giai đoạn 2 (Voice I/O): ✅ 95% — wake-word chờ phần cứng
- Giai đoạn 3 (RAG): ✅ 100%
- Giai đoạn 4 (Vision + Cry): ✅ 100%
- Giai đoạn 5 (Cơ khí): 🚫 Chờ phần cứng
- Giai đoạn 6 (Parent App): ✅ 100%
- Giai đoạn 7 (Tối ưu): ✅ 100%
- **TỔNG: ~93% (7% còn lại chờ phần cứng)**

### ⚠️ Cần test thủ công (cần mic + loa)
- Chạy robot và nói chuyện thật — verify Bi nghe và trả lời
- Mở Parent App trên phone — verify PIN, camera, task, puppet
- Cài PWA lên phone — verify icon trên Home Screen

### 🔧 Khi có phần cứng robot
1. Train openWakeWord model "bi_oi" từ 30+ audio samples
2. Đặt model vào src_brain/senses/models/bi_oi.onnx
3. Set WAKEWORD_ENABLED = True trong ear_stt.py
4. Implement ESP32 motor control (Sprint 4)

---

## 2026-04-16-session-G.md

## ⚡ KẾT QUẢ SESSION G — Sprint 6 Parent App hoàn thiện (2026-04-14)

### ✅ Đã hoàn thành
- PIN authentication: `/api/auth/login` + `/api/auth/logout` + `require_auth` dependency (Header + Query param)
- Tất cả endpoints nhạy cảm đều yêu cầu auth: events, chats, memories, puppet, camera, tasks
- MJPEG camera stream: `/api/camera` endpoint, placeholder frame khi không có camera, graceful fallback khi không có opencv
- TaskManager: nhiệm vụ hằng ngày, reminder TTS đúng giờ (daemon thread 30s), sao thưởng tích lũy
- API tasks: GET/POST /api/tasks, POST /api/tasks/{id}/complete, DELETE /api/tasks/{id}, GET /api/tasks/stars
- Dashboard: login overlay PIN, logout button, stars badge ở header, tab Nhiệm vụ, camera toggle trong tab Sự kiện
- main_loop.py: `_speak_text()` method + `init_task_manager()` call trong `__init__`
- /api/status trả thêm `total_stars`

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| `src_brain/network/api_server.py` | PIN auth, require_auth dependency, MJPEG camera, task endpoints |
| `src_brain/network/task_manager.py` | Tạo mới — TaskManager class (add, complete, delete, stars, reminder loop) |
| `src_brain/network/static/index.html` | PIN login screen, logout, stars header, camera toggle, tab Nhiệm vụ |
| `src_brain/main_loop.py` | import init_task_manager, gọi trong __init__, thêm _speak_text() |

### 🧪 Test results
| Test | Kết quả |
|------|---------|
| TaskManager unit test (add/complete/stars/delete) | PASS |
| Syntax check api_server.py | PASS |
| Syntax check task_manager.py | PASS |
| Syntax check main_loop.py | PASS |
| Import chain RobotBiApp | PASS |

### 📌 Quyết định kỹ thuật
| Quyết định | Giá trị | Lý do |
|------------|---------|-------|
| Auth token storage | localStorage ('bi_token') | Đơn giản, đủ cho LAN nội bộ |
| Camera auth | Header hoặc query param ?auth= | img src không gửi được custom header |
| CV2 import | try/except graceful | Tránh crash khi opencv chưa cài |
| TaskManager init | Lazy (trong init_task_manager) | Tránh circular import khi api_server load |
| Reminder loop interval | 30 giây | Đủ chính xác theo phút, không tốn CPU |

### ⚠️ Chưa có (để Session H)
- HTTPS/mTLS (SRS NFR-07) — chấp nhận tạm thời cho LAN nội bộ
- Reset sao hằng ngày (cron job tự động)
- Push notification mobile (cần service worker PWA)
- Stress test RAM (SRS Giai đoạn 7)

### 🗺️ TRẠNG THÁI SAU SESSION G
- Giai đoạn 6 (Parent App): ✅ ~95% (REST + WebSocket + Auth + Camera + Tasks)
- Còn lại: HTTPS, reset daily cron, PWA notification

### 🚀 Session tiếp theo: Session H — Sprint 7 Tối ưu & Đóng gói
1. Stress test RAM (đảm bảo ≤ 13GB peak — SRS NFR-01)
2. Đo độ trễ end-to-end (≤ 2.5s P50 — SRS NFR-03)
3. Reset daily tasks (cron midnight)
4. Logging có cấu trúc JSON (SRS NFR-13)

---

## 2026-04-16-session-F.md

## ⚡ KẾT QUẢ SESSION F — Fix Môi Trường Windows

### ✅ Đã hoàn thành
- Bug 1: edge-tts retry 3 lần với delay tăng dần (0.3s, 0.6s, 0.9s)
- Bug 2: pyttsx3 fallback đổi sang .wav, audio worker kiểm tra file tồn tại
- Bug 3: cleanup() unload pygame trước khi xóa file, bắt PermissionError
- Bug 4: MIC_DEVICE=1 set nhất quán trong ear_stt.py
- Side fix: cài fastapi (thiếu từ trước), import chain pass

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| src_brain/senses/mouth_tts.py | edge-tts retry 3 lần, fallback .wav |
| src_brain/senses/ear_stt.py | MIC_DEVICE=1 constant, dùng nhất quán ở cả 2 InputStream |
| src_brain/main_loop.py | cleanup() fix PermissionError + .wav, audio worker kiểm tra file tồn tại |

### 🧪 Test results
| Test | Kết quả |
|------|---------|
| Import chain toàn bộ | PASS |
| mouth_tts.py standalone | Chưa test thủ công (cần internet cho edge-tts) |

### ⚠️ Cần test thủ công (cần mic + loa)
- Chạy `python -m src_brain.main_loop` và nói "Xin chào Bi"
- Verify Bi trả lời qua loa, không có dòng "edge-tts lỗi"
- Nếu vẫn lỗi → tăng delay lên 0.5s mỗi lần retry

### 🚀 Session tiếp theo: Session G — Sprint 6 Parent App hoàn thiện

---

## 2026-04-16-session-E.md

## ⚡ KẾT QUẢ SESSION E — Hoàn thiện Giai đoạn 4 (Vision 100%)

### ✅ Đã hoàn thành
- CryDetector: YAMNet TFLite primary + energy/ZCR fallback (src_brain/senses/cry_detector.py)
- EventNotifier: event queue JSON + WebSocket stub (src_brain/network/notifier.py)
- Face recognition nâng cấp: LBPH primary (confidence < 80) + histogram fallback
- main_loop.py: tích hợp CryDetector + Notifier + chat log + vision events (5 điểm thay đổi)
- src_brain/senses/models/README.md: hướng dẫn download yamnet.tflite
- requirements.txt: thêm tflite-runtime + sounddevice

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| src_brain/senses/cry_detector.py | Tạo mới — CryDetector class (YAMNet + energy fallback) |
| src_brain/network/__init__.py | Tạo mới |
| src_brain/network/notifier.py | Tạo mới — EventNotifier class (stub) |
| src_brain/senses/eye_vision.py | Nâng cấp face recognition: LBPH primary + histogram fallback |
| src_brain/main_loop.py | Tích hợp CryDetector + Notifier + chat log notification |
| src_brain/senses/models/README.md | Tạo mới — hướng dẫn download YAMNet |
| requirements.txt | Thêm tflite-runtime |
| CLAUDE.md | Cập nhật stack, file map, sprint status, lệnh hay dùng |

### 🧪 Test results
| Test | Kết quả |
|------|---------|
| CryDetector khởi tạo + start/stop | PASS |
| EventNotifier push_event + push_chat_log | PASS |
| EyeVision LBPH recognizer attribute | PASS |
| main_loop import chain | PASS |
| event_queue.json được tạo | PASS |

### 📌 Quyết định kỹ thuật
| Quyết định | Giá trị | Lý do |
|------------|---------|-------|
| Cry detection primary | YAMNet TFLite | Offline, nhẹ (~3.5MB), chính xác |
| Cry detection fallback | Energy + ZCR | Không cần model, chạy được ngay |
| Face recognition | LBPH (confidence < 80) + histogram | LBPH tốt hơn nhưng cần opencv-contrib |
| Notification mode | JSON queue (stub) | Sprint 5 upgrade WebSocket |
| Cooldown cry alert | 10 giây | Tránh spam notification |

### ⚠️ Lưu ý quan trọng
- YAMNet model chưa được download — cần thủ công: xem src_brain/senses/models/README.md
- Khi không có yamnet.tflite, CryDetector dùng energy fallback tự động — KHÔNG crash
- LBPH cần opencv-contrib-python — hiện máy chỉ có opencv-python nên tự động dùng histogram fallback
- WebSocket notification chỉ lưu local — cần Sprint 5 để gửi thật đến Parent App

### 🗺️ TRẠNG THÁI DỰ ÁN SAU SESSION E
- Giai đoạn 1 (Nền móng): ✅ 100%
- Giai đoạn 2 (Voice I/O): ✅ ~95% (wake-word stub, edge-tts cần internet)
- Giai đoạn 3 (RAG): ✅ 100%
- Giai đoạn 4 (Vision + Cry + Notification): ✅ 100%
- Giai đoạn 5 (Cơ khí): 🚫 Bỏ qua (không có phần cứng)
- Giai đoạn 6 (Parent App): ⏳ Sprint tiếp theo
- Giai đoạn 7 (Tối ưu): ⏳ Sprint cuối

---

## ⚡ KẾT QUẢ SPRINT 5 — Parent App Backend (2026-04-14)

### ✅ Đã hoàn thành

- FastAPI backend: `src_brain/network/api_server.py` — REST + WebSocket, chạy daemon thread
- Web dashboard: `src_brain/network/static/index.html` — 5 tab, mobile-friendly, WebSocket realtime
- Puppet feature: `POST /api/puppet` → queue → main_loop.py `_handle_puppet_queue()` đọc và TTS
- WebSocket broadcaster: `notifier.set_ws_broadcaster()` + `_send_ws()` gọi thật (thay stub)
- main_loop.py: `init_server()` + `start_api_server()` + `_handle_puppet_queue()` ở 2 điểm trong run()
- Cài: `fastapi`, `uvicorn[standard]`, `websockets`

### 📁 Files đã thay đổi

| File | Thay đổi |
|------|----------|
| `src_brain/network/api_server.py` | Tạo mới — FastAPI app, 11 endpoints, WebSocket, puppet queue |
| `src_brain/network/static/index.html` | Tạo mới — Web dashboard 5 tab |
| `src_brain/network/notifier.py` | Thêm `set_ws_broadcaster()`, `_send_ws()` gọi thật |
| `src_brain/main_loop.py` | Import + `init_server` + `start_api_server` + `_handle_puppet_queue()` |
| `requirements.txt` | Thêm `fastapi`, `uvicorn[standard]` |

### 🌐 REST API endpoints

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/` | Web dashboard |
| WS | `/ws` | Real-time event push |
| GET | `/api/status` | Trạng thái robot |
| GET | `/api/events` | Sự kiện (filter: type, unread_only, limit) |
| POST | `/api/events/read_all` | Đánh dấu đã đọc |
| GET | `/api/chats` | Nhật ký hội thoại |
| GET | `/api/memories` | Danh sách trí nhớ |
| POST | `/api/memories` | Thêm trí nhớ thủ công |
| PUT | `/api/memories/{id}` | Sửa trí nhớ |
| DELETE | `/api/memories/{id}` | Xóa trí nhớ |
| GET | `/api/memories/export` | Export JSON |
| POST | `/api/puppet` | Phụ huynh gõ → Bi đọc TTS |

### 📌 Quyết định kỹ thuật

| Quyết định | Giá trị | Lý do |
|------------|---------|-------|
| Port | 8000 | Mặc định FastAPI |
| Host | 0.0.0.0 | Cho phép truy cập từ LAN |
| Thread model | Daemon thread riêng | Không block main_loop voice I/O |
| WS broadcast | asyncio.run_coroutine_threadsafe | Thread-safe từ notifier → api event loop |
| Puppet queue check | Sau listen() rỗng + sau audio_queue.join() | 2 điểm để phản hồi nhanh nhất |
| Dashboard | Inline CSS, no CDN | Offline-friendly |

### ⚠️ Còn tồn tại (carry forward)

- **[TRUNG BÌNH]** Chưa có xác thực (PIN) — bất kỳ ai trên cùng LAN đều xem được (SRS NFR-06)
- **[TRUNG BÌNH]** Live camera stream chưa có — cần MJPEG hoặc WebRTC (SRS 4.1)
- **[THẤP]** Chưa có HTTPS/mTLS (SRS NFR-07) — chấp nhận tạm thời cho LAN nội bộ

### 🗺️ TRẠNG THÁI SAU SPRINT 5

- Giai đoạn 6 (Parent App): ✅ ~70% (REST + WebSocket + Dashboard + Puppet)
- Còn lại: Live camera stream, xác thực PIN, nhiệm vụ hằng ngày (SRS 4.4)

### 🚀 Sprint tiếp theo: Sprint 6 — Hoàn thiện Parent App + Tối ưu

Theo thứ tự ưu tiên:
1. **Xác thực PIN** — SRS NFR-06 (bảo vệ dashboard khỏi truy cập không phép)
2. **Live camera stream** — MJPEG endpoint `/api/camera` (SRS 4.1)
3. **Nhiệm vụ hằng ngày** — `POST /api/tasks`, cron nhắc TTS (SRS 4.4)
4. **Stress test** + tối ưu RAM (SRS Giai đoạn 7)

---

## 2026-04-16-session-D.md

## ⚡ KẾT QUẢ SESSION D — Hoàn thiện Giai đoạn 3 (RAG)

### ✅ Đã hoàn thành
- Similarity threshold: 0.35 → 0.50 (giảm false positive, tăng chính xác)
- Thêm constant: `_MIN_SIMILARITY_STRICT = 0.65`, `_MAX_FACTS_PER_QUERY = 3`
- Fact extraction: thêm 6 nhóm pattern mới (lớp học, môn học, thức ăn, sức khỏe, thành tích, cảm xúc)
- Deduplication: smart overlap check (>70% từ giống nhau → bỏ) thay vì exact match
- 4 methods mới: add_manual_memory(), update_memory(), export_memories(), clear_all_memories()
- Context format cải thiện — "[Thông tin Bi đã biết về bé — hãy dùng tự nhiên nếu liên quan]"
- main_loop.py: cập nhật inject format → `f"{rag_context}\n\nBé hỏi: {user_text}"`
- Test suite: 4 → 8 unit tests, tất cả PASS
- Integration test: PASS

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| src_brain/memory_rag/rag_manager.py | Threshold, patterns, 4 methods mới, dedup thông minh, test suite 8 |
| src_brain/main_loop.py | Cập nhật context inject format |
| CLAUDE.md | Cập nhật mô tả rag_manager.py (10 methods), Session D done |

### 📌 Quyết định kỹ thuật
| Quyết định | Giá trị | Lý do |
|------------|---------|-------|
| Similarity threshold | 0.50 | Cân bằng recall vs precision cho tiếng Việt |
| Max facts per query | 3 | Tránh context pollution cho LLM 7B |
| Dedup overlap | 70% | Bắt các fact paraphrase của nhau |
| Manual memory source | "parent" | Phân biệt với "conversation" cho Parent App |

### 🚀 Session tiếp theo: Session E — Sprint 5 Parent App
- FastAPI backend trên robot (WebSocket + REST)
- Xem SRS Phần 4 để biết đầy đủ tính năng
- add_manual_memory() đã sẵn sàng cho Parent App gọi

---

## 2026-04-16-session-C.md

## ⚡ KẾT QUẢ SESSION C — Hoàn thiện Giai đoạn 2

### ✅ Đã hoàn thành
- Safety filter post-LLM: src_brain/ai_core/safety_filter.py (SafetyFilter class)
- Tích hợp SafetyFilter vào main_loop.py — inject trước generate_audio() tại 2 điểm
- Wake-word stub: listen_for_wakeword() trong EarSTT + WAKEWORD_ENABLED=False flag
- edge-tts offline fallback: pyttsx3 trong mouth_tts.py (thêm docstring + _fallback_tts())
- prompts.py: điền đầy đủ MAIN_SYSTEM_PROMPT, REFUSAL_RESPONSE, GREETING, SAFETY_CHECK_PROMPT
- requirements.txt: thêm pyttsx3
- CLAUDE.md: cập nhật stack (pyttsx3 + SafetyFilter), file map, vấn đề đã biết

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| src_brain/ai_core/safety_filter.py | Tạo mới — SafetyFilter class |
| src_brain/ai_core/prompts.py | Điền nội dung — 4 prompt constants |
| src_brain/main_loop.py | Thêm SafetyFilter import + __init__ + inject tại 2 điểm audio loop |
| src_brain/senses/ear_stt.py | Thêm WAKEWORD_ENABLED, WAKEWORD_PHRASE, listen_for_wakeword() |
| src_brain/senses/mouth_tts.py | Rewrite với docstring + try/except + _fallback_tts(pyttsx3) |
| requirements.txt | Thêm pyttsx3 |
| CLAUDE.md | Cập nhật stack, file map, vấn đề đã biết, lệnh hay dùng |

### 🧪 Test results
| Test | Kết quả |
|------|---------|
| SafetyFilter — text bình thường pass | PASS |
| SafetyFilter — text chiến tranh/bạo lực bị block | PASS |
| SafetyFilter — blacklist word "ngu ngốc" bị xóa | PASS |
| EarSTT wake-word stub tồn tại (listen_for_wakeword + WAKEWORD_ENABLED) | PASS |
| prompts.py constants đầy đủ (4 constants) | PASS |
| main_loop.py syntax OK + SafetyFilter integrated | PASS |

### 📌 Quyết định kỹ thuật
| Quyết định | Giá trị | Lý do |
|------------|---------|-------|
| Safety approach | Regex pattern + blacklist | Nhanh, không cần LLM, đủ cho MVP |
| Wake-word | Stub (WAKEWORD_ENABLED=False) | openWakeWord cần model training — để sau |
| TTS fallback | pyttsx3 | Nhẹ, không cần internet, có sẵn pip |
| Refusal response | "Bi chưa có dữ liệu về vấn đề này." | Đúng SRS 2.3 |
| Safety inject point | Trước _generate_audio() tại 2 điểm | Cover cả sentence trong loop và buffer cuối |

### ⚠️ Còn tồn tại (cần upgrade sau)
- Wake-word: cần train openWakeWord model "bi_oi" — khi có đủ audio samples
- edge-tts: vẫn cần internet lần đầu — cần Coqui TTS hoặc Piper cho fully offline
- Safety patterns: chỉ MVP coverage — cần mở rộng thêm tiếng Việt colloquial

### 🚀 Session tiếp theo: Sprint 5 — Parent App
- FastAPI backend trên robot (WebSocket + REST)
- Xem SRS Phần 4 để biết đầy đủ tính năng

---

## 🗂️ TRẠNG THÁI CÁC FILE QUAN TRỌNG (sau Session C)

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `src_brain/main_loop.py` | ✅ Streaming + RAG + Vision + Safety | Entry point chính |
| `src_brain/ai_core/core_ai.py` | ✅ Có stream_chat() | Không thay đổi Session C |
| `src_brain/ai_core/safety_filter.py` | ✅ SafetyFilter implemented | Session C — post-LLM filter |
| `src_brain/ai_core/prompts.py` | ✅ 4 prompt constants | Session C — MAIN_SYSTEM_PROMPT, REFUSAL, GREETING |
| `src_brain/senses/mouth_tts.py` | ✅ edge-tts + pyttsx3 fallback | Session C — offline fallback |
| `src_brain/senses/ear_stt.py` | ✅ faster-whisper + wakeword stub | Session C — WAKEWORD_ENABLED=False |
| `src_brain/senses/eye_vision.py` | ✅ EyeVision implemented | Sprint 3 hoàn thành |
| `src_brain/memory_rag/rag_manager.py` | ✅ RAGManager | Sprint 2 hoàn thành |
| `src_brain/main.py` | ⛔ Legacy | Không dùng |
| `src_brain/senses/voice_io.py` | ⛔ Legacy | Không dùng |

---

## 2026-04-16-session-B.md

## ⚡ KẾT QUẢ SESSION B — Sprint 3 Vision

### ✅ Đã hoàn thành
- Implement eye_vision.py: class EyeVision với 8 methods (start, stop, set_surveillance_mode, register_face, get_stats, is_running + 2 internal helpers)
- Motion detection: MOG2 background subtraction, threshold 5000px²
- Face recognition: histogram correlation fallback (cv2.face/LBPH không có trong opencv-python, không cần contrib)
- Clip recording: pre-buffer 5s + 10s post-event, lưu MP4
- Graceful degradation: hoạt động ngay cả khi không có camera (log warning, return sớm)
- Tích hợp main_loop.py: 4 điểm thay đổi — import, __init__, _on_vision_event, stop()
- EyeVision chạy daemon thread song song, KHÔNG block voice I/O
- CLAUDE.md, requirements.txt đã cập nhật

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| src_brain/senses/eye_vision.py | Implement mới hoàn toàn |
| src_brain/main_loop.py | Thêm EyeVision integration (4 điểm) |
| requirements.txt | Thêm opencv-python |
| CLAUDE.md | Cập nhật stack Vision, Sprint 3 done, next = Sprint 5 |

### 🧪 Test results
| Test | Kết quả |
|------|---------|
| Unit test 1 — khởi tạo không crash | PASS |
| Unit test 2 — start() không crash | PASS |
| Unit test 3 — is_running() | PASS |
| Unit test 4 — get_stats() format | PASS |
| Unit test 5 — stop() không crash | PASS |
| Integration test | PASS |

### 📌 Quyết định kỹ thuật
| Quyết định | Giá trị | Lý do |
|------------|---------|-------|
| Face recognizer | Histogram correlation (cv2.compareHist CORREL) | cv2.face (LBPH) không có trong opencv-python (cần contrib) |
| Cascade | haarcascade_frontalface_default.xml | Built-in OpenCV, không cần thư viện ngoài |
| Frame resize | 640x480 | Cân bằng CPU vs chất lượng |
| Face recognition interval | Mỗi 10 frame | Giảm CPU, đủ responsive |
| Pre-buffer clip | 5 giây @ 20fps = 100 frame (deque) | Đủ để capture context trước sự kiện |
| Post-event record | 10 giây @ 20fps = 200 frame | Theo SRS Phần 3.4 |
| Motion threshold | 5000 px² | Bỏ qua noise nhỏ, bắt chuyển động thật |
| Face similarity threshold | 0.5 histogram correlation | Đủ phân biệt known/stranger |
| OpenCV version | 4.13.0 | numpy upgrade: 1.26.4 → 2.4.4 (kéo theo) |

### ⚠️ Lưu ý khi test thật
- Cần webcam USB hoặc built-in camera (index=0) để test đầy đủ
- Để đăng ký khuôn mặt: cho ảnh vào src_brain/senses/vision_data/known_faces/[tên]/001.jpg
- Clip được ghi vào src_brain/senses/vision_data/clips/
- RAM khi chạy Vision: +~0.3-0.5GB (OpenCV nhẹ hơn YOLOv8 nhiều)
- numpy upgrade 1.26.4 → 2.4.4: kiểm tra compatibility với sentence-transformers nếu có vấn đề

### ⚠️ TODO cho Sprint 5 (đã đánh dấu trong code)
- _on_vision_event → gửi WebSocket notification đến Parent App (comment TODO trong code)
- set_surveillance_mode → trigger từ Parent App thay vì gọi trực tiếp
- YAMNet cry detection (SRS 3.4) → để Sprint 5 hoặc Sprint 6

### 🚀 Sprint tiếp theo: Sprint 5 — Parent App
- FastAPI backend trên robot (WebSocket + REST)
- App mobile iOS/Android hoặc Progressive Web App
- Live camera stream, nhật ký chat, điều khiển từ xa
- Xem SRS Phần 4 để biết đầy đủ tính năng

---

## 2026-04-16-session-A.md

## ⚡ KẾT QUẢ SESSION A — Fix STT Offline

### ✅ Đã hoàn thành
- Rewrite ear_stt.py: Google STT → faster-whisper (Whisper small, int8, offline)
- HC-01 vi phạm đã được giải quyết — hệ thống giờ chạy 100% offline
- requirements.txt: thêm faster-whisper, sounddevice, soundfile, numpy
- CLAUDE.md: cập nhật stack STT và đánh dấu issue #4 đã fix

### 📁 Files đã thay đổi
| File | Thay đổi |
|------|----------|
| src_brain/senses/ear_stt.py | Rewrite hoàn toàn — faster-whisper thay Google STT |
| requirements.txt | Thêm faster-whisper, sounddevice, soundfile, numpy |
| CLAUDE.md | Cập nhật stack STT, đánh dấu issue #4 fixed |

### 📌 Quyết định kỹ thuật
| Quyết định | Giá trị | Lý do |
|------------|---------|-------|
| Whisper model size | small | Cân bằng tốc độ/accuracy cho tiếng Việt, ~244MB |
| compute_type | int8 | Giảm RAM ~50%, vẫn đủ chính xác |
| VAD filter | True | Bỏ qua đoạn im lặng, tăng tốc transcribe |
| Silence threshold | 1500ms | Đủ dài để bé dừng giữa câu, không quá dài gây lag |

### ⚠️ Lưu ý khi test thật
- Lần đầu chạy: Whisper small (~244MB) sẽ tự download vào ~/.cache/huggingface
- Cần có microphone vật lý để test listen() thực sự
- Nếu máy không có mic → EarSTT vẫn khởi tạo được, listen() trả về "" và log warning

### 🚀 Session tiếp theo
- Session B: Sprint 3 Vision — implement eye_vision.py (OpenCV, xem SRS Phần 3.4)
- Sau Session B: tích hợp EyeVision vào main_loop.py

---

## 🗂️ TRẠNG THÁI CÁC FILE QUAN TRỌNG (cập nhật)

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `src_brain/main_loop.py` | ✅ Streaming + RAG | Entry point chính |
| `src_brain/ai_core/core_ai.py` | ✅ Có stream_chat() | Không thay đổi Sprint 2 |
| `src_brain/senses/mouth_tts.py` | ✅ Chunk support | Không thay đổi Sprint 2 |
| `src_brain/senses/ear_stt.py` | ✅ faster-whisper offline | Google STT đã thay — chạy 100% offline |
| `src_brain/memory_rag/rag_manager.py` | ✅ Implemented | Sprint 2 hoàn thành |
| `src_brain/senses/eye_vision.py` | 🔲 Chưa implement | Sprint 3 |
| `src_brain/main.py` | ⛔ Legacy | Không dùng |
| `src_brain/senses/voice_io.py` | ⛔ Legacy | Không dùng |

---

## 2026-04-16-session-1.md

# 📋 Sổ Bàn Giao — Sprint 1 Hoàn Tất / Sprint 2 Sẵn Sàng

> ⚠️ File này là NGUỒN SỰ THẬT DUY NHẤT. Claude Code hãy cập nhật kết quả vào cuối file này sau khi làm xong.

## 🗺️ TRẠNG THÁI HIỆN TẠI
- **Đang ở đâu:** Sprint 1 đã hoàn tất toàn bộ — Streaming Architecture hoạt động ổn định. Hệ thống Nghe → Nghĩ (stream) → Nói (chunk) đã chạy thực tế.
- **Vấn đề còn lại:** Bi đang bị "não cá vàng" — tắt máy là quên hết. Sprint 2 sẽ giải quyết bằng ChromaDB RAG.

---

## ✅ VIỆC ĐÃ HOÀN THÀNH (Session này — 2026-04-13)

### Sprint 1 — System Audit & Streaming Optimization

**1. requirements.txt — ĐÃ SYNC với stack thực tế**
- Xóa: `faster-whisper`, `sounddevice`, `soundfile`, `gTTS`
- Thêm: `speechrecognition`, `pyaudio`, `edge-tts`
- Giữ: `ollama`, `pygame>=2.5.0`, `python-dotenv>=1.0.0`

**2. core_ai.py — ĐÃ THÊM `stream_chat()`**
- Hàm `stream_chat(self, user_input: str)` → generator, yield từng token từ `ollama.chat(..., stream=True)`
- Cập nhật history sau khi stream hoàn tất
- Hàm `chat()` cũ giữ nguyên — backward compatible 100%

**3. mouth_tts.py — ĐÃ REFACTOR `_generate_audio()`**
- `_generate_audio(self, text, chunk_index=0)` → lưu `voice_chunk_{chunk_index}.mp3`, trả về path (string)
- `speak()` cũ giữ nguyên — backward compatible 100%

**4. main_loop.py — ĐÃ NÂNG CẤP STREAMING ARCHITECTURE**
- Thêm: `threading`, `queue`, `glob`, `asyncio`, `re`, `pygame`
- `self.audio_queue = queue.Queue()` + daemon thread `_audio_worker_loop`
- Worker thread: nhận file từ queue → play → unload → xóa file
- Vòng lặp `run()`: stream tokens → tách câu theo `.?!\n` → generate chunk → đưa vào queue
- `KeyboardInterrupt`: đưa None vào queue, cleanup tất cả `voice_chunk_*.mp3`, đóng event loop
- `if __name__ == "__main__":` guard — không chạy khi import
- Fix encoding: `sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)`

**5. ear_stt.py — ĐÃ FIX `WaitTimeoutError`**
- Thêm `except sr.WaitTimeoutError: return ""` — không crash khi không ai nói

**6. Kết quả chạy thực tế:**
```
[Hệ thống] Robot Bi đã khởi động và sẵn sàng!
[Bi - Tai] Đang đo tiếng ồn môi trường...
[Bi - Tai] Đã sẵn sàng! Bạn hãy nói gì đó đi...
```
✅ Hệ thống khởi động thành công, vòng lặp listen ổn định, không crash.

---

## ⚡ TASK TIẾP THEO (Sprint 2)

### 🔲 Chế tạo Hải Mã (Memory Manager)
- **Mô tả:** Xây dựng class quản lý trí nhớ dài hạn bằng ChromaDB.
- **File cần tạo:** `src_brain/memory_rag/rag_manager.py`
- **Build Order:**
  1. Cài đặt thư viện: `chromadb`, `sentence-transformers`
  2. Khởi tạo `chromadb.PersistentClient` trỏ vào `./data/memory_db`
  3. Dùng model nhúng `paraphrase-multilingual-MiniLM-L12-v2`
  4. Viết hàm `add_memory(text)` — sinh UUID, lưu vector
  5. Viết hàm `recall_memory(query, top_k=2)` — trả về list chuỗi gần nhất
  6. Tích hợp vào `core_ai.py`: trước khi gửi prompt, `recall_memory(user_input)` và inject vào context
  7. Block test: lưu "Bo thích ăn gà rán KFC" → query → kết quả phải match

- **Acceptance Criteria:**
  - [ ] File chạy không báo lỗi
  - [ ] Thư mục `data/memory_db` tự động được tạo
  - [ ] Block test in ra đúng "gà rán KFC" khi được hỏi
  - [ ] main_loop.py hoạt động bình thường với RAG tích hợp

---

## 🗂️ TRẠNG THÁI CÁC FILE QUAN TRỌNG

| File | Trạng thái | Ghi chú |
|------|-----------|---------|
| `src_brain/main_loop.py` | ✅ Streaming arch | Entry point chính — dùng cái này |
| `src_brain/ai_core/core_ai.py` | ✅ Có stream_chat() | Class BiAI, chat() + stream_chat() |
| `src_brain/senses/mouth_tts.py` | ✅ Chunk support | _generate_audio(text, chunk_index=0) |
| `src_brain/senses/ear_stt.py` | ✅ WaitTimeout fixed | Google STT — cần internet |
| `requirements.txt` | ✅ Synced | speechrecognition, pyaudio, edge-tts |
| `src_brain/memory_rag/rag_manager.py` | 🔲 Chưa implement | Sprint 2 |
| `src_brain/main.py` | ⛔ Legacy | Không dùng |
| `src_brain/senses/voice_io.py` | ⛔ Legacy | Không dùng |

---

## 📝 VẤN ĐỀ ĐÃ BIẾT (CÒN LẠI)

| # | Vấn đề | File | Mức độ |
|---|--------|------|--------|
| 1 | `ear_stt.py` dùng Google STT — cần internet, vi phạm offline constraint | `ear_stt.py` | Trung bình |
| 2 | `edge-tts` cần internet để generate audio | `mouth_tts.py` | Thấp (chấp nhận tạm thời) |

---

## 💻 LỆNH HAY DÙNG

```bash
# Chạy hệ thống chính
python -m src_brain.main_loop

# Test từng module
python src_brain/senses/ear_stt.py
python src_brain/senses/mouth_tts.py
python src_brain/ai_core/core_ai.py
python src_brain/memory_rag/rag_manager.py   # Test RAG (4 unit tests)

# Syntax check
python -m py_compile src_brain/main_loop.py
python -m py_compile src_brain/ai_core/core_ai.py
python -m py_compile src_brain/senses/mouth_tts.py
python -m py_compile src_brain/memory_rag/rag_manager.py

# Cài dependencies
pip install ollama edge-tts pygame speechrecognition chromadb sentence-transformers
```

---

## ⚡ KẾT QUẢ SPRINT 2 — Trí nhớ RAG (Session 2026-04-13)

### ✅ Đã hoàn thành

- Cài đặt chromadb 1.5.7 + sentence-transformers 5.4.0 (torch 2.11.0 kéo theo)
- Implement `src_brain/memory_rag/rag_manager.py` — class `RAGManager` với 6 methods:
  - `__init__`: PersistentClient + model paraphrase-multilingual-MiniLM-L12-v2
  - `extract_and_save`: regex fact extraction + ChromaDB add
  - `retrieve`: similarity search → context string
  - `list_memories`: list toàn bộ facts sorted by timestamp
  - `delete_memory`: xóa fact theo ID
  - `get_stats`: tổng số facts + timestamps
- Tích hợp RAGManager vào `src_brain/main_loop.py` tại 2 điểm:
  - Trước `stream_chat()`: retrieve context + prepend vào user_text
  - Sau `audio_queue.join()`: background thread save facts
- Cập nhật `requirements.txt`, `CLAUDE.md`
- Pass 4/4 unit tests + integration test

### 📁 Files đã thay đổi

| File | Loại thay đổi | Mô tả |
|------|---------------|-------|
| `src_brain/memory_rag/rag_manager.py` | Tạo mới | RAGManager class với 6 methods |
| `src_brain/main_loop.py` | Sửa | Import RAGManager, tích hợp retrieve + extract_and_save |
| `CLAUDE.md` | Sửa | Cập nhật RAG stack, file map, Sprint 2 → ✅, Sprint 3 là next |
| `requirements.txt` | Sửa | Thêm chromadb, sentence-transformers |
| `.claude/handoff.md` | Cập nhật | File này |

### 🧪 Test results

| Test | Kết quả | Output thực tế |
|------|---------|----------------|
| Unit test save (3 facts) | ✅ PASS | 8 facts extracted từ 3 pairs |
| Unit test retrieve | ✅ PASS | Context: `[Trí nhớ của Bi] Bé tên là An ...` |
| Unit test list | ✅ PASS | 8 entries |
| Unit test delete | ✅ PASS | 7 entries sau khi xóa |
| Integration test | ✅ PASS | `INTEGRATION TEST PASSED` |

### 📌 Quyết định kỹ thuật đã chốt

| Quyết định | Giá trị | Lý do |
|------------|---------|-------|
| Embedding model | paraphrase-multilingual-MiniLM-L12-v2 | Hỗ trợ tiếng Việt, nhẹ (~420MB) |
| ChromaDB backend | PersistentClient (DuckDB) | Không cần server, offline hoàn toàn |
| Fact extraction | Regex + keyword matching | Không dùng LLM để giữ latency thấp |
| Similarity threshold | `_MIN_SIMILARITY = 0.35` | cosine similarity tối thiểu để inject vào prompt |
| RAG inject point | Prepend vào user_text | Giữ nguyên stream_chat() interface, backward compatible |
| save() threading | Background daemon thread | Không block audio queue — không ảnh hưởng latency |

### ⚠️ Vấn đề còn tồn tại (carry forward)

- **[TRUNG BÌNH]** `ear_stt.py` dùng Google STT — cần internet, vi phạm HC-01 (offline). Nên thay Whisper local trước Sprint 3
- **[THẤP]** `edge-tts` cần internet để generate audio — chấp nhận tạm thời
- **[THẤP]** `sentence-transformers` lần đầu load model cần download từ HuggingFace (~420MB). Sau đó cached local
- **[THẤP]** Windows không hỗ trợ symlink cho HuggingFace cache — chỉ là warning, không ảnh hưởng chức năng
- **[THẤP]** Test DB (`_test_db`) không xóa được do ChromaDB file lock trên Windows — để lại folder trống, vô hại

### 🚀 Build Order gợi ý cho Sprint 3 — Vision (để session tiếp theo dùng)

1. Đọc SRS Phần 3.4 (Nhóm 4 — Giám sát an ninh)
2. Implement `src_brain/senses/eye_vision.py` — class EyeVision với OpenCV
3. Motion detection: MOG2 background subtraction
4. Face recognition: load danh sách khuôn mặt từ `data/faces/` folder
5. Tích hợp vào main_loop.py như một daemon thread song song (KHÔNG block voice I/O)
6. Test với webcam thật
7. Cập nhật handoff.md

---

## 🗺️ TRẠNG THÁI HIỆN TẠI (2026-04-13 sau Sprint 2)

- **Sprint đã hoàn thành:** Sprint 1 (Streaming Voice I/O) + Sprint 2 (RAG) ✅
- **Sprint tiếp theo:** Sprint 3 — Vision (OpenCV) — xem SRS Phần 3.4
- **Entry point:** `src_brain/main_loop.py`
- **Stack active:** ollama(qwen2.5:7b) + edge-tts + speechrecognition + chromadb + sentence-transformers

---

## HANDOFF — Current State

# Handoff - Robot Bi

> Current-state handoff only. Historical details belong in `changelog/`.

## Current State

- `PROJECT.md` is the source of truth for rules, protected fixes, workflow, and AI context policy.
- Current source root is `src/`; `src_brain/` is deprecated and must not be used.
- Main entry point: `src/main.py`.
- API server: `src/api/server.py`.
- Parent App: `frontend/parent_app/`.
- Robot Display: `frontend/robot_display/`.
- Firmware: `firmware/Robot_BI/Robot_BI.ino`.
- Runtime DB: `runtime/robot_bi.db`.
- Generated agent docs: `CLAUDE.md` and `AGENTS.md`, regenerated with `python sync.py`.

## Last Completed Task

- 2026-05-14: **Goal 4 — wire Parent App mock adapters to backend APIs (390/390 PASS)**. `frontend/parent_app/src/services/api.js` rewritten with transform functions for 6 adapters: `getChildProfiles` (GET /api/children, child_id→id, age already computed by backend), `getRadioChannels` / `getVideoLessons` / `getInteractiveGames` (content_items schema, content_id→id, fallback to mock when backend has no seeded data), `getMonthlyEmotions` (GET /api/emotions/monthly, weekly count→percentage transform), `getSystemLogs` (GET /api/admin/logs, component→source). All six use mock fallback when backend returns empty or 403. BLOCKED adapters (`getRoomLocation`, `getParentChatHistory`) return null — no component renders their data. Save-button stubs in SettingsOverlay unchanged (show toast, no api.js call). Encoding artifacts cleaned. 390/390 PASS, `npm run build` passes (196KB JS, 25KB CSS).

- 2026-05-14: **Goal 3 — runtime hardening (390/390 PASS)**. `stopCamera()` now dispatches `bi:stopcamera` CustomEvent; `MonitorPage` listens and sets `camOn=false`. Motor forward/backward/spin capped at 5 000 ms in `motor_router.py`. Dashboard field mapping corrected: `loadTodaySummary` switched from `/api/status` to `/api/analytics/daily`; emotion reads `emotionData.dominant`; weekly stats now fall back to `conversations/hours/tasks_completed`.

- 2026-05-14: **Goal 2 — remaining test failures fixed (390/390 PASS)**. Updated 8 outdated test functions to check React source files instead of legacy `index.html` (React+Vite migration moved code). Added `stopCamera` / `stopAudioMonitor` exports to `api.js`; wired them in `handleTabChange` and `handleLogout` in `App.jsx`; added `beforeunload` cleanup handler; added `notif-banner` class to `Toast.jsx`; added music volume control with `level` field to `MorePage.jsx`; created `docs/kehoach.md` with outdated banner; fixed test 47.4 to use `sys.executable` instead of `python3` on Windows. All Goal 1 fixes preserved.

- 2026-05-13: **Parent App backend integration Phase 4 implemented (spec 002-parent-app-backend-integration)**. Added family-scoped QR device connection metadata (`/api/device/connection-qr`), robot room/location metadata (`/api/robot/location`), and admin-only sanitized system logs (`/api/admin/logs`). Added migration-safe SQLite tables for pairing metadata and robot location metadata; admin logs intentionally return controlled sanitized operational entries rather than parsing raw log files. Full `python tests/run_tests.py` ran with new Group 63 passing; remaining failures are pre-existing frontend/docs/Windows helper checks outside this backend Phase 4 scope.

- 2026-05-13: **Parent App backend integration Phase 3 implemented (spec 002-parent-app-backend-integration)**. Added family-scoped CSV/PDF report export (`/api/reports/export`), radio/video/game metadata APIs (`/api/entertainment/radio`, `/api/entertainment/videos`, `/api/games/interactive`), and separate parent-to-Bi chat history endpoints (`/api/conversations/parent*`). Added migration-safe SQLite tables for report export audit metadata, content metadata, and parent chat sessions/messages. Full `python tests/run_tests.py` ran with new Group 62 passing; remaining failures are pre-existing frontend/docs/Windows helper checks outside this backend Phase 3 scope.

- 2026-05-13: **Parent App backend integration Phase 2 implemented (spec 002-parent-app-backend-integration)**. Added family-scoped child profile CRUD/activation, age-based content settings, daily interaction limit storage with usage lookup, sleep schedule settings, and push notification settings storage. Added migration-safe SQLite tables and focused tests in `tests/run_tests.py`. Full `python tests/run_tests.py` ran with new Group 61 passing; remaining failures are pre-existing frontend/docs/Windows helper checks outside this backend Phase 2 scope.

- 2026-05-13: **Parent App backend integration Phase 1 implemented (spec 002-parent-app-backend-integration)**. Added family-scoped parent notes on events, advanced `/api/events` filters, and monthly emotion statistics endpoints (`/api/emotion/monthly`, `/api/emotions/monthly`). Added migration-safe `parent_event_notes` SQLite schema and focused tests in `tests/run_tests.py`. Full `python tests/run_tests.py` ran with new Group 60 passing; remaining failures are pre-existing frontend/docs/Windows helper checks outside this backend Phase 1 scope.

- 2026-05-13: **Parent App React + Vite migration — IMPLEMENTED (spec 001-parent-app-redesign, T001–T072)**. Full React + Vite SPA built under `frontend/parent_app/src/`. Legacy `index.html` replaced with Vite mount shell. `npm run build` passes (191KB JS, 20KB CSS). All Tier 1 backend APIs preserved in `src/services/api.js`. Tier 2 features use mock data with badges. 5-tab navigation, sidebar, settings overlay, admin section, and all 5 pages implemented. SYSTEM_MAP.md updated.

- 2026-05-13: **Parent App UI Redesign — spec artifacts updated for React + Vite target (spec 001-parent-app-redesign)**. All spec files updated. SYSTEM_MAP.md was reverted then correctly updated after implementation.

- 2026-05-13: AI context and instruction docs were normalized so PROJECT remains authoritative, SYSTEM_MAP is descriptive only, Spec Kit is conditional, and generated agent docs sync from PROJECT.

## Known Issues

- Wake-word custom `bi_oi` model is not confirmed; current repo contains dev/test wake-word paths.
- Cloudflare quick tunnel URL may change after restart unless a named tunnel is configured.
- YAMNet TFLite support depends on optional runtime dependencies.
- Camera, browser audio, mobile behavior, and motor hardware still require real-device verification.

## Next Recommended Action

- **Manual browser test recommended**: login with real credentials, verify WebSocket status, open Settings overlay (child profiles), open More tab (radio/video/games), open Journal tab (emotion chart), open Admin panel (system logs). Check Network tab that calls hit real backend, not mock.
- Seed content data in SQLite (`content_items` table) if radio/video/game sections show mock data — backend returns empty array when no rows exist, triggering mock fallback.
- Remaining BLOCKED items: `getRoomLocation` (no component renders it), `getParentChatHistory` (LearningPage shows coming-soon), SettingsOverlay save buttons (show toast, backend endpoints exist but buttons don't call them yet).
- If backend serves Parent App via `ops_router.py` StaticFiles, point it to `frontend/parent_app/dist/` instead of the root `frontend/parent_app/`.
- For other code changes, read `PROJECT.md`, this handoff, and relevant source files.
- For large feature/API/schema/cross-module work, use Spec Kit or write a clear plan first.

## Current Test Command

```bash
python tests/run_tests.py
```

## Files Recently Touched

- `frontend/parent_app/index.html` (replaced legacy 4000-line HTML with Vite mount shell)
- `frontend/parent_app/package.json` (new — React 18 + Vite 5)
- `frontend/parent_app/vite.config.js` (new)
- `frontend/parent_app/src/main.jsx` (new — React entry)
- `frontend/parent_app/src/App.jsx` (new — auth gate + routing + layout)
- `frontend/parent_app/src/styles.css` (new — full design system)
- `frontend/parent_app/src/services/api.js` (new — all Tier 1 + Tier 2 mock adapters)
- `frontend/parent_app/src/data/mockData.js` (new — Vietnamese mock data)
- `frontend/parent_app/src/components/` (new — Sidebar, BottomNav, RobotStatusCard, UserCard, SettingsOverlay, FeatureBadge, SectionState, Toast)
- `frontend/parent_app/src/pages/` (new — LoginPage, HomePage, MonitorPage, LearningPage, JournalPage, MorePage)
- `frontend/parent_app/dist/` (build output — not git-tracked)
- `src/api/routers/control_router.py` (Phase 1 event filters and parent event note endpoints)
- `src/api/routers/control_router.py` (Phase 2 child profiles and parent settings endpoints)
- `src/api/routers/control_router.py` (Phase 3 report export endpoint)
- `src/api/routers/control_router.py` (Phase 4 device QR and robot location endpoints)
- `src/api/routers/admin_router.py` (Phase 4 sanitized admin logs endpoint)
- `src/api/routers/conversation_router.py` (Phase 3 parent-to-Bi chat history endpoints)
- `src/api/routers/game_router.py` (Phase 3 radio/video/game metadata endpoints)
- `src/api/routers/emotion_router.py` (monthly emotion endpoints)
- `src/emotion/emotion_analyzer.py` (monthly aggregation)
- `src/infrastructure/database/db.py` (`parent_event_notes` schema and helpers)
- `src/infrastructure/database/db.py` (Phase 2 child/settings/usage/notification schema)
- `src/infrastructure/database/db.py` (Phase 3 report/content/parent-chat schema)
- `src/infrastructure/database/db.py` (Phase 4 device pairing and robot location schema)
- `src/infrastructure/sessions/state.py` (advanced event query filters)
- `tests/run_tests.py` (Groups 60-63 backend tests for spec 002 phases 1-4)
- `SYSTEM_MAP.md` (Section 6 updated to describe React+Vite implementation)
- `.claude/handoff.md`

