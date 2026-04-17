# 2026-04-17 - Phase 2 Prep: wake-word dev/test path + tests

- Updated `src_brain/senses/ear_stt.py` to add `WAKEWORD_THRESHOLD` from `.env`.
- Implemented the wake-word path so `WAKEWORD_ENABLED=False` returns `False` immediately.
- Added safe fallback when `openwakeword` import fails: warn once, set `WAKEWORD_ENABLED=False`, return `False`.
- Added dev/test proxy detection with `openwakeword.Model(wakeword_models=[])`.
- Wake-word loop now reads 80ms audio chunks, checks model scores against `WAKEWORD_THRESHOLD`, plays beep on detection, and pauses while `is_mom_talking()` is active.
- Extended Group 13 in `run_tests.py` with 3 wake-word tests.
- Verification: `python run_tests.py` -> `76/76 PASS`.
