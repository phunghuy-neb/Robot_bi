"""
knowledge_client.py — Robot Bi: lớp tra cứu API ngoài (an toàn, no-key)
=======================================================================
Gom các nguồn kiến thức/giải trí công khai cho trẻ 5-12 thành một service
dùng chung: HTTP có timeout, cache TTL, và lọc nội dung qua SafetyFilter.

Nguyên tắc:
- KHÔNG bao giờ raise ra ngoài: lỗi mạng/parse → trả {"ok": False, "error": ...}.
- Nội dung chữ hiển thị cho bé (joke, fun fact, wiki, poem…) đi qua SafetyFilter
  (defense-in-depth, ngoài safe-mode của chính API).
- No-key trừ NASA (dùng DEMO_KEY nếu thiếu NASA_API_KEY trong .env).

Tất cả truy cập mạng đi qua `_get_json` / `_get_text` (module-level) để test có
thể monkeypatch, chạy offline.
"""

import html
import logging
import os
import time
from urllib.parse import quote

import requests

from src.safety.safety_filter import SafetyFilter

logger = logging.getLogger(__name__)

_TIMEOUT = 6  # giây
_CACHE_TTL = max(0, int(os.getenv("KNOWLEDGE_CACHE_TTL_SECONDS", "1800") or "0"))
_JOKE_BLACKLIST = "nsfw,religious,political,racist,sexist,explicit"

_cache: dict[str, tuple[float, dict]] = {}
_safety = SafetyFilter()


# ── HTTP + cache + safety helpers ────────────────────────────────────────────
def _get_json(url: str, params: dict | None = None, headers: dict | None = None):
    resp = requests.get(url, params=params, headers=headers, timeout=_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}")
    return resp.json()


def _get_text(url: str, params: dict | None = None) -> str:
    resp = requests.get(url, params=params, timeout=_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}")
    return (resp.text or "").strip()


def _get_cached(key: str):
    if _CACHE_TTL <= 0:
        return None
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] <= _CACHE_TTL:
        return hit[1]
    return None


def _set_cached(key: str, value: dict) -> None:
    if _CACHE_TTL > 0 and key and value:
        _cache[key] = (time.monotonic(), value)


def _safe_call(key: str, fetch) -> dict:
    """Chạy `fetch` (raise được), bọc cache + chống raise."""
    cached = _get_cached(key)
    if cached is not None:
        return cached
    try:
        data = fetch()
    except Exception as e:  # noqa: BLE001 — mọi lỗi đều degrade mượt
        logger.warning("[knowledge] %s lỗi: %s", key, e)
        return {"ok": False, "error": "unavailable"}
    out = {"ok": True, **data}
    _set_cached(key, out)
    return out


def _clean(text: str) -> str:
    """Lọc text qua SafetyFilter — không an toàn → chuỗi rỗng (bỏ)."""
    if not text or not text.strip():
        return ""
    ok, clean = _safety.check(text)
    return clean if ok else ""


# ── HỌC TẬP / NGÔN NGỮ ───────────────────────────────────────────────────────
def dictionary(word: str, lang: str = "en") -> dict:
    word = (word or "").strip()
    lang = (lang or "en").strip().lower()
    if not word:
        return {"ok": False, "error": "missing word"}

    def fetch():
        data = _get_json(f"https://api.dictionaryapi.dev/api/v2/entries/{lang}/{quote(word)}")
        entry = data[0] if isinstance(data, list) and data else {}
        phonetics = entry.get("phonetics", []) or []
        audio = next((p.get("audio") for p in phonetics if p.get("audio")), "")
        meanings = []
        for m in (entry.get("meanings", []) or [])[:3]:
            defs = [d.get("definition", "") for d in (m.get("definitions", []) or [])[:2]]
            meanings.append({"part_of_speech": m.get("partOfSpeech", ""), "definitions": defs})
        return {
            "word": entry.get("word", word),
            "phonetic": entry.get("phonetic", ""),
            "audio": audio,
            "meanings": meanings,
        }

    return _safe_call(f"dict:{lang}:{word.lower()}", fetch)


def country(name: str) -> dict:
    name = (name or "").strip()
    if not name:
        return {"ok": False, "error": "missing name"}

    def fetch():
        data = _get_json(f"https://restcountries.com/v3.1/name/{quote(name)}",
                         {"fields": "name,capital,region,population,flags,currencies,languages"})
        c = data[0] if isinstance(data, list) and data else {}
        return {
            "name": (c.get("name") or {}).get("common", name),
            "capital": (c.get("capital") or [""])[0],
            "region": c.get("region", ""),
            "population": c.get("population"),
            "flag": (c.get("flags") or {}).get("png", ""),
            "currencies": list((c.get("currencies") or {}).keys()),
            "languages": list((c.get("languages") or {}).values()),
        }

    return _safe_call(f"country:{name.lower()}", fetch)


