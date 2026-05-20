"""
emotion_risk_detector.py — Robot Bi: Phát hiện rủi ro cảm xúc
==============================================================
Chạy trên USER INPUT. Phát hiện khi bé đang trong trạng thái cảm xúc
cần can thiệp đặc biệt.

Hỗ trợ cả input có dấu lẫn không dấu (phổ biến trên điện thoại trẻ em).

Cấp độ rủi ro:
  HIGH   — tự hại, bắt nạt nặng, người lạ nguy hiểm, sợ bạo lực
           → Bi phản hồi hỗ trợ + đề nghị nói chuyện với người lớn tin tưởng
           → Log safety event
           → OVERRIDE LLM hoàn toàn
  MEDIUM — buồn kéo dài, cô đơn, tự ti, stress học
           → Comfort nhẹ, follow-up
           → Log event (không override LLM)
  LOW    — buồn nhẹ, giận bạn, điểm kém
           → Empathy nhẹ (LLM tự handle qua system prompt)
           → Không log, không override
  NONE   — không có rủi ro cảm xúc đặc biệt

Nguyên tắc:
  - KHÔNG panic mode.
  - KHÔNG therapist mode.
  - Bi là bạn nhỏ, không phải chuyên gia tâm lý.
  - Luôn hướng bé về người lớn tin tưởng khi HIGH risk.
  - Giọng: ấm, quan tâm thật, không kịch tính.

Interface:
    rd = EmotionRiskDetector()
    result = rd.check(user_text)
    # result = {
    #   "level": "high"|"medium"|"low"|"none",
    #   "triggers": ["tên pattern đã match"],
    #   "response": "câu Bi nói" | None,
    #   "should_override": True|False,  # True chỉ khi HIGH
    #   "log_event": True|False,
    # }
"""

import re
import logging

from src.safety.vi_normalize import normalize_vi

logger = logging.getLogger(__name__)

RISK_NONE   = "none"
RISK_LOW    = "low"
RISK_MEDIUM = "medium"
RISK_HIGH   = "high"


def _compile_dual(pattern_str: str) -> tuple:
    p_orig = re.compile(pattern_str, re.IGNORECASE | re.UNICODE)
    p_norm = re.compile(normalize_vi(pattern_str), re.IGNORECASE)
    return p_orig, p_norm


def _search_dual(text: str, p_orig, p_norm) -> bool:
    return bool(p_orig.search(text) or p_norm.search(normalize_vi(text)))


