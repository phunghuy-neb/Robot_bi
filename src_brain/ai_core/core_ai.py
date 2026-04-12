"""
core_ai.py — Robot Bi: Não Bộ AI (Ollama + Qwen 2.5)
======================================================
Chức năng:
  - Giao tiếp với Ollama chạy 100% cục bộ (offline).
  - Duy trì lịch sử hội thoại theo cơ chế sliding window (tối đa 10 lượt).
  - Định hình tính cách "Bi" qua System Prompt tiếng Việt.

Xử lý lỗi:
  - Ollama chưa chạy hoặc model chưa tải → trả về thông báo tiếng Việt.
  - Mọi exception đều được bắt → không bao giờ để crash main loop.

Test độc lập:
    python core_ai.py
"""

import os
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# ── Cấu hình logging ──────────────────────────────────────────────────────────
logger = logging.getLogger("core_ai")

# ── Cấu hình từ .env ──────────────────────────────────────────────────────────
_MODEL       = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
_MAX_HISTORY = 10  # Số lượt hội thoại tối đa giữ trong RAM (sliding window)

# ── System Prompt — Tính cách của Bi ─────────────────────────────────────────
_SYSTEM_PROMPT = """Bạn là Bi, một robot gia sư thông minh và gần gũi do sinh viên PTIT tạo ra. Bạn xưng là "Bi" và gọi người dùng là "bạn" hoặc "em".

TUYỆT ĐỐI TUÂN THỦ 3 QUY TẮC SAU:
1. LUÔN viết thành một đoạn văn xuôi duy nhất, KHÔNG BAO GIỜ xuống dòng, KHÔNG BAO GIỜ dùng gạch đầu dòng hay số thứ tự.
2. Tối đa 3 đến 4 câu. Mọi kiến thức phức tạp đều BẮT BUỘC phải kèm theo ví dụ so sánh bằng những đồ vật quen thuộc hàng ngày. Dùng các từ đệm tự nhiên (Dạ, Vâng, Nhé).
3. Nếu câu hỏi quá chuyên sâu hoặc Bi không chắc chắn, CHỈ ĐƯỢC PHÉP nói: "Bi chưa có dữ liệu về phần này."

DƯỚI ĐÂY LÀ CÁC VÍ DỤ BẮT BUỘC BẠN PHẢI BẮT CHƯỚC CÁCH TRẢ LỜI:
Người: Tại sao bầu trời có màu xanh thế Bi?
Bi: Dạ, ánh sáng mặt trời có đủ 7 màu cầu vồng, nhưng khi chiếu xuống Trái Đất thì màu xanh bị các hạt không khí cản lại và bắn tung tóe ra khắp nơi. Nó giống hệt như khi bạn xịt vòi nước mạnh vào bức tường và những tia nước li ti văng ra vậy đó. Mắt chúng ta hứng trọn những tia sáng xanh văng ra này nên nhìn thấy bầu trời màu xanh nhé!

Người: Liệt kê cho tôi 5 hành tinh trong hệ mặt trời.
Bi: Vâng, 5 hành tinh trong hệ Mặt Trời bao gồm Sao Thủy, Sao Kim, Trái Đất, Sao Hỏa và Sao Mộc nhé. Bạn thích hành tinh nào nhất?

Người: Giải thích thuật toán Transformer attention mechanism trong deep learning.
Bi: Dạ, Bi chưa có dữ liệu về phần này. Bạn có câu hỏi nào khác không?
"""

# ── Import ollama ─────────────────────────────────────────────────────────────
try:
    import ollama as _ollama
    _OLLAMA_AVAILABLE = True
    logger.debug("ollama import thành công.")
except ImportError:
    logger.critical("Thiếu thư viện 'ollama'. Chạy: pip install ollama")
    _OLLAMA_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
#  Class BiAI — Não bộ trung tâm
# ═══════════════════════════════════════════════════════════════════════════════

