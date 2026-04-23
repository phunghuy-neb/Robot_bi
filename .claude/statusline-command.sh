#!/usr/bin/env bash
# Claude Code statusLine command for Robot Bi project
input=$(cat)

user=$(whoami)
host=$(hostname -s)
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd')
model=$(echo "$input" | jq -r '.model.display_name // ""')

# Shorten cwd: replace HOME prefix with ~
home_dir="$HOME"
short_cwd="${cwd/#$home_dir/\~}"

# Git branch (skip optional locks)
git_branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)

# Context usage
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Build status line
parts=$(printf '\033[32m%s@%s\033[0m' "$user" "$host")
parts="$parts $(printf '\033[34m%s\033[0m' "$short_cwd")"

if [ -n "$git_branch" ]; then
  parts="$parts $(printf '\033[33m(%s)\033[0m' "$git_branch")"
fi

if [ -n "$model" ]; then
  parts="$parts $(printf '\033[36m[%s]\033[0m' "$model")"
fi

if [ -n "$used_pct" ]; then
  used_int=$(printf '%.0f' "$used_pct")
  if [ "$used_int" -ge 80 ]; then
    parts="$parts $(printf '\033[31mCtx:%s%%\033[0m' "$used_int")"
  else
    parts="$parts $(printf '\033[90mCtx:%s%%\033[0m' "$used_int")"
  fi
fi

printf '%s' "$parts"
