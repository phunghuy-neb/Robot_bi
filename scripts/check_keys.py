#!/usr/bin/env python3
"""
check_keys.py — Kiểm tra nhanh các API key trong .env còn sống hay không.

Gọi thử nhẹ từng nhà cung cấp và báo OK / LỖI / CHƯA ĐẶT.
CHỈ in TÊN KEY + trạng thái — KHÔNG bao giờ in giá trị secret.

Dùng:  python scripts/check_keys.py
"""

import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 12
_PLACEHOLDER = re.compile(r"^(your_.*_here|REPLACE_WITH.*|change_this.*|DEMO_KEY)$", re.I)


def parse_env(path: Path) -> dict:
    vals = {}
    if not path.exists():
        return vals
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Z][A-Z0-9_]*)=(.*)$", line)
        if m:
            v = m.group(2)
            cut = re.search(r"\s#", v)
            if cut:
                v = v[: cut.start()]
            vals[m.group(1)] = v.strip().strip('"').strip("'")
    return vals


ENV = parse_env(ROOT / ".env")


def _val(key: str):
    v = ENV.get(key, "")
    if not v or _PLACEHOLDER.match(v):
        return None
    return v


def _status(resp) -> tuple[bool, str]:
    if resp.status_code == 200:
        return True, "HTTP 200"
    if resp.status_code in (401, 403):
        return False, f"HTTP {resp.status_code} — key sai/không đủ quyền"
    if resp.status_code == 429:
        return True, "HTTP 429 — key OK nhưng đang bị giới hạn lượt"
    return False, f"HTTP {resp.status_code}"


def _bearer(url):
    def fn(key):
        return _status(requests.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT))
    return fn


def _check_gemini(key):
    return _status(requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": key}, timeout=TIMEOUT))


def _check_cloudflare(key):
    acct = _val("CLOUDFLARE_ACCOUNT_ID")
    if not acct:
        return False, "thiếu CLOUDFLARE_ACCOUNT_ID"
    return _status(requests.get(
        f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/models/search",
        headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT))


def _check_tavily(key):
    r = requests.post("https://api.tavily.com/search",
                      json={"api_key": key, "query": "test", "max_results": 1}, timeout=TIMEOUT)
    return _status(r)


def _check_brave(key):
    r = requests.get("https://api.search.brave.com/res/v1/web/search",
                     headers={"X-Subscription-Token": key, "Accept": "application/json"},
                     params={"q": "test", "count": 1}, timeout=TIMEOUT)
    return _status(r)


def _check_youtube(key):
    r = requests.get("https://www.googleapis.com/youtube/v3/i18nLanguages",
                     params={"part": "snippet", "key": key}, timeout=TIMEOUT)
    return _status(r)


def _check_nasa(key):
    r = requests.get("https://api.nasa.gov/planetary/apod", params={"api_key": key}, timeout=TIMEOUT)
    return _status(r)


def _check_hf(key):
    return _status(requests.get("https://huggingface.co/api/whoami-v2",
                                headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT))


# (env_var, nhãn, hàm kiểm tra, bắt buộc?)
CHECKS = [
    ("CEREBRAS_API_KEY",  "Cerebras (LLM chính)",   _bearer("https://api.cerebras.ai/v1/models"), True),
    ("GROQ_API_KEY",      "Groq (LLM #2)",          _bearer("https://api.groq.com/openai/v1/models"), True),
    ("SAMBANOVA_API_KEY", "Sambanova (LLM #3)",     _bearer("https://api.sambanova.ai/v1/models"), True),
    ("GEMINI_API_KEY",    "Gemini (LLM #4)",        _check_gemini, True),
    ("CLOUDFLARE_API_KEY","Cloudflare WorkersAI #5",_check_cloudflare, True),
    ("DEEPSEEK_API_KEY",  "DeepSeek (fallback cuối)", _bearer("https://api.deepseek.com/models"), False),
    ("TAVILY_API_KEY",    "Tavily (web search)",    _check_tavily, False),
    ("BRAVE_API_KEY",     "Brave (web search #2)",  _check_brave, False),
    ("YOUTUBE_API_KEY",   "YouTube (video lessons)",_check_youtube, False),
    ("NASA_API_KEY",      "NASA APOD",              _check_nasa, False),
    ("HF_TOKEN",          "HuggingFace",            _check_hf, False),
]


def main() -> int:
    ok, bad, missing = [], [], []
    print("Kiểm tra API key (chỉ in tên + trạng thái, không lộ giá trị)\n" + "=" * 60)
    for env_var, label, fn, required in CHECKS:
        key = _val(env_var)
        if not key:
            tag = "BẮT BUỘC" if required else "tùy chọn"
            print(f"  ⚪ CHƯA ĐẶT  {env_var:24} {label}  [{tag}]")
            (missing if required else []).append(env_var) if required else None
            if required:
                missing.append(env_var)
            continue
        try:
            good, detail = fn(key)
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  MẠNG?    {env_var:24} {label} — không gọi được ({type(e).__name__})")
            continue
        if good:
            print(f"  ✅ OK       {env_var:24} {label} — {detail}")
            ok.append(env_var)
        else:
            print(f"  ❌ LỖI      {env_var:24} {label} — {detail}")
            bad.append(env_var)

    print("=" * 60)
    print(f"  OK: {len(ok)}  |  LỖI: {len(bad)}  |  BẮT BUỘC còn thiếu: {len(missing)}")
    if bad:
        print(f"  ❌ Cần sửa key: {', '.join(bad)}")
    if missing:
        print(f"  ⚪ Bắt buộc chưa đặt: {', '.join(missing)}")
    if not bad and not missing:
        print("  🎉 Không có key lỗi và không thiếu key bắt buộc.")
    return 1 if (bad or missing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
