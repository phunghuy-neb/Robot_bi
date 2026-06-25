#!/usr/bin/env python3
"""
resolve_youtube_channels.py — Tra channel_id THẬT từ tên/từ khóa kênh YouTube.

Dùng YOUTUBE_API_KEY trong .env để search kênh, in ra channel_id (UC...),
tên kênh, mô tả ngắn và URL — để bạn xác minh trước khi thêm vào
resources/youtube_channels.json. KHÔNG tự thêm vào allowlist.

Dùng:
    python scripts/resolve_youtube_channels.py "POPS Kids" "Bút Chì TV"
"""

import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 12


def _api_key() -> str:
    p = ROOT / ".env"
    if not p.exists():
        return ""
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*YOUTUBE_API_KEY=(.*)$", line)
        if m:
            v = m.group(1)
            cut = re.search(r"\s#", v)
            return (v[: cut.start()] if cut else v).strip().strip('"').strip("'")
    return ""


def search_channels(query: str, key: str, limit: int = 2):
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={"part": "snippet", "type": "channel", "q": query,
                "maxResults": limit, "key": key, "regionCode": "VN",
                "relevanceLanguage": "vi", "safeSearch": "strict"},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:120]}")
    out = []
    for item in r.json().get("items", []):
        sn = item.get("snippet", {})
        cid = item.get("id", {}).get("channelId", "")
        if cid:
            out.append({
                "channel_id": cid,
                "title": sn.get("channelTitle") or sn.get("title", ""),
                "description": (sn.get("description") or "")[:120],
            })
    return out


def main() -> int:
    key = _api_key()
    if not key or key.startswith("your_"):
        print("[resolve] Thiếu YOUTUBE_API_KEY hợp lệ trong .env", file=sys.stderr)
        return 1
    queries = sys.argv[1:]
    if not queries:
        print("Dùng: python scripts/resolve_youtube_channels.py \"tên kênh 1\" \"tên kênh 2\"")
        return 1
    for q in queries:
        print(f"\n🔎 '{q}'")
        try:
            results = search_channels(q, key)
        except Exception as e:
            print(f"   lỗi: {e}")
            continue
        if not results:
            print("   (không thấy kênh)")
        for c in results:
            print(f"   • {c['channel_id']}  | {c['title']}")
            print(f"       https://www.youtube.com/channel/{c['channel_id']}")
            if c["description"]:
                print(f"       {c['description']}")
    print("\n⚠️  Hãy MỞ link kiểm tra nội dung trước khi thêm vào allowlist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
