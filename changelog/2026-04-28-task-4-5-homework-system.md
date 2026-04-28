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
