# Implementation Plan: Stage 2 Special Memories
> Clarifications resolved 2026-06-24 (see spec.md "Resolved Decisions").

## Technical Context
- Current `src/memory/family_memory.py` is a placeholder only (4 lines).
- Emotion journal is NOT a `db.py` table: class `EmotionJournal` in `src/emotion/emotion_journal.py` creates/manages its own `emotion_journal` table (columns include `family_id`, `timestamp`, `emotion`, `note`; verify the id column name before wiring promotion). Promotion-from-emotion goes through that module.
- Existing `events` table (in `db.py`) is family-scoped; real PK is `db_id` (autoincrement) and `event_id` is a nullable text column. Soft-links use `events.db_id`.
- Existing RAG layer is ChromaDB-based in `src/memory/rag_manager.py`; this plan does not change it.
- Existing API auth/family isolation patterns live in `src/api/routers/*` using `get_current_user` and `_require_family()`.
- SQLite DB path remains `runtime/robot_bi.db`; tests override DB path with a temp DB as the existing suite does.

## Constitution / Protected-Fixes Check
- Do not change RAG threshold `0.62`, deduplication, or family-scoped ChromaDB filters.
- Do not change DB path `runtime/robot_bi.db`.
- Do not bypass JWT route protection or family isolation.
- Do not change SafetyFilter placement.
- Do not read `.env`, runtime DB, logs, cache/model/media files by default during implementation/testing.
- Do not touch unimplemented camera/CV stubs for this feature.

## Architecture & Affected Files
- MODIFY `src/memory/family_memory.py`: replace placeholder with `SpecialMemoryManager` (CRUD, approval workflow, recall filtering, dedup, encryption hooks).
- MODIFY `src/infrastructure/database/db.py`: add `special_memories` table + indexes in `init_db()` (additive `CREATE TABLE IF NOT EXISTS`).
- NEW `src/api/routers/special_memory_router.py`: parent CRUD, propose-draft, approval, promote-from-event/emotion, export, audio-free reminder candidates.
- MODIFY `src/api/server.py`: include new router.
- MODIFY `src/main.py`: inject approved recall context (active + child_safe + approved only) before LLM, labelled as data.
- NEW encryption helper (small module or function): app-level encrypt/decrypt of content fields; key sourced OUTSIDE SQLite (env var / OS keystore — exact source is an implementation decision).
- MODIFY `frontend/parent_app/src/services/api.js`: memory CRUD + approval + export helpers.
- MODIFY `frontend/parent_app/src/pages/JournalPage.jsx` (or a new memories page): parent review/approve/manage UI.
- NEW `tests/test_special_memories.py`: temp-DB tests for schema, CRUD, family isolation, three-axis enforcement, draft approval, promotion soft-refs, recall filtering, encryption-at-rest, dedup suggestion, retention.

## Data / Schema changes
- Add `special_memories` table (see spec Key Entities) with three independent axes (`status`, `visibility`, `recall_policy`), a `created_by` proposer field, encrypted `title_enc`/`summary_enc`, and soft-ref `source_type`/`source_id`.
- Indexes:
  - `idx_special_memories_family_status` on `(family_id, status, updated_at)`
  - `idx_special_memories_family_recall` on `(family_id, status, visibility, recall_policy)`
  - `idx_special_memories_source` on `(source_type, source_id)`
  - `idx_special_memories_date` on `(family_id, memory_date)`
- No changes required to `events` or the `EmotionJournal` table for P1/P2; references are soft links (`events.db_id`, emotion id).
- Encryption: content columns store ciphertext; key never in SQLite. Dedup embeddings (if stored in ChromaDB) must not contain plaintext of sensitive memories.

## API / Contracts
- `GET /api/special-memories?status=active&limit=50` — current family memories (decrypted for parent).
- `POST /api/special-memories` — parent creates an `active` (or `pending`) memory.
- `POST /api/special-memories/propose` — Bi/child proposes a `pending` draft (created_by=child|bi).
- `POST /api/special-memories/{memory_id}/approve` — parent approves a pending draft → `active`.
- `PATCH /api/special-memories/{memory_id}` — update title, summary, type, axes (status/visibility/recall_policy), tags, date.
- `DELETE /api/special-memories/{memory_id}` — hard delete (purges row + embedding + derived); archive is via PATCH status='archived'.
- `POST /api/special-memories/from-event/{db_id}` — memory referencing `events.db_id` (soft ref, no mutation).
- `POST /api/special-memories/from-emotion/{entry_id}` — memory referencing an EmotionJournal entry (via the module).
- `GET /api/special-memories/export` — JSON export of the family's memories.
- `GET /api/special-memories/reminders` — due anniversary/reminder candidates (only if parent enabled; no TTS).
- Internal manager method: `get_recall_context(family_id, limit=3, max_chars=600) -> str` — returns ONLY active + child_safe + approved memories whose recall_policy permits child recall, labelled as data.

## Phases
- Phase 0 clarification: (resolved) — see Resolved Decisions in spec.md.
- Phase 1 data/model: schema + encryption helper + manager CRUD with tests.
- Phase 2 API: authenticated family-scoped CRUD + propose/approve endpoints with tests.
- Phase 3 source promotion: event (`db_id`) / emotion soft-ref promotion.
- Phase 4 recall integration: runtime prompt-context injection honoring the three axes (parent_only never reaches child).
- Phase 5 privacy/retention: encryption-at-rest verification, draft 30-day expiry, hard-delete purge, JSON export, dedup-suggest.
- Phase 6 reminders: parent-enabled anniversary candidates (no proactive TTS, quiet-hours aware).
- Phase 7 UI: parent review/approve/manage + export.

## Risks & Open Questions
- Sensitive memories require conservative defaults (concern → parent_only + never_to_child).
- Recall must be parent-controlled; parent_only must never reach the child prompt.
- Memory text in prompt context must be labelled as data to resist injection.
- Encryption key management (env var vs OS keystore) is an implementation decision; must stay outside SQLite.
- Hard delete must also purge embeddings/derived data, not just the SQLite row.
