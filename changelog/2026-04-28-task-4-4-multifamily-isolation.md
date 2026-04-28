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
