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

import re

from src.safety.vi_normalize import normalize_vi

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

        # Bước 1: Phân loại chủ đề nhạy cảm — refusal ngay nếu trigger
        if not self._topic_classifier(text):
            return False, _REFUSAL_RESPONSE

        # Bước 2: Lọc blacklist — thay thế từ xấu
        has_blacklist, clean_text = self._blacklist_filter(text)

        # Bước 3: Kiểm tra độ dài câu — cắt bớt nếu quá 4 câu (SRS ST-01)
        clean_text = self._sentence_length_check(clean_text)

        return True, clean_text

    def _blacklist_filter(self, text: str) -> tuple[bool, str]:
        """
        Lọc và thay thế các từ trong blacklist (SRS ST-04).

        Args:
            text: Chuỗi cần lọc.

        Returns:
            (has_blacklist_word, cleaned_text):
                has_blacklist_word = True nếu có từ xấu
                cleaned_text = text sau khi thay thế từ xấu bằng "..."
        """
        has_blacklist = False
        result = text
        for word, pattern in self._blacklist_regexes:
            if pattern.search(result):
                has_blacklist = True
                result = pattern.sub("...", result)
        return has_blacklist, result

    def _topic_classifier(self, text: str) -> bool:
        """
        Phát hiện chủ đề nhạy cảm bằng regex pattern matching.

        - Accented Vietnamese patterns: match trên text gốc (giữ nguyên dấu).
        - No-diacritic/English patterns: match trên text đã normalize.
        Tách hai nhóm để tránh bắn→ban = bạn→ban collision.

        Returns:
            True nếu an toàn, False nếu phát hiện chủ đề nhạy cảm.
        """
        for pattern in self._vi_regexes:
            if pattern.search(text):
                return False
        norm_text = normalize_vi(text)
        for pattern in self._norm_regexes:
            if pattern.search(norm_text):
                return False
        return True

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
