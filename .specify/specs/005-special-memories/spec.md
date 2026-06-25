# Feature Specification: Stage 2 Special Memories
**Feature dir**: `.specify/specs/005-special-memories/`   **Status**: Draft (Clarifications resolved 2026-06-24)   **Date**: 2026-06-24

## Summary
Stage 2 Special Memories is a curated, parent-controlled memory layer for long-term, emotionally-meaningful family/child moments that deserve more durable handling than ordinary RAG facts or emotion logs. A special memory is created/approved only by a parent (Bi or the child may *propose* a draft by voice). Each memory has independent status, visibility, and recall-policy axes, is encrypted at rest, and is recalled into child conversations only when genuinely relevant and explicitly child-safe + approved. The current repo has a placeholder `src/memory/family_memory.py`, an `EmotionJournal` module, and a family-scoped `events` table to build on.

## User Scenarios
- As a parent, I want to mark a meaningful moment as special so that Bi can remember it later in an appropriate, child-safe way.
- As a child, I want Bi to remember happy milestones and comforting notes so that conversations feel personal without becoming invasive — but only after a parent approves them.
- As a parent, I want to review, edit, export, or delete special memories so that family privacy stays under parent control.
- As an operator, I want special memories to be family-scoped and testable without reading runtime DB or logs.

## User Stories (prioritized)
- US1 (P1): Parent can create/list/update/archive/delete a special memory for the current family; Bi/child can only create a `pending` draft awaiting parent approval. Independent test: authenticated API creates a memory scoped to family A; family B cannot read it; a child/Bi-proposed memory lands as `status='pending'`.
- US2 (P1): Robot runtime recalls a special memory only when relevant AND it is `active` + `child_safe` + parent-approved; `parent_only` memories never enter the child prompt. Independent test: retrieval returns only active/child_safe/approved family-scoped memories and omits pending/archived/parent_only entries.
- US3 (P2): Important events/emotions can be promoted to special memories via soft reference. Independent test: a special memory can reference an existing `events.db_id` or an `EmotionJournal` entry without copying or mutating the source row.
- US4 (P2): Parent controls the three independent axes — status (pending/active/archived), visibility (parent_only/child_safe), recall (related_only/parent_triggered/never_to_child). Independent test: a memory set to `parent_only` or `never_to_child` is visible to the parent but never injected into child prompt context.
- US5 (P2): Memory content is encrypted at rest; sensitive memories never appear as plaintext in logs or ChromaDB. Independent test: stored DB cells for content are ciphertext; a sensitive-type memory produces no plaintext in any log/embedding path.
- US6 (P3): Special memories can generate gentle anniversaries/reminders ONLY when the parent enables it. Independent test: a date-tagged memory due today creates a family-scoped reminder candidate; no TTS is emitted automatically; quiet hours respected.
- US7 (P3): Parent can export (JSON) and hard-delete memories; delete purges record, embedding, and derived data. Independent test: export returns the family's memories; delete removes row + embedding + any derived artifacts.

## Functional Requirements
- FR-001: Special memories MUST be family-scoped by `family_id` for every create, read, update, delete, and retrieval operation.
- FR-002: Special memories MUST NOT use or modify ChromaDB RAG threshold `0.62`; if embeddings are used for dedup they MUST keep existing family filters.
- FR-003: Special memories MUST NOT replace `RAGManager`; they are a separate curated memory layer. Ordinary preferences/facts stay in RAG.
- FR-004: Parent CRUD endpoints MUST require JWT authentication and current family from `_require_family()`.
- FR-005: Admin endpoints across families, if any, MUST require `is_admin`.
- FR-006: Runtime recall MUST return only `status='active'`, `visibility='child_safe'`, parent-approved memories, and MUST honor the recall-policy axis; `parent_only` content MUST NEVER enter the child conversation prompt.
- FR-007: Special memories MUST support soft source references to existing `events.db_id` (PK) and/or an `EmotionJournal` entry id, without requiring those sources to change for P1, and without mutating the source row.
- FR-008: Memory text exposed to child prompt context MUST be bounded in count and length, and MUST be labelled as data (not instruction) to resist prompt injection.
- FR-009: Parent MUST be able to archive and hard-delete a special memory; archived/deleted memories MUST NOT be recalled.
- FR-010: Tests MUST use a temporary SQLite DB and MUST NOT read `runtime/robot_bi.db`.
- FR-011: No API response may expose memories from another family.
- FR-012: No raw logs, cache/model files, or runtime media may be read to create special memories.
- FR-013: Only a parent may activate/approve a memory. Bi or the child MAY propose a memory by voice, but it MUST be created as a `pending` draft requiring parent approval before it becomes `active`.
- FR-014: Memory content MUST be encrypted at rest at the application level; the encryption key MUST NOT be stored in SQLite. Sensitive memories MUST NOT be written as plaintext to logs or ChromaDB.
- FR-015: The three axes MUST be independent columns: `status` (pending/active/archived), `visibility` (parent_only/child_safe), `recall_policy` (related_only/parent_triggered/never_to_child).
- FR-016: MVP memory types are: `milestone`, `achievement`, `family_event`, `comfort_note`, `birthday_anniversary`, plus a separate SENSITIVE type `concern`. Ordinary preferences are NOT a special-memory type (they stay in RAG).
- FR-017: A `concern` (sensitive) memory MUST default to `parent_only` + `never_to_child` and require explicit parent action to change.
- FR-018: Reminders/anniversaries MUST be generated only when the parent explicitly enables them; the feature MUST NOT emit proactive TTS by default and MUST respect quiet hours and current interaction context.
- FR-019: Retention — `pending` drafts MUST auto-delete after 30 days; approved memories persist until the parent archives/deletes, with an annual review reminder. JSON export MUST be supported. Hard delete MUST purge the record, its embedding, and any derived data.
- FR-020: Deduplication MUST first check normalized-text hash + source reference, then embedding similarity within the same `family_id`; on near-duplicate it MUST only SUGGEST a merge to the parent and MUST NOT auto-merge.

