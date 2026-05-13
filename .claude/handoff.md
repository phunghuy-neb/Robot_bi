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

- 2026-05-13: **Parent App UI Redesign (spec 001-parent-app-redesign)** — completed full frontend redesign of `frontend/parent_app/index.html`. Changes: "Công nghệ ấm áp" design system (Be Vietnam Pro, 16px base, 48px tap targets), new 5-tab sidebar with robot status card + user card + settings + logout in correct bottom order, settings overlay panel, weekly report cards on Trang chủ and Giám sát, journal filter bar + emotion monthly chart + export button + advanced filter, Học tập with Luyện tập and Chat với Bi sections, Thêm with Radio/Video/Interactive Games mock sections, all Tier 2 features marked with appropriate badges. All existing API calls and protected functions (doLogin, doLogout, apiFetch, connectWS, setStatus, switchTab, loadThreads, showThreadDetail, startMomMic, stopMomMic, toast) preserved. SYSTEM_MAP.md updated.

- 2026-05-13: AI context and instruction docs were normalized so PROJECT remains authoritative, SYSTEM_MAP is descriptive only, Spec Kit is conditional, and generated agent docs sync from PROJECT.

## Known Issues

- Wake-word custom `bi_oi` model is not confirmed; current repo contains dev/test wake-word paths.
- Cloudflare quick tunnel URL may change after restart unless a named tunnel is configured.
- YAMNet TFLite support depends on optional runtime dependencies.
- Camera, browser audio, mobile behavior, and motor hardware still require real-device verification.

## Next Recommended Action

- For code changes, read `PROJECT.md`, this handoff, and relevant source files.
- For large feature/API/schema/cross-module work, use Spec Kit or write a clear plan first.
- For docs/audit-only work, do not run full tests unless code changes.

## Current Test Command

```bash
python tests/run_tests.py
```

## Files Recently Touched

- `PROJECT.md`
- `SYSTEM_MAP.md`
- `.specify/memory/constitution.md`
- `.claude/handoff.md`
- `.claudeignore`
- `HUONG_DAN_CHAY.md`
- `sync.py`
- `CLAUDE.md` and `AGENTS.md` after sync
