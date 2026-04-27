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

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

import edge_tts
import pygame


class MouthTTS:
    def __init__(self):
        # Pre-init 44100Hz stereo — chuẩn cho edge-tts MP3
        # Phải gọi trước pygame.init() / mixer.init() để có hiệu lực
        pygame.mixer.pre_init(
            frequency=44100,
            size=-16,       # 16-bit signed
            channels=2,     # Stereo — chuẩn cho MP3
            buffer=2048,    # ~46ms buffer, tránh underrun
        )
        pygame.mixer.init()
        self.voice = "vi-VN-HoaiMyNeural"
        self.temp_file = "temp_bi_voice.mp3"

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
        filename = f"voice_chunk_{chunk_index}.mp3"
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
            filename = f"voice_chunk_{chunk_index}.wav"
            engine.save_to_file(text, filename)
            engine.runAndWait()
            return filename
        except Exception as e2:
            logger.error("[Bi - Miệng] Fallback TTS cũng lỗi: %s", e2)
            return None

    def speak(self, text):
        """Blocking TTS — dùng cho test độc lập."""
        logger.info("[Bi - Miệng] Đang nói: %s", text)
        audio_file = asyncio.run(self._generate_audio(text, chunk_index=0))
        if audio_file is None:
            logger.warning("[Bi - Miệng] Không thể generate audio.")
            return
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        try:
            os.remove(audio_file)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    tts = MouthTTS()
    tts.speak("Xin chào, mình là Bi. Rất vui được gặp bạn!")
