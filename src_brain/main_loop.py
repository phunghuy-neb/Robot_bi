import sys
import os
import threading
import queue
import glob
import asyncio
import re

# Fix encoding cho console Windows (cp1252 không hỗ trợ tiếng Việt)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import pygame

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src_brain.senses.ear_stt import EarSTT
from src_brain.senses.mouth_tts import MouthTTS
from src_brain.ai_core.core_ai import BiAI


class RobotBiApp:
    def __init__(self):
        self.ear = EarSTT()
        self.mouth = MouthTTS()
        self.brain = BiAI()
        self.audio_queue = queue.Queue()
        self._chunk_counter = 0
        self._loop = asyncio.new_event_loop()

        # Daemon thread xử lý audio queue: play → unload → xóa file
        self._worker_thread = threading.Thread(
            target=self._audio_worker_loop, daemon=True
        )
        self._worker_thread.start()

        print("[Hệ thống] Robot Bi đã khởi động và sẵn sàng!")

    def _audio_worker_loop(self):
        """Worker thread: nhận audio file từ queue, phát, unload, xóa."""
        while True:
            item = self.audio_queue.get()
            if item is None:
                self.audio_queue.task_done()
                break
            audio_file = item
            try:
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.music.unload()
            except Exception as e:
                print(f"[Bi - Miệng] Lỗi phát audio: {e}")
            finally:
                try:
                    os.remove(audio_file)
                except FileNotFoundError:
                    pass
            self.audio_queue.task_done()

    def _cleanup_chunks(self):
        """Xóa tất cả file voice_chunk_*.mp3 còn sót lại."""
        for f in glob.glob("voice_chunk_*.mp3"):
            try:
                os.remove(f)
            except FileNotFoundError:
                pass

    def run(self):
        try:
            while True:
                user_text = self.ear.listen()
                if not user_text:
                    continue

                print("[Bi - Não] Đang suy nghĩ...")
                buffer = ""
                self._chunk_counter = 0

                # Stream tokens từ LLM, tách câu theo . ? ! \n
                for token in self.brain.stream_chat(user_text):
                    buffer += token
                    while True:
                        match = re.search(r'[.?!\n]', buffer)
                        if not match:
                            break
                        end_pos = match.end()
                        sentence = buffer[:end_pos].strip()
                        buffer = buffer[end_pos:]
                        if sentence:
                            audio_file = self._loop.run_until_complete(
                                self.mouth._generate_audio(
                                    sentence, chunk_index=self._chunk_counter
                                )
                            )
                            self._chunk_counter += 1
                            self.audio_queue.put(audio_file)
                            print(f"[Bi - Miệng] Chunk {self._chunk_counter}: {sentence}")

                # Phần còn lại trong buffer (câu chưa kết thúc bằng dấu câu)
                if buffer.strip():
                    audio_file = self._loop.run_until_complete(
                        self.mouth._generate_audio(
                            buffer.strip(), chunk_index=self._chunk_counter
                        )
                    )
                    self._chunk_counter += 1
                    self.audio_queue.put(audio_file)
                    print(f"[Bi - Miệng] Chunk {self._chunk_counter}: {buffer.strip()}")

                # Đợi worker phát hết hàng đợi trước khi nghe tiếp
                self.audio_queue.join()

        except KeyboardInterrupt:
            self.audio_queue.put(None)
            self.audio_queue.join()
            self._cleanup_chunks()
            self._loop.close()
            print("[Hệ thống] Robot Bi đang tắt. Tạm biệt!")


if __name__ == "__main__":
    app = RobotBiApp()
    app.run()
