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
import os

import edge_tts
import pygame


class MouthTTS:
    def __init__(self):
        pygame.mixer.init()
        self.voice = "vi-VN-HoaiMyNeural"
        self.temp_file = "temp_bi_voice.mp3"

    async def _generate_audio(self, text, chunk_index=0):
        """
        Generate audio file từ text.

        Thử edge-tts trước; nếu lỗi (mất internet hoặc API fail) thì
        fallback sang pyttsx3 offline.

        Args:
            text: Chuỗi text cần chuyển thành audio.
            chunk_index: Index để tạo tên file unique tránh conflict.

        Returns:
            Đường dẫn file MP3/WAV đã generate, hoặc None nếu cả hai TTS đều fail.
        """
        filename = f"voice_chunk_{chunk_index}.mp3"
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(filename)
            return filename
        except Exception as e:
            # Fallback: pyttsx3 offline nếu edge-tts fail (mất internet)
            print(f"[Bi - Miệng] edge-tts lỗi ({e}), dùng fallback offline...")
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
            filename = f"voice_chunk_{chunk_index}.mp3"
            engine.save_to_file(text, filename)
            engine.runAndWait()
            return filename
        except Exception as e2:
            print(f"[Bi - Miệng] Fallback TTS cũng lỗi: {e2}")
            return None

    def speak(self, text):
        """Blocking TTS — dùng cho test độc lập."""
        print(f"[Bi - Miệng] Đang nói: {text}")
        audio_file = asyncio.run(self._generate_audio(text, chunk_index=0))
        if audio_file is None:
            print("[Bi - Miệng] Không thể generate audio.")
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
