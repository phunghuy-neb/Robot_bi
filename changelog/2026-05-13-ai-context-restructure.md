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