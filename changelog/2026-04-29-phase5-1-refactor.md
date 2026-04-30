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
