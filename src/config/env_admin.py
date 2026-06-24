"""
env_admin.py — Đọc/ghi an toàn các biến .env mà admin được phép sửa qua web.

CHỈ cho phép sửa danh sách WHITELIST (key public + công tắc tính năng).
TUYỆT ĐỐI không động tới key LLM / JWT / mật khẩu admin.
Ghi .env (giữ nguyên cấu trúc) + cập nhật os.environ để có hiệu lực ngay với
các biến đọc theo request; một số biến đọc lúc khởi động (camera, cry, wakeword,
youtube singleton) cần restart — đánh dấu needs_restart.
"""

import os
import re
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
_TIMEOUT = 10

# Key public admin được xem/sửa. KHÔNG có key LLM/JWT ở đây — đó là chủ ý bảo mật.
PUBLIC_KEYS = [
    {"name": "YOUTUBE_API_KEY", "label": "YouTube Data API", "hint": "console.cloud.google.com → YouTube Data API v3"},
    {"name": "NASA_API_KEY",    "label": "NASA APOD",        "hint": "api.nasa.gov (bỏ trống = DEMO_KEY)"},
    {"name": "TAVILY_API_KEY",  "label": "Tavily web search", "hint": "app.tavily.com"},
    {"name": "BRAVE_API_KEY",   "label": "Brave web search",  "hint": "api.search.brave.com"},
]

# Công tắc tính năng (boolean, không phải secret).
TOGGLES = [
    {"name": "REGISTRATION_ENABLED",   "label": "Cho phép đăng ký tài khoản", "needs_restart": False},
    {"name": "WEB_SEARCH_ENABLED",     "label": "Web search",                 "needs_restart": False},
    {"name": "YOUTUBE_LESSONS_ENABLED", "label": "Video YouTube",             "needs_restart": True},
    {"name": "WAKEWORD_ENABLED",       "label": "Wake word",                  "needs_restart": True},
    {"name": "CAMERA_ENABLED",         "label": "Camera",                     "needs_restart": True},
    {"name": "CRY_DETECTION_ENABLED",  "label": "Phát hiện tiếng khóc",       "needs_restart": True},
]

_PUBLIC_KEY_NAMES = {k["name"] for k in PUBLIC_KEYS}
_TOGGLE_NAMES = {t["name"] for t in TOGGLES}
_EDITABLE = _PUBLIC_KEY_NAMES | _TOGGLE_NAMES
_PLACEHOLDER = re.compile(r"^(your_.*_here|REPLACE_WITH.*|change_this.*)$", re.I)
_TRUE = {"1", "true", "yes", "on"}


def _assert_editable(name: str) -> None:
    if name not in _EDITABLE:
        raise ValueError(f"Biến '{name}' không nằm trong whitelist admin được sửa")


def _read_value(name: str) -> str:
    """Đọc giá trị hiện tại (ưu tiên os.environ, sau đó .env)."""
    v = os.environ.get(name)
    if v is not None:
        return v
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        m = re.match(rf"^\s*{re.escape(name)}=(.*)$", line)
        if m:
            val = m.group(1)
            cut = re.search(r"\s#", val)
            return (val[: cut.start()] if cut else val).strip().strip('"').strip("'")
    return ""


def _is_real(value: str) -> bool:
    v = (value or "").strip()
    return bool(v) and not _PLACEHOLDER.match(v)


def write_env_var(name: str, value: str) -> None:
    """Ghi/cập nhật một biến trong .env (whitelist) + os.environ.
    Thay dòng `NAME=` (kể cả đang comment) nếu có, ngược lại append."""
    _assert_editable(name)
    value = "" if value is None else str(value)
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    pat = re.compile(rf"^\s*#?\s*{re.escape(name)}=")
    replaced = False
    for i, line in enumerate(lines):
        if pat.match(line):
            lines[i] = f"{name}={value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{name}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[name] = value
    logger.info("[env_admin] cập nhật %s (đã ghi .env)", name)


# ── Trạng thái (không bao giờ trả giá trị thật của key) ───────────────────────
def _mask(value: str) -> str:
    v = (value or "").strip()
    if not _is_real(v):
        return ""
    return f"••••{v[-4:]}" if len(v) > 4 else "••••"


def keys_status() -> list[dict]:
    out = []
    for k in PUBLIC_KEYS:
        v = _read_value(k["name"])
        out.append({
            "name": k["name"], "label": k["label"], "hint": k["hint"],
            "is_set": _is_real(v), "masked": _mask(v),
        })
    return out


def toggles_status() -> list[dict]:
    out = []
    for t in TOGGLES:
        v = (_read_value(t["name"]) or "").strip().lower()
        out.append({
            "name": t["name"], "label": t["label"],
            "enabled": v in _TRUE,
            "needs_restart": t["needs_restart"],
        })
    return out


# ── Test key public sống/chết (chỉ trả OK/LỖI, không lộ key) ──────────────────
def _test_youtube(key):
    r = requests.get("https://www.googleapis.com/youtube/v3/i18nLanguages",
                     params={"part": "snippet", "key": key}, timeout=_TIMEOUT)
    return r.status_code


def _test_nasa(key):
    r = requests.get("https://api.nasa.gov/planetary/apod",
                     params={"api_key": key or "DEMO_KEY"}, timeout=_TIMEOUT)
    return r.status_code


def _test_tavily(key):
    r = requests.post("https://api.tavily.com/search",
                      json={"api_key": key, "query": "test", "max_results": 1}, timeout=_TIMEOUT)
    return r.status_code


def _test_brave(key):
    r = requests.get("https://api.search.brave.com/res/v1/web/search",
                     headers={"X-Subscription-Token": key, "Accept": "application/json"},
                     params={"q": "test", "count": 1}, timeout=_TIMEOUT)
    return r.status_code


_TESTERS = {
    "YOUTUBE_API_KEY": _test_youtube,
    "NASA_API_KEY": _test_nasa,
    "TAVILY_API_KEY": _test_tavily,
    "BRAVE_API_KEY": _test_brave,
}


def test_key(name: str) -> dict:
    if name not in _PUBLIC_KEY_NAMES:
        return {"name": name, "ok": False, "detail": "không hỗ trợ test"}
    value = _read_value(name)
    if name == "NASA_API_KEY" and not _is_real(value):
        value = "DEMO_KEY"  # NASA vẫn chạy được bằng DEMO_KEY
    elif not _is_real(value):
        return {"name": name, "ok": False, "detail": "chưa đặt key"}
    try:
        code = _TESTERS[name](value)
    except requests.exceptions.RequestException:
        return {"name": name, "ok": False, "detail": "không gọi được (mạng?)"}
    if code == 200:
        return {"name": name, "ok": True, "detail": "HTTP 200"}
    if code == 429:
        return {"name": name, "ok": True, "detail": "HTTP 429 (sống, đang giới hạn lượt)"}
    if code in (401, 403):
        return {"name": name, "ok": False, "detail": f"HTTP {code} — key sai/không đủ quyền"}
    return {"name": name, "ok": False, "detail": f"HTTP {code}"}
