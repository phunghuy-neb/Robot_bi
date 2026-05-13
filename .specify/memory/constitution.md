# Robot Bi Spec Kit Constitution

## Authority

`PROJECT.md` is the single source of truth for Robot Bi.

This constitution supports Spec Kit workflows only. It cannot override `PROJECT.md`, `.claude/handoff.md`, or the current source code.

## Non-Override Rules

Spec Kit cannot override:

- Protected Fixes in `PROJECT.md`
- Child safety and privacy requirements
- Auth, JWT, refresh-token rotation, PIN auth, and rate-limit behavior
- Multi-family isolation and family-scoped data access
- SQLite DB path and schema constraints
- Current stack constraints
- Required verification after code changes
- File Creation Policy
- `SYSTEM_MAP.md` Maintenance Policy

## When To Use Spec Kit

Use Spec Kit for:

- Large features
- API/schema changes
- Cross-module changes
- Major UI flows
- Roadmap phase planning
- Tasks where the user explicitly asks for spec/plan/tasks

## When Not To Use Spec Kit

Do not use Spec Kit for:

- Small hotfixes
- Audit-only tasks
- Simple docs-only edits
- Protected regression fixes
- One-file obvious fixes

## Governance

Every active Spec Kit spec, plan, or task list must remain subordinate to `PROJECT.md`.

If a Spec Kit artifact conflicts with `PROJECT.md`, follow `PROJECT.md` and update or discard the conflicting Spec Kit artifact.

Every Robot Bi Spec Kit plan must consider protected fixes, child safety/privacy, family isolation, current stack constraints, file creation policy, and required verification.

**Version**: 1.0.0 | **Ratified**: 2026-05-13 | **Last Amended**: 2026-05-13
