"""
voice_io.py — Robot Bi: Pipeline Giọng Nói (STT + TTS)
=======================================================
Chức năng:
  - STT (Nghe): sounddevice InputStream streaming → faster-whisper (OFFLINE).
  - TTS (Nói):  gTTS tạo MP3 → pygame phát âm (non-blocking thread).
  - Interrupt: Người dùng nói khi AI đang phát → TTS dừng ngay.
  - Semantic Completeness: Phân biệt im lặng "suy nghĩ" vs "nói xong".

Ràng buộc phần cứng:
  - faster-whisper chạy trên device='cpu', compute_type='int8'.
  - Tối ưu cho Intel Core i5 + 16GB RAM.

Xử lý lỗi:
  - Micro lỗi / không ghi được → trả None.
  - Whisper lỗi nhận dạng → trả None.
  - gTTS lỗi mạng → log, gọi callback, không crash.

Test độc lập:
    python voice_io.py
"""

import os
import logging
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from dotenv import load_dotenv

load_dotenv()

# ── Cấu hình logging ──────────────────────────────────────────────────────────
logger = logging.getLogger("voice_io")

# ── Cấu hình STT từ .env ──────────────────────────────────────────────────────
_WHISPER_MODEL      = os.getenv("WHISPER_MODEL", "small")
_WHISPER_LANGUAGE   = os.getenv("WHISPER_LANGUAGE", "vi")
_SAMPLE_RATE        = 16000  # Whisper yêu cầu 16kHz
_STT_MAX_SECONDS    = int(os.getenv("STT_MAX_SECONDS", "20"))
_VAD_SPEECH_THRESH  = float(os.getenv("VAD_SPEECH_THRESH", "0.015"))
_VAD_SILENCE_THRESH = float(os.getenv("VAD_SILENCE_THRESH", "0.008"))
_INTERRUPT_THRESH   = float(os.getenv("INTERRUPT_THRESH", "0.03"))
_SEMANTIC_MAX_RETRY = int(os.getenv("SEMANTIC_MAX_RETRY", "3"))

# ── Thư mục file âm thanh tạm ─────────────────────────────────────────────────
_TEMP_DIR = Path(tempfile.gettempdir())

# ── Interrupt event (module-level, UPGRADE 2) ─────────────────────────────────
_stop_speaking_event = threading.Event()


# ═══════════════════════════════════════════════════════════════════════════════
#  Import các thư viện tùy chọn (graceful degradation)
# ═══════════════════════════════════════════════════════════════════════════════

# ── sounddevice (ghi âm) ──────────────────────────────────────────────────────
try:
    import sounddevice as sd
    import soundfile as sf
    _SD_AVAILABLE = True
    logger.debug("sounddevice + soundfile import thành công.")
except ImportError:
    logger.critical("Thiếu 'sounddevice' hoặc 'soundfile'. Chạy: pip install sounddevice soundfile")
    _SD_AVAILABLE = False

# ── faster-whisper (STT offline) ──────────────────────────────────────────────
try:
    from faster_whisper import WhisperModel
    _whisper_model: Optional[WhisperModel] = None  # Lazy load lần đầu dùng
    _WHISPER_AVAILABLE = True
    logger.debug("faster-whisper import thành công.")
except ImportError:
    logger.critical("Thiếu 'faster-whisper'. Chạy: pip install faster-whisper")
    _WHISPER_AVAILABLE = False

# ── gTTS (TTS) ────────────────────────────────────────────────────────────────
try:
    from gtts import gTTS
    _GTTS_AVAILABLE = True
    logger.debug("gTTS import thành công.")
except ImportError:
    logger.critical("Thiếu 'gTTS'. Chạy: pip install gTTS")
    _GTTS_AVAILABLE = False

# ── pygame (phát âm thanh) ────────────────────────────────────────────────────
try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    _PYGAME_AVAILABLE = True
    logger.info("pygame.mixer khởi tạo thành công.")
except Exception as e:
    logger.critical("Không khởi tạo được pygame.mixer: %s — TTS bị vô hiệu hóa.", e)
    _PYGAME_AVAILABLE = False

# ── ollama (semantic check) ────────────────────────────────────────────────────
try:
    import ollama as _ollama_lib
    _OLLAMA_AVAILABLE = True
    logger.debug("ollama import thành công.")
except ImportError:
    logger.warning("Thiếu 'ollama' — semantic check sẽ mặc định True.")
    _OLLAMA_AVAILABLE = False

