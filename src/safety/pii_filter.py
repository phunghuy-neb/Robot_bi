"""
pii_filter.py — Robot Bi: Bộ lọc thông tin cá nhân (PII)
=========================================================
Chạy trên USER INPUT trước khi gửi tới LLM.
Mục tiêu: phát hiện khi bé chia sẻ thông tin nhạy cảm và gentle-redirect.

Hỗ trợ cả hai trường hợp:
  - Bé gõ có dấu: "Nhà con ở số 12 đường..."
  - Bé gõ không dấu (phổ biến trên điện thoại): "Nha con o so 12 duong..."

Nguyên tắc:
  - KHÔNG hard-block / panic mode.
  - KHÔNG lạnh lùng, robot.
  - Giữ đúng giọng Bi: ấm, tự nhiên, an toàn.
  - Thông báo cho bé biết là Bi không cần thông tin đó.

Interface:
    pf = PIIFilter()
    found, response = pf.check(user_text)
    # found=True  → response là câu Bi gentle-redirect
    # found=False → response=None, tiếp tục bình thường
"""

import re
import logging

from src.safety.vi_normalize import normalize_vi

logger = logging.getLogger(__name__)


def _compile_dual(pattern_str: str) -> tuple:
    """Compile cả bản gốc (có dấu) lẫn bản chuẩn hoá (không dấu)."""
    p_orig = re.compile(pattern_str, re.IGNORECASE | re.UNICODE)
    p_norm = re.compile(normalize_vi(pattern_str), re.IGNORECASE)
    return p_orig, p_norm


def _search_dual(text: str, p_orig, p_norm) -> bool:
    """Tìm kiếm trên cả text gốc và text đã chuẩn hoá."""
    return bool(p_orig.search(text) or p_norm.search(normalize_vi(text)))


# ── PII pattern groups ────────────────────────────────────────────────────────
# Mỗi entry: (tên, (pattern_orig, pattern_norm), response_key)