# ── HIGH risk patterns ────────────────────────────────────────────────────────
_HIGH_PATTERNS = [
    # Tự hại / không muốn sống
    (
        "self_harm",
        _compile_dual(
            r'(?:muốn chết|muon chet|không muốn sống|khong muon song|'
            r'chán sống|chan song|tự làm đau|tu lam dau|'
            r'cắt tay mình|cat tay minh|ghét bản thân|ghet ban than|'
            r'chết đi cho xong|chet di cho xong|muốn biến mất mãi|'
            r'muon bien mat mai|không muốn tồn tại|khong muon ton tai|'
            r'tự tử|tu tu)'
        ),
    ),
    # Bị đánh / bạo lực gia đình hoặc học đường
    (
        "violence",
        _compile_dual(
            r'(?:bị đánh|bi danh|bố đánh con|bo danh con|'
            r'mẹ đánh con|me danh con|ba đánh con|ba danh con|'
            r'má đánh con|ma danh con|bị bắt nạt nặng|bi bat nat nang|'
            r'họ đánh con|ho danh con|đánh con đau|danh con dau|'
            r'bị ức hiếp|bi uc hiep|bị hành hạ|bi hanh ha|'
            r'bị tra tấn|bi tra tan|đánh con mỗi ngày|danh con moi ngay)'
        ),
    ),
    # Người lạ dụ dỗ / stranger danger
    (
        "stranger_danger",
        _compile_dual(
            r'(?:người lạ (?:cho|dụ|kêu|bảo|nói)|'
            r'nguoi la (?:cho|du|keu|bao|noi)|'
            r'không quen (?:cho|dụ|kêu|bảo)|'
            r'khong quen (?:cho|du|keu|bao)|'
            r'chú ấy bảo (?:đi|không nói|giữ bí mật)|'
            r'chu ay bao (?:di|khong noi|giu bi mat)|'
            r'anh ấy bảo (?:đi|không nói|giữ bí mật)|'
            r'anh ay bao (?:di|khong noi|giu bi mat)|'
            r'người đó (?:cho kẹo|dụ con|bảo đừng nói)|'
            r'nguoi do (?:cho keo|du con|bao dung noi)|'
            r'có người muốn (?:đưa|dẫn|đón) con|'
            r'co nguoi muon (?:dua|dan|don) con)'
        ),
    ),
    # Sợ bố mẹ / bạo lực gia đình
    (
        "family_violence",
        _compile_dual(
            r'(?:sợ bố đánh|so bo danh|sợ mẹ đánh|so me danh|'
            r'bố hay đánh|bo hay danh|mẹ hay đánh|me hay danh|'
            r'ba hay đánh|ba hay danh|má hay đánh|ma hay danh|'
            r'sợ về nhà|so ve nha|bị đánh ở nhà|bi danh o nha|'
            r'ở nhà bị đánh|o nha bi danh)'
        ),
    ),
    # Bị đe dọa
    (
        "threat",
        _compile_dual(
            r'(?:bị đe dọa|bi de doa|họ đe con|ho de con|'
            r'nếu không (?:làm|đưa) (?:thì|sẽ)|'
            r'neu khong (?:lam|dua) (?:thi|se)|'
            r'đe sẽ đánh|de se danh|bắt con phải|bat con phai)'
        ),
    ),
]

# ── MEDIUM risk patterns ──────────────────────────────────────────────────────
_MEDIUM_PATTERNS = [
    # Buồn kéo dài
    (
        "prolonged_sadness",
        _compile_dual(
            r'(?:buồn mãi|buon mai|luôn buồn|luon buon|'
            r'không vui được|khong vui duoc|ngày nào cũng buồn|'
            r'ngay nao cung buon|buồn hoài|buon hoai|'
            r'buồn cả tuần|buon ca tuan|không hết buồn|khong het buon)'
        ),
    ),
    # Cô đơn / không có bạn
    (
        "loneliness",
        _compile_dual(
            r'(?:không ai chơi|khong ai choi|không có bạn|khong co ban|'
            r'cô đơn lắm|co don lam|một mình mãi|mot minh mai|'
            r'không ai thích con|khong ai thich con|'
            r'bạn bè không cần con|ban be khong can con|'
            r'tất cả đều ghét con|tat ca deu ghet con)'
        ),
    ),
    # Tự ti nặng
    (
        "low_self_esteem",
        _compile_dual(
            r'(?:con kém lắm|con kem lam|con không giỏi gì hết|'
            r'con khong gioi gi het|con xấu xí|con xau xi|'
            r'con vô dụng|con vo dung|không ai cần con|'
            r'khong ai can con|con là đồ bỏ đi|con la do bo di|'
            r'con chẳng làm được gì|con chang lam duoc gi)'
        ),
    ),
    # Bắt nạt nhẹ hơn HIGH (không bạo lực vật lý)
    (
        "bullying",
        _compile_dual(
            r'(?:bị bắt nạt|bi bat nat|bạn hay chọc|ban hay choc|'
            r'bị trêu chọc mãi|bi treu choc mai|'
            r'không ai bảo vệ con|khong ai bao ve con|'
            r'bị cô lập|bi co lap|bị xa lánh|bi xa lanh)'
        ),
    ),
    # Stress học tập
    (
        "study_stress",
        _compile_dual(
            r'(?:học căng thẳng lắm|hoc cang thang lam|'
            r'stress vì học|stress vi hoc|'
            r'áp lực học quá|ap luc hoc qua|'
            r'học không nổi|hoc khong noi|'
            r'sắp thi rồi sợ lắm|sap thi roi so lam|'
            r'mệt vì học|met vi hoc)'
        ),
    ),
]