_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")


# ═══════════════════════════════════════════════════════════════════════════════
#  STT — Speech-to-Text (Nghe offline với faster-whisper)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_whisper_model() -> Optional["WhisperModel"]:
    """
    Lazy loader cho WhisperModel — chỉ tải model lần đầu tiên được gọi.
    Tái sử dụng instance cho các lần sau để tiết kiệm RAM và thời gian.
    """
    global _whisper_model
    if not _WHISPER_AVAILABLE:
        return None
    if _whisper_model is None:
        logger.info(
            "⏳ Đang tải Whisper model '%s' (lần đầu, có thể mất 10-30 giây)...",
            _WHISPER_MODEL,
        )
        _whisper_model = WhisperModel(
            _WHISPER_MODEL,
            device="cpu",
            compute_type="int8",
        )
        logger.info("✅ Whisper model '%s' đã sẵn sàng.", _WHISPER_MODEL)
    return _whisper_model


def _is_sentence_complete(text: str) -> bool:
    """
    Kiểm tra 2 tầng xem câu đã hoàn chỉnh ngữ nghĩa chưa.

    Tầng 1: Filler/Incomplete filter (tức thì, không cần AI).
    Tầng 2: Ollama semantic check (timeout 2s).

    Returns True nếu câu hoàn chỉnh, False nếu chưa.
    """
    # Filler đơn và cụm từ chưa hoàn chỉnh
    _MULTI_WORD_FILLERS = ["ý tôi", "ý là", "tức là", "nghĩa là"]
    _SINGLE_WORD_FILLERS = {"à", "ừ", "ừm", "ờ", "ơ", "thì", "là", "mà"}
    _INCOMPLETE_ENDINGS  = {
        "là", "thì", "mà", "và", "hoặc", "nhưng",
        "vì", "nếu", "để", "với", "cho", "của",
    }

    # ── Tầng 1: Filler / Incomplete Filter ────────────────────────────────────
    text_lower = text.lower().strip()
    if not text_lower:
        return False

    # Loại bỏ cụm filler nhiều từ trước
    text_clean = text_lower
    for phrase in _MULTI_WORD_FILLERS:
        text_clean = text_clean.replace(phrase, " ")

    words = text_clean.split()
    if not words:
        logger.debug("Tầng 1: Sau khi loại filler cụm → rỗng → False")
        return False

    # Kiểm tra kết thúc bằng từ chưa hoàn chỉnh (trên raw words trước khi lọc filler đơn)
    if words[-1] in _INCOMPLETE_ENDINGS:
        logger.debug("Tầng 1: Kết thúc bằng '%s' → False", words[-1])
        return False

    # Đếm từ có nghĩa (loại filler đơn)
    meaningful = [w for w in words if w not in _SINGLE_WORD_FILLERS]
    if len(meaningful) < 3:
        logger.debug("Tầng 1: Chỉ %d từ có nghĩa < 3 → False", len(meaningful))
        return False

    # ── Tầng 2: Ollama Semantic Check ─────────────────────────────────────────
    if not _OLLAMA_AVAILABLE:
        return True  # Mặc định True nếu không có Ollama

    result_holder = [True]  # Default True — ưu tiên không làm người dùng chờ
    done_flag = threading.Event()

    def _ollama_call() -> None:
        try:
            response = _ollama_lib.chat(
                model=_OLLAMA_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Trả lời chỉ 'YES' hoặc 'NO'. Không giải thích.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Câu sau đây có phải là một ý hoàn chỉnh không "
                            "(dù ngắn hay dài, miễn là người nghe hiểu được ý định):\n"
                            f"'{text}'\n"
                            "Chỉ trả lời YES hoặc NO."
                        ),
                    },
                ],
            )
            answer = response["message"]["content"].strip().upper()
            if "NO" in answer:
                result_holder[0] = False
            elif "YES" in answer:
                result_holder[0] = True
            # else: giữ nguyên default True
        except Exception as e:
            logger.debug("Ollama semantic check lỗi: %s — mặc định True", e)
            result_holder[0] = True
        finally:
            done_flag.set()

    t = threading.Thread(target=_ollama_call, daemon=True, name="OllamaSemanticCheck")
    t.start()
    done_flag.wait(timeout=2.0)  # Timeout 2 giây

    logger.debug("Tầng 2 Ollama: %s", "True" if result_holder[0] else "False")
    return result_holder[0]


