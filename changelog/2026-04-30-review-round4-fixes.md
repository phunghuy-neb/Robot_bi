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
