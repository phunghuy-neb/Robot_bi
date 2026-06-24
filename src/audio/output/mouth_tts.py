"""
mouth_tts.py — Robot Bi: Text-to-Speech
========================================
QUAN TRỌNG — Trạng thái offline:
  - edge-tts yêu cầu internet để generate audio (vi phạm HC-01, tạm thời chấp nhận)
  - Khi không có internet → fallback sang pyttsx3 (offline, giọng kém hơn)
  - Upgrade path: thay bằng Coqui TTS hoặc Piper TTS khi có đủ tài nguyên

Fallback priority:
  1. edge-tts (internet available) — chất lượng tốt nhất
  2. pyttsx3 (offline fallback) — chất lượng thấp hơn nhưng không crash

Interface:
    tts = MouthTTS()
    tts.speak(text)                         # Blocking — dùng cho test
    await tts._generate_audio(text, idx)    # Async — dùng trong streaming pipeline
"""

import asyncio
import logging
import os
import warnings

logger = logging.getLogger(__name__)

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

import edge_tts
import pygame


_AUDIO_BACKEND_ERRORS = (pygame.error, OSError, RuntimeError)

# Thư mục TẠM cho file audio chunk (M2): KHÔNG ghi vào CWD nữa (rác + xung đột khi
# chạy từ thư mục khác). Dùng temp-dir riêng; main._cleanup_chunks quét đúng dir này.
import tempfile as _tempfile

CHUNK_DIR = os.path.join(_tempfile.gettempdir(), "robot_bi_voice")
try:
    os.makedirs(CHUNK_DIR, exist_ok=True)
except OSError:
    CHUNK_DIR = _tempfile.gettempdir()


def _chunk_path(chunk_index: int, ext: str) -> str:
    return os.path.join(CHUNK_DIR, f"voice_chunk_{chunk_index}.{ext}")


def _tts_offline_only() -> bool:
    """True nếu cấu hình ép TTS chạy HOÀN TOÀN offline (pyttsx3), bỏ qua edge-tts.
    Bật bằng `TTS_OFFLINE=true` hoặc `TTS_ENGINE=pyttsx3|offline` trong .env.
    Đọc tại thời điểm gọi → đổi cấu hình + restart robot là có hiệu lực."""
    if os.getenv("TTS_OFFLINE", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return os.getenv("TTS_ENGINE", "").strip().lower() in {"pyttsx3", "offline"}


class MouthTTS:
    def __init__(self):
        self.voice = "vi-VN-HoaiMyNeural"
        self.temp_file = "temp_bi_voice.mp3"
        self.audio_disabled = False
        self._audio_disabled = False
        self.audio_init_error = None

        # Pre-init 44100Hz stereo — chuẩn cho edge-tts MP3
        # Phải gọi trước pygame.init() / mixer.init() để có hiệu lực
        try:
            pygame.mixer.pre_init(
                frequency=44100,
                size=-16,       # 16-bit signed
                channels=2,     # Stereo - standard MP3 output
                buffer=2048,    # ~46ms buffer
            )
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except _AUDIO_BACKEND_ERRORS as exc:
            self._disable_audio(exc, "init")

    def _disable_audio(self, exc, context: str):
        self.audio_disabled = True
        self._audio_disabled = True
        self.audio_init_error = exc
        logger.warning(
            "[Bi - Mieng] Audio backend unavailable during %s; playback disabled: %s",
            context,
            exc,
        )

    def _play_audio_file(self, audio_file: str):
        if self._audio_disabled:
            logger.warning("[Bi - Mieng] Audio backend unavailable; skipping playback.")
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        except _AUDIO_BACKEND_ERRORS as exc:
            self._disable_audio(exc, "playback")
        except Exception as exc:
            logger.error("[Bi - Mieng] Audio playback failed: %s", exc)

    async def _generate_audio(self, text, chunk_index=0):
        """
        Generate audio file từ text.

        Thử edge-tts tối đa 3 lần với delay tăng dần; nếu vẫn fail thì
        fallback sang pyttsx3 offline.

        Args:
            text: Chuỗi text cần chuyển thành audio.
            chunk_index: Index để tạo tên file unique tránh conflict.

        Returns:
            Đường dẫn file MP3/WAV đã generate, hoặc None nếu cả hai TTS đều fail.
        """
        # Chế độ offline-only: dùng thẳng pyttsx3, không gọi edge-tts (cần internet).
        if _tts_offline_only():
            return self._fallback_tts(text, chunk_index)
        filename = _chunk_path(chunk_index, "mp3")
        for attempt in range(3):
            try:
                if attempt > 0:
                    await asyncio.sleep(0.3 * attempt)  # retry delay: 0.3s, 0.6s
                communicate = edge_tts.Communicate(text, self.voice)
                await communicate.save(filename)
                return filename
            except Exception as e:
                if attempt == 2:  # Lần thử cuối fail → fallback
                    logger.warning("[Bi - Miệng] edge-tts fail sau 3 lần, dùng fallback...")
                    return self._fallback_tts(text, chunk_index)

    def _fallback_tts(self, text: str, chunk_index: int):
        """
        Fallback TTS offline dùng pyttsx3.

        Dùng khi edge-tts không khả dụng (mất internet).
        Chất lượng giọng kém hơn edge-tts nhưng hoạt động hoàn toàn offline.

        Args:
            text: Chuỗi text cần chuyển thành audio.
            chunk_index: Index để tạo tên file unique.

        Returns:
            Đường dẫn file audio đã generate, hoặc None nếu pyttsx3 cũng fail.
        """
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            # Thử set giọng tiếng Việt nếu có
            voices = engine.getProperty('voices')
            for v in voices:
                if 'vietnamese' in v.name.lower() or 'vi' in v.id.lower():
                    engine.setProperty('voice', v.id)
                    break
            filename = _chunk_path(chunk_index, "wav")
            engine.save_to_file(text, filename)
            engine.runAndWait()
            return filename
        except Exception as e2:
            logger.error("[Bi - Miệng] Fallback TTS cũng lỗi: %s", e2)
            return None

    def speak(self, text):
        """Blocking TTS — dùng cho test độc lập."""
        logger.debug("[Bi - Miệng] Đang nói text_len=%d", len(text or ""))
        if self._audio_disabled:
            logger.warning("[Bi - Mieng] Audio backend unavailable; skipping TTS playback.")
            return

        audio_file = asyncio.run(self._generate_audio(text, chunk_index=0))
        if audio_file is None:
            logger.warning("[Bi - Miệng] Không thể generate audio.")
            return
        try:
            self._play_audio_file(audio_file)
        finally:
            try:
                os.remove(audio_file)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    tts = MouthTTS()
    tts.speak("Xin chào, mình là Bi. Rất vui được gặp bạn!")
