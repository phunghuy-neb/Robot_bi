import edge_tts
import pygame
import asyncio
import os


class MouthTTS:
    def __init__(self):
        pygame.mixer.init()
        self.voice = "vi-VN-HoaiMyNeural"
        self.temp_file = "temp_bi_voice.mp3"

    async def _generate_audio(self, text, chunk_index=0):
        communicate = edge_tts.Communicate(text, self.voice)
        filename = f"voice_chunk_{chunk_index}.mp3"
        await communicate.save(filename)
        return filename

    def speak(self, text):
        print(f"[Bi - Miệng] Đang nói: {text}")
        audio_file = asyncio.run(self._generate_audio(text, chunk_index=0))
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
