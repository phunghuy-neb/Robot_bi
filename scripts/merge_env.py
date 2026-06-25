#!/usr/bin/env python3
"""
merge_env.py — Trộn .env cũ vào template .env.example mới.

Sinh ra một file .env mới GIỮ NGUYÊN bố cục/section + biến mới của
.env.example, nhưng ĐIỀN LẠI các giá trị bạn đã đặt trong .env cũ — khỏi
copy thủ công.

An toàn:
- Chỉ IN RA TÊN BIẾN (không bao giờ in giá trị secret).
- Mặc định ghi ra .env.merged để bạn xem trước (không đụng .env).
- Dùng --in-place để backup .env -> .env.bak rồi ghi đè .env.

Cách dùng:
    python scripts/merge_env.py                 # .env + .env.example -> .env.merged
    python scripts/merge_env.py --in-place      # backup .env.bak rồi ghi .env
    python scripts/merge_env.py --env .env --example .env.example --out .env.merged
"""

import argparse
import re
import sys
from pathlib import Path

# Dòng gán biến: KEY=VALUE, cho phép thụt đầu dòng và tiền tố "# " (commented).
_LINE_RE = re.compile(r"^(\s*)(#\s*)?([A-Z][A-Z0-9_]*)=(.*)$")
# Giá trị mẫu coi như "chưa đặt".
_PLACEHOLDER_RE = re.compile(
    r"^(your_.*_here|REPLACE_WITH.*|change_this.*)$", re.IGNORECASE
)


def _value_only(raw: str) -> str:
    """Bỏ comment cuối dòng kiểu 'value   # chú thích' (cần khoảng trắng trước #)."""
    m = re.search(r"\s#", raw)
    v = raw[: m.start()] if m else raw
    return v.strip().strip('"').strip("'")


def _is_real(value: str) -> bool:
    v = _value_only(value)
    if not v:
        return False
    return not _PLACEHOLDER_RE.match(v)


def parse_env(text: str) -> dict:
    """Lấy KEY=VALUE đang BẬT (bỏ qua dòng comment) từ .env cũ."""
    out = {}
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if not m or m.group(2):  # m.group(2) = đang bị comment
            continue
        out[m.group(3)] = m.group(4)
    return out


def merge(example_text: str, real: dict):
    used, out = set(), []
    for line in example_text.splitlines():
        m = _LINE_RE.match(line)
        if m and m.group(3) in real and _is_real(real[m.group(3)]):
            indent, key = m.group(1), m.group(3)
            # Giữ lại comment cuối dòng của template (vd "# inference.cerebras.ai").
            _, sep, comment = m.group(4).partition("#")
            tail = f"    #{comment}".rstrip() if sep else ""
            out.append(f"{indent}{key}={real[key]}{tail}")
            used.add(key)
        else:
            out.append(line)

    leftover = [k for k, v in real.items() if k not in used and _is_real(v)]
    if leftover:
        out += [
            "",
            "# ════════════════════════════════════════════════════════════",
            "#  PHẦN 6 · [GIỮ TỪ .env CŨ] — biến không có trong template mới",
            "# ════════════════════════════════════════════════════════════",
        ]
        out += [f"{k}={real[k]}" for k in leftover]
    return "\n".join(out) + "\n", used, leftover


def main() -> int:
    ap = argparse.ArgumentParser(description="Trộn .env cũ vào .env.example mới.")
    ap.add_argument("--env", default=".env", help="File .env cũ (mặc định .env)")
    ap.add_argument("--example", default=".env.example", help="Template mới")
    ap.add_argument("--out", default=".env.merged", help="File kết quả")
    ap.add_argument("--in-place", action="store_true",
                    help="Backup .env -> .env.bak rồi ghi đè .env")
    args = ap.parse_args()

    example_path = Path(args.example)
    env_path = Path(args.env)
    if not example_path.exists():
        print(f"[merge_env] Thiếu template: {example_path}", file=sys.stderr)
        return 1
    real = parse_env(env_path.read_text(encoding="utf-8")) if env_path.exists() else {}
    if not env_path.exists():
        print(f"[merge_env] Không thấy {env_path} — chỉ tạo file từ template.")

    merged, used, leftover = merge(example_path.read_text(encoding="utf-8"), real)

    # Báo cáo các biến trong template còn để giá trị mẫu (cần điền tay).
    need_fill = []
    for line in example_path.read_text(encoding="utf-8").splitlines():
        m = _LINE_RE.match(line)
        if m and not m.group(2):
            key = m.group(3)
            if key not in used and not _is_real(m.group(4)):
                need_fill.append(key)

    target = env_path if args.in_place else Path(args.out)
    if args.in_place and env_path.exists():
        backup = env_path.with_suffix(env_path.suffix + ".bak")
        backup.write_text(env_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[merge_env] Đã backup -> {backup}")
    target.write_text(merged, encoding="utf-8")

    # CHỈ in tên biến — không in giá trị.
    print(f"\n[merge_env] Ghi: {target}")
    print(f"  ✓ Điền lại từ .env cũ ({len(used)}): {', '.join(sorted(used)) or '—'}")
    print(f"  ✎ Còn để mẫu, cần điền tay ({len(need_fill)}): {', '.join(need_fill) or '—'}")
    print(f"  + Giữ thêm từ .env cũ ({len(leftover)}): {', '.join(leftover) or '—'}")
    if not args.in_place:
        print("\n  Xem xong, kích hoạt bằng:")
        print(f"     mv {args.env} {args.env}.bak && mv {target} {args.env}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
