"""
youtube_lessons.py — Robot Bi: video bài học từ YouTube (allowlist kênh)
========================================================================
Lấy video MỚI từ một DANH SÁCH KÊNH GIÁO DỤC ĐÃ DUYỆT (allowlist) qua YouTube
Data API v3, trả về cùng shape với content_items type='video' để merge vào
endpoint `/api/entertainment/videos`.

An toàn trẻ em:
- CHỈ lấy video từ các kênh khai báo trong `resources/youtube_channels.json`
  (không search mở YouTube). Allowlist chính là ranh giới an toàn.
- Dùng playlist "uploads" của kênh (UC… → UU…) nên rẻ quota (1 unit/kênh).

Graceful degradation: thiếu `YOUTUBE_API_KEY`, thiếu allowlist, hoặc call lỗi
=> trả về [] (endpoint chỉ hiển thị nội dung DB như cũ). Không bao giờ raise.

Cấu hình:
- `.env`:  YOUTUBE_API_KEY=...           (bắt buộc để bật; KHÔNG hardcode)
           YOUTUBE_LESSONS_ENABLED=false (đặt false để tắt dù có key)
           YOUTUBE_MAX_PER_CHANNEL=4
           YOUTUBE_CACHE_TTL_SECONDS=21600  (6 giờ — tiết kiệm quota daily)
- allowlist: resources/youtube_channels.json
"""

import json
import logging
import os
import re
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 6  # giây
_API_BASE = "https://www.googleapis.com/youtube/v3"

# SafetyFilter dùng để lọc TIÊU ĐỀ video (lazy — không bắt buộc khi import).
_safety = None


def _title_is_safe(title: str) -> bool:
    """True nếu tiêu đề an toàn cho trẻ (qua SafetyFilter topic classifier).
    Lỗi/không tải được filter → coi như an toàn (không chặn nhầm)."""
    global _safety
    if not title:
        return True
    try:
        if _safety is None:
            from src.safety.safety_filter import SafetyFilter
            _safety = SafetyFilter()
        is_safe, _clean = _safety.check(title)
        return is_safe
    except Exception:
        return True
_CHANNELS_PATH = Path(__file__).resolve().parents[2] / "resources" / "youtube_channels.json"
_PLACEHOLDER_KEYS = {"your_youtube_api_key_here", ""}
_ISO8601_DURATION = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_channel(ch: dict) -> dict | None:
    """Chuẩn hóa 1 entry kênh; trả None nếu channel_id không hợp lệ (phải UC…)."""
    if not isinstance(ch, dict):
        return None
    cid = str(ch.get("channel_id") or "").strip()
    if not cid.startswith("UC") or len(cid) < 10:
        return None
    return {
        "channel_id": cid,
        "label": str(ch.get("label") or "").strip(),
        "language": (str(ch.get("language") or "vi").strip().lower() or "vi"),
        "age_min": _coerce_int(ch.get("age_min"), 5),
        "age_max": _coerce_int(ch.get("age_max"), 12),
        "tags": [str(t).lower() for t in (ch.get("tags") or [])],
    }


def _fmt_duration(iso: str) -> str:
    """ISO8601 (PT#H#M#S) -> chuỗi tiếng Việt ngắn, vd '12 phút', '1 giờ 5 phút'."""
    if not iso:
        return ""
    m = _ISO8601_DURATION.fullmatch(iso.strip())
    if not m:
        return ""
    hours = int(m.group(1) or 0)
    mins = int(m.group(2) or 0)
    secs = int(m.group(3) or 0)
    if secs >= 30:
        mins += 1
    if hours and mins:
        return f"{hours} giờ {mins} phút"
    if hours:
        return f"{hours} giờ"
    if mins:
        return f"{mins} phút"
    return "<1 phút"


