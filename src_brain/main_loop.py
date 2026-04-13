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
from src_brain.memory_rag.rag_manager import RAGManager
from src_brain.senses.eye_vision import EyeVision
from src_brain.ai_core.safety_filter import SafetyFilter
from src_brain.senses.cry_detector import CryDetector
from src_brain.network.notifier import get_notifier


class RobotBiApp:
    def __init__(self):
        self.ear = EarSTT()
        self.mouth = MouthTTS()
        self.brain = BiAI()
        self.rag = RAGManager()
        self.audio_queue = queue.Queue()
        self._chunk_counter = 0
        self._loop = asyncio.new_event_loop()

        # Daemon thread xử lý audio queue: play → unload → xóa file
        self._worker_thread = threading.Thread(
            target=self._audio_worker_loop, daemon=True
        )
        self._worker_thread.start()

        # EyeVision: daemon thread song song, không block voice I/O
        self.eye = EyeVision(
            camera_index=0,
            on_event_callback=self._on_vision_event,
        )
        self.eye.start()

        self.safety = SafetyFilter()

        # Notifier (WebSocket stub — Sprint 5 upgrade)
        self.notifier = get_notifier()

        # CryDetector — daemon thread song song
        self.cry_detector = CryDetector(on_cry_callback=self._on_cry_detected)
        self.cry_detector.start()

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

    def _on_cry_detected(self) -> None:
        """Callback khi CryDetector phát hiện tiếng khóc."""
        print("[Bi - Tai khoc] Phat hien tieng khoc! Bi dang kiem tra...")
        self.notifier.push_event(
            event_type="cry",
            message="Phat hien tieng khoc cua be",
        )
        # TODO Sprint 5: trigger robot di chuyen den vi tri be

    def _on_vision_event(self, event_type: str, clip_path: str | None) -> None:
        """Callback khi EyeVision phát hiện sự kiện."""
        if event_type == "stranger":
            print(f"[Bi - Mat] Phat hien nguoi la! Clip: {clip_path}")
            self.notifier.push_event(
                event_type="stranger",
                message="Phat hien nguoi la trong nha",
                clip_path=clip_path,
            )
        elif event_type == "motion":
            print(f"[Bi - Mat] Phat hien chuyen dong. Clip: {clip_path}")
            self.notifier.push_event(
                event_type="motion",
                message="Phat hien chuyen dong",
                clip_path=clip_path,
            )
        elif event_type == "known_face":
            print(f"[Bi - Mat] Nhan ra: {clip_path}")
            self.notifier.push_event(
                event_type="known_face",
                message=f"Nhan ra: {clip_path}",
            )

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
                # TODO Sprint upgrade: thay bằng wake-word detection
                # if self.ear.WAKEWORD_ENABLED:
                #     detected = self.ear.listen_for_wakeword(timeout=30.0)
                #     if not detected: continue
                user_text = self.ear.listen()
                if not user_text:
                    continue

                print("[Bi - Não] Đang suy nghĩ...")
                buffer = ""
                self._chunk_counter = 0

                # ── RAG: Retrieve context từ trí nhớ ──────────────────────────
                user_text_goc = user_text  # giữ lại bản gốc cho extract_and_save
                rag_context = self.rag.retrieve(user_text)
                if rag_context:
                    user_text = f"{rag_context}\n\nBé hỏi: {user_text}"
                    print(f"[Bi - Trí nhớ] {rag_context}")

                # Stream tokens từ LLM, tách câu theo . ? ! \n
                full_reply_parts = []
                for token in self.brain.stream_chat(user_text):
                    buffer += token
                    full_reply_parts.append(token)
                    while True:
                        match = re.search(r'[.?!\n]', buffer)
                        if not match:
                            break
                        end_pos = match.end()
                        sentence = buffer[:end_pos].strip()
                        buffer = buffer[end_pos:]
                        if sentence:
                            is_safe, clean_sentence = self.safety.check(sentence)
                            if not clean_sentence.strip():
                                continue  # bỏ qua câu rỗng sau khi lọc
                            audio_file = self._loop.run_until_complete(
                                self.mouth._generate_audio(
                                    clean_sentence, chunk_index=self._chunk_counter
                                )
                            )
                            if audio_file is None:
                                continue  # TTS hoàn toàn fail → bỏ qua chunk này
                            self._chunk_counter += 1
                            self.audio_queue.put(audio_file)
                            print(f"[Bi - Miệng] Chunk {self._chunk_counter}: {clean_sentence}")

                # Phần còn lại trong buffer (câu chưa kết thúc bằng dấu câu)
                if buffer.strip():
                    is_safe, clean_buffer = self.safety.check(buffer.strip())
                    if clean_buffer.strip():
                        audio_file = self._loop.run_until_complete(
                            self.mouth._generate_audio(
                                clean_buffer, chunk_index=self._chunk_counter
                            )
                        )
                        if audio_file is not None:
                            self._chunk_counter += 1
                            self.audio_queue.put(audio_file)
                            print(f"[Bi - Miệng] Chunk {self._chunk_counter}: {clean_buffer}")

                # Đợi worker phát hết hàng đợi trước khi nghe tiếp
                self.audio_queue.join()

                # ── RAG: Lưu facts vào ChromaDB (background, không block audio) ──
                full_reply = "".join(full_reply_parts).strip()
                if full_reply:
                    threading.Thread(
                        target=self.rag.extract_and_save,
                        args=(user_text_goc, full_reply),
                        daemon=True,
                    ).start()
                    # Log hội thoại cho Parent App (non-blocking)
                    threading.Thread(
                        target=self.notifier.push_chat_log,
                        args=(user_text_goc, full_reply),
                        daemon=True,
                    ).start()

        except KeyboardInterrupt:
            self.cry_detector.stop()
            self.eye.stop()
            self.audio_queue.put(None)
            self.audio_queue.join()
            self._cleanup_chunks()
            self._loop.close()
            print("[Hệ thống] Robot Bi đang tắt. Tạm biệt!")


if __name__ == "__main__":
    app = RobotBiApp()
    app.run()