class BiAI:
    """
    Não bộ AI của Robot Bi, sử dụng Ollama (Qwen 2.5) chạy hoàn toàn offline.

    Attributes:
        history: Danh sách các lượt hội thoại gần nhất (sliding window).
        total_turns: Tổng số lượt đã hội thoại kể từ khi khởi động.
    """

    def __init__(self) -> None:
        if not _OLLAMA_AVAILABLE:
            raise RuntimeError(
                "Thư viện 'ollama' chưa được cài đặt. "
                "Chạy: pip install ollama"
            )

        self.history: list[dict] = []
        self.total_turns: int = 0
        logger.info(
            "BiAI khởi tạo — model: '%s' | max history: %d lượt.",
            _MODEL, _MAX_HISTORY,
        )

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _trim_history(self) -> None:
        """
        Áp dụng sliding window: chỉ giữ lại _MAX_HISTORY lượt gần nhất.
        Mỗi lượt = 1 message user + 1 message assistant = 2 phần tử.
        """
        max_messages = _MAX_HISTORY * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]
            logger.debug("Sliding window: cắt history còn %d messages.", max_messages)

    def _build_messages(self, user_input: str) -> list[dict]:
        """Xây dựng danh sách messages gửi cho Ollama, bao gồm system prompt."""
        messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_input})
        return messages

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(self, user_input: str) -> str:
        """
        Gửi câu hỏi của người dùng, nhận câu trả lời từ Ollama.

        Luồng hoạt động:
          1. Xây dựng messages (system + history + user input mới).
          2. Gọi ollama.chat() với model đã cấu hình.
          3. Lưu cặp (user, assistant) vào history.
          4. Áp dụng sliding window.
          5. Trả về chuỗi phản hồi thuần túy.

        Args:
            user_input: Văn bản câu hỏi của người dùng.

        Returns:
            Chuỗi câu trả lời của Bi, hoặc thông báo lỗi tiếng Việt.
        """
        if not user_input or not user_input.strip():
            return "Bạn vừa nói gì đó mình chưa nghe rõ, bạn nói lại được không?"

        user_input = user_input.strip()
        logger.info("🧠 Bi đang suy nghĩ: '%s'", user_input)

        try:
            messages = self._build_messages(user_input)
            response = _ollama.chat(model=_MODEL, messages=messages)

            reply: str = response["message"]["content"].strip()

            # Cập nhật lịch sử hội thoại
            self.history.append({"role": "user",      "content": user_input})
            self.history.append({"role": "assistant", "content": reply})
            self._trim_history()

            self.total_turns += 1
            logger.info("🤖 Bi trả lời (lượt %d): '%s'", self.total_turns, reply[:80])
            return reply

        except _ollama.ResponseError as e:
            error_msg = (
                f"Xin lỗi, model '{_MODEL}' chưa được tải về. "
                f"Hãy chạy lệnh: ollama pull {_MODEL}"
            )
            logger.error("Ollama ResponseError: %s", e)
            return error_msg

        except ConnectionRefusedError:
            error_msg = (
                "Xin lỗi, không kết nối được với Ollama. "
                "Hãy mở terminal và chạy: ollama serve"
            )
            logger.error("Ollama chưa chạy — ConnectionRefusedError.")
            return error_msg

        except Exception as e:
            error_msg = "Xin lỗi, não bộ của mình đang gặp sự cố nhỏ. Bạn thử hỏi lại nhé!"
            logger.error("Lỗi không mong đợi trong chat(): %s: %s", type(e).__name__, e)
            return error_msg

    def reset_history(self) -> None:
        """Xóa toàn bộ lịch sử hội thoại trong RAM (giữ nguyên total_turns)."""
        self.history.clear()
        logger.info("Lịch sử hội thoại đã được reset.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Test độc lập
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    print("=" * 60)
    print("  TEST core_ai.py — Ollama + Qwen 2.5")
    print("=" * 60)
    print(f"  Model: {_MODEL}")
    print(f"  Max history: {_MAX_HISTORY} lượt\n")

    try:
        bi = BiAI()
    except RuntimeError as e:
        print(f"\n❌ {e}")
        sys.exit(1)

    test_questions = [
        "Xin chào Bi!",
        "Trái đất quay quanh mặt trời mất bao lâu?",
        "Tại sao bầu trời màu xanh?",
        "Tóm tắt lại những gì chúng ta vừa nói.",  # Test memory
    ]

    for q in test_questions:
        print(f"\n👦 Bạn: {q}")
        answer = bi.chat(q)
        print(f"🤖 Bi: {answer}")

    print(f"\n✅ Test hoàn thành — Tổng {bi.total_turns} lượt hội thoại.")