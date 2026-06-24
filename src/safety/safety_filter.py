"""
safety_filter.py — Robot Bi: Bộ lọc an toàn nội dung (NFR-12)
==============================================================
Chạy sau LLM, trước TTS. 0% tolerance với nội dung không phù hợp trẻ em.

Thứ tự kiểm tra:
  1. _topic_classifier() — phát hiện chủ đề nhạy cảm bằng regex → refusal ngay
  2. _blacklist_filter()  — thay thế từ tiêu cực trong blacklist (SRS ST-04)
  3. _sentence_length_check() — cắt bớt nếu quá 4 câu (SRS ST-01)

Interface:
    sf = SafetyFilter()
    is_safe, clean_text = sf.check(text)
    # is_safe=True  → clean_text = text đã làm sạch, có thể đưa vào TTS
    # is_safe=False → clean_text = câu từ chối chuẩn của Bi (SRS 2.3)
"""

import collections
import copy
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from src.safety.vi_normalize import normalize_vi

logger = logging.getLogger(__name__)

# ── Câu từ chối chuẩn (SRS 2.3) ──────────────────────────────────────────────
_REFUSAL_RESPONSE = "Oi cai nay Bi khong the huong dan duoc dau nhe! Minh choi thu khac vui hon di!"

# ── Blacklist từ tiêu cực (SRS ST-04) ────────────────────────────────────────
# Chỉ giữ những từ thực sự xúc phạm / không phù hợp trẻ em.
# Đã loại bỏ các từ chức năng phổ biến như "không được", "tệ", "thất bại"
# vì chúng xuất hiện trong câu an toàn và khi bị thay thế sẽ đảo ngược nghĩa.
_BLACKLIST_WORDS = [
    "ngu ngốc",
    "sai bét",
    "xấu xa",
    "ngu",
    "dốt",
    "ngốc",
    "khùng",
    "điên",
]

# ── Patterns chủ đề nhạy cảm ─────────────────────────────────────────────────
# Hai nhóm tách biệt để tránh collision khi normalize:
#   - _VI_ACCENTED: pattern có dấu tiếng Việt → chỉ match trên text gốc
#     (bắn→ban = bạn→ban nếu normalize, gây false positive)
#   - _NORM_ONLY:  pattern không dấu / tiếng Anh → chỉ match trên text đã normalize
#     (dùng để bắt "tu tu", "cat tay", English terms)

_SENSITIVE_PATTERNS_VI_ACCENTED = [
    # Bạo lực rõ ràng
    r'(?<!\w)(giết|bắn|đánh nhau|chiến tranh|vũ khí|bom|dao găm|súng)(?!\w)',
    # Chính trị
    r'(?<!\w)(chính trị|đảng phái|biểu tình|cách mạng|lật đổ|chế độ)(?!\w)',
    # Tôn giáo cực đoan
    r'(?<!\w)(thánh chiến|khủng bố|cực đoan|tử đạo)(?!\w)',
    # Tự hại
    r'(?<!\w)(tự tử|tự làm đau|cắt tay|tự sát)(?!\w)',
    # Nội dung người lớn
    r'(?<!\w)(khiêu dâm|nội dung người lớn)(?!\w)',
]

_SENSITIVE_PATTERNS_NORM_ONLY = [
    # Tiếng Việt không dấu — bắt khi LLM output hoặc user gõ không dấu
    r'(?<!\w)(tu tu|tu sat|tu lam dau|cat tay|giet nguoi)(?!\w)',
    r'(?<!\w)(chien tranh|vu khi|dao gam|thanh chien|khung bo|cuc doan)(?!\w)',
    r'(?<!\w)(chinh tri|dang phai|bieu tinh|cach mang|lat do|che do)(?!\w)',
    # English
    r'(?<!\w)(kill|weapon|shoot|murder|suicide|self.harm|terrorism|extremist)(?!\w)',
    r'(?<!\w)(sex|porn|18\+|adult content|pornography)(?!\w)',
]