# ── LOW risk patterns ─────────────────────────────────────────────────────────
_LOW_PATTERNS = [
    # Buồn nhẹ
    (
        "mild_sadness",
        _compile_dual(
            r'(?:hơi buồn|hoi buon|buồn vì|buon vi|'
            r'buồn một chút|buon mot chut|'
            r'không vui lắm|khong vui lam|hơi chán|hoi chan)'
        ),
    ),
    # Giận bạn
    (
        "mild_anger",
        _compile_dual(
            r'(?:giận bạn|gian ban|tức bạn|tuc ban|'
            r'bạn không chơi với con|ban khong choi voi con|'
            r'bạn nói xấu con|ban noi xau con|'
            r'bạn không công bằng|ban khong cong bang)'
        ),
    ),
    # Điểm kém
    (
        "poor_grade",
        _compile_dual(
            r'(?:điểm kém|diem kem|điểm xấu|diem xau|'
            r'thi trượt|thi truot|không được điểm cao|'
            r'khong duoc diem cao|bị điểm thấp|bi diem thap)'
        ),
    ),
]

# ── Responses — giọng Bi ─────────────────────────────────────────────────────
_HIGH_RESPONSES = {
    "self_harm": (
        "Ôi bé ơi, Bi lo cho bé lắm khi nghe điều đó. "
        "Bé đang cảm thấy như thế nào vậy? "
        "Quan trọng nhất là bé cần nói chuyện với bố mẹ hoặc người lớn mà bé tin tưởng ngay nhé. "
        "Họ sẽ giúp bé được!"
    ),
    "violence": (
        "Ôi bé ơi, nghe vậy Bi xót lòng lắm. "
        "Bé không nên bị đối xử như vậy đâu. "
        "Hãy nói với bố mẹ, thầy cô, hoặc người lớn mà bé tin nhất ngay nhé — "
        "họ sẽ bảo vệ bé!"
    ),
    "stranger_danger": (
        "Bé ơi, điều đó nghe rất đáng lo! "
        "Người lạ mà bảo giữ bí mật hoặc đi theo thì bé không nên đi nhé. "
        "Hãy nói ngay với bố mẹ hoặc thầy cô — đây là việc quan trọng lắm đó!"
    ),
    "family_violence": (
        "Bé ơi, Bi nghe rồi. Bé không nên sợ như vậy. "
        "Hãy nói chuyện với người lớn mà bé tin tưởng — có thể là thầy cô, ông bà, "
        "hoặc bất kỳ người thân nào. Bé xứng đáng được an toàn!"
    ),
    "threat": (
        "Bé ơi, nghe như vậy Bi lo lắm. "
        "Đây là việc bé cần nói với bố mẹ hoặc thầy cô ngay nhé, "
        "đừng giữ trong lòng một mình!"
    ),
    "default": (
        "Bé ơi, Bi nghe rồi và lo cho bé lắm. "
        "Điều quan trọng nhất là bé hãy nói chuyện với bố mẹ hoặc người lớn mà bé tin tưởng ngay nhé. "
        "Họ sẽ giúp bé được!"
    ),
}

_MEDIUM_RESPONSES = {
    "prolonged_sadness": (
        "Ôi bé ơi, buồn mãi như vậy mệt lắm nhỉ. "
        "Bé có muốn kể cho Bi nghe không, buồn vì chuyện gì vậy?"
    ),
    "loneliness": (
        "Ôi bé ơi, Bi hiểu cảm giác đó. "
        "Bé kể cho Bi nghe chuyện gì đang xảy ra được không?"
    ),
    "low_self_esteem": (
        "Bé ơi, sao lại nói vậy! Bé giỏi hơn bé nghĩ nhiều lắm đó. "
        "Kể cho Bi nghe bé đang khó khăn gì nhé?"
    ),
    "bullying": (
        "Ôi bé ơi, nghe vậy Bi xót lòng. "
        "Bị bắt nạt rất khó chịu đúng không? Bé kể thêm cho Bi nghe đi."
    ),
    "study_stress": (
        "Ôi học nhiều quá cũng mệt thật nhỉ! "
        "Bé đang lo môn gì nhất vậy, Bi giúp được không?"
    ),
    "default": (
        "Ôi bé ơi, nghe vậy Bi lo cho bé. "
        "Bé kể thêm cho Bi nghe được không?"
    ),
}


