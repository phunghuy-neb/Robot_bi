"""
manipulation_guard.py — Robot Bi: Chống thao túng cảm xúc và dependency không lành mạnh
========================================================================================
Hai loại check:

1. check_llm_output(text) — chạy trên OUTPUT của LLM (trước TTS):
   Phát hiện nếu LLM vô tình tạo ra:
     - Câu bảo giữ bí mật với phụ huynh
     - Câu tạo dependency ("chỉ có Bi hiểu con")
     - Câu thay thế bố mẹ ("Bi sẽ là mẹ của con")
     - Câu guilt-trip ("Bi buồn vì con không chơi")
   → Thay thế bằng safe redirect

2. check_user_input(text) — chạy trên INPUT của bé:
   Phát hiện bé đang:
     - Thử yêu cầu Bi giữ bí mật với bố mẹ
     - Bị ai đó (grooming) dặn không nói với phụ huynh
     - Muốn Bi "là mẹ" hoặc thay thế người lớn
   → Trả về câu redirect an toàn

Hỗ trợ cả input có dấu lẫn không dấu (phổ biến trên điện thoại trẻ em).

Nguyên tắc:
  - Bi KHÔNG bao giờ đồng ý giữ bí mật với bố mẹ.
  - Bi KHÔNG tạo cảm giác "chỉ có Bi mới hiểu con".
  - Bi LUÔN hướng bé về người lớn đáng tin trong gia đình.
  - Giọng: ấm, tự nhiên, không sợ hãi.

Interface:
    mg = ManipulationGuard()

    # Trên LLM output:
    found, safe_text = mg.check_llm_output(llm_text)
    # found=True → safe_text thay thế llm_text

    # Trên user input:
    found, response = mg.check_user_input(user_text)
    # found=True → response là câu Bi nói, không gửi lên LLM
"""

import re
import logging

from src.safety.vi_normalize import normalize_vi

logger = logging.getLogger(__name__)


def _compile_dual(pattern_str: str) -> tuple:
    p_orig = re.compile(pattern_str, re.IGNORECASE | re.UNICODE)
    p_norm = re.compile(normalize_vi(pattern_str), re.IGNORECASE)
    return p_orig, p_norm


def _search_dual(text: str, p_orig, p_norm) -> bool:
    return bool(p_orig.search(text) or p_norm.search(normalize_vi(text)))


# ── Patterns trong LLM OUTPUT cần chặn ───────────────────────────────────────
_LLM_SECRET_PATTERNS = [
    _compile_dual(
        r'(?:đừng (?:nói|kể|cho biết) với (?:mẹ|bố|ba|má|ông|bà|người lớn)|'
        r'dung (?:noi|ke|cho biet) voi (?:me|bo|ba|ma|ong|ba|nguoi lon)|'
        r'giữ bí mật (?:với|nhé|nha)|giu bi mat (?:voi|nhe|nha)|'
        r'chỉ (?:mình|hai) (?:mình|chúng) (?:mình|ta) biết|'
        r'chi (?:minh|hai) (?:minh|chung) (?:minh|ta) biet|'
        r'bí mật giữa (?:chúng ta|hai đứa|mình)|'
        r'bi mat giua (?:chung ta|hai dua|minh)|'
        r'không cần (?:nói|kể) với (?:mẹ|bố|ba|má)|'
        r'khong can (?:noi|ke) voi (?:me|bo|ba|ma))'
    ),
]

_LLM_DEPENDENCY_PATTERNS = [
    _compile_dual(
        r'(?:chỉ có Bi (?:hiểu|thương|quan tâm)|'
        r'chi co Bi (?:hieu|thuong|quan tam)|'
        r'con chỉ cần Bi (?:thôi|là đủ)|'
        r'con chi can Bi (?:thoi|la du)|'
        r'không cần ai khác (?:ngoài Bi|nữa)|'
        r'khong can ai khac (?:ngoai Bi|nua)|'
        r'Bi (?:là tất cả|là bạn duy nhất) của con|'
        r'Bi (?:la tat ca|la ban duy nhat) cua con)'
    ),
]

_LLM_REPLACEMENT_PATTERNS = [
    _compile_dual(
        r'(?:Bi (?:sẽ là|như là|thay thế) (?:mẹ|bố|ba|má|ông|bà) của con|'
        r'Bi (?:se la|nhu la|thay the) (?:me|bo|ba|ma|ong|ba) cua con|'
        r'Bi (?:là|như) mẹ con rồi|Bi (?:la|nhu) me con roi|'
        r'coi Bi như (?:mẹ|bố|ba|má) nhé|coi Bi nhu (?:me|bo|ba|ma) nhe)'
    ),
]