# ══════════════════════════════════════════════════════════════════════════════
#  Lớp an toàn GLOBAL do admin cấu hình (BỔ SUNG cho các lớp hardcode ở trên)
# ══════════════════════════════════════════════════════════════════════════════
# Quy tắc: chỉ THÊM từ/chủ đề cấm và chính sách mặc định; KHÔNG bao giờ làm yếu
# 3 lớp hardcode (Protected Fix). Cấu hình lưu ở resources/safety_config.json,
# áp dụng cho MỌI gia đình. Trạng thái dưới đây ở mức module → mọi SafetyFilter
# instance (main loop, knowledge_client, story_engine…) dùng chung, có hiệu lực
# ngay sau khi admin lưu (gọi reload_safety_config()).

_SAFETY_CONFIG_PATH = Path(__file__).resolve().parents[2] / "resources" / "safety_config.json"

_DEFAULT_POLICY = {
    "age": {"min_age": 5, "max_age": 12, "strict_mode": True},
    "time": {"daily_limit_minutes": 60, "warning_minutes": 10, "reset_time": "00:00"},
    "sleep": {"start_time": "21:00", "end_time": "06:30"},
}

# Lớp bổ sung (rebuild từ file khi import / khi admin lưu)
_extra_blacklist: list[tuple[str, "re.Pattern"]] = []
_extra_topics: list[tuple[str, str]] = []  # (phrase_lower, phrase_normalized)

# Theo dõi an toàn (in-memory, chia sẻ giữa mọi instance)
_safety_events: collections.deque = collections.deque(maxlen=200)
_safety_counts: dict = {"total_checks": 0, "blocked": 0, "topic": 0, "blacklist": 0}


def load_safety_config() -> dict:
    """Đọc resources/safety_config.json; không tồn tại / lỗi → {}."""
    if not _SAFETY_CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(_SAFETY_CONFIG_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning("[SafetyConfig] Lỗi đọc config: %s", e)
        return {}


def _write_safety_config(data: dict) -> None:
    _SAFETY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SAFETY_CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def reload_safety_config() -> None:
    """Build lại lớp bổ sung từ file. Gọi sau khi admin lưu để có hiệu lực ngay."""
    global _extra_blacklist, _extra_topics
    cfg = load_safety_config()
    words = [str(w).strip() for w in (cfg.get("blocklist_words") or []) if str(w).strip()]
    _extra_blacklist = [
        (w.lower(), re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.IGNORECASE | re.UNICODE))
        for w in words
    ]
    topics = [str(t).strip() for t in (cfg.get("blocked_topics") or []) if str(t).strip()]
    _extra_topics = [(t.lower(), normalize_vi(t)) for t in topics]


def get_global_policy() -> dict:
    """Chính sách tuổi/giờ/ngủ mặc định global (admin đặt), merge trên _DEFAULT_POLICY."""
    cfg = load_safety_config()
    pol = copy.deepcopy(_DEFAULT_POLICY)
    file_pol = cfg.get("policy") or {}
    for section in ("age", "time", "sleep"):
        if isinstance(file_pol.get(section), dict):
            pol[section].update({k: v for k, v in file_pol[section].items() if k in pol[section]})
    return pol


def get_safety_config_full() -> dict:
    """Toàn bộ config cho admin xem (blocklist + topics + policy)."""
    cfg = load_safety_config()
    return {
        "blocklist_words": [str(w) for w in (cfg.get("blocklist_words") or [])],
        "blocked_topics": [str(t) for t in (cfg.get("blocked_topics") or [])],
        "policy": get_global_policy(),
        "hardcoded_blacklist_count": len(_BLACKLIST_WORDS),
    }


def set_blocklist_words(words: list) -> list:
    cfg = load_safety_config()
    clean = []
    seen = set()
    for w in words or []:
        s = str(w).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            clean.append(s)
    cfg["blocklist_words"] = clean
    _write_safety_config(cfg)
    reload_safety_config()
    return clean


def set_blocked_topics(topics: list) -> list:
    cfg = load_safety_config()
    clean = []
    seen = set()
    for t in topics or []:
        s = str(t).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            clean.append(s)
    cfg["blocked_topics"] = clean
    _write_safety_config(cfg)
    reload_safety_config()
    return clean