def _quick_transcribe(audio_array: np.ndarray) -> str:
    """
    Transcribe nhanh audio buffer để kiểm tra ngữ nghĩa.
    Dùng beam_size=1 và cùng model instance — KHÔNG load lại model.
    """
    model = _get_whisper_model()
    if model is None or len(audio_array) < int(_SAMPLE_RATE * 0.3):
        return ""

    tmp_wav: Optional[Path] = None
    try:
        tmp_fd, tmp_str = tempfile.mkstemp(suffix=".wav", dir=_TEMP_DIR)
        os.close(tmp_fd)
        tmp_wav = Path(tmp_str)
        sf.write(str(tmp_wav), audio_array, _SAMPLE_RATE, subtype="PCM_16")

        segments, _ = model.transcribe(
            str(tmp_wav),
            language=_WHISPER_LANGUAGE,
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
    except Exception as e:
        logger.debug("Quick transcribe lỗi: %s", e)
        return ""
    finally:
        if tmp_wav and tmp_wav.exists():
            try:
                tmp_wav.unlink()
            except OSError:
                pass


def listen_to_mic() -> Optional[str]:
    """
    Ghi âm streaming từ microphone với VAD endpointing và semantic completeness.

    Luồng hoạt động:
      1. Dùng sd.InputStream đọc chunk 50ms liên tục.
      2. Pre-buffer 300ms để không mất phần đầu câu.
      3. Sau 800ms im lặng: transcribe thử + kiểm tra ngữ nghĩa (UPGRADE 4).
      4. Nếu hoàn chỉnh → transcribe chính thức và return.
      5. Nếu chưa → reset im lặng, tiếp tục nghe (tối đa SEMANTIC_MAX_RETRY lần).
      6. Giới hạn tối đa STT_MAX_SECONDS giây.

    Returns:
        str nếu nhận dạng thành công, None trong mọi trường hợp lỗi.
    """
    if not _SD_AVAILABLE:
        logger.error("sounddevice chưa cài — STT không hoạt động.")
        return None
    if not _WHISPER_AVAILABLE:
        logger.error("faster-whisper chưa cài — STT không hoạt động.")
        return None

    model = _get_whisper_model()
    if model is None:
        return None

    CHUNK_MS        = 50
    CHUNK_FRAMES    = int(_SAMPLE_RATE * CHUNK_MS / 1000)     # 800 frames
    PRE_BUF_CHUNKS  = int(300 / CHUNK_MS)                     # 6 chunks = 300ms
    SILENCE_LIMIT   = int(800 / CHUNK_MS)                     # 16 chunks = 800ms
    MAX_CHUNKS      = int(_STT_MAX_SECONDS * 1000 / CHUNK_MS) # 400 chunks = 20s

    pre_buffer: deque = deque(maxlen=PRE_BUF_CHUNKS)
    audio_buffer: list = []
    silent_chunks   = 0
    speech_started  = False
    semantic_retry  = 0
    tmp_wav: Optional[Path] = None

    logger.info("🎤 Đang lắng nghe... (tối đa %ds, nói để bắt đầu)", _STT_MAX_SECONDS)

    try:
        stream = sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_FRAMES,
        )
        stream.start()

        try:
            for _ in range(MAX_CHUNKS):
                chunk, overflowed = stream.read(CHUNK_FRAMES)
                if overflowed:
                    logger.debug("InputStream overflow — bỏ qua chunk.")

                rms = float(np.sqrt(np.mean(chunk ** 2)))

                if not speech_started:
                    pre_buffer.append(chunk.copy())
                    if rms >= _VAD_SPEECH_THRESH:
                        speech_started = True
                        audio_buffer.extend(list(pre_buffer))
                        logger.debug("🗣️ Phát hiện tiếng nói, bắt đầu ghi...")
                    continue

                # Speech đã bắt đầu — ghi chunk vào buffer
                audio_buffer.append(chunk.copy())

                if rms < _VAD_SILENCE_THRESH:
                    silent_chunks += 1
                else:
                    silent_chunks = 0

                if silent_chunks >= SILENCE_LIMIT:
                    # 800ms im lặng — transcribe thử + kiểm tra ngữ nghĩa
                    audio_array = np.concatenate(audio_buffer).flatten()
                    partial_text = _quick_transcribe(audio_array)
                    logger.debug("Quick transcribe: '%s'", partial_text)

                    if _is_sentence_complete(partial_text):
                        logger.debug("✅ Câu hoàn chỉnh — dừng ghi âm.")
                        break

                    semantic_retry += 1
                    logger.info(
                        "⏳ Câu chưa hoàn chỉnh — tiếp tục nghe... (retry %d/%d)",
                        semantic_retry, _SEMANTIC_MAX_RETRY,
                    )
                    silent_chunks = 0

                    if semantic_retry >= _SEMANTIC_MAX_RETRY:
                        logger.info("⚠️ Đạt giới hạn retry — dừng và dùng text hiện tại.")
                        break
        finally:
            stream.stop()
            stream.close()

        if not audio_buffer:
            logger.info("🔇 Không phát hiện âm thanh — bỏ qua.")
            return None

        audio_array = np.concatenate(audio_buffer).flatten()
        rms_total = float(np.sqrt(np.mean(audio_array ** 2)))
        if rms_total < 0.001:
            logger.info("🔇 RMS quá thấp — bỏ qua.")
            return None

        # ── Transcribe chính thức ────────────────────────────────────────────
        tmp_fd, tmp_str = tempfile.mkstemp(suffix=".wav", dir=_TEMP_DIR)
        os.close(tmp_fd)
        tmp_wav = Path(tmp_str)
        sf.write(str(tmp_wav), audio_array, _SAMPLE_RATE, subtype="PCM_16")

        logger.info("🔄 Đang nhận dạng giọng nói (Whisper '%s')...", _WHISPER_MODEL)
        segments, _ = model.transcribe(
            str(tmp_wav),
            language=_WHISPER_LANGUAGE,
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=2000),
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()

        if not text:
            logger.info("🔇 Whisper không nhận dạng được gì — bỏ qua.")
            return None

        logger.info("✅ Nhận dạng thành công: '%s'", text)
        return text

    except sd.PortAudioError as e:
        logger.error("🎙️ Lỗi thiết bị micro (PortAudio): %s", e)
        return None
    except Exception as e:
        logger.error("❌ Lỗi không mong đợi trong listen_to_mic(): %s: %s", type(e).__name__, e)
        return None
    finally:
        if tmp_wav and tmp_wav.exists():
            try:
                tmp_wav.unlink()
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
#  TTS — Text-to-Speech (Nói) với gTTS + pygame
# ═══════════════════════════════════════════════════════════════════════════════