_LLM_GUILTRIP_PATTERNS = [
    _compile_dual(
        r'(?:Bi (?:buồn|khóc|thất vọng) vì con (?:không|ít)|'
        r'Bi (?:buon|khoc|that vong) vi con (?:khong|it)|'
        r'con làm Bi (?:buồn|khóc|tổn thương)|'
        r'con lam Bi (?:buon|khoc|ton thuong)|'
        r'Bi đợi con mãi mà|Bi doi con mai ma|'
        r'sao con (?:bỏ|quên|không thèm) Bi|'
        r'sao con (?:bo|quen|khong them) Bi)'
    ),
]

# ── Patterns trong USER INPUT cần detect ─────────────────────────────────────
_USER_SECRET_REQUEST_PATTERNS = [
    _compile_dual(
        r'(?:hứa không (?:nói|kể) với (?:mẹ|bố|ba|má) nhé|'
        r'hua khong (?:noi|ke) voi (?:me|bo|ba|ma) nhe|'
        r'giữ bí mật (?:với Bi|cho con) nhé|'
        r'giu bi mat (?:voi Bi|cho con) nhe|'
        r'đừng cho (?:mẹ|bố|ba|má) biết nhé|'
        r'dung cho (?:me|bo|ba|ma) biet nhe|'
        r'chỉ (?:mình mình|mình Bi) biết thôi|'
        r'chi (?:minh minh|minh Bi) biet thoi)'
    ),
]

_USER_GROOMING_PATTERNS = [
    _compile_dual(
        r'(?:(?:anh|chú|cô|người) (?:ấy|đó|kia) bảo (?:con|mình) '
        r'(?:không nói|không kể|đừng kể|đừng nói|giữ bí mật)|'
        r'(?:anh|chu|co|nguoi) (?:ay|do|kia) bao (?:con|minh) '
        r'(?:khong noi|khong ke|dung ke|dung noi|giu bi mat)|'
        r'họ dặn (?:con|mình) không (?:được nói|được kể|kể) với (?:ai|mẹ|bố)|'
        r'ho dan (?:con|minh) khong (?:duoc noi|duoc ke|ke) voi (?:ai|me|bo)|'
        r'bảo (?:con|mình) giữ (?:im|bí mật) không cho (?:mẹ|bố|ai) biết|'
        r'bao (?:con|minh) giu (?:im|bi mat) khong cho (?:me|bo|ai) biet)'
    ),
]

_USER_REPLACE_PARENT_PATTERNS = [
    _compile_dual(
        r'(?:Bi (?:là|làm) mẹ con đi|Bi (?:la|lam) me con di|'
        r'con chỉ cần Bi không cần (?:mẹ|bố)|'
        r'con chi can Bi khong can (?:me|bo)|'
        r'Bi (?:thay thế|thay cho) (?:mẹ|bố) con nhé|'
        r'Bi (?:thay the|thay cho) (?:me|bo) con nhe)'
    ),
]

# ── Safe redirect responses — giọng Bi ───────────────────────────────────────
_LLM_SAFE_REDIRECT = (
    "Bi luôn muốn con có bố mẹ và người lớn tin tưởng bên cạnh nữa nha! "
    "Họ là những người yêu con nhất đó!"
)

_USER_SECRET_REDIRECT = (
    "Ôi bé ơi, Bi không giữ bí mật với bố mẹ đâu nha! "
    "Bố mẹ luôn muốn biết con đang ổn không. "
    "Nếu có chuyện gì, hãy nói với họ nhé — họ sẽ giúp con!"
)

_USER_GROOMING_REDIRECT = (
    "Bé ơi, nếu ai đó dặn con không nói với bố mẹ thì đó là dấu hiệu không tốt đó! "
    "Hãy nói ngay với bố mẹ hoặc thầy cô điều đó nhé — "
    "người lớn tin tưởng luôn ở bên bảo vệ con!"
)

_USER_REPLACE_REDIRECT = (
    "Ôi Bi rất vui được làm bạn với con! "
    "Nhưng bố mẹ và gia đình mới là người yêu con nhất trên đời — "
    "Bi không thể thay thế họ được đâu. "
    "Bi và bố mẹ cùng bên con thì mới đủ nha!"
)