class YouTubeLessons:
    """Nguồn video bài học từ allowlist kênh YouTube giáo dục."""

    def __init__(self) -> None:
        self._api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
        enabled_raw = os.getenv("YOUTUBE_LESSONS_ENABLED", "").strip().lower()
        self._explicitly_disabled = enabled_raw in {"0", "false", "no", "off"}
        self._max_per_channel = max(1, int(os.getenv("YOUTUBE_MAX_PER_CHANNEL", "4") or "4"))
        self._cache_ttl = max(0, int(os.getenv("YOUTUBE_CACHE_TTL_SECONDS", "21600") or "0"))
        self._has_key = bool(self._api_key) and self._api_key.lower() not in _PLACEHOLDER_KEYS
        self._channels = self._load_channels()
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        if self._explicitly_disabled:
            logger.info("[YouTubeLessons] Disabled by YOUTUBE_LESSONS_ENABLED")
        elif not self._has_key:
            logger.info("[YouTubeLessons] Thiếu YOUTUBE_API_KEY — video YouTube tắt")
        elif not self._channels:
            logger.info("[YouTubeLessons] Allowlist kênh rỗng — chưa có video YouTube")
        else:
            logger.info("[YouTubeLessons] Active: %d kênh allowlist", len(self._channels))

    @property
    def available(self) -> bool:
        """Có thể fetch bất kỳ kênh nào (global hoặc family): có key + không bị tắt.
        Tách khỏi `enabled` để kênh gia đình vẫn chạy khi allowlist global rỗng."""
        return not self._explicitly_disabled and self._has_key

    @property
    def enabled(self) -> bool:
        """Allowlist GLOBAL đang hoạt động (có key + có ít nhất 1 kênh global)."""
        return self.available and bool(self._channels)

    def _load_channels(self) -> list[dict]:
        if not _CHANNELS_PATH.exists():
            return []
        try:
            data = json.loads(_CHANNELS_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("[YouTubeLessons] Lỗi đọc allowlist: %s", e)
            return []
        out = []
        for ch in data.get("channels") or []:
            norm = _normalize_channel(ch)
            if norm:  # chỉ chấp nhận channel id hợp lệ (UC…)
                out.append(norm)
        return out

    # ── Quản lý allowlist GLOBAL (admin) ──────────────────────────────────────
    def _read_raw(self) -> dict:
        if not _CHANNELS_PATH.exists():
            return {}
        try:
            data = json.loads(_CHANNELS_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_raw(self, data: dict) -> None:
        _CHANNELS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CHANNELS_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def reload(self) -> None:
        """Đọc lại allowlist global từ file (sau khi admin sửa)."""
        self._channels = self._load_channels()
        self._cache.clear()

    def list_global_channels(self) -> list[dict]:
        return [dict(c) | {"scope": "global"} for c in self._channels]

    def add_global_channel(self, ch: dict) -> dict:
        """Thêm/cập nhật 1 kênh vào allowlist global (ghi file + reload)."""
        norm = _normalize_channel(ch)
        if not norm:
            raise ValueError("channel_id phải bắt đầu bằng UC… và hợp lệ")
        data = self._read_raw()
        chans = data.get("channels")
        if not isinstance(chans, list):
            chans = []
        chans = [c for c in chans if str(c.get("channel_id") or "").strip() != norm["channel_id"]]
        chans.append({
            "channel_id": norm["channel_id"], "label": norm["label"],
            "language": norm["language"], "age_min": norm["age_min"],
            "age_max": norm["age_max"], "tags": norm["tags"],
        })
        data["channels"] = chans
        self._write_raw(data)
        self.reload()
        return norm

    def remove_global_channel(self, channel_id: str) -> bool:
        cid = str(channel_id or "").strip()
        data = self._read_raw()
        chans = data.get("channels") or []
        new = [c for c in chans if str(c.get("channel_id") or "").strip() != cid]
        if len(new) == len(chans):
            return False
        data["channels"] = new
        self._write_raw(data)
        self.reload()
        return True

    def get_status(self) -> dict:
        """Trạng thái an toàn (không lộ key)."""
        return {
            "enabled": self.enabled,
            "available": self.available,
            "has_key": self._has_key,
            "channels": len(self._channels),
            "max_per_channel": self._max_per_channel,
            "cache_size": len(self._cache),
        }

    # ── Cache ────────────────────────────────────────────────────────────────
    def _get_cached(self, key: str):
        if self._cache_ttl <= 0:
            return None
        hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] <= self._cache_ttl:
            return hit[1]
        return None

    def _set_cached(self, key: str, items: list[dict]) -> None:
        if self._cache_ttl > 0 and key:
            self._cache[key] = (time.monotonic(), items)

    # ── Fetch ────────────────────────────────────────────────────────────────
    def fetch_videos(self, language=None, min_age=None, max_age=None, extra_channels=None) -> list[dict]:
        """Trả về list video (shape content_items) từ allowlist global + (tùy chọn)
        kênh gia đình `extra_channels`. Đã cache. Không bao giờ raise — lỗi => []."""
        if not self.available:
            return []
        channels = list(self._channels)
        if extra_channels:
            seen = {c["channel_id"] for c in channels}
            for raw in extra_channels:
                norm = _normalize_channel(raw)
                if norm and norm["channel_id"] not in seen:
                    channels.append(norm)
                    seen.add(norm["channel_id"])
        if not channels:
            return []
        key = "{}|{}|{}|{}".format(
            (language or "").lower(), min_age, max_age,
            ",".join(sorted(c["channel_id"] for c in channels)),
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        try:
            items = self._fetch_uncached(channels, language, min_age, max_age)
        except Exception as e:  # network/quota/parse — không phá endpoint
            logger.warning("[YouTubeLessons] fetch lỗi: %s", e)
            return []
        self._set_cached(key, items)
        return items

    def _fetch_uncached(self, channels, language, min_age, max_age) -> list[dict]:
        out: list[dict] = []
        for ch in channels:
            if language and ch["language"] != language.strip().lower():
                continue
            if min_age is not None and ch["age_max"] is not None and ch["age_max"] < min_age:
                continue
            if max_age is not None and ch["age_min"] is not None and ch["age_min"] > max_age:
                continue
            out.extend(self._fetch_channel(ch))
        return out

    def _fetch_channel(self, ch: dict) -> list[dict]:
        # UC… (channel) -> UU… (uploads playlist) — không tốn thêm call.
        uploads = "UU" + ch["channel_id"][2:]
        resp = requests.get(
            f"{_API_BASE}/playlistItems",
            params={
                "part": "snippet,contentDetails",
                "playlistId": uploads,
                "maxResults": self._max_per_channel,
                "key": self._api_key,
            },
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"playlistItems HTTP {resp.status_code}")
        rows = resp.json().get("items", [])
        video_ids = [
            r.get("contentDetails", {}).get("videoId")
            for r in rows
            if r.get("contentDetails", {}).get("videoId")
        ]
        durations = self._fetch_durations(video_ids)
        items = []
        for r in rows:
            sn = r.get("snippet", {})
            vid = r.get("contentDetails", {}).get("videoId")
            if not vid or not sn.get("title"):
                continue
            if not _title_is_safe(sn.get("title", "")):
                continue  # bỏ video có tiêu đề bị SafetyFilter chặn
            thumbs = sn.get("thumbnails", {})
            thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
            items.append({
                "content_id": f"yt-{vid}",
                "type": "video",
                "title": sn.get("title", ""),
                "description": (sn.get("description") or "")[:300],
                "source_url": f"https://www.youtube.com/watch?v={vid}",
                "thumbnail_url": thumb,
                "age_min": ch["age_min"],
                "age_max": ch["age_max"],
                "language": ch["language"],
                "tags": ch["tags"],
                "duration": _fmt_duration(durations.get(vid, "")),
                "channel": ch["label"],
                "enabled": True,
                "source": "youtube",
            })
        return items

    def _fetch_durations(self, video_ids: list[str]) -> dict[str, str]:
        if not video_ids:
            return {}
        try:
            resp = requests.get(
                f"{_API_BASE}/videos",
                params={"part": "contentDetails", "id": ",".join(video_ids[:50]), "key": self._api_key},
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                return {}
            return {
                it["id"]: it.get("contentDetails", {}).get("duration", "")
                for it in resp.json().get("items", [])
            }
        except Exception:
            return {}


# Singleton — load 1 lần khi import (giống WebSearchEngine usage).
youtube_lessons = YouTubeLessons()
