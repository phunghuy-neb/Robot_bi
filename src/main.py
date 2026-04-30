import sys
import os
import atexit
import logging
import threading
import queue
import glob
import asyncio
import re
import warnings

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

# Fix encoding cho console Windows (cp1252 không hỗ trợ tiếng Việt)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import pygame

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.audio.input.ear_stt import EarSTT
from src.audio.output.mouth_tts import MouthTTS
from src.ai.ai_engine import BiAI
from src.memory.rag_manager import RAGManager
from src.vision.camera_stream import EyeVision
from src.safety.safety_filter import SafetyFilter
from src.education.homework_classifier import classify_homework
from src.audio.analysis.cry_detector import CryDetector
from src.infrastructure.database.db import (
    init_db,
    cleanup_orphan_sessions,
    create_session,
    close_session,
    add_turn,
    mark_session_homework,
)
from src.infrastructure.notifications.notifier import get_notifier
from src.api.server import init_server, start_api_server, get_puppet_queue, init_task_manager, is_mom_talking
import src.infrastructure.sessions.state as _network_state

FAMILY_ID = os.getenv("FAMILY_ID", "default")

logger = logging.getLogger(__name__)


class RobotBiApp:
    def __init__(self):
        self._shutdown_done = False
        self._task_manager = None
        init_db()
        cleanup_orphan_sessions(max_age_hours=24)
        self.ear = EarSTT()
        self.mouth = MouthTTS()
        self.brain = BiAI()
        self.rag = RAGManager()
        self.audio_queue = queue.Queue()
        self._chunk_counter = 0
        self._loop = asyncio.new_event_loop()
        self._current_session_id = None
        self._family_id = FAMILY_ID

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

        # Notifier (Sprint 5: WebSocket thật)
        self.notifier = get_notifier()

        # CryDetector — daemon thread song song
        self.cry_detector = CryDetector(on_cry_callback=self._on_cry_detected)
        self.cry_detector.start()

        # Parent App API Server (Sprint 5)
        init_server(self.notifier, self.rag)

        # Task Manager với TTS callback (Sprint 6)
        init_task_manager(tts_callback=self._speak_text)
        self._task_manager = _network_state._task_manager
        start_api_server()
        self._puppet_queue = get_puppet_queue()

        atexit.register(self._shutdown)

        logger.info("[Hệ thống] Robot Bi đã khởi động và sẵn sàng!")

    def _speak_text(self, text: str) -> None:
        """Phát text qua TTS — dùng cho TaskManager reminder.
        Dùng asyncio.run() thay vì self._loop để tránh xung đột khi gọi từ reminder thread.
        """
        audio_file = asyncio.run(
            self.mouth._generate_audio(text, chunk_index=self._chunk_counter)
        )
        if audio_file:
            self._chunk_counter += 1
            self.audio_queue.put(audio_file)

    def _audio_worker_loop(self):
        """Worker thread: nhận audio file từ queue, phát, unload, xóa."""
        while True:
            item = self.audio_queue.get()
            if item is None:
                self.audio_queue.task_done()
                break
            audio_file = item
            if not os.path.exists(audio_file) or os.path.getsize(audio_file) == 0:
                logger.warning("[Bi - Miệng] File audio rỗng hoặc không tồn tại: %s", audio_file)
                self.audio_queue.task_done()
                continue
            try:
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.music.unload()
            except Exception as e:
                logger.error("[Bi - Miệng] Lỗi phát audio: %s", e)
            finally:
                try:
                    os.remove(audio_file)
                except (FileNotFoundError, PermissionError):
                    pass
            self.audio_queue.task_done()

    def _on_cry_detected(self) -> None:
        """Callback khi CryDetector phát hiện tiếng khóc."""
        logger.info("[Bi - Tai khoc] Phat hien tieng khoc! Bi dang kiem tra...")
        self.notifier.push_event(
            event_type="cry",
            message="Phat hien tieng khoc cua be",
        )

    def _on_vision_event(self, event_type: str, clip_path: str | None) -> None:
        """Callback khi EyeVision phát hiện sự kiện."""
        if event_type == "stranger":
            logger.info("[Bi - Mat] Phat hien nguoi la! Clip: %s", clip_path)
            self.notifier.push_event(
                event_type="stranger",
                message="Phat hien nguoi la trong nha",
                clip_path=clip_path,
            )
        elif event_type == "motion":
            logger.info("[Bi - Mat] Phat hien chuyen dong. Clip: %s", clip_path)
            self.notifier.push_event(
                event_type="motion",
                message="Phat hien chuyen dong",
                clip_path=clip_path,
            )
        elif event_type == "known_face":
            logger.info("[Bi - Mat] Nhan ra: %s", clip_path)
            self.notifier.push_event(
                event_type="known_face",
                message=f"Nhan ra: {clip_path}",
            )

    def _handle_puppet_queue(self) -> None:
        """
        Xử lý tất cả puppet commands đang chờ trong queue.
        Được gọi sau mỗi lượt nói chuyện và khi listen() trả về rỗng.
        SRS 4.5: "Phụ huynh gõ câu bất kỳ trên app, Bi đọc to ngay tại nhà"
        """
        queued = 0
        while not self._puppet_queue.empty():
            try:
                puppet_text = self._puppet_queue.get_nowait()
            except queue.Empty:
                break
            if not puppet_text:
                continue
            is_safe, clean = self.safety.check(puppet_text)
            if not clean.strip():
                continue
            logger.info("[Bi - Puppet] queued len=%d", len(clean))
            audio_file = self._loop.run_until_complete(
                self.mouth._generate_audio(clean, chunk_index=self._chunk_counter)
            )
            if audio_file:
                self._chunk_counter += 1
                self.audio_queue.put(audio_file)
                queued += 1
        if queued > 0:
            self.audio_queue.join()

    def _cleanup_chunks(self):
        """Xóa tất cả file voice_chunk_*.mp3 và *.wav còn sót lại."""
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception:
            pass
        import time
        time.sleep(0.3)
        for f in glob.glob("voice_chunk_*.mp3") + glob.glob("voice_chunk_*.wav"):
            try:
                os.remove(f)
            except (FileNotFoundError, PermissionError):
                pass

    def _close_current_session(self) -> None:
        if not self._current_session_id:
            return
        try:
            close_session(self._current_session_id)
        except Exception as e:
            logger.warning("[Bi - Session] Loi dong session: %s", e)
        finally:
            self._current_session_id = None

    def _mark_homework_if_needed(self, session_id: str | None, user_text: str) -> None:
        if not session_id:
            return
        try:
            if not classify_homework(user_text):
                return
            if mark_session_homework(session_id, family_id=self._family_id):
                self.notifier.push_event(
                    "homework",
                    f"Bé vừa hỏi bài: {user_text[:50]}",
                    family_id=self._family_id,
                )
        except Exception as e:
            logger.warning("[Bi - Homework] Loi classify/mark homework: %s", e)

    def _shutdown(self):
        if self._shutdown_done:
            return
        self._shutdown_done = True
        logger.info("[Shutdown] Bat dau don dep...")

        self._close_current_session()

        if self._task_manager:
            try:
                self._task_manager.stop()
            except Exception:
                pass

        try:
            from src.api.routers.ops_router import _tunnel_process
            if _tunnel_process and _tunnel_process.poll() is None:
                _tunnel_process.terminate()
                _tunnel_process.wait(timeout=5)
        except Exception:
            pass

        try:
            from src.api.routers.webrtc_router import _peer_connections
            loop = asyncio.get_event_loop()
            for pc in list(_peer_connections.values()):
                loop.run_until_complete(pc.close())
            _peer_connections.clear()
        except Exception:
            pass

        try:
            self.cry_detector.stop()
        except Exception:
            pass
        try:
            self.eye.stop()
        except Exception:
            pass
        try:
            self.audio_queue.put(None)
            self.audio_queue.join()
        except Exception:
            pass
        self._cleanup_chunks()
        try:
            self._loop.close()
        except Exception:
            pass

        logger.info("[Shutdown] Hoan tat.")

    def run(self):
        import time as _time
        try:
            while True:
                try:
                    # Skip listen khi mẹ đang nói trực tiếp qua /api/mom/audio
                    if is_mom_talking():
                        _time.sleep(0.5)
                        continue

                    user_text = self.ear.listen()
                    if not user_text:
                        self._handle_puppet_queue()   # xử lý puppet khi không có ai nói
                        continue

                    logger.debug("[Bi - Não] Đang suy nghĩ...")
                    buffer = ""
                    self._chunk_counter = 0
                    self._close_current_session()
                    self._current_session_id = create_session(FAMILY_ID)
                    is_first_turn_of_session = True

                    # ── RAG: Retrieve context từ trí nhớ ──────────────────────────
                    user_text_goc = user_text  # giữ lại bản gốc cho extract_and_save
                    add_turn(self._current_session_id, 'user', user_text_goc)
                    if is_first_turn_of_session:
                        def _name_session(session_id=self._current_session_id, user_text=user_text_goc):
                            from src.infrastructure.sessions.session_namer import _generate_session_title
                            from src.infrastructure.database.db import update_session_title

                            title = _generate_session_title(user_text)
                            update_session_title(session_id, title)

                        threading.Thread(target=_name_session, daemon=True).start()
                        is_first_turn_of_session = False
                    rag_context = self.rag.retrieve(user_text, family_id=FAMILY_ID)
                    if rag_context:
                        user_text = f"{rag_context}\n\nBé hỏi: {user_text}"
                        # DEBUG: chứa PII - tắt trong production.
                        logger.debug("[Bi - Trí nhớ] %s", rag_context)

                    # Stream tokens từ LLM, tách câu theo . ? ! \n
                    full_reply_parts = []
                    sanitized_reply_parts = []
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
                                sanitized_reply_parts.append(clean_sentence)
                                audio_file = self._loop.run_until_complete(
                                    self.mouth._generate_audio(
                                        clean_sentence, chunk_index=self._chunk_counter
                                    )
                                )
                                if audio_file is None:
                                    continue  # TTS hoàn toàn fail → bỏ qua chunk này
                                self._chunk_counter += 1
                                self.audio_queue.put(audio_file)
                                logger.debug("[Bi - Miệng] Chunk %d len=%d", self._chunk_counter, len(clean_sentence))

                    # Phần còn lại trong buffer (câu chưa kết thúc bằng dấu câu)
                    if buffer.strip():
                        is_safe, clean_buffer = self.safety.check(buffer.strip())
                        if clean_buffer.strip():
                            sanitized_reply_parts.append(clean_buffer)
                            audio_file = self._loop.run_until_complete(
                                self.mouth._generate_audio(
                                    clean_buffer, chunk_index=self._chunk_counter
                                )
                            )
                            if audio_file is not None:
                                self._chunk_counter += 1
                                self.audio_queue.put(audio_file)
                                logger.debug("[Bi - Miệng] Chunk %d len=%d", self._chunk_counter, len(clean_buffer))

                    # Đợi worker phát hết hàng đợi trước khi nghe tiếp
                    self.audio_queue.join()

                    # Xử lý puppet sau khi Bi nói xong
                    self._handle_puppet_queue()

                    # ── RAG: Lưu facts vào ChromaDB (background, không block audio) ──
                    full_reply = "".join(full_reply_parts).strip()
                    sanitized_reply = " ".join(sanitized_reply_parts).strip()
                    if full_reply:
                        add_turn(self._current_session_id, 'assistant', sanitized_reply)
                        self._mark_homework_if_needed(self._current_session_id, user_text_goc)
                        self._close_current_session()
                        threading.Thread(
                            target=self.rag.extract_and_save,
                            args=(user_text_goc, sanitized_reply),
                            kwargs={"family_id": FAMILY_ID},
                            daemon=True,
                        ).start()
                        # Log hội thoại cho Parent App (non-blocking)
                        threading.Thread(
                            target=self.notifier.push_chat_log,
                            args=(user_text_goc, sanitized_reply),
                            kwargs={"family_id": FAMILY_ID},
                            daemon=True,
                        ).start()
                    else:
                        self._close_current_session()
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error("[MainLoop] Loi khong mong doi, bo qua iteration: %s", e, exc_info=True)
                    self._close_current_session()
                    _time.sleep(1)
                    continue

        except KeyboardInterrupt:
            self._shutdown()
            logger.info("[Hệ thống] Robot Bi đang tắt. Tạm biệt!")


if __name__ == "__main__":
    app = RobotBiApp()
    app.run()