def number_fact(number=None) -> dict:
    token = str(number).strip() if number not in (None, "") else "random"

    def fetch():
        text = _get_text(f"http://numbersapi.com/{quote(token)}")
        return {"number": token, "fact": text}

    return _safe_call(f"numfact:{token}", fetch)


def math_eval(expr: str) -> dict:
    expr = (expr or "").strip()
    if not expr:
        return {"ok": False, "error": "missing expr"}

    def fetch():
        result = _get_text("https://api.mathjs.org/v4/", {"expr": expr})
        return {"expr": expr, "result": result}

    return _safe_call(f"math:{expr}", fetch)


def trivia(amount: int = 5, category=None, difficulty=None) -> dict:
    amount = max(1, min(int(amount or 5), 20))

    def fetch():
        params = {"amount": amount, "type": "multiple"}
        if category:
            params["category"] = category
        if difficulty:
            params["difficulty"] = difficulty
        data = _get_json("https://opentdb.com/api.php", params)
        items = []
        for r in data.get("results", []):
            items.append({
                "category": html.unescape(r.get("category", "")),
                "difficulty": r.get("difficulty", ""),
                "question": html.unescape(r.get("question", "")),
                "correct_answer": html.unescape(r.get("correct_answer", "")),
                "incorrect_answers": [html.unescape(a) for a in r.get("incorrect_answers", [])],
            })
        return {"items": items, "note": "tiếng Anh — cần dịch + duyệt trước khi nạp question_bank"}

    return _safe_call(f"trivia:{amount}:{category}:{difficulty}", fetch)


# ── ĐỌC & VĂN HỌC ────────────────────────────────────────────────────────────
def books(q: str) -> dict:
    q = (q or "").strip()
    if not q:
        return {"ok": False, "error": "missing query"}

    def fetch():
        data = _get_json("https://openlibrary.org/search.json", {"q": q, "limit": 5})
        items = []
        for d in (data.get("docs") or [])[:5]:
            cover = d.get("cover_i")
            items.append({
                "title": d.get("title", ""),
                "authors": d.get("author_name", []),
                "year": d.get("first_publish_year"),
                "cover": f"https://covers.openlibrary.org/b/id/{cover}-M.jpg" if cover else "",
            })
        return {"items": items}

    return _safe_call(f"books:{q.lower()}", fetch)


def gutenberg(q: str) -> dict:
    q = (q or "").strip()
    if not q:
        return {"ok": False, "error": "missing query"}

    def fetch():
        data = _get_json("https://gutendex.com/books", {"search": q})
        items = []
        for r in (data.get("results") or [])[:5]:
            fmts = r.get("formats", {}) or {}
            text_url = fmts.get("text/plain; charset=utf-8") or fmts.get("text/plain", "")
            items.append({
                "title": r.get("title", ""),
                "authors": [a.get("name", "") for a in r.get("authors", [])],
                "text_url": text_url,
            })
        return {"items": items}

    return _safe_call(f"gutenberg:{q.lower()}", fetch)


def poem(author: str = "", title: str = "") -> dict:
    author = (author or "").strip()
    title = (title or "").strip()

    def fetch():
        if title:
            url = f"https://poetrydb.org/title/{quote(title)}"
        elif author:
            url = f"https://poetrydb.org/author/{quote(author)}"
        else:
            url = "https://poetrydb.org/random/1"
        data = _get_json(url)
        p = data[0] if isinstance(data, list) and data else {}
        lines = p.get("lines", []) or []
        return {
            "title": p.get("title", ""),
            "author": p.get("author", ""),
            "lines": lines[:30],
        }

    return _safe_call(f"poem:{author.lower()}:{title.lower()}", fetch)


def wiki(q: str, lang: str = "vi") -> dict:
    q = (q or "").strip()
    lang = (lang or "vi").strip().lower()
    if not q:
        return {"ok": False, "error": "missing query"}

    def fetch():
        data = _get_json(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(q)}")
        return {
            "title": data.get("title", q),
            "extract": _clean(data.get("extract", "")),
            "thumbnail": (data.get("thumbnail") or {}).get("source", ""),
            "url": (data.get("content_urls", {}).get("desktop", {}) or {}).get("page", ""),
        }

    return _safe_call(f"wiki:{lang}:{q.lower()}", fetch)


# ── KHOA HỌC & KHÁM PHÁ ──────────────────────────────────────────────────────
def weather(city: str) -> dict:
    city = (city or "").strip()
    if not city:
        return {"ok": False, "error": "missing city"}

    def fetch():
        geo = _get_json("https://geocoding-api.open-meteo.com/v1/search", {"name": city, "count": 1})
        results = geo.get("results") or []
        if not results:
            raise RuntimeError("city not found")
        loc = results[0]
        fc = _get_json("https://api.open-meteo.com/v1/forecast", {
            "latitude": loc["latitude"], "longitude": loc["longitude"], "current_weather": True,
        })
        cw = fc.get("current_weather", {}) or {}
        return {
            "city": loc.get("name", city),
            "country": loc.get("country", ""),
            "temperature_c": cw.get("temperature"),
            "windspeed_kmh": cw.get("windspeed"),
            "weathercode": cw.get("weathercode"),
        }

    return _safe_call(f"weather:{city.lower()}", fetch)