class EmotionRiskDetector:
    """
    Phát hiện rủi ro cảm xúc trong câu nói của bé.

    Hỗ trợ cả input có dấu lẫn không dấu.
    HIGH risk: override LLM + log event.
    MEDIUM risk: supportive response hint + log event.
    LOW risk: pass through (LLM system prompt tự handle).
    """

    def check(self, text: str) -> dict:
        """
        Kiểm tra mức độ rủi ro cảm xúc trong user input.

        Args:
            text: Câu nói của bé (raw user input).

        Returns:
            dict với keys:
                level: "high"|"medium"|"low"|"none"
                triggers: list of trigger names
                response: câu Bi nói (str) hoặc None
                should_override: bool (True = skip LLM hoàn toàn)
                log_event: bool (True = ghi vào safety events)
        """
        if not text or not text.strip():
            return self._build_result(RISK_NONE, [], None, False, False)

        # Kiểm tra HIGH trước (ưu tiên cao nhất)
        for name, (p_orig, p_norm) in _HIGH_PATTERNS:
            if _search_dual(text, p_orig, p_norm):
                response = _HIGH_RESPONSES.get(name, _HIGH_RESPONSES["default"])
                logger.warning("[EmotionRisk] HIGH risk detected: trigger=%s", name)
                return self._build_result(RISK_HIGH, [name], response, True, True)

        # Kiểm tra MEDIUM
        medium_triggers = []
        for name, (p_orig, p_norm) in _MEDIUM_PATTERNS:
            if _search_dual(text, p_orig, p_norm):
                medium_triggers.append(name)

        if medium_triggers:
            primary = medium_triggers[0]
            response = _MEDIUM_RESPONSES.get(primary, _MEDIUM_RESPONSES["default"])
            logger.info("[EmotionRisk] MEDIUM risk detected: triggers=%s", medium_triggers)
            return self._build_result(RISK_MEDIUM, medium_triggers, response, False, True)

        # Kiểm tra LOW
        low_triggers = []
        for name, (p_orig, p_norm) in _LOW_PATTERNS:
            if _search_dual(text, p_orig, p_norm):
                low_triggers.append(name)

        if low_triggers:
            return self._build_result(RISK_LOW, low_triggers, None, False, False)

        return self._build_result(RISK_NONE, [], None, False, False)

    @staticmethod
    def _build_result(level, triggers, response, should_override, log_event):
        return {
            "level": level,
            "triggers": triggers,
            "response": response,
            "should_override": should_override,
            "log_event": log_event,
        }


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    rd = EmotionRiskDetector()
    cases = [
        # No diacritics (phổ biến trên điện thoại)
        ("Con muon chet cho xong", RISK_HIGH),
        ("nguoi la cho con keo va bao khong noi voi me", RISK_HIGH),
        ("bi bat nat o truong", RISK_MEDIUM),
        ("Khong ai choi voi con het", RISK_MEDIUM),
        ("con hoi buon vi ban khong cho choi", RISK_LOW),
        ("Diem kem hom nay", RISK_LOW),
        ("Hom nay hoc toan vui lam", RISK_NONE),
        ("Bo danh con moi ngay", RISK_HIGH),
        # With diacritics
        ("Con muốn chết cho xong", RISK_HIGH),
        ("Bố đánh con mỗi ngày", RISK_HIGH),
        ("Không ai chơi với con hết", RISK_MEDIUM),
    ]
    print("=" * 55)
    print("  TEST emotion_risk_detector.py")
    print("=" * 55)
    all_pass = True
    for text, expected_level in cases:
        result = rd.check(text)
        ok = result["level"] == expected_level
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  {status}  [{result['level']:6}] {text[:55]}")
    print()
    print("ALL PASS ✅" if all_pass else "SOME TESTS FAILED ❌")
