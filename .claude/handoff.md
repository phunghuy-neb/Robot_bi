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

- 2026-05-13: **Parent App UI Redesign — spec artifacts updated for React + Vite target (spec 001-parent-app-redesign)**. All spec files (spec.md, plan.md, research.md, data-model.md, tasks.md, checklists/requirements.md) updated to target React + Vite migration instead of vanilla JS single-file. SYSTEM_MAP.md premature update reverted — will be updated after implementation. `frontend/parent_app/index.html` still contains legacy code. Implementation has NOT started.

- 2026-05-13: AI context and instruction docs were normalized so PROJECT remains authoritative, SYSTEM_MAP is descriptive only, Spec Kit is conditional, and generated agent docs sync from PROJECT.

## Known Issues

- Wake-word custom `bi_oi` model is not confirmed; current repo contains dev/test wake-word paths.
- Cloudflare quick tunnel URL may change after restart unless a named tunnel is configured.
- YAMNet TFLite support depends on optional runtime dependencies.
- Camera, browser audio, mobile behavior, and motor hardware still require real-device verification.

## Next Recommended Action

- **To implement Parent App React+Vite migration**: Read `specs/001-parent-app-redesign/tasks.md` (T001–T072). Start with Phase 1 (audit `frontend/parent_app/index.html`) → Phase 2 (Vite setup) → Phase 3 (api.js, HIGH RISK, verify protected behavior before replacing index.html).
- For other code changes, read `PROJECT.md`, this handoff, and relevant source files.
- For large feature/API/schema/cross-module work, use Spec Kit or write a clear plan first.

## Current Test Command

```bash
python tests/run_tests.py
```

## Files Recently Touched

- `SYSTEM_MAP.md` (reverted premature redesign description)
- `specs/001-parent-app-redesign/spec.md` (Assumptions updated for React+Vite)
- `specs/001-parent-app-redesign/plan.md` (full rewrite for React+Vite)
- `specs/001-parent-app-redesign/research.md` (architecture decision updated)
- `specs/001-parent-app-redesign/data-model.md` (state section updated for React)
- `specs/001-parent-app-redesign/tasks.md` (full rewrite — 72 tasks, React+Vite phases)
- `specs/001-parent-app-redesign/checklists/requirements.md` (notes updated)
- `.claude/handoff.md`
