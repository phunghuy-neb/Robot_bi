#!/usr/bin/env bash
# Stop hook — read-only reminder (per PROJECT.md Mandatory Rule 9).
# Blocks the stop ONCE with a reminder IFF code/content changed (src/ frontend/
# resources/ firmware/) but .claude/handoff.md was NOT touched. Self-clearing:
# as soon as handoff.md shows up as changed, the condition is false and it exits 0.
# Never writes anything — only inspects `git status`.
set -uo pipefail

root="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "${root:-}" ] || exit 0
cd "$root" 2>/dev/null || exit 0

st="$(git status --porcelain 2>/dev/null)" || exit 0
[ -n "$st" ] || exit 0

# Any code/content change in the tracked work dirs?
printf '%s\n' "$st" | grep -qE '(src/|frontend/|resources/|firmware/)' || exit 0

# Handoff already updated this round? Then nothing to nag about.
printf '%s\n' "$st" | grep -q 'handoff\.md' && exit 0

# Condition met → remind me (Claude) to update the handoff anchor.
printf '%s' '{"decision":"block","reason":"PROJECT.md Mandatory Rule 9: có thay đổi trong src/ frontend/ resources/ firmware/ nhưng .claude/handoff.md chưa được cập nhật. Trước khi dừng, hãy cập nhật mục \"In Progress / Stopped Here\" (vừa làm xong gì + bước kế tiếp, kèm commit id nếu đã commit). Nếu thay đổi chỉ là thử nghiệm/không cần ghi nhận, hãy nói rõ điều đó rồi dừng."}'