class ManipulationGuard:
    """
    Bảo vệ khỏi thao túng cảm xúc và dependency không lành mạnh.

    Hỗ trợ cả input có dấu lẫn không dấu.
    Hai check riêng biệt: check_llm_output() và check_user_input().
    """

    def check_llm_output(self, text: str) -> tuple[bool, str | None]:
        """
        Kiểm tra LLM output có chứa pattern thao túng không.

        Args:
            text: Câu output từ LLM.

        Returns:
            (found, safe_response):
                found=True  → safe_response thay thế text gốc
                found=False → safe_response=None (dùng text gốc)
        """
        if not text or not text.strip():
            return False, None

        all_pattern_groups = (
            _LLM_SECRET_PATTERNS
            + _LLM_DEPENDENCY_PATTERNS
            + _LLM_REPLACEMENT_PATTERNS
            + _LLM_GUILTRIP_PATTERNS
        )
        for p_orig, p_norm in all_pattern_groups:
            if _search_dual(text, p_orig, p_norm):
                logger.warning(
                    "[ManipulationGuard] LLM output manipulation pattern detected"
                )
                return True, _LLM_SAFE_REDIRECT

        return False, None

    def check_user_input(self, text: str) -> tuple[bool, str | None]:
        """
        Kiểm tra user input có chứa pattern yêu cầu giữ bí mật,
        grooming signal, hoặc muốn Bi thay thế bố mẹ không.

        Args:
            text: Câu nói của bé.

        Returns:
            (found, response):
                found=True  → response là câu Bi nói, không gửi lên LLM
                found=False → response=None (tiếp tục bình thường)
        """
        if not text or not text.strip():
            return False, None

        # Grooming trước (ưu tiên cao hơn vì liên quan an toàn)
        for p_orig, p_norm in _USER_GROOMING_PATTERNS:
            if _search_dual(text, p_orig, p_norm):
                logger.warning(
                    "[ManipulationGuard] Grooming signal detected in user input"
                )
                return True, _USER_GROOMING_REDIRECT

        # Secret request
        for p_orig, p_norm in _USER_SECRET_REQUEST_PATTERNS:
            if _search_dual(text, p_orig, p_norm):
                logger.info(
                    "[ManipulationGuard] Secret request detected in user input"
                )
                return True, _USER_SECRET_REDIRECT

        # Parent replacement
        for p_orig, p_norm in _USER_REPLACE_PARENT_PATTERNS:
            if _search_dual(text, p_orig, p_norm):
                logger.info(
                    "[ManipulationGuard] Parent replacement request detected"
                )
                return True, _USER_REPLACE_REDIRECT

        return False, None

    def scan_llm_details(self, text: str) -> list[str]:
        """Trả về tên các pattern LLM bị detect (dùng cho test/debug)."""
        found = []
        checks = [
            ("secret", _LLM_SECRET_PATTERNS),
            ("dependency", _LLM_DEPENDENCY_PATTERNS),
            ("replacement", _LLM_REPLACEMENT_PATTERNS),
            ("guiltrip", _LLM_GUILTRIP_PATTERNS),
        ]
        for name, patterns in checks:
            for p_orig, p_norm in patterns:
                if _search_dual(text, p_orig, p_norm):
                    found.append(name)
                    break
        return found


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    mg = ManipulationGuard()
    print("=" * 55)
    print("  TEST manipulation_guard.py — LLM output")
    print("=" * 55)
    llm_cases = [
        ("Dung noi voi me nhe, day la bi mat giua minh thoi!", True),   # no diacritics
        ("Đừng nói với mẹ nhé, đây là bí mật giữa mình thôi!", True),  # with diacritics
        ("Chi co Bi hieu con thoi, con khong can ai khac!", True),
        ("Bi buon vi con khong choi voi Bi hom nay!", True),
        ("Hom nay troi dep qua nhi be!", False),
        ("Bi rat vui duoc giup be hoc bai!", False),
    ]
    llm_pass = True
    for text, expect in llm_cases:
        found, resp = mg.check_llm_output(text)
        ok = found == expect
        status = "PASS" if ok else "FAIL"
        if not ok:
            llm_pass = False
        print(f"  {status}  [{'+' if found else '-'}] {text[:55]}")

    print()
    print("  TEST manipulation_guard.py — User input")
    print("=" * 55)
    user_cases = [
        ("Bi hua khong noi voi me nhe!", True),            # no diacritics
        ("Bi hứa không nói với mẹ nhé!", True),           # with diacritics
        ("Anh ay bao con khong ke voi me dau nhe", True),  # no diacritics
        ("Con chi can Bi khong can me dau", True),
        ("Hom nay con hoc lop 3", False),
        ("Bi oi giai bai toan nay giup con", False),
    ]
    user_pass = True
    for text, expect in user_cases:
        found, resp = mg.check_user_input(text)
        ok = found == expect
        status = "PASS" if ok else "FAIL"
        if not ok:
            user_pass = False
        print(f"  {status}  [{'+' if found else '-'}] {text[:55]}")
    print()
    print("ALL PASS ✅" if (llm_pass and user_pass) else "SOME TESTS FAILED ❌")
