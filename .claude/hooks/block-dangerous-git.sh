#!/usr/bin/env bash
input=$(cat)
cmd=$(echo "$input" | python -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

BLOCKED=(
  "git push"
  "git reset --hard"
  "git clean -f"
  "git branch -D"
  "git checkout ."
  "git restore ."
)

for pattern in "${BLOCKED[@]}"; do
  if echo "$cmd" | grep -qF "$pattern"; then
    echo "[BLOCKED] Lệnh nguy hiểm: $pattern" >&2
    echo "Xác nhận với user trước khi chạy lệnh này." >&2
    exit 2
  fi
done
exit 0