## Key Entities / Data
- Existing `events` (in `src/infrastructure/database/db.py`): real columns `db_id` (PK autoincrement), `family_id`, `event_id` (nullable text), `timestamp`, `type`, `message`, `clip_path`, `metadata_json`, `is_read`, `import_key`. Source soft-links MUST reference `events.db_id` (NOT the nullable `event_id`).
- Existing emotion journal: NOT a `db.py` table — it is created/managed by class `EmotionJournal` in `src/emotion/emotion_journal.py` (columns include `family_id`, `timestamp`, `emotion`, `note`; **verify the id column name in `src/emotion/emotion_journal.py`** before wiring promotion). Promotion-from-emotion MUST go through that module/its data.
- Existing `RAGManager`: general facts in ChromaDB; separate from this feature.
- New SQLite table `special_memories` (content fields encrypted at rest):
  - `memory_id TEXT PRIMARY KEY`
  - `family_id TEXT NOT NULL`
  - `title_enc TEXT NOT NULL`            -- encrypted
  - `summary_enc TEXT NOT NULL`          -- encrypted
  - `memory_type TEXT NOT NULL DEFAULT 'milestone'`   -- milestone|achievement|family_event|comfort_note|birthday_anniversary|concern
  - `emotion TEXT DEFAULT ''`
  - `memory_date TEXT`
  - `source_type TEXT DEFAULT ''`        -- ''|event|emotion
  - `source_id TEXT DEFAULT ''`          -- events.db_id or EmotionJournal id
  - `status TEXT NOT NULL DEFAULT 'pending'`          -- pending|active|archived
  - `visibility TEXT NOT NULL DEFAULT 'parent_only'`  -- parent_only|child_safe
  - `recall_policy TEXT NOT NULL DEFAULT 'related_only'` -- related_only|parent_triggered|never_to_child
  - `created_by TEXT NOT NULL DEFAULT 'parent'`       -- parent|child|bi (proposer)
  - `tags_json TEXT NOT NULL DEFAULT '[]'`
  - `metadata_json TEXT NOT NULL DEFAULT '{}'`
  - `created_at TEXT NOT NULL`
  - `updated_at TEXT NOT NULL`
- Encryption key source (env var / OS keystore) is an implementation decision; it MUST live outside SQLite.

## Success Criteria
- CRUD API tests prove family isolation for special memories.
- Child/Bi-proposed memories are created as `pending` and excluded from recall until a parent approves.
- Runtime retrieval returns at most a configured number of active + child_safe + approved memories under a configured character budget; parent_only never reaches child prompt.
- Stored content cells are ciphertext; sensitive memories produce no plaintext in logs/ChromaDB.
- Promotion preserves a soft reference to `events.db_id`/emotion entry without mutating the source.
- Drafts auto-delete after 30 days; hard delete purges row + embedding + derived data; JSON export works.
- Dedup suggests merges but never auto-merges.
- Full regression suite passes where dependencies are available.

## Edge Cases & Safety
- Sensitive memory (grief, bullying, medical, family conflict) → `concern` type, defaults `parent_only` + `never_to_child` (FR-017).
- Child asks about a parent_only memory; Bi must not reveal parent-only details.
- Duplicate memories from the same source → dedup suggests merge to parent; never auto-merge (FR-020).
- Deleted/archived source event must not break memory listing (soft reference).
- Multi-family isolation is mandatory.
- Export/delete must not touch raw runtime logs or media files; delete must also purge embeddings.
- Prompt injection inside memory text must be treated as data, not instruction (FR-008).

## Out of Scope
- Replacing ChromaDB RAG or changing RAG threshold/filtering.
- Reading runtime logs/media/cache to auto-create memories.
- Face recognition, camera-based memory capture, or unimplemented CV stubs.
- Automatic child-facing recall of sensitive events.
- Production cloud sync or cross-device encrypted backup.

## Resolved Decisions (2026-06-24)
- **Definition**: curated, approved, emotionally-meaningful long-term memory with its own recall policy; ordinary facts stay in RAG. (FR-003/016)
- **Creator**: parent-only activation/approval; Bi/child can propose a `pending` draft. (FR-013)
- **MVP types**: milestone, achievement, family_event, comfort_note, birthday_anniversary; `concern` is a separate sensitive type; preferences stay in RAG. (FR-016/017)
- **Three independent axes**: status, visibility, recall_policy. (FR-015)
- **Encryption**: yes, app-level, key outside SQLite; no plaintext of sensitive memories in logs/ChromaDB. (FR-014)
- **Recall default**: only when relevant AND active + child_safe + approved; parent_only never reaches child prompt. (FR-006)
- **Reminders/TTS**: only if parent enables; no proactive TTS by default; respect quiet hours. (FR-018)
- **Retention**: drafts auto-delete after 30 days; approved kept until archive/delete + annual review; JSON export; delete purges record + embedding + derived. (FR-019)
- **Dedup**: normalized-text hash + source first, then embedding within family; suggest merge only, never auto-merge. (FR-020)
- **Schema corrections**: soft-link to `events.db_id`; `emotion_journal` lives in `src/emotion/emotion_journal.py` (verify id column).