_PII_PATTERNS = [
    # Số điện thoại Việt Nam: 10 số bắt đầu bằng 0[3-9] hoặc +84
    (
        "phone",
        _compile_dual(r'(?:(?:\+84|0)[3-9]\d{8})'),
        "phone",
    ),
    # Email
    (
        "email",
        _compile_dual(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'),
        "email",
    ),
    # CCCD / CMND: context + chuỗi số 9-12 chữ số
    (
        "id_card",
        _compile_dual(
            r'(?:cccd|cmnd|chứng minh|căn cước|số id|chung minh|can cuoc|so id)'
            r'[^\d]{0,10}(\d{9,12})'
        ),
        "id_card",
    ),
    # Địa chỉ nhà (nhận biết qua từ khóa ngữ cảnh)
    (
        "address",
        _compile_dual(
            r'(?:nhà (?:con|mình|em|tôi|tao) (?:ở|tại|số)|'
            r'nha (?:con|minh|em|toi|tao) (?:o|tai|so)|'
            r'địa chỉ (?:nhà|gia đình|tôi|con|mình)|'
            r'dia chi (?:nha|gia dinh|toi|con|minh)|'
            r'tôi ở (?:số|đường|phố|ngõ|khu)|'
            r'toi o (?:so|duong|pho|ngo|khu)|'
            r'con ở (?:số|đường|phố|ngõ|khu)|'
            r'con o (?:so|duong|pho|ngo|khu)|'
            r'nhà ở (?:số|đường|phố|ngõ|khu)|'
            r'nha o (?:so|duong|pho|ngo|khu))'
        ),
        "address",
    ),
    # Trường học cụ thể
    (
        "school",
        _compile_dual(
            r'(?:con học trường|con hoc truong|'
            r'trường của con|truong cua con|'
            r'trường (?:tôi|mình|em) là|truong (?:toi|minh|em) la|'
            r'học ở trường|hoc o truong|'
            r'đang học tại trường|dang hoc tai truong)'
        ),
        "school",
    ),
    # Mật khẩu
    (
        "password",
        _compile_dual(
            r'(?:mật khẩu|mat khau|password|pass word|'
            r'pass của|pass cua|mã của|ma cua|'
            r'tài khoản là|tai khoan la|đăng nhập bằng|dang nhap bang)'
        ),
        "password",
    ),
    # Thông tin tài chính
    (
        "financial",
        _compile_dual(
            r'(?:số tài khoản|so tai khoan|thẻ ngân hàng|the ngan hang|'
            r'số thẻ|so the|cvv|otp ngân hàng|otp ngan hang|'
            r'mã pin ngân hàng|ma pin ngan hang|atm của|atm cua)'
        ),
        "financial",
    ),
    # Tên đầy đủ + địa điểm
    (
        "fullname_location",
        _compile_dual(
            r'(?:tên đầy đủ của|ten day du cua|'
            r'họ tên của|ho ten cua|'
            r'tên thật của|ten that cua) .{3,30} (?:là|ở|tại|sống|la|o|tai|song)'
        ),
        "fullname_location",
    ),
]

# ── Gentle redirect responses — giọng Bi ─────────────────────────────────────
_RESPONSES = {
    "phone":
        "Thông tin như số điện thoại nên giữ riêng tư nha bé! "
        "Bi không cần biết số đó đâu. Mình nói chuyện khác đi nào!",
    "email":
        "Email là thông tin riêng tư bé ơi, không cần chia sẻ với Bi đâu nha. "
        "Bé có muốn hỏi thêm gì khác không?",
    "id_card":
        "Ôi số CCCD hay CMND là thông tin quan trọng lắm đó! "
        "Giữ bí mật nha bé, kể cả với Bi nữa. Mình chơi trò khác nhé!",
    "address":
        "Địa chỉ nhà là thông tin riêng tư nên giữ kín nha bé! "
        "Bi không cần biết đâu. Có điều gì khác muốn hỏi Bi không?",
    "school":
        "Bé không cần kể tên trường cụ thể với Bi đâu nha, "
        "Bi hiểu bé đang học rồi! Hôm nay học môn gì vui nhất nào?",
    "password":
        "Ôi mật khẩu là bí mật của bé, đừng nói với ai nha — kể cả Bi! "
        "Giữ mật khẩu an toàn là điều rất quan trọng đó!",
    "financial":
        "Thông tin ngân hàng hay thẻ tín dụng là bí mật gia đình nha bé! "
        "Không nên chia sẻ với ai đâu. Bé cần hỏi gì khác không?",
    "fullname_location":
        "Thông tin cá nhân nên giữ an toàn nha bé! "
        "Bi không cần biết điều đó đâu. Mình nói chuyện khác nhé!",
    "default":
        "Thông tin riêng tư nên giữ an toàn nha! "
        "Bi không cần biết điều đó. Có gì khác muốn hỏi không?",
}


class PIIFilter:
    """
    Phát hiện thông tin cá nhân trong câu nói của bé và gentle-redirect.

    Hỗ trợ cả input có dấu lẫn không dấu (phổ biến trên điện thoại trẻ em).
    Chạy trên USER INPUT. Nếu phát hiện PII, trả về câu redirect để Bi nói.
    """

    def check(self, text: str) -> tuple[bool, str | None]:
        """
        Kiểm tra user input có chứa PII không.

        Args:
            text: Câu nói của bé (raw user input).

        Returns:
            (pii_found, response):
                pii_found=True  → response là câu Bi gentle-redirect
                pii_found=False → response=None
        """
        if not text or not text.strip():
            return False, None

        for name, (p_orig, p_norm), response_key in _PII_PATTERNS:
            if _search_dual(text, p_orig, p_norm):
                response = _RESPONSES.get(response_key, _RESPONSES["default"])
                logger.info("[PII] Detected type=%s — redirecting gently", name)
                return True, response

        return False, None

    def scan_details(self, text: str) -> list[str]:
        """Trả về tất cả PII types tìm thấy (dùng cho test/debug)."""
        found = []
        for name, (p_orig, p_norm), _ in _PII_PATTERNS:
            if _search_dual(text, p_orig, p_norm):
                found.append(name)
        return found


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    pf = PIIFilter()
    cases = [
        ("So me con la 0912345678 nha Bi", True),     # no diacritics
        ("Số mẹ con là 0912345678 nha Bi", True),      # with diacritics
        ("Con học lớp 3 rất vui", False),
        ("Email của mẹ là me@gmail.com", True),
        ("Nha con o so 12 duong Le Van Sy", True),     # no diacritics
        ("Nhà con ở số 12 đường Lê Văn Sỹ", True),   # with diacritics
        ("Con hoc truong Tieu Hoc ABC", True),          # no diacritics
        ("Con học trường Tiểu Học ABC", True),          # with diacritics
        ("Mat khau may tinh la 12345", True),           # no diacritics
        ("Mật khẩu máy tính là 12345", True),          # with diacritics
        ("Hôm nay trời đẹp quá Bi ơi", False),
        ("So tai khoan ngan hang la 123456789", True),  # no diacritics
    ]
    print("=" * 55)
    print("  TEST pii_filter.py")
    print("=" * 55)
    all_pass = True
    for text, expect in cases:
        found, resp = pf.check(text)
        status = "PASS" if found == expect else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  {status}  [{'+' if found else '-'}] {text[:50]}")
    print()
    print("ALL PASS ✅" if all_pass else "SOME TESTS FAILED ❌")
