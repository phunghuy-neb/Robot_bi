"""
main.py — Robot Bi: Vòng Lặp Điều Phối Trung Tâm
=================================================
Luồng hoạt động:
  1. Khởi tạo BiAI (kết nối Ollama cục bộ).
  2. Phát lời chào → đặt cờ is_speaking = True.
  3. Vòng lặp chính:
       - is_speaking = True  → chờ 0.1s, lặp lại (KHÔNG nghe).
       - is_speaking = False → gọi listen_to_mic().
       - Có input → đặt is_speaking = True → gọi bi.chat() → speak() → callback reset cờ.
  4. Ctrl+C → tắt gracefully.

Nguyên tắc cốt lõi:
  - Cờ is_speaking chống audio feedback loop (mic nghe lại tiếng loa).
  - speak() là non-blocking; callback _on_speak_done() reset cờ sau khi loa ngừng.
  - Mọi exception trong main loop đều được bắt và log, KHÔNG để crash.

Chạy:
    python main.py

Dừng:
    Ctrl+C
"""

import os
import sys
import time
import signal
import logging

from dotenv import load_dotenv

# Nạp biến môi trường trước khi import các module khác
load_dotenv()

# ── Cấu hình logging toàn cục ────────────────────────────────────────────────
# Gọi basicConfig TRƯỚC khi import core_ai và voice_io
# để tất cả logger con kế thừa đúng cấu hình.
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")
logger.info("Logging khởi tạo với cấp độ: %s", _log_level)

# ── Import module nội bộ ─────────────────────────────────────────────────────
from core_ai  import BiAI
from voice_io import listen_to_mic, speak


# ═══════════════════════════════════════════════════════════════════════════════
#  Trạng thái toàn cục
# ═══════════════════════════════════════════════════════════════════════════════

# Cờ chống feedback loop: True khi loa đang phát → micro bị khóa
is_speaking: bool = False

# Cờ kiểm soát vòng lặp chính: False khi người dùng nhấn Ctrl+C
_running: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
#  Các hàm trợ giúp
# ═══════════════════════════════════════════════════════════════════════════════

def _on_speak_done() -> None:
    """
    Callback được speak() gọi sau khi phát audio xong (hoặc lỗi).
    Reset cờ is_speaking để main loop tiếp tục nhận input.

    LƯU Ý: Hàm này chạy trong TTS-SpeakThread, KHÔNG phải main thread.
    Gán boolean là atomic trong CPython → thread-safe.
    """
    global is_speaking
    is_speaking = False
    logger.debug("🔓 is_speaking = False — micro sẵn sàng nghe.")


def _handle_shutdown(signum, frame) -> None:
    """Xử lý Ctrl+C (SIGINT): đặt cờ _running = False để thoát gracefully."""
    global _running
    print("\n\n👋 Bi đang tắt... Hẹn gặp lại bạn nhé!")
    logger.info("Nhận SIGINT — đang tắt vòng lặp chính...")
    _running = False


# ═══════════════════════════════════════════════════════════════════════════════
#  Vòng lặp chính
# ═══════════════════════════════════════════════════════════════════════════════