def stop_speaking() -> None:
    """Ngắt TTS đang phát ngay lập tức (thread-safe, UPGRADE 2)."""
    _stop_speaking_event.set()


def _interrupt_monitor(playback_done: threading.Event) -> None:
    """
    Daemon thread: giám sát mic trong khi AI đang nói (UPGRADE 2).
    Nếu RMS > INTERRUPT_THRESH → gọi stop_speaking() → thoát.
    Thoát ngay khi playback_done được set.
    """
    if not _SD_AVAILABLE:
        return

    CHUNK_MS     = 50
    CHUNK_FRAMES = int(_SAMPLE_RATE * CHUNK_MS / 1000)

    try:
        stream = sd.InputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_FRAMES,
        )
        stream.start()
        try:
            while not playback_done.is_set():
                chunk, _ = stream.read(CHUNK_FRAMES)
                rms = float(np.sqrt(np.mean(chunk ** 2)))
                if rms > _INTERRUPT_THRESH:
                    logger.info("🛑 Interrupt: người dùng lên tiếng — dừng TTS.")
                    stop_speaking()
                    break
        finally:
            stream.stop()
            stream.close()
    except Exception as e:
        logger.debug("_interrupt_monitor lỗi: %s", e)


def speak(text: str, on_done_callback: Optional[Callable[[], None]] = None) -> None:
    """
    Chuyển văn bản thành giọng nói (gTTS) và phát qua loa bằng pygame.
    NON-BLOCKING. Hỗ trợ interrupt khi người dùng lên tiếng (UPGRADE 2).

    Args:
        text:             Chuỗi văn bản cần phát thành tiếng.
        on_done_callback: Hàm gọi lại sau khi phát xong (hoặc lỗi/bị ngắt).
    """
    if not text or not text.strip():
        logger.warning("speak() nhận text rỗng — bỏ qua.")
        if on_done_callback:
            on_done_callback()
        return

    # (a) Clear interrupt event TRƯỚC khi start TTS thread
    _stop_speaking_event.clear()

    # (b) Event báo hiệu playback đã xong — truyền vào cả worker và monitor
    playback_done = threading.Event()

    thread = threading.Thread(
        target=_speak_worker,
        args=(text.strip(), on_done_callback, playback_done),
        daemon=True,
        name="TTS-SpeakThread",
    )
    thread.start()

    # (c) Start interrupt monitor song song như daemon thread
    monitor_thread = threading.Thread(
        target=_interrupt_monitor,
        args=(playback_done,),
        daemon=True,
        name="TTS-InterruptMonitor",
    )
    monitor_thread.start()

    logger.debug("TTS thread đã khởi động: '%s...'", text[:40])