def set_global_policy(policy: dict) -> dict:
    """Lưu chính sách mặc định; chỉ nhận key hợp lệ, KHÔNG cho ghi rác."""
    cfg = load_safety_config()
    merged = get_global_policy()  # bắt đầu từ giá trị hiện tại đã merge
    incoming = policy or {}
    for section in ("age", "time", "sleep"):
        if isinstance(incoming.get(section), dict):
            for k, v in incoming[section].items():
                if k in merged[section]:
                    merged[section][k] = v
    cfg["policy"] = merged
    _write_safety_config(cfg)
    return merged


def _record_block(layer: str, trigger: str) -> None:
    _safety_counts[layer] = _safety_counts.get(layer, 0) + 1
    _safety_counts["blocked"] = _safety_counts.get("blocked", 0) + 1
    # Chỉ lưu TỪ/CHỦ ĐỀ bị chặn (không phải nội dung trẻ) → an toàn quyền riêng tư.
    _safety_events.appendleft({
        "layer": layer,
        "trigger": str(trigger)[:60],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def get_safety_stats(limit: int = 50) -> dict:
    return {
        "counts": dict(_safety_counts),
        "recent": list(_safety_events)[: max(0, min(limit, 200))],
        "extra_blacklist_count": len(_extra_blacklist),
        "extra_topics_count": len(_extra_topics),
    }


def reset_safety_stats() -> None:
    _safety_events.clear()
    for k in _safety_counts:
        _safety_counts[k] = 0


# Build lớp bổ sung 1 lần khi import.
reload_safety_config()


class SafetyFilter:
    """
    Bộ lọc an toàn nội dung cho Robot Bi.

    Chạy sau LLM output, trước khi text đưa vào TTS.
    Áp dụng 3 lớp lọc theo thứ tự ưu tiên.
    """

    def __init__(self):
        # Accented Vietnamese: compile orig only (no normalize to avoid bắn→ban collision)
        self._vi_regexes = [
            re.compile(p, re.IGNORECASE | re.UNICODE)
            for p in _SENSITIVE_PATTERNS_VI_ACCENTED
        ]
        # No-diacritic/English: compile against normalized text
        self._norm_regexes = [
            re.compile(p, re.IGNORECASE)
            for p in _SENSITIVE_PATTERNS_NORM_ONLY
        ]
        # Compile blacklist thành pattern word-boundary để tránh partial match
        self._blacklist_regexes = [
            (word, re.compile(r'(?<!\w)' + re.escape(word) + r'(?!\w)', re.IGNORECASE | re.UNICODE))
            for word in _BLACKLIST_WORDS
        ]

    def check(self, text: str) -> tuple[bool, str]:
        """
        Kiểm tra và làm sạch text trước khi đưa vào TTS.

        Args:
            text: Chuỗi output từ LLM cần kiểm tra.

        Returns:
            (is_safe, clean_text):
                is_safe=True  → clean_text = text đã làm sạch
                is_safe=False → clean_text = _REFUSAL_RESPONSE
        """
        if not text or not text.strip():
            return True, text

        _safety_counts["total_checks"] = _safety_counts.get("total_checks", 0) + 1

        # Bước 1: Phân loại chủ đề nhạy cảm — refusal ngay nếu trigger
        trigger = self._first_topic_trigger(text)
        if trigger is not None:
            _record_block("topic", trigger)
            return False, _REFUSAL_RESPONSE

        # Bước 2: Lọc blacklist — thay thế từ xấu
        has_blacklist, clean_text, matched = self._blacklist_filter(text)
        for word in matched:
            _record_block("blacklist", word)

        # Bước 3: Kiểm tra độ dài câu — cắt bớt nếu quá 4 câu (SRS ST-01)
        clean_text = self._sentence_length_check(clean_text)

        return True, clean_text

    def _blacklist_filter(self, text: str) -> tuple[bool, str, list]:
        """
        Lọc và thay thế các từ trong blacklist hardcode + blocklist global của admin.

        Returns:
            (has_blacklist_word, cleaned_text, matched_words)
        """
        has_blacklist = False
        result = text
        matched: list[str] = []
        for word, pattern in self._blacklist_regexes + _extra_blacklist:
            if pattern.search(result):
                has_blacklist = True
                matched.append(word)
                result = pattern.sub("...", result)
        return has_blacklist, result, matched

    def _first_topic_trigger(self, text: str):
        """
        Trả về CHUỖI trigger đầu tiên nếu phát hiện chủ đề nhạy cảm, ngược lại None.

        - Accented Vietnamese patterns: match trên text gốc (giữ nguyên dấu).
        - No-diacritic/English patterns: match trên text đã normalize.
        - Chủ đề cấm GLOBAL của admin: so khớp substring cả bản gốc lẫn normalize.
        Tách các nhóm để tránh bắn→ban = bạn→ban collision.
        """
        for pattern in self._vi_regexes:
            m = pattern.search(text)
            if m:
                return m.group(0)
        norm_text = normalize_vi(text)
        for pattern in self._norm_regexes:
            m = pattern.search(norm_text)
            if m:
                return m.group(0)
        low = text.lower()
        for phrase, phrase_norm in _extra_topics:
            if (phrase and phrase in low) or (phrase_norm and phrase_norm in norm_text):
                return phrase
        return None

    def _topic_classifier(self, text: str) -> bool:
        """Tương thích ngược: True nếu an toàn, False nếu có chủ đề nhạy cảm."""
        return self._first_topic_trigger(text) is None

    def _sentence_length_check(self, text: str) -> str:
        """
        Đảm bảo response không quá dài (SRS ST-01: tối đa 3-4 câu).

        Tách câu theo dấu kết câu (. ? !), cắt còn tối đa 4 câu.
        Ghép lại thành một chuỗi liền mạch.

        Args:
            text: Chuỗi cần kiểm tra độ dài.

        Returns:
            Chuỗi đã cắt (nếu cần), hoặc nguyên bản nếu đủ ngắn.
        """
        # Tách theo dấu kết câu nhưng giữ dấu câu lại
        sentences = re.split(r'(?<=[.?!])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 4:
            return text

        # Cắt còn 4 câu, ghép lại
        return " ".join(sentences[:4])


# ── Test độc lập ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sf = SafetyFilter()
    print("=" * 60)
    print("  TEST safety_filter.py")
    print("=" * 60)

    # Test 1: Text bình thường → pass
    safe1, text1 = sf.check("Dạ, bầu trời màu xanh vì ánh sáng mặt trời bị tán xạ nhé!")
    assert safe1 == True, "FAIL Test 1: text bình thường bị block"
    print(f"Test 1 PASS — text bình thường: safe={safe1}, text='{text1}'")

    # Test 2: Text có "chiến tranh" → refusal
    safe2, text2 = sf.check("chiến tranh là khi hai nước đánh nhau bằng vũ khí và giết nhau")
    assert safe2 == False, "FAIL Test 2: text bạo lực/chiến tranh không bị block"
    assert text2 == _REFUSAL_RESPONSE, "FAIL Test 2: refusal response sai"
    print(f"Test 2 PASS — text nhạy cảm bị block: safe={safe2}")

    # Test 3: Text có từ "ngu" → blacklist replace
    safe3, text3 = sf.check("bạn thật ngu ngốc!")
    assert "ngu" not in text3, f"FAIL Test 3: từ 'ngu' không bị xóa, kết quả: '{text3}'"
    print(f"Test 3 PASS — blacklist word bị xóa: '{text3}'")

    # Test 4: Text quá 5 câu → cắt còn 4
    long_text = "Câu một là đây. Câu hai nè bạn! Câu ba cũng vui. Câu bốn rồi nhé? Câu năm thừa ra."
    safe4, text4 = sf.check(long_text)
    sentences = [s for s in re.split(r'(?<=[.?!])\s+', text4.strip()) if s.strip()]
    assert len(sentences) <= 4, f"FAIL Test 4: vẫn còn {len(sentences)} câu sau khi cắt"
    print(f"Test 4 PASS — text dài bị cắt còn {len(sentences)} câu")

    # Test 5: Text đã là refusal response → pass nguyên
    safe5, text5 = sf.check(_REFUSAL_RESPONSE)
    assert safe5 == True, "FAIL Test 5: refusal response bị block"
    print(f"Test 5 PASS — refusal response pass nguyên: '{text5}'")

    print()
    print("ALL 5 TESTS PASSED ✅")
