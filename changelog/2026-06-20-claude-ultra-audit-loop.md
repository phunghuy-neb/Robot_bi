# Claude Ultra Full-System Audit Loop

## Summary

Hardened the external Claude Code review service so full-project audit rounds are manifest-driven, read-only, fail-closed, and resumable without losing prior findings.

## Changes

- Installed a Python review wrapper at `/home/huyphung/bin/claude-deep-review-loop`.
- Installed the Ultra Full-System charter at `/home/huyphung/bin/claude-deep-review-charter.md`.
- Updated the user systemd service at `/home/huyphung/.config/systemd/user/claude-deep-review-loop.service`.
- Added manifest generation from Git/status/diff/find signals, file hashing, module grouping, and change detection.
- Added strict marker validation, stable issue/coverage delta merging, atomic writes, timestamped backups, and preservation on parse errors.
- Added model-route attestation and explicit `MODEL_UNAVAILABLE`, `OPUS_LIMIT_HIT`, and `MODEL_FALLBACK_DETECTED` handling.
- Pinned runtime configuration to Opus 4.8, plan mode, Read/Glob/Grep, 250 turns, text output, and disabled session persistence.

## Verification

- Project baseline: 560/560 tests passed.
- Wrapper self-test: 6/6 passed.
- Fake-Claude success integration passed and injected `claude-opus-4-8` into LATEST.
- Truncated-marker integration returned `PARSE_ERROR`; checksums confirmed LATEST, OPEN_ISSUES, COVERAGE_MATRIX, and PROJECT_MANIFEST were preserved.
- `systemd-analyze verify --user` passed for the installed unit.
- Runtime environment confirmed Opus 4.8, 250 turns, 5-second interval, and 120-second quota retry.
- Live service created a 377-file manifest and entered `OPUS_LIMIT_HIT` without replacing prior reports.