def run_main_loop(bi: BiAI) -> None:
    """
    Vòng lặp điều phối trung tâm của robot Bi.

    Trạng thái:
        is_speaking=True  → đang phát âm → KHÔNG nghe → chờ 0.1s.
        is_speaking=False → sẵn sàng     → gọi listen_to_mic() → xử lý.

    Args:
        bi: Instance BiAI đã khởi tạo.
    """
    global is_speaking

    logger.info("🚀 Vòng lặp chính bắt đầu.")
    print("\n" + "═" * 58)
    print("  🤖  Robot Bi đã sẵn sàng!")
    print("  📢  Hãy nói gì đó để bắt đầu trò chuyện...")
    print(f"  🧠  Ollama model: {os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b')}")
    print(f"  👂  Whisper STT: {os.getenv('WHISPER_MODEL', 'tiny')} (offline)")
    print("  🛑  Nhấn Ctrl+C để thoát.")
    print("═" * 58 + "\n")

    # Lời chào mở đầu
    is_speaking = True
    speak(
        "Xin chào! Mình là Bi! Robot gia sư của bạn đây! Hôm nay bạn muốn học gì nào?",
        on_done_callback=_on_speak_done,
    )

    while _running:
        # ── Bước 1: Chờ nếu đang phát âm ────────────────────────────────────
        if is_speaking:
            time.sleep(0.1)
            continue

        # ── Bước 2: Lắng nghe (offline, faster-whisper) ───────────────────────
        try:
            user_input = listen_to_mic()
        except Exception as e:
            logger.error("Lỗi không mong đợi trong listen_to_mic(): %s: %s", type(e).__name__, e)
            time.sleep(0.5)
            continue

        # ── Bước 3a: Không có input → chờ rồi lặp lại ───────────────────────
        if not user_input:
            time.sleep(0.2)  # Tránh busy-loop khi im lặng
            continue

        # ── Bước 3b: Có input → bắt đầu xử lý ───────────────────────────────
        print(f'\n👦 Bạn: "{user_input}"')
        logger.info("Input nhận được: '%s'", user_input)

        # Khóa micro NGAY để tránh race condition
        is_speaking = True
        logger.debug("🔒 is_speaking = True — micro bị khóa.")

        # ── Bước 4: Gửi đến Ollama AI ────────────────────────────────────────
        logger.info("⏳ Đang gửi đến Ollama...")
        try:
            reply = bi.chat(user_input)
        except Exception as e:
            logger.error("Lỗi nghiêm trọng trong bi.chat(): %s: %s", type(e).__name__, e)
            is_speaking = False
            continue

        # ── Bước 5: In ra terminal và phát giọng nói ─────────────────────────
        print(f'\n🤖 Bi: "{reply}"\n')

        if reply:
            # Non-blocking; callback _on_speak_done sẽ reset is_speaking
            speak(reply, on_done_callback=_on_speak_done)
        else:
            # reply rỗng (không mong đợi) → unblock ngay lập tức
            logger.warning("bi.chat() trả về reply rỗng — reset is_speaking ngay.")
            _on_speak_done()

    logger.info("Vòng lặp chính đã kết thúc.")


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def _print_banner() -> None:
    """In banner khởi động ra terminal."""
    print(r"""
  ██████╗ ██╗
  ██╔══██╗██║
  ██████╔╝██║
  ██╔══██╗██║
  ██████╔╝██║
  ╚═════╝ ╚═╝  — Robot Gia Sư Mini (Ollama + Qwen 2.5 | 100% Offline)
    """)


if __name__ == "__main__":
    # ── Đăng ký handler Ctrl+C ────────────────────────────────────────────────
    signal.signal(signal.SIGINT, _handle_shutdown)

    _print_banner()

    # ── Khởi tạo AI Engine ────────────────────────────────────────────────────
    try:
        bi_ai = BiAI()
        logger.info(
            "BiAI khởi tạo thành công. Model: %s | Max history: 10 lượt.",
            os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
        )
    except RuntimeError as e:
        print(f"\n❌ Lỗi khởi động AI: {e}")
        print("\n📋 Hướng dẫn:")
        print("  1. Cài Ollama: https://ollama.com/download")
        print("  2. Chạy: ollama pull qwen2.5:1.5b")
        print("  3. Chạy: ollama serve  (trong terminal khác)")
        logger.critical("RuntimeError khi khởi tạo BiAI: %s", e)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Lỗi không mong đợi: {type(e).__name__}: {e}")
        logger.critical("Exception không mong đợi: %s: %s", type(e).__name__, e)
        sys.exit(1)

    # ── Chạy vòng lặp chính ───────────────────────────────────────────────────
    try:
        run_main_loop(bi_ai)
    except KeyboardInterrupt:
        print("\n👋 Bi đang tắt... Hẹn gặp lại bạn nhé!")
        logger.info("KeyboardInterrupt nhận được — thoát.")
    except Exception as e:
        logger.critical(
            "Lỗi nghiêm trọng không bắt được trong main loop: %s: %s",
            type(e).__name__, e,
        )
        sys.exit(1)
    finally:
        logger.info("✅ Robot Bi đã tắt an toàn.")
        print("\n✅ Robot Bi đã tắt an toàn.")