def iss() -> dict:
    def fetch():
        pos = _get_json("http://api.open-notify.org/iss-now.json")
        astros = _get_json("http://api.open-notify.org/astros.json")
        p = pos.get("iss_position", {}) or {}
        return {
            "latitude": p.get("latitude"),
            "longitude": p.get("longitude"),
            "people_in_space": astros.get("number"),
        }

    return _safe_call("iss", fetch)


def apod() -> dict:
    key = os.getenv("NASA_API_KEY", "DEMO_KEY").strip() or "DEMO_KEY"

    def fetch():
        data = _get_json("https://api.nasa.gov/planetary/apod", {"api_key": key})
        return {
            "title": data.get("title", ""),
            "date": data.get("date", ""),
            "explanation": (data.get("explanation", "") or "")[:600],
            "media_type": data.get("media_type", ""),
            "url": data.get("url", ""),
        }

    return _safe_call("apod", fetch)


def animal_fact(kind: str = "cat") -> dict:
    kind = (kind or "cat").strip().lower()
    if kind not in ("cat", "dog"):
        return {"ok": False, "error": "kind phải là cat hoặc dog"}

    def fetch():
        if kind == "cat":
            data = _get_json("https://catfact.ninja/fact")
            fact = data.get("fact", "")
            image = ""
        else:
            data = _get_json("https://dogapi.dog/api/v2/facts", {"limit": 1})
            facts = data.get("data") or []
            fact = (facts[0].get("attributes", {}) if facts else {}).get("body", "")
            image = (_get_json("https://dog.ceo/api/breeds/image/random") or {}).get("message", "")
        return {"animal": kind, "fact": _clean(fact), "image": image}

    return _safe_call(f"animal:{kind}", fetch)


def fun_fact() -> dict:
    def fetch():
        data = _get_json("https://uselessfacts.jsph.pl/api/v2/facts/random", {"language": "en"})
        return {"fact": _clean(data.get("text", ""))}

    return _safe_call("funfact", fetch)


# ── GIẢI TRÍ & MEDIA ─────────────────────────────────────────────────────────
def joke(jtype: str = "single") -> dict:
    jtype = "twopart" if (jtype or "").strip().lower() == "twopart" else "single"

    def fetch():
        data = _get_json("https://v2.jokeapi.dev/joke/Any", {
            "safe-mode": "", "blacklistFlags": _JOKE_BLACKLIST, "type": jtype,
        })
        if data.get("type") == "twopart":
            text = f"{data.get('setup', '')}\n{data.get('delivery', '')}".strip()
        else:
            text = data.get("joke", "")
        clean = _clean(text)
        if not clean:
            raise RuntimeError("joke filtered/empty")
        return {"type": jtype, "joke": clean}

    return _safe_call(f"joke:{jtype}", fetch)


def pokemon(name: str) -> dict:
    name = (name or "").strip().lower()
    if not name:
        return {"ok": False, "error": "missing name"}

    def fetch():
        data = _get_json(f"https://pokeapi.co/api/v2/pokemon/{quote(name)}")
        return {
            "name": data.get("name", name),
            "id": data.get("id"),
            "types": [t.get("type", {}).get("name", "") for t in data.get("types", [])],
            "sprite": (data.get("sprites", {}) or {}).get("front_default", ""),
        }

    return _safe_call(f"pokemon:{name}", fetch)


def disney(name: str) -> dict:
    name = (name or "").strip()
    if not name:
        return {"ok": False, "error": "missing name"}

    def fetch():
        data = _get_json("https://api.disneyapi.dev/character", {"name": name})
        rows = data.get("data") or []
        c = rows[0] if isinstance(rows, list) and rows else (rows if isinstance(rows, dict) else {})
        return {
            "name": c.get("name", name),
            "films": (c.get("films") or [])[:5],
            "image": c.get("imageUrl", ""),
        }

    return _safe_call(f"disney:{name.lower()}", fetch)


def status() -> dict:
    """Liệt kê nguồn + nguồn nào cần key (không lộ key)."""
    return {
        "ok": True,
        "no_key_sources": [
            "dictionary", "country", "number_fact", "math", "trivia", "books",
            "gutenberg", "poem", "wiki", "weather", "iss", "animal_fact",
            "fun_fact", "joke", "pokemon", "disney",
        ],
        "key_sources": {"apod": "NASA_API_KEY (mặc định DEMO_KEY)"},
        "cache_ttl_seconds": _CACHE_TTL,
    }
