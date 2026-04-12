import edge_tts
import pygame
import asyncio
import os


class MouthTTS:
    def __init__(self):
        pygame.mixer.init()
        self.voice = "vi-VN-HoaiMyNeural"
        self.temp_file = "temp_bi_voice.mp3"

    async def _generate_audio(self, text):
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(self.temp_file)

    def speak(self, text):
        print(f"[Bi - Miệng] Đang nói: {text}")
        asyncio.run(self._generate_audio(text))
        pygame.mixer.music.load(self.temp_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        try:
            os.remove(self.temp_file)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    tts = MouthTTS()
    tts.speak("Xin chào, mình là Bi. Rất vui được gặp bạn!")