def _speak_worker(
    text: str,
    on_done_callback: Optional[Callable[[], None]],
    playback_done: threading.Event,
) -> None:
    """
    Worker thread: gTTS → lưu MP3 tạm → phát qua pygame → dọn dẹp → callback.
    Hỗ trợ interrupt qua _stop_speaking_event.
    Mọi lỗi đều được bắt; callback LUÔN được gọi để không treo main loop.
    """
    tmp_path: Optional[Path] = None

    try:
        if not _GTTS_AVAILABLE:
            logger.error("gTTS chưa cài — không thể phát âm thanh.")
            return
        if not _PYGAME_AVAILABLE:
            logger.error("pygame chưa khởi tạo — không thể phát âm thanh.")
            return

        # ── Bước 1: Tạo file MP3 tạm ────────────────────────────────────────
        tmp_fd, tmp_str = tempfile.mkstemp(suffix=".mp3", dir=_TEMP_DIR)
        os.close(tmp_fd)
        tmp_path = Path(tmp_str)

        logger.info(
            "🔊 Đang tổng hợp giọng nói: '%s%s'",
            text[:60], "..." if len(text) > 60 else "",
        )

        # ── Bước 2: Gọi gTTS → lưu MP3 ─────────────────────────────────────
        tts = gTTS(text=text, lang="vi", slow=False)
        tts.save(str(tmp_path))

        # ── Bước 3: Phát qua pygame ─────────────────────────────────────────
        pygame.mixer.music.load(str(tmp_path))
        pygame.mixer.music.play()

        # Polling với interrupt check (UPGRADE 2)
        while pygame.mixer.music.get_busy():
            if _stop_speaking_event.is_set():
                pygame.mixer.music.stop()
                logger.info("🛑 TTS bị ngắt theo yêu cầu.")
                break
            time.sleep(0.05)

        logger.info("✅ Phát âm thanh hoàn thành.")

    except Exception as e:
        logger.error("❌ Lỗi trong _speak_worker: %s: %s", type(e).__name__, e)

    finally:
        # playback_done.set() trong finally — đảm bảo interrupt monitor thoát
        playback_done.set()

        # Giải phóng file để Windows không khóa
        if _PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass

        if tmp_path and tmp_path.exists():
            time.sleep(0.15)  # Đợi OS giải phóng handle
            try:
                tmp_path.unlink()
            except OSError:
                pass

        # Callback LUÔN được gọi — kể cả khi có lỗi hoặc bị ngắt
        if on_done_callback:
            try:
                on_done_callback()
            except Exception as e:
                logger.error("Lỗi trong on_done_callback: %s", e)


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
    print("  TEST voice_io.py — faster-whisper + gTTS + pygame")
    print("=" * 60)

    # ── Test TTS ──────────────────────────────────────────────────────────────
    done_event = threading.Event()

    def _on_tts_done() -> None:
        print("  ✅ TTS Callback — phát âm xong!\n")
        done_event.set()

    test_text = (
        "Xin chào! Mình là Bi, robot gia sư của bạn đây! "
        "Hôm nay bạn muốn học gì nào?"
    )
    print(f"\n[TTS] Đang phát: \"{test_text}\"\n")
    speak(test_text, on_done_callback=_on_tts_done)

    if not done_event.wait(timeout=30):
        print("  ⚠️ TTS Timeout sau 30 giây.")
        sys.exit(1)

    # ── Test STT ──────────────────────────────────────────────────────────────
    print("  Nhấn Enter để thử STT (ghi âm streaming)...")
    input()

    print(f"\n[STT] 🎤 Đang lắng nghe (tối đa {_STT_MAX_SECONDS}s) — Hãy nói gì đó:")
    result = listen_to_mic()

    if result:
        print(f"\n  ✅ Nhận dạng: '{result}'")
    else:
        print("\n  ⚠️ Không nhận dạng được hoặc có lỗi.")

    print("\n  Test hoàn thành!")
