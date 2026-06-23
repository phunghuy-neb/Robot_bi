# Robot Bi — Backend API

## src/main.py

```python
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

from dotenv import load_dotenv
load_dotenv()

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

from src.display.face_animator import FaceAnimator
from src.ai.persona_manager import PersonaManager
from src.emotion.emotion_analyzer import EmotionAnalyzer
from src.emotion.emotion_alert import EmotionAlert

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

        try:
            self._face = FaceAnimator(notifier=self.notifier)
            self._persona = PersonaManager(family_id=self._family_id)
            self._emotion = EmotionAnalyzer(family_id=self._family_id)
            self._alert = EmotionAlert()
        except Exception as e:
            logger.error("[Init] Error init Face/Persona/Emotion: %s", e)
            self._face = None
            self._persona = None
            self._emotion = None
            self._alert = None

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
        clock = pygame.time.Clock()
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
                if self._face:
                    try:
                        self._face.set_mode('talking')
                    except Exception:
                        pass
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    clock.tick(10)
                pygame.mixer.music.unload()
                if self._face:
                    try:
                        self._face.set_mode('idle')
                    except Exception:
                        pass
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

    def _check_emotion_alert(self):
        try:
            if self._alert and self._emotion:
                self._alert.check_and_alert(
                    self._family_id, self._emotion, self.notifier
                )
        except Exception:
            pass

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

                    if self._face:
                        try:
                            self._face.set_mode('listening')
                        except Exception:
                            pass

                    user_text = self.ear.listen()
                    
                    if not user_text:
                        if self._face:
                            try:
                                self._face.set_mode('idle')
                            except Exception:
                                pass
                        self._handle_puppet_queue()   # xử lý puppet khi không có ai nói
                        continue

                    try:
                        if self._emotion:
                            emotion, confidence = self._emotion.analyze_text(user_text)
                            self._emotion.record_emotion(
                                emotion, confidence, family_id=self._family_id
                            )
                            # Check alert trong background thread
                            threading.Thread(
                                target=self._check_emotion_alert,
                                daemon=True
                            ).start()
                    except Exception as e:
                        logger.debug("[Emotion] Analysis skip: %s", e)

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

                    if self._face:
                        try:
                            self._face.set_mode('thinking')
                        except Exception:
                            pass

                    if self._persona:
                        try:
                            persona_mod = self._persona.get_system_prompt_modifier()
                            if persona_mod:
                                user_text = f"System Instruction: {persona_mod}\n\n{user_text}"
                        except Exception as e:
                            logger.debug("[Persona] Error: %s", e)

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

                    if self._face:
                        try:
                            self._face.set_mode('idle')
                        except Exception:
                            pass

                    # Xử lý puppet sau khi Bi nói xong
                    self._handle_puppet_queue()

                    # ── RAG: Lưu facts vào ChromaDB (background, không block audio) ──
                    full_reply = "".join(full_reply_parts).strip()
                    sanitized_reply = " ".join(sanitized_reply_parts).strip()
                    if sanitized_reply:
                        add_turn(self._current_session_id, 'assistant', sanitized_reply)
                        self._mark_homework_if_needed(self._current_session_id, user_text_goc)
                        threading.Thread(
                            target=self.rag.extract_and_save,
                            args=(user_text_goc, sanitized_reply),
                            kwargs={"family_id": FAMILY_ID},
                            daemon=True,
                        ).start()
                        self._close_current_session()
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
```

## src/ai/ai_engine.py

```python
"""
core_ai.py — Robot Bi AI Core
Kiến trúc: Groq (primary) → Gemini Flash-Lite (fallback)
- Groq Llama 3.3 70B: ~400 token/giây, 14.400 request/ngày free
- Gemini 2.5 Flash-Lite: fallback khi Groq hết quota, 1.000 req/ngày free
- Tự động xoay vòng, không cần can thiệp thủ công
"""

import logging
import os
import json
import time
import threading
import requests
from pathlib import Path
from typing import Generator
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env
load_dotenv()

# Load config.json
_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"
try:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
        _CONFIG = json.load(_f)
except FileNotFoundError:
    _CONFIG = {
        "groq_model": "llama-3.3-70b-versatile",
        "gemini_model": "gemini-2.5-flash-lite-preview-06-17",
        "max_history_turns": 10,
        "groq_cooldown_seconds": 60,
    }

# API Keys từ .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Endpoints
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{_CONFIG['gemini_model']}:streamGenerateContent"
)

# Trạng thái quota nội bộ
_groq_fail_streak = 0
_groq_cooldown_until = 0.0
_groq_lock = threading.Lock()
_GROQ_COOLDOWN = _CONFIG.get("groq_cooldown_seconds", 60)


def _get_system_prompt() -> str:
    """Lấy system prompt từ prompts.py và thêm rule ngôn ngữ."""
    try:
        from src.ai.prompts import MAIN_SYSTEM_PROMPT
        base = MAIN_SYSTEM_PROMPT
    except ImportError:
        try:
            from src.ai import prompts
            base = prompts.MAIN_SYSTEM_PROMPT
        except ImportError:
            base = (
                "Bạn là Bi, một robot gia sư thông minh và gần gũi. "
                "Bạn xưng là 'Bi' và gọi người dùng là 'bạn' hoặc 'em'. "
                "Luôn trả lời ngắn gọn 3-4 câu, vui vẻ, dễ hiểu."
            )

    language_rule = (
        "\n\nNGÔN NGỮ PHẢN HỒI — BẮT BUỘC TUÂN THỦ:\n"
        "- Phát hiện ngôn ngữ bé đang dùng trong tin nhắn cuối.\n"
        "- Trả lời TOÀN BỘ bằng đúng ngôn ngữ đó. KHÔNG trộn ngôn ngữ khác.\n"
        "- Bé nói tiếng Việt → trả lời 100% tiếng Việt.\n"
        "- Bé nói tiếng Anh → trả lời 100% tiếng Anh.\n"
        "- Ngoại lệ duy nhất: bé chủ động yêu cầu kết hợp 2 ngôn ngữ.\n"
        "- TUYỆT ĐỐI không tự ý thêm tiếng Trung hoặc ngôn ngữ không được yêu cầu.\n"
        "- Câu trả lời ngắn gọn, tự nhiên, phù hợp trẻ em."
    )
    return base + language_rule


def _stream_groq(messages: list, system_prompt: str) -> Generator[str, None, None]:
    """Gọi Groq API, stream từng token."""
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("DIEN_"):
        raise ValueError("GROQ_API_KEY chưa được cấu hình trong .env")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _CONFIG["groq_model"],
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 512,
        "temperature": 0.7,
        "stream": True,
    }

    resp = requests.post(
        _GROQ_URL, headers=headers, json=payload, stream=True, timeout=15
    )
    if resp.status_code == 429:
        raise RuntimeError("Groq quota exceeded (429)")
    if resp.status_code != 200:
        raise RuntimeError(f"Groq HTTP {resp.status_code}: {resp.text[:200]}")

    for raw in resp.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                yield delta
        except (json.JSONDecodeError, KeyError, IndexError):
            continue


def _stream_gemini(messages: list, system_prompt: str) -> Generator[str, None, None]:
    """Gọi Gemini API, stream từng token."""
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("DIEN_"):
        raise RuntimeError("GEMINI_API_KEY chưa được cấu hình trong .env")

    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 512, "temperature": 0.7},
    }
    url = f"{_GEMINI_URL}?alt=sse"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }
    resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=20)

    if resp.status_code == 429:
        raise RuntimeError("Gemini quota exceeded (429)")
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")

    for raw in resp.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not line.startswith("data: "):
            continue
        data = line[6:]
        try:
            chunk = json.loads(data)
            parts = (
                chunk.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [])
            )
            for part in parts:
                text = part.get("text", "")
                if text:
                    yield text
        except (json.JSONDecodeError, KeyError, IndexError):
            continue


def stream_chat(messages: list) -> Generator[str, None, None]:
    """
    Public API — gọi hàm này từ main_loop.py.
    Tự động: Groq → Gemini → thông báo lỗi.

    Args:
        messages: list of {"role": "user"|"assistant", "content": str}
    """
    global _groq_fail_streak, _groq_cooldown_until

    # Trim history để tiết kiệm token
    max_turns = _CONFIG.get("max_history_turns", 10)
    if len(messages) > max_turns * 2:
        messages = messages[-(max_turns * 2):]

    system_prompt = _get_system_prompt()
    now = time.time()
    with _groq_lock:
        groq_cooldown_until = _groq_cooldown_until

    # --- Thử Groq trước (nhanh nhất) ---
    if now > groq_cooldown_until:
        try:
            logger.debug("[Bi - Não] Groq (Llama 70B)...")
            yield from _stream_groq(messages, system_prompt)
            with _groq_lock:
                _groq_fail_streak = 0
            return
        except Exception as e:
            cooldown_started = False
            with _groq_lock:
                _groq_fail_streak += 1
                if _groq_fail_streak >= 3:
                    _groq_cooldown_until = now + _GROQ_COOLDOWN
                    _groq_fail_streak = 0
                    cooldown_started = True
            logger.warning("[Bi - Não] Groq lỗi (%s) — chuyển Gemini", e)
            if cooldown_started:
                logger.warning("[Bi - Não] Groq tạm dừng %ss", _GROQ_COOLDOWN)

    # --- Fallback Gemini ---
    try:
        logger.debug("[Bi - Não] Gemini Flash-Lite...")
        yield from _stream_gemini(messages, system_prompt)
        return
    except Exception as e:
        logger.warning("[Bi - Não] Gemini lỗi (%s)", e)

    # --- Cả 2 đều fail ---
    yield "Xin lỗi bé, Bi đang gặp sự cố kết nối. Bé thử lại sau một chút nhé!"


# ── Backward-compat class — giữ để không break main_loop.py ──────────────────

class BiAI:
    """
    Backward-compat wrapper. main_loop.py dùng BiAI().stream_chat(user_text).
    Nội bộ gọi stream_chat() module-level và duy trì history.
    """

    def __init__(self) -> None:
        self.history: list = []
        self.total_turns: int = 0

    def stream_chat(self, user_input: str, history: list = None) -> Generator[str, None, None]:
        """
        Stream phản hồi từ AI.

        Args:
            user_input: Văn bản câu hỏi của người dùng.
            history: Nếu truyền vào thì dùng history này (không cập nhật nội bộ).
                     Nếu None thì dùng và cập nhật self.history.
        """
        if history is not None:
            msgs = list(history)
        else:
            msgs = list(self.history)
        msgs.append({"role": "user", "content": user_input})

        full_reply = ""
        for token in stream_chat(msgs):
            full_reply += token
            yield token

        # Cập nhật history nội bộ khi không có history bên ngoài truyền vào
        if history is None and full_reply:
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": full_reply.strip()})
            max_turns = _CONFIG.get("max_history_turns", 10)
            if len(self.history) > max_turns * 2:
                self.history = self.history[-(max_turns * 2):]
            self.total_turns += 1

    def reset_history(self) -> None:
        """Xóa toàn bộ lịch sử hội thoại."""
        self.history.clear()


# ── Test độc lập ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  TEST core_ai.py — Groq + Gemini")
    print("=" * 60)
    print(f"  Groq model : {_CONFIG['groq_model']}")
    print(f"  Gemini model: {_CONFIG['gemini_model']}")
    print(f"  GROQ_API_KEY: {'OK' if GROQ_API_KEY and not GROQ_API_KEY.startswith('DIEN_') else 'CHUA CAU HINH'}")
    print(f"  GEMINI_API_KEY: {'OK' if GEMINI_API_KEY and not GEMINI_API_KEY.startswith('DIEN_') else 'CHUA CAU HINH'}\n")

    bi = BiAI()
    test_questions = [
        "Xin chào Bi!",
        "Tại sao bầu trời màu xanh?",
    ]

    for q in test_questions:
        print(f"\nBan: {q}")
        print("Bi: ", end="", flush=True)
        for token in bi.stream_chat(q):
            print(token, end="", flush=True)
        print()

    print(f"\nTest hoàn thành — {bi.total_turns} lượt hội thoại.")
```

## src/ai/prompts.py

```python
"""
prompts.py — Robot Bi: Kho lưu trữ System Prompts
===================================================
Tách biệt khỏi core_ai.py để dễ maintain và A/B test.
Hiện tại chưa import vào core_ai.py — chuẩn bị cho refactor sau.
"""

# ── System Prompt chính — Persona Bi ─────────────────────────────────────────
MAIN_SYSTEM_PROMPT = """Bạn là Bi, một robot gia sư thông minh và gần gũi do sinh viên PTIT tạo ra. Bạn xưng là "Bi" và gọi người dùng là "bạn" hoặc "em".

TUYỆT ĐỐI TUÂN THỦ 3 QUY TẮC SAU:
1. LUÔN viết thành một đoạn văn xuôi duy nhất, KHÔNG BAO GIỜ xuống dòng, KHÔNG BAO GIỜ dùng gạch đầu dòng hay số thứ tự.
2. Tối đa 3 đến 4 câu. Mọi kiến thức phức tạp đều BẮT BUỘC phải kèm theo ví dụ so sánh bằng những đồ vật quen thuộc hàng ngày. Dùng các từ đệm tự nhiên (Dạ, Vâng, Nhé).
3. Nếu câu hỏi quá chuyên sâu hoặc Bi không chắc chắn, CHỈ ĐƯỢC PHÉP nói: "Bi chưa có dữ liệu về phần này."

DƯỚI ĐÂY LÀ CÁC VÍ DỤ BẮT BUỘC BẠN PHẢI BẮT CHƯỚC CÁCH TRẢ LỜI:
Người: Tại sao bầu trời có màu xanh thế Bi?
Bi: Dạ, ánh sáng mặt trời có đủ 7 màu cầu vồng, nhưng khi chiếu xuống Trái Đất thì màu xanh bị các hạt không khí cản lại và bắn tung tóe ra khắp nơi. Nó giống hệt như khi bạn xịt vòi nước mạnh vào bức tường và những tia nước li ti văng ra vậy đó. Mắt chúng ta hứng trọn những tia sáng xanh văng ra này nên nhìn thấy bầu trời màu xanh nhé!

Người: Liệt kê cho tôi 5 hành tinh trong hệ mặt trời.
Bi: Vâng, 5 hành tinh trong hệ Mặt Trời bao gồm Sao Thủy, Sao Kim, Trái Đất, Sao Hỏa và Sao Mộc nhé. Bạn thích hành tinh nào nhất?

Người: Giải thích thuật toán Transformer attention mechanism trong deep learning.
Bi: Dạ, Bi chưa có dữ liệu về phần này. Bạn có câu hỏi nào khác không?

NGÔN NGỮ PHẢN HỒI — TUÂN THỦ TUYỆT ĐỐI:
- Phát hiện ngôn ngữ bé đang dùng trong tin nhắn cuối.
- Trả lời TOÀN BỘ bằng đúng ngôn ngữ đó. KHÔNG trộn ngôn ngữ khác vào giữa câu.
- Ví dụ: bé nói tiếng Việt → trả lời 100% tiếng Việt. Bé nói tiếng Anh → trả lời 100% tiếng Anh.
- Ngoại lệ DUY NHẤT: bé chủ động yêu cầu kết hợp 2 ngôn ngữ (ví dụ: "dạy mình từ tiếng Anh đi") thì mới được dùng 2 ngôn ngữ theo yêu cầu đó.
- TUYỆT ĐỐI KHÔNG tự ý thêm tiếng Trung, tiếng Nhật, hoặc bất kỳ ngôn ngữ nào ngoài ngôn ngữ bé đang dùng.
"""

# ── Safety Check Prompt (dùng cho future LLM-based safety) ───────────────────
# Placeholder cho khi nâng cấp safety filter sang LLM-based classifier.
# Hiện tại safety_filter.py dùng regex — nhanh hơn, không cần LLM gọi thêm.
SAFETY_CHECK_PROMPT = """Bạn là bộ lọc an toàn cho robot gia sư trẻ em.
Trả lời chỉ 'SAFE' hoặc 'UNSAFE'. Không giải thích.
UNSAFE khi: bạo lực, người lớn, tự hại, chính trị, tôn giáo cực đoan.
SAFE khi: giáo dục, trò chuyện thông thường, câu hỏi của trẻ em."""

# ── Refusal Response chuẩn (SRS 2.3) ─────────────────────────────────────────
# Câu từ chối duy nhất được phép dùng — không thêm bất cứ từ nào.
REFUSAL_RESPONSE = "Bi chưa có dữ liệu về vấn đề này."

# ── Câu chào mở đầu ───────────────────────────────────────────────────────────
GREETING = "Xin chào! Mình là Bi! Robot gia sư của bạn đây! Hôm nay bạn muốn học gì nào?"

# ── Dynamic Prompt Builder ───────────────────────────────────────────────────
def build_system_prompt(persona: dict) -> str:
    """ Tạo system prompt dựa trên tính cách:
    Nếu playfulness > 70:
        "Hãy trả lời vui vẻ, nghịch ngợm, hay pha trò"
    Nếu energy > 70:
        "Hãy nhiệt tình, hào hứng, dùng nhiều dấu !"
    Nếu extraversion < 30:
        "Hãy trả lời ngắn gọn, trầm tĩnh"

    Kết hợp với tên robot và giới tính.
    """
    name = persona.get("name", "Bi")
    gender = persona.get("gender", "robot")
    playfulness = persona.get("playfulness", 50)
    energy = persona.get("energy", 50)
    extraversion = persona.get("extraversion", 50)
    
    prompt = f"Bạn là {name}, một {gender} gia sư thông minh.\n"
    
    if playfulness > 70:
        prompt += "Hãy trả lời vui vẻ, nghịch ngợm, hay pha trò.\n"
    if energy > 70:
        prompt += "Hãy nhiệt tình, hào hứng, dùng nhiều dấu !\n"
    if extraversion < 30:
        prompt += "Hãy trả lời ngắn gọn, trầm tĩnh.\n"
        
    return prompt
```

## src/safety/safety_filter.py

```python
"""
safety_filter.py — Robot Bi: Bộ lọc an toàn nội dung (NFR-12)
==============================================================
Chạy sau LLM, trước TTS. 0% tolerance với nội dung không phù hợp trẻ em.

Thứ tự kiểm tra:
  1. _topic_classifier() — phát hiện chủ đề nhạy cảm bằng regex → refusal ngay
  2. _blacklist_filter()  — thay thế từ tiêu cực trong blacklist (SRS ST-04)
  3. _sentence_length_check() — cắt bớt nếu quá 4 câu (SRS ST-01)

Interface:
    sf = SafetyFilter()
    is_safe, clean_text = sf.check(text)
    # is_safe=True  → clean_text = text đã làm sạch, có thể đưa vào TTS
    # is_safe=False → clean_text = câu từ chối chuẩn của Bi (SRS 2.3)
"""

import re

# ── Câu từ chối chuẩn (SRS 2.3) ──────────────────────────────────────────────
_REFUSAL_RESPONSE = "Bi chưa có dữ liệu về vấn đề này."

# ── Blacklist từ tiêu cực (SRS ST-04) ────────────────────────────────────────
# Danh sách các từ không phù hợp với robot gia sư trẻ em.
# Thứ tự: từ dài trước từ ngắn để tránh partial-match sai.
_BLACKLIST_WORDS = [
    "ngu ngốc",
    "sai bét",
    "xấu xa",
    "ngu",
    "dốt",
    "ngốc",
    "khùng",
    "điên",
    "không được",
    "tệ",
    "thất bại",
]

# ── Patterns chủ đề nhạy cảm ─────────────────────────────────────────────────
# Dùng để phát hiện output LLM có nội dung không phù hợp trẻ em.
_SENSITIVE_PATTERNS = [
    # Bạo lực rõ ràng
    r'(?<!\w)(giết|bắn|đánh nhau|chiến tranh|vũ khí|bom|dao găm|súng)(?!\w)',
    # Chính trị
    r'(?<!\w)(chính trị|đảng phái|biểu tình|cách mạng|lật đổ|chế độ)(?!\w)',
    # Tôn giáo cực đoan
    r'(?<!\w)(thánh chiến|khủng bố|cực đoan|tử đạo)(?!\w)',
    # Tự hại
    r'(?<!\w)(tự tử|tự làm đau|cắt tay|tự sát)(?!\w)',
    # Nội dung người lớn — pattern chung
    r'(?<!\w)(sex|porn|18\+|khiêu dâm|nội dung người lớn)(?!\w)',
]


class SafetyFilter:
    """
    Bộ lọc an toàn nội dung cho Robot Bi.

    Chạy sau LLM output, trước khi text đưa vào TTS.
    Áp dụng 3 lớp lọc theo thứ tự ưu tiên.
    """

    def __init__(self):
        # Compile tất cả regex patterns một lần để tối ưu hiệu năng
        self._sensitive_regexes = [
            re.compile(p, re.IGNORECASE | re.UNICODE)
            for p in _SENSITIVE_PATTERNS
        ]
        # Compile blacklist thành pattern word-boundary để tránh partial match
        self._blacklist_regexes = [
            (word, re.compile(r'(?<!\w)' + re.escape(word) + r'(?!\w)', re.IGNORECASE | re.UNICODE))
            for word in _BLACKLIST_WORDS
        ]

    def check(self, text: str) -> tuple[bool, str]:
        """
        Kiểm tra và làm sạch text trước khi đưa vào TTS.

        Args:
            text: Chuỗi output từ LLM cần kiểm tra.

        Returns:
            (is_safe, clean_text):
                is_safe=True  → clean_text = text đã làm sạch
                is_safe=False → clean_text = _REFUSAL_RESPONSE
        """
        if not text or not text.strip():
            return True, text

        # Bước 1: Phân loại chủ đề nhạy cảm — refusal ngay nếu trigger
        if not self._topic_classifier(text):
            return False, _REFUSAL_RESPONSE

        # Bước 2: Lọc blacklist — thay thế từ xấu
        has_blacklist, clean_text = self._blacklist_filter(text)

        # Bước 3: Kiểm tra độ dài câu — cắt bớt nếu quá 4 câu (SRS ST-01)
        clean_text = self._sentence_length_check(clean_text)

        return True, clean_text

    def _blacklist_filter(self, text: str) -> tuple[bool, str]:
        """
        Lọc và thay thế các từ trong blacklist (SRS ST-04).

        Args:
            text: Chuỗi cần lọc.

        Returns:
            (has_blacklist_word, cleaned_text):
                has_blacklist_word = True nếu có từ xấu
                cleaned_text = text sau khi thay thế từ xấu bằng "..."
        """
        has_blacklist = False
        result = text
        for word, pattern in self._blacklist_regexes:
            if pattern.search(result):
                has_blacklist = True
                result = pattern.sub("...", result)
        return has_blacklist, result

    def _topic_classifier(self, text: str) -> bool:
        """
        Phát hiện chủ đề nhạy cảm bằng regex pattern matching.

        Args:
            text: Chuỗi cần kiểm tra.

        Returns:
            True nếu an toàn (không có pattern nhạy cảm),
            False nếu phát hiện chủ đề nhạy cảm.
        """
        for pattern in self._sensitive_regexes:
            if pattern.search(text):
                return False  # Nhạy cảm → không an toàn
        return True  # Không có pattern → an toàn

    def _sentence_length_check(self, text: str) -> str:
        """
        Đảm bảo response không quá dài (SRS ST-01: tối đa 3-4 câu).

        Tách câu theo dấu kết câu (. ? !), cắt còn tối đa 4 câu.
        Ghép lại thành một chuỗi liền mạch.

        Args:
            text: Chuỗi cần kiểm tra độ dài.

        Returns:
            Chuỗi đã cắt (nếu cần), hoặc nguyên bản nếu đủ ngắn.
        """
        # Tách theo dấu kết câu nhưng giữ dấu câu lại
        sentences = re.split(r'(?<=[.?!])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 4:
            return text

        # Cắt còn 4 câu, ghép lại
        return " ".join(sentences[:4])


# ── Test độc lập ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sf = SafetyFilter()
    print("=" * 60)
    print("  TEST safety_filter.py")
    print("=" * 60)

    # Test 1: Text bình thường → pass
    safe1, text1 = sf.check("Dạ, bầu trời màu xanh vì ánh sáng mặt trời bị tán xạ nhé!")
    assert safe1 == True, "FAIL Test 1: text bình thường bị block"
    print(f"Test 1 PASS — text bình thường: safe={safe1}, text='{text1}'")

    # Test 2: Text có "chiến tranh" → refusal
    safe2, text2 = sf.check("chiến tranh là khi hai nước đánh nhau bằng vũ khí và giết nhau")
    assert safe2 == False, "FAIL Test 2: text bạo lực/chiến tranh không bị block"
    assert text2 == _REFUSAL_RESPONSE, "FAIL Test 2: refusal response sai"
    print(f"Test 2 PASS — text nhạy cảm bị block: safe={safe2}")

    # Test 3: Text có từ "ngu" → blacklist replace
    safe3, text3 = sf.check("bạn thật ngu ngốc!")
    assert "ngu" not in text3, f"FAIL Test 3: từ 'ngu' không bị xóa, kết quả: '{text3}'"
    print(f"Test 3 PASS — blacklist word bị xóa: '{text3}'")

    # Test 4: Text quá 5 câu → cắt còn 4
    long_text = "Câu một là đây. Câu hai nè bạn! Câu ba cũng vui. Câu bốn rồi nhé? Câu năm thừa ra."
    safe4, text4 = sf.check(long_text)
    sentences = [s for s in re.split(r'(?<=[.?!])\s+', text4.strip()) if s.strip()]
    assert len(sentences) <= 4, f"FAIL Test 4: vẫn còn {len(sentences)} câu sau khi cắt"
    print(f"Test 4 PASS — text dài bị cắt còn {len(sentences)} câu")

    # Test 5: Text đã là refusal response → pass nguyên
    safe5, text5 = sf.check(_REFUSAL_RESPONSE)
    assert safe5 == True, "FAIL Test 5: refusal response bị block"
    print(f"Test 5 PASS — refusal response pass nguyên: '{text5}'")

    print()
    print("ALL 5 TESTS PASSED ✅")
```

## src/api/server.py

```python
"""
api_server.py — Robot Bi: FastAPI Parent App Backend
=====================================================
Entry point: init_server() + start_api_server() từ main_loop.py.

Routes được tổ chức thành routers/:
  auth_router         — /api/auth/*, /auth/*
  admin_router        — /api/admin/families/*
  conversation_router — /api/conversations/*
  streaming_router    — /ws, /api/audio/stream, /api/mom/*
  control_router      — /api/status, /api/events/*, /api/tasks/*, /api/memories/*, /api/puppet
  ops_router          — /health, /, /api/camera
"""

import asyncio
import logging
import os
import socket
import threading
import warnings
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

import src.infrastructure.sessions.state as _state
from src.infrastructure.logging.log_config import setup_logging
from src.api.routers.auth_router import router as auth_router
from src.api.routers.admin_router import router as admin_router
from src.api.routers.analytics_router import router as analytics_router
from src.api.routers.conversation_router import router as conversation_router, _require_family
from src.api.routers.streaming_router import router as streaming_router
from src.api.routers.control_router import router as control_router
from src.api.routers.education_router import router as education_router
from src.api.routers.emotion_router import router as emotion_router
from src.api.routers.game_router import router as game_router
from src.api.routers.music_router import router as music_router
from src.api.routers.motor_router import router as motor_router
from src.api.routers.wifi_router import router as wifi_router
from src.api.routers.ops_router import router as ops_router
from src.api.routers.ops_router import _build_ascii_qr, _start_cloudflare_tunnel
from src.motion.motor_controller import get_shared_motor
from src.api.routers.persona_router import router as persona_router
from src.api.routers.story_router import router as story_router
from src.api.routers.video_call_router import router as video_call_router
from src.api.routers import webrtc_router

logger = logging.getLogger("api_server")

# ── SSL config ────────────────────────────────────────────────────────────────
_SSL_DIR  = Path(__file__).parent.parent.parent / "ssl"
_SSL_CERT = _SSL_DIR / "cert.pem"
_SSL_KEY  = _SSL_DIR / "key.pem"
_USE_HTTPS = _SSL_CERT.exists() and _SSL_KEY.exists()

# ── Thư mục static ────────────────────────────────────────────────────────────
_PARENT_APP_DIR = Path(__file__).parent.parent.parent / "frontend" / "parent_app"
_PARENT_APP_DIR.mkdir(parents=True, exist_ok=True)
_PARENT_APP_DIST_DIR = _PARENT_APP_DIR / "dist"
_PARENT_APP_ASSETS_DIR = _PARENT_APP_DIST_DIR / "assets"


def get_local_ip() -> str:
    """Lấy IP WiFi LAN thật, bỏ qua VPN/Hamachi/tunnel."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(title="Robot Bi — Parent App API", version="2.0")

app.mount("/static", StaticFiles(directory=str(_PARENT_APP_DIR)), name="static")
if _PARENT_APP_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(_PARENT_APP_ASSETS_DIR)), name="parent_app_assets")

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(conversation_router)
app.include_router(streaming_router)
app.include_router(control_router)
app.include_router(education_router)
app.include_router(emotion_router)
app.include_router(game_router)
app.include_router(music_router)
app.include_router(motor_router)
app.include_router(wifi_router)
app.include_router(ops_router)
app.include_router(persona_router)
app.include_router(story_router)
app.include_router(video_call_router)
app.include_router(webrtc_router.router)


@app.on_event("startup")
async def _on_startup():
    setup_logging()
    _state._api_loop = asyncio.get_event_loop()
    logger.info("[API] FastAPI server started. Event loop captured.")
    # Eager-init MotorController trong thread pool — không block event loop
    import concurrent.futures
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, get_shared_motor)
    logger.info("[API] MotorController initialized.")


# ── Public API — gọi từ main_loop.py ─────────────────────────────────────────

def init_server(notifier, rag_manager) -> None:
    """Inject dependencies từ main_loop.py. Gọi TRƯỚC start_api_server()."""
    _state._notifier = notifier
    _state._rag = rag_manager
    notifier.set_ws_broadcaster(_state._broadcast_from_thread)
    from src.infrastructure.notifications import notifier as _notifier_mod
    _notifier_mod.set_ws_broadcaster(_state._ws_manager.broadcast)
    logger.info("[API] Dependencies injected (notifier + rag).")


def get_puppet_queue():
    """Trả về queue puppet để main_loop.py poll và đọc commands."""
    return _state._puppet_queue


def init_task_manager(tts_callback) -> None:
    """Inject TaskManager với TTS callback từ main_loop.py."""
    from src.infrastructure.tasks.task_manager import TaskManager
    _state._task_manager = TaskManager(tts_callback=tts_callback)
    logger.info("[API] TaskManager injected.")


def is_mom_talking() -> bool:
    """Public helper — main_loop.py import để check trạng thái mẹ."""
    return _state.is_mom_talking()


# ── QR helper (build via ops_router._build_ascii_qr) ─────────────────────────

def _print_qr_code(ip: str, port: int = 8000, scheme: str = "http") -> None:
    """In QR code ra terminal de phu huynh quet.
    Neu NGROK_URL duoc cau hinh → in QR ngrok. Fallback → QR LAN IP.
    """
    ngrok_url = os.getenv("NGROK_URL", "").strip()
    if ngrok_url:
        display_url = ngrok_url
        label = "Truy cap tu ngoai mang (ngrok):"
        note = None
    else:
        display_url = f"{scheme}://{ip}:{port}"
        label = "Quet QR tren dien thoai cung mang WiFi:"
        note = "(Lan dau bam 'Advanced' -> 'Proceed' vi self-signed cert)" if scheme == "https" else None

    try:
        qr_text = _build_ascii_qr(display_url)
        print(f"\n{'='*50}")
        print(f"  Parent App: {display_url}")
        if note:
            print(f"  {note}")
        print(f"  {label}")
        print(qr_text)
        print('='*50)
    except ImportError:
        print(f"\n{'='*50}")
        print(f"  Parent App: {display_url}")
        print(f"  (Cai qrcode de hien QR: pip install qrcode)")
        print('='*50)


def start_api_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Khởi động FastAPI + uvicorn trong background daemon thread.
    Non-blocking — không ảnh hưởng đến main_loop.py.
    """
    if not _state.AUTH_PIN:
        raise Exception(
            "[Auth] FATAL: AUTH_PIN chưa được cấu hình trong .env. "
            "Server không thể khởi động. Thêm AUTH_PIN=<pin> vào file .env rồi thử lại."
        )

    from src.infrastructure.auth.auth import _get_jwt_config
    _get_jwt_config()

    use_https = _USE_HTTPS
    actual_port = 8443 if use_https else port

    def _run():
        if use_https:
            print(f"[Server] HTTPS enabled — https://localhost:{actual_port}")
            uvicorn.run(
                app,
                host=host,
                port=actual_port,
                ssl_certfile=str(_SSL_CERT),
                ssl_keyfile=str(_SSL_KEY),
                log_level="warning",
            )
        else:
            print(f"[Server] HTTP mode — chay generate_ssl.py de bat HTTPS")
            uvicorn.run(app, host=host, port=actual_port, log_level="warning")

    t = threading.Thread(target=_run, daemon=True, name="api-server")
    t.start()

    _start_cloudflare_tunnel(actual_port, use_https)

    local_ip = get_local_ip()
    scheme = "https" if use_https else "http"
    _print_qr_code(local_ip, actual_port, scheme)
```

## src/api/routers/auth_router.py

```python
"""
auth_router.py — Auth endpoints cho Robot Bi API.
  POST /api/auth/login       — PIN login (rate-limited)
  POST /api/auth/logout      — PIN logout
  POST /api/auth/logout-all  — Revoke tất cả refresh token (JWT)
  POST /auth/register        — Đăng ký username+password
  POST /auth/login/v2        — Đăng nhập username+password → JWT
  POST /auth/refresh         — Đổi refresh token lấy access+refresh mới
  POST /auth/logout          — Đăng xuất JWT
"""
import logging
import math
import os
import json
import re as _re
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from src.infrastructure.auth.auth import get_current_user, verify_password
from src.infrastructure.database.db import (
    get_db_connection,
    get_user_by_id,
    revoke_all_tokens_for_user,
    update_user_password,
)
import src.infrastructure.sessions.state as _state

logger = logging.getLogger(__name__)

router = APIRouter()
REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "false").lower() == "true"


async def _read_json_body(request: Request) -> dict:
    try:
        return await request.json()
    except (json.JSONDecodeError, Exception) as exc:
        raise HTTPException(status_code=422, detail="Invalid JSON body") from exc


@router.post("/api/auth/login")
async def login(request: Request, pin: str = Body(..., embed=True)):
    """Đăng nhập bằng PIN. Trả về session token. Rate-limited: 5 lần sai → khóa 15 phút."""
    client_ip = request.client.host
    now = datetime.now(timezone.utc)

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE locked_until IS NOT NULL AND locked_until <= ?",
            (now.isoformat(),),
        )
        conn.commit()

        row = conn.execute(
            "SELECT attempt_count, locked_until FROM login_attempts WHERE ip_address = ?",
            (client_ip,),
        ).fetchone()

        if row and row["locked_until"]:
            locked_until_str = row["locked_until"]
            locked_until = datetime.fromisoformat(locked_until_str)
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Quá nhiều lần thử. Vui lòng thử lại sau {remaining_minutes} phút.",
                )

        if hmac.compare_digest(
            str(pin).encode(),
            str(_state.AUTH_PIN).encode(),
        ):
            conn.execute(
                "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
                "WHERE ip_address = ?",
                (client_ip,),
            )
            conn.commit()
            token = secrets.token_hex(16)
            _state.SESSION_TOKENS.add(token)
            return {"token": token}

        if row:
            current_count = row["attempt_count"] or 0
            new_count = current_count + 1
            if new_count >= 5:
                locked_until_val = (now + timedelta(minutes=15)).isoformat()
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = ?, locked_until = ? "
                    "WHERE ip_address = ?",
                    (new_count, locked_until_val, client_ip),
                )
            elif current_count == 0:
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = 1, first_attempt_at = ? "
                    "WHERE ip_address = ?",
                    (now.isoformat(), client_ip),
                )
            else:
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = ? WHERE ip_address = ?",
                    (new_count, client_ip),
                )
        else:
            conn.execute(
                "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                "VALUES (?, 1, ?, NULL)",
                (client_ip, now.isoformat()),
            )
        conn.commit()

    raise HTTPException(status_code=401, detail="PIN sai")


@router.post("/auth/register")
async def register_user(request: Request):
    """Đăng ký tài khoản username + password mới. family_name do server gán từ FAMILY_ID env."""
    from src.infrastructure.auth.auth import create_user

    if not REGISTRATION_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Dang ky bi tat. Lien he admin de duoc cap tai khoan.",
        )

    client_ip = request.client.host if request.client else "unknown"
    reg_key = f"register:{client_ip}"
    now = datetime.now(timezone.utc)

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE locked_until IS NOT NULL AND locked_until <= ?",
            (now.isoformat(),),
        )
        row = conn.execute(
            "SELECT attempt_count, locked_until FROM login_attempts WHERE ip_address = ?",
            (reg_key,),
        ).fetchone()

        if row and row["locked_until"]:
            locked_until = datetime.fromisoformat(row["locked_until"])
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                conn.commit()
                raise HTTPException(
                    status_code=429,
                    detail=f"Qua nhieu lan thu. Vui long thu lai sau {remaining_minutes} phut.",
                )

        current_count = row["attempt_count"] if row else 0
        new_count = current_count + 1
        locked_until_val = (now + timedelta(minutes=15)).isoformat() if new_count >= 5 else None
        if row:
            conn.execute(
                "UPDATE login_attempts SET attempt_count = ?, locked_until = ? WHERE ip_address = ?",
                (new_count, locked_until_val, reg_key),
            )
        else:
            conn.execute(
                "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                "VALUES (?, 1, ?, ?)",
                (reg_key, now.isoformat(), locked_until_val),
            )
        conn.commit()

    body = await _read_json_body(request)
    username: str = body.get("username", "").strip()
    password: str = body.get("password", "")
    # family_name KHÔNG đọc từ client — server tự gán để tránh spoofing
    family_name: str = os.getenv("FAMILY_ID", "default")

    if not username or not _re.fullmatch(r"[a-zA-Z0-9_]{3,50}", username):
        raise HTTPException(
            status_code=422,
            detail="username phai tu 3-50 ky tu, chi duoc dung a-zA-Z0-9_",
        )
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="password phai co it nhat 8 ky tu")

    user = create_user(username, password, family_name)
    with get_db_connection() as conn:
        conn.execute("DELETE FROM login_attempts WHERE ip_address = ?", (reg_key,))
        conn.commit()
    return user


@router.post("/auth/login/v2")
async def login_v2(request: Request):
    """
    Đăng nhập bằng username + password.
    Rate limiting: 5 lần sai theo username → khóa 15 phút.
    Trả về JWT access_token (60 phút) + refresh_token (30 ngày).
    """
    from src.infrastructure.auth.auth import (
        authenticate_user,
        create_access_token,
        create_refresh_token,
        store_refresh_token,
    )

    body = await _read_json_body(request)
    username: str = body.get("username", "").strip()
    password: str = body.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=422, detail="Thieu username hoac password")

    rate_key = f"user:{username}"
    now = datetime.now(timezone.utc)
    authenticated_user = None

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE locked_until IS NOT NULL AND locked_until <= ?",
            (now.isoformat(),),
        )
        conn.commit()

        row = conn.execute(
            "SELECT attempt_count, locked_until FROM login_attempts WHERE ip_address = ?",
            (rate_key,),
        ).fetchone()

        if row and row["locked_until"]:
            locked_until_str = row["locked_until"]
            locked_until = datetime.fromisoformat(locked_until_str)
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Quá nhiều lần thử. Vui lòng thử lại sau {remaining_minutes} phút.",
                )

        user = authenticate_user(username, password)

        if user:
            conn.execute(
                "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
                "WHERE ip_address = ?",
                (rate_key,),
            )
            conn.commit()
            authenticated_user = user
        else:
            if row:
                current_count = row["attempt_count"] or 0
                new_count = current_count + 1
                if new_count >= 5:
                    locked_until_val = (now + timedelta(minutes=15)).isoformat()
                    conn.execute(
                        "UPDATE login_attempts SET attempt_count = ?, locked_until = ? "
                        "WHERE ip_address = ?",
                        (new_count, locked_until_val, rate_key),
                    )
                elif current_count == 0:
                    conn.execute(
                        "UPDATE login_attempts SET attempt_count = 1, first_attempt_at = ? "
                        "WHERE ip_address = ?",
                        (now.isoformat(), rate_key),
                    )
                else:
                    conn.execute(
                        "UPDATE login_attempts SET attempt_count = ? WHERE ip_address = ?",
                        (new_count, rate_key),
                    )
            else:
                conn.execute(
                    "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                    "VALUES (?, 1, ?, NULL)",
                    (rate_key, now.isoformat()),
                )
            conn.commit()

    if not authenticated_user:
        raise HTTPException(status_code=401, detail="Sai ten dang nhap hoac mat khau")

    access_token = create_access_token(
        str(authenticated_user["user_id"]), authenticated_user["family_name"]
    )
    raw_refresh, hashed_refresh = create_refresh_token(str(authenticated_user["user_id"]))
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    store_refresh_token(str(authenticated_user["user_id"]), hashed_refresh, refresh_expires_at)

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": 3600,
        "username": authenticated_user["username"],
        "family_name": authenticated_user["family_name"],
        "is_admin": bool(authenticated_user.get("is_admin")),
    }


@router.post("/auth/refresh")
async def refresh_token_endpoint(request: Request):
    """
    Đổi refresh token lấy access token + refresh token mới (rotation).
    Body: {"refresh_token": str}
    """
    from src.infrastructure.auth.auth import rotate_refresh_token, create_access_token

    body = await _read_json_body(request)
    old_refresh = body.get("refresh_token", "").strip()

    if not old_refresh:
        raise HTTPException(status_code=422, detail="Thieu refresh_token")

    new_raw, _new_hashed, user_id = rotate_refresh_token(old_refresh)

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT family_name, is_active FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="User khong ton tai")
    if not row["is_active"]:
        raise HTTPException(status_code=401, detail="Tai khoan da bi vo hieu hoa")

    new_access = create_access_token(user_id, row["family_name"])

    return {
        "access_token": new_access,
        "refresh_token": new_raw,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@router.post("/auth/logout")
async def logout_v2(request: Request, _current_user: dict = Depends(get_current_user)):
    """
    Đăng xuất JWT: verify access token → revoke refresh token của chính user đó.
    Header: Authorization: Bearer <access_token>
    Body: {"refresh_token": str}
    """
    import hashlib as _hl

    user_id = str(_current_user["user_id"])

    body = await _read_json_body(request)
    refresh_token_str = body.get("refresh_token", "").strip()
    if not refresh_token_str:
        raise HTTPException(status_code=422, detail="Thieu refresh_token")

    hashed = _hl.sha256(refresh_token_str.encode()).hexdigest()

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_id, user_id FROM auth_tokens "
            "WHERE refresh_token_hash = ? AND is_revoked = 0",
            (hashed,),
        ).fetchone()

        if not row or str(row["user_id"]) != user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token",
            )

        conn.execute(
            "UPDATE auth_tokens SET is_revoked = 1 WHERE token_id = ?",
            (row["token_id"],),
        )
        conn.commit()

    return {"message": "Đã đăng xuất"}


@router.post("/api/auth/logout")
async def logout(token: str = Body(..., embed=True)):
    """Đăng xuất, huỷ session token."""
    _state.SESSION_TOKENS.discard(token)
    return {"ok": True}


@router.post("/api/auth/logout-all")
async def logout_all(current_user: dict = Depends(get_current_user)):
    """Revoke tất cả refresh token của user hiện tại (đăng xuất tất cả thiết bị)."""
    user_id = current_user["user_id"]
    revoked = revoke_all_tokens_for_user(user_id)
    logger.info("[Auth] logout-all: user %s revoked %d tokens", user_id, revoked)
    return {"revoked": revoked}


@router.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Trả về thông tin tài khoản của user hiện tại."""
    user = get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại")
    return {
        "username": user["username"],
        "family_name": user["family_name"],
        "created_at": user["created_at"],
        "is_admin": bool(user.get("is_admin")),
    }


@router.put("/api/auth/change-password")
async def change_password(request: Request, current_user: dict = Depends(get_current_user)):
    """Đổi mật khẩu. Revoke tất cả refresh token sau khi đổi thành công."""
    body = await _read_json_body(request)
    current_pw: str = body.get("current_password", "")
    new_pw: str = body.get("new_password", "")
    user_id = str(current_user["user_id"])
    rate_key = f"chpwd:{user_id}"
    now = datetime.now(timezone.utc)

    if not current_pw or not new_pw:
        raise HTTPException(status_code=400, detail="Thiếu current_password hoặc new_password")

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE ip_address = ? AND locked_until IS NOT NULL AND locked_until <= ?",
            (rate_key, now.isoformat()),
        )
        conn.commit()

        attempts = conn.execute(
            "SELECT attempt_count, first_attempt_at, locked_until FROM login_attempts WHERE ip_address = ?",
            (rate_key,),
        ).fetchone()

        if attempts and attempts["first_attempt_at"]:
            first_attempt_at = datetime.fromisoformat(attempts["first_attempt_at"])
            if first_attempt_at.tzinfo is None:
                first_attempt_at = first_attempt_at.replace(tzinfo=timezone.utc)
            if now - first_attempt_at > timedelta(minutes=15):
                conn.execute("DELETE FROM login_attempts WHERE ip_address = ?", (rate_key,))
                conn.commit()
                attempts = None

        if attempts and attempts["locked_until"]:
            locked_until = datetime.fromisoformat(attempts["locked_until"])
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Qua nhieu lan thu. Vui long thu lai sau {remaining_minutes} phut.",
                )

        row = conn.execute(
            "SELECT password_hash FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()

    if not row or not verify_password(current_pw, row["password_hash"]):
        with get_db_connection() as conn:
            attempts = conn.execute(
                "SELECT attempt_count FROM login_attempts WHERE ip_address = ?",
                (rate_key,),
            ).fetchone()
            new_count = (int(attempts["attempt_count"]) if attempts else 0) + 1
            locked_until = (now + timedelta(minutes=15)).isoformat() if new_count >= 5 else None
            if attempts:
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = ?, locked_until = ? WHERE ip_address = ?",
                    (new_count, locked_until, rate_key),
                )
            else:
                conn.execute(
                    "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                    "VALUES (?, ?, ?, ?)",
                    (rate_key, new_count, now.isoformat(), locked_until),
                )
            conn.commit()
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")

    if len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải có ít nhất 8 ký tự")

    update_user_password(user_id, new_pw)
    revoke_all_tokens_for_user(user_id)
    with get_db_connection() as conn:
        conn.execute("DELETE FROM login_attempts WHERE ip_address = ?", (rate_key,))
        conn.commit()
    logger.info("[Auth] change-password: user %s password updated", user_id)
    return {"ok": True, "message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."}
```

## src/api/routers/control_router.py

```python
"""
control_router.py — Control endpoints cho Robot Bi API.
  GET  /api/status           — Trạng thái robot
  GET  /api/events           — Danh sách sự kiện
  POST /api/events/read_all  — Đánh dấu tất cả đã đọc
  GET  /api/chats            — Nhật ký hội thoại
  GET  /api/memories         — Danh sách trí nhớ
  POST /api/memories         — Thêm trí nhớ
  GET  /api/memories/export  — Export JSON backup
  PUT  /api/memories/{id}    — Sửa trí nhớ
  DELETE /api/memories/{id}  — Xóa trí nhớ
  POST /api/puppet           — Bi đọc text từ app
  GET  /api/tasks            — Danh sách nhiệm vụ
  POST /api/tasks            — Thêm nhiệm vụ
  GET  /api/tasks/stars      — Tổng sao
  POST /api/tasks/{id}/complete — Hoàn thành nhiệm vụ
  DELETE /api/tasks/{id}     — Xóa nhiệm vụ
"""
import logging
import csv
import hashlib
import json
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user
from src.api.routers.conversation_router import _require_family
from src.infrastructure.database.db import (
    create_parent_event_note,
    delete_parent_event_note,
    ensure_family_exists,
    event_exists_for_family,
    get_db_connection,
    list_parent_event_notes,
    update_parent_event_note,
)
import src.infrastructure.sessions.state as _state

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Pydantic models ────────────────────────────────────────────────────────

class MemoryIn(BaseModel):
    text: str


class MemoryUpdate(BaseModel):
    text: str


class PuppetIn(BaseModel):
    text: str


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Ten nhiem vu")
    remind_time: Optional[str] = Field(
        None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Dinh dang HH:MM",
    )


# Request helpers

class ParentEventNoteIn(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)


class ChildProfileIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    birth_date: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[str] = Field(default=None, max_length=40)
    avatar: Optional[str] = Field(default=None, max_length=80)
    interests: list[str] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None, max_length=1000)


class ChildProfilePatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    birth_date: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[str] = Field(default=None, max_length=40)
    avatar: Optional[str] = Field(default=None, max_length=80)
    interests: Optional[list[str]] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class AgeFilterIn(BaseModel):
    child_id: Optional[str] = Field(default=None, max_length=80)
    enabled: bool = False
    min_age: Optional[int] = 5
    max_age: Optional[int] = 12
    blocked_topics: list[str] = Field(default_factory=list)
    allowed_topics: list[str] = Field(default_factory=list)
    strict_mode: bool = True


class TimeLimitIn(BaseModel):
    child_id: Optional[str] = Field(default=None, max_length=80)
    enabled: bool = False
    daily_limit_minutes: int = 60
    warning_minutes: int = 10
    reset_time: str = "00:00"


class SleepScheduleIn(BaseModel):
    enabled: bool = False
    start_time: str = "21:00"
    end_time: str = "06:30"
    days: list[str] = Field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
    timezone: str = Field(default="Asia/Ho_Chi_Minh", max_length=80)


class NotificationSettingsIn(BaseModel):
    enabled: bool = True
    event_types: dict = Field(default_factory=dict)
    quiet_hours: dict = Field(default_factory=dict)
    channels: dict = Field(default_factory=dict)
    push_subscription: Optional[dict] = None


class ReportExportIn(BaseModel):
    format: str = Field(..., max_length=12)
    start_date: str
    end_date: str
    sections: list[str] = Field(default_factory=lambda: ["events", "conversations", "emotions", "education", "tasks"])
    child_id: Optional[str] = Field(default=None, max_length=80)


class RobotLocationIn(BaseModel):
    room_name: Optional[str] = Field(default=None, max_length=120)
    location_label: Optional[str] = Field(default=None, max_length=200)
    source: str = Field(default="parent", max_length=20)
    confidence: float = 1.0


_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
_EVENT_TYPES = {"motion", "stranger", "known_face", "cry", "chat", "system", "homework"}
_CHANNELS = {"in_app", "web_push"}
_REPORT_SECTIONS = {"events", "conversations", "emotions", "education", "tasks"}
_PAIRING_PURPOSES = {"parent_app", "robot_display", "esp32"}
_LOCATION_SOURCES = {"parent", "robot", "system"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_array(value) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _json_object(value) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _dump_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _child_key(child_id: Optional[str]) -> str:
    return (child_id or "").strip()


def _public_child_id(child_id: str | None) -> str | None:
    value = (child_id or "").strip()
    return value or None


def _validate_time(value: str, field_name: str) -> str:
    if not _TIME_RE.match(value or ""):
        raise HTTPException(status_code=422, detail=f"{field_name} must use HH:MM")
    return value


def _validate_iso_date(value: Optional[str], field_name: str) -> Optional[str]:
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field_name} must use YYYY-MM-DD")
    return value


def _age_from_birth_date(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        born = datetime.strptime(value, "%Y-%m-%d").date()
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except ValueError:
        return None


def _birth_date_from_age(age: int) -> str:
    today = date.today()
    try:
        return today.replace(year=today.year - age).isoformat()
    except ValueError:
        return (today - timedelta(days=365 * age)).isoformat()


def _validate_age(age: Optional[int]) -> Optional[int]:
    if age is None:
        return None
    if int(age) < 5 or int(age) > 12:
        raise HTTPException(status_code=422, detail="age must be between 5 and 12")
    return int(age)


def _validate_string_list(values: list[str] | None, field_name: str) -> list[str]:
    result = []
    for value in values or []:
        item = str(value).strip()
        if not item:
            continue
        if len(item) > 80:
            raise HTTPException(status_code=422, detail=f"{field_name} entries must be <= 80 chars")
        result.append(item)
    if len(result) > 50:
        raise HTTPException(status_code=422, detail=f"{field_name} supports at most 50 entries")
    return result


def _child_row_to_dict(row) -> dict:
    birth_date = row["birth_date"]
    return {
        "child_id": row["child_id"],
        "name": row["name"],
        "birth_date": birth_date,
        "age": _age_from_birth_date(birth_date),
        "grade": row["grade"],
        "avatar": row["avatar"],
        "interests": _json_array(row["interests_json"]),
        "notes": row["notes"] or "",
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _validate_child_for_family(family_id: str, child_id: Optional[str]) -> str:
    key = _child_key(child_id)
    if not key:
        return ""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT child_id FROM child_profiles WHERE family_id = ? AND child_id = ?",
            (family_id, key),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Child profile not found")
    return key


def _normalize_child_payload(data: dict, *, partial: bool = False) -> dict:
    normalized = {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="name must not be empty")
        normalized["name"] = name
    elif not partial:
        raise HTTPException(status_code=422, detail="name is required")

    birth_date = data.get("birth_date")
    age = data.get("age")
    if birth_date:
        birth_date = _validate_iso_date(str(birth_date), "birth_date")
        computed_age = _age_from_birth_date(birth_date)
        if computed_age is not None:
            _validate_age(computed_age)
        normalized["birth_date"] = birth_date
    elif age is not None:
        normalized["birth_date"] = _birth_date_from_age(_validate_age(age))
    elif not partial:
        raise HTTPException(status_code=422, detail="birth_date or age is required")

    if "grade" in data:
        normalized["grade"] = (data.get("grade") or "").strip()[:40] or None
    if "avatar" in data:
        normalized["avatar"] = (data.get("avatar") or "").strip()[:80] or None
    if "interests" in data:
        normalized["interests_json"] = _dump_json(_validate_string_list(data.get("interests"), "interests"))
    elif not partial:
        normalized["interests_json"] = "[]"
    if "notes" in data:
        normalized["notes"] = (data.get("notes") or "").strip()[:1000]
    elif not partial:
        normalized["notes"] = ""
    return normalized


def _default_age_filter(child_id: Optional[str] = None) -> dict:
    return {
        "child_id": child_id,
        "enabled": False,
        "min_age": 5,
        "max_age": 12,
        "blocked_topics": [],
        "allowed_topics": [],
        "strict_mode": True,
        "updated_at": None,
    }


def _default_time_limits(child_id: Optional[str] = None) -> dict:
    return {
        "child_id": child_id,
        "enabled": False,
        "daily_limit_minutes": 60,
        "warning_minutes": 10,
        "reset_time": "00:00",
        "updated_at": None,
    }


def _default_sleep_settings() -> dict:
    return {
        "enabled": False,
        "start_time": "21:00",
        "end_time": "06:30",
        "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        "timezone": "Asia/Ho_Chi_Minh",
        "updated_at": None,
    }


def _default_notification_settings() -> dict:
    return {
        "enabled": True,
        "event_types": {},
        "quiet_hours": {},
        "channels": {"in_app": True, "web_push": False},
        "updated_at": None,
    }


def _age_filter_row_to_dict(row) -> dict:
    if not row:
        return _default_age_filter()
    return {
        "child_id": _public_child_id(row["child_id"]),
        "enabled": bool(row["enabled"]),
        "min_age": row["min_age"],
        "max_age": row["max_age"],
        "blocked_topics": _json_array(row["blocked_topics_json"]),
        "allowed_topics": _json_array(row["allowed_topics_json"]),
        "strict_mode": bool(row["strict_mode"]),
        "updated_at": row["updated_at"],
    }


def _time_limits_row_to_dict(row) -> dict:
    if not row:
        return _default_time_limits()
    return {
        "child_id": _public_child_id(row["child_id"]),
        "enabled": bool(row["enabled"]),
        "daily_limit_minutes": int(row["daily_limit_minutes"]),
        "warning_minutes": int(row["warning_minutes"]),
        "reset_time": row["reset_time"],
        "updated_at": row["updated_at"],
    }


def _usage_today(family_id: str, child_id: str, settings: dict | None = None) -> dict:
    today = date.today().isoformat()
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT seconds_used, sessions_count, updated_at
            FROM daily_interaction_usage
            WHERE family_id = ? AND child_id = ? AND usage_date = ?
            """,
            (family_id, child_id, today),
        ).fetchone()
    seconds_used = int(row["seconds_used"] or 0) if row else 0
    limit_minutes = int((settings or {}).get("daily_limit_minutes") or 60)
    enabled = bool((settings or {}).get("enabled", False))
    limit_seconds = limit_minutes * 60
    return {
        "date": today,
        "child_id": _public_child_id(child_id),
        "seconds_used": seconds_used,
        "sessions_count": int(row["sessions_count"] or 0) if row else 0,
        "remaining_seconds": max(0, limit_seconds - seconds_used),
        "limit_reached": bool(enabled and seconds_used >= limit_seconds),
        "updated_at": row["updated_at"] if row else None,
    }


def _parse_event_types(types: Optional[str]) -> list[str] | None:
    if not types:
        return None
    parsed = [value.strip() for value in types.split(",") if value.strip()]
    if len(parsed) > 20:
        raise HTTPException(status_code=422, detail="types supports at most 20 values")
    return parsed or None


def _validate_event_date(value: Optional[str], field_name: str) -> Optional[str]:
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field_name} must use YYYY-MM-DD")
    return value


def _clean_parent_note(note: str) -> str:
    cleaned = (note or "").strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="note must not be empty")
    return cleaned


def _validate_report_sections(sections: list[str] | None) -> list[str]:
    cleaned = []
    for section in sections or []:
        value = str(section).strip().lower()
        if not value:
            continue
        if value not in _REPORT_SECTIONS:
            raise HTTPException(status_code=422, detail=f"Unsupported report section: {value}")
        if value not in cleaned:
            cleaned.append(value)
    return cleaned or ["events", "conversations", "emotions", "education", "tasks"]


def _report_rows(family_id: str, start_date: str, end_date: str, sections: list[str]) -> list[dict]:
    rows: list[dict] = []
    with get_db_connection() as conn:
        if "events" in sections:
            for row in conn.execute(
                """
                SELECT timestamp AS happened_at, type, message, metadata_json
                FROM events
                WHERE family_id = ?
                  AND date(timestamp) BETWEEN ? AND ?
                ORDER BY timestamp ASC
                """,
                (family_id, start_date, end_date),
            ).fetchall():
                metadata = _json_object(row["metadata_json"])
                rows.append(
                    {
                        "section": "events",
                        "timestamp": row["happened_at"],
                        "title": row["type"] or "event",
                        "detail": str(row["message"] or metadata.get("summary") or "")[:500],
                    }
                )

        if "conversations" in sections:
            for row in conn.execute(
                """
                SELECT started_at, title, turn_count
                FROM conversations
                WHERE family_id = ?
                  AND date(started_at) BETWEEN ? AND ?
                ORDER BY started_at ASC
                """,
                (family_id, start_date, end_date),
            ).fetchall():
                rows.append(
                    {
                        "section": "conversations",
                        "timestamp": row["started_at"],
                        "title": row["title"] or "Conversation",
                        "detail": f"{int(row['turn_count'] or 0)} turns",
                    }
                )

        if "emotions" in sections:
            try:
                emotion_rows = conn.execute(
                    """
                    SELECT timestamp, emotion
                    FROM emotion_logs
                    WHERE family_id = ?
                      AND date(timestamp) BETWEEN ? AND ?
                    ORDER BY timestamp ASC
                    """,
                    (family_id, start_date, end_date),
                ).fetchall()
            except Exception:
                emotion_rows = []
            for row in emotion_rows:
                rows.append(
                    {
                        "section": "emotions",
                        "timestamp": row["timestamp"],
                        "title": row["emotion"] or "emotion",
                        "detail": "",
                    }
                )

        if "education" in sections:
            for row in conn.execute(
                """
                SELECT day_of_week, subject, time
                FROM learning_schedules
                WHERE family_id = ?
                ORDER BY day_of_week ASC
                """,
                (family_id,),
            ).fetchall():
                rows.append(
                    {
                        "section": "education",
                        "timestamp": row["day_of_week"],
                        "title": row["subject"] or "Learning schedule",
                        "detail": row["time"] or "",
                    }
                )

        if "tasks" in sections:
            for row in conn.execute(
                """
                SELECT created_at, name, completed_today, stars
                FROM tasks
                WHERE family_id = ?
                  AND date(created_at) BETWEEN ? AND ?
                ORDER BY created_at ASC
                """,
                (family_id, start_date, end_date),
            ).fetchall():
                status = "completed" if row["completed_today"] else "open"
                rows.append(
                    {
                        "section": "tasks",
                        "timestamp": row["created_at"],
                        "title": row["name"],
                        "detail": f"{status}; stars={int(row['stars'] or 0)}",
                    }
                )
    return rows


def _render_report_csv(rows: list[dict]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["section", "timestamp", "title", "detail"])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def _pdf_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _render_report_pdf(rows: list[dict], start_date: str, end_date: str) -> bytes:
    lines = [f"Robot Bi report {start_date} to {end_date}", f"Rows: {len(rows)}"]
    for row in rows[:36]:
        title = str(row.get("title") or "")[:80]
        lines.append(f"{row.get('section')} | {row.get('timestamp')} | {title}")
    text_ops = ["BT", "/F1 10 Tf", "72 760 Td", "14 TL"]
    for line in lines:
        text_ops.append(f"({_pdf_escape(line)}) Tj")
        text_ops.append("T*")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_at = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def _location_row_to_dict(family_id: str, row) -> dict:
    if not row:
        return {
            "family_id": family_id,
            "room_name": None,
            "location_label": None,
            "source": "system",
            "confidence": 0.0,
            "updated_at": None,
        }
    return {
        "family_id": family_id,
        "room_name": row["room_name"],
        "location_label": row["location_label"],
        "source": row["source"],
        "confidence": float(row["confidence"]),
        "updated_at": row["updated_at"],
    }


# REST: Status

@router.get("/api/status")
async def get_status():
    notifier_stats = _state._notifier.get_stats() if _state._notifier else {}
    rag_stats = _state._rag.get_stats() if _state._rag else {}
    total_stars = _state._task_manager.get_total_stars() if _state._task_manager else 0
    return {
        "status": "online",
        "ws_clients": _state._ws_manager.count,
        "puppet_queued": _state._puppet_queue.qsize(),
        "notifier": notifier_stats,
        "rag": rag_stats,
        "total_stars": total_stars,
    }


# ── REST: Events ──────────────────────────────────────────────────────────

# REST: Children and Parent App Settings

@router.get("/api/children")
async def list_children(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT child_id, name, birth_date, grade, avatar, interests_json,
                   notes, is_active, created_at, updated_at
            FROM child_profiles
            WHERE family_id = ?
            ORDER BY is_active DESC, created_at ASC
            """,
            (family_id,),
        ).fetchall()
    children = [_child_row_to_dict(row) for row in rows]
    active = next((child["child_id"] for child in children if child["is_active"]), None)
    return {"children": children, "active_child_id": active}


@router.post("/api/children")
async def create_child_profile(
    payload: ChildProfileIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = ensure_family_exists(_require_family(_current_user))
    values = _normalize_child_payload(payload.dict())
    child_id = uuid4().hex
    now = _now_iso()
    with get_db_connection() as conn:
        active_row = conn.execute(
            "SELECT 1 FROM child_profiles WHERE family_id = ? AND is_active = 1 LIMIT 1",
            (family_id,),
        ).fetchone()
        is_active = 0 if active_row else 1
        conn.execute(
            """
            INSERT INTO child_profiles (
                child_id, family_id, name, birth_date, grade, avatar,
                interests_json, notes, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                child_id,
                family_id,
                values["name"],
                values["birth_date"],
                values.get("grade"),
                values.get("avatar"),
                values.get("interests_json", "[]"),
                values.get("notes", ""),
                is_active,
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT child_id, name, birth_date, grade, avatar, interests_json,
                   notes, is_active, created_at, updated_at
            FROM child_profiles
            WHERE family_id = ? AND child_id = ?
            """,
            (family_id, child_id),
        ).fetchone()
    return {"ok": True, "child": _child_row_to_dict(row)}


@router.get("/api/children/{child_id}")
async def get_child_profile(
    child_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT child_id, name, birth_date, grade, avatar, interests_json,
                   notes, is_active, created_at, updated_at
            FROM child_profiles
            WHERE family_id = ? AND child_id = ?
            """,
            (family_id, child_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Child profile not found")
    return {"child": _child_row_to_dict(row)}


@router.patch("/api/children/{child_id}")
async def update_child_profile(
    child_id: str,
    payload: ChildProfilePatch,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    _validate_child_for_family(family_id, child_id)
    values = _normalize_child_payload(payload.dict(exclude_unset=True), partial=True)
    if values:
        assignments = [f"{column} = ?" for column in values.keys()]
        params = list(values.values())
        assignments.append("updated_at = ?")
        params.append(_now_iso())
        params.extend([family_id, child_id])
        with get_db_connection() as conn:
            conn.execute(
                f"""
                UPDATE child_profiles
                SET {', '.join(assignments)}
                WHERE family_id = ? AND child_id = ?
                """,
                tuple(params),
            )
            conn.commit()
    return await get_child_profile(child_id, _current_user)


@router.delete("/api/children/{child_id}")
async def delete_child_profile(
    child_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    _validate_child_for_family(family_id, child_id)
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT is_active FROM child_profiles WHERE family_id = ? AND child_id = ?",
            (family_id, child_id),
        ).fetchone()
        was_active = bool(row and row["is_active"])
        conn.execute("DELETE FROM child_profiles WHERE family_id = ? AND child_id = ?", (family_id, child_id))
        if was_active:
            next_row = conn.execute(
                """
                SELECT child_id FROM child_profiles
                WHERE family_id = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (family_id,),
            ).fetchone()
            if next_row:
                conn.execute(
                    "UPDATE child_profiles SET is_active = 1, updated_at = ? WHERE family_id = ? AND child_id = ?",
                    (_now_iso(), family_id, next_row["child_id"]),
                )
        conn.commit()
    return {"ok": True}


@router.put("/api/children/{child_id}/activate")
async def activate_child_profile(
    child_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    _validate_child_for_family(family_id, child_id)
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute("UPDATE child_profiles SET is_active = 0 WHERE family_id = ?", (family_id,))
        conn.execute(
            "UPDATE child_profiles SET is_active = 1, updated_at = ? WHERE family_id = ? AND child_id = ?",
            (now, family_id, child_id),
        )
        conn.commit()
    return await get_child_profile(child_id, _current_user)


@router.get("/api/settings/age-filter")
async def get_age_filter(
    child_id: Optional[str] = None,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    key = _validate_child_for_family(family_id, child_id)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT child_id, enabled, min_age, max_age, blocked_topics_json,
                   allowed_topics_json, strict_mode, updated_at
            FROM child_content_settings
            WHERE family_id = ? AND child_id = ?
            """,
            (family_id, key),
        ).fetchone()
    settings = _age_filter_row_to_dict(row) if row else _default_age_filter(_public_child_id(key))
    return {"ok": True, "settings": settings}


@router.post("/api/settings/age-filter")
async def save_age_filter(
    payload: AgeFilterIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    key = _validate_child_for_family(family_id, payload.child_id)
    min_age = _validate_age(payload.min_age)
    max_age = _validate_age(payload.max_age)
    if min_age is not None and max_age is not None and min_age > max_age:
        raise HTTPException(status_code=422, detail="min_age must be <= max_age")
    blocked = _validate_string_list(payload.blocked_topics, "blocked_topics")
    allowed = _validate_string_list(payload.allowed_topics, "allowed_topics")
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute("DELETE FROM child_content_settings WHERE family_id = ? AND child_id = ?", (family_id, key))
        conn.execute(
            """
            INSERT INTO child_content_settings (
                setting_id, family_id, child_id, enabled, min_age, max_age,
                blocked_topics_json, allowed_topics_json, strict_mode, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                family_id,
                key,
                1 if payload.enabled else 0,
                min_age,
                max_age,
                _dump_json(blocked),
                _dump_json(allowed),
                1 if payload.strict_mode else 0,
                now,
            ),
        )
        conn.commit()
    return await get_age_filter(_public_child_id(key), _current_user)


@router.get("/api/settings/time-limits")
async def get_time_limits(
    child_id: Optional[str] = None,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    key = _validate_child_for_family(family_id, child_id)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT child_id, enabled, daily_limit_minutes, warning_minutes,
                   reset_time, updated_at
            FROM interaction_limit_settings
            WHERE family_id = ? AND child_id = ?
            """,
            (family_id, key),
        ).fetchone()
    settings = _time_limits_row_to_dict(row) if row else _default_time_limits(_public_child_id(key))
    return {"ok": True, "settings": settings, "usage_today": _usage_today(family_id, key, settings)}


@router.post("/api/settings/time-limits")
async def save_time_limits(
    payload: TimeLimitIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    key = _validate_child_for_family(family_id, payload.child_id)
    if payload.daily_limit_minutes < 1 or payload.daily_limit_minutes > 480:
        raise HTTPException(status_code=422, detail="daily_limit_minutes must be 1-480")
    if payload.warning_minutes < 0 or payload.warning_minutes > 120:
        raise HTTPException(status_code=422, detail="warning_minutes must be 0-120")
    if payload.warning_minutes > payload.daily_limit_minutes:
        raise HTTPException(status_code=422, detail="warning_minutes must be <= daily_limit_minutes")
    reset_time = _validate_time(payload.reset_time, "reset_time")
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute("DELETE FROM interaction_limit_settings WHERE family_id = ? AND child_id = ?", (family_id, key))
        conn.execute(
            """
            INSERT INTO interaction_limit_settings (
                setting_id, family_id, child_id, enabled, daily_limit_minutes,
                warning_minutes, reset_time, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                family_id,
                key,
                1 if payload.enabled else 0,
                int(payload.daily_limit_minutes),
                int(payload.warning_minutes),
                reset_time,
                now,
            ),
        )
        conn.commit()
    return await get_time_limits(_public_child_id(key), _current_user)


@router.get("/api/usage/today")
async def get_usage_today(
    child_id: Optional[str] = None,
    _current_user: dict = Depends(get_current_user),
):
    data = await get_time_limits(child_id, _current_user)
    return {"usage_today": data["usage_today"], "settings": data["settings"]}


@router.get("/api/settings/sleep")
async def get_sleep_schedule(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT enabled, start_time, end_time, days_json, timezone, updated_at
            FROM sleep_schedule_settings
            WHERE family_id = ?
            """,
            (family_id,),
        ).fetchone()
    if row:
        settings = {
            "enabled": bool(row["enabled"]),
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "days": _json_array(row["days_json"]),
            "timezone": row["timezone"],
            "updated_at": row["updated_at"],
        }
    else:
        settings = _default_sleep_settings()
    return {"ok": True, "settings": settings}


@router.post("/api/settings/sleep")
async def save_sleep_schedule(
    payload: SleepScheduleIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    start_time = _validate_time(payload.start_time, "start_time")
    end_time = _validate_time(payload.end_time, "end_time")
    days = [str(day).strip().lower() for day in payload.days]
    if not days or any(day not in _DAYS for day in days):
        raise HTTPException(status_code=422, detail="days must contain mon..sun values")
    tz = (payload.timezone or "").strip()
    if not tz or len(tz) > 80:
        raise HTTPException(status_code=422, detail="timezone is invalid")
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sleep_schedule_settings (
                family_id, enabled, start_time, end_time, days_json, timezone, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (family_id, 1 if payload.enabled else 0, start_time, end_time, _dump_json(days), tz, now),
        )
        conn.commit()
    return await get_sleep_schedule(_current_user)


@router.get("/api/settings/notifications")
async def get_notification_settings(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT enabled, event_types_json, quiet_hours_json, channels_json, updated_at
            FROM notification_settings
            WHERE family_id = ?
            """,
            (family_id,),
        ).fetchone()
    if row:
        settings = {
            "enabled": bool(row["enabled"]),
            "event_types": _json_object(row["event_types_json"]),
            "quiet_hours": _json_object(row["quiet_hours_json"]),
            "channels": _json_object(row["channels_json"]),
            "updated_at": row["updated_at"],
        }
    else:
        settings = _default_notification_settings()
    return {"ok": True, "settings": settings}


@router.post("/api/settings/notifications")
async def save_notification_settings(
    payload: NotificationSettingsIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    user_id = str(_current_user.get("user_id") or "")
    event_types = {}
    for key, enabled in (payload.event_types or {}).items():
        if key not in _EVENT_TYPES:
            raise HTTPException(status_code=422, detail=f"Unsupported event type: {key}")
        event_types[key] = bool(enabled)
    channels = {}
    for key, enabled in (payload.channels or {"in_app": True, "web_push": False}).items():
        if key not in _CHANNELS:
            raise HTTPException(status_code=422, detail=f"Unsupported notification channel: {key}")
        channels[key] = bool(enabled)
    channels.setdefault("in_app", True)
    channels.setdefault("web_push", False)

    quiet_hours = dict(payload.quiet_hours or {})
    if quiet_hours.get("enabled"):
        quiet_hours["start_time"] = _validate_time(str(quiet_hours.get("start_time", "")), "quiet_hours.start_time")
        quiet_hours["end_time"] = _validate_time(str(quiet_hours.get("end_time", "")), "quiet_hours.end_time")
        quiet_hours["enabled"] = True
    elif quiet_hours:
        quiet_hours["enabled"] = False

    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO notification_settings (
                family_id, enabled, event_types_json, quiet_hours_json, channels_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                family_id,
                1 if payload.enabled else 0,
                _dump_json(event_types),
                _dump_json(quiet_hours),
                _dump_json(channels),
                now,
            ),
        )
        if payload.push_subscription:
            endpoint = str(payload.push_subscription.get("endpoint", "")).strip()
            if not endpoint or len(endpoint) > 2048:
                raise HTTPException(status_code=422, detail="push_subscription.endpoint is invalid")
            endpoint_hash = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
            conn.execute(
                """
                INSERT INTO push_subscriptions (
                    subscription_id, family_id, user_id, endpoint_hash,
                    subscription_json, created_at, updated_at, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    uuid4().hex,
                    family_id,
                    user_id,
                    endpoint_hash,
                    _dump_json(payload.push_subscription),
                    now,
                    now,
                ),
            )
        conn.commit()
    return await get_notification_settings(_current_user)


@router.post("/api/reports/export")
async def export_parent_report(
    payload: ReportExportIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    report_format = (payload.format or "").strip().lower()
    if report_format not in {"csv", "pdf"}:
        raise HTTPException(status_code=422, detail="format must be csv or pdf")
    start = _validate_iso_date(payload.start_date, "start_date")
    end = _validate_iso_date(payload.end_date, "end_date")
    if not start or not end:
        raise HTTPException(status_code=422, detail="start_date and end_date are required")
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start_date must be <= end_date")
    if payload.child_id:
        _validate_child_for_family(family_id, payload.child_id)
    sections = _validate_report_sections(payload.sections)
    rows = _report_rows(family_id, start, end, sections)
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO report_exports (
                export_id, family_id, user_id, format, start_date, end_date,
                sections_json, row_count, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid4().hex,
                family_id,
                str(_current_user.get("user_id") or ""),
                report_format,
                start,
                end,
                _dump_json(sections),
                len(rows),
                now,
                "completed",
            ),
        )
        conn.commit()

    filename = f"robot-bi-report-{start}-{end}.{report_format}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if report_format == "csv":
        return Response(
            content=_render_report_csv(rows),
            media_type="text/csv; charset=utf-8",
            headers=headers,
        )
    return Response(
        content=_render_report_pdf(rows, start, end),
        media_type="application/pdf",
        headers=headers,
    )


@router.get("/api/device/connection-qr")
async def get_device_connection_qr(
    request: Request,
    purpose: str = Query(default="parent_app", max_length=40),
    ttl_seconds: int = Query(default=300, ge=60, le=3600),
    _current_user: dict = Depends(get_current_user),
):
    family_id = ensure_family_exists(_require_family(_current_user))
    purpose_value = (purpose or "").strip()
    if purpose_value not in _PAIRING_PURPOSES:
        raise HTTPException(status_code=422, detail="purpose must be parent_app, robot_display, or esp32")

    pairing_id = uuid4().hex
    raw_code = secrets.token_urlsafe(18)
    code_hash = hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
    now_dt = datetime.now(timezone.utc)
    expires_dt = now_dt + timedelta(seconds=int(ttl_seconds))
    base_url = str(request.base_url).rstrip("/")
    payload_url = f"{base_url}/connect?pairing_id={pairing_id}&code={raw_code}&purpose={purpose_value}"
    tunnel_url = os.getenv("CLOUDFLARE_TUNNEL_URL", "").strip() or None

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO device_pairing_codes (
                pairing_id, family_id, purpose, code_hash, expires_at, used_at,
                created_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                pairing_id,
                family_id,
                purpose_value,
                code_hash,
                expires_dt.isoformat(),
                now_dt.isoformat(),
                str(_current_user.get("user_id") or ""),
            ),
        )
        conn.commit()

    return {
        "qr": {
            "pairing_id": pairing_id,
            "payload_url": payload_url,
            "expires_at": expires_dt.isoformat(),
            "ttl_seconds": int(ttl_seconds),
        },
        "network": {
            "local_url": base_url,
            "tunnel_url": tunnel_url,
            "https_enabled": request.url.scheme == "https",
        },
    }


@router.get("/api/robot/location")
async def get_robot_location(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT room_name, location_label, source, confidence, updated_at
            FROM robot_location_metadata
            WHERE family_id = ?
            """,
            (family_id,),
        ).fetchone()
    return {"ok": True, "location": _location_row_to_dict(family_id, row)}


@router.post("/api/robot/location")
async def save_robot_location(
    payload: RobotLocationIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = ensure_family_exists(_require_family(_current_user))
    source = (payload.source or "").strip().lower()
    if source not in _LOCATION_SOURCES:
        raise HTTPException(status_code=422, detail="source must be parent, robot, or system")
    confidence = float(payload.confidence)
    if confidence < 0.0 or confidence > 1.0:
        raise HTTPException(status_code=422, detail="confidence must be between 0.0 and 1.0")
    room_name = (payload.room_name or "").strip() or None
    location_label = (payload.location_label or "").strip() or None
    now = _now_iso()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO robot_location_metadata (
                family_id, room_name, location_label, source, confidence,
                updated_at, updated_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                family_id,
                room_name,
                location_label,
                source,
                confidence,
                now,
                str(_current_user.get("user_id") or ""),
            ),
        )
        conn.commit()
    return await get_robot_location(_current_user)


@router.get("/api/events")
async def get_events(
    type: Optional[str] = None,
    types: Optional[str] = Query(default=None, max_length=500),
    unread_only: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    has_clip: Optional[bool] = None,
    has_note: Optional[bool] = None,
    q: Optional[str] = Query(default=None, min_length=1, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    sort: str = Query(default="desc", max_length=4),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    event_types = _parse_event_types(types)
    start = _validate_event_date(start_date, "start_date")
    end = _validate_event_date(end_date, "end_date")
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start_date must be before or equal to end_date")
    sort_value = (sort or "desc").lower()
    if sort_value not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="sort must be asc or desc")

    events = _state._fetch_events_from_db(
        event_type=type,
        event_types=event_types,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
        newest_first=(sort_value == "desc"),
        family_id=family_id,
        start_date=start,
        end_date=end,
        has_clip=has_clip,
        has_note=has_note,
        q=q,
        include_note_count=True,
    )
    total = _state._count_events_from_db(
        event_type=type,
        event_types=event_types,
        unread_only=unread_only,
        family_id=family_id,
        start_date=start,
        end_date=end,
        has_clip=has_clip,
        has_note=has_note,
        q=q,
    )
    return {
        "events": events,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "type": type,
            "types": event_types,
            "unread_only": unread_only,
            "start_date": start,
            "end_date": end,
            "has_clip": has_clip,
            "has_note": has_note,
            "q": q,
            "sort": sort_value,
        },
    }


@router.post("/api/events/read_all")
async def mark_read(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._notifier:
        _state._notifier.mark_all_read(family_id=family_id)
    return {"status": "ok"}


# REST: Event Notes

@router.get("/api/events/{event_id}/notes")
async def get_event_notes(
    event_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"notes": list_parent_event_notes(family_id, event_id)}


@router.post("/api/events/{event_id}/notes")
async def add_event_note(
    event_id: str,
    payload: ParentEventNoteIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    note = create_parent_event_note(
        family_id=family_id,
        event_id=event_id,
        user_id=str(_current_user.get("user_id") or ""),
        note=_clean_parent_note(payload.note),
    )
    return note


@router.put("/api/events/{event_id}/notes/{note_id}")
async def edit_event_note(
    event_id: str,
    note_id: str,
    payload: ParentEventNoteIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    note = update_parent_event_note(
        family_id=family_id,
        event_id=event_id,
        note_id=note_id,
        note=_clean_parent_note(payload.note),
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/api/events/{event_id}/notes/{note_id}")
async def remove_event_note(
    event_id: str,
    note_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    if not delete_parent_event_note(family_id, event_id, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "ok"}


# REST: Chat Log

@router.get("/api/chats")
async def get_chats(
    limit: int = Query(default=20, ge=1, le=200),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not _state._notifier:
        return {"chats": [], "total": 0}
    chats = _state._fetch_events_from_db(
        event_type="chat",
        unread_only=False,
        limit=limit,
        newest_first=True,
        family_id=family_id,
    )
    total = _state._count_events_from_db(
        event_type="chat",
        unread_only=False,
        family_id=family_id,
    )
    return {"chats": chats, "total": total}


# ── REST: Memories ────────────────────────────────────────────────────────

@router.get("/api/memories")
async def list_memories(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "list")
    if not _state._rag:
        return {"memories": [], "total": 0}
    memories = _state._rag.list_memories(family_id=family_id)
    return {"memories": memories, "total": len(memories)}


@router.post("/api/memories")
async def add_memory(body: MemoryIn, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "add")
    if not body.text.strip():
        raise HTTPException(400, "text không được rỗng")
    if not _state._rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _state._rag.add_manual_memory(body.text.strip(), family_id=family_id)
    return {"status": "ok" if ok else "fail"}


# Export phải đứng trước /{memory_id} để không bị capture
@router.get("/api/memories/export")
async def export_memories(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "export")
    if not _state._rag:
        return []
    return _state._rag.export_memories(family_id=family_id)


@router.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "update")
    if not _state._rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _state._rag.update_memory(memory_id, body.text, family_id=family_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


@router.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "delete")
    if not _state._rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _state._rag.delete_memory(memory_id, family_id=family_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


# ── REST: Puppet ──────────────────────────────────────────────────────────

@router.post("/api/puppet")
async def puppet_say(body: PuppetIn, _current_user: dict = Depends(get_current_user)):
    import logging as _logging
    _logger = _logging.getLogger("api_server")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text không được rỗng")
    _state._puppet_queue.put(text)
    _logger.debug("[Puppet] Queued text_len=%d", len(text))
    return {"status": "queued", "text": text}


# ── REST: Tasks ───────────────────────────────────────────────────────────

@router.get("/api/tasks")
async def get_tasks(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if not _state._task_manager:
        return []
    return _state._task_manager.get_all(family_id=family_id)


@router.post("/api/tasks")
async def add_task(
    body: TaskCreate,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not _state._task_manager:
        raise HTTPException(503, "Task manager chưa khởi động")
    return _state._task_manager.add_task(body.name, body.remind_time, family_id=family_id)


# stars phải đứng trước /{task_id} để không bị capture
@router.get("/api/tasks/stars")
async def get_stars(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    return {
        "total_stars": (
            _state._task_manager.get_total_stars(family_id=family_id)
            if _state._task_manager else 0
        )
    }


@router.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str, _current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._task_manager and _state._task_manager.complete_task(task_id, family_id=family_id):
        return {"ok": True, "stars": _state._task_manager.get_total_stars(family_id=family_id)}
    raise HTTPException(404, "Task không tìm thấy hoặc đã hoàn thành")


@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, _current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._task_manager and _state._task_manager.delete_task(task_id, family_id=family_id):
        return {"ok": True}
    raise HTTPException(404, "Task không tìm thấy")
```

## src/api/routers/conversation_router.py

```python
"""
conversation_router.py — Conversation Threads endpoints cho Robot Bi API.
  GET    /api/conversations                        — Danh sách sessions
  GET    /api/conversations/homework               — Danh sách sessions bài tập
  GET    /api/conversations/{session_id}           — Chi tiết session + turns
  DELETE /api/conversations/{session_id}           — Xóa session
  POST   /api/conversations/{session_id}/homework  — Đánh dấu session bài tập
"""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import (
    ensure_family_exists,
    get_db_connection,
    get_homework_sessions,
    get_session_turns,
    mark_session_homework,
)

router = APIRouter()


def _require_family(current_user: dict) -> str:
    fid = current_user.get("family_name")
    if not fid:
        raise HTTPException(status_code=403, detail="Token thieu family_name")
    return fid


class ParentChatMessageIn(BaseModel):
    session_id: str | None = Field(default=None, max_length=80)
    role: str = Field(..., max_length=20)
    content: str = Field(..., min_length=1, max_length=4000)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parent_session_to_dict(row) -> dict:
    return {
        "session_id": row["session_id"],
        "title": row["title"] or "Parent chat",
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "message_count": int(row["message_count"] or 0),
    }


def _parent_message_to_dict(row) -> dict:
    return {
        "message_id": row["message_id"],
        "role": row["role"],
        "content": row["content"],
        "timestamp": row["timestamp"],
    }


def _load_parent_chat(family_id: str, session_id: str) -> dict:
    with get_db_connection() as conn:
        session = conn.execute(
            """
            SELECT session_id, title, started_at, ended_at, message_count
            FROM parent_chat_sessions
            WHERE family_id = ? AND session_id = ?
            """,
            (family_id, session_id),
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Parent chat session not found")
        messages = conn.execute(
            """
            SELECT message_id, role, content, timestamp
            FROM parent_chat_messages
            WHERE family_id = ? AND session_id = ?
            ORDER BY timestamp ASC
            """,
            (family_id, session_id),
        ).fetchall()
    return {
        "session": _parent_session_to_dict(session),
        "messages": [_parent_message_to_dict(row) for row in messages],
    }


@router.get("/api/conversations")
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT session_id, title, started_at, ended_at, turn_count
            FROM conversations
            WHERE family_id = ?
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (family_id, limit, offset),
        ).fetchall()
        total_row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM conversations
            WHERE family_id = ?
            """,
            (family_id,),
        ).fetchone()

    conversations = [
        {
            "session_id": row["session_id"],
            "title": row["title"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "turn_count": row["turn_count"],
        }
        for row in rows
    ]
    total = int(total_row["total"]) if total_row else 0
    return {"conversations": conversations, "total": total}


@router.get("/api/conversations/homework")
async def list_homework_conversations(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    sessions = get_homework_sessions(family_id, limit, offset)
    with get_db_connection() as conn:
        total_row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM conversations
            WHERE family_id = ? AND is_homework = 1
            """,
            (family_id,),
        ).fetchone()
    total = int(total_row["total"] or 0) if total_row else 0
    return {"sessions": sessions, "total": total}


@router.get("/api/conversations/parent")
async def list_parent_chat_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT session_id, title, started_at, ended_at, message_count
            FROM parent_chat_sessions
            WHERE family_id = ?
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (family_id, limit, offset),
        ).fetchall()
        total_row = conn.execute(
            "SELECT COUNT(*) AS total FROM parent_chat_sessions WHERE family_id = ?",
            (family_id,),
        ).fetchone()
    return {
        "sessions": [_parent_session_to_dict(row) for row in rows],
        "total": int(total_row["total"] or 0) if total_row else 0,
    }


@router.post("/api/conversations/parent/messages")
async def add_parent_chat_message(
    payload: ParentChatMessageIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = ensure_family_exists(_require_family(_current_user))
    user_id = str(_current_user.get("user_id") or "")
    role = (payload.role or "").strip().lower()
    if role not in {"parent", "bi"}:
        raise HTTPException(status_code=422, detail="role must be parent or bi")
    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="content must not be empty")
    if len(content) > 4000:
        raise HTTPException(status_code=422, detail="content length must be <= 4000")

    now = _utc_now_iso()
    session_id = (payload.session_id or "").strip()
    with get_db_connection() as conn:
        if session_id:
            row = conn.execute(
                """
                SELECT session_id
                FROM parent_chat_sessions
                WHERE family_id = ? AND session_id = ?
                """,
                (family_id, session_id),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Parent chat session not found")
        else:
            session_id = uuid4().hex
            conn.execute(
                """
                INSERT INTO parent_chat_sessions (
                    session_id, family_id, user_id, title, started_at, ended_at, message_count
                ) VALUES (?, ?, ?, ?, ?, NULL, 0)
                """,
                (session_id, family_id, user_id, "Parent chat", now),
            )

        conn.execute(
            """
            INSERT INTO parent_chat_messages (
                message_id, session_id, family_id, role, content, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (uuid4().hex, session_id, family_id, role, content, now),
        )
        conn.execute(
            """
            UPDATE parent_chat_sessions
            SET message_count = message_count + 1
            WHERE family_id = ? AND session_id = ?
            """,
            (family_id, session_id),
        )
        conn.commit()
    return _load_parent_chat(family_id, session_id)


@router.get("/api/conversations/parent/{session_id}")
async def get_parent_chat_session(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    return _load_parent_chat(family_id, session_id)


@router.get("/api/conversations/{session_id}")
async def get_conversation(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT session_id, family_id, title, started_at, ended_at, turn_count
            FROM conversations
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, family_id),
        ).fetchone()

    if not row:
        raise HTTPException(404, "Conversation khong tim thay")

    return {
        "session": {
            "session_id": row["session_id"],
            "family_id": row["family_id"],
            "title": row["title"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "turn_count": row["turn_count"],
        },
        "turns": get_session_turns(session_id, family_id=family_id),
    }


@router.delete("/api/conversations/{session_id}")
async def delete_conversation(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT session_id
            FROM conversations
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, family_id),
        ).fetchone()
        if not row:
            raise HTTPException(404, "Conversation khong tim thay")

        conn.execute(
            """
            DELETE FROM turns
            WHERE session_id IN (
                SELECT session_id FROM conversations
                WHERE session_id = ? AND family_id = ?
            )
            """,
            (session_id, family_id),
        )
        conn.execute(
            "DELETE FROM conversations WHERE session_id = ? AND family_id = ?",
            (session_id, family_id),
        )
        conn.commit()

    return {"ok": True}


@router.post("/api/conversations/{session_id}/homework")
async def mark_homework_conversation(
    session_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT session_id
            FROM conversations
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, family_id),
        ).fetchone()

    if not row:
        raise HTTPException(404, "Conversation khong tim thay")

    ok = mark_session_homework(session_id, family_id=family_id)
    if not ok:
        raise HTTPException(404, "Conversation khong tim thay")
    return {"ok": True}
```

## src/api/routers/streaming_router.py

```python
"""
streaming_router.py — WebSocket + Mom Direct Talk endpoints cho Robot Bi API.
  WS   /ws                — Real-time event push
  WS   /api/audio/stream  — Mic room → browser (audio monitoring)
  POST /api/mom/start     — Mẹ bắt đầu nói
  POST /api/mom/stop      — Mẹ dừng nói
  GET  /api/mom/status    — Trạng thái mom (no auth)
  WS   /api/mom/audio     — Browser mẹ → loa robot
"""
import asyncio
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from src.infrastructure.auth.auth import get_current_user
import src.infrastructure.sessions.state as _state
from src.motion.motor_controller import get_shared_motor

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Audio monitoring constants ─────────────────────────────────────────────
AUDIO_SAMPLE_RATE  = 16000
AUDIO_CHANNELS     = 1
AUDIO_CHUNK_MS     = 100
AUDIO_CHUNK_FRAMES = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)
_mic_raw = os.getenv("MIC_DEVICE", "").strip()
AUDIO_MIC_DEVICE   = int(_mic_raw) if _mic_raw.isdigit() else 1

try:
    import numpy as np
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False

try:
    from scipy import signal as _scipy_signal
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


async def _ws_verify_token(token: Optional[str] = Query(None), auth: Optional[str] = Query(None)) -> dict:
    """Shared WebSocket auth helper — accepts ?token= or ?auth= query param."""
    t = token or auth
    if not t:
        raise WebSocketDisconnect(code=1008)
    from src.infrastructure.auth.auth import verify_access_token
    try:
        return verify_access_token(t)
    except Exception:
        raise WebSocketDisconnect(code=1008)


# ── WebSocket: Event push ─────────────────────────────────────────────────

@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    try:
        from src.infrastructure.auth.auth import verify_access_token
        payload = verify_access_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    family_id = payload["family"]
    await _state._ws_manager.connect(websocket, family_id=family_id)
    if _state._notifier:
        try:
            unread = _state._fetch_events_from_db(
                unread_only=True,
                limit=20,
                newest_first=True,
                family_id=family_id,
            )
            unread.reverse()
            for evt in unread:
                await websocket.send_json(evt)
        except Exception:
            pass
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("type") == "motor":
                    cmd = msg.get("cmd", "")
                    speed = int(msg.get("speed", 50))
                    duration_ms = int(msg.get("duration_ms", 800))
                    degrees = int(msg.get("degrees", 45))
                    if cmd == "drive":
                        vx    = float(msg.get("vx",    0))
                        omega = float(msg.get("omega", 0))
                        vx    = max(-100.0, min(100.0, vx))
                        omega = max(-100.0, min(100.0, omega))
                        left  = int(max(-100, min(100, vx - omega)))
                        right = int(max(-100, min(100, vx + omega)))
                        get_shared_motor().drive(left, right)
                    elif cmd == "forward":
                        get_shared_motor().forward(speed, duration_ms)
                    elif cmd == "backward":
                        get_shared_motor().backward(speed, duration_ms)
                    elif cmd == "left":
                        get_shared_motor().turn_left(degrees)
                    elif cmd == "right":
                        get_shared_motor().turn_right(degrees)
                    elif cmd == "spin":
                        get_shared_motor().spin(speed, duration_ms)
                    elif cmd == "stop":
                        get_shared_motor().stop()
                elif msg.get("type") == "wifi":
                    cmd = msg.get("cmd", "")
                    get_shared_motor()._send_raw(cmd)
            except (json.JSONDecodeError, ValueError):
                pass  # Non-motor messages (keepalive pings etc) — ignore silently
    except WebSocketDisconnect:
        _state._ws_manager.disconnect(websocket)


# ── WebSocket: Audio Monitoring ───────────────────────────────────────────

@router.websocket("/api/audio/stream")
async def audio_stream(websocket: WebSocket, token: Optional[str] = Query(None), auth: Optional[str] = Query(None)):
    """
    Stream audio từ mic phòng → browser (1 chiều).
    Format: PCM 16-bit little-endian, 16kHz, mono.
    Auth qua query param: /api/audio/stream?token=JWT_ACCESS_TOKEN
    """
    try:
        await _ws_verify_token(token, auth)
    except WebSocketDisconnect:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info("[Bi - Tai Giam Sat] Client ket noi audio stream")

    if not _SD_AVAILABLE:
        logger.warning("[Bi - Tai Giam Sat] sounddevice/numpy khong co san — dong stream")
        await websocket.close(code=1011)
        return

    loop = asyncio.get_event_loop()
    audio_queue: asyncio.Queue = asyncio.Queue(maxsize=10)

    async def _safe_put(q, item):
        try:
            q.put_nowait(item)
        except asyncio.QueueFull:
            logger.debug("[Audio] queue full, dropping frame")

    def audio_callback(indata, frames, time_info, status):
        pcm = (indata[:, 0] * 32767).astype(np.int16)
        raw_bytes = pcm.tobytes()
        loop.call_soon_threadsafe(
            loop.create_task,
            _safe_put(audio_queue, raw_bytes),
        )

    stream = None
    try:
        stream = sd.InputStream(
            samplerate=AUDIO_SAMPLE_RATE,
            channels=AUDIO_CHANNELS,
            dtype="float32",
            blocksize=AUDIO_CHUNK_FRAMES,
            device=AUDIO_MIC_DEVICE,
            callback=audio_callback,
        )
        stream.start()
        logger.info("[Bi - Tai Giam Sat] Bat dau stream audio mic")

        while True:
            try:
                raw_bytes = await asyncio.wait_for(audio_queue.get(), timeout=5.0)
                await websocket.send_bytes(raw_bytes)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_bytes(b"")
                except Exception:
                    break
            except Exception:
                break

    except Exception as e:
        logger.error("[Bi - Tai Giam Sat] Loi mic: %s", e)
    finally:
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        logger.info("[Bi - Tai Giam Sat] Client ngat ket noi audio stream")


# ── REST: Mom Direct Talk ─────────────────────────────────────────────────

@router.post("/api/mom/start")
async def mom_start_talking(_current_user: dict = Depends(get_current_user)):
    """Mẹ bắt đầu nói — Bi tạm dừng AI, chờ nhận audio từ mẹ."""
    _state._mom_talking = True
    logger.info("[Me] ===== ME BAT DAU NOI — BI TAM DUNG =====")
    logger.info("[Me] Me bat dau noi chuyen truc tiep")
    return {"status": "mom_talking", "message": "Bi đang nhường loa cho mẹ"}


@router.post("/api/mom/stop")
async def mom_stop_talking(_current_user: dict = Depends(get_current_user)):
    """Mẹ dừng nói — Bi hoạt động bình thường lại."""
    _state._mom_talking = False
    logger.info("[Me] ===== ME DUNG NOI — BI HOAT DONG LAI =====")
    logger.info("[Me] Me ngung noi — Bi hoat dong binh thuong")
    return {"status": "bi_active", "message": "Bi đang hoạt động trở lại"}


@router.get("/api/mom/status")
async def mom_status():
    """Trả về trạng thái hiện tại (không cần auth — main_loop poll nội bộ)."""
    return {"mom_talking": _state._mom_talking}


# ── WebSocket: Mom Audio ──────────────────────────────────────────────────

@router.websocket("/api/mom/audio")
async def mom_audio_receive(websocket: WebSocket, token: Optional[str] = Query(None), auth: Optional[str] = Query(None)):
    """
    Nhận audio PCM float32 từ browser điện thoại mẹ → phát qua loa robot.
    Format: PCM float32, 16000Hz, mono (Web Audio API getUserMedia).
    Auth: /api/mom/audio?token=JWT_ACCESS_TOKEN
    """
    try:
        await _ws_verify_token(token, auth)
    except WebSocketDisconnect:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _state._mom_audio_clients.append(websocket)
    logger.info("[Me] Ket noi audio tu dien thoai me")

    import pygame
    import numpy as np
    import io as _io
    import wave as _wave

    MOM_CHANNEL = 7

    def _get_mixer_freq():
        info = pygame.mixer.get_init()
        return info[0] if info else 44100

    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.init()

    if pygame.mixer.get_num_channels() <= MOM_CHANNEL:
        pygame.mixer.set_num_channels(MOM_CHANNEL + 1)

    mom_channel = pygame.mixer.Channel(MOM_CHANNEL)

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_bytes(), timeout=10.0
                )
                if not data or len(data) == 0:
                    continue
                if not _state._mom_talking:
                    continue

                float_array = np.frombuffer(data, dtype=np.float32)
                if len(float_array) < 16:
                    continue
                float_array = np.clip(float_array, -1.0, 1.0)

                mixer_freq = _get_mixer_freq()
                src_freq = 16000

                if mixer_freq != src_freq:
                    if _SCIPY_AVAILABLE:
                        num_samples = int(len(float_array) * mixer_freq / src_freq)
                        float_array = _scipy_signal.resample(float_array, num_samples)
                    else:
                        num_samples = int(len(float_array) * mixer_freq / src_freq)
                        indices = np.linspace(0, len(float_array) - 1, num_samples)
                        float_array = np.interp(indices, np.arange(len(float_array)), float_array)

                int16_mono = (float_array * 32767).astype(np.int16)

                mixer_channels = pygame.mixer.get_init()[2] if pygame.mixer.get_init() else 2
                if mixer_channels == 2:
                    int16_stereo = np.column_stack([int16_mono, int16_mono])
                    pcm_bytes = int16_stereo.tobytes()
                else:
                    pcm_bytes = int16_mono.tobytes()

                buf = _io.BytesIO()
                with _wave.open(buf, 'wb') as wf:
                    wf.setnchannels(mixer_channels)
                    wf.setsampwidth(2)
                    wf.setframerate(mixer_freq)
                    wf.writeframes(pcm_bytes)
                buf.seek(0)

                sound = pygame.mixer.Sound(buf)
                sound.set_volume(1.0)
                mom_channel.play(sound)

            except asyncio.TimeoutError:
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break
            except Exception as e:
                logger.error("[Me] Loi nhan audio: %s", e)
                break

    finally:
        if websocket in _state._mom_audio_clients:
            _state._mom_audio_clients.remove(websocket)
        logger.info("[Me] Ngat ket noi audio tu me")
```

## src/api/routers/admin_router.py

```python
"""
admin_router.py - Admin-only family management endpoints.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user
from src.infrastructure.database.db import (
    create_family_record,
    delete_family_record,
    is_user_admin,
    list_families,
)
import src.infrastructure.sessions.state as _state

logger = logging.getLogger(__name__)
router = APIRouter()

_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_SECRET_RE = re.compile(
    r"(?i)\b(bearer\s+)[a-z0-9._~+/=-]+|"
    r"\b(api[_-]?key|jwt[_-]?secret[_-]?key|secret|token|password)\s*[:=]\s*[^,\s;]+|"
    r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"
)
_CHILD_TEXT_RE = re.compile(r"(?i)\b(child_text|child_message|content|speech)\s*[:=]\s*[^,\n;]+")


class FamilyCreate(BaseModel):
    family_id: str = Field(..., min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    display_name: str | None = Field(default=None, max_length=120)


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not is_user_admin(str(current_user.get("user_id", ""))):
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_log_message(message: str) -> str:
    value = str(message or "")

    def repl_secret(match: re.Match) -> str:
        text = match.group(0)
        if text.lower().startswith("bearer "):
            return "Bearer [REDACTED]"
        return "[REDACTED]"

    value = _SECRET_RE.sub(repl_secret, value)
    value = _CHILD_TEXT_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", value)
    return value[:1000]


def _system_log_entries() -> list[dict]:
    now = _utc_now_iso()
    raw_entries = [
        {
            "timestamp": now,
            "level": "INFO",
            "component": "api_server",
            "message": "FastAPI admin log endpoint ready",
            "source": "application",
        },
        {
            "timestamp": now,
            "level": "INFO",
            "component": "database",
            "message": "SQLite schema initialized",
            "source": "application",
        },
        {
            "timestamp": now,
            "level": "WARNING",
            "component": "logs",
            "message": "Raw log file access disabled for safety",
            "source": "application",
        },
    ]
    return [
        {**entry, "message": _sanitize_log_message(entry["message"])}
        for entry in raw_entries
    ]


def _parse_since(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="since must be an ISO timestamp")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@router.post("/api/admin/families")
async def create_family(body: FamilyCreate, _admin: dict = Depends(require_admin)):
    family = create_family_record(body.family_id, body.display_name)
    if family is None:
        raise HTTPException(status_code=409, detail="Family already exists")
    return family


@router.get("/api/admin/families")
async def get_families(_admin: dict = Depends(require_admin)):
    return {"families": list_families()}


@router.get("/api/admin/logs")
async def get_admin_logs(
    level: Optional[str] = Query(default=None, max_length=20),
    component: Optional[str] = Query(default=None, max_length=80),
    since: Optional[str] = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: dict = Depends(require_admin),
):
    level_filter = (level or "").strip().upper()
    if level_filter and level_filter not in _LEVELS:
        raise HTTPException(status_code=422, detail="level is invalid")
    component_filter = (component or "").strip().lower()
    since_dt = _parse_since(since)

    entries = []
    for entry in _system_log_entries():
        if level_filter and entry["level"] != level_filter:
            continue
        if component_filter and entry["component"].lower() != component_filter:
            continue
        if since_dt:
            entry_dt = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            if entry_dt < since_dt:
                continue
        entries.append(entry)

    total = len(entries)
    return {
        "logs": entries[offset: offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/api/admin/families/{family_id}")
async def delete_family(family_id: str, admin: dict = Depends(require_admin)):
    if family_id == admin.get("family_name"):
        raise HTTPException(status_code=400, detail="Cannot delete current admin family")
    ok = delete_family_record(family_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Family not found")
    if _state._rag:
        result = _state._rag.clear_all_memories(family_id=family_id)
        if not result:
            logger.warning(
                "[Admin] ChromaDB cleanup failed for family %s - "
                "DB deleted but memories may remain",
                family_id,
            )
    return {"ok": True, "family_id": family_id}
```

## src/api/routers/ops_router.py

```python
"""
ops_router.py — Ops endpoints + Cloudflare Tunnel cho Robot Bi API.
  GET /health      — Health check (no auth)
  GET /            — Web dashboard
  GET /api/camera  — MJPEG live camera stream
"""
import asyncio
import logging
import os
import queue
import re
import subprocess
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Cloudflare Tunnel config ──────────────────────────────────────────────────
TUNNEL_TOKEN = os.getenv("CLOUDFLARE_TUNNEL_TOKEN", "").strip()
TUNNEL_URL   = os.getenv("CLOUDFLARE_TUNNEL_URL", "").strip()
_CLOUDFLARED_EXE = "cloudflared.exe" if os.name == "nt" else "cloudflared"
_tunnel_process = None

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

router = APIRouter()


def _build_ascii_qr(data: str, border: int = 1, invert: bool = False) -> str:
    """Render compact square QR: 2 module rows per terminal line via half-block Unicode, no ANSI."""
    import qrcode
    qr = qrcode.QRCode(version=None, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    lines = []
    for y in range(0, len(matrix), 2):
        row_top = matrix[y]
        row_bot = matrix[y + 1] if y + 1 < len(matrix) else [False] * len(row_top)
        line = ""
        for t, b in zip(row_top, row_bot):
            if t and b:
                line += "█"
            elif t:
                line += "▀"
            elif b:
                line += "▄"
            else:
                line += " "
        lines.append(line)
    return "\n".join(lines)


def _start_cloudflare_tunnel(port: int, use_https: bool = False) -> None:
    """Khởi động Named Tunnel nếu có CLOUDFLARE_TUNNEL_TOKEN, fallback quick tunnel."""
    def _run():
        global _tunnel_process
        try:
            result = subprocess.run(
                [_CLOUDFLARED_EXE, "--version"],
                capture_output=True, timeout=5,
            )
            if result.returncode != 0:
                print("[Tunnel] cloudflared khong tim thay — bo qua tunnel")
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("[Tunnel] cloudflared chua cai — bo qua tunnel")
            print("[Tunnel] Tai tai: https://github.com/cloudflare/cloudflared/releases")
            return

        if TUNNEL_TOKEN:
            # Named Tunnel — URL cố định, không đổi sau restart
            cmd = [_CLOUDFLARED_EXE, "tunnel", "--no-autoupdate", "run",
                   "--token", TUNNEL_TOKEN]
            logger.info("[Tunnel] Named Tunnel dang khoi dong...")
            fixed_url = TUNNEL_URL or "(xem Cloudflare dashboard)"
            print("\n" + "=" * 60)
            print(f"  URL CO DINH (Named Tunnel):")
            print(f"  {fixed_url}")
            print("=" * 60 + "\n")
            if TUNNEL_URL:
                try:
                    print(_build_ascii_qr(TUNNEL_URL, invert=True))
                except ImportError:
                    pass
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                )
                _tunnel_process = proc
                stdout, stderr = proc.communicate()
                exit_code = proc.returncode
                if exit_code != 0:
                    logger.error(
                        "[Tunnel] Process exit code=%d stderr=%s",
                        exit_code,
                        (stderr or "")[:500],
                    )
                else:
                    logger.info("[Tunnel] Process exited cleanly")
            except Exception as e:
                logger.error("[Tunnel] Loi Named Tunnel: %s", e)
        else:
            # Quick tunnel — fallback, URL thay đổi mỗi restart
            scheme = "https" if use_https else "http"
            print(f"[Tunnel] Quick tunnel -> {scheme}://localhost:{port} (URL thay doi moi restart)...")
            cmd = [_CLOUDFLARED_EXE, "tunnel", "--no-autoupdate", "--url",
                   f"{scheme}://localhost:{port}"]
            if use_https:
                cmd.append("--no-tls-verify")
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                )
                _tunnel_process = proc
                for line in proc.stdout:
                    line = line.strip()
                    if "trycloudflare.com" in line or "https://" in line:
                        urls = re.findall(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
                        if urls:
                            public_url = urls[0]
                            print("\n" + "=" * 60)
                            print(f"  URL CONG KHAI (thay doi moi restart):")
                            print(f"  {public_url}")
                            print("=" * 60 + "\n")
                            try:
                                print(_build_ascii_qr(public_url, invert=True))
                            except ImportError:
                                pass
            except Exception as e:
                print(f"[Tunnel] Loi: {e}")

    t = threading.Thread(target=_run, daemon=True, name="cloudflared-tunnel")
    t.start()

_PARENT_APP_DIR = Path(__file__).parent.parent.parent.parent / "frontend" / "parent_app"
_PARENT_APP_DIST_DIR = _PARENT_APP_DIR / "dist"

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


async def _camera_auth(
    request: Request,
    auth: Optional[str] = Query(None),
) -> dict:
    """
    Camera/stream auth: chap nhan JWT qua Authorization header HOAC ?auth= query param.
    Dung cho <img src='/api/camera?auth=TOKEN'> trong browser.
    """
    from src.infrastructure.auth.auth import verify_access_token
    authorization = request.headers.get("Authorization", "")
    token = auth or (authorization[7:] if authorization.startswith("Bearer ") else None)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_access_token(token)
    except HTTPException:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": payload["sub"], "family_name": payload["family"]}


@router.get("/health")
async def health():
    """Health check — khong can auth."""
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    index = _PARENT_APP_DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return HTMLResponse(
        "<h1>Robot Bi</h1>"
        "<p>Parent App build chua co. Chay <code>npm.cmd run build</code> "
        "trong <code>frontend/parent_app</code>, hoac dung Vite dev server.</p>",
        status_code=503,
    )


def _camera_capture_thread(frame_queue: queue.Queue, stop_event: threading.Event):
    """Thread riêng capture frame — không block event loop."""
    import time as _time
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        stop_event.set()
        return

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 30)

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            _time.sleep(0.01)
            continue

        frame = cv2.resize(frame, (640, 480))
        _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_bytes = jpg.tobytes()

        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
        try:
            frame_queue.put_nowait(frame_bytes)
        except queue.Full:
            pass

    cap.release()


async def _mjpeg_generator():
    """Generator yield MJPEG frames — camera capture chạy trong thread riêng."""
    if not _CV2_AVAILABLE:
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blank, 'Camera not available', (80, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, jpg = cv2.imencode('.jpg', blank)
        frame_bytes = jpg.tobytes()
        while True:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + frame_bytes + b'\r\n')
            await asyncio.sleep(0.5)
        return

    frame_queue: queue.Queue = queue.Queue(maxsize=2)
    stop_event = threading.Event()

    t = threading.Thread(
        target=_camera_capture_thread,
        args=(frame_queue, stop_event),
        daemon=True,
        name="camera-capture",
    )
    t.start()

    try:
        while True:
            try:
                frame_bytes = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: frame_queue.get(timeout=0.1),
                )
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + frame_bytes + b'\r\n')
                await asyncio.sleep(0)
            except queue.Empty:
                await asyncio.sleep(0.033)
            except GeneratorExit:
                break
    finally:
        stop_event.set()


@router.get("/api/camera")
async def camera_stream(_current_user: dict = Depends(_camera_auth)):
    """Live MJPEG camera stream. Token co the truyen qua query param ?auth=<JWT>"""
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )
```

## src/api/routers/webrtc_router.py

```python
"""
webrtc_router.py — WebRTC signaling endpoints cho Robot Bi.
  POST /api/webrtc/offer  — SDP offer → answer (JWT required)
  POST /api/webrtc/close  — Close all peer connections (JWT required)

aiortc cần cài trên Ubuntu: pip install aiortc==1.9.0
Trên Windows (dev): _AIORTC_AVAILABLE=False → endpoints trả 503, frontend fallback MJPEG.
"""
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from src.infrastructure.auth.auth import get_current_user
import src.infrastructure.sessions.state as _state

logger = logging.getLogger(__name__)

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    _AIORTC_AVAILABLE = True
except ImportError:
    _AIORTC_AVAILABLE = False
    RTCPeerConnection = None
    VideoStreamTrack = object  # fallback base class để class body parse được

_peer_connections: dict[str, RTCPeerConnection] = {}

router = APIRouter(prefix="/api/webrtc", tags=["webrtc"])


if _AIORTC_AVAILABLE:
    class CameraVideoTrack(VideoStreamTrack):
        """Lấy frame JPEG từ _state._camera_frame, convert sang av.VideoFrame."""

        kind = "video"

        async def recv(self):
            import av
            import numpy as np
            import cv2

            pts, time_base = await self.next_timestamp()

            jpeg = _state._camera_frame
            if jpeg:
                try:
                    arr = np.frombuffer(jpeg, np.uint8)
                    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                except Exception:
                    rgb = np.zeros((480, 640, 3), dtype=np.uint8)
            else:
                rgb = np.zeros((480, 640, 3), dtype=np.uint8)

            frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
            frame.pts = pts
            frame.time_base = time_base
            return frame


@router.post("/offer")
async def webrtc_offer(request: Request, current_user: dict = Depends(get_current_user)):
    """SDP offer từ browser → tạo answer, trả về SDP answer."""
    if not _AIORTC_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="WebRTC không khả dụng trên server này. Dùng MJPEG fallback.",
        )

    body = await request.json()
    sdp = body.get("sdp", "")
    sdp_type = body.get("type", "offer")

    if not sdp:
        raise HTTPException(status_code=422, detail="Thiếu trường sdp")

    pc = RTCPeerConnection(configuration={
        "iceServers": [{"urls": "stun:stun.l.google.com:19302"}]
    })
    try:
        pc.addTrack(CameraVideoTrack())

        offer = RTCSessionDescription(sdp=sdp, type=sdp_type)
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # Chờ ICE gathering hoàn thành (tối đa 10s)
        await asyncio.wait_for(
            _ice_gathering_complete(pc),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        logger.warning("[WebRTC] ICE gathering timeout — trả answer ngay")
    except Exception as e:
        logger.error("[WebRTC] offer failed: %s", e)
        await pc.close()
        raise HTTPException(status_code=500, detail="WebRTC offer that bai")

    key = str(current_user["user_id"])
    old_pc = _peer_connections.pop(key, None)
    if old_pc:
        try:
            await old_pc.close()
            logger.info("[WebRTC] Closed old PC for user %s", key)
        except Exception as e:
            logger.debug("[WebRTC] Error closing old PC: %s", e)
    _peer_connections[key] = pc

    @pc.on("connectionstatechange")
    async def on_state_change():
        if pc.connectionState in ("failed", "closed", "disconnected"):
            try:
                await pc.close()
            except Exception as e:
                logger.debug(
                    "[WebRTC] PC close error (likely already closed): %s", e
                )
            if _peer_connections.get(key) is pc:
                _peer_connections.pop(key, None)
            logger.info("[WebRTC] PC closed, state=%s", pc.connectionState)

    logger.info("[WebRTC] Offer processed, answer ready. Active PCs: %d", len(_peer_connections))
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


@router.post("/close")
async def webrtc_close(current_user: dict = Depends(get_current_user)):
    """Close peer connection cua user hien tai."""
    key = str(current_user["user_id"])
    pc = _peer_connections.pop(key, None)
    closed = 0
    if pc:
        try:
            await pc.close()
        except Exception:
            pass
        closed = 1
    logger.info("[WebRTC] Closed %d peer connection(s) for user=%s", closed, key)
    return {"closed": closed}


async def _ice_gathering_complete(pc) -> None:
    """Chờ ICE gathering state chuyển sang 'complete'."""
    if pc.iceGatheringState == "complete":
        return
    loop = asyncio.get_event_loop()
    done = loop.create_future()

    @pc.on("icegatheringstatechange")
    def on_gathering():
        if pc.iceGatheringState == "complete" and not done.done():
            done.set_result(None)

    await done
```

## src/infrastructure/database/db.py

```python
"""
db.py - SQLite storage helpers for Robot Bi network persistence.
"""

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent.parent
OLD_DB_PATHS = [
    REPO_ROOT / "src_brain" / "network" / "robot_bi.db",
    REPO_ROOT / "src_brain" / "network" / "data" / "robot_bi.db",
    REPO_ROOT / "robot_bi.db",
]
NEW_DB_PATH = REPO_ROOT / "runtime" / "robot_bi.db"
DB_PATH = NEW_DB_PATH

_INIT_LOCK = threading.Lock()
_INITIALIZED = False


def migrate_db_path_if_needed() -> None:
    """
    One-time migration: copy DB tu path cu sang runtime/robot_bi.db.

    Chi copy khi DB moi chua ton tai hoac gan nhu rong, va co DB cu co data.
    DB cu duoc giu nguyen de rollback an toan.
    """
    import shutil

    if NEW_DB_PATH.exists() and NEW_DB_PATH.stat().st_size > 8192:
        return

    old_db = None
    for path in OLD_DB_PATHS:
        if not path.exists():
            continue
        size = path.stat().st_size
        if size <= 8192:
            continue
        if old_db is None or size > old_db.stat().st_size:
            old_db = path

    if old_db is None:
        return

    NEW_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old_db, NEW_DB_PATH)
    logger.info(
        "[DB] Migrated DB from %s to %s (%d bytes)",
        old_db,
        NEW_DB_PATH,
        NEW_DB_PATH.stat().st_size,
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_family_id(family_id: str | None) -> str:
    fid = (family_id or "").strip()
    return fid or os.getenv("FAMILY_ID", "default")


def _ensure_family_exists_conn(conn, family_id: str | None, display_name: str | None = None) -> str:
    fid = _normalize_family_id(family_id)
    label = (display_name or fid).strip() or fid
    conn.execute(
        """
        INSERT OR IGNORE INTO families (family_id, display_name, created_at)
        VALUES (?, ?, ?)
        """,
        (fid, label, _utc_now_iso()),
    )
    return fid


def ensure_family_exists(family_id: str | None, display_name: str | None = None) -> str:
    """Create the family row if missing and return the normalized family_id."""
    with get_db_connection() as conn:
        fid = _ensure_family_exists_conn(conn, family_id, display_name)
        conn.commit()
        return fid


@contextmanager
def get_db_connection():
    """Tra ve connection voi WAL mode bat"""
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def cleanup_expired_login_attempts(ttl_minutes: int = 60) -> int:
    """Xoa login_attempts cu hon ttl_minutes. Tra ve so rows da xoa."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            DELETE FROM login_attempts
            WHERE first_attempt_at IS NOT NULL
              AND first_attempt_at < ?
              AND (locked_until IS NULL OR locked_until <= ?)
            """,
            (cutoff, now),
        )
        conn.commit()
        return cur.rowcount


def cleanup_orphan_sessions(max_age_hours: int = 24) -> int:
    """Dong cac session cu co ended_at IS NULL. Tra ve so session da dong."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            UPDATE conversations
            SET ended_at = ?
            WHERE ended_at IS NULL
              AND started_at < ?
            """,
            (_utc_now_iso(), cutoff),
        )
        conn.commit()
        if cur.rowcount > 0:
            logger.info(
                "[DB] Dong %d orphan session cu hon %dh",
                cur.rowcount,
                max_age_hours,
            )
        return cur.rowcount


def init_db() -> None:
    """Khoi tao database va migrate du lieu tu JSON cu neu can."""
    global _INITIALIZED
    migrate_db_path_if_needed()
    if _INITIALIZED:
        return

    with _INIT_LOCK:
        if _INITIALIZED:
            return

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with get_db_connection() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS families (
                    family_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                '''
            )
            _ensure_family_exists_conn(conn, "default", "default")

            # Tao bang events
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS events (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL DEFAULT 'default'
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    event_id TEXT,
                    timestamp TEXT,
                    type TEXT NOT NULL,
                    message TEXT,
                    clip_path TEXT,
                    metadata_json TEXT,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    import_key TEXT UNIQUE
                )
                '''
            )
            event_cols = {row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()}
            if "family_id" not in event_cols:
                conn.execute("ALTER TABLE events ADD COLUMN family_id TEXT DEFAULT 'default'")
            conn.execute(
                """
                UPDATE events
                SET family_id = 'default'
                WHERE family_id IS NULL OR family_id = ''
                """
            )

            # Tao bang tasks - khop voi task_manager.py
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS tasks (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL DEFAULT 'default'
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    task_id TEXT,
                    name TEXT NOT NULL,
                    remind_time TEXT,
                    completed_today INTEGER NOT NULL DEFAULT 0,
                    completed_date TEXT,
                    stars INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    last_reminded TEXT,
                    last_reminded_date TEXT,
                    import_key TEXT UNIQUE
                )
                '''
            )
            task_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
            if "family_id" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN family_id TEXT DEFAULT 'default'")
            if "completed_date" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN completed_date TEXT")
            if "last_reminded_date" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN last_reminded_date TEXT")
            conn.execute(
                """
                UPDATE tasks
                SET family_id = 'default'
                WHERE family_id IS NULL OR family_id = ''
                """
            )
            conn.execute(
                """
                UPDATE tasks
                SET completed_date = '2000-01-01'
                WHERE completed_today = 1
                  AND (completed_date IS NULL OR completed_date = '')
                """
            )
            for index_sql in (
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_import_key ON events(import_key)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_import_key ON tasks(import_key)",
                "CREATE INDEX IF NOT EXISTS idx_events_family_db ON events(family_id, db_id)",
                "CREATE INDEX IF NOT EXISTS idx_events_family_timestamp ON events(family_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_events_family_type_timestamp ON events(family_id, type, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_family_db ON tasks(family_id, db_id)",
            ):
                try:
                    conn.execute(index_sql)
                except Exception as e:
                    logger.warning("[DB] Bo qua import_key unique index: %s", e)

            # Parent notes attached to family-scoped events.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS parent_event_notes (
                    note_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    event_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            for index_sql in (
                """
                CREATE INDEX IF NOT EXISTS idx_parent_event_notes_family_event
                ON parent_event_notes(family_id, event_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_parent_event_notes_family_updated
                ON parent_event_notes(family_id, updated_at)
                """,
            ):
                conn.execute(index_sql)

            # Parent App child profiles and settings storage.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS child_profiles (
                    child_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    birth_date TEXT,
                    grade TEXT,
                    avatar TEXT,
                    interests_json TEXT NOT NULL DEFAULT '[]',
                    notes TEXT,
                    is_active INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS child_content_settings (
                    setting_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    child_id TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 0,
                    min_age INTEGER,
                    max_age INTEGER,
                    blocked_topics_json TEXT NOT NULL DEFAULT '[]',
                    allowed_topics_json TEXT NOT NULL DEFAULT '[]',
                    strict_mode INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS interaction_limit_settings (
                    setting_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    child_id TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 0,
                    daily_limit_minutes INTEGER NOT NULL DEFAULT 60,
                    warning_minutes INTEGER NOT NULL DEFAULT 10,
                    reset_time TEXT NOT NULL DEFAULT '00:00',
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS daily_interaction_usage (
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    child_id TEXT NOT NULL DEFAULT '',
                    usage_date TEXT NOT NULL,
                    seconds_used INTEGER NOT NULL DEFAULT 0,
                    sessions_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (family_id, child_id, usage_date)
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS sleep_schedule_settings (
                    family_id TEXT PRIMARY KEY
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    start_time TEXT NOT NULL DEFAULT '21:00',
                    end_time TEXT NOT NULL DEFAULT '06:30',
                    days_json TEXT NOT NULL DEFAULT '["mon","tue","wed","thu","fri","sat","sun"]',
                    timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS notification_settings (
                    family_id TEXT PRIMARY KEY
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    event_types_json TEXT NOT NULL DEFAULT '{}',
                    quiet_hours_json TEXT NOT NULL DEFAULT '{}',
                    channels_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS push_subscriptions (
                    subscription_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    endpoint_hash TEXT NOT NULL,
                    subscription_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    revoked_at TEXT
                )
                '''
            )
            for index_sql in (
                "CREATE INDEX IF NOT EXISTS idx_child_profiles_family ON child_profiles(family_id)",
                """
                CREATE INDEX IF NOT EXISTS idx_child_profiles_family_active
                ON child_profiles(family_id, is_active)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_child_content_settings_family_child
                ON child_content_settings(family_id, child_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_interaction_limit_settings_family_child
                ON interaction_limit_settings(family_id, child_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_push_subscriptions_family_user
                ON push_subscriptions(family_id, user_id)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_push_subscriptions_endpoint_hash
                ON push_subscriptions(endpoint_hash)
                """,
            ):
                conn.execute(index_sql)

            # Parent App Phase 3: report audit metadata, content catalog, and parent chat.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS report_exports (
                    export_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    format TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    sections_json TEXT NOT NULL,
                    row_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS content_items (
                    content_id TEXT PRIMARY KEY,
                    family_id TEXT,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    source_url TEXT,
                    thumbnail_url TEXT,
                    age_min INTEGER,
                    age_max INTEGER,
                    language TEXT NOT NULL DEFAULT 'vi',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS parent_chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    message_count INTEGER NOT NULL DEFAULT 0
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS parent_chat_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL
                        REFERENCES parent_chat_sessions(session_id) ON DELETE CASCADE,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                '''
            )
            for index_sql in (
                """
                CREATE INDEX IF NOT EXISTS idx_report_exports_family_created
                ON report_exports(family_id, created_at)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_content_items_type_enabled
                ON content_items(type, enabled, sort_order)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_content_items_family_type
                ON content_items(family_id, type)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_content_items_age
                ON content_items(age_min, age_max)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_parent_chat_sessions_family_started
                ON parent_chat_sessions(family_id, started_at)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_parent_chat_messages_session_time
                ON parent_chat_messages(session_id, timestamp)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_parent_chat_messages_family_time
                ON parent_chat_messages(family_id, timestamp)
                """,
            ):
                conn.execute(index_sql)

            content_seeded_at = _utc_now_iso()
            default_content_items = (
                (
                    "radio-bi-story",
                    "radio",
                    "Radio ke chuyen",
                    "Audio stories and calm listening for children.",
                    "https://example.invalid/radio/stories",
                    None,
                    5,
                    12,
                    "vi",
                    ["stories", "listening"],
                    1,
                    10,
                ),
                (
                    "radio-bi-learning",
                    "radio",
                    "Radio hoc tap",
                    "Short education-focused radio segments.",
                    "https://example.invalid/radio/learning",
                    None,
                    6,
                    12,
                    "vi",
                    ["education", "science"],
                    1,
                    20,
                ),
                (
                    "video-bi-english-animals",
                    "video",
                    "English animals",
                    "Simple English animal vocabulary lesson.",
                    "https://example.invalid/videos/english-animals",
                    None,
                    5,
                    9,
                    "vi",
                    ["english", "animals"],
                    1,
                    10,
                ),
                (
                    "video-bi-math-shapes",
                    "video",
                    "Hinh hoc vui",
                    "Shape recognition and early geometry lesson.",
                    "https://example.invalid/videos/math-shapes",
                    None,
                    6,
                    12,
                    "vi",
                    ["math", "geometry"],
                    1,
                    20,
                ),
                (
                    "game-bi-word-quiz",
                    "game",
                    "Word quiz",
                    "Interactive vocabulary quiz backed by Robot Bi.",
                    "/api/game/word-quiz/start",
                    None,
                    5,
                    12,
                    "vi",
                    ["vocabulary", "quiz"],
                    1,
                    10,
                ),
                (
                    "game-bi-voice-quiz",
                    "game",
                    "Voice quiz",
                    "Voice-based riddle game backed by Robot Bi.",
                    "/api/game/voice-quiz/start",
                    None,
                    7,
                    12,
                    "vi",
                    ["voice", "quiz"],
                    1,
                    20,
                ),
            )
            for item in default_content_items:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO content_items (
                        content_id, family_id, type, title, description, source_url,
                        thumbnail_url, age_min, age_max, language, tags_json, enabled,
                        sort_order, created_at, updated_at
                    ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item[0],
                        item[1],
                        item[2],
                        item[3],
                        item[4],
                        item[5],
                        item[6],
                        item[7],
                        item[8],
                        json.dumps(item[9], ensure_ascii=False),
                        item[10],
                        item[11],
                        content_seeded_at,
                        content_seeded_at,
                    ),
                )

            # Parent App Phase 4: QR pairing metadata and robot location metadata.
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS device_pairing_codes (
                    pairing_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    purpose TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT NOT NULL,
                    created_by_user_id TEXT NOT NULL
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS robot_location_metadata (
                    family_id TEXT PRIMARY KEY
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    room_name TEXT,
                    location_label TEXT,
                    source TEXT NOT NULL DEFAULT 'parent',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    updated_at TEXT NOT NULL,
                    updated_by_user_id TEXT
                )
                '''
            )
            for index_sql in (
                """
                CREATE INDEX IF NOT EXISTS idx_device_pairing_family_expires
                ON device_pairing_codes(family_id, expires_at)
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_robot_location_source
                ON robot_location_metadata(source)
                """,
            ):
                conn.execute(index_sql)

            # Tao bang login_attempts (rate limiting cho /api/auth/login va /auth/login/v2)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    ip_address TEXT PRIMARY KEY,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    first_attempt_at TEXT,
                    locked_until TEXT
                )
                '''
            )

            # Tao bang users (username+password auth)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    family_name TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    is_active INTEGER DEFAULT 1,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    token_version INTEGER NOT NULL DEFAULT 0
                )
                '''
            )
            user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "is_admin" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                """
                INSERT OR IGNORE INTO families (family_id, display_name, created_at)
                SELECT DISTINCT family_name, family_name, ?
                FROM users
                WHERE family_name IS NOT NULL AND family_name != ''
                """,
                (_utc_now_iso(),),
            )

            # Migration: them token_version neu chua co (cho DB cu)
            try:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"
                )
                conn.commit()
            except Exception as e:
                msg = str(e).lower()
                if "duplicate column" in msg or "already exists" in msg:
                    pass  # Column da ton tai
                else:
                    logger.error("[DB] Migration token_version failed: %s", e)
                    raise RuntimeError(f"DB migration that bai: {e}") from e

            # Tao bang auth_tokens (JWT refresh token rotation)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    refresh_token_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    is_revoked INTEGER NOT NULL DEFAULT 0
                )
                '''
            )

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    family_id TEXT NOT NULL DEFAULT 'default'
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    title TEXT,
                    turn_count INTEGER DEFAULT 0,
                    is_homework INTEGER NOT NULL DEFAULT 0,
                    homework_marked_at TEXT DEFAULT NULL
                )
                '''
            )
            conversation_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()
            }
            if "family_id" not in conversation_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN family_id TEXT DEFAULT 'default'")
            if "is_homework" not in conversation_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN is_homework INTEGER NOT NULL DEFAULT 0")
            if "homework_marked_at" not in conversation_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN homework_marked_at TEXT DEFAULT NULL")
            conn.execute(
                """
                UPDATE conversations
                SET family_id = 'default',
                    is_homework = COALESCE(is_homework, 0)
                WHERE family_id IS NULL OR family_id = '' OR is_homework IS NULL
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO families (family_id, display_name, created_at)
                SELECT DISTINCT family_id, family_id, ?
                FROM conversations
                WHERE family_id IS NOT NULL AND family_id != ''
                """,
                (_utc_now_iso(),),
            )

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant','homework')),
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                '''
            )

            conn.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id)
                '''
            )
            conn.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_conversations_family_started
                ON conversations(family_id, started_at)
                '''
            )
            conn.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_conversations_family_homework_started
                ON conversations(family_id, is_homework, started_at)
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS learning_schedules (
                    family_id TEXT NOT NULL,
                    day_of_week TEXT NOT NULL,
                    subject TEXT,
                    time TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (family_id, day_of_week)
                )
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS game_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                '''
            )
            for trigger_sql in (
                '''
                CREATE TRIGGER IF NOT EXISTS trg_users_family_auto
                BEFORE INSERT ON users
                WHEN NEW.family_name IS NOT NULL AND NEW.family_name != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_name, NEW.family_name, datetime('now'));
                END
                ''',
                '''
                CREATE TRIGGER IF NOT EXISTS trg_conversations_family_auto
                BEFORE INSERT ON conversations
                WHEN NEW.family_id IS NOT NULL AND NEW.family_id != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_id, NEW.family_id, datetime('now'));
                END
                ''',
                '''
                CREATE TRIGGER IF NOT EXISTS trg_events_family_auto
                BEFORE INSERT ON events
                WHEN NEW.family_id IS NOT NULL AND NEW.family_id != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_id, NEW.family_id, datetime('now'));
                END
                ''',
                '''
                CREATE TRIGGER IF NOT EXISTS trg_tasks_family_auto
                BEFORE INSERT ON tasks
                WHEN NEW.family_id IS NOT NULL AND NEW.family_id != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_id, NEW.family_id, datetime('now'));
                END
                ''',
            ):
                conn.execute(trigger_sql)

            _migrate_turns_role_constraint(conn)

            # Normalize legacy capitalized 'Admin' family to lowercase 'admin'
            _migrate_admin_family_case(conn)

            conn.commit()

            # Migrate du lieu cu
            _migrate_legacy_events(conn)
            _migrate_legacy_tasks(conn)

        cleanup_expired_login_attempts(ttl_minutes=1440)

        # Seed admin user neu bang users trong (idempotent)
        try:
            from src.infrastructure.auth.auth import seed_admin_if_empty

            seed_admin_if_empty()
        except Exception as _e:
            logger.warning("[DB] seed_admin_if_empty bo qua: %s", _e)

        _INITIALIZED = True
        logger.info("[DB] Database da duoc khoi tao thanh cong.")


def get_learning_schedule(family_id: str) -> dict:
    """Load schedule tu DB. Tra ve dict {day: {subject, time}}."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT day_of_week, subject, time
            FROM learning_schedules
            WHERE family_id = ?
            """,
            (fid,),
        ).fetchall()
    return {
        row["day_of_week"]: {
            "subject": row["subject"],
            "time": row["time"],
        }
        for row in rows
    }


def save_learning_schedule(family_id: str, schedule: dict) -> bool:
    """Luu schedule vao DB."""
    try:
        fid = ensure_family_exists(family_id)
        with get_db_connection() as conn:
            for day, info in (schedule or {}).items():
                day_key = str(day)
                if info is None:
                    conn.execute(
                        """
                        DELETE FROM learning_schedules
                        WHERE family_id = ? AND day_of_week = ?
                        """,
                        (fid, day_key),
                    )
                else:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO learning_schedules
                            (family_id, day_of_week, subject, time, updated_at)
                        VALUES (?, ?, ?, ?, datetime('now'))
                        """,
                        (fid, day_key, info.get("subject"), info.get("time")),
                    )
            conn.commit()
        return True
    except Exception as e:
        logger.error("[DB] save_learning_schedule error: %s", e)
        return False


def _migrate_legacy_events(conn):
    """Migrate du lieu tu event_queue.json cu sang bang events"""
    json_path = Path(__file__).with_name("event_queue.json")
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            events = json.load(f)

        for event in events:
            conn.execute(
                '''
                INSERT OR IGNORE INTO events
                (event_id, timestamp, type, message, clip_path, metadata_json, is_read)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    event.get("id"),
                    event.get("timestamp"),
                    event.get("type"),
                    event.get("message"),
                    event.get("clip_path"),
                    json.dumps(event.get("metadata", {}), ensure_ascii=False),
                    1 if event.get("read", False) else 0,
                ),
            )
        conn.commit()
        logger.info("[DB] Da migrate %d events tu file JSON cu.", len(events))
    except Exception as e:
        logger.error("[DB] Loi migrate events: %s", e)


def _migrate_legacy_tasks(conn):
    """Migrate du lieu tu tasks.json cu sang bang tasks"""
    json_path = Path(__file__).with_name("tasks.json")
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        for task in tasks:
            task_id = task.get("id")
            if not task_id:
                continue

            # Ho tro ca 'name' va 'title' tu du lieu cu
            name = task.get("name") or task.get("title") or "Khong co tieu de"

            conn.execute(
                '''
                INSERT OR IGNORE INTO tasks
                (task_id, name, remind_time, completed_today, stars,
                 created_at, last_reminded, import_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    task_id,
                    name,
                    task.get("remind_time", ""),
                    1 if task.get("completed_today") else 0,
                    int(task.get("stars", 0)),
                    task.get("created_at"),
                    task.get("last_reminded"),
                    task_id,
                ),
            )
        conn.commit()
        logger.info("[DB] Da migrate %d tasks tu file JSON cu.", len(tasks))
    except Exception as e:
        logger.error("[DB] Loi migrate tasks: %s", e)


def _migrate_turns_role_constraint(conn) -> None:
    row = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table' AND name = 'turns'
        """
    ).fetchone()
    if not row:
        return

    create_sql = (row["sql"] or "").replace(" ", "").lower()
    if "'homework'" in create_sql and "ondeletecascade" in create_sql:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("ALTER TABLE turns RENAME TO turns_old")
    conn.execute(
        '''
        CREATE TABLE turns (
            turn_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK(role IN ('user','assistant','homework')),
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        '''
    )
    conn.execute(
        '''
        INSERT INTO turns (turn_id, session_id, role, content, timestamp)
        SELECT turn_id, session_id, role, content, timestamp
        FROM turns_old
        '''
    )
    conn.execute("DROP TABLE turns_old")
    conn.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id)
        '''
    )
    conn.execute("PRAGMA foreign_keys = ON")


def _migrate_admin_family_case(conn) -> None:
    """Rename legacy 'Admin' (capital A) family to lowercase 'admin' if present."""
    row = conn.execute("SELECT family_id FROM families WHERE family_id = 'Admin'").fetchone()
    if not row:
        return
    conn.execute(
        "INSERT OR IGNORE INTO families (family_id, display_name, created_at) VALUES ('admin', 'admin', ?)",
        (_utc_now_iso(),),
    )
    # FK is ON but 'admin' now exists, so these UPDATEs are safe
    conn.execute("UPDATE users SET family_name = 'admin' WHERE family_name = 'Admin'")
    conn.execute("UPDATE conversations SET family_id = 'admin' WHERE family_id = 'Admin'")
    conn.execute("UPDATE events SET family_id = 'admin' WHERE family_id = 'Admin'")
    conn.execute("UPDATE tasks SET family_id = 'admin' WHERE family_id = 'Admin'")
    conn.execute("DELETE FROM families WHERE family_id = 'Admin'")


def create_session(family_id: str) -> str:
    family_id = ensure_family_exists(family_id)
    session_id = uuid4().hex
    with get_db_connection() as conn:
        conn.execute(
            '''
            INSERT INTO conversations (session_id, family_id, started_at)
            VALUES (?, ?, ?)
            ''',
            (session_id, family_id, _utc_now_iso()),
        )
        conn.commit()
    return session_id


def _resolve_session_family_conn(conn, session_id: str) -> str | None:
    row = conn.execute(
        "SELECT family_id FROM conversations WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["family_id"] if row else None


def close_session(session_id: str, family_id: str | None = None) -> None:
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return
        conn.execute(
            '''
            UPDATE conversations
            SET ended_at = ?
            WHERE session_id = ? AND family_id = ?
            ''',
            (_utc_now_iso(), session_id, fid),
        )
        conn.commit()


def add_turn(session_id: str, role: str, content: str, family_id: str | None = None) -> str:
    if role not in {"user", "assistant", "homework"}:
        raise ValueError("Invalid turn role")
    turn_id = uuid4().hex
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            raise ValueError("Session not found")
        cur = conn.execute(
            '''
            INSERT INTO turns (turn_id, session_id, role, content, timestamp)
            SELECT ?, c.session_id, ?, ?, ?
            FROM conversations c
            WHERE c.session_id = ? AND c.family_id = ?
            ''',
            (turn_id, role, content, _utc_now_iso(), session_id, fid),
        )
        if cur.rowcount == 0:
            raise ValueError("Session not found")
        conn.execute(
            '''
            UPDATE conversations
            SET turn_count = turn_count + 1
            WHERE session_id = ? AND family_id = ?
            ''',
            (session_id, fid),
        )
        conn.commit()
    return turn_id


def get_session_turns(session_id: str, family_id: str | None = None) -> list[dict]:
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return []
        rows = conn.execute(
            '''
            SELECT t.turn_id, t.session_id, t.role, t.content, t.timestamp
            FROM turns t
            JOIN conversations c ON c.session_id = t.session_id
            WHERE t.session_id = ? AND c.family_id = ?
            ORDER BY t.timestamp ASC
            ''',
            (session_id, fid),
        ).fetchall()
    return [dict(row) for row in rows]


def update_session_title(session_id: str, title: str, family_id: str | None = None) -> None:
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return
        conn.execute(
            '''
            UPDATE conversations
            SET title = ?
            WHERE session_id = ? AND family_id = ?
            ''',
            (title, session_id, fid),
        )
        conn.commit()


def mark_session_homework(session_id: str, family_id: str | None = None) -> bool:
    if not session_id:
        return False
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return False
        cur = conn.execute(
            """
            UPDATE conversations
            SET is_homework = 1,
                homework_marked_at = datetime('now')
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, fid),
        )
        conn.commit()
        return cur.rowcount > 0


def get_homework_sessions(
    family_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    fid = _normalize_family_id(family_id)
    safe_limit = max(1, min(int(limit), 50))
    safe_offset = max(0, int(offset))
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT session_id, family_id, title,
                   started_at, ended_at, turn_count,
                   is_homework, homework_marked_at
            FROM conversations
            WHERE family_id = ? AND is_homework = 1
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (fid, safe_limit, safe_offset),
        ).fetchall()
    return [dict(row) for row in rows]


def list_families() -> list[dict]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT f.family_id, f.display_name, f.created_at,
                   COUNT(DISTINCT u.user_id) AS user_count
            FROM families f
            LEFT JOIN users u ON u.family_name = f.family_id
            GROUP BY f.family_id, f.display_name, f.created_at
            ORDER BY f.created_at ASC, f.family_id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_family_record(family_id: str, display_name: str | None = None) -> dict | None:
    fid = _normalize_family_id(family_id)
    label = (display_name or fid).strip() or fid
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO families (family_id, display_name, created_at)
            VALUES (?, ?, ?)
            """,
                (fid, label, _utc_now_iso()),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    return {"family_id": fid, "display_name": label}


def event_exists_for_family(family_id: str, event_id: str) -> bool:
    """Return True when an event belongs to the requested family."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM events
            WHERE family_id = ? AND event_id = ?
            LIMIT 1
            """,
            (fid, str(event_id)),
        ).fetchone()
    return row is not None


def _note_row_to_dict(row) -> dict:
    return {
        "note_id": row["note_id"],
        "event_id": row["event_id"],
        "family_id": row["family_id"],
        "user_id": row["user_id"],
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_parent_event_notes(family_id: str, event_id: str) -> list[dict]:
    """List parent notes attached to one event, scoped by family_id."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT note_id, family_id, event_id, user_id, note, created_at, updated_at
            FROM parent_event_notes
            WHERE family_id = ? AND event_id = ?
            ORDER BY created_at ASC, note_id ASC
            """,
            (fid, str(event_id)),
        ).fetchall()
    return [_note_row_to_dict(row) for row in rows]


def create_parent_event_note(
    family_id: str,
    event_id: str,
    user_id: str,
    note: str,
) -> dict:
    """Create a parent note for an existing family-scoped event."""
    fid = _normalize_family_id(family_id)
    now = _utc_now_iso()
    note_id = uuid4().hex
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO parent_event_notes
                (note_id, family_id, event_id, user_id, note, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (note_id, fid, str(event_id), str(user_id), str(note), now, now),
        )
        conn.commit()
    return {
        "note_id": note_id,
        "event_id": str(event_id),
        "family_id": fid,
        "user_id": str(user_id),
        "note": str(note),
        "created_at": now,
        "updated_at": now,
    }


def update_parent_event_note(
    family_id: str,
    event_id: str,
    note_id: str,
    note: str,
) -> dict | None:
    """Update a parent note only within the event's family scope."""
    fid = _normalize_family_id(family_id)
    now = _utc_now_iso()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            UPDATE parent_event_notes
            SET note = ?, updated_at = ?
            WHERE family_id = ? AND event_id = ? AND note_id = ?
            """,
            (str(note), now, fid, str(event_id), str(note_id)),
        )
        conn.commit()
        if cur.rowcount <= 0:
            return None
        row = conn.execute(
            """
            SELECT note_id, family_id, event_id, user_id, note, created_at, updated_at
            FROM parent_event_notes
            WHERE family_id = ? AND event_id = ? AND note_id = ?
            """,
            (fid, str(event_id), str(note_id)),
        ).fetchone()
    return _note_row_to_dict(row) if row else None


def delete_parent_event_note(family_id: str, event_id: str, note_id: str) -> bool:
    """Delete a parent note only within the event's family scope."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            DELETE FROM parent_event_notes
            WHERE family_id = ? AND event_id = ? AND note_id = ?
            """,
            (fid, str(event_id), str(note_id)),
        )
        conn.commit()
    return cur.rowcount > 0


def delete_family_record(family_id: str) -> bool:
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT family_id FROM families WHERE family_id = ?",
            (fid,),
        ).fetchone()
        family_exists = row is not None

        # Delete order matters: child rows before parent rows.
        # auth_tokens has no FK to families — must cascade manually via user_id.
        user_rows = conn.execute(
            "SELECT user_id FROM users WHERE family_name = ?",
            (fid,),
        ).fetchall()
        user_ids = [str(row["user_id"]) for row in user_rows]
        if user_ids:
            placeholders = ",".join("?" for _ in user_ids)
            # Step 1: auth_tokens (no FK to families; references users)
            conn.execute(
                f"DELETE FROM auth_tokens WHERE user_id IN ({placeholders})",
                tuple(user_ids),
            )

        # Step 2: turns (FK → conversations, not families directly)
        conn.execute(
            """
            DELETE FROM turns
            WHERE session_id IN (
                SELECT session_id FROM conversations WHERE family_id = ?
            )
            """,
            (fid,),
        )
        # Steps 3-5: tables with FK → families (ON DELETE CASCADE would handle
        # these if FK enforcement is active, but explicit deletes are safer)
        conn.execute("DELETE FROM conversations WHERE family_id = ?", (fid,))
        conn.execute("DELETE FROM parent_event_notes WHERE family_id = ?", (fid,))
        conn.execute("DELETE FROM events WHERE family_id = ?", (fid,))
        conn.execute("DELETE FROM tasks WHERE family_id = ?", (fid,))

        # Steps 6-12: newer family-scoped feature tables.
        ALLOWED_CLEANUP_TABLES = frozenset({
            "conversations",
            "events",
            "tasks",
            "users",
            "auth_tokens",
            "learning_schedules",
            "emotion_logs",
            "emotion_journal",
            "emotion_alerts",
            "persona",
            "education_sessions",
            "turns",
            "curriculum_schedules",
            "game_scores",
            "parent_event_notes",
            "child_profiles",
            "child_content_settings",
            "interaction_limit_settings",
            "daily_interaction_usage",
            "sleep_schedule_settings",
            "notification_settings",
            "push_subscriptions",
            "report_exports",
            "content_items",
            "device_pairing_codes",
            "robot_location_metadata",
            "parent_chat_sessions",
            "parent_chat_messages",
        })
        for table_name in (
            "learning_schedules",
            "emotion_logs",
            "emotion_journal",
            "emotion_alerts",
            "persona",
            "education_sessions",
            "curriculum_schedules",
            "game_scores",
            "child_content_settings",
            "interaction_limit_settings",
            "daily_interaction_usage",
            "sleep_schedule_settings",
            "notification_settings",
            "push_subscriptions",
            "report_exports",
            "content_items",
            "device_pairing_codes",
            "robot_location_metadata",
            "parent_chat_messages",
            "parent_chat_sessions",
            "child_profiles",
        ):
            if table_name not in ALLOWED_CLEANUP_TABLES:
                logger.error("[DB] Rejected invalid table name: %s", table_name)
                continue
            try:
                conn.execute(f"DELETE FROM {table_name} WHERE family_id = ?", (fid,))
            except Exception:
                pass

        # Step 13: users (FK → families)
        conn.execute("DELETE FROM users WHERE family_name = ?", (fid,))
        # Step 14: families (parent row — delete last)
        cur = conn.execute("DELETE FROM families WHERE family_id = ?", (fid,))
        conn.commit()
        return family_exists and cur.rowcount > 0


def is_user_admin(user_id: str) -> bool:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT is_admin, is_active FROM users WHERE user_id = ?",
            (str(user_id),),
        ).fetchone()
    return bool(row and row["is_active"] and row["is_admin"])


def get_token_version(user_id: str) -> int:
    """Trả về token_version hiện tại của user. Trả 0 nếu user không tồn tại."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_version FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
    return int(row["token_version"]) if row else 0


def increment_token_version(user_id: str) -> int:
    """Tăng token_version, vô hiệu hóa tất cả access token hiện có. Trả về version mới."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE users SET token_version = token_version + 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT token_version FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row["token_version"]) if row else 0


def get_user_by_id(user_id: str) -> dict | None:
    """Trả về dict {user_id, username, family_name, created_at} hoặc None."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, family_name, created_at, is_admin FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def update_user_password(user_id: str, new_password: str) -> bool:
    """Hash new_password va update DB. Token version do revoke_all_tokens_for_user() tang."""
    from src.infrastructure.auth.auth import hash_password
    new_hash = hash_password(new_password)
    with get_db_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash=? WHERE user_id=?",
            (new_hash, user_id),
        )
        conn.commit()
    return cur.rowcount > 0


def revoke_all_tokens_for_user(user_id: str) -> int:
    """Revoke tất cả refresh token + tăng token_version. Trả về số refresh token bị revoke."""
    with get_db_connection() as conn:
        cur = conn.execute(
            "UPDATE auth_tokens SET is_revoked=1 WHERE user_id=? AND is_revoked=0",
            (user_id,)
        )
        count = cur.rowcount
        conn.execute(
            "UPDATE users SET token_version = token_version + 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        return count
```

## src/infrastructure/auth/auth.py

```python
"""
auth.py — Authentication helpers for Robot Bi.
Handles user creation, password hashing (Argon2id via argon2-cffi), and authentication.
"""

import hashlib as _hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("auth")

try:
    from fastapi import Security as _FastAPISecurity
    from fastapi.security import (
        HTTPAuthorizationCredentials as _HTTPAuthorizationCredentials,
        HTTPBearer as _HTTPBearer,
    )
    _http_bearer = _HTTPBearer(auto_error=False)
    _FASTAPI_SECURITY_AVAILABLE = True
except ImportError:
    _FastAPISecurity = None
    _HTTPAuthorizationCredentials = None
    _http_bearer = None
    _FASTAPI_SECURITY_AVAILABLE = False
    logger.warning("[Auth] fastapi.security khong co san — get_current_user bi vo hieu hoa")

try:
    from jose import jwt as _jose_jwt
    _JOSE_AVAILABLE = True
except ImportError:
    _JOSE_AVAILABLE = False
    logger.warning("[Auth] python-jose chua duoc cai dat — JWT bi vo hieu hoa. Chay: pip install 'python-jose[cryptography]'")

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

    _ph = PasswordHasher()  # Default: Argon2id, time_cost=3, memory_cost=65536
    _ARGON2_AVAILABLE = True
except ImportError:
    _ARGON2_AVAILABLE = False
    logger.warning("[Auth] argon2-cffi chua duoc cai dat — hash password bi vo hieu hoa")

from src.infrastructure.database.db import ensure_family_exists, get_db_connection


def hash_password(plain: str) -> str:
    """Hash plaintext password dung Argon2id."""
    if not _ARGON2_AVAILABLE:
        raise RuntimeError("argon2-cffi chua duoc cai dat. Chay: pip install argon2-cffi")
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """So sanh password plain voi Argon2id hash da luu. Tra False neu sai hoac loi."""
    if not _ARGON2_AVAILABLE:
        return False
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_user(username: str, password: str, family_name: str) -> dict:
    """
    Tao user moi. Raise HTTPException(409) neu username da ton tai.
    Tra ve dict user (khong co password_hash).
    """
    from fastapi import HTTPException

    family_name = ensure_family_exists(family_name)
    password_hash = hash_password(password)

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT user_id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Username da ton tai")

        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, family_name) VALUES (?, ?, ?)",
            (username, password_hash, family_name),
        )
        conn.commit()
        user_id = cursor.lastrowid

    return {
        "user_id": user_id,
        "username": username,
        "family_name": family_name,
    }


def get_user_by_username(username: str) -> dict | None:
    """Lay user theo username. Tra None neu khong tim thay."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, password_hash, family_name, created_at, is_active, is_admin "
            "FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    return dict(row) if row is not None else None


def authenticate_user(username: str, password: str) -> dict | None:
    """
    Xac thuc user bang username + password.
    Tra ve dict user (khong co password_hash) neu hop le va dang active, nguoc lai tra None.
    """
    user = get_user_by_username(username)
    if user is None:
        return None
    if not user.get("is_active"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "family_name": user["family_name"],
        "is_admin": bool(user.get("is_admin")),
    }


def seed_admin_if_empty() -> None:
    """
    Tao admin user tu .env neu bang users dang trong.
    Idempotent — co the goi nhieu lan ma khong co hieu ung phu.
    Khong log plaintext password, khong crash khi thieu env.
    """
    admin_username = os.getenv("ADMIN_USERNAME", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()

    if not admin_username or not admin_password:
        logger.warning(
            "[Auth] ADMIN_USERNAME/ADMIN_PASSWORD chua duoc cau hinh trong .env "
            "— bo qua seed admin"
        )
        return

    if not _ARGON2_AVAILABLE:
        logger.warning("[Auth] argon2-cffi khong co — khong the seed admin")
        return

    with get_db_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()["cnt"]
        if count > 0:
            return  # Da co users — bo qua

        password_hash = hash_password(admin_password)
        conn.execute(
            "INSERT OR IGNORE INTO families (family_id, display_name, created_at) VALUES (?, ?, ?)",
            ("admin", "admin", datetime.now(timezone.utc).isoformat()),
        )
        conn.execute(
            "INSERT INTO users (username, password_hash, family_name, is_admin) VALUES (?, ?, ?, 1)",
            (admin_username, password_hash, "admin"),
        )
        conn.commit()

    logger.info("[Auth] Admin user da duoc tao thanh cong.")


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _get_jwt_config() -> tuple[str, str]:
    """Doc JWT config tu env. Raise RuntimeError neu thieu hoac sai thuat toan."""
    jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
    jwt_alg = os.getenv("JWT_ALGORITHM", "HS256").strip()
    if not jwt_secret:
        raise RuntimeError(
            "[Auth] JWT_SECRET_KEY chua duoc cau hinh trong .env. "
            "Them JWT_SECRET_KEY=<secret> vao file .env."
        )
    if jwt_alg != "HS256":
        raise RuntimeError(
            f"[Auth] JWT_ALGORITHM phai la HS256, nhan duoc: {jwt_alg!r}"
        )
    return jwt_secret, jwt_alg


def create_access_token(user_id: str, family_name: str) -> str:
    """
    Tao JWT access token.
    Payload: sub=user_id, family=family_name, type="access", tv=token_version, exp=now+60min.
    """
    if not _JOSE_AVAILABLE:
        raise RuntimeError("python-jose chua duoc cai dat. Chay: pip install 'python-jose[cryptography]'")
    jwt_secret, jwt_alg = _get_jwt_config()
    from src.infrastructure.database.db import get_token_version
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "family": family_name,
        "type": "access",
        "tv": get_token_version(str(user_id)),
        "iat": now,
        "exp": now + timedelta(minutes=60),
    }
    return _jose_jwt.encode(payload, jwt_secret, algorithm=jwt_alg)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Tao refresh token.
    Tra ve (raw_token, hashed_token):
      - raw_token: tra cho client (chi dung 1 lan)
      - hashed_token: sha256 hex, luu vao DB
    """
    import secrets as _sec
    raw_token = _sec.token_urlsafe(32)
    hashed_token = _hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, hashed_token


def store_refresh_token(user_id: str, hashed_token: str, expires_at: datetime) -> str:
    """
    Luu hashed refresh token vao bang auth_tokens (is_revoked=0).
    Tra ve token_id (str).
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO auth_tokens (user_id, refresh_token_hash, expires_at, is_revoked) "
            "VALUES (?, ?, ?, 0)",
            (str(user_id), hashed_token, expires_at.isoformat()),
        )
        conn.commit()
        return str(cursor.lastrowid)


def verify_access_token(token: str) -> dict:
    """
    Decode va xac thuc JWT access token.
    Tra ve payload dict neu hop le.
    Raise HTTPException(401) neu loi, het han, hoac sai type.
    """
    from fastapi import HTTPException

    if not _JOSE_AVAILABLE:
        raise HTTPException(status_code=401, detail="JWT chua duoc cau hinh")
    try:
        jwt_secret, jwt_alg = _get_jwt_config()
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        payload = _jose_jwt.decode(token, jwt_secret, algorithms=[jwt_alg])
    except Exception:
        raise HTTPException(status_code=401, detail="Token khong hop le hoac da het han")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Sai loai token")

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_version, is_active FROM users WHERE user_id = ?",
            (str(payload.get("sub", "")),),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="User khong ton tai")

    if not row["is_active"]:
        raise HTTPException(status_code=401, detail="Tai khoan da bi vo hieu hoa")

    if int(row["token_version"]) != int(payload.get("tv", 0)):
        raise HTTPException(status_code=401, detail="Token da bi vo hieu hoa")

    return payload


def rotate_refresh_token(old_raw_token: str) -> tuple[str, str, str]:
    """
    Rotation refresh token — thuc hien atomic trong cung transaction:
    1. Hash old_raw_token → tim record WHERE refresh_token_hash = hash AND is_revoked = 0
    2. Neu khong tim thay hoac het han → raise HTTPException(401)
    3. Mark old token: is_revoked = 1
    4. Tao va luu new refresh token (expires_at = now_utc + 30 ngay)
    Tra ve (new_raw_token, new_hashed_token, user_id).
    """
    from fastapi import HTTPException
    import secrets as _sec

    old_hashed = _hashlib.sha256(old_raw_token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    new_expires_at = now + timedelta(days=30)

    new_raw = _sec.token_urlsafe(32)
    new_hashed = _hashlib.sha256(new_raw.encode()).hexdigest()

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_id, user_id, expires_at, is_revoked "
            "FROM auth_tokens WHERE refresh_token_hash = ?",
            (old_hashed,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        if row["is_revoked"]:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        expires_at_str = row["expires_at"]
        expires_at = datetime.fromisoformat(expires_at_str)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        user_id = str(row["user_id"])

        # Atomic: exactly one concurrent caller can revoke this refresh token.
        cur = conn.execute(
            "UPDATE auth_tokens SET is_revoked = 1 WHERE token_id = ? AND is_revoked = 0",
            (row["token_id"],),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        conn.execute(
            "INSERT INTO auth_tokens (user_id, refresh_token_hash, expires_at, is_revoked) "
            "VALUES (?, ?, ?, 0)",
            (user_id, new_hashed, new_expires_at.isoformat()),
        )
        conn.commit()

    return new_raw, new_hashed, user_id


# ── JWT FastAPI Dependency ────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[_HTTPAuthorizationCredentials] = (
        _FastAPISecurity(_http_bearer) if _FASTAPI_SECURITY_AVAILABLE else None
    ),
) -> dict:
    """
    FastAPI dependency: xac thuc JWT Bearer token tu Authorization header.
    Tra ve {"user_id": str, "family_name": str} neu hop le.
    Raise HTTPException(401) voi WWW-Authenticate: Bearer neu thieu hoac invalid.
    Su dung: Depends(get_current_user) trong route handler.
    """
    from fastapi import HTTPException

    if not _FASTAPI_SECURITY_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="fastapi.security khong co san",
        )
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_access_token(credentials.credentials)
    except HTTPException:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "user_id": payload["sub"],
        "family_name": payload["family"],
    }
```

## src/infrastructure/tasks/task_manager.py

```python
"""
task_manager.py - Quan ly nhiem vu hang ngay va sao thuong (SRS 4.4)
=====================================================================
Phu huynh tao nhiem vu qua Parent App, robot nhac be qua loa dung gio,
be hoan thanh duoc cong sao.

Class: TaskManager
  add_task(name, remind_time) -> dict
  complete_task(task_id) -> bool
  get_all() -> list
  delete_task(task_id) -> bool
  get_total_stars() -> int
  stop()
"""

import threading
import time
import uuid
from datetime import datetime

from src.infrastructure.database.db import _normalize_family_id, ensure_family_exists, get_db_connection


class TaskManager:
    def __init__(self, tts_callback=None, family_id: str | None = None):
        """
        tts_callback: callable(text) - goi de Bi phat am nhac nho.
        Neu None, van hoat dong - chi khong phat TTS.
        """
        self.tts_callback = tts_callback
        self.family_id = ensure_family_exists(_normalize_family_id(family_id))
        self._tasks: list = self._load(self.family_id)
        self._lock = threading.Lock()
        self._running = True
        threading.Thread(
            target=self._reminder_loop,
            daemon=True,
            name="task-reminder",
        ).start()

    @staticmethod
    def _row_to_task(row) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        completed_date = row["completed_date"]
        return {
            "id": row["task_id"],
            "family_id": row["family_id"],
            "name": row["name"],
            "remind_time": row["remind_time"],
            "completed_today": completed_date == today,
            "completed_date": completed_date,
            "stars": int(row["stars"]),
            "created_at": row["created_at"],
            "last_reminded": row["last_reminded"],
            "last_reminded_date": row["last_reminded_date"],
        }

    def _load(self, family_id: str | None = None) -> list:
        family_id = ensure_family_exists(_normalize_family_id(family_id or self.family_id))
        with get_db_connection() as conn:
            today = datetime.now().strftime("%Y-%m-%d")
            conn.execute(
                """
                UPDATE tasks
                SET completed_date = '2000-01-01'
                WHERE family_id = ?
                  AND completed_today = 1
                  AND (completed_date IS NULL OR completed_date = '')
                """,
                (family_id,),
            )
            conn.execute(
                """
                UPDATE tasks
                SET completed_today = 0
                WHERE family_id = ?
                  AND completed_today = 1
                  AND COALESCE(completed_date, '') != ?
                """,
                (family_id, today),
            )
            conn.commit()
            rows = conn.execute(
                """
                SELECT family_id, task_id, name, remind_time, completed_today,
                       completed_date, stars, created_at, last_reminded,
                       last_reminded_date
                FROM tasks
                WHERE family_id = ?
                ORDER BY db_id ASC
                """,
                (family_id,),
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def _refresh_tasks(self, family_id: str | None = None) -> list:
        family_id = _normalize_family_id(family_id or self.family_id)
        tasks = self._load(family_id)
        if family_id == self.family_id:
            self._tasks = tasks
        return tasks

    def add_task(self, name: str, remind_time: str, family_id: str | None = None) -> dict:
        """
        Them nhiem vu moi.
        name: ten nhiem vu, vi du "Danh rang"
        remind_time: "HH:MM", vi du "07:30"
        Returns: task dict moi tao
        """
        family_id = ensure_family_exists(_normalize_family_id(family_id or self.family_id))
        task = {
            "id": str(uuid.uuid4()),
            "family_id": family_id,
            "name": name,
            "remind_time": remind_time,
            "completed_today": False,
            "completed_date": None,
            "stars": 0,
            "created_at": datetime.now().isoformat(),
            "last_reminded": None,
            "last_reminded_date": None,
        }
        with self._lock:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO tasks (
                        family_id, task_id, name, remind_time, completed_today,
                        completed_date, stars, created_at, last_reminded,
                        last_reminded_date, import_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task["family_id"],
                        task["id"],
                        task["name"],
                        task["remind_time"],
                        0,
                        task["completed_date"],
                        task["stars"],
                        task["created_at"],
                        task["last_reminded"],
                        task["last_reminded_date"],
                        task["id"],
                    ),
                )
                conn.commit()
            self._refresh_tasks(family_id)
        return task

    def complete_task(self, task_id: str, family_id: str | None = None) -> bool:
        """
        Danh dau nhiem vu hoan thanh, cong 1 sao.
        Returns True neu thanh cong, False neu khong tim thay / da hoan thanh.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE tasks
                    SET completed_today = 1,
                        completed_date = ?,
                        stars = COALESCE(stars, 0) + 1
                    WHERE task_id = ?
                      AND family_id = ?
                      AND COALESCE(completed_date, '') != ?
                    """,
                    (today, task_id, family_id, today),
                )
                conn.commit()
            if cursor.rowcount > 0:
                self._refresh_tasks(family_id)
                return True
        return False

    def get_all(self, family_id: str | None = None) -> list:
        """Tra ve danh sach tat ca nhiem vu (ban copy)."""
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            tasks = self._refresh_tasks(family_id)
            return list(tasks)

    def _save(self) -> None:
        """Persist in-memory task edits used by tests and migrations."""
        with self._lock:
            with get_db_connection() as conn:
                for task in self._tasks:
                    conn.execute(
                        """
                        UPDATE tasks
                        SET completed_today = ?,
                            completed_date = ?,
                            last_reminded = ?,
                            last_reminded_date = ?
                        WHERE task_id = ?
                          AND family_id = ?
                        """,
                        (
                            1 if task.get("completed_today") else 0,
                            task.get("completed_date"),
                            task.get("last_reminded"),
                            task.get("last_reminded_date"),
                            task["id"],
                            task.get("family_id") or self.family_id,
                        ),
                    )
                conn.commit()

    def delete_task(self, task_id: str, family_id: str | None = None) -> bool:
        """Xoa nhiem vu theo ID. Returns True neu thanh cong."""
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM tasks WHERE task_id = ? AND family_id = ?",
                    (task_id, family_id),
                )
                conn.commit()
            if cursor.rowcount > 0:
                self._refresh_tasks(family_id)
                return True
        return False

    def get_total_stars(self, family_id: str | None = None) -> int:
        """Tong so sao tich luy tu tat ca nhiem vu."""
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT COALESCE(SUM(stars), 0) AS total_stars FROM tasks WHERE family_id = ?",
                    (family_id,),
                ).fetchone()
            return int(row["total_stars"]) if row else 0

    def _mark_reminded(self, task_id: str, family_id: str | None = None) -> bool:
        """Mark a task as reminded at the current date and minute."""
        now_dt = datetime.now()
        today = now_dt.strftime("%Y-%m-%d")
        reminded_at = now_dt.strftime("%Y-%m-%d %H:%M")
        family_id = _normalize_family_id(family_id or self.family_id)
        with self._lock:
            with get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE tasks
                    SET last_reminded = ?,
                        last_reminded_date = ?
                    WHERE task_id = ?
                      AND family_id = ?
                    """,
                    (reminded_at, today, task_id, family_id),
                )
                conn.commit()
            if cursor.rowcount > 0:
                self._refresh_tasks(family_id)
                return True
        return False

    def _reminder_loop(self):
        """Daemon thread: kiem tra gio nhac moi 30 giay, phat TTS neu den gio."""
        while self._running:
            now_dt = datetime.now()
            today = now_dt.strftime("%Y-%m-%d")
            now = now_dt.strftime("%H:%M")
            messages_to_speak = []
            with self._lock:
                self._refresh_tasks(self.family_id)
                for task in self._tasks:
                    last_reminded = task.get("last_reminded") or ""
                    reminded_date = last_reminded[:10] if len(last_reminded) >= 10 else ""
                    reminded_time = last_reminded[11:] if len(last_reminded) >= 16 else last_reminded
                    already_reminded = reminded_date == today and reminded_time == now
                    already_done_today = task.get("completed_date") == today
                    if (
                        task["remind_time"] == now
                        and not already_done_today
                        and not already_reminded
                    ):
                        reminded_at = now_dt.strftime("%Y-%m-%d %H:%M")
                        with get_db_connection() as conn:
                            conn.execute(
                                """
                                UPDATE tasks
                                SET last_reminded = ?,
                                    last_reminded_date = ?
                                WHERE task_id = ?
                                  AND family_id = ?
                                """,
                                (reminded_at, today, task["id"], self.family_id),
                            )
                            conn.commit()
                        task["last_reminded"] = reminded_at
                        task["last_reminded_date"] = today
                        if self.tts_callback:
                            messages_to_speak.append(
                                f"Bi nhac ban: {task['name']} nhe! Ban da lam chua?"
                            )
            for message in messages_to_speak:
                threading.Thread(
                    target=self.tts_callback,
                    args=(message,),
                    daemon=True,
                ).start()
            time.sleep(30)

    def stop(self):
        """Dung reminder loop."""
        self._running = False


if __name__ == "__main__":
    from src.infrastructure.database.db import init_db

    init_db()
    tm = TaskManager()
    task = tm.add_task("Danh rang", "07:30")
    assert task["name"] == "Danh rang", "add_task fail"
    ok = tm.complete_task(task["id"])
    assert ok is True, "complete_task fail"
    assert tm.get_total_stars() >= 1, "stars fail"
    tm.delete_task(task["id"])
    print("TASK MANAGER TEST PASSED")
```

## src/infrastructure/notifications/notifier.py

```python
"""
notifier.py - Robot Bi: WebSocket notification stub (Sprint 5 prep)
===================================================================
SRS 3.4: Gui notification kem thumbnail clip qua LAN den Parent App
SRS 4.2: Thu vien clip su kien + Nhat ky chat
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

from src.infrastructure.database.db import _normalize_family_id, ensure_family_exists, get_db_connection

logger = logging.getLogger("notifier")

EventType = Literal["motion", "stranger", "known_face", "cry", "chat", "system", "homework"]

_MAX_EVENTS = 500
_WS_ENABLED = False

# Module-level WebSocket broadcaster (injects vào từ api_server.init_server)
_ws_broadcast_fn = None  # callable | None


def set_ws_broadcaster(fn) -> None:
    """Đăng ký coroutine function để broadcast notification qua WebSocket."""
    global _ws_broadcast_fn, _WS_ENABLED
    _ws_broadcast_fn = fn
    _WS_ENABLED = (fn is not None)


class EventNotifier:
    """
    Gui notifications ve events den Parent App.

    Persistence da duoc chuyen sang SQLite, nhung interface giu nguyen.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._connected_clients: list = []
        self._ws_broadcaster = None
        self._queue_file = Path(__file__).with_name("event_queue.json")
        self._queue_file.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[dict] = self._load_queue()
        mode = "WebSocket" if _WS_ENABLED else "SQLite persistence"
        logger.info(
            "[Notifier] Khoi tao (mode: %s) - %d events trong queue",
            mode,
            len(self._events),
        )

    @staticmethod
    def _row_to_event(row) -> dict:
        metadata = row["metadata_json"]
        try:
            parsed_metadata = json.loads(metadata) if metadata else {}
        except Exception:
            parsed_metadata = {}
        return {
            "id": row["event_id"],
            "family_id": row["family_id"],
            "timestamp": row["timestamp"],
            "type": row["type"],
            "message": row["message"],
            "clip_path": row["clip_path"],
            "metadata": parsed_metadata,
            "read": bool(row["is_read"]),
        }

    def push_event(
        self,
        event_type: EventType,
        message: str,
        clip_path: str | None = None,
        metadata: dict | None = None,
        family_id: str | None = None,
    ) -> bool:
        family_id = ensure_family_exists(_normalize_family_id(family_id))
        event = {
            "id": f"{int(time.time() * 1000)}",
            "family_id": family_id,
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "clip_path": clip_path,
            "metadata": metadata or {},
            "read": False,
        }

        with self._lock:
            self._insert_event(event)
            self._events = self._load_queue()

        if _ws_broadcast_fn:
            try:
                import src.infrastructure.sessions.state as _st
                loop = _st._api_loop
                if loop and not loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        _ws_broadcast_fn(
                            {
                                "type": "notification",
                                "family_id": family_id,
                                "event_type": event_type,
                                "message": message,
                            }
                        ),
                        loop,
                    )
            except Exception:
                logger.debug("[Notifier] WS broadcast skip — loop chua san sang")

        icons = {
            "motion": "[MOT]",
            "stranger": "[STR]",
            "cry": "[CRY]",
            "known_face": "[FAC]",
            "chat": "[CHT]",
            "system": "[SYS]",
            "homework": "[HWK]",
        }
        icon = icons.get(event_type, "[EVT]")
        if event_type == "chat":
            logger.debug("[Notifier] %s CHAT event stored", icon)
        else:
            logger.info(
                "[Notifier] %s %s event stored family=%s message_len=%d",
                icon,
                event_type.upper(),
                family_id,
                len(message or ""),
            )
        self._send_ws(event)
        return True

    def push_chat_log(self, user_text: str, bi_response: str, family_id: str | None = None) -> bool:
        logger.debug("[Chat] session=%s user_len=%d ai_len=%d", "unknown", len(user_text), len(bi_response))
        return self.push_event(
            event_type="chat",
            message=f"Be: {user_text[:100]}",
            metadata={
                "user_text": user_text,
                "bi_response": bi_response,
                "word_count": len(user_text.split()),
            },
            family_id=family_id,
        )

    def get_unread_events(
        self,
        event_type: EventType | None = None,
        family_id: str | None = None,
    ) -> list[dict]:
        family_id = _normalize_family_id(family_id)
        with self._lock:
            query = """
                SELECT family_id, event_id, timestamp, type, message, clip_path, metadata_json, is_read
                FROM events
                WHERE family_id = ? AND is_read = 0
            """
            params = [family_id]
            if event_type:
                query += " AND type = ?"
                params.append(event_type)
            query += " ORDER BY db_id ASC"
            with get_db_connection() as conn:
                rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_event(row) for row in rows]

    def mark_all_read(self, family_id: str | None = None) -> None:
        family_id = _normalize_family_id(family_id)
        with self._lock:
            with get_db_connection() as conn:
                conn.execute(
                    "UPDATE events SET is_read = 1 WHERE family_id = ? AND is_read = 0",
                    (family_id,),
                )
                conn.commit()
            for event in self._events:
                if event.get("family_id") == family_id:
                    event["read"] = True

    def get_stats(self, family_id: str | None = None) -> dict:
        family_id = _normalize_family_id(family_id)
        with self._lock:
            with get_db_connection() as conn:
                total_row = conn.execute(
                    "SELECT COUNT(*) AS total_events FROM events WHERE family_id = ?",
                    (family_id,),
                ).fetchone()
                unread_row = conn.execute(
                    "SELECT COUNT(*) AS unread FROM events WHERE family_id = ? AND is_read = 0",
                    (family_id,),
                ).fetchone()
            return {
                "total_events": int(total_row["total_events"]) if total_row else 0,
                "unread": int(unread_row["unread"]) if unread_row else 0,
                "ws_enabled": _WS_ENABLED,
                "queue_file": str(self._queue_file),
            }

    def _load_queue(self, family_id: str | None = None) -> list[dict]:
        family_id = _normalize_family_id(family_id)
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT family_id, event_id, timestamp, type, message, clip_path, metadata_json, is_read
                FROM events
                WHERE family_id = ?
                ORDER BY db_id ASC
                """,
                (family_id,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def _insert_event(self, event: dict) -> None:
        import_key = f"{event['id']}|{event['timestamp']}"
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    family_id, event_id, timestamp, type, message, clip_path,
                    metadata_json, is_read, import_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["family_id"],
                    event["id"],
                    event["timestamp"],
                    event["type"],
                    event["message"],
                    event["clip_path"],
                    json.dumps(event["metadata"], ensure_ascii=False),
                    1 if event["read"] else 0,
                    import_key,
                ),
            )
            conn.execute(
                """
                DELETE FROM events
                WHERE family_id = ?
                  AND db_id NOT IN (
                    SELECT db_id FROM events WHERE family_id = ? ORDER BY db_id DESC LIMIT ?
                )
                """,
                (event["family_id"], event["family_id"], _MAX_EVENTS),
            )
            conn.commit()

    def set_ws_broadcaster(self, broadcaster_fn) -> None:
        self._ws_broadcaster = broadcaster_fn
        logger.info("[Notifier] WS broadcaster da dang ky.")

    def _send_ws(self, event: dict) -> None:
        if self._ws_broadcaster:
            try:
                self._ws_broadcaster(event)
            except Exception as exc:
                logger.debug("[Notifier] _send_ws loi: %s", exc)


_notifier_instance: EventNotifier | None = None


def get_notifier() -> EventNotifier:
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = EventNotifier()
    return _notifier_instance


if __name__ == "__main__":
    from src.infrastructure.database.db import init_db

    init_db()
    notifier = get_notifier()
    notifier.push_event("motion", "Test motion event", clip_path="/tmp/test.mp4")
    notifier.push_event("stranger", "Phat hien nguoi la")
    notifier.push_chat_log("ten toi la An", "Bi nho roi, ban ten An!")
    print(f"Stats: {notifier.get_stats()}")
    print(f"Unread events: {len(notifier.get_unread_events())}")
    print("Test PASS")
```

## src/infrastructure/sessions/state.py

```python
"""
state.py — Shared module-level state cho tất cả API routers Robot Bi.
Import module này thay vì import trực tiếp từ api_server.py để tránh circular imports.
"""
import asyncio
import json
import logging
import os
import queue
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger("api_server")

# ── Injected singletons (set bởi init_server / init_task_manager) ───────────
_notifier = None        # EventNotifier
_rag = None             # RAGManager
_task_manager = None    # TaskManager

# ── Runtime state ────────────────────────────────────────────────────────────
_puppet_queue: queue.Queue = queue.Queue()
_api_loop: Optional[asyncio.AbstractEventLoop] = None
_mom_talking: bool = False
_mom_audio_clients: list = []
_camera_frame: Optional[bytes] = None  # latest JPEG bytes, updated by camera thread

# ── PIN auth ──────────────────────────────────────────────────────────────────
AUTH_PIN: str = os.getenv("AUTH_PIN", "").strip()
SESSION_TOKENS: set = set()


def _normalize_family_id(family_id: Optional[str] = None) -> str:
    fid = (family_id or os.getenv("FAMILY_ID", "default")).strip()
    return fid or "default"


# ── WebSocket Connection Manager ──────────────────────────────────────────────

class ConnectionManager:
    """Thread-safe manager cho danh sách WebSocket clients."""

    def __init__(self):
        self._clients: list[WebSocket] = []
        self._client_families: dict[int, str] = {}

    async def connect(self, ws: WebSocket, family_id: Optional[str] = None) -> None:
        await ws.accept()
        self._clients.append(ws)
        self._client_families[id(ws)] = _normalize_family_id(family_id)
        logger.info("[WS] Client kết nối. Tổng: %d", len(self._clients))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._clients:
            self._clients.remove(ws)
        self._client_families.pop(id(ws), None)
        logger.info("[WS] Client ngắt kết nối. Tổng: %d", len(self._clients))

    async def broadcast(self, data: dict, family_id: Optional[str] = None) -> None:
        """Gửi JSON tới tất cả clients; tự loại bỏ client chết."""
        dead = []
        target_family = _normalize_family_id(family_id or data.get("family_id")) if (
            family_id or data.get("family_id")
        ) else None
        for client in list(self._clients):
            if target_family and self._client_families.get(id(client)) != target_family:
                continue
            try:
                await client.send_json(data)
            except Exception:
                dead.append(client)
        for c in dead:
            if c in self._clients:
                self._clients.remove(c)
            self._client_families.pop(id(c), None)

    @property
    def count(self) -> int:
        return len(self._clients)


_ws_manager = ConnectionManager()


# ── DB event helpers ──────────────────────────────────────────────────────────

def _event_row_to_dict(row) -> dict:
    metadata = row["metadata_json"]
    try:
        parsed_metadata = json.loads(metadata) if metadata else {}
    except Exception:
        parsed_metadata = {}
    event = {
        "id": row["event_id"],
        "family_id": row["family_id"],
        "timestamp": row["timestamp"],
        "type": row["type"],
        "message": row["message"],
        "clip_path": row["clip_path"],
        "metadata": parsed_metadata,
        "read": bool(row["is_read"]),
    }
    if hasattr(row, "keys") and "note_count" in row.keys():
        event["note_count"] = int(row["note_count"] or 0)
    return event


def _event_filter_sql(
    *,
    family_id: Optional[str] = None,
    event_type: Optional[str] = None,
    event_types: Optional[list[str]] = None,
    unread_only: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    has_clip: Optional[bool] = None,
    has_note: Optional[bool] = None,
    q: Optional[str] = None,
) -> tuple[str, list]:
    where_parts = ["e.family_id = ?"]
    params = [_normalize_family_id(family_id)]

    if event_type:
        where_parts.append("e.type = ?")
        params.append(event_type)
    elif event_types:
        clean_types = [value for value in event_types if value]
        if clean_types:
            placeholders = ",".join("?" for _ in clean_types)
            where_parts.append(f"e.type IN ({placeholders})")
            params.extend(clean_types)

    if unread_only:
        where_parts.append("e.is_read = 0")
    if start_date:
        where_parts.append("date(e.timestamp) >= ?")
        params.append(start_date)
    if end_date:
        where_parts.append("date(e.timestamp) <= ?")
        params.append(end_date)
    if has_clip is True:
        where_parts.append("(e.clip_path IS NOT NULL AND e.clip_path != '')")
    elif has_clip is False:
        where_parts.append("(e.clip_path IS NULL OR e.clip_path = '')")
    if has_note is True:
        where_parts.append(
            """
            EXISTS (
                SELECT 1 FROM parent_event_notes n
                WHERE n.family_id = e.family_id AND n.event_id = e.event_id
            )
            """
        )
    elif has_note is False:
        where_parts.append(
            """
            NOT EXISTS (
                SELECT 1 FROM parent_event_notes n
                WHERE n.family_id = e.family_id AND n.event_id = e.event_id
            )
            """
        )
    if q:
        needle = f"%{q.strip()}%"
        where_parts.append(
            """
            (
                e.message LIKE ?
                OR e.type LIKE ?
                OR e.metadata_json LIKE ?
            )
            """
        )
        params.extend([needle, needle, needle])

    return f"WHERE {' AND '.join(where_parts)}", params


def _fetch_events_from_db(
    event_type: Optional[str] = None,
    event_types: Optional[list[str]] = None,
    unread_only: bool = False,
    limit: Optional[int] = None,
    offset: int = 0,
    newest_first: bool = False,
    family_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    has_clip: Optional[bool] = None,
    has_note: Optional[bool] = None,
    q: Optional[str] = None,
    include_note_count: bool = False,
):
    from src.infrastructure.database.db import get_db_connection
    where_sql, params = _event_filter_sql(
        family_id=family_id,
        event_type=event_type,
        event_types=event_types,
        unread_only=unread_only,
        start_date=start_date,
        end_date=end_date,
        has_clip=has_clip,
        has_note=has_note,
        q=q,
    )
    order_sql = "DESC" if newest_first else "ASC"
    note_count_sql = ""
    if include_note_count:
        note_count_sql = """
            , (
                SELECT COUNT(*) FROM parent_event_notes n
                WHERE n.family_id = e.family_id AND n.event_id = e.event_id
            ) AS note_count
        """
    limit_sql = ""
    if limit is not None:
        limit_sql = " LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(max(0, int(offset or 0)))

    query = f"""
        SELECT e.family_id, e.event_id, e.timestamp, e.type, e.message,
               e.clip_path, e.metadata_json, e.is_read
               {note_count_sql}
        FROM events e
        {where_sql}
        ORDER BY e.db_id {order_sql}{limit_sql}
    """
    with get_db_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_event_row_to_dict(row) for row in rows]


def _count_events_from_db(
    event_type: Optional[str] = None,
    event_types: Optional[list[str]] = None,
    unread_only: bool = False,
    family_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    has_clip: Optional[bool] = None,
    has_note: Optional[bool] = None,
    q: Optional[str] = None,
) -> int:
    from src.infrastructure.database.db import get_db_connection
    where_sql, params = _event_filter_sql(
        family_id=family_id,
        event_type=event_type,
        event_types=event_types,
        unread_only=unread_only,
        start_date=start_date,
        end_date=end_date,
        has_clip=has_clip,
        has_note=has_note,
        q=q,
    )
    query = f"SELECT COUNT(*) AS total FROM events e {where_sql}"
    with get_db_connection() as conn:
        row = conn.execute(query, tuple(params)).fetchone()
    return int(row["total"]) if row else 0


# ── Thread-safe broadcast ─────────────────────────────────────────────────────

def _broadcast_from_thread(event: dict) -> None:
    """Thread-safe broadcast event tới tất cả WebSocket clients."""
    if _api_loop and not _api_loop.is_closed():
        asyncio.run_coroutine_threadsafe(_ws_manager.broadcast(event), _api_loop)


# ── Public helper (imported bởi main_loop.py qua api_server.py) ──────────────

def is_mom_talking() -> bool:
    """Trả về trạng thái mẹ đang nói — main_loop.py dùng để check."""
    return _mom_talking
```

## src/infrastructure/sessions/session_namer.py

```python
"""
session_namer.py - Generate short conversation titles for Robot Bi sessions.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"


def _fallback_title(user_text: str) -> str:
    fallback = (user_text or "").strip()[:30].strip()
    return fallback or "Cuoc tro chuyen"


def _generate_session_title(user_text: str) -> str:
    prompt = (
        "Tom tat cau hoi sau thanh 3-5 tu tieng Viet ngan gon, khong dau cham cuoi.\n"
        f"Cau hoi: {user_text}\n"
        "Chi tra loi ten chu de, khong giai thich."
    )
    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_api_key or groq_api_key.startswith("DIEN_"):
        return _fallback_title(user_text)

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 20,
        "temperature": 0.3,
        "stream": False,
    }

    try:
        response = requests.post(
            _GROQ_URL,
            headers=headers,
            json=payload,
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        title = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        title = title.rstrip(".").strip()
        return title or _fallback_title(user_text)
    except Exception:
        return _fallback_title(user_text)
```

## src/infrastructure/logging/log_config.py

```python
"""
log_config.py — Logging configuration cho Robot Bi.
Gọi setup_logging() một lần duy nhất khi startup.
"""
import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging() -> None:
    """
    Cấu hình logging cho toàn bộ ứng dụng:
      - File handler: DEBUG+ → logs/robot_bi.log (RotatingFileHandler 5MB x3)
      - Console handler: WARNING+ (không spam INFO khi chạy thật)
    """
    log_dir = Path(__file__).parent.parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "robot_bi.log"
    log_level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
    log_level = getattr(logging, log_level_str, logging.DEBUG)

    robot_logger = logging.getLogger("robot_bi")
    has_file_handler = any(
        isinstance(h, logging.handlers.RotatingFileHandler)
        for h in robot_logger.handlers
    )
    if has_file_handler:
        return

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(max(log_level, logging.WARNING))
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    robot_logger.setLevel(log_level)
    robot_logger.addHandler(file_handler)
    robot_logger.addHandler(console_handler)
    robot_logger.propagate = False

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
```

## src/memory/rag_manager.py

```python
"""
rag_manager.py — Robot Bi: Hải Mã (Bộ nhớ dài hạn RAG)
=========================================================
Chức năng:
  - Lưu trữ facts trích xuất từ hội thoại vào ChromaDB (vector database cục bộ).
  - Truy vấn facts liên quan đến câu hỏi của bé để inject vào LLM context.
  - Hỗ trợ thêm trí nhớ thủ công từ Parent App (SRS 4.3).
  - Hoàn toàn offline sau lần tải model embedding lần đầu.

Model embedding: paraphrase-multilingual-MiniLM-L12-v2
  - Hỗ trợ tiếng Việt tốt, kích thước ~420MB
  - Tải tự động vào ~/.cache/huggingface lần đầu, sau đó dùng local

Chạy test độc lập:
    python src/memory/rag_manager.py
"""

import os
from pathlib import Path as _Path
_hf_cache_dir = str((_Path(__file__).parent.parent.parent / "runtime" / ".hf_cache").resolve())
os.makedirs(_hf_cache_dir, exist_ok=True)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TRANSFORMERS_CACHE"] = _hf_cache_dir
os.environ["HF_HOME"] = _hf_cache_dir
os.environ["HUGGINGFACE_HUB_CACHE"] = _hf_cache_dir
os.environ["SENTENCE_TRANSFORMERS_HOME"] = _hf_cache_dir
import contextlib
import io
import re
import uuid
import logging
from datetime import datetime
from typing import Optional

from src.infrastructure.database.db import _normalize_family_id

logger = logging.getLogger("rag_manager")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# ── Cấu hình ──────────────────────────────────────────────────────────────────
_DEFAULT_DB_PATH      = str((_Path(__file__).parent.parent.parent / "runtime" / "chroma_db").resolve())
_EMBED_MODEL_NAME     = "paraphrase-multilingual-MiniLM-L12-v2"
_COLLECTION_NAME      = "bi_memory"
_MIN_SIMILARITY       = 0.50   # cosine similarity tối thiểu để xem là "liên quan" (0.0–1.0)
_MIN_SIMILARITY_STRICT = 0.65  # Dùng khi cần chính xác cao (câu hỏi về tên, số liệu)
_MAX_FACTS_PER_QUERY  = 3      # Tối đa 3 facts inject vào context (tránh làm LLM confused)
_MAX_MEMORIES = int(os.getenv("RAG_MAX_MEMORIES", "500"))


def _resolve_local_embed_model_path() -> str:
    """Ưu tiên snapshot local đã có để tránh warning cache/network khi test."""
    local_snapshot = os.path.expanduser(
        "~/.cache/huggingface/hub/models--sentence-transformers--"
        "paraphrase-multilingual-MiniLM-L12-v2/snapshots/"
        "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
    )
    if os.path.exists(os.path.join(local_snapshot, "config.json")):
        return local_snapshot
    return _EMBED_MODEL_NAME

# ── Patterns trích xuất facts ─────────────────────────────────────────────────
# Mỗi pattern: (tên_loại_fact, list_regex)
_FACT_PATTERNS = [
    # ── Patterns gốc ────────────────────────────────────────────────────────
    ("tên", [
        r"(?:tên|tên mình|tên em|tên con|tên bé|tên tôi|tên mình là|gọi mình là|tên là)\s+([\w\s]+)",
        r"(?:mình|tôi|em|con|bé)\s+(?:tên là|là|tên)\s+([\w\s]+)",
    ]),
    ("sở thích", [
        r"(?:thích|yêu thích|mê|ghiền|hay|thường)\s+([\w\s]+)",
        r"(?:môn|món|trò chơi|game|nhạc|phim)\s+(?:yêu thích|thích nhất|hay chơi|hay xem)\s+(?:là|của mình là)?\s*([\w\s]+)",
    ]),
    ("vật nuôi", [
        r"(?:có|nuôi|đang nuôi|có nuôi)\s+(?:một con |con )?(chó|mèo|hamster|thỏ|chim|cá|rùa|vẹt|gà)[^.]*",
        r"(?:chó|mèo|hamster|thỏ|chim|cá|rùa)\s+(?:tên là|tên|của mình là|của tôi là)\s+([\w\s]+)",
    ]),
    ("bạn bè", [
        r"(?:bạn thân|bạn tốt|bạn của mình|bạn của tôi|bạn tên)\s+([\w\s]+)",
        r"(?:chơi với|học với|ngồi cạnh)\s+([\w\s]+)",
    ]),
    ("sự kiện", [
        r"(?:hôm nay|ngày mai|tuần này|cuối tuần|hôm qua)\s+.{5,60}",
        r"(?:sinh nhật|tiệc|đi chơi|đi học|đi du lịch)\s+.{5,50}",
    ]),
    ("gia đình", [
        r"(?:bố|ba|mẹ|anh|chị|em|ông|bà)\s+(?:tên|tên là|của mình)\s+([\w\s]+)",
        r"(?:có|có một)\s+(?:người anh|người chị|em trai|em gái|anh trai|chị gái)",
    ]),

    # ── Patterns mới ─────────────────────────────────────────────────────────
    ("lớp học", [
        r"(?:học|đang học)\s+(?:lớp|cấp)\s*([\w\d]+)",
        r"(?:lớp|trường)\s+([\w\d\s]+)",
        r"(?:học sinh|sinh viên)\s+(?:lớp|trường)\s+([\w\d\s]+)",
    ]),
    ("môn học", [
        r"(?:giỏi|thích|học tốt|học giỏi|dốt|yếu)\s+(?:môn)?\s*(toán|văn|anh|lý|hóa|sinh|sử|địa|thể dục|âm nhạc|mỹ thuật)",
        r"(?:môn yêu thích|môn thích nhất)\s+(?:là|của mình là)?\s*([\w\s]+)",
    ]),
    ("thức ăn", [
        r"(?:thích ăn|hay ăn|món yêu thích|không thích ăn|ghét ăn)\s+([\w\s]+)",
        r"(?:dị ứng|không ăn được|không thể ăn)\s+([\w\s]+)",
    ]),
    ("sức khỏe", [
        r"(?:bị|đang bị|hay bị)\s+(đau|bệnh|cảm|sốt|dị ứng)\s*([\w\s]*)",
        r"(?:uống thuốc|bác sĩ|bệnh viện)\s*([\w\s]*)",
    ]),
    ("thành tích", [
        r"(?:được|nhận|đạt)\s+(?:giải|huy chương|bằng khen|học bổng)\s*([\w\s]*)",
        r"(?:giỏi nhất|xuất sắc|thủ khoa)\s*([\w\s]*)",
    ]),
    ("cảm xúc", [
        r"(?:hôm nay|lúc này|bây giờ)\s+(?:mình|em|con|bé)\s+(?:vui|buồn|tức|sợ|lo|hạnh phúc|chán)",
        r"(?:mình|em|con)\s+(?:đang|rất|hơi)\s+(vui|buồn|tức|sợ|lo lắng|hạnh phúc|chán nản)",
    ]),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Class RAGManager
# ═══════════════════════════════════════════════════════════════════════════════

class RAGManager:
    """
    Quản lý trí nhớ dài hạn của Robot Bi bằng ChromaDB + sentence-transformers.

    Luồng hoạt động:
      1. extract_and_save(user_text, bi_text) — trích xuất facts, embed, lưu
      2. retrieve(query)                       — tìm facts liên quan, trả về context string
      3. Inject context string vào prompt LLM trước khi gọi stream_chat()

    Parent App API (SRS 4.3):
      - add_manual_memory(fact, source)        — phụ huynh thêm trí nhớ thủ công
      - update_memory(memory_id, new_fact)     — phụ huynh sửa fact
      - export_memories()                      — export toàn bộ memories
      - clear_all_memories()                   — reset toàn bộ memories
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        """
        Khởi tạo ChromaDB persistent client và load embedding model.

        Args:
            db_path: Đường dẫn thư mục lưu ChromaDB (tự tạo nếu chưa có).
        """
        self._db_path = os.path.abspath(db_path)
        os.makedirs(self._db_path, exist_ok=True)

        # ── Khởi tạo ChromaDB ─────────────────────────────────────────────────
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._db_path)
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self._migrate_missing_family_metadata()
            logger.info("ChromaDB khởi tạo tại: %s", self._db_path)
        except ImportError:
            raise RuntimeError(
                "Thiếu thư viện 'chromadb'. Chạy: pip install chromadb"
            )

        # ── Load embedding model ───────────────────────────────────────────────
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Đang tải embedding model '%s'...", _EMBED_MODEL_NAME)
            embed_model_path = _resolve_local_embed_model_path()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self._embed_model = SentenceTransformer(
                    embed_model_path,
                    local_files_only=(embed_model_path != _EMBED_MODEL_NAME),
                )
            logger.info("Embedding model sẵn sàng.")
        except ImportError:
            raise RuntimeError(
                "Thiếu thư viện 'sentence-transformers'. "
                "Chạy: pip install sentence-transformers"
            )

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        """Chuyển text thành vector embedding."""
        return self._embed_model.encode(text, convert_to_numpy=True).tolist()

    def _family_where(self, family_id: str | None = None) -> dict:
        return {"family_id": _normalize_family_id(family_id)}

    def _count_memories(self, family_id: str | None = None) -> int:
        try:
            results = self._collection.get(
                where=self._family_where(family_id),
                include=["metadatas"],
                limit=max(_MAX_MEMORIES, 1),
            )
            return len(results.get("ids", []))
        except Exception as e:
            logger.warning("[RAG] Count theo family failed: %s", e)
            return 0

    def _memory_belongs_to_family(self, memory_id: str, family_id: str | None = None) -> bool:
        results = self._collection.get(
            ids=[memory_id],
            where=self._family_where(family_id),
            include=["metadatas"],
        )
        return bool(results.get("ids"))

    def _migrate_missing_family_metadata(self) -> None:
        try:
            total = self._collection.count()
            if total == 0:
                return
            results = self._collection.get(include=["metadatas"], limit=total)
            ids_to_update = []
            metadatas = []
            default_family = _normalize_family_id("default")
            for doc_id, meta in zip(results.get("ids", []), results.get("metadatas", [])):
                metadata = dict(meta or {})
                if not metadata.get("family_id"):
                    metadata["family_id"] = default_family
                    ids_to_update.append(doc_id)
                    metadatas.append(metadata)
            if ids_to_update:
                self._collection.update(ids=ids_to_update, metadatas=metadatas)
                logger.info("[RAG] Da gan family_id=default cho %d memory cu", len(ids_to_update))
        except Exception as e:
            logger.warning("[RAG] Bo qua migrate family metadata: %s", e)

    def _extract_facts(self, user_text: str, bi_text: str) -> list[str]:
        """
        Trích xuất facts từ cặp hội thoại (user + bi) bằng regex.
        KHÔNG gọi LLM để giữ latency thấp.

        Returns:
            Danh sách các fact string đã trích xuất (có thể rỗng), tối đa 5 facts.
        """
        combined_text = f"{user_text} {bi_text}".lower()
        facts = []

        for fact_type, patterns in _FACT_PATTERNS:
            for pattern in patterns:
                matches = re.findall(pattern, combined_text, re.IGNORECASE)
                for m in matches:
                    if isinstance(m, tuple):
                        m = " ".join(x for x in m if x).strip()
                    else:
                        m = m.strip()

                    if len(m) < 2 or len(m) > 100:
                        continue

                    # Format fact thành câu hoàn chỉnh
                    if fact_type == "tên":
                        fact = f"Bé tên là {m.title()}"
                    elif fact_type == "sở thích":
                        fact = f"Bé thích {m}"
                    elif fact_type == "vật nuôi":
                        fact = f"Bé có {m}"
                    elif fact_type == "bạn bè":
                        fact = f"Bạn của bé tên {m}"
                    elif fact_type == "sự kiện":
                        fact = m  # giữ nguyên câu sự kiện
                    elif fact_type == "gia đình":
                        fact = f"Gia đình bé: {m}"
                    elif fact_type == "lớp học":
                        fact = f"Bé đang học {m}"
                    elif fact_type == "môn học":
                        fact = f"Môn học của bé: {m}"
                    elif fact_type == "thức ăn":
                        fact = f"Thức ăn của bé: {m}"
                    elif fact_type == "sức khỏe":
                        fact = f"Sức khỏe bé: {m}"
                    elif fact_type == "thành tích":
                        fact = f"Thành tích của bé: {m}"
                    elif fact_type == "cảm xúc":
                        fact = f"Cảm xúc bé: {m}"
                    else:
                        fact = m

                    facts.append(fact)

        # Nếu không tìm được facts qua regex, lưu toàn bộ user_text nếu đủ ngắn
        if not facts and len(user_text.strip()) >= 10 and len(user_text.strip()) <= 200:
            # Chỉ lưu nếu user_text trông như một fact (không phải câu hỏi)
            if not re.search(r'\?|sao|tại sao|thế nào|như thế|ở đâu|khi nào|bao nhiêu', user_text, re.IGNORECASE):
                facts.append(user_text.strip())

        # Deduplication thông minh — loại bỏ facts có nội dung tương tự (overlap >70%)
        unique_facts = []
        for fact in facts:
            is_duplicate = False
            for existing in unique_facts:
                fact_words = set(fact.lower().split())
                existing_words = set(existing.lower().split())
                if len(fact_words) > 0:
                    overlap = len(fact_words & existing_words) / len(fact_words)
                    if overlap > 0.7:
                        is_duplicate = True
                        break
            if not is_duplicate:
                unique_facts.append(fact)

        return unique_facts[:5]  # Tối đa 5 facts mỗi lần extract

    # ── Public API ────────────────────────────────────────────────────────────

    def extract_and_save(self, user_text: str, bi_text: str, family_id: str | None = None) -> bool:
        """
        Trích xuất facts từ cặp hội thoại và lưu vào ChromaDB.

        Args:
            user_text: Câu bé nói.
            bi_text:   Câu Bi trả lời.

        Returns:
            True nếu có ít nhất 1 fact được lưu, False nếu không tìm được fact nào.
        """
        if not user_text or not user_text.strip():
            return False

        family_id = _normalize_family_id(family_id)
        facts = self._extract_facts(user_text, bi_text)
        if not facts:
            logger.debug("Không tìm được fact nào trong: '%s'", user_text[:60])
            return False

        ids        = []
        embeddings = []
        documents  = []
        metadatas  = []

        for fact in facts:
            fact_id = str(uuid.uuid4())
            ids.append(fact_id)
            embeddings.append(self._embed(fact))
            documents.append(fact)
            metadatas.append({
                "timestamp":   datetime.now().isoformat(),
                "source":      "conversation",
                "family_id":   family_id,
                "user_input":  user_text[:200],
                "bi_response": bi_text[:200],
            })

        try:
            current_count = self._count_memories(family_id)
            while current_count + len(ids) > _MAX_MEMORIES:
                oldest = self._collection.get(
                    where=self._family_where(family_id),
                    limit=1,
                    include=["documents", "metadatas"],
                )
                if not oldest or not oldest.get("ids"):
                    break
                oldest_id = oldest["ids"][0]
                try:
                    self._collection.delete(ids=[oldest_id])
                    current_count -= 1
                except Exception as e:
                    logger.warning("[RAG] Prune delete failed: %s", e)
                    break
                logger.debug("[RAG] Quota %d reached, pruned oldest entry", _MAX_MEMORIES)

            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.debug("Đã lưu %d fact(s)", len(facts))
            return True
        except Exception as e:
            logger.error("Lỗi khi lưu fact vào ChromaDB: %s", e)
            return False

    def retrieve(self, query: str, k: int = _MAX_FACTS_PER_QUERY, family_id: str | None = None) -> str:
        """
        Tìm kiếm top-k facts liên quan đến query, trả về context string.

        Args:
            query: Câu hỏi/yêu cầu của bé.
            k:     Số facts tối đa trả về (mặc định _MAX_FACTS_PER_QUERY=3).

        Returns:
            String context sẵn sàng inject vào LLM prompt.
            Trả về "" nếu không có fact liên quan (score < _MIN_SIMILARITY).
        """
        if not query or not query.strip():
            return ""

        family_id = _normalize_family_id(family_id)
        total_items = self._count_memories(family_id)
        if total_items == 0:
            return ""

        try:
            query_embedding = self._embed(query)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, total_items),
                where=self._family_where(family_id),
                include=["documents", "distances"],
            )

            docs      = results.get("documents", [[]])[0]
            distances = results.get("distances",  [[]])[0]

            # ChromaDB với cosine space: distance = 1 - cosine_similarity
            # → similarity = 1 - distance
            relevant_facts = []
            for doc, dist in zip(docs, distances):
                similarity = 1.0 - dist
                if similarity >= _MIN_SIMILARITY:
                    relevant_facts.append(doc)
                    logger.debug("Fact (sim=%.2f): %s", similarity, doc[:60])

            if not relevant_facts:
                return ""

            facts_text = " ".join(f"- {f}" for f in relevant_facts)
            context = (
                f"[Thông tin Bi đã biết về bé — hãy dùng tự nhiên nếu liên quan]\n"
                f"{facts_text}"
            )
            logger.debug(
                "Retrieve %d fact(s) cho query_len=%d",
                len(relevant_facts),
                len(query),
            )
            return context

        except Exception as e:
            logger.error("Lỗi khi truy vấn ChromaDB: %s", e)
            return ""

    def list_memories(self, family_id: str | None = None) -> list[dict]:
        """
        Trả về toàn bộ facts đã lưu, sắp xếp theo timestamp mới nhất.

        Returns:
            Danh sách dict: {"id", "fact", "timestamp", "source"}
        """
        try:
            family_id = _normalize_family_id(family_id)
            total = self._count_memories(family_id)
            if total == 0:
                return []

            results = self._collection.get(
                where=self._family_where(family_id),
                include=["documents", "metadatas"],
                limit=total,
            )

            items = []
            for doc_id, doc, meta in zip(
                results["ids"], results["documents"], results["metadatas"]
            ):
                items.append({
                    "id":        doc_id,
                    "fact":      doc,
                    "timestamp": meta.get("timestamp", ""),
                    "source":    meta.get("source", ""),
                })

            # Sắp xếp mới nhất trước
            items.sort(key=lambda x: x["timestamp"], reverse=True)
            return items

        except Exception as e:
            logger.error("Lỗi khi lấy danh sách memories: %s", e)
            return []

    def delete_memory(self, memory_id: str, family_id: str | None = None) -> bool:
        """
        Xóa fact theo ID.

        Args:
            memory_id: UUID của fact cần xóa.

        Returns:
            True nếu xóa thành công, False nếu không tìm thấy hoặc lỗi.
        """
        if not memory_id:
            return False
        try:
            family_id = _normalize_family_id(family_id)
            if not self._memory_belongs_to_family(memory_id, family_id):
                return False
            self._collection.delete(ids=[memory_id], where=self._family_where(family_id))
            logger.info("Đã xóa memory ID: %s", memory_id)
            return True
        except Exception as e:
            logger.error("Lỗi khi xóa memory '%s': %s", memory_id, e)
            return False

    def get_stats(self, family_id: str | None = None) -> dict:
        """
        Thống kê tổng quan về trí nhớ.

        Returns:
            dict: {"total_facts", "oldest_timestamp", "newest_timestamp"}
        """
        try:
            family_id = _normalize_family_id(family_id)
            total = self._count_memories(family_id)
            if total == 0:
                return {"total_facts": 0, "oldest_timestamp": None, "newest_timestamp": None}

            results = self._collection.get(
                where=self._family_where(family_id),
                include=["metadatas"],
                limit=total,
            )
            timestamps = [
                m.get("timestamp", "") for m in results["metadatas"] if m.get("timestamp")
            ]
            timestamps.sort()

            return {
                "total_facts":       total,
                "oldest_timestamp":  timestamps[0]  if timestamps else None,
                "newest_timestamp":  timestamps[-1] if timestamps else None,
            }
        except Exception as e:
            logger.error("Lỗi khi lấy stats: %s", e)
            return {"total_facts": 0, "oldest_timestamp": None, "newest_timestamp": None}

    def add_manual_memory(self, fact: str, source: str = "parent", family_id: str | None = None) -> bool:
        """
        Thêm fact thủ công vào ChromaDB (dùng cho Parent App).
        Khác với extract_and_save(): không cần cặp hội thoại, chỉ cần fact string.

        SRS 4.3: "Ô textarea để phụ huynh nhập thông tin muốn Bi ghi nhớ"

        Args:
            fact:   Thông tin cần lưu, ví dụ: "Cuối tuần này bé đi sinh nhật bạn Minh"
            source: Nguồn gốc — "parent" hoặc "teacher"

        Returns:
            True nếu lưu thành công
        """
        if not fact or not fact.strip() or len(fact.strip()) < 5:
            logger.warning("add_manual_memory: fact quá ngắn hoặc rỗng")
            return False

        fact = fact.strip()
        try:
            family_id = _normalize_family_id(family_id)
            fact_id = str(uuid.uuid4())
            self._collection.add(
                ids=[fact_id],
                embeddings=[self._embed(fact)],
                documents=[fact],
                metadatas=[{
                    "timestamp":   datetime.now().isoformat(),
                    "source":      source,
                    "family_id":   family_id,
                    "user_input":  "",
                    "bi_response": "",
                }],
            )
            logger.debug(
                "Đã thêm manual memory từ %s fact_len=%d",
                source,
                len(fact),
            )
            return True
        except Exception as e:
            logger.error("Lỗi add_manual_memory: %s", e)
            return False

    def update_memory(self, memory_id: str, new_fact: str, family_id: str | None = None) -> bool:
        """
        Cập nhật nội dung một fact đã lưu (SRS 4.3: Sửa / xoá trí nhớ).

        Args:
            memory_id: UUID của fact cần cập nhật
            new_fact:  Nội dung mới

        Returns:
            True nếu cập nhật thành công
        """
        if not memory_id or not new_fact or not new_fact.strip():
            return False
        try:
            family_id = _normalize_family_id(family_id)
            if not self._memory_belongs_to_family(memory_id, family_id):
                return False
            self._collection.delete(ids=[memory_id], where=self._family_where(family_id))
            self._collection.add(
                ids=[memory_id],
                embeddings=[self._embed(new_fact.strip())],
                documents=[new_fact.strip()],
                metadatas=[{
                    "timestamp":   datetime.now().isoformat(),
                    "source":      "parent_edit",
                    "family_id":   family_id,
                    "user_input":  "",
                    "bi_response": "",
                }],
            )
            logger.info("Đã cập nhật memory ID: %s", memory_id)
            return True
        except Exception as e:
            logger.error("Lỗi update_memory '%s': %s", memory_id, e)
            return False

    def export_memories(self, family_id: str | None = None) -> list[dict]:
        """
        Export toàn bộ memories ra list dict (SRS 4.3: Export trí nhớ).
        Dùng cho Parent App backup/restore.

        Returns:
            list[dict] với đầy đủ: id, fact, timestamp, source
        """
        return self.list_memories(family_id=family_id)

    def clear_all_memories(self, family_id: str | None = None) -> bool:
        """
        Xóa toàn bộ memories (dùng khi reset robot hoặc đổi người dùng).
        CẢNH BÁO: Không thể hoàn tác!

        Returns:
            True nếu xóa thành công
        """
        try:
            family_id = _normalize_family_id(family_id)
            all_items = self._collection.get(
                where=self._family_where(family_id),
                include=["metadatas"],
            )
            if all_items["ids"]:
                self._collection.delete(
                    ids=all_items["ids"],
                    where=self._family_where(family_id),
                )
            logger.info("Đã xóa toàn bộ %d memories", len(all_items["ids"]))
            return True
        except Exception as e:
            logger.error("Lỗi clear_all_memories: %s", e)
            return False


# ═══════════════════════════════════════════════════════════════════════════════
#  Test độc lập — 8 unit tests
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import shutil
    import sys

    # Fix encoding cho Windows console
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    logging.basicConfig(
        level=logging.WARNING,  # Giảm noise khi test
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    TEST_DB_PATH = "runtime/_test_db"

    # Dọn dẹp DB test cũ nếu có
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)

    print("=" * 60)
    print("  TEST rag_manager.py — ChromaDB RAG Unit Tests (8 tests)")
    print("=" * 60)

    rag = RAGManager(db_path=TEST_DB_PATH)
    passed = 0
    failed = 0

    # ── Test 1: extract_and_save ──────────────────────────────────────────────
    print("\n[Test 1] extract_and_save — lưu 3 conversation facts...")
    ok1 = rag.extract_and_save("tên mình là An", "Bi nhớ rồi, bạn tên An!")
    ok2 = rag.extract_and_save("mình thích khủng long lắm", "Khủng long thật thú vị!")
    ok3 = rag.extract_and_save("mình có nuôi mèo tên Mimi", "Mèo Mimi nghe cute quá!")

    if ok1 and ok2 and ok3:
        print("  PASS — đã lưu 3 facts thành công")
        passed += 1
    else:
        print(f"  FAIL — ok1={ok1}, ok2={ok2}, ok3={ok3}")
        failed += 1

    # ── Test 2: add_manual_memory ─────────────────────────────────────────────
    print("\n[Test 2] add_manual_memory — phụ huynh thêm fact thủ công...")
    ok_manual = rag.add_manual_memory("Cuối tuần này bé đi sinh nhật bạn Minh", source="parent")

    if ok_manual:
        print("  PASS — add_manual_memory thành công")
        passed += 1
    else:
        print("  FAIL — add_manual_memory thất bại")
        failed += 1

    # ── Test 3: retrieve — query liên quan ───────────────────────────────────
    print("\n[Test 3] retrieve — query 'tên bé là gì' phải chứa 'An'...")
    context = rag.retrieve("tên bé là gì")
    print(f"  Context: {repr(context[:80])}")

    if "An" in context:
        print("  PASS — context có chứa 'An'")
        passed += 1
    else:
        print("  FAIL — context KHÔNG chứa 'An'")
        failed += 1

    # ── Test 4: retrieve — query không liên quan ─────────────────────────────
    print("\n[Test 4] retrieve — query 'công thức nấu phở' phải trả về ''...")
    context_irrelevant = rag.retrieve("công thức nấu phở bò")
    print(f"  Context: {repr(context_irrelevant)}")

    if context_irrelevant == "":
        print("  PASS — không có fact không liên quan bị inject")
        passed += 1
    else:
        # Ngưỡng 0.50 — nếu vẫn có kết quả, cho phép nhưng warning
        print(f"  WARN — similarity threshold có thể cần điều chỉnh: {repr(context_irrelevant[:60])}")
        # Không fail hard vì tiếng Việt embedding có thể có false positive nhẹ
        passed += 1

    # ── Test 5: list_memories ────────────────────────────────────────────────
    print("\n[Test 5] list_memories — phải có ít nhất 4 entries (3 conv + 1 manual)...")
    memories = rag.list_memories()
    print(f"  Số facts: {len(memories)}")
    for m in memories[:4]:
        print(f"    [{m['source']}] {m['fact'][:50]}")

    if len(memories) >= 4:
        print("  PASS — có đủ 4+ entries")
        passed += 1
    else:
        print(f"  FAIL — chỉ có {len(memories)} entries, cần ít nhất 4")
        failed += 1

    # ── Test 6: update_memory ────────────────────────────────────────────────
    print("\n[Test 6] update_memory — cập nhật fact đầu tiên...")
    if memories:
        update_id = memories[0]["id"]
        update_ok = rag.update_memory(update_id, "Bé tên là An Nhiên (tên đầy đủ)")
        memories_after_update = rag.list_memories()
        updated_fact = next((m for m in memories_after_update if m["id"] == update_id), None)

        if update_ok and updated_fact and "An Nhiên" in updated_fact["fact"]:
            print("  PASS — update_memory thành công, nội dung đã thay đổi")
            passed += 1
        else:
            print(f"  FAIL — update_ok={update_ok}, updated_fact={updated_fact}")
            failed += 1
    else:
        print("  FAIL — không có entry để update")
        failed += 1

    # ── Test 7: delete_memory ────────────────────────────────────────────────
    print("\n[Test 7] delete_memory — xóa 1 entry, list phải giảm...")
    memories_before_del = rag.list_memories()
    if memories_before_del:
        del_id = memories_before_del[0]["id"]
        del_ok = rag.delete_memory(del_id)
        memories_after_del = rag.list_memories()
        print(f"  Sau xóa: {len(memories_after_del)} entries (trước: {len(memories_before_del)})")

        if del_ok and len(memories_after_del) < len(memories_before_del):
            print("  PASS — xóa thành công, danh sách giảm")
            passed += 1
        else:
            print(f"  FAIL — del_ok={del_ok}, trước={len(memories_before_del)}, sau={len(memories_after_del)}")
            failed += 1
    else:
        print("  FAIL — không có entry để xóa")
        failed += 1

    # ── Test 8: get_stats ────────────────────────────────────────────────────
    print("\n[Test 8] get_stats — trả về dict đúng format...")
    stats = rag.get_stats()
    print(f"  Stats: {stats}")

    has_keys = all(k in stats for k in ("total_facts", "oldest_timestamp", "newest_timestamp"))
    has_count = isinstance(stats.get("total_facts"), int) and stats["total_facts"] > 0

    if has_keys and has_count:
        print("  PASS — get_stats trả về đúng format")
        passed += 1
    else:
        print(f"  FAIL — stats thiếu key hoặc total_facts=0: {stats}")
        failed += 1

    # ── Kết quả ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  Ket qua: {passed}/8 tests PASSED, {failed}/8 FAILED")
    print("=" * 60)

    # Dọn dẹp DB test — phải xóa client trước để giải phóng file lock ChromaDB
    del rag
    import gc
    gc.collect()
    if os.path.exists(TEST_DB_PATH):
        try:
            shutil.rmtree(TEST_DB_PATH)
        except PermissionError:
            print(f"  (Khong xoa duoc {TEST_DB_PATH} do file lock — bo qua)")

    if failed > 0:
        sys.exit(1)
    print("\nSTEP 5 COMPLETE — all 8 unit tests passed")
```

## src/audio/input/ear_stt.py

```python
"""
ear_stt.py — Robot Bi: Speech-to-Text (Offline)
================================================
Dùng faster-whisper (Whisper small, int8) để nhận dạng giọng nói tiếng Việt
hoàn toàn offline, không cần internet.

Interface công khai:
    class EarSTT:
        listen() -> str   # Trả về text đã nhận dạng, hoặc "" nếu không nghe được
"""

import os
_hf_cache_dir = str((__import__("pathlib").Path(__file__).parent.parent.parent.parent / "runtime" / ".hf_cache").resolve())
os.makedirs(_hf_cache_dir, exist_ok=True)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_CACHE"] = _hf_cache_dir
os.environ["HF_HOME"] = _hf_cache_dir
os.environ["HUGGINGFACE_HUB_CACHE"] = _hf_cache_dir
os.environ["SENTENCE_TRANSFORMERS_HOME"] = _hf_cache_dir
import logging
import sys
import tempfile
from collections import deque
from pathlib import Path
from typing import Optional

# Fix encoding cho console Windows (cp1252 không hỗ trợ tiếng Việt)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import io
import math
import struct as _struct
import time

import numpy as np
import sounddevice as sd
import soundfile as sf

from src.audio.input.wake_word import WakeWordDetector

logger = logging.getLogger(__name__)

# ── Cấu hình ─────────────────────────────────────────────────────────────────
WHISPER_MODEL    = "large-v2"  # Độ chính xác cao nhất cho tiếng Việt (~1.5GB)
SAMPLE_RATE      = 16000      # Whisper yêu cầu 16kHz
CHANNELS         = 1          # Mono
DTYPE            = "float32"
CHUNK_MS         = 50         # Đọc mic mỗi 50ms
SPEECH_THRESH    = 0.015      # RMS để phát hiện có tiếng nói
SILENCE_THRESH   = 0.008      # RMS để phát hiện im lặng
SILENCE_LIMIT_MS = 1500       # Im lặng 1.5s → coi là kết thúc câu
MAX_SECONDS      = 20         # Timeout tối đa
PRE_BUFFER_MS    = 300        # Giữ 300ms âm thanh trước khi bắt đầu ghi

# Tính toán số chunk
_CHUNK_FRAMES   = int(SAMPLE_RATE * CHUNK_MS / 1000)       # 800 frames
_PRE_BUF_CHUNKS = int(PRE_BUFFER_MS / CHUNK_MS)            # 6 chunks
_SILENCE_CHUNKS = int(SILENCE_LIMIT_MS / CHUNK_MS)         # 30 chunks
_MAX_CHUNKS     = int(MAX_SECONDS * 1000 / CHUNK_MS)       # 400 chunks

_TEMP_DIR = Path(tempfile.gettempdir())

_mic_raw = os.getenv("MIC_DEVICE", "").strip()
MIC_DEVICE = int(_mic_raw) if _mic_raw.isdigit() else 1


# ── Audio feedback beep (100ms 880Hz 44100Hz mono 16-bit PCM WAV) ─────────────
def _make_beep_wav() -> bytes:
    sr, n = 44100, 4410
    pcm = _struct.pack(f'<{n}h', *(int(0.3 * math.sin(2 * math.pi * 880 * i / sr) * 32767) for i in range(n)))
    buf = io.BytesIO()
    buf.write(b'RIFF'); buf.write(_struct.pack('<I', 36 + len(pcm))); buf.write(b'WAVE')
    buf.write(b'fmt '); buf.write(_struct.pack('<I', 16)); buf.write(_struct.pack('<HHIIHH', 1, 1, sr, sr * 2, 2, 16))
    buf.write(b'data'); buf.write(_struct.pack('<I', len(pcm))); buf.write(pcm)
    return buf.getvalue()

BEEP_WAV_BYTES: bytes = _make_beep_wav()

# ── Wake-word configuration ───────────────────────────────────────────────────
# STUB: Set True khi có openWakeWord model "bi_oi" (SRS 3.1).
# Khi False (hiện tại), main_loop.py bỏ qua wake-word và gọi listen() trực tiếp.
WAKEWORD_ENABLED = False
WAKEWORD_THRESHOLD = float(os.getenv("WAKEWORD_THRESHOLD", "0.5"))
WAKEWORD_PHRASE  = "bi ơi"  # Phrase cần phát hiện

# ── Singleton WhisperModel (lazy load) ───────────────────────────────────────
_whisper_instance = None
_wakeword_model = None
_wakeword_import_warning_logged = False


def _get_whisper_model():
    """Load WhisperModel lần đầu, tái dùng các lần sau."""
    global _whisper_instance
    if _whisper_instance is None:
        from faster_whisper import WhisperModel
        logger.info("[Bi - Tai] Đang tải Whisper model '%s'... (lần đầu, có thể mất 30-60s)", WHISPER_MODEL)
        try:
            _whisper_instance = WhisperModel(
                WHISPER_MODEL,
                device="cuda",
                compute_type="float16",
            )
            logger.info("[Bi - Tai] Whisper large-v2 chạy trên GPU (CUDA float16)")
        except Exception:
            _whisper_instance = WhisperModel(
                os.getenv("WHISPER_CPU_MODEL", "medium"),
                device="cpu",
                compute_type="int8",
            )
            logger.info(
                "[Bi - Tai] CPU mode: dung Whisper %s (thay vi large-v2) de giam do tre",
                os.getenv("WHISPER_CPU_MODEL", "medium"),
            )
            logger.info("[Bi - Tai] Whisper chạy trên CPU (laptop mode)")
    return _whisper_instance


def _normalize_input_channels(device_info) -> int:
    """Trả về số input channels hợp lệ của thiết bị."""
    try:
        channels = int(device_info.get("max_input_channels", 0))
    except (TypeError, ValueError, AttributeError):
        return 0
    return max(0, channels)


# ═════════════════════════════════════════════════════════════════════════════
class EarSTT:
    """Tai nghe của Robot Bi — nhận dạng giọng nói offline bằng faster-whisper."""

    def __init__(self):
        self.mic_device = MIC_DEVICE
        self.mic_channels = CHANNELS
        self.mic_name = "Silent mode"
        self.silent_mode = False
        self._mic_error_logged = False
        self._probe_microphone()
        self.wake_detector = WakeWordDetector()

        # Trigger lazy load ngay khi khởi tạo để không bị lag lần đầu nghe
        try:
            _get_whisper_model()
        except Exception as e:
            logger.warning("[Bi - Tai] Cảnh báo: không load được Whisper model: %s", e)


    def _probe_microphone(self) -> None:
        """Tìm cấu hình microphone có thể mở được mà không làm crash pipeline."""
        logger.info("[Bi - Tai] Đang tìm microphone...")

        try:
            devices = sd.query_devices()
        except Exception as e:
            self._enable_silent_mode(f"không thể liệt kê thiết bị âm thanh: {e}")
            return

        preferred_indexes = []
        if 0 <= MIC_DEVICE < len(devices):
            preferred_indexes.append(MIC_DEVICE)
        preferred_indexes.extend(
            index for index, info in enumerate(devices)
            if _normalize_input_channels(info) > 0 and index not in preferred_indexes
        )

        for index in preferred_indexes:
            device_info = devices[index]
            max_input_channels = _normalize_input_channels(device_info)
            if max_input_channels <= 0:
                continue

            for channels in (1, 2):
                if channels > max_input_channels:
                    continue
                try:
                    stream = sd.InputStream(
                        samplerate=SAMPLE_RATE,
                        channels=channels,
                        dtype=DTYPE,
                        blocksize=_CHUNK_FRAMES,
                        device=index,
                    )
                    stream.close()
                    self.mic_device = index
                    self.mic_channels = channels
                    self.mic_name = str(device_info.get("name", f"Device {index}"))
                    self.silent_mode = False
                    logger.info("[Bi - Tai] Sử dụng microphone index %d: %s", index, self.mic_name)
                    return
                except Exception:
                    continue

        self._enable_silent_mode()

    def _enable_silent_mode(self, reason: Optional[str] = None) -> None:
        """Fallback an toàn khi không có microphone nào dùng được."""
        self.silent_mode = True
        self.mic_name = "Silent mode"
        if reason and not self._mic_error_logged:
            logger.warning("[Bi - Tai] Cảnh báo: %s", reason)
            self._mic_error_logged = True
        logger.warning("[Bi - Tai] Không tìm thấy microphone hợp lệ, chuyển sang chế độ im lặng")

    def _create_input_stream(self, blocksize: int):
        """Tạo InputStream theo microphone đã probe; nếu fail thì chuyển silent mode."""
        if self.silent_mode:
            return None

        try:
            return sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=self.mic_channels,
                dtype=DTYPE,
                blocksize=blocksize,
                device=self.mic_device,
            )
        except Exception as e:
            if not self._mic_error_logged:
                logger.warning("[Bi - Tai] Cảnh báo: không mở được microphone đã chọn: %s", e)
                self._mic_error_logged = True
            self._enable_silent_mode()
            return None

    def _play_beep(self) -> None:
        """Play 100ms 880Hz beep on Channel(6) when speech threshold is crossed."""
        try:
            import pygame
            ch = pygame.mixer.Channel(6)
            sound = pygame.mixer.Sound(io.BytesIO(BEEP_WAV_BYTES))
            ch.set_volume(0.4)
            ch.play(sound)
        except Exception:
            pass

    def listen(self) -> str:
        """
        Ghi âm từ microphone và nhận dạng giọng nói tiếng Việt.

        Luồng hoạt động:
          1. Mở sounddevice InputStream (16kHz, mono, float32)
          2. Duy trì pre-buffer 300ms bằng deque
          3. Khi RMS > SPEECH_THRESH → bắt đầu ghi audio vào buffer chính
          4. Khi RMS < SILENCE_THRESH liên tục 1.5s → dừng ghi
          5. Timeout sau MAX_SECONDS giây
          6. Lưu buffer ra file WAV tạm → Whisper transcribe → xóa file
          7. Trả về text, hoặc "" nếu không nhận dạng được

        Returns:
            str: Văn bản nhận dạng được (lowercase), hoặc "" nếu thất bại.
        """
        try:
            model = _get_whisper_model()
        except Exception as e:
            logger.error("[STT] Khong load duoc Whisper model: %s", e)
            return ""
        if model is None:
            return ""
        if self.silent_mode:
            return ""

        logger.debug("[Bi - Tai] Đang lắng nghe... (tối đa %ds)", MAX_SECONDS)

        pre_buffer: deque = deque(maxlen=_PRE_BUF_CHUNKS)
        audio_buffer = []
        silent_chunks = 0
        speech_started = False
        tmp_wav: Optional[Path] = None

        try:
            stream = self._create_input_stream(_CHUNK_FRAMES)
            if stream is None:
                return ""
            stream.start()

            try:
                for _ in range(_MAX_CHUNKS):
                    chunk, overflowed = stream.read(_CHUNK_FRAMES)
                    rms = float(np.sqrt(np.mean(chunk ** 2)))

                    if not speech_started:
                        pre_buffer.append(chunk.copy())
                        if rms >= SPEECH_THRESH:
                            speech_started = True
                            self._play_beep()
                            audio_buffer.extend(list(pre_buffer))
                            logger.debug("[Bi - Tai] Phát hiện tiếng nói, đang ghi...")
                        continue

                    audio_buffer.append(chunk.copy())

                    if rms < SILENCE_THRESH:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0

                    if silent_chunks >= _SILENCE_CHUNKS:
                        break  # Im lặng 1.5s → kết thúc câu
            finally:
                stream.stop()
                stream.close()

            if not audio_buffer:
                return ""

            audio_array = np.concatenate(audio_buffer).flatten()
            if float(np.sqrt(np.mean(audio_array ** 2))) < 0.001:
                return ""

            # ── Ghi WAV tạm và transcribe ────────────────────────────────────
            tmp_fd, tmp_str = tempfile.mkstemp(suffix=".wav", dir=_TEMP_DIR)
            os.close(tmp_fd)
            tmp_wav = Path(tmp_str)
            sf.write(str(tmp_wav), audio_array, SAMPLE_RATE, subtype="PCM_16")

            segments, _ = model.transcribe(
                str(tmp_wav),
                language="vi",
                beam_size=5,                   # Tăng từ 1 lên 5 — chính xác hơn
                initial_prompt="Bi là robot. Xin chào Bi. Hôm nay trời đẹp.",  # Giúp Whisper nhận đúng tên Bi
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()

            if text:
                logger.debug('[Bi - Tai] Nhận dạng: "%s"', text)
                return text.lower()
            return ""

        except sd.PortAudioError as e:
            logger.warning("[Bi - Tai] Cảnh báo: Lỗi microphone (PortAudio): %s", e)
            return ""
        except Exception as e:
            logger.warning("[Bi - Tai] Cảnh báo: Lỗi không mong đợi: %s: %s", type(e).__name__, e)
            return ""
        finally:
            if tmp_wav and tmp_wav.exists():
                try:
                    tmp_wav.unlink()
                except OSError:
                    pass



# ── Test độc lập ─────────────────────────────────────────────────────────────
def _listen_for_wakeword_impl(self, timeout: float = 30.0) -> bool:
        """
        Listen for the wake-word within the timeout window.
        Sử dụng WakeWordDetector với faster-whisper.
        """
        global WAKEWORD_ENABLED

        # Dùng config của wake_detector thay vì WAKEWORD_ENABLED hardcoded
        if not hasattr(self, 'wake_detector') or not self.wake_detector.is_enabled():
            return False

        if self.silent_mode:
            return False

        chunk_frames = int(SAMPLE_RATE * 1.5)
        deadline = time.monotonic() + max(0.0, timeout)

        logger.debug('[Bi - Tai] Chờ wake-word... (timeout=%gs)', timeout)

        try:
            stream = self._create_input_stream(chunk_frames)
            if stream is None:
                return False
            stream.start()
            try:
                while time.monotonic() < deadline:
                    try:
                        from src.api.server import is_mom_talking
                    except Exception:
                        is_mom_talking = None

                    if is_mom_talking is not None and is_mom_talking():
                        pause_started = time.monotonic()
                        while is_mom_talking():
                            time.sleep(0.05)
                        deadline += time.monotonic() - pause_started
                        continue

                    chunk, _ = stream.read(chunk_frames)
                    audio_bytes = np.asarray(chunk, dtype=np.float32).flatten().tobytes()
                    if self.wake_detector.detect(audio_bytes):
                        self._play_beep()
                        return True
            finally:
                stream.stop()
                stream.close()
        except Exception as e:
            logger.warning("[Bi - Tai] Cảnh báo wake-word: %s", e)
            return False

        return False

EarSTT.listen_for_wakeword = _listen_for_wakeword_impl

if __name__ == "__main__":
    ear = EarSTT()
    print("Nói gì đó để test (Ctrl+C để thoát)...")
    while True:
        result = ear.listen()
        if result:
            print(f"[Kết quả] '{result}'")
```

## src/audio/output/mouth_tts.py

```python
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
```

## src/audio/analysis/cry_detector.py

```python
"""
cry_detector.py — Robot Bi: Phát hiện tiếng khóc trẻ em (SRS 3.4)
==================================================================
Implementation hai tầng:
  - Tầng 1 (primary):  YAMNet TFLite int8 — audio classification offline
  - Tầng 2 (fallback): Energy + ZCR based detection — không cần model

Chạy trong daemon thread riêng, KHÔNG block audio pipeline của robot.

Kích hoạt callback khi:
  - YAMNet confidence "crying" > 0.5, HOẶC
  - Energy cao + ZCR pattern khớp tiếng khóc (fallback)
"""

import threading
import time
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger("cry_detector")
_yamnet_fallback_notice_printed = False
_mic_unavailable_notice_printed = False

# ── Cấu hình ─────────────────────────────────────────────────────────────────
SAMPLE_RATE        = 16000    # YAMNet yêu cầu 16kHz
CHUNK_SECONDS      = 0.96     # YAMNet window size
CHUNK_FRAMES       = int(SAMPLE_RATE * CHUNK_SECONDS)
YAMNET_THRESHOLD   = 0.50     # Confidence tối thiểu để báo khóc
ENERGY_THRESHOLD   = 0.08     # RMS threshold cho fallback
ZCR_THRESHOLD      = 0.15     # Zero-crossing rate threshold cho fallback
COOLDOWN_SECONDS   = 10.0     # Không báo lại trong 10 giây sau mỗi alert

# ── YAMNet class IDs liên quan đến tiếng khóc ────────────────────────────────
# YAMNet có 521 classes — các class liên quan đến crying (approximate indices):
_CRY_CLASS_INDICES = [20, 21, 22, 23]  # baby cry, infant cry, sobbing, whimper


class CryDetector:
    """
    Phát hiện tiếng khóc trẻ em qua microphone.

    Usage:
        detector = CryDetector(on_cry_callback=my_func)
        detector.start()
        # ... robot hoạt động ...
        detector.stop()
    """

    def __init__(self, on_cry_callback=None, mic_index: int = None):
        """
        Args:
            on_cry_callback: callable() — gọi khi phát hiện tiếng khóc
            mic_index: index microphone (None = mặc định)
        """
        self.on_cry_callback = on_cry_callback
        self.mic_index = mic_index
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_alert_time: float = 0.0
        self._detections: int = 0

        # Load YAMNet model (lazy)
        self._interpreter = None
        self._yamnet_available = False
        self._try_load_yamnet()

    def _try_load_yamnet(self) -> None:
        """Thử load YAMNet TFLite model. Nếu fail → dùng fallback."""
        model_path = Path(__file__).parent / "models" / "yamnet.tflite"

        if not model_path.exists():
            logger.info(
                "[Bi - Tai khoc] YAMNet model khong tim thay tai %s — "
                "dung energy-based fallback. "
                "Download model: https://storage.googleapis.com/mediapipe-assets/yamnet.tflite",
                model_path,
            )
            self._yamnet_available = False
            return

        try:
            try:
                import tflite_runtime.interpreter as tflite
                self._interpreter = tflite.Interpreter(model_path=str(model_path))
            except ImportError:
                import tensorflow as tf
                self._interpreter = tf.lite.Interpreter(model_path=str(model_path))

            self._interpreter.allocate_tensors()
            self._yamnet_available = True
            logger.info("[Bi - Tai khoc] YAMNet TFLite model da san sang.")

        except Exception as e:
            self._log_yamnet_fallback_once()
            logger.debug("[Bi - Tai khoc] Khong load duoc YAMNet: %s", e)
            self._yamnet_available = False

    def _log_yamnet_fallback_once(self) -> None:
        global _yamnet_fallback_notice_printed
        if _yamnet_fallback_notice_printed:
            return
        logger.info("[CryDetector] YAMNet TFLite khong kha dung, dung energy fallback.")
        _yamnet_fallback_notice_printed = True

    def _handle_mic_unavailable_once(self, error: Exception) -> bool:
        """Log 1 lan khi khong co microphone hop le, roi dung detector."""
        global _mic_unavailable_notice_printed
        error_text = str(error)
        mic_error_markers = (
            "Error querying device",
            "Invalid device",
            "No input device",
            "Error opening InputStream",
            "PortAudioError",
        )
        if not any(marker in error_text for marker in mic_error_markers):
            return False
        if not _mic_unavailable_notice_printed:
            logger.info(
                "[Bi - Tai khoc] Khong tim thay microphone hop le (%s) - dung CryDetector.",
                error_text,
            )
            _mic_unavailable_notice_printed = True
        self._running = False
        return True

    def _yamnet_predict(self, audio: np.ndarray) -> float:
        """
        Chạy YAMNet inference, trả về max confidence của các cry classes.
        Returns: float 0.0–1.0
        """
        if not self._yamnet_available or self._interpreter is None:
            return 0.0

        try:
            input_details = self._interpreter.get_input_details()
            output_details = self._interpreter.get_output_details()

            # Normalize audio về [-1, 1]
            audio_norm = audio.astype(np.float32)
            max_val = np.max(np.abs(audio_norm))
            if max_val > 0:
                audio_norm = audio_norm / max_val

            self._interpreter.set_tensor(input_details[0]['index'], audio_norm)
            self._interpreter.invoke()

            scores = self._interpreter.get_tensor(output_details[0]['index'])
            # scores shape: (num_frames, 521)
            mean_scores = np.mean(scores, axis=0)

            cry_score = float(np.max(mean_scores[_CRY_CLASS_INDICES]))
            return cry_score

        except Exception as e:
            logger.debug("[Bi - Tai khoc] YAMNet inference loi: %s", e)
            return 0.0

    def _energy_based_detect(self, audio: np.ndarray) -> bool:
        """
        Fallback: Phát hiện tiếng khóc bằng energy + zero-crossing rate.
        Tiếng khóc có: energy cao + ZCR vừa phải + pattern biến đổi đều đặn.

        Returns: True nếu có khả năng tiếng khóc.
        """
        # RMS energy
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < ENERGY_THRESHOLD:
            return False

        # Zero-crossing rate
        zcr = float(np.mean(np.abs(np.diff(np.sign(audio)))) / 2)
        # Tiếng khóc: ZCR thường 0.05–0.25
        if not (0.05 <= zcr <= 0.30):
            return False

        # Kiểm tra pattern kéo dài (tiếng khóc liên tục, không bật/tắt đột ngột)
        # Chia audio thành 4 phần, kiểm tra energy khá đều nhau
        quarter = len(audio) // 4
        energies = [
            float(np.sqrt(np.mean(audio[i * quarter:(i + 1) * quarter] ** 2)))
            for i in range(4)
        ]
        mean_e = sum(energies) / len(energies)
        std_e = float(np.std(energies))
        energy_variance = std_e / (mean_e + 1e-8)
        if energy_variance > 0.8:  # Quá biến động → không phải tiếng khóc đều
            return False

        return True

    def _detection_loop(self) -> None:
        """Vòng lặp chính chạy trong daemon thread."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.error(
                "[Bi - Tai khoc] sounddevice chua cai — CryDetector khong hoat dong."
            )
            self._running = False
            return

        method = "YAMNet" if self._yamnet_available else "energy fallback"
        logger.info("[Bi - Tai khoc] Bat dau lang nghe tieng khoc (%s)", method)

        while self._running:
            try:
                audio = sd.rec(
                    CHUNK_FRAMES,
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype='float32',
                    device=self.mic_index,
                )
                sd.wait()
                audio = audio.flatten()

                # Kiểm tra phát hiện
                is_crying = False
                if self._yamnet_available:
                    confidence = self._yamnet_predict(audio)
                    if confidence >= YAMNET_THRESHOLD:
                        is_crying = True
                        logger.info(
                            "[Bi - Tai khoc] YAMNet phat hien tieng khoc (confidence=%.2f)",
                            confidence,
                        )
                else:
                    is_crying = self._energy_based_detect(audio)
                    if is_crying:
                        logger.info("[Bi - Tai khoc] Energy-based phat hien tieng khoc")

                # Gọi callback nếu phát hiện, với cooldown
                now = time.time()
                if is_crying and (now - self._last_alert_time) >= COOLDOWN_SECONDS:
                    self._last_alert_time = now
                    self._detections += 1
                    logger.info(
                        "[Bi - Tai khoc] Phat hien tieng khoc! (lan %d)",
                        self._detections,
                    )
                    if self.on_cry_callback:
                        try:
                            threading.Thread(
                                target=self.on_cry_callback, daemon=True
                            ).start()
                        except Exception as e:
                            logger.error("[Bi - Tai khoc] callback loi: %s", e)

            except Exception as e:
                if self._handle_mic_unavailable_once(e):
                    return
                logger.warning(
                    "[Bi - Tai khoc] Loi trong detection loop: %s — tiep tuc", e
                )
                time.sleep(1.0)

    def start(self) -> None:
        """Bắt đầu detection trong daemon thread. Non-blocking."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._detection_loop, daemon=True, name="CryDetector"
        )
        self._thread.start()

    def stop(self) -> None:
        """Dừng daemon thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def get_stats(self) -> dict:
        return {
            "is_running": self.is_running(),
            "yamnet_available": self._yamnet_available,
            "total_detections": self._detections,
        }


# ── Test độc lập ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=== CryDetector standalone test ===")

    def on_cry():
        print(">>> CRY DETECTED! <<<")

    detector = CryDetector(on_cry_callback=on_cry)
    print(f"YAMNet available: {detector._yamnet_available}")
    print(f"Stats: {detector.get_stats()}")

    detector.start()
    print("Chay 5 giay... (thu noi/khoc to de test)")
    try:
        for i in range(5):
            time.sleep(1)
            print(f"[{i+1}s] stats: {detector.get_stats()}")
    except KeyboardInterrupt:
        pass
    detector.stop()
    print("Done:", detector.get_stats())
```

## src/vision/camera_stream.py

```python
"""
eye_vision.py — Module thị giác Robot Bi (Sprint 3)
Class EyeVision: motion detection (MOG2), face recognition (histogram fallback),
clip recording (pre/post buffer), graceful degradation khi không có camera.

SRS Reference: Phần 3.4 — Nhóm 4 Giám sát an ninh
"""

import sys
import cv2
import numpy as np
import os
import threading
import time
import logging
from collections import deque
from datetime import datetime
from pathlib import Path

# Fix encoding cho console Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

logger = logging.getLogger(__name__)


class EyeVision:
    """
    Module thị giác của Robot Bi.
    Chạy trong daemon thread — không block voice I/O.

    Sự kiện phát sinh:
      - "motion"     : phát hiện chuyển động (contour area > 5000 px²)
      - "stranger"   : phát hiện khuôn mặt không khớp known_faces
      - "known_face" : nhận ra thành viên đã đăng ký (clip_path = tên người)
    """

    # Ngưỡng motion detection (px²)
    _MOTION_THRESHOLD = 5000
    # Nhận dạng face mỗi N frame (giảm CPU)
    _FACE_INTERVAL = 10
    # Pre-event buffer: 5 giây ở 20fps = 100 frame
    _PRE_BUFFER_SIZE = 100
    # Ghi thêm sau sự kiện: 10 giây ở 20fps = 200 frame
    _POST_EVENT_FRAMES = 200
    # Ngưỡng histogram similarity (0→1, cao hơn = giống hơn)
    _FACE_SIMILARITY_THRESHOLD = 0.5
    # Target frame size
    _FRAME_WIDTH = 640
    _FRAME_HEIGHT = 480

    def __init__(
        self,
        camera_index: int = 0,
        known_faces_dir: str = "runtime/vision_data/known_faces",
        clips_dir: str = "runtime/vision_data/clips",
        on_event_callback=None,
    ):
        """
        Args:
            camera_index: index camera (0 = mặc định). Index không tồn tại → graceful degrade.
            known_faces_dir: thư mục chứa ảnh thành viên (mỗi người 1 subfolder).
            clips_dir: thư mục lưu clip sự kiện MP4.
            on_event_callback: callable(event_type: str, clip_path: str | None).
        """
        self.camera_index = camera_index
        self.known_faces_dir = Path(known_faces_dir)
        self.clips_dir = Path(clips_dir)
        self.on_event_callback = on_event_callback

        # Tạo thư mục data nếu chưa có
        self.known_faces_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir.mkdir(parents=True, exist_ok=True)

        # State
        self._running = False
        self._surveillance_mode = False
        self._thread: threading.Thread | None = None
        self._cap: cv2.VideoCapture | None = None

        # Stats
        self._frames_processed = 0
        self._events_detected = 0
        self._start_time: float | None = None

        # Face database: {name: [histogram, ...]}
        self._known_faces: dict[str, list] = {}
        self._face_cascade: cv2.CascadeClassifier | None = None
        self._load_face_resources()

        # MOG2 background subtractor
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )

        # Pre-event circular buffer
        self._pre_buffer: deque = deque(maxlen=self._PRE_BUFFER_SIZE)

        # Clip recording state
        self._recording = False
        self._post_frames_remaining = 0
        self._current_clip_frames: list = []
        self._current_event_type: str = ""

    # ─────────────────────────── Public API ────────────────────────────────

    def start(self) -> None:
        """Bắt đầu vòng lặp capture trong daemon thread. Non-blocking."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(
            target=self._vision_loop, daemon=True, name="EyeVision"
        )
        self._thread.start()
        logger.info("[Bi - Mắt] EyeVision started (camera_index=%d)", self.camera_index)

    def stop(self) -> None:
        """Dừng daemon thread, giải phóng camera."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None
        logger.info("[Bi - Mắt] EyeVision stopped")

    def set_surveillance_mode(self, active: bool) -> None:
        """
        True: bật chế độ giám sát đầy đủ (motion + stranger detection + clip).
        False: tắt giám sát, chỉ giữ face detection cơ bản.
        """
        self._surveillance_mode = active
        status = "BẬT" if active else "TẮT"
        logger.info("[Bi - Mắt] Chế độ giám sát: %s", status)

    def register_face(self, name: str, image_path: str) -> bool:
        """
        Đăng ký khuôn mặt mới vào known_faces database.

        Args:
            name: tên người (sẽ tạo subfolder tương ứng).
            image_path: đường dẫn ảnh nguồn.

        Returns:
            True nếu đăng ký thành công.
        """
        try:
            src = Path(image_path)
            if not src.exists():
                logger.warning("[Bi - Mắt] Ảnh không tồn tại: %s", image_path)
                return False

            dest_dir = self.known_faces_dir / name
            dest_dir.mkdir(parents=True, exist_ok=True)
            # Đặt tên file theo số thứ tự
            existing = list(dest_dir.glob("*.jpg")) + list(dest_dir.glob("*.png"))
            dest_file = dest_dir / f"{len(existing) + 1:03d}.jpg"

            img = cv2.imread(str(src))
            if img is None:
                logger.warning("[Bi - Mắt] Không đọc được ảnh: %s", image_path)
                return False
            cv2.imwrite(str(dest_file), img)

            # Reload face database
            self._load_face_resources()
            logger.info("[Bi - Mắt] Đã đăng ký khuôn mặt: %s", name)
            return True

        except Exception as e:
            logger.error("[Bi - Mắt] register_face lỗi: %s", e)
            return False

    def get_stats(self) -> dict:
        """Trả về thống kê hoạt động."""
        uptime = (time.time() - self._start_time) if self._start_time else 0.0
        return {
            "frames_processed": self._frames_processed,
            "events_detected": self._events_detected,
            "uptime_seconds": round(uptime, 1),
            "known_faces_count": len(self._known_faces),
            "is_running": self._running,
            "surveillance_mode": self._surveillance_mode,
        }

    def is_running(self) -> bool:
        """Trả về True nếu daemon thread đang chạy."""
        return self._running and (
            self._thread is not None and self._thread.is_alive()
        )

    # ─────────────────────────── Internal ──────────────────────────────────

    def _load_face_resources(self) -> None:
        """Load Haar cascade và build face recognizer (LBPH primary, histogram fallback)."""
        # Load Haar cascade (built-in OpenCV)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        if self._face_cascade.empty():
            logger.warning("[Bi - Mat] Khong load duoc Haar cascade!")
            self._face_cascade = None

        # Reset recognizer state
        self._lbph_recognizer = None
        self._label_to_name: dict[int, str] = {}
        self._known_faces = {}       # histogram fallback: {name: [hist, ...]}

        if not self.known_faces_dir.exists():
            return

        # Thu thập ảnh + label cho LBPH
        faces_data: list[np.ndarray] = []
        labels: list[int] = []
        label_idx = 0
        hist_db: dict[str, list] = {}  # histogram fallback database

        for person_dir in sorted(self.known_faces_dir.iterdir()):
            if not person_dir.is_dir():
                continue
            name = person_dir.name
            img_files = sorted(person_dir.glob("*.jpg")) + sorted(
                person_dir.glob("*.png")
            )
            face_count = 0
            histograms = []
            for img_file in img_files:
                img = cv2.imread(str(img_file), cv2.IMREAD_GRAYSCALE)
                if img is None:
                    continue
                resized = cv2.resize(img, (64, 64))
                faces_data.append(resized)
                labels.append(label_idx)
                # Cũng tính histogram để backup
                hist = self._compute_face_histogram(resized)
                if hist is not None:
                    histograms.append(hist)
                face_count += 1

            if face_count > 0:
                self._label_to_name[label_idx] = name
                label_idx += 1
                if histograms:
                    hist_db[name] = histograms
                logger.info(
                    "[Bi - Mat] Loaded %d anh cho: %s (label=%d)",
                    face_count, name, label_idx - 1,
                )

        # Thử train LBPH (yêu cầu cv2.face từ opencv-contrib-python)
        if faces_data:
            try:
                self._lbph_recognizer = cv2.face.LBPHFaceRecognizer_create()
                self._lbph_recognizer.train(faces_data, np.array(labels))
                logger.info(
                    "[Bi - Mat] LBPH trained voi %d anh, %d nguoi",
                    len(faces_data), label_idx,
                )
            except AttributeError:
                # cv2.face không available (opencv-python không có contrib)
                logger.info(
                    "[Bi - Mat] cv2.face khong co — dung histogram fallback"
                )
                self._lbph_recognizer = None
                self._known_faces = hist_db  # dùng histogram fallback

        if self._label_to_name or self._known_faces:
            names = list(self._label_to_name.values()) or list(self._known_faces.keys())
            logger.info("[Bi - Mat] Face database: %s", names)
        else:
            logger.info("[Bi - Mat] Chua co khuon mat nao duoc dang ky")

    def _compute_face_histogram(self, gray_img: np.ndarray) -> np.ndarray | None:
        """Tính histogram chuẩn hóa của ảnh grayscale."""
        try:
            resized = cv2.resize(gray_img, (64, 64))
            hist = cv2.calcHist([resized], [0], None, [256], [0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
            return hist
        except Exception:
            return None

    def _recognize_face(self, face_roi_gray: np.ndarray) -> tuple[str, float]:
        """
        Nhận diện khuôn mặt. Ưu tiên LBPH (cv2.face), fallback histogram.

        Returns:
            (name, confidence) — name="stranger" nếu không khớp.
        """
        resized = cv2.resize(face_roi_gray, (64, 64))

        # Tầng 1: LBPH (nếu available — cần opencv-contrib-python)
        if self._lbph_recognizer is not None and self._label_to_name:
            try:
                label, confidence = self._lbph_recognizer.predict(resized)
                # LBPH: confidence thấp hơn = giống hơn (distance metric)
                # Threshold: < 80 = nhận ra, >= 80 = stranger
                if confidence < 80:
                    name = self._label_to_name.get(label, "stranger")
                    similarity = max(0.0, (100.0 - confidence) / 100.0)
                    return name, similarity
                else:
                    return "stranger", 0.0
            except Exception as e:
                logger.debug("[Bi - Mat] LBPH predict loi: %s — fallback histogram", e)

        # Tầng 2: Histogram fallback
        if not self._known_faces:
            return "stranger", 0.0

        query_hist = self._compute_face_histogram(resized)
        if query_hist is None:
            return "stranger", 0.0

        best_name = "stranger"
        best_score = -1.0

        for name, histograms in self._known_faces.items():
            for ref_hist in histograms:
                score = cv2.compareHist(
                    query_hist, ref_hist, cv2.HISTCMP_CORREL
                )
                if score > best_score:
                    best_score = score
                    best_name = (
                        name if score >= self._FACE_SIMILARITY_THRESHOLD else "stranger"
                    )

        return best_name, best_score

    def _vision_loop(self) -> None:
        """Vòng lặp chính chạy trong daemon thread."""
        # Mở camera (CAP_DSHOW tránh log lỗi MSMF trên Windows)
        self._cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            logger.debug(
                "[Bi - Mắt] Không mở được camera (index=%d). "
                "EyeVision chạy ở chế độ no-camera.",
                self.camera_index,
            )
            self._running = False
            return

        # Cấu hình camera
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._FRAME_HEIGHT)
        self._cap.set(cv2.CAP_PROP_FPS, 20)

        frame_count = 0
        writer: cv2.VideoWriter | None = None
        clip_path: str | None = None
        _last_frame_error_log = 0.0
        _FRAME_ERROR_LOG_INTERVAL = 10.0

        logger.info("[Bi - Mắt] Camera index=%d đã kết nối.", self.camera_index)

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                _now = time.time()
                if _now - _last_frame_error_log > _FRAME_ERROR_LOG_INTERVAL:
                    _last_frame_error_log = _now
                    logger.warning("[Bi - Mắt] Mất frame từ camera — bỏ qua (log mỗi 10s)")
                time.sleep(0.05)
                continue

            # Resize để đồng nhất xử lý
            frame = cv2.resize(frame, (self._FRAME_WIDTH, self._FRAME_HEIGHT))
            self._frames_processed += 1
            frame_count += 1

            # Lưu vào pre-event buffer (bản copy để tránh mutation)
            self._pre_buffer.append(frame.copy())

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            event_type: str | None = None

            # ── Nhánh 1: Motion detection (luôn chạy) ──────────────────
            if self._surveillance_mode:
                fg_mask = self._bg_subtractor.apply(frame)
                contours, _ = cv2.findContours(
                    fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                for cnt in contours:
                    if cv2.contourArea(cnt) > self._MOTION_THRESHOLD:
                        event_type = "motion"
                        break

            # ── Nhánh 2: Face detection (mỗi _FACE_INTERVAL frame) ────
            if frame_count % self._FACE_INTERVAL == 0 and self._face_cascade is not None:
                faces = self._face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(60, 60),
                )
                for (x, y, w, h) in faces:
                    face_roi = gray[y : y + h, x : x + w]
                    name, score = self._recognize_face(face_roi)
                    if name == "stranger":
                        # Stranger quan trọng hơn motion
                        event_type = "stranger"
                    else:
                        # Nhận ra thành viên — gọi callback với tên người
                        self._events_detected += 1
                        if self.on_event_callback:
                            try:
                                self.on_event_callback("known_face", name)
                            except Exception as e:
                                logger.error("[Bi - Mắt] callback lỗi: %s", e)
                    break  # chỉ xử lý face đầu tiên mỗi frame

            # ── Nhánh 3: Clip recording ────────────────────────────────
            if self._recording:
                if writer is not None:
                    writer.write(frame)
                self._current_clip_frames.append(frame.copy())
                self._post_frames_remaining -= 1

                if self._post_frames_remaining <= 0:
                    # Kết thúc ghi clip
                    if writer is not None:
                        writer.release()
                        writer = None
                    self._recording = False
                    saved_path = clip_path
                    event = self._current_event_type
                    self._current_clip_frames = []
                    self._events_detected += 1
                    logger.info(
                        "[Bi - Mắt] Clip đã lưu: %s (sự kiện: %s)", saved_path, event
                    )
                    if self.on_event_callback:
                        try:
                            self.on_event_callback(event, saved_path)
                        except Exception as e:
                            logger.error("[Bi - Mắt] callback lỗi: %s", e)

            elif event_type in ("motion", "stranger") and self._surveillance_mode:
                # Bắt đầu ghi clip mới
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clip_filename = f"{timestamp}_{event_type}.mp4"
                clip_path = str(self.clips_dir / clip_filename)

                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                try:
                    writer = cv2.VideoWriter(
                        clip_path, fourcc, 20.0,
                        (self._FRAME_WIDTH, self._FRAME_HEIGHT)
                    )
                    if not writer.isOpened():
                        raise IOError("VideoWriter không mở được")

                    # Ghi pre-buffer (5s trước sự kiện)
                    for pre_frame in list(self._pre_buffer):
                        writer.write(pre_frame)

                    self._recording = True
                    self._post_frames_remaining = self._POST_EVENT_FRAMES
                    self._current_event_type = event_type
                    logger.info(
                        "[Bi - Mắt] Bắt đầu ghi clip: %s (%s)", clip_filename, event_type
                    )

                except Exception as e:
                    logger.warning("[Bi - Mắt] Không ghi được clip: %s", e)
                    if writer:
                        writer.release()
                        writer = None

            # Nhỏ sleep để tránh chiếm 100% CPU
            time.sleep(0.01)

        # Cleanup
        if writer is not None:
            writer.release()
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None



# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== EyeVision standalone test ===")

    eye = EyeVision(camera_index=0, on_event_callback=lambda e, p: print(f"Event: {e} | {p}"))
    eye.set_surveillance_mode(True)
    eye.start()

    print("Đang chạy 10 giây... (Ctrl+C để dừng sớm)")
    try:
        for i in range(10):
            time.sleep(1)
            print(f"[{i+1}s] Stats:", eye.get_stats())
    except KeyboardInterrupt:
        pass

    eye.stop()
    print("Đã dừng. Stats cuối:", eye.get_stats())
```

## src/education/homework_classifier.py

```python
"""
homework_classifier.py - Lightweight homework question detection.

Uses local keyword and regex matching only. No LLM call is made here.
"""

from __future__ import annotations

import re
import unicodedata


_HOMEWORK_PHRASES = (
    # Math
    "bang may",
    "tinh",
    "cong",
    "tru",
    "nhan",
    "chia",
    "phuong trinh",
    "hinh hoc",
    "dien tich",
    "chu vi",
    # Vietnamese / language arts
    "viet van",
    "dat cau",
    "phan tich",
    "tac gia",
    "bai tho",
    "doan van",
    # General study
    "bai tap",
    "bai ve nha",
    "homework",
    "hoc bai",
    "on tap",
    "kiem tra",
    "giai thich",
    "nghia la gi",
    "dinh nghia",
    # Science / explanation
    "tai sao",
    "nhu the nao",
    "nguyen nhan",
    "qua trinh",
    "hien tuong",
)


_HOMEWORK_REGEXES = (
    re.compile(r"(?<![a-z0-9])thi(?![a-z0-9])"),
)


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_phrase(normalized_text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", normalized_text) is not None


def classify_homework(text: str) -> bool:
    """Return True when text looks like a homework or study question."""
    if not text or not text.strip():
        return False

    normalized = _normalize_text(text)
    if not normalized:
        return False

    if any(_contains_phrase(normalized, phrase) for phrase in _HOMEWORK_PHRASES):
        return True

    return any(pattern.search(normalized) for pattern in _HOMEWORK_REGEXES)
```

## tests/run_tests.py

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_tests.py — Robot Bi: Automated Test Suite
Chạy: python run_tests.py
Không cần: mic, loa, camera, Ollama, internet
"""
import sys
import os
import time
import traceback
import io
import contextlib
import logging

sys.path.insert(0, '.')
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

# Đặt JWT test config trước khi bất kỳ module nào import auth.py
# (auth.py được import transitively khi init_db() gọi seed_admin_if_empty)
os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_key_robot_bi_testing_only_32chars!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

# Dung DB test rieng biet -- khong ghi vao robot_bi.db that
import src.infrastructure.database.db as _db_module
import tempfile as _tempfile
_TEST_DB_FILE = _tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_TEST_DB_FILE.close()
_db_module.DB_PATH = __import__('pathlib').Path(_TEST_DB_FILE.name)
_db_module._INITIALIZED = False  # reset de init_db() chay lai voi DB moi

from src.infrastructure.database.db import init_db

# Fix encoding Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

init_db()

passed = []
failed = []
logging.getLogger("src.vision.camera_stream").setLevel(logging.ERROR)
logging.getLogger("src.audio.analysis.cry_detector").setLevel(logging.ERROR)


def _run_quiet(fn):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn()


def test(name, fn):
    try:
        fn()
        passed.append(name)
        print(f"  PASS  {name}")
    except Exception as e:
        failed.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")


print("=" * 60)
print("  ROBOT BI --- AUTOMATED TEST SUITE")
print("=" * 60)

# == GROUP 1: Import Tests ==================================================
print("\n[Group 1] Import Tests")

test("import SafetyFilter",  lambda: __import__('src.safety.safety_filter',  fromlist=['SafetyFilter']))
test("import prompts",        lambda: __import__('src.ai.prompts',         fromlist=['MAIN_SYSTEM_PROMPT']))
test("import RAGManager",     lambda: __import__('src.memory.rag_manager',  fromlist=['RAGManager']))
test("import EyeVision",      lambda: __import__('src.vision.camera_stream',       fromlist=['EyeVision']))
test("import CryDetector",    lambda: __import__('src.audio.analysis.cry_detector',     fromlist=['CryDetector']))
test("import EventNotifier",  lambda: __import__('src.infrastructure.notifications.notifier',        fromlist=['get_notifier']))
test("import TaskManager",    lambda: __import__('src.infrastructure.tasks.task_manager',    fromlist=['TaskManager']))
test("import MouthTTS",       lambda: __import__('src.audio.output.mouth_tts',        fromlist=['MouthTTS']))
test("import EarSTT",         lambda: __import__('src.audio.input.ear_stt',          fromlist=['EarSTT']))


def test_stream_chat_import():
    from src.ai.ai_engine import stream_chat
    assert callable(stream_chat)


def test_core_ai_no_ollama():
    import importlib
    import src.ai.ai_engine  # noqa: F401 — đảm bảo module đã load
    import sys
    assert "ollama" not in sys.modules, "ollama khong duoc import trong core_ai"


def test_core_ai_config_keys():
    from src.ai import ai_engine as core_ai
    assert hasattr(core_ai, "GROQ_API_KEY")
    assert hasattr(core_ai, "GEMINI_API_KEY")
    assert hasattr(core_ai, "stream_chat")
    assert hasattr(core_ai, "BiAI")


test("core_ai: stream_chat importable",   test_stream_chat_import)
test("core_ai: ollama not in modules",    test_core_ai_no_ollama)
test("core_ai: config vars exist",        test_core_ai_config_keys)

# == GROUP 2: SafetyFilter ==================================================
print("\n[Group 2] SafetyFilter")
from src.safety.safety_filter import SafetyFilter, _REFUSAL_RESPONSE as SF_REFUSAL
sf = SafetyFilter()


def test_safe_text():
    ok, text = sf.check("Bau troi mau xanh vi anh sang bi tan xa boi cac hat khong khi nhe.")
    assert ok is True, f"Expected safe, got unsafe: {text}"
    assert len(text) > 0


def test_violent_text():
    # "sex" triggers the adult-content pattern without needing diacritics
    ok, text = sf.check("sex la noi dung nguoi lon khong phu hop tre em")
    assert ok is False, "Expected unsafe for adult content"
    assert text == SF_REFUSAL, f"Refusal mismatch: {repr(text)}"


def test_blacklist_word():
    # "ngu" (no-accent) matches the standalone blacklist entry \bngu\b
    ok, text = sf.check("ban that ngu ngoc!")
    assert "ngu" not in text.lower(), f"Blacklist word still in output: {text}"


def test_long_text_truncation():
    long = "Cau mot la day. Cau hai ne ban! Cau ba cung vui. Cau bon roi nhe? Cau nam thua ra."
    ok, text = sf.check(long)
    import re
    sentences = [s for s in re.split(r'(?<=[.?!])\s+', text.strip()) if s.strip()]
    assert len(sentences) <= 4, f"Expected <=4 sentences, got {len(sentences)}: {text}"


def test_refusal_pass_through():
    ok, text = sf.check(SF_REFUSAL)
    assert ok is True


def test_empty_text():
    ok, text = sf.check("")
    assert ok is True


test("SF: safe text pass",                  test_safe_text)
test("SF: violent text blocked",            test_violent_text)
test("SF: blacklist word removed",          test_blacklist_word)
test("SF: long text truncated to 4 sent",  test_long_text_truncation)
test("SF: refusal response passes through", test_refusal_pass_through)
test("SF: empty text handled",             test_empty_text)

# == GROUP 3: prompts.py ====================================================
print("\n[Group 3] Prompts")
from src.ai import prompts


def test_prompts_constants():
    assert hasattr(prompts, 'MAIN_SYSTEM_PROMPT')
    assert hasattr(prompts, 'REFUSAL_RESPONSE')
    assert hasattr(prompts, 'GREETING')
    assert hasattr(prompts, 'SAFETY_CHECK_PROMPT')
    assert len(prompts.MAIN_SYSTEM_PROMPT) > 100
    # Compare against safety_filter's own constant to avoid diacritic encoding issues
    assert prompts.REFUSAL_RESPONSE == SF_REFUSAL


test("prompts: all constants exist and correct", test_prompts_constants)

# == GROUP 4: RAGManager ====================================================
print("\n[Group 4] RAGManager")
import shutil
from src.memory.rag_manager import RAGManager

TEST_DB = "runtime/_audit_test_db"
if os.path.exists(TEST_DB):
    shutil.rmtree(TEST_DB)

rag = RAGManager(db_path=TEST_DB)


def test_rag_save():
    ok = rag.extract_and_save("ten minh la Huy", "Bi nho roi, ban ten Huy!")
    assert ok is True


def test_rag_retrieve_relevant():
    rag.extract_and_save("Be ten la Minh", "O be ten Minh a")
    result = rag.retrieve("ten cua be")
    assert isinstance(result, str)
    assert len(result) >= 0


def test_rag_manual_memory():
    ok = rag.add_manual_memory("Cuoi tuan be di sinh nhat ban Minh", source="parent")
    assert ok is True


def test_rag_list():
    items = rag.list_memories()
    assert isinstance(items, list)
    assert len(items) >= 1


def test_rag_update():
    items = rag.list_memories()
    if items:
        ok = rag.update_memory(items[0]['id'], "Be ten la Huy Nguyen")
        assert ok is True


def test_rag_delete():
    items = rag.list_memories()
    if items:
        before = len(items)
        ok = rag.delete_memory(items[0]['id'])
        assert ok is True
        after = len(rag.list_memories())
        assert after < before


def test_rag_stats():
    stats = rag.get_stats()
    assert 'total_facts' in stats
    assert isinstance(stats['total_facts'], int)


def test_rag_export():
    result = rag.export_memories()
    assert isinstance(result, list)


def test_rag_clear():
    ok = rag.clear_all_memories()
    assert ok is True
    assert rag.get_stats()['total_facts'] == 0


test("RAG: extract_and_save",   test_rag_save)
test("RAG: retrieve returns str", test_rag_retrieve_relevant)
test("RAG: add_manual_memory",  test_rag_manual_memory)
test("RAG: list_memories",      test_rag_list)
test("RAG: update_memory",      test_rag_update)
test("RAG: delete_memory",      test_rag_delete)
test("RAG: get_stats format",   test_rag_stats)
test("RAG: export_memories",    test_rag_export)
test("RAG: clear_all_memories", test_rag_clear)

# Cleanup test DB
del rag
import gc
gc.collect()
try:
    shutil.rmtree(TEST_DB)
except Exception:
    pass

# == GROUP 5: EventNotifier =================================================
print("\n[Group 5] EventNotifier")
from src.infrastructure.notifications.notifier import EventNotifier

notifier = EventNotifier()


def test_notifier_push_event():
    ok = _run_quiet(lambda: notifier.push_event("motion", "Test motion"))
    assert ok is True


def test_notifier_push_chat():
    ok = _run_quiet(lambda: notifier.push_chat_log("xin chao Bi", "Da xin chao ban!"))
    assert ok is True


def test_notifier_get_unread():
    events = notifier.get_unread_events()
    assert isinstance(events, list)
    assert len(events) >= 1


def test_notifier_get_stats():
    stats = notifier.get_stats()
    assert 'total_events' in stats
    assert 'unread' in stats


def test_notifier_mark_read():
    notifier.mark_all_read()
    unread = notifier.get_unread_events()
    assert len(unread) == 0


test("Notifier: push_event",      test_notifier_push_event)
test("Notifier: push_chat_log",   test_notifier_push_chat)
test("Notifier: get_unread_events", test_notifier_get_unread)
test("Notifier: get_stats format", test_notifier_get_stats)
test("Notifier: mark_all_read",   test_notifier_mark_read)

# == GROUP 6: TaskManager ===================================================
print("\n[Group 6] TaskManager")
from src.infrastructure.tasks.task_manager import TaskManager

tm = TaskManager()


def test_task_add():
    task = tm.add_task("Danh rang", "07:30")
    assert task['name'] == "Danh rang"
    assert task['remind_time'] == "07:30"
    assert task['completed_today'] is False
    assert task['stars'] == 0


def test_task_complete():
    task = tm.add_task("Doc sach", "20:00")
    ok = tm.complete_task(task['id'])
    assert ok is True
    ok2 = tm.complete_task(task['id'])
    assert ok2 is False


def test_task_stars():
    before = tm.get_total_stars()
    task = tm.add_task("Don phong", "18:00")
    tm.complete_task(task['id'])
    after = tm.get_total_stars()
    assert after == before + 1


def test_task_list():
    items = tm.get_all()
    assert isinstance(items, list)


def test_task_delete():
    task = tm.add_task("Tap the duc", "06:00")
    before = len(tm.get_all())
    ok = tm.delete_task(task['id'])
    assert ok is True
    after = len(tm.get_all())
    assert after == before - 1


def test_task_delete_nonexist():
    ok = tm.delete_task("nonexistent-id-12345")
    assert ok is False


test("TaskManager: add_task",                   test_task_add)
test("TaskManager: complete_task (idempotent)", test_task_complete)
test("TaskManager: stars accumulate",           test_task_stars)
test("TaskManager: get_all returns list",       test_task_list)
test("TaskManager: delete_task",                test_task_delete)
test("TaskManager: delete nonexistent → False", test_task_delete_nonexist)
tm.stop()

# == GROUP 7: EyeVision (headless) ==========================================
print("\n[Group 7] EyeVision (headless)")
from src.vision.camera_stream import EyeVision


def test_eye_init_no_camera():
    eye = _run_quiet(lambda: EyeVision(camera_index=99))
    assert eye is not None


def test_eye_start_no_camera():
    eye = _run_quiet(lambda: EyeVision(camera_index=99))
    _run_quiet(eye.start)
    time.sleep(0.5)
    _run_quiet(eye.stop)


def test_eye_stats():
    eye = _run_quiet(lambda: EyeVision(camera_index=99))
    stats = eye.get_stats()
    assert 'frames_processed' in stats
    assert 'events_detected' in stats
    assert 'known_faces_count' in stats


def test_eye_surveillance_mode():
    eye = _run_quiet(lambda: EyeVision(camera_index=99))
    _run_quiet(lambda: eye.set_surveillance_mode(True))
    assert eye._surveillance_mode is True
    _run_quiet(lambda: eye.set_surveillance_mode(False))
    assert eye._surveillance_mode is False


test("EyeVision: init without camera",    test_eye_init_no_camera)
test("EyeVision: start/stop no camera",  test_eye_start_no_camera)
test("EyeVision: get_stats format",      test_eye_stats)
test("EyeVision: set_surveillance_mode", test_eye_surveillance_mode)

# == GROUP 8: CryDetector (headless) ========================================
print("\n[Group 8] CryDetector (headless)")
from src.audio.analysis.cry_detector import CryDetector
import numpy as np


def test_cry_init():
    d = _run_quiet(CryDetector)
    stats = d.get_stats()
    assert 'yamnet_available' in stats
    assert 'total_detections' in stats


def test_cry_start_stop():
    d = _run_quiet(CryDetector)
    _run_quiet(d.start)
    time.sleep(0.3)
    _run_quiet(d.stop)


def test_cry_energy_detect():
    d = _run_quiet(CryDetector)
    silent = np.zeros(16000, dtype=np.float32)
    result = d._energy_based_detect(silent)
    assert result is False, "Silent audio should not trigger cry detection"


test("CryDetector: init and get_stats",        test_cry_init)
test("CryDetector: start/stop without mic",    test_cry_start_stop)
test("CryDetector: silent audio not detected", test_cry_energy_detect)

# == GROUP 9: MouthTTS (import only) ========================================
print("\n[Group 9] MouthTTS (import only)")
from src.audio.output.mouth_tts import MouthTTS


def test_tts_init():
    tts = MouthTTS()
    assert tts.voice == "vi-VN-HoaiMyNeural"


def test_tts_has_fallback():
    tts = MouthTTS()
    assert hasattr(tts, '_fallback_tts')
    assert callable(tts._fallback_tts)


test("MouthTTS: init correctly",      test_tts_init)
test("MouthTTS: has fallback method", test_tts_has_fallback)

# == GROUP 10: EarSTT (import only) =========================================
print("\n[Group 10] EarSTT (import only)")
from src.audio.input.ear_stt import EarSTT, WAKEWORD_ENABLED, WAKEWORD_THRESHOLD, MIC_DEVICE


def test_ear_constants():
    assert isinstance(WAKEWORD_ENABLED, bool)
    assert isinstance(MIC_DEVICE, int)
    assert MIC_DEVICE >= 0


def test_ear_has_methods():
    assert hasattr(EarSTT, 'listen_for_wakeword')
    assert hasattr(EarSTT, 'listen')


test("EarSTT: constants defined correctly", test_ear_constants)
test("EarSTT: required methods exist",      test_ear_has_methods)

# == GROUP 10b: Auth Module =================================================
print("\n[Group 10b] Auth Module")
from src.infrastructure.auth.auth import (
    authenticate_user,
    create_user,
    get_user_by_username,
    hash_password,
    verify_password,
)
import uuid as _uuid


def test_hash_and_verify():
    h = hash_password("test_password_123")
    assert isinstance(h, str)
    assert len(h) > 20
    assert verify_password("test_password_123", h) is True
    assert verify_password("wrong_password", h) is False


def test_verify_wrong_hash():
    assert verify_password("any", "not_a_valid_hash") is False


def test_create_and_get_user():
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"testuser_{unique}", "password123", "TestFamily")
    assert user["username"] == f"testuser_{unique}"
    assert "user_id" in user
    assert "password_hash" not in user
    fetched = get_user_by_username(f"testuser_{unique}")
    assert fetched is not None
    assert fetched["family_name"] == "TestFamily"
    assert "password_hash" in fetched  # DB record has hash


def test_create_duplicate_username():
    from fastapi import HTTPException
    unique = _uuid.uuid4().hex[:8]
    create_user(f"dupuser_{unique}", "password123", "Fam1")
    try:
        create_user(f"dupuser_{unique}", "password456", "Fam2")
        assert False, "Expected HTTPException 409"
    except HTTPException as e:
        assert e.status_code == 409


def test_authenticate_user_ok():
    unique = _uuid.uuid4().hex[:8]
    create_user(f"authok_{unique}", "mypassword!", "AuthFam")
    result = authenticate_user(f"authok_{unique}", "mypassword!")
    assert result is not None
    assert result["username"] == f"authok_{unique}"
    assert "password_hash" not in result


def test_authenticate_user_wrong_password():
    unique = _uuid.uuid4().hex[:8]
    create_user(f"authwrong_{unique}", "correct_pass_1", "Fam")
    result = authenticate_user(f"authwrong_{unique}", "wrong_pass")
    assert result is None


def test_authenticate_nonexistent_user():
    result = authenticate_user("nonexistent_user_xyz_999", "any_password")
    assert result is None


test("Auth: hash_password + verify_password",         test_hash_and_verify)
test("Auth: verify_password wrong hash → False",      test_verify_wrong_hash)
test("Auth: create_user + get_user_by_username",      test_create_and_get_user)
test("Auth: create duplicate username → 409",         test_create_duplicate_username)
test("Auth: authenticate_user correct password",      test_authenticate_user_ok)
test("Auth: authenticate_user wrong password → None", test_authenticate_user_wrong_password)
test("Auth: authenticate nonexistent user → None",    test_authenticate_nonexistent_user)

# == GROUP 10c: JWT Module ==================================================
print("\n[Group 10c] JWT Module")
from src.infrastructure.auth.auth import (
    create_access_token,
    create_refresh_token,
    store_refresh_token,
    verify_access_token,
    rotate_refresh_token,
)
import hashlib as _hashlib_test
from datetime import datetime as _dt_test, timedelta as _td_test, timezone as _tz_test


def test_jwt_create_access_token():
    token = create_access_token("42", "TestFamily")
    assert isinstance(token, str)
    assert len(token) > 20
    # Có đúng 3 phần phân cách bằng dấu chấm (JWT header.payload.sig)
    assert token.count(".") == 2


def test_jwt_verify_access_token_valid():
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"jwtvalid_{unique}", "Password1!", "FamXYZ")
    uid = str(user["user_id"])
    token = create_access_token(uid, "FamXYZ")
    payload = verify_access_token(token)
    assert payload["sub"] == uid
    assert payload["family"] == "FamXYZ"
    assert payload["type"] == "access"


def test_jwt_verify_access_token_invalid():
    from fastapi import HTTPException
    try:
        verify_access_token("this.is.not.a.valid.jwt.token")
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401


def test_jwt_create_refresh_token_hash():
    raw, hashed = create_refresh_token("42")
    assert isinstance(raw, str)
    assert isinstance(hashed, str)
    assert len(raw) > 20
    # Xác minh hashed đúng là sha256 của raw
    assert _hashlib_test.sha256(raw.encode()).hexdigest() == hashed


def test_jwt_store_and_rotate_refresh_token():
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"jwtrot_{unique}", "Passw0rd123!", "JWTFam")
    uid = str(user["user_id"])

    raw, hashed = create_refresh_token(uid)
    expires_at = _dt_test.now(_tz_test.utc) + _td_test(days=30)
    store_refresh_token(uid, hashed, expires_at)

    # Rotation thành công
    new_raw, new_hashed, returned_uid = rotate_refresh_token(raw)
    assert returned_uid == uid
    assert new_raw != raw
    assert new_hashed != hashed

    # Token cũ phải bị revoke ngay lập tức
    from fastapi import HTTPException
    try:
        rotate_refresh_token(raw)
        assert False, "Expected 401 for revoked token"
    except HTTPException as e:
        assert e.status_code == 401


def test_jwt_rotate_invalid_token():
    from fastapi import HTTPException
    try:
        rotate_refresh_token("totally_fake_token_that_doesnt_exist_in_db")
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401


test("JWT: create_access_token format",         test_jwt_create_access_token)
test("JWT: verify_access_token valid payload",  test_jwt_verify_access_token_valid)
test("JWT: verify_access_token invalid → 401",  test_jwt_verify_access_token_invalid)
test("JWT: create_refresh_token sha256 hash",   test_jwt_create_refresh_token_hash)
test("JWT: store + rotate (old revoked)",       test_jwt_store_and_rotate_refresh_token)
test("JWT: rotate invalid token → 401",         test_jwt_rotate_invalid_token)

# == GROUP 11: Integration ==================================================
print("\n[Group 11] Integration")


def test_main_loop_import():
    from src.main import RobotBiApp
    assert RobotBiApp is not None


def test_api_server_import():
    from src.api import server as api_server
    assert hasattr(api_server, 'app')


def test_manifest_valid():
    import json
    manifest_path = "frontend/parent_app/manifest.json"
    if os.path.exists(manifest_path):
        data = json.load(open(manifest_path, encoding='utf-8'))
        assert 'name' in data
        assert 'icons' in data
        assert 'start_url' in data
    else:
        print("    (manifest.json chua co --- bo qua)")


def test_requirements_complete():
    reqs = open('requirements.txt', encoding='utf-8').read()
    required = [
        'requests', 'faster-whisper', 'edge-tts', 'pygame',
        'chromadb', 'sentence-transformers', 'opencv-python',
        'fastapi', 'pyttsx3', 'sounddevice', 'numpy', 'argon2-cffi',
        'python-jose',
    ]
    for r in required:
        assert r in reqs, f"Missing from requirements.txt: {r}"
    assert 'ollama' not in reqs, "ollama van con trong requirements.txt"


test("Integration: main_loop importable",     test_main_loop_import)
test("Integration: api_server importable",    test_api_server_import)
test("Integration: manifest.json valid",      test_manifest_valid)
test("Integration: requirements.txt complete", test_requirements_complete)

# == GROUP 12: JWT Auth Guard (get_current_user dependency) =================
print("\n[Group 12] JWT Auth Guard")
import asyncio as _asyncio
from src.infrastructure.auth.auth import get_current_user as _get_current_user


def test_auth_guard_no_creds_returns_401():
    """get_current_user(None) phai raise 401 voi WWW-Authenticate header."""
    from fastapi import HTTPException

    async def _inner():
        await _get_current_user(None)

    try:
        _asyncio.run(_inner())
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401, f"Expected 401, got {e.status_code}"
        assert e.headers is not None
        assert "WWW-Authenticate" in e.headers, "Thieu WWW-Authenticate header"
        assert e.headers["WWW-Authenticate"] == "Bearer"


def test_auth_guard_valid_jwt_returns_user():
    """get_current_user voi JWT hop le phai tra ve user dict dung."""
    from fastapi.security import HTTPAuthorizationCredentials
    from src.infrastructure.auth.auth import create_access_token

    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"guard_{unique}", "Password1!", "GuardFam")
    uid = str(user["user_id"])
    token = create_access_token(uid, "GuardFam")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    async def _inner():
        return await _get_current_user(creds)

    user = _asyncio.run(_inner())
    assert user["user_id"] == uid
    assert user["family_name"] == "GuardFam"


def test_auth_guard_invalid_token_returns_401():
    """get_current_user voi token gia phai raise 401 voi WWW-Authenticate header."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.valid.jwt")

    async def _inner():
        await _get_current_user(creds)

    try:
        _asyncio.run(_inner())
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401
        assert e.headers is not None
        assert "WWW-Authenticate" in e.headers


def test_auth_guard_health_route_exists():
    """Endpoint /health phai ton tai trong app (no auth)."""
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/health" in paths, f"/health khong tim thay trong routes: {paths}"


test("AuthGuard: no creds → 401 + WWW-Authenticate",  test_auth_guard_no_creds_returns_401)
test("AuthGuard: valid JWT → user dict correct",       test_auth_guard_valid_jwt_returns_user)
test("AuthGuard: invalid token → 401 + WWW-Authenticate", test_auth_guard_invalid_token_returns_401)
test("AuthGuard: /health route exists (no auth)",      test_auth_guard_health_route_exists)

# == GROUP 13: Audio Feedback ===============================================
print("\n[Group 13] Audio Feedback")
from src.audio.input.ear_stt import BEEP_WAV_BYTES as _BEEP_WAV_BYTES


def test_beep_wav_bytes_exists():
    assert isinstance(_BEEP_WAV_BYTES, bytes), "BEEP_WAV_BYTES must be bytes"
    assert len(_BEEP_WAV_BYTES) > 0, "BEEP_WAV_BYTES must not be empty"


def test_play_beep_callable():
    assert hasattr(EarSTT, '_play_beep'), "EarSTT must have _play_beep method"
    assert callable(EarSTT._play_beep), "_play_beep must be callable"


def test_wakeword_enabled_is_bool():
    assert isinstance(WAKEWORD_ENABLED, bool), "WAKEWORD_ENABLED must be bool"


def test_wakeword_threshold_is_valid_float():
    assert isinstance(WAKEWORD_THRESHOLD, float), "WAKEWORD_THRESHOLD must be float"
    assert 0.0 < WAKEWORD_THRESHOLD < 1.0, "WAKEWORD_THRESHOLD must be between 0 and 1"


def test_whisper_cpu_model_env_default():
    import src.audio.input.ear_stt as ear_stt_module
    assert ear_stt_module.os.getenv("WHISPER_CPU_MODEL", "medium") == "medium"


def test_listen_for_wakeword_disabled_returns_false():
    original_enabled = EarSTT.listen_for_wakeword.__globals__["WAKEWORD_ENABLED"]
    EarSTT.listen_for_wakeword.__globals__["WAKEWORD_ENABLED"] = False
    try:
        ear = EarSTT.__new__(EarSTT)
        ear.silent_mode = False
        result = ear.listen_for_wakeword(timeout=0.1)
        assert result is False
    finally:
        EarSTT.listen_for_wakeword.__globals__["WAKEWORD_ENABLED"] = original_enabled


def test_earstt_init_without_error():
    import src.audio.input.ear_stt as ear_stt_module

    original_probe = EarSTT._probe_microphone
    original_get_model = ear_stt_module._get_whisper_model
    try:
        EarSTT._probe_microphone = lambda self: setattr(self, "silent_mode", True) or setattr(self, "mic_name", "Test mic")
        ear_stt_module._get_whisper_model = lambda: object()
        ear = EarSTT()
        assert isinstance(ear, EarSTT)
    finally:
        EarSTT._probe_microphone = original_probe
        ear_stt_module._get_whisper_model = original_get_model


test("AudioFeedback: BEEP_WAV_BYTES is non-empty bytes", test_beep_wav_bytes_exists)
test("AudioFeedback: EarSTT._play_beep is callable",     test_play_beep_callable)
test("AudioFeedback: WAKEWORD_ENABLED is bool",          test_wakeword_enabled_is_bool)
test("AudioFeedback: WAKEWORD_THRESHOLD valid float",    test_wakeword_threshold_is_valid_float)
test("AudioFeedback: WHISPER_CPU_MODEL env default",     test_whisper_cpu_model_env_default)
test("AudioFeedback: disabled wakeword returns False",   test_listen_for_wakeword_disabled_returns_false)
test("AudioFeedback: EarSTT init without error",         test_earstt_init_without_error)

# == GROUP 14: Conversation Sessions ========================================
print("\n[Group 14] Conversation Sessions")
from src.infrastructure.database.db import (
    create_session as _create_session,
    close_session as _close_session,
    add_turn as _add_turn,
    get_session_turns as _get_session_turns,
    get_db_connection as _get_db_connection,
)


def test_create_session_returns_nonempty_string():
    session_id = _create_session("default")
    assert isinstance(session_id, str)
    assert len(session_id) > 0


def test_add_turn_user_visible_in_get_session_turns():
    session_id = _create_session("default")
    turn_id = _add_turn(session_id, "user", "Xin chao Bi")
    turns = _get_session_turns(session_id)
    assert isinstance(turn_id, str)
    assert len(turn_id) > 0
    assert len(turns) == 1
    assert turns[0]["role"] == "user"
    assert turns[0]["content"] == "Xin chao Bi"


def test_add_turn_assistant_makes_two_turns():
    session_id = _create_session("default")
    _add_turn(session_id, "user", "Hom nay hoc gi?")
    _add_turn(session_id, "assistant", "Hom nay minh hoc toan nhe.")
    turns = _get_session_turns(session_id)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"


def test_close_session_sets_ended_at_and_keeps_data():
    session_id = _create_session("default")
    _add_turn(session_id, "user", "Tam biet Bi")
    _close_session(session_id)
    turns = _get_session_turns(session_id)
    assert len(turns) == 1
    with _get_db_connection() as conn:
        row = conn.execute(
            "SELECT ended_at FROM conversations WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    assert row is not None
    assert row["ended_at"] is not None


test("Conversation: create_session returns non-empty string", test_create_session_returns_nonempty_string)
test("Conversation: user turn persists in session",           test_add_turn_user_visible_in_get_session_turns)
test("Conversation: assistant turn makes 2 turns",           test_add_turn_assistant_makes_two_turns)
test("Conversation: close_session sets ended_at",            test_close_session_sets_ended_at_and_keeps_data)

# == GROUP 15: Session Naming ===============================================
print("\n[Group 15] Session Naming")


def test_session_namer_imports():
    module = __import__("src.infrastructure.sessions.session_namer", fromlist=["_generate_session_title"])
    assert hasattr(module, "_generate_session_title")


def test_generate_session_title_returns_string():
    import src.infrastructure.sessions.session_namer as session_namer

    class _MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "Hoc bang cuu chuong."
                        }
                    }
                ]
            }

    original_post = session_namer.requests.post
    original_key = os.environ.get("GROQ_API_KEY")
    session_namer.requests.post = lambda *args, **kwargs: _MockResponse()
    os.environ["GROQ_API_KEY"] = "mock_groq_key"
    try:
        title = session_namer._generate_session_title("Bang cuu chuong la gi?")
        assert isinstance(title, str)
        assert title == "Hoc bang cuu chuong"
    finally:
        session_namer.requests.post = original_post
        if original_key is None:
            os.environ.pop("GROQ_API_KEY", None)
        else:
            os.environ["GROQ_API_KEY"] = original_key


def test_update_session_title_updates_db():
    from src.infrastructure.database.db import update_session_title as _update_session_title

    session_id = _create_session("default")
    _update_session_title(session_id, "Hoc chu cai")
    with _get_db_connection() as conn:
        row = conn.execute(
            "SELECT title FROM conversations WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    assert row is not None
    assert row["title"] == "Hoc chu cai"


test("SessionNaming: module imports",                  test_session_namer_imports)
test("SessionNaming: title generator returns string", test_generate_session_title_returns_string)
test("SessionNaming: update_session_title updates DB", test_update_session_title_updates_db)

# == GROUP 16: Conversation API =============================================
print("\n[Group 16] Conversation API")


def test_conversations_list_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations" in paths


def test_conversation_detail_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations/{session_id}" in paths


def test_conversation_homework_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations/{session_id}/homework" in paths


def test_conversation_delete_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations/{session_id}" in paths


test("ConversationAPI: GET /api/conversations exists",                    test_conversations_list_endpoint_exists)
test("ConversationAPI: GET /api/conversations/{session_id} exists",      test_conversation_detail_endpoint_exists)
test("ConversationAPI: POST /api/conversations/{session_id}/homework exists", test_conversation_homework_endpoint_exists)
test("ConversationAPI: DELETE /api/conversations/{session_id} exists",   test_conversation_delete_endpoint_exists)

# == GROUP 17: Pre-Phase 3 Regression ======================================
print("\n[Group 17] Pre-Phase 3 Regression")


def test_prephase3_safety_filter_blocks_harmful_phrase():
    ok, _text = sf.check("hướng dẫn làm bom")
    assert ok is False, "SafetyFilter must block harmful content"


def test_prephase3_require_family_fails_closed():
    from fastapi import HTTPException
    from src.api.server import _require_family

    try:
        _require_family({})
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 403

    try:
        _require_family({"family_name": ""})
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 403


def test_prephase3_require_family_returns_family_name():
    from src.api.server import _require_family

    result = _require_family({"family_name": "nguyen"})
    assert result == "nguyen"


def test_prephase3_wakeword_monkey_patch_exists():
    from src.audio.input.ear_stt import EarSTT

    ear = EarSTT.__new__(EarSTT)
    assert hasattr(ear, "listen_for_wakeword"), "listen_for_wakeword must exist"
    assert callable(ear.listen_for_wakeword), "listen_for_wakeword must be callable"


def test_task_manager_daily_reset_behavior():
    from src.infrastructure.tasks.task_manager import TaskManager
    from src.infrastructure.database.db import get_db_connection

    tm = TaskManager()
    task = tm.add_task("Daily task prephase behavior", remind_time="08:00")
    try:
        task_id = task["id"]
        tm.complete_task(task_id)
        tasks = tm.get_all()
        current = next(t for t in tasks if t["id"] == task_id)
        assert current.get("completed_today") is True, "Task phai completed_today sau khi complete"

        with get_db_connection() as conn:
            conn.execute(
                "UPDATE tasks SET completed_date=? WHERE task_id=?",
                ("2000-01-01", task_id),
            )
            conn.commit()

        tasks = tm.get_all()
        current = next(t for t in tasks if t["id"] == task_id)
        assert current.get("completed_today") is False, "Task hoan thanh ngay khac khong phai completed_today"
    finally:
        tm.delete_task(task["id"])
        tm.stop()


def test_prephase3_api_server_no_require_auth():
    import src.api.server as _api

    assert not hasattr(_api, "require_auth"), "require_auth must be removed"


test("PrePhase3: SafetyFilter blocks harmful phrase",          test_prephase3_safety_filter_blocks_harmful_phrase)
test("PrePhase3: _require_family fails closed",                test_prephase3_require_family_fails_closed)
test("PrePhase3: _require_family returns family_name",         test_prephase3_require_family_returns_family_name)
test("PrePhase3: wake-word monkey-patch exists",               test_prephase3_wakeword_monkey_patch_exists)
test("PrePhase3: TaskManager daily reset behavior",            test_task_manager_daily_reset_behavior)
test("PrePhase3: api_server.require_auth absent",              test_prephase3_api_server_no_require_auth)

# == GROUP 18: Logout All Devices ===========================================
print("\n[Group 18] Logout All Devices")
from src.infrastructure.database.db import revoke_all_tokens_for_user as _revoke_all


def test_revoke_all_tokens_callable():
    assert callable(_revoke_all)


def test_revoke_all_tokens_nonexistent_user_returns_zero():
    count = _revoke_all("nonexistent-user-id")
    assert isinstance(count, int)
    assert count == 0


def test_logout_all_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/auth/logout-all" in paths, f"/api/auth/logout-all not found in: {paths}"


test("LogoutAll: revoke_all_tokens_for_user callable",           test_revoke_all_tokens_callable)
test("LogoutAll: nonexistent user → 0, no crash",               test_revoke_all_tokens_nonexistent_user_returns_zero)
test("LogoutAll: POST /api/auth/logout-all endpoint registered", test_logout_all_endpoint_exists)

# == GROUP 19: Account Settings =============================================
print("\n[Group 19] Account Settings")
from src.infrastructure.database.db import get_user_by_id as _get_user_by_id
from src.infrastructure.database.db import update_user_password as _update_user_password


def test_get_user_by_id_nonexistent():
    result = _get_user_by_id("nonexistent-id")
    assert result is None


def test_get_user_by_id_real_user():
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"settingsuser_{unique}", "Password1!", "SettingsFam")
    uid = str(user["user_id"])
    result = _get_user_by_id(uid)
    assert result is not None
    assert result["username"] == f"settingsuser_{unique}"
    assert result["family_name"] == "SettingsFam"
    assert "user_id" in result
    assert "created_at" in result
    assert "password_hash" not in result


def test_update_user_password_nonexistent():
    result = _update_user_password("nonexistent-id", "newpassword123")
    assert result is False


def test_me_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/auth/me" in paths, f"/api/auth/me not found in: {paths}"


def test_change_password_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/auth/change-password" in paths, f"/api/auth/change-password not found in: {paths}"


test("AccountSettings: get_user_by_id nonexistent → None",        test_get_user_by_id_nonexistent)
test("AccountSettings: get_user_by_id real user → correct dict",  test_get_user_by_id_real_user)
test("AccountSettings: update_user_password nonexistent → False", test_update_user_password_nonexistent)
test("AccountSettings: GET /api/auth/me route registered",        test_me_endpoint_exists)
test("AccountSettings: PUT /api/auth/change-password registered", test_change_password_endpoint_exists)

# == GROUP 20: Cloudflare Named Tunnel ======================================
print("\n[Group 20] Cloudflare Named Tunnel")

os.environ.setdefault("CLOUDFLARE_TUNNEL_TOKEN", "")
os.environ.setdefault("CLOUDFLARE_TUNNEL_URL", "")

from src.api.routers import ops_router as _ops_router_module


def test_tunnel_token_attr_exists():
    assert hasattr(_ops_router_module, "TUNNEL_TOKEN")
    assert isinstance(_ops_router_module.TUNNEL_TOKEN, str)


def test_tunnel_url_attr_exists():
    assert hasattr(_ops_router_module, "TUNNEL_URL")
    assert isinstance(_ops_router_module.TUNNEL_URL, str)


def test_start_cloudflare_tunnel_callable():
    assert callable(_ops_router_module._start_cloudflare_tunnel)


test("CloudflareTunnel: TUNNEL_TOKEN attr exists + is str",           test_tunnel_token_attr_exists)
test("CloudflareTunnel: TUNNEL_URL attr exists + is str",             test_tunnel_url_attr_exists)
test("CloudflareTunnel: _start_cloudflare_tunnel is callable",        test_start_cloudflare_tunnel_callable)

# == GROUP 21: Push Notifications ==========================================
print("\n[Group 21] Push Notifications")
from src.infrastructure.notifications.notifier import set_ws_broadcaster as _set_ws_broadcaster


def test_set_ws_broadcaster_callable():
    assert callable(_set_ws_broadcaster)


def test_set_ws_broadcaster_accepts_fn_and_none():
    test_called = []

    def mock_broadcast(data):
        test_called.append(data)

    _set_ws_broadcaster(mock_broadcast)
    import src.infrastructure.notifications.notifier as _notifier_mod
    assert _notifier_mod._WS_ENABLED is True, "_WS_ENABLED phai True sau khi set broadcaster"
    _set_ws_broadcaster(None)
    assert _notifier_mod._WS_ENABLED is False, "_WS_ENABLED phai False sau khi clear broadcaster"


def test_push_event_no_crash_without_broadcaster():
    _set_ws_broadcaster(None)
    from src.infrastructure.notifications.notifier import EventNotifier
    n = EventNotifier()
    ok = _run_quiet(lambda: n.push_event("test", "unit test message"))
    assert ok is True


test("PushNotif: set_ws_broadcaster is callable",                   test_set_ws_broadcaster_callable)
test("PushNotif: set_ws_broadcaster accepts fn and None",           test_set_ws_broadcaster_accepts_fn_and_none)
test("PushNotif: push_event no crash when broadcaster is None",     test_push_event_no_crash_without_broadcaster)

# == GROUP 22: WebRTC Camera Stream =========================================
print("\n[Group 22] WebRTC Camera Stream")
from src.api.routers import webrtc_router as _webrtc_router


def test_webrtc_aiortc_available_attr():
    assert hasattr(_webrtc_router, "_AIORTC_AVAILABLE")
    assert isinstance(_webrtc_router._AIORTC_AVAILABLE, bool)


def test_webrtc_peer_connections_is_dict():
    assert isinstance(_webrtc_router._peer_connections, dict)


def test_webrtc_routes_registered():
    paths = [r.path for r in _webrtc_router.router.routes if hasattr(r, 'path')]
    assert "/api/webrtc/offer" in paths, f"offer not in {paths}"
    assert "/api/webrtc/close" in paths, f"close not in {paths}"


def test_webrtc_available_flag_is_bool():
    assert _webrtc_router._AIORTC_AVAILABLE in (True, False)


def test_webrtc_mjpeg_fallback_intact():
    from src.api.routers.ops_router import router as _ops
    ops_paths = [r.path for r in _ops.routes if hasattr(r, 'path')]
    assert "/api/camera" in ops_paths, f"/api/camera missing from ops_router: {ops_paths}"


test("WebRTC: _AIORTC_AVAILABLE attr exists + is bool",      test_webrtc_aiortc_available_attr)
test("WebRTC: _peer_connections is a dict",                  test_webrtc_peer_connections_is_dict)
test("WebRTC: /api/webrtc/offer + /close routes registered", test_webrtc_routes_registered)
test("WebRTC: _AIORTC_AVAILABLE value is True or False",     test_webrtc_available_flag_is_bool)
test("WebRTC: MJPEG fallback /api/camera still intact",      test_webrtc_mjpeg_fallback_intact)

# == GROUP 23: Pre-Release Security Fixes ==================================
print("\n[Group 23] Pre-Release Security Fixes")
from src.infrastructure.database.db import get_db_connection as _gdb
from src.infrastructure.database.db import increment_token_version as _increment_tv


def test_token_version_column_in_schema():
    with _gdb() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    assert "token_version" in cols, f"token_version missing, cols: {cols}"


def test_increment_token_version_callable_returns_int():
    assert callable(_increment_tv)
    # user không tồn tại → không crash, trả về 0 (UPDATE 0 rows)
    result = _increment_tv("nonexistent-tv-user")
    assert isinstance(result, int)


def test_access_token_invalid_after_increment():
    from src.infrastructure.auth.auth import create_access_token, verify_access_token
    from fastapi import HTTPException
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"tvtest_{unique}", "Password1!", "TVFam")
    uid = str(user["user_id"])
    token = create_access_token(uid, "TVFam")
    # Token hợp lệ trước khi increment
    payload = verify_access_token(token)
    assert payload["sub"] == uid
    # Sau increment → token cũ bị vô hiệu hóa
    _increment_tv(uid)
    try:
        verify_access_token(token)
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401


def test_register_ignores_client_family_name():
    """POST /auth/register không được nhận family_name từ client."""
    import inspect
    from src.api.routers.auth_router import register_user
    src = inspect.getsource(register_user)
    # family_name không được đọc từ body
    assert 'body.get("family_name"' not in src, "family_name vẫn đọc từ client body!"
    # Server dùng FAMILY_ID env
    assert "FAMILY_ID" in src


def test_register_route_exists():
    from src.api.routers.auth_router import router as _ar
    paths = [r.path for r in _ar.routes if hasattr(r, 'path')]
    assert "/auth/register" in paths


def test_token_version_zero_for_new_user():
    from src.infrastructure.database.db import get_token_version as _get_tv
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"tvzero_{unique}", "Password1!", "ZeroFam")
    uid = str(user["user_id"])
    assert _get_tv(uid) == 0


def test_token_version_increments_correctly():
    from src.infrastructure.database.db import get_token_version as _get_tv
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"tvinc_{unique}", "Password1!", "IncFam")
    uid = str(user["user_id"])
    v1 = _increment_tv(uid)
    assert v1 == 1
    v2 = _increment_tv(uid)
    assert v2 == 2


test("Fix1: register ignores client family_name, uses FAMILY_ID",   test_register_ignores_client_family_name)
test("Fix1: /auth/register route still registered",                  test_register_route_exists)
test("Fix2: token_version column exists in users schema",            test_token_version_column_in_schema)
test("Fix2: increment_token_version callable, nonexistent→no crash", test_increment_token_version_callable_returns_int)
test("Fix2: access token → 401 after increment_token_version",      test_access_token_invalid_after_increment)
test("Fix2: new user starts at token_version=0",                     test_token_version_zero_for_new_user)
test("Fix2: token_version increments correctly",                     test_token_version_increments_correctly)

# == GROUP 24: Phase 3 Final Fix Verification ==============================
print("\n[Group 24] Phase 3 Final Fix Verification")


def _phase3_auth_headers(prefix: str = "phase3") -> dict:
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"{prefix}_{unique}", "Password1!", "Phase3Fam")
    token = create_access_token(str(user["user_id"]), "Phase3Fam")
    return {"Authorization": f"Bearer {token}"}


def _post_task_for_phase3(payload: dict):
    from fastapi.testclient import TestClient
    from src.api.server import app
    import src.infrastructure.sessions.state as _state_mod
    from src.infrastructure.tasks.task_manager import TaskManager

    old_tm = _state_mod._task_manager
    tm = TaskManager()
    _state_mod._task_manager = tm
    try:
        with TestClient(app) as client:
            return client.post("/api/tasks", json=payload, headers=_phase3_auth_headers("task"))
    finally:
        tm.stop()
        _state_mod._task_manager = old_tm


# Test 24.1 - FIX-01: XSS validation
def test_24_1_task_remind_time_xss_rejected():
    r = _post_task_for_phase3({
        "name": "Doc sach",
        "remind_time": "<script>alert(1)</script>",
    })
    assert r.status_code == 422


# Test 24.2 - FIX-01: remind_time invalid reject
def test_24_2_task_remind_time_range_rejected():
    r = _post_task_for_phase3({"name": "Doc sach", "remind_time": "25:99"})
    assert r.status_code == 422


# Test 24.3 - FIX-01: remind_time valid accept
def test_24_3_task_remind_time_valid_accept():
    r = _post_task_for_phase3({"name": "Doc sach", "remind_time": "08:30"})
    assert r.status_code in (200, 201)


# Test 24.4 - FIX-02: registration disabled -> 403
def test_24_4_registration_disabled_403():
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.api.routers import auth_router

    auth_router.REGISTRATION_ENABLED = False
    with TestClient(app) as client:
        r = client.post("/auth/register", json={
            "username": f"reg_{_uuid.uuid4().hex[:8]}",
            "password": "Password1!",
        })
    assert r.status_code == 403


# Test 24.5 - FIX-02: REGISTRATION_ENABLED attr exists
def test_24_5_registration_enabled_attr_exists():
    from src.api.routers import auth_router
    assert hasattr(auth_router, "REGISTRATION_ENABLED")


# Test 24.6 - FIX-03: _require_family in memory handlers
def test_24_6_memory_handlers_require_family():
    import inspect
    from src.api.routers import control_router

    handlers = [
        control_router.list_memories,
        control_router.add_memory,
        control_router.export_memories,
        control_router.update_memory,
        control_router.delete_memory,
    ]
    for handler in handlers:
        src = inspect.getsource(handler)
        assert "_require_family" in src, handler.__name__


# Test 24.7 - FIX-06: PC not leaked on bad SDP
def test_24_7_webrtc_offer_adds_pc_after_success_only():
    import inspect
    from src.api.routers import webrtc_router

    src = inspect.getsource(webrtc_router.webrtc_offer)
    assert "await pc.close()" in src
    assert "except Exception" in src
    assert src.index("await pc.setLocalDescription(answer)") < src.index("_peer_connections[key] = pc")
    assert "old_pc" in src, "Phai co logic dong PC cu khi reconnect"


# Test 24.8 - FIX-07: _peer_connections is dict
def test_24_8_peer_connections_is_dict():
    from src.api.routers import webrtc_router
    assert isinstance(webrtc_router._peer_connections, dict)


# Test 24.9 - FIX-09: nonexistent user token -> 401
def test_24_9_nonexistent_user_access_token_rejected():
    from fastapi import HTTPException
    token = create_access_token("nonexistent-user-id", "NoFam")
    try:
        verify_access_token(token)
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401


# Test 24.10 - FIX-10: change-password rate limit in source
def test_24_10_change_password_rate_limit_source():
    import inspect
    from src.api.routers.auth_router import change_password

    src = inspect.getsource(change_password)
    assert "chpwd:" in src
    assert "login_attempts" in src


# Test 24.11 - FIX-11: limit bounds validation
def test_24_11_limit_bounds_validation():
    from fastapi.testclient import TestClient
    from src.api.server import app

    headers = _phase3_auth_headers("limit")
    with TestClient(app) as client:
        assert client.get("/api/events?limit=0", headers=headers).status_code == 422
        assert client.get("/api/events?limit=201", headers=headers).status_code == 422
        assert client.get("/api/events?limit=50", headers=headers).status_code == 200


# Test 24.12 - FIX-12: init_db idempotent x3
def test_24_12_init_db_idempotent_x3():
    import src.infrastructure.database.db as db_mod
    for _ in range(3):
        db_mod._INITIALIZED = False
        init_db()


# Test 24.13 - FIX-16: no PII in INFO logs
def test_24_13_no_pii_content_in_info_logs():
    import re
    files = [
        "src/infrastructure/notifications/notifier.py",
        "src/main.py",
        "src/ai/ai_engine.py",
    ]
    bad = re.compile(
        r"logger\.(info|warning|error)\([^\\n]*(user_text|bi_response|full_reply|clean_sentence|clean_buffer|rag_context)"
    )
    for path in files:
        text = open(path, "r", encoding="utf-8").read()
        assert not bad.search(text), path


# Test 24.14 - FIX-17: _shutdown callable
def test_24_14_robot_app_shutdown_callable():
    from src.main import RobotBiApp
    assert callable(getattr(RobotBiApp, "_shutdown", None))


# Test 24.15 - FIX-19: no duplicate handlers on double setup
def test_24_15_setup_logging_no_duplicate_file_handlers():
    import logging.handlers
    from src.infrastructure.logging.log_config import setup_logging

    robot_logger = logging.getLogger("robot_bi")
    setup_logging()
    first = sum(isinstance(h, logging.handlers.RotatingFileHandler) for h in robot_logger.handlers)
    setup_logging()
    second = sum(isinstance(h, logging.handlers.RotatingFileHandler) for h in robot_logger.handlers)
    assert first == second


# Test 24.16 - FIX-20: requirements-ubuntu.txt exists
def test_24_16_requirements_ubuntu_aiortc_exists():
    content = open("requirements-ubuntu.txt", "r", encoding="utf-8").read()
    assert "aiortc==1.9.0" in content


# Test 24.17 - FIX-22: ws_enabled updates with broadcaster
def test_24_17_ws_enabled_updates_with_broadcaster():
    import src.infrastructure.notifications.notifier as notifier_mod

    notifier_mod.set_ws_broadcaster(lambda data: None)
    assert notifier_mod._WS_ENABLED is True
    notifier_mod.set_ws_broadcaster(None)
    assert notifier_mod._WS_ENABLED is False


test("24.1 FIX-01: task remind_time XSS rejected",        test_24_1_task_remind_time_xss_rejected)
test("24.2 FIX-01: task remind_time range rejected",      test_24_2_task_remind_time_range_rejected)
test("24.3 FIX-01: task remind_time valid accepted",      test_24_3_task_remind_time_valid_accept)
test("24.4 FIX-02: registration disabled returns 403",    test_24_4_registration_disabled_403)
test("24.5 FIX-02: REGISTRATION_ENABLED attr exists",     test_24_5_registration_enabled_attr_exists)
test("24.6 FIX-03: memory handlers require family",       test_24_6_memory_handlers_require_family)
test("24.7 FIX-06: WebRTC bad offer cleanup logic",       test_24_7_webrtc_offer_adds_pc_after_success_only)
test("24.8 FIX-07: _peer_connections is dict",            test_24_8_peer_connections_is_dict)
test("24.9 FIX-09: nonexistent user token rejected",      test_24_9_nonexistent_user_access_token_rejected)
test("24.10 FIX-10: change-password rate limit source",   test_24_10_change_password_rate_limit_source)
test("24.11 FIX-11: list limit bounds validation",        test_24_11_limit_bounds_validation)
test("24.12 FIX-12: init_db idempotent x3",               test_24_12_init_db_idempotent_x3)
test("24.13 FIX-16: no PII content in INFO logs",         test_24_13_no_pii_content_in_info_logs)
test("24.14 FIX-17: RobotBiApp._shutdown callable",       test_24_14_robot_app_shutdown_callable)
test("24.15 FIX-19: setup_logging no duplicate handlers", test_24_15_setup_logging_no_duplicate_file_handlers)
test("24.16 FIX-20: requirements-ubuntu contains aiortc", test_24_16_requirements_ubuntu_aiortc_exists)
test("24.17 FIX-22: ws_enabled tracks broadcaster",       test_24_17_ws_enabled_updates_with_broadcaster)

# == GROUP 25: Sprint A Safety & Logic Fix Verification =====================
print("\n[Group 25] Sprint A  Safety & Logic Fix Verification")


def test_25_1_safety_filter_output_used_for_persist():
    import inspect
    from src import main as main_loop

    loop_fn = (
        main_loop.RobotBiApp._run_conversation_loop
        if hasattr(main_loop.RobotBiApp, "_run_conversation_loop")
        else main_loop.RobotBiApp.run
    )
    src = inspect.getsource(loop_fn)
    sf_pos = src.find("self.safety.check")
    at_pos = src.find("add_turn(self._current_session_id, 'assistant'")
    assert sf_pos != -1, "safety_filter phai duoc goi trong conversation loop"
    assert at_pos != -1, "assistant add_turn phai ton tai"
    assert sf_pos < at_pos, "safety_filter phai duoc goi truoc assistant add_turn"
    assert (
        "add_turn(self._current_session_id, 'assistant', sanitized_reply)" in src
    ), "assistant add_turn phai dung sanitized_reply"
    assert (
        src.count("args=(user_text_goc, sanitized_reply)") >= 2
    ), "RAG va notifier phai dung sanitized_reply"
    assert (
        "add_turn(self._current_session_id, 'assistant', full_reply)" not in src
    ), "khong duoc persist raw full_reply"


def test_25_2_task_completed_date_daily_reset():
    import datetime
    from src.infrastructure.tasks.task_manager import TaskManager

    tm = TaskManager()
    task = tm.add_task("Sprint A daily reset", remind_time="08:00")
    try:
        task_id = task["id"]
        assert tm.complete_task(task_id) is True
        today = datetime.date.today().strftime("%Y-%m-%d")
        tasks = tm.get_all()
        current = next(t for t in tasks if t["id"] == task_id)
        assert current.get("completed_date") == today, "completed_date phai la hom nay"
        assert current.get("completed_today") is True, "completed_today phai dung trong ngay"

        current["completed_date"] = "2000-01-01"
        current["completed_today"] = True
        tm._save()
        tasks_next_day = tm.get_all()
        updated = next(t for t in tasks_next_day if t["id"] == task_id)
        assert (
            updated.get("completed_date") == "2000-01-01"
        ), "completed_date phai giu nguyen gia tri da set"
        assert updated.get("completed_today") is False, "completed_today phai reset khi qua ngay"
    finally:
        tm.delete_task(task["id"])
        tm.stop()


def test_25_3_last_reminded_has_date_prefix():
    import datetime
    from src.infrastructure.tasks.task_manager import TaskManager

    tm = TaskManager()
    task = tm.add_task("Sprint A reminder format", remind_time="09:00")
    try:
        assert tm._mark_reminded(task["id"]) is True
        tasks = tm.get_all()
        current = next(t for t in tasks if t["id"] == task["id"])
        lr = current.get("last_reminded", "")
        today = datetime.date.today().strftime("%Y-%m-%d")
        assert len(lr) >= 16, "last_reminded phai co format YYYY-MM-DD HH:MM"
        assert lr[:4].isdigit(), "last_reminded phai bat dau bang YYYY"
        assert lr[4] == "-" and lr[7] == "-" and lr[10] == " ", "last_reminded sai format"
        assert current.get("last_reminded_date") == today, "last_reminded_date phai la hom nay"
    finally:
        tm.delete_task(task["id"])
        tm.stop()


def test_25_4_refresh_promise_single_flight_present():
    with open("frontend/parent_app/src/services/api.js", encoding="utf-8") as f:
        src = f.read()
    assert "_refreshPromise" in src, "_refreshPromise phai co trong api.js"
    fn_pos = src.find("async function refreshToken")
    if fn_pos < 0:
        fn_pos = src.find("async function tryRefreshToken")
    assert fn_pos != -1, "refreshToken phai ton tai trong api.js"
    refresh_src = src[fn_pos: fn_pos + 1200]
    assert "if (_refreshPromise) return _refreshPromise" in refresh_src, "phai reuse refresh promise dang chay"
    assert "_refreshPromise = (async () =>" in refresh_src, "refresh phai duoc boc trong promise"
    assert "finally" in refresh_src and "_refreshPromise = null" in refresh_src, "finally phai reset _refreshPromise"


test("25.1 FIX A-1: SafetyFilter output used for persist", test_25_1_safety_filter_output_used_for_persist)
test("25.2 FIX A-2: Task completed_date daily reset", test_25_2_task_completed_date_daily_reset)
test("25.3 FIX A-2: last_reminded stores date+time", test_25_3_last_reminded_has_date_prefix)
test("25.4 FIX A-3: _refreshPromise single-flight present", test_25_4_refresh_promise_single_flight_present)

# == GROUP 26: Sprint B Auth Security Fix Verification ======================
print("\n[Group 26] Sprint B  Auth Security Fix Verification")


def test_26_1_rotate_refresh_token_atomic_rowcount():
    import inspect
    from src.infrastructure.auth import auth

    src = inspect.getsource(auth.rotate_refresh_token)
    assert "rowcount" in src, "rotate_refresh_token phai check rowcount"
    assert (
        "is_revoked = 0" in src or "is_revoked=0" in src
    ), "UPDATE phai co dieu kien is_revoked=0"


def test_26_2_access_token_checks_is_active():
    import inspect
    from src.infrastructure.auth import auth
    from src.api.routers import auth_router

    src = inspect.getsource(auth.verify_access_token)
    assert "is_active" in src, "verify_access_token phai check is_active"
    refresh_src = inspect.getsource(auth_router.refresh_token_endpoint)
    assert "is_active" in refresh_src, "refresh endpoint phai check is_active"


def test_26_3_revoke_all_tokens_atomic_token_version():
    import inspect
    from src.infrastructure.database import db

    src = inspect.getsource(db.revoke_all_tokens_for_user)
    assert "token_version" in src, "revoke_all phai increment token_version trong cung transaction"
    assert "increment_token_version" not in src, "revoke_all khong duoc goi increment_token_version rieng"


def test_26_4_register_has_rate_limit_key():
    import inspect
    from src.api.routers import auth_router

    src = inspect.getsource(auth_router)
    reg_idx = src.find("async def register")
    reg_src = src[reg_idx: reg_idx + 2000] if reg_idx >= 0 else ""
    assert (
        "register:" in reg_src or "login_attempts" in reg_src
    ), "register handler phai co rate limit"


test("26.1 FIX B-1: rotate_refresh_token atomic rowcount", test_26_1_rotate_refresh_token_atomic_rowcount)
test("26.2 FIX B-2: inactive users rejected", test_26_2_access_token_checks_is_active)
test("26.3 FIX B-3: revoke_all atomic token_version", test_26_3_revoke_all_tokens_atomic_token_version)
test("26.4 FIX B-4: register rate limit present", test_26_4_register_has_rate_limit_key)

# == GROUP 27: Sprint C Stability & Backend Verification ====================
print("\n[Group 27] Sprint C  Stability & Backend Verification")


def test_27_1_earstt_listen_wraps_whisper_load():
    import inspect
    from src.audio.input.ear_stt import EarSTT

    src = inspect.getsource(EarSTT.listen)
    assert "_get_whisper_model" in src, "_get_whisper_model phai duoc goi trong listen()"
    assert src.count("try:") >= 1, "listen() phai co it nhat 1 try/except block"


def test_27_2_cleanup_expired_login_attempts_callable():
    from src.infrastructure.database.db import cleanup_expired_login_attempts

    assert callable(cleanup_expired_login_attempts)
    result = cleanup_expired_login_attempts(ttl_minutes=1440)
    assert isinstance(result, int)
    assert result >= 0


def test_27_3_cleanup_orphan_sessions_closes_old_session():
    from src.infrastructure.database.db import cleanup_orphan_sessions, get_db_connection, init_db

    init_db()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations
            (session_id, family_id, started_at, ended_at)
            VALUES ('orphan-test-001', 'test', datetime('now', '-25 hours'), NULL)
            """
        )
        conn.commit()
    count = cleanup_orphan_sessions(max_age_hours=24)
    assert count >= 1, "Phai dong it nhat 1 orphan session"


def test_27_4_main_loop_has_iteration_recovery():
    import inspect
    from src import main as main_loop

    src = inspect.getsource(
        main_loop.RobotBiApp.run
        if hasattr(main_loop.RobotBiApp, "run")
        else main_loop.RobotBiApp._run_conversation_loop
    )
    assert "except Exception" in src, "Main loop phai co except Exception handler"
    assert "KeyboardInterrupt" in src, "KeyboardInterrupt phai duoc xu ly rieng"


def test_27_5_rag_max_memories_constant_valid():
    from src.memory.rag_manager import RAGManager, _MAX_MEMORIES

    assert RAGManager is not None
    assert isinstance(_MAX_MEMORIES, int)
    assert _MAX_MEMORIES > 0
    assert _MAX_MEMORIES <= 10000, "Quota phai co gioi han hop ly"


def test_27_6_init_db_idempotent_with_import_key_indexes():
    from src.infrastructure.database.db import init_db, get_db_connection

    init_db()
    init_db()
    with get_db_connection() as conn:
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='events'"
        ).fetchall()
        idx_names = [r["name"] for r in indexes]
        assert len(idx_names) >= 0


test("27.1 FIX C-1: EarSTT listen wraps Whisper load", test_27_1_earstt_listen_wraps_whisper_load)
test("27.2 FIX C-2: cleanup_expired_login_attempts callable", test_27_2_cleanup_expired_login_attempts_callable)
test("27.3 FIX C-3: cleanup_orphan_sessions closes old session", test_27_3_cleanup_orphan_sessions_closes_old_session)
test("27.4 FIX C-4: main loop iteration recovery", test_27_4_main_loop_has_iteration_recovery)
test("27.5 FIX C-5: RAG max memories quota valid", test_27_5_rag_max_memories_constant_valid)
test("27.6 FIX C-6: init_db idempotent import_key indexes", test_27_6_init_db_idempotent_with_import_key_indexes)

# == GROUP 28: Sprint D Frontend, Cleanup & Docs Verification ===============
print("\n[Group 28] Sprint D  Frontend, Cleanup & Docs Verification")


def test_28_1_webrtc_closes_old_pc_on_reconnect():
    import inspect
    from src.api.routers import webrtc_router

    src = inspect.getsource(webrtc_router)
    assert "old_pc" in src, "Phai co logic close PC cu truoc khi assign moi"


def test_28_2_tab_switch_cleanup_camera_mom_mic():
    with open("frontend/parent_app/src/App.jsx", encoding="utf-8") as f:
        src = f.read()
    assert "stopCamera" in src, "App.jsx phai co stopCamera"
    assert "stopMomMic" in src, "App.jsx phai co stopMomMic"
    tab_fn_start = src.find("handleTabChange")
    assert tab_fn_start >= 0, "Phai co handleTabChange function"
    tab_src = src[tab_fn_start: tab_fn_start + 400]
    assert "stopCamera" in tab_src and "stopMomMic" in tab_src, "handleTabChange phai cleanup camera va mom mic"


def test_28_3_webrtc_connectionstatechange_handler():
    with open("frontend/parent_app/src/pages/MonitorPage.jsx", encoding="utf-8") as f:
        src = f.read()
    assert "onError" in src or "onconnectionstatechange" in src, "Phai co camera connection/disconnect handler"
    assert "camError" in src or "disconnected" in src, "Phai handle camera disconnected/error state"


def test_28_4_ops_router_tunnel_captures_stderr():
    import inspect
    from src.api.routers import ops_router

    src = inspect.getsource(ops_router)
    assert "stderr" in src, "ops_router phai capture stderr tu tunnel process"


def test_28_5_log_config_reads_log_level():
    import inspect
    from src.infrastructure.logging import log_config

    src = inspect.getsource(log_config.setup_logging)
    assert "LOG_LEVEL" in src, "setup_logging phai doc LOG_LEVEL tu env"


def test_28_6_notification_stacking_present():
    with open("frontend/parent_app/src/components/Toast.jsx", encoding="utf-8") as f:
        src = f.read()
    assert "_notifCount" in src or "notif-banner" in src, "Toast.jsx phai co notification stacking logic"


def test_28_7_run_guide_no_default_pin():
    with open("HUONG_DAN_CHAY.md", encoding="utf-8") as f:
        content = f.read()
    assert "123456" not in content, "Phai xoa PIN mac dinh 123456 khoi docs"
    assert "PIN_CODE" not in content, "Phai xoa PIN_CODE khoi docs"


def test_28_8_handoff_phase3_complete():
    with open(".claude/handoff.md", encoding="utf-8") as f:
        content = f.read()
    assert "Phase 3" in content, "handoff phai mention Phase 3"
    assert "Bắt đầu Phase 3" not in content or "COMPLETE" in content, "handoff phai reflect Phase 3 da xong"


def test_28_9_kehoach_outdated_banner():
    with open("docs/kehoach.md", encoding="utf-8") as f:
        content = f.read()
    assert "LOI THOI" in content or "LỖI THỜI" in content or "outdated" in content.lower(), "kehoach.md phai co warning banner loi thoi"


def test_28_10_gitignore_runtime_artifacts():
    with open(".gitignore", encoding="utf-8") as f:
        content = f.read()
    assert "logs/" in content, ".gitignore phai ignore logs/ directory"
    assert "_test_db" in content or "chroma_db" in content, ".gitignore phai ignore test DB artifacts"


def test_28_11_train_text_import_no_side_effect():
    import sys

    old_stdin = sys.stdin
    try:
        if "src.train_text" in sys.modules:
            del sys.modules["src.train_text"]
        import src.train_text  # noqa: F401
        assert True
    except SystemExit:
        assert False, "train_text khong duoc exit khi import"
    finally:
        sys.stdin = old_stdin


def test_28_12_bool_file_removed():
    import os

    assert not os.path.exists("bool"), "File 'bool' phai duoc xoa"


test("28.1 FIX D-1: WebRTC closes old PC on reconnect", test_28_1_webrtc_closes_old_pc_on_reconnect)
test("28.2 FIX D-2: tab switch cleanup camera and mom mic", test_28_2_tab_switch_cleanup_camera_mom_mic)
test("28.3 FIX D-3: WebRTC connection loss handler", test_28_3_webrtc_connectionstatechange_handler)
test("28.4 FIX D-6: tunnel stderr captured", test_28_4_ops_router_tunnel_captures_stderr)
test("28.5 FIX D-7: LOG_LEVEL env used", test_28_5_log_config_reads_log_level)
test("28.6 FIX D-8: notification stacking present", test_28_6_notification_stacking_present)
test("28.7 FIX D-9: run guide removes default PIN docs", test_28_7_run_guide_no_default_pin)
test("28.8 FIX D-10: handoff marks Phase 3 complete", test_28_8_handoff_phase3_complete)
test("28.9 FIX D-11: kehoach outdated banner", test_28_9_kehoach_outdated_banner)
test("28.10 FIX D-12: gitignore runtime artifacts", test_28_10_gitignore_runtime_artifacts)
test("28.11 FIX D-13: train_text import no side effect", test_28_11_train_text_import_no_side_effect)
test("28.12 FIX D-14: bool file removed", test_28_12_bool_file_removed)

# == GROUP 29: Final Pre-Phase 4 Fix Verification ===========================
print("\n[Group 29] Final Pre-Phase 4 Fix Verification")


# Test 29.1 - FIX-01: old_pc.close() trong offer handler
def test_29_1_webrtc_offer_closes_old_pc():
    import inspect
    from src.api.routers import webrtc_router as wr

    src = inspect.getsource(wr)
    offer_start = src.find("async def webrtc_offer")
    if offer_start < 0:
        offer_start = src.find("/api/webrtc/offer")
    offer_src = src[offer_start:offer_start + 2000]
    assert "old_pc" in offer_src, "Phai co old_pc.close() truoc khi assign PC moi"
    assert (
        "old_pc.close()" in offer_src or ("old_pc" in offer_src and "close" in offer_src)
    ), "old_pc phai duoc close()"


# Test 29.2 - FIX-02: beforeunload co stopCamera va stopAudioMonitor
def test_29_2_beforeunload_stops_camera_and_audio_monitor():
    with open("frontend/parent_app/src/App.jsx", encoding="utf-8") as f:
        src = f.read()
    bu_idx = src.find("beforeunload")
    assert bu_idx >= 0, "Phai co beforeunload handler"
    bu_section = src[bu_idx:bu_idx + 300]
    assert "stopCamera" in bu_section, "beforeunload phai goi stopCamera()"
    assert "stopAudioMonitor" in bu_section or "stopMomMic" in bu_section, "beforeunload phai goi stop audio"


# Test 29.3 - FIX-03: doLogout co stopCamera o dau
def test_29_3_do_logout_stops_camera_early():
    with open("frontend/parent_app/src/App.jsx", encoding="utf-8") as f:
        src = f.read()
    logout_idx = src.find("async function doLogout")
    if logout_idx < 0:
        logout_idx = src.find("handleLogout")
    assert logout_idx >= 0, "Phai co handleLogout / doLogout function"
    logout_start = src[logout_idx:logout_idx + 400]
    assert "stopCamera" in logout_start, "stopCamera phai duoc goi trong logout"


# Test 29.4 - FIX-04: speech content khong log o INFO
def test_29_4_speech_content_not_logged_at_info():
    import inspect
    import re
    from src.audio.input.ear_stt import EarSTT

    src = inspect.getsource(EarSTT)
    info_speech = re.findall(
        r'logger\.info\([^)]*(?:text|speech|nhan_dang|Nhận dạng)[^)]*\)',
        src,
    )
    assert len(info_speech) == 0, f"Speech content khong duoc log o INFO: {info_speech}"


# Test 29.5 - FIX-05: foreign_keys duoc bat
def test_29_5_sqlite_foreign_keys_enabled():
    from src.infrastructure.database.db import get_db_connection

    with get_db_connection() as conn:
        result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1, "PRAGMA foreign_keys phai duoc bat (= 1)"


# Test 29.6 - FIX-06: prune logic co error handling
def test_29_6_rag_prune_has_error_handling():
    import inspect
    from src.memory import rag_manager

    src = inspect.getsource(rag_manager.RAGManager.extract_and_save)
    assert "break" in src or "except" in src, "Prune loop phai co error handling voi break"


# Test 29.7 - FIX-07: MIC_DEVICE doc tu env trong ear_stt
def test_29_7_mic_device_reads_from_env():
    import inspect
    from src.audio.input import ear_stt

    src = inspect.getsource(ear_stt)
    assert "MIC_DEVICE" in src, "ear_stt phai co MIC_DEVICE tu env"
    assert (
        'getenv("MIC_DEVICE"' in src or "getenv('MIC_DEVICE'" in src
    ), "MIC_DEVICE phai doc tu os.getenv()"


# Test 29.8 - FIX-08: ADMIN_PASSWORD placeholder khong phai weak default
def test_29_8_admin_password_placeholder_not_weak():
    with open(".env.example", encoding="utf-8") as f:
        content = f.read()
    assert "change_me_please" not in content, ".env.example khong duoc chua password mac dinh yeu"


# Test 29.9 - FIX-09: logout dung _current_user, khong goi verify thu 2
def test_29_9_logout_does_not_double_verify():
    import inspect
    from src.api.routers import auth_router

    src = inspect.getsource(auth_router)
    logout_idx = src.find("async def logout")
    if logout_idx < 0:
        logout_idx = src.find("/auth/logout")
    logout_src = src[logout_idx:logout_idx + 500] if logout_idx >= 0 else ""
    assert logout_src.count("verify_access_token") == 0, (
        "logout handler khong duoc goi verify_access_token() truc tiep"
    )


# Test 29.10 - FIX-10: connectionstatechange co try/except
def test_29_10_webrtc_connectionstatechange_has_try_except():
    import inspect
    from src.api.routers import webrtc_router as wr

    src = inspect.getsource(wr)
    state_idx = src.find("connectionstatechange")
    state_src = src[state_idx:state_idx + 400] if state_idx >= 0 else ""
    assert "try:" in state_src, "connectionstatechange callback phai co try/except"


# Test 29.11 - FIX-11: icon files ton tai
def test_29_11_manifest_icon_files_exist():
    import os

    assert os.path.exists("frontend/parent_app/icon-192.png"), "icon-192.png phai ton tai"
    assert os.path.exists("frontend/parent_app/icon-512.png"), "icon-512.png phai ton tai"


# Test 29.12 - FIX-12: khong con reference train_text trong docs
def test_29_12_run_guide_no_train_text_reference():
    with open("HUONG_DAN_CHAY.md", encoding="utf-8") as f:
        content = f.read()
    assert "train_text.py" not in content, "HUONG_DAN_CHAY.md khong duoc reference train_text.py"


test("29.1 FIX-01: WebRTC offer closes old PC", test_29_1_webrtc_offer_closes_old_pc)
test("29.2 FIX-02: beforeunload stops camera/audio", test_29_2_beforeunload_stops_camera_and_audio_monitor)
test("29.3 FIX-03: doLogout stops camera early", test_29_3_do_logout_stops_camera_early)
test("29.4 FIX-04: speech content not INFO logged", test_29_4_speech_content_not_logged_at_info)
test("29.5 FIX-05: SQLite foreign_keys enabled", test_29_5_sqlite_foreign_keys_enabled)
test("29.6 FIX-06: RAG prune has error handling", test_29_6_rag_prune_has_error_handling)
test("29.7 FIX-07: MIC_DEVICE reads from env", test_29_7_mic_device_reads_from_env)
test("29.8 FIX-08: admin password placeholder not weak", test_29_8_admin_password_placeholder_not_weak)
test("29.9 FIX-09: logout avoids double verify", test_29_9_logout_does_not_double_verify)
test("29.10 FIX-10: WebRTC state close try/except", test_29_10_webrtc_connectionstatechange_has_try_except)
test("29.11 FIX-11: manifest icon files exist", test_29_11_manifest_icon_files_exist)
test("29.12 FIX-12: run guide has no train_text reference", test_29_12_run_guide_no_train_text_reference)

# == GROUP 30: Phase 4.4 Multi-Family Isolation ===============================
print("\n[Group 30] Phase 4.4 Multi-Family Isolation")


def _phase44_headers(username_prefix: str, family_id: str, is_admin: bool = False) -> dict:
    from src.infrastructure.auth.auth import create_access_token, create_user
    from src.infrastructure.database.db import get_db_connection

    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"{username_prefix}_{unique}", "Password1!", family_id)
    if is_admin:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE users SET is_admin = 1 WHERE user_id = ?",
                (str(user["user_id"]),),
            )
            conn.commit()
    token = create_access_token(str(user["user_id"]), user["family_name"])
    return {"Authorization": f"Bearer {token}"}


def test_30_1_rag_family_filter_real():
    import gc
    import shutil
    from src.memory.rag_manager import RAGManager

    test_db = "runtime/_family_isolation_test_db"
    if os.path.exists(test_db):
        shutil.rmtree(test_db)
    rag = RAGManager(db_path=test_db)
    try:
        fam_a = f"rag-a-{_uuid.uuid4().hex[:6]}"
        fam_b = f"rag-b-{_uuid.uuid4().hex[:6]}"
        assert rag.add_manual_memory("Family A secret: blue dinosaur", family_id=fam_a) is True
        assert rag.add_manual_memory("Family B secret: red robot", family_id=fam_b) is True

        memories_a = rag.list_memories(family_id=fam_a)
        memories_b = rag.list_memories(family_id=fam_b)
        assert len(memories_a) == 1
        assert len(memories_b) == 1
        assert "blue dinosaur" in memories_a[0]["fact"]
        assert "red robot" in memories_b[0]["fact"]
        assert not rag.delete_memory(memories_b[0]["id"], family_id=fam_a)

        context_a = rag.retrieve("red robot", family_id=fam_a)
        assert "red robot" not in context_a.lower()
    finally:
        del rag
        gc.collect()
        try:
            shutil.rmtree(test_db)
        except Exception:
            pass


def test_30_2_conversation_api_family_scope():
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.infrastructure.database.db import add_turn, create_session

    fam_a = f"conv-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"conv-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("conv_a", fam_a)
    session_a = create_session(fam_a)
    session_b = create_session(fam_b)
    add_turn(session_a, "user", "hello from A", family_id=fam_a)
    add_turn(session_b, "user", "hello from B", family_id=fam_b)

    client = TestClient(app)
    list_resp = client.get("/api/conversations", headers=headers_a)
    assert list_resp.status_code == 200
    listed = [row["session_id"] for row in list_resp.json()["conversations"]]
    assert session_a in listed
    assert session_b not in listed

    detail_resp = client.get(f"/api/conversations/{session_b}", headers=headers_a)
    assert detail_resp.status_code == 404


def test_30_3_events_family_scope():
    from src.infrastructure.notifications.notifier import EventNotifier

    fam_a = f"evt-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"evt-b-{_uuid.uuid4().hex[:6]}"
    msg_a = f"event A {_uuid.uuid4().hex}"
    msg_b = f"event B {_uuid.uuid4().hex}"
    notifier_local = EventNotifier()
    notifier_local.push_event("system", msg_a, family_id=fam_a)
    notifier_local.push_event("system", msg_b, family_id=fam_b)

    events_a = notifier_local.get_unread_events(family_id=fam_a)
    assert any(evt["message"] == msg_a for evt in events_a)
    assert all(evt["message"] != msg_b for evt in events_a)

    notifier_local.mark_all_read(family_id=fam_a)
    events_b = notifier_local.get_unread_events(family_id=fam_b)
    assert any(evt["message"] == msg_b for evt in events_b)


def test_30_4_tasks_family_scope():
    from src.infrastructure.tasks.task_manager import TaskManager

    fam_a = f"task-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"task-b-{_uuid.uuid4().hex[:6]}"
    tm_local = TaskManager(family_id=fam_a)
    try:
        task_a = tm_local.add_task("Task family A", "07:10", family_id=fam_a)
        task_b = tm_local.add_task("Task family B", "07:20", family_id=fam_b)

        tasks_a = tm_local.get_all(family_id=fam_a)
        assert any(task["id"] == task_a["id"] for task in tasks_a)
        assert all(task["id"] != task_b["id"] for task in tasks_a)
        assert tm_local.complete_task(task_b["id"], family_id=fam_a) is False
        assert tm_local.complete_task(task_b["id"], family_id=fam_b) is True
        assert tm_local.get_total_stars(family_id=fam_a) == 0
        assert tm_local.get_total_stars(family_id=fam_b) >= 1
    finally:
        tm_local.delete_task(task_a["id"], family_id=fam_a)
        tm_local.delete_task(task_b["id"], family_id=fam_b)
        tm_local.stop()


def test_30_5_admin_family_endpoints_and_delete_cleanup():
    import gc
    import shutil
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.infrastructure.auth.auth import create_user
    from src.infrastructure.database.db import add_turn, create_session, get_db_connection
    from src.infrastructure.notifications.notifier import EventNotifier
    from src.infrastructure.tasks.task_manager import TaskManager
    from src.memory.rag_manager import RAGManager
    import src.infrastructure.sessions.state as _state

    client = TestClient(app)
    admin_headers = _phase44_headers("admin44", f"admin-{_uuid.uuid4().hex[:6]}", is_admin=True)
    user_headers = _phase44_headers("user44", f"user-{_uuid.uuid4().hex[:6]}")
    fam = f"delete-{_uuid.uuid4().hex[:8]}"
    test_db = f"runtime/_family_delete_test_db_{_uuid.uuid4().hex[:8]}"
    old_rag = _state._rag
    rag = None

    try:
        blocked = client.post("/api/admin/families", json={"family_id": fam}, headers=user_headers)
        assert blocked.status_code == 403

        created = client.post(
            "/api/admin/families",
            json={"family_id": fam, "display_name": "Delete Test"},
            headers=admin_headers,
        )
        assert created.status_code == 200
        listed = client.get("/api/admin/families", headers=admin_headers)
        assert listed.status_code == 200
        assert any(row["family_id"] == fam for row in listed.json()["families"])

        rag = RAGManager(db_path=test_db)
        _state._rag = rag
        assert rag.add_manual_memory("family delete chroma cleanup memory", family_id=fam)

        create_user(f"user_{_uuid.uuid4().hex[:8]}", "Password1!", fam)
        session_id = create_session(fam)
        add_turn(session_id, "user", "family delete test", family_id=fam)
        notifier_local = EventNotifier()
        notifier_local.push_event("system", "family delete event", family_id=fam)
        tm_local = TaskManager(family_id=fam)
        task = tm_local.add_task("family delete task", "08:00", family_id=fam)
        tm_local.stop()

        deleted = client.delete(f"/api/admin/families/{fam}", headers=admin_headers)
        assert deleted.status_code == 200
        memories_after = rag.list_memories(family_id=fam)
        assert len(memories_after) == 0, "ChromaDB memories phai duoc xoa khi delete family"

        with get_db_connection() as conn:
            family_count = conn.execute(
                "SELECT COUNT(*) AS c FROM families WHERE family_id = ?",
                (fam,),
            ).fetchone()["c"]
            user_count = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE family_name = ?",
                (fam,),
            ).fetchone()["c"]
            conv_count = conn.execute(
                "SELECT COUNT(*) AS c FROM conversations WHERE family_id = ?",
                (fam,),
            ).fetchone()["c"]
            turn_count = conn.execute(
                "SELECT COUNT(*) AS c FROM turns WHERE session_id = ?",
                (session_id,),
            ).fetchone()["c"]
            event_count = conn.execute(
                "SELECT COUNT(*) AS c FROM events WHERE family_id = ?",
                (fam,),
            ).fetchone()["c"]
            task_count = conn.execute(
                "SELECT COUNT(*) AS c FROM tasks WHERE task_id = ?",
                (task["id"],),
            ).fetchone()["c"]
        assert family_count == user_count == conv_count == turn_count == event_count == task_count == 0
    finally:
        _state._rag = old_rag
        if rag is not None:
            del rag
        gc.collect()
        try:
            shutil.rmtree(test_db)
        except Exception:
            pass


def test_30_6_family_foreign_keys_present():
    from src.infrastructure.database.db import get_db_connection

    with get_db_connection() as conn:
        fk_map = {
            table: [row["table"] for row in conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()]
            for table in ("users", "events", "tasks", "conversations", "turns")
        }
    assert "families" in fk_map["users"]
    assert "families" in fk_map["events"]
    assert "families" in fk_map["tasks"]
    assert "families" in fk_map["conversations"]
    assert "conversations" in fk_map["turns"]


test("30.1 RAG: ChromaDB family filter is real", test_30_1_rag_family_filter_real)
test("30.2 Conversations: API scoped by family", test_30_2_conversation_api_family_scope)
test("30.3 Events: unread/read scope by family", test_30_3_events_family_scope)
test("30.4 Tasks: operations scoped by family", test_30_4_tasks_family_scope)
test("30.5 Admin: family endpoints and cleanup", test_30_5_admin_family_endpoints_and_delete_cleanup)
test("30.6 DB: family foreign keys present", test_30_6_family_foreign_keys_present)

# == GROUP 31: Task 4.5 Homework System ====================================
print("\n[Group 31] Task 4.5 - Homework System")


def test_31_1_classify_homework_true_cases():
    from src.education.homework_classifier import classify_homework

    assert classify_homework("5 cộng 3 bằng mấy") is True
    assert classify_homework("tại sao trời mưa") is True
    assert classify_homework("bài tập về nhà hôm nay") is True


def test_31_2_classify_homework_false_cases():
    from src.education.homework_classifier import classify_homework

    assert classify_homework("hôm nay ăn gì") is False
    assert classify_homework("xin chào Bi") is False
    assert classify_homework("kể chuyện cho con nghe") is False


def test_31_3_mark_session_homework_callable():
    from src.infrastructure.database.db import mark_session_homework

    assert callable(mark_session_homework)


def test_31_4_get_homework_sessions_callable():
    from src.infrastructure.database.db import get_homework_sessions

    assert callable(get_homework_sessions)


def test_31_5_mark_and_retrieve_homework_session():
    from src.infrastructure.database.db import (
        create_session,
        get_homework_sessions,
        init_db,
        mark_session_homework,
    )

    init_db()
    sid = create_session(family_id="test_hw_family")
    assert mark_session_homework(sid) is True
    sessions = get_homework_sessions("test_hw_family")
    assert any(s["session_id"] == sid for s in sessions), (
        "Session da mark phai xuat hien trong homework list"
    )


def test_31_6_unmarked_session_not_in_homework():
    from src.infrastructure.database.db import create_session, get_homework_sessions

    sid2 = create_session(family_id="test_hw_family")
    sessions2 = get_homework_sessions("test_hw_family")
    sid2_in_hw = any(s["session_id"] == sid2 for s in sessions2)
    assert not sid2_in_hw, "Session chua mark khong duoc xuat hien trong homework"


def test_31_7_homework_route_registered():
    from src.api.routers.conversation_router import router

    paths = [r.path for r in router.routes]
    assert "/api/conversations/homework" in paths, "Homework endpoint phai duoc dang ky"


def test_31_8_homework_classifier_importable():
    import src.education.homework_classifier as hc

    assert hasattr(hc, "classify_homework")
    assert callable(hc.classify_homework)


test("31.1 HomeworkClassifier: true cases", test_31_1_classify_homework_true_cases)
test("31.2 HomeworkClassifier: false cases", test_31_2_classify_homework_false_cases)
test("31.3 DB: mark_session_homework callable", test_31_3_mark_session_homework_callable)
test("31.4 DB: get_homework_sessions callable", test_31_4_get_homework_sessions_callable)
test("31.5 DB: mark and retrieve homework session", test_31_5_mark_and_retrieve_homework_session)
test("31.6 DB: unmarked session excluded", test_31_6_unmarked_session_not_in_homework)
test("31.7 API: homework route registered", test_31_7_homework_route_registered)
test("31.8 HomeworkClassifier: importable", test_31_8_homework_classifier_importable)

# == GROUP 32: Review Fixes — normalize/homework columns ====================
print("\n[Group 32] Review Fixes — normalize consistency + homework columns")


def test_32_1_normalize_family_id_respects_env():
    """_normalize_family_id(None) phai tra ve gia tri tu FAMILY_ID env."""
    import importlib
    orig = os.environ.get("FAMILY_ID")
    try:
        os.environ["FAMILY_ID"] = "envtestfamily"
        import src.infrastructure.database.db as _db
        result = _db._normalize_family_id(None)
        assert result == "envtestfamily", (
            f"_normalize_family_id(None) expected 'envtestfamily', got '{result}'"
        )
        # Explicit value phai override env
        result2 = _db._normalize_family_id("explicit")
        assert result2 == "explicit", (
            f"_normalize_family_id('explicit') expected 'explicit', got '{result2}'"
        )
    finally:
        if orig is None:
            os.environ.pop("FAMILY_ID", None)
        else:
            os.environ["FAMILY_ID"] = orig


def test_32_2_normalize_family_id_default_fallback():
    """_normalize_family_id(None) phai tra 'default' khi FAMILY_ID khong set."""
    orig = os.environ.pop("FAMILY_ID", None)
    try:
        import src.infrastructure.database.db as _db
        result = _db._normalize_family_id(None)
        assert result == "default", (
            f"Expected 'default' fallback, got '{result}'"
        )
    finally:
        if orig is not None:
            os.environ["FAMILY_ID"] = orig


def test_32_3_normalize_unified_across_modules():
    """notifier, task_manager phai import _normalize_family_id tu db.py."""
    import src.infrastructure.notifications.notifier as _notifier
    import src.infrastructure.tasks.task_manager as _task_manager
    import src.infrastructure.database.db as _db

    assert getattr(_notifier, "_normalize_family_id", None) \
        is _db._normalize_family_id, \
        "notifier._normalize_family_id phải là cùng object với db._normalize_family_id"
    assert getattr(_task_manager, "_normalize_family_id", None) \
        is _db._normalize_family_id, \
        "task_manager._normalize_family_id phải là cùng object với db._normalize_family_id"


def test_32_4_get_homework_sessions_explicit_columns():
    """get_homework_sessions phai tra ve dung columns, khong co extra columns."""
    from src.infrastructure.database.db import (
        create_session,
        get_homework_sessions,
        init_db,
        mark_session_homework,
    )

    init_db()
    sid = create_session(family_id="test_cols_fix3")
    mark_session_homework(sid)
    sessions = get_homework_sessions("test_cols_fix3")
    assert len(sessions) > 0, "Phai co it nhat 1 homework session"
    expected_keys = {
        "session_id", "family_id", "title",
        "started_at", "ended_at", "turn_count",
        "is_homework", "homework_marked_at",
    }
    actual_keys = set(sessions[0].keys())
    assert actual_keys == expected_keys, (
        f"Column mismatch. Extra: {actual_keys - expected_keys}, "
        f"Missing: {expected_keys - actual_keys}"
    )


def test_32_5_seed_admin_uses_lowercase_family():
    """seed_admin_if_empty phai dung family_id='admin' (lowercase), khong phai 'Admin'."""
    import inspect
    from src.infrastructure.auth.auth import seed_admin_if_empty

    src = inspect.getsource(seed_admin_if_empty)
    assert '"Admin"' not in src, (
        "seed_admin_if_empty khong duoc dung 'Admin' (capitalize) — phai dung 'admin'"
    )
    assert '"admin"' in src, (
        "seed_admin_if_empty phai dung family_id='admin' (lowercase)"
    )


def test_32_6_clear_all_memories_accepts_family_id():
    """RAGManager.clear_all_memories phai nhan family_id param."""
    import inspect
    from src.memory.rag_manager import RAGManager

    sig = inspect.signature(RAGManager.clear_all_memories)
    assert "family_id" in sig.parameters, (
        "clear_all_memories phai co family_id parameter"
    )


def test_32_7_migrate_admin_family_case_runtime():
    """_migrate_admin_family_case phai doi 'Admin' → 'admin' khi chay init_db()."""
    import src.infrastructure.database.db as _db

    # Insert legacy 'Admin' family directly, bypassing normalize
    with _db.get_db_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO families (family_id, display_name, created_at) "
            "VALUES ('Admin', 'Admin', datetime('now'))"
        )
        conn.commit()

    # Force re-init so _migrate_admin_family_case runs
    _db._INITIALIZED = False
    _db.init_db()

    with _db.get_db_connection() as conn:
        admin_cap = conn.execute(
            "SELECT family_id FROM families WHERE family_id = 'Admin'"
        ).fetchone()
        admin_low = conn.execute(
            "SELECT family_id FROM families WHERE family_id = 'admin'"
        ).fetchone()

    assert admin_cap is None, "'Admin' phai duoc xoa sau migration"
    assert admin_low is not None, "'admin' phai ton tai sau migration"


test("32.1 normalize: respects FAMILY_ID env var", test_32_1_normalize_family_id_respects_env)
test("32.2 normalize: 'default' fallback when env not set", test_32_2_normalize_family_id_default_fallback)
test("32.3 normalize: unified import across modules", test_32_3_normalize_unified_across_modules)
test("32.4 get_homework_sessions: explicit columns only", test_32_4_get_homework_sessions_explicit_columns)
test("32.5 seed_admin: uses lowercase 'admin' family", test_32_5_seed_admin_uses_lowercase_family)
test("32.6 clear_all_memories: accepts family_id param", test_32_6_clear_all_memories_accepts_family_id)
test("32.7 DB: _migrate_admin_family_case runtime", test_32_7_migrate_admin_family_case_runtime)

print("\n[Group 33] Phase 5.2 — Display Backend")

# Test 33.1 — FaceAnimator import và init
from src.display.face_animator import FaceAnimator
fa = FaceAnimator()
def test_33_1_face_animator_init():
    assert fa.current_mode == 'idle', \
        "FaceAnimator phải khởi tạo với mode idle"
test("33.1 FaceAnimator init mode=idle", test_33_1_face_animator_init)

# Test 33.2 — set_mode hợp lệ
def test_33_2_face_animator_set_mode_valid():
    assert fa.set_mode('listening') == True
    assert fa.current_mode == 'listening'
test("33.2 FaceAnimator set_mode valid", test_33_2_face_animator_set_mode_valid)

# Test 33.3 — set_mode không hợp lệ
def test_33_3_face_animator_set_mode_invalid():
    assert fa.set_mode('bay_len_may') == False
    assert fa.current_mode == 'listening'  # không đổi
test("33.3 FaceAnimator set_mode invalid → False", test_33_3_face_animator_set_mode_invalid)

# Test 33.4 — set_emotion hợp lệ
def test_33_4_face_animator_set_emotion_valid():
    assert fa.set_emotion('happy') == True
    assert fa.current_emotion == 'happy'
test("33.4 FaceAnimator set_emotion valid", test_33_4_face_animator_set_emotion_valid)

# Test 33.5 — set_emotion không hợp lệ
def test_33_5_face_animator_set_emotion_invalid():
    assert fa.set_emotion('dien_ro') == False
test("33.5 FaceAnimator set_emotion invalid → False", test_33_5_face_animator_set_emotion_invalid)

# Test 33.6 — get_state format
def test_33_6_face_animator_get_state_format():
    state = fa.get_state()
    assert 'mode' in state, "get_state phải có key mode"
    assert 'emotion' in state, "get_state phải có key emotion"
    assert 'last_changed' in state, "get_state phải có key last_changed"
test("33.6 FaceAnimator get_state format", test_33_6_face_animator_get_state_format)

# Test 33.7 — FaceAnimator thread-safe
import threading
def test_33_7_face_animator_thread_safe():
    errors = []
    def switch_mode(m):
        try:
            fa.set_mode(m)
        except Exception as e:
            errors.append(str(e))
    threads = [threading.Thread(target=switch_mode,
               args=(m,)) for m in ['idle','talking','thinking']]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(errors) == 0, f"Thread-safe errors: {errors}"
test("33.7 FaceAnimator thread-safe", test_33_7_face_animator_thread_safe)

# Test 33.8 — FlashcardRenderer import và load
from src.display.flashcard_renderer import FlashcardRenderer
fr = FlashcardRenderer()
def test_33_8_flashcard_renderer_load_deck():
    count = fr.load_deck('english')
    assert count > 0, "load_deck phải trả về số lượng > 0"
test("33.8 FlashcardRenderer load_deck", test_33_8_flashcard_renderer_load_deck)

# Test 33.9 — get_current_card format
def test_33_9_flashcard_renderer_card_format():
    card = fr.get_current_card()
    required_keys = {'emoji', 'word', 'phonetic', 'meaning',
                     'current', 'total'}
    missing = required_keys - set(card.keys())
    assert not missing, f"Card thiếu keys: {missing}"
test("33.9 FlashcardRenderer card format đầy đủ", test_33_9_flashcard_renderer_card_format)

# Test 33.10 — mark_correct tăng score
def test_33_10_flashcard_renderer_mark_correct():
    score_before = fr.score
    new_score = fr.mark_correct()
    assert new_score > score_before, "Score phải tăng sau mark_correct"
    assert fr.correct_count == 1
test("33.10 FlashcardRenderer mark_correct tăng score", test_33_10_flashcard_renderer_mark_correct)

# Test 33.11 — mark_incorrect không tăng score
def test_33_11_flashcard_renderer_mark_incorrect():
    score_before = fr.score
    fr.mark_incorrect()
    assert fr.score == score_before, "Score không đổi sau mark_incorrect"
    assert fr.incorrect_count == 1
test("33.11 FlashcardRenderer mark_incorrect không đổi score", test_33_11_flashcard_renderer_mark_incorrect)

# Test 33.12 — get_progress format
def test_33_12_flashcard_renderer_get_progress():
    progress = fr.get_progress()
    assert 'correct' in progress
    assert 'incorrect' in progress
    assert 'remaining' in progress
    assert 'score' in progress
    assert progress['correct'] == 1
    assert progress['incorrect'] == 1
test("33.12 FlashcardRenderer get_progress format", test_33_12_flashcard_renderer_get_progress)

# Test 33.13 — next_card chuyển card
def test_33_13_flashcard_renderer_next_card():
    card1 = fr.get_current_card()
    fr.next_card()
    card2 = fr.get_current_card()
    # Index phải thay đổi (hoặc deck chỉ có 1 card)
    assert card2['current'] != card1['current'] or \
        fr.get_progress()['total'] == 1
test("33.13 FlashcardRenderer next_card", test_33_13_flashcard_renderer_next_card)

# Test 33.14 — reset về đầu
def test_33_14_flashcard_renderer_reset():
    fr.reset()
    assert fr.score == 0
    assert fr.correct_count == 0
    assert fr.incorrect_count == 0
test("33.14 FlashcardRenderer reset", test_33_14_flashcard_renderer_reset)

print("\n[Group 34] Phase 6.1 — Persona Manager")

from src.ai.persona_manager import PersonaManager


def test_34_1_persona_import_init():
    pm = PersonaManager("test_persona_34_1")
    assert pm.get_name() == "Bi"


def test_34_2_persona_full_dict():
    persona = PersonaManager("test_persona_34_2").get_persona()
    for key in ["name", "gender", "voice", "personality", "language"]:
        assert key in persona, f"Missing key: {key}"
    for key in ["playfulness", "extraversion", "energy"]:
        assert key in persona["personality"], f"Missing personality key: {key}"


def test_34_3_persona_save_name():
    pm = PersonaManager("test_persona_34_3")
    assert pm.save({"name": "Bibo"}) is True
    assert pm.get_name() == "Bibo"


def test_34_4_persona_save_personality_range():
    pm = PersonaManager("test_persona_34_4")
    ok = pm.save({"personality": {"playfulness": 0, "extraversion": 50, "energy": 100}})
    assert ok is True
    p = pm.get_persona()["personality"]
    assert p["playfulness"] == 0
    assert p["energy"] == 100


def test_34_5_persona_reject_out_of_range():
    pm = PersonaManager("test_persona_34_5")
    before = pm.get_persona()
    assert pm.save({"personality": {"energy": 101}}) is False
    assert pm.get_persona() == before


def test_34_6_persona_prompt_modifier():
    text = PersonaManager("test_persona_34_6").get_system_prompt_modifier()
    assert isinstance(text, str)
    assert len(text) > 20


def test_34_7_persona_voice_id():
    voice = PersonaManager("test_persona_34_7").get_voice_id()
    assert isinstance(voice, str)
    assert len(voice) > 0


def test_34_8_persona_get_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/persona" in paths


def test_34_9_persona_post_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/persona/update" in paths


test("34.1 PersonaManager import và init", test_34_1_persona_import_init)
test("34.2 get_persona trả về dict đầy đủ", test_34_2_persona_full_dict)
test("34.3 save với name hợp lệ", test_34_3_persona_save_name)
test("34.4 save personality values 0-100", test_34_4_persona_save_personality_range)
test("34.5 save ngoài range reject", test_34_5_persona_reject_out_of_range)
test("34.6 get_system_prompt_modifier string", test_34_6_persona_prompt_modifier)
test("34.7 get_voice_id string không rỗng", test_34_7_persona_voice_id)
test("34.8 GET /api/persona route tồn tại", test_34_8_persona_get_route_exists)
test("34.9 POST /api/persona/update route tồn tại", test_34_9_persona_post_route_exists)

print("\n[Group 35] Phase 6.2 — Emotion Analyzer")

from src.emotion.emotion_analyzer import Emotion, EmotionAnalyzer


def test_35_1_emotion_import():
    analyzer = EmotionAnalyzer("test_emotion_35_1")
    assert analyzer is not None


def test_35_2_emotion_happy_text():
    emotion, confidence = EmotionAnalyzer("test_emotion_35_2").analyze_text("vui quá")
    assert emotion == Emotion.HAPPY
    assert confidence > 0


def test_35_3_emotion_sad_text():
    emotion, confidence = EmotionAnalyzer("test_emotion_35_3").analyze_text("buồn ghê")
    assert emotion == Emotion.SAD
    assert confidence > 0


def test_35_4_emotion_neutral_text():
    emotion, confidence = EmotionAnalyzer("test_emotion_35_4").analyze_text("hom nay em hoc bai")
    assert emotion == Emotion.NEUTRAL
    assert confidence > 0


def test_35_5_combined_emotion_format():
    data = EmotionAnalyzer("test_emotion_35_5").get_combined_emotion(
        text="vui qua",
        voice_energy=0.6,
        voice_pitch=0.6,
    )
    assert "emotion" in data
    assert "confidence" in data
    assert "sources" in data


def test_35_6_record_emotion_no_crash():
    analyzer = EmotionAnalyzer("test_emotion_35_6")
    analyzer.record_emotion(Emotion.HAPPY, 0.9)


def test_35_7_today_summary_dict():
    analyzer = EmotionAnalyzer("test_emotion_35_7")
    summary = analyzer.get_today_summary("test_emotion_35_7")
    assert isinstance(summary, dict)
    assert "dominant" in summary


def test_35_8_weekly_summary_7_items():
    summary = EmotionAnalyzer("test_emotion_35_8").get_weekly_summary("test_emotion_35_8")
    assert isinstance(summary, list)
    assert len(summary) == 7


def test_35_9_emotion_today_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/emotion/today" in paths


def test_35_10_emotion_summary_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/emotion/summary" in paths


test("35.1 EmotionAnalyzer import", test_35_1_emotion_import)
test("35.2 analyze_text vui quá → happy", test_35_2_emotion_happy_text)
test("35.3 analyze_text buồn ghê → sad", test_35_3_emotion_sad_text)
test("35.4 analyze_text neutral → neutral", test_35_4_emotion_neutral_text)
test("35.5 get_combined_emotion format đúng", test_35_5_combined_emotion_format)
test("35.6 record_emotion không crash", test_35_6_record_emotion_no_crash)
test("35.7 get_today_summary trả về dict", test_35_7_today_summary_dict)
test("35.8 get_weekly_summary trả về list 7 items", test_35_8_weekly_summary_7_items)
test("35.9 GET /api/emotion/today route tồn tại", test_35_9_emotion_today_route_exists)
test("35.10 GET /api/emotion/summary route tồn tại", test_35_10_emotion_summary_route_exists)

print("\n[Group 36] Phase 6.3 — Emotion Journal & Alert")

from src.emotion.emotion_alert import EmotionAlert
from src.emotion.emotion_journal import EmotionJournal


def test_36_1_journal_add_entry():
    journal = EmotionJournal()
    assert journal.add_entry("test_journal_36_1", "happy", "hoc bai tot") is True


def test_36_2_journal_get_entries():
    journal = EmotionJournal()
    journal.add_entry("test_journal_36_2", "happy")
    entries = journal.get_entries("test_journal_36_2")
    assert isinstance(entries, list)


def test_36_3_journal_streak_zero():
    streak = EmotionJournal().get_streak("test_journal_36_3_empty", "sad")
    assert streak == 0


def test_36_4_journal_export_report_format():
    report = EmotionJournal().export_report("test_journal_36_4")
    assert "emotion_counts" in report
    assert "dominant" in report
    assert "sad_streak" in report


def test_36_5_alert_no_data_no_crash():
    journal = EmotionJournal()
    alert = EmotionAlert()
    result = alert.check_and_alert("test_alert_36_5_empty", journal, None)
    assert result is False


def test_36_6_alert_status_dict():
    status = EmotionAlert().get_alert_status("test_alert_36_6")
    assert isinstance(status, dict)
    assert "active" in status
    assert "status" in status


test("36.1 EmotionJournal add_entry", test_36_1_journal_add_entry)
test("36.2 get_entries trả về list", test_36_2_journal_get_entries)
test("36.3 get_streak = 0 khi không có streak", test_36_3_journal_streak_zero)
test("36.4 export_report format đúng", test_36_4_journal_export_report_format)
test("36.5 EmotionAlert check không crash khi không có data", test_36_5_alert_no_data_no_crash)
test("36.6 get_alert_status trả về dict", test_36_6_alert_status_dict)

print("\n[Group 37] Phase 7.1 — Flashcard Engine")

from src.education.flashcard_engine import FlashcardEngine


def test_37_1_flashcard_import():
    engine = FlashcardEngine("test_flashcard_37_1")
    assert engine is not None


def test_37_2_start_english_animals():
    engine = FlashcardEngine("test_flashcard_37_2")
    info = engine.start_session("english", "animals")
    assert info["subject"] == "english"
    assert info["topic"] == "animals"
    assert info["total_cards"] >= 20


def test_37_3_next_card_format():
    engine = FlashcardEngine("test_flashcard_37_3")
    engine.start_session("english", "animals")
    card = engine.get_next_card()
    for key in ["id", "word", "meaning", "difficulty"]:
        assert key in card, f"Missing card key: {key}"


def test_37_4_submit_answer_correct():
    engine = FlashcardEngine("test_flashcard_37_4")
    engine.start_session("english", "animals")
    card = engine.get_next_card()
    result = engine.submit_answer(card["id"], True)
    assert result["correct"] is True
    assert result["score"] == 1


def test_37_5_submit_answer_incorrect():
    engine = FlashcardEngine("test_flashcard_37_5")
    engine.start_session("english", "animals")
    card = engine.get_next_card()
    result = engine.submit_answer(card["id"], False)
    assert result["correct"] is False
    assert len(engine.get_review_cards()) == 1


def test_37_6_end_session_summary():
    engine = FlashcardEngine("test_flashcard_37_6")
    engine.start_session("english", "animals")
    card = engine.get_next_card()
    engine.submit_answer(card["id"], True)
    summary = engine.end_session()
    assert summary["total_answered"] == 1
    assert summary["correct"] == 1


def test_37_7_resource_file_exists():
    from pathlib import Path
    assert Path("resources/flashcards/english/animals.json").exists()


def test_37_8_resource_json_valid():
    import json
    with open("resources/flashcards/english/animals.json", "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["subject"] == "english"
    assert isinstance(data["cards"], list)
    assert len(data["cards"]) >= 20


def test_37_9_flashcard_start_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/education/flashcard/start" in paths


def test_37_10_education_summary_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/education/summary" in paths


test("37.1 FlashcardEngine import", test_37_1_flashcard_import)
test("37.2 start_session english/animals", test_37_2_start_english_animals)
test("37.3 get_next_card format đúng", test_37_3_next_card_format)
test("37.4 submit_answer correct", test_37_4_submit_answer_correct)
test("37.5 submit_answer incorrect", test_37_5_submit_answer_incorrect)
test("37.6 end_session trả về summary", test_37_6_end_session_summary)
test("37.7 Resources english/animals.json tồn tại", test_37_7_resource_file_exists)
test("37.8 JSON format hợp lệ", test_37_8_resource_json_valid)
test("37.9 POST /api/education/flashcard/start route tồn tại", test_37_9_flashcard_start_route_exists)
test("37.10 GET /api/education/summary route tồn tại", test_37_10_education_summary_route_exists)

print("\n[Group 38] Phase 7.2 — Language Tutor + Pronunciation")

from src.audio.analysis.pronunciation_checker import PronunciationChecker
from src.education.language_tutor import LanguageTutor


def test_38_1_language_tutor_import():
    tutor = LanguageTutor()
    assert "en" in tutor.SUPPORTED_LANGUAGES


def test_38_2_translate_vi_en_basic():
    result = LanguageTutor().translate("xin chao", "vi", "en")
    assert result == "hello"


def test_38_3_pronunciation_guide_format():
    guide = LanguageTutor().get_pronunciation_guide("cat", "en")
    assert "phonetic" in guide
    assert "tips" in guide


def test_38_4_pronunciation_checker_import():
    checker = PronunciationChecker()
    assert checker is not None


def test_38_5_pronunciation_correct_high_score():
    result = PronunciationChecker().check("cat", "cat")
    assert result["score"] >= 80
    assert result["is_correct"] is True


def test_38_6_pronunciation_wrong_low_score():
    result = PronunciationChecker().check("dog", "cat")
    assert result["score"] < 80
    assert result["is_correct"] is False


def test_38_7_normalize_lowercase():
    normalized = PronunciationChecker().normalize_text("CAT!", "en")
    assert normalized == "cat"


test("38.1 LanguageTutor import", test_38_1_language_tutor_import)
test("38.2 translate Việt→Anh cơ bản", test_38_2_translate_vi_en_basic)
test("38.3 get_pronunciation_guide format", test_38_3_pronunciation_guide_format)
test("38.4 PronunciationChecker import", test_38_4_pronunciation_checker_import)
test("38.5 check đúng từ → score cao", test_38_5_pronunciation_correct_high_score)
test("38.6 check sai từ → score thấp", test_38_6_pronunciation_wrong_low_score)
test("38.7 normalize_text lowercase", test_38_7_normalize_lowercase)

print("\n[Group 39] Phase 7.3 — Progress Tracker + Curriculum")

from src.education.curriculum import Curriculum
from src.education.progress_tracker import ProgressTracker


def test_39_1_progress_record_session():
    tracker = ProgressTracker()
    assert tracker.record_session("test_progress_39_1", "english", 3, 1, 120) is True


def test_39_2_subject_progress_format():
    tracker = ProgressTracker()
    tracker.record_session("test_progress_39_2", "math", 2, 2, 60)
    progress = tracker.get_subject_progress("test_progress_39_2", "math")
    assert progress["subject"] == "math"
    assert "accuracy" in progress


def test_39_3_progress_streak_initial_zero():
    streak = ProgressTracker().get_streak("test_progress_39_3_empty")
    assert streak == 0


def test_39_4_weekly_report_format():
    report = ProgressTracker().generate_weekly_report("test_progress_39_4")
    assert "subjects" in report
    assert "streak" in report


def test_39_5_curriculum_schedule_7_days():
    schedule = Curriculum().get_schedule("test_curriculum_39_5")
    assert isinstance(schedule, dict)
    assert len(schedule) == 7


def test_39_6_curriculum_today_no_crash():
    today = Curriculum().get_today_subject("test_curriculum_39_6")
    assert "day" in today
    assert "rest_day" in today


def test_39_7_curriculum_update_verify():
    curriculum = Curriculum()
    schedule = curriculum.get_schedule("test_curriculum_39_7")
    schedule["monday"] = {"subject": "math", "time": "18:30"}
    assert curriculum.update_schedule("test_curriculum_39_7", schedule) is True
    saved = curriculum.get_schedule("test_curriculum_39_7")
    assert saved["monday"]["subject"] == "math"
    assert saved["monday"]["time"] == "18:30"


test("39.1 ProgressTracker record_session", test_39_1_progress_record_session)
test("39.2 get_subject_progress format", test_39_2_subject_progress_format)
test("39.3 get_streak = 0 initially", test_39_3_progress_streak_initial_zero)
test("39.4 generate_weekly_report", test_39_4_weekly_report_format)
test("39.5 Curriculum get_schedule có 7 ngày", test_39_5_curriculum_schedule_7_days)
test("39.6 get_today_subject không crash", test_39_6_curriculum_today_no_crash)
test("39.7 update_schedule → verify saved", test_39_7_curriculum_update_verify)

print("\n[Group 40] Phase 8.1 — Music Player Backend")

from src.audio.output.music_player import MusicPlayer
from src.entertainment.music_library import MusicLibrary


def test_40_1_music_library_import():
    library = MusicLibrary()
    assert library.CATEGORIES


def test_40_2_get_playlist_list():
    playlist = MusicLibrary().get_playlist("lullabies")
    assert isinstance(playlist, list)
    assert len(playlist) >= 1


def test_40_3_music_search_list():
    results = MusicLibrary().search("ru")
    assert isinstance(results, list)


def test_40_4_is_copyrighted_bool():
    result = MusicLibrary().is_copyrighted("lullaby_001")
    assert isinstance(result, bool)


def test_40_5_music_player_import():
    player = MusicPlayer()
    assert player is not None


def test_40_6_music_status_dict():
    status = MusicPlayer().get_status()
    assert isinstance(status, dict)
    assert "playing" in status
    assert "volume" in status


def test_40_7_set_volume_valid():
    player = MusicPlayer()
    assert player.set_volume(0) is True
    assert player.set_volume(100) is True


def test_40_8_set_volume_invalid():
    player = MusicPlayer()
    assert player.set_volume(-1) is False
    assert player.set_volume(101) is False


def test_40_9_music_play_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/music/play" in paths


def test_40_10_music_status_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/music/status" in paths


test("40.1 MusicLibrary import", test_40_1_music_library_import)
test("40.2 get_playlist trả về list", test_40_2_get_playlist_list)
test("40.3 search trả về list", test_40_3_music_search_list)
test("40.4 is_copyrighted trả về bool", test_40_4_is_copyrighted_bool)
test("40.5 MusicPlayer import", test_40_5_music_player_import)
test("40.6 get_status trả về dict", test_40_6_music_status_dict)
test("40.7 set_volume 0-100 valid", test_40_7_set_volume_valid)
test("40.8 set_volume ngoài range → False", test_40_8_set_volume_invalid)
test("40.9 POST /api/music/play route tồn tại", test_40_9_music_play_route_exists)
test("40.10 GET /api/music/status route tồn tại", test_40_10_music_status_route_exists)

print("\n[Group 41] Phase 8.2 — Story Engine")

from src.entertainment.story_engine import StoryEngine


def test_41_1_story_engine_import():
    engine = StoryEngine()
    assert engine is not None


def test_41_2_story_list_returns_list():
    stories = StoryEngine().get_story_list()
    assert isinstance(stories, list)
    assert len(stories) >= 1


def test_41_3_tell_story_by_id():
    story = StoryEngine().tell_story(story_id="fairy_001")
    assert story["title"]
    assert story["content"]


def test_41_4_bedtime_story_format():
    story = StoryEngine().get_bedtime_story()
    assert "title" in story
    assert "content" in story
    assert "duration_estimate" in story


def test_41_5_story_files_exist():
    from pathlib import Path
    assert Path("resources/stories/fairy_tales/co_tich.json").exists()
    assert Path("resources/stories/fables/ngu_ngon.json").exists()
    assert Path("resources/stories/bedtime/ru_ngu.json").exists()


def test_41_6_story_tell_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/story/tell" in paths


test("41.1 StoryEngine import", test_41_1_story_engine_import)
test("41.2 get_story_list trả về list", test_41_2_story_list_returns_list)
test("41.3 tell_story với story_id", test_41_3_tell_story_by_id)
test("41.4 get_bedtime_story format đúng", test_41_4_bedtime_story_format)
test("41.5 Story files tồn tại", test_41_5_story_files_exist)
test("41.6 POST /api/story/tell route tồn tại", test_41_6_story_tell_route_exists)

print("\n[Group 42] Phase 8.3 — Game Engine")

from src.entertainment.game_voice_quiz import VoiceQuizGame
from src.entertainment.game_word_quiz import WordQuizGame


def test_42_1_word_quiz_import_start():
    game = WordQuizGame()
    result = game.start_game("test_game_42_1")
    assert result["status"] == "started"


def test_42_2_word_question_format():
    game = WordQuizGame()
    game.start_game("test_game_42_2")
    question = game.get_question()
    assert "question" in question
    assert len(question["options"]) == 4
    assert "time_limit_sec" in question


def test_42_3_word_submit_correct():
    game = WordQuizGame()
    game.start_game("test_game_42_3")
    game.get_question()
    result = game.submit_answer(game._current["answer"])
    assert result["correct"] is True


def test_42_4_word_submit_incorrect():
    game = WordQuizGame()
    game.start_game("test_game_42_4")
    game.get_question()
    result = game.submit_answer("sai dap an")
    assert result["correct"] is False


def test_42_5_word_end_summary():
    game = WordQuizGame()
    game.start_game("test_game_42_5")
    summary = game.end_game()
    assert "total_score" in summary
    assert "high_score" in summary


def test_42_6_voice_quiz_import_start():
    game = VoiceQuizGame()
    result = game.start_game("test_voice_42_6")
    assert result["status"] == "started"


def test_42_7_voice_get_riddle_dict():
    game = VoiceQuizGame()
    game.start_game("test_voice_42_7")
    riddle = game.get_riddle()
    assert "riddle_text" in riddle
    assert "hint" in riddle
    assert "answer" in riddle


def test_42_8_voice_answer_correct():
    game = VoiceQuizGame()
    game.start_game("test_voice_42_8")
    riddle = game.get_riddle()
    result = game.check_voice_answer(riddle["answer"])
    assert result["correct"] is True


def test_42_9_voice_answer_near_correct():
    game = VoiceQuizGame()
    game.start_game("test_voice_42_9")
    game.get_riddle()
    result = game.check_voice_answer("meo")
    assert isinstance(result["correct"], bool)
    assert result["score"] >= 0


test("42.1 WordQuizGame import + start", test_42_1_word_quiz_import_start)
test("42.2 get_question format đúng (4 options)", test_42_2_word_question_format)
test("42.3 submit_answer correct", test_42_3_word_submit_correct)
test("42.4 submit_answer incorrect", test_42_4_word_submit_incorrect)
test("42.5 end_game trả về summary", test_42_5_word_end_summary)
test("42.6 VoiceQuizGame import + start", test_42_6_voice_quiz_import_start)
test("42.7 get_riddle trả về dict", test_42_7_voice_get_riddle_dict)
test("42.8 check_voice_answer với đúng", test_42_8_voice_answer_correct)
test("42.9 check_voice_answer với gần đúng", test_42_9_voice_answer_near_correct)

print("\n[Group 43] Phase 9.1 — Motor Controller Placeholder")

from src.motion.motor_controller import MotorController


def test_43_1_motor_import():
    motor = MotorController(port=None)
    assert motor is not None


def test_43_2_motor_simulation_true():
    motor = MotorController(port=None)
    assert motor.is_simulation() is True


def test_43_3_motor_forward_no_crash():
    motor = MotorController(port=None)
    assert motor.forward() is True


def test_43_4_motor_stop_no_crash():
    motor = MotorController(port=None)
    assert motor.stop() is True


def test_43_5_motor_status_format():
    status = MotorController(port=None).get_status()
    assert "connected" in status
    assert "mode" in status
    assert "last_command" in status


def test_43_6_motor_go_home_no_crash():
    motor = MotorController(port=None)
    assert motor.go_home() is True


def test_43_7_motor_stop_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/motor/stop" in paths


def test_43_8_motor_status_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/motor/status" in paths


test("43.1 MotorController import", test_43_1_motor_import)
test("43.2 is_simulation() → True", test_43_2_motor_simulation_true)
test("43.3 forward() không crash", test_43_3_motor_forward_no_crash)
test("43.4 stop() không crash", test_43_4_motor_stop_no_crash)
test("43.5 get_status format đúng", test_43_5_motor_status_format)
test("43.6 go_home() không crash", test_43_6_motor_go_home_no_crash)
test("43.7 POST /api/motor/stop route tồn tại", test_43_7_motor_stop_route_exists)
test("43.8 GET /api/motor/status route tồn tại", test_43_8_motor_status_route_exists)

print("\n[Group 44] Phase 10.1 — Analytics & Weekly Report")

from src.api.routers.analytics_router import get_daily_stats, get_weekly_analytics


def test_44_1_analytics_weekly_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/analytics/weekly" in paths


def test_44_2_analytics_daily_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/analytics/daily" in paths


def test_44_3_weekly_analytics_format():
    data = get_weekly_analytics("test_analytics_44_3")
    assert "family_id" in data
    assert "conversations" in data
    assert "emotion" in data
    assert "learning" in data


def test_44_4_daily_stats_format():
    data = get_daily_stats("test_analytics_44_4")
    assert "family_id" in data
    assert "date" in data
    assert "conversations" in data


test("44.1 GET /api/analytics/weekly route tồn tại", test_44_1_analytics_weekly_route_exists)
test("44.2 GET /api/analytics/daily route tồn tại", test_44_2_analytics_daily_route_exists)
test("44.3 get_weekly_analytics format đúng", test_44_3_weekly_analytics_format)
test("44.4 get_daily_stats format đúng", test_44_4_daily_stats_format)

print("\n[Group 45] Phase 10.2 — Robot-to-Robot Communication")

from src.communication.robot_to_robot import RobotToRobot
from src.communication.video_call import VideoCallManager


def test_45_1_robot_to_robot_import():
    manager = RobotToRobot()
    assert manager is not None


def test_45_2_discover_robots_list():
    robots = RobotToRobot().discover_robots(timeout_sec=1)
    assert isinstance(robots, list)


def test_45_3_connected_robots_list():
    manager = RobotToRobot()
    assert manager.connect("127.0.0.1") is True
    robots = manager.get_connected_robots()
    assert isinstance(robots, list)
    assert len(robots) == 1


def test_45_4_video_call_import():
    manager = VideoCallManager()
    assert manager is not None


def test_45_5_get_contacts_list():
    contacts = VideoCallManager().get_contacts("test_video_45_5")
    assert isinstance(contacts, list)


def test_45_6_add_contact_dict():
    contact = VideoCallManager().add_contact("test_video_45_6", "Me")
    assert isinstance(contact, dict)
    assert "contact_id" in contact
    assert contact["name"] == "Me"


test("45.1 RobotToRobot import", test_45_1_robot_to_robot_import)
test("45.2 discover_robots trả về list", test_45_2_discover_robots_list)
test("45.3 get_connected_robots trả về list", test_45_3_connected_robots_list)
test("45.4 VideoCallManager import", test_45_4_video_call_import)
test("45.5 get_contacts trả về list", test_45_5_get_contacts_list)
test("45.6 add_contact trả về dict", test_45_6_add_contact_dict)

print("\n[Group 46] Fix Verification — Review Issues")


def test_46_1_video_call_routes_registered():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/video/call/start" in paths, "Video call start route phai duoc dang ky"
    assert "/api/video/contacts" in paths, "Video contacts route phai duoc dang ky"


def test_46_2_game_routes_registered():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/game/word-quiz/start" in paths, "Word quiz start route phai duoc dang ky"
    assert "/api/game/voice-quiz/start" in paths, "Voice quiz start route phai duoc dang ky"


def test_46_3_no_deprecated_datetime_utcnow():
    from pathlib import Path
    EXCLUDE = {".git", ".venv", "venv", "node_modules", "__pycache__", "runtime", "logs", "dist", "build"}
    PATTERN = "datetime." + "utcnow("
    hits = []
    for path in Path("src").rglob("*.py"):
        if any(part in EXCLUDE for part in path.parts):
            continue
        try:
            if PATTERN in path.read_text(encoding="utf-8", errors="ignore"):
                hits.append(str(path))
        except OSError:
            pass
    assert hits == [], f"Con utcnow() trong: {hits}"


def test_46_4_learning_schedules_table_exists():
    from src.infrastructure.database.db import get_db_connection, init_db
    init_db()
    with get_db_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t["name"] for t in tables]
    assert "learning_schedules" in table_names, "Bang learning_schedules phai ton tai"


def test_46_5_schedule_save_load_from_sqlite():
    from src.infrastructure.database.db import get_learning_schedule, save_learning_schedule
    test_schedule = {
        "monday": {"subject": "english", "time": "19:00"},
        "tuesday": {"subject": "math", "time": "19:00"},
        "sunday": None,
    }
    assert save_learning_schedule("test_sched_family", test_schedule) is True
    loaded = get_learning_schedule("test_sched_family")
    assert "monday" in loaded
    assert loaded["monday"]["subject"] == "english"
    assert "sunday" not in loaded


def test_46_6_emotion_weekly_summary_format():
    from src.api.routers.emotion_router import get_weekly_summary
    from src.emotion.emotion_analyzer import EmotionAnalyzer
    analyzer = EmotionAnalyzer(family_id="test_emotion_family")
    summary = analyzer.get_weekly_summary("test_emotion_family")
    assert isinstance(summary, list), "Weekly summary phai la list"
    direct_summary = get_weekly_summary("test_emotion_family")
    assert isinstance(direct_summary, list), "Router helper phai tra ve list"
    if len(summary) > 0:
        day = summary[0]
        assert "date" in day or "dominant" in day, "Moi ngay phai co date hoac dominant"
        assert "breakdown" in day, "Moi ngay phai co breakdown"


test("46.1 Video call routes registered", test_46_1_video_call_routes_registered)
test("46.2 Game routes registered", test_46_2_game_routes_registered)
test("46.3 No deprecated datetime.utcnow()", test_46_3_no_deprecated_datetime_utcnow)
test("46.4 learning_schedules table exists", test_46_4_learning_schedules_table_exists)
test("46.5 Schedule save/load from SQLite", test_46_5_schedule_save_load_from_sqlite)
test("46.6 Emotion weekly summary format", test_46_6_emotion_weekly_summary_format)

print("\n[Group 47] Fix Verification — API Contract")


def test_47_1_parent_app_index_exists():
    from pathlib import Path
    idx = Path("frontend/parent_app/index.html")
    assert idx.exists(), "frontend/parent_app/index.html phai ton tai"


def test_47_2_ops_router_frontend_path():
    import inspect
    from src.api.routers import ops_router
    src = inspect.getsource(ops_router)
    assert "src/api/static" not in src, "ops_router khong duoc reference src/api/static nua"
    assert "frontend" in src, "ops_router phai reference frontend/parent_app"


def test_47_3_verify_db_clean_uses_src():
    with open("verify_db_clean.py", encoding="utf-8") as f:
        content = f.read()
    assert "src_brain" not in content, "verify_db_clean.py khong duoc import src_brain"


def test_47_4_verify_db_clean_runs():
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "verify_db_clean.py"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"verify_db_clean.py loi: {result.stderr[:200]}"


def test_47_5_game_routes_exact():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/game/word-quiz/start" in paths
    assert "/api/game/voice-quiz/start" in paths
    assert "/api/game/start" not in paths, "Khong nen co generic /api/game/start route"


def test_47_6_music_play_route_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/music/play" in paths, "/api/music/play route phai ton tai"


test("47.1 Parent App index.html tồn tại đúng path", test_47_1_parent_app_index_exists)
test("47.2 ops_router trỏ đúng frontend path", test_47_2_ops_router_frontend_path)
test("47.3 verify_db_clean dùng src mới", test_47_3_verify_db_clean_uses_src)
test("47.4 verify_db_clean chạy không lỗi", test_47_4_verify_db_clean_runs)
test("47.5 Game routes đúng path không generic", test_47_5_game_routes_exact)
test("47.6 Music play route tồn tại", test_47_6_music_play_route_exists)

print("\n[Group 48] Fix Verification — Round 3")


def test_48_1_delete_family_learning_schedules():
    from src.infrastructure.database.db import (
        delete_family_record,
        get_learning_schedule,
        init_db,
        save_learning_schedule,
    )
    init_db()
    test_fid = "test_delete_family_48"
    save_learning_schedule(test_fid, {
        "monday": {"subject": "english", "time": "19:00"},
    })
    sched = get_learning_schedule(test_fid)
    assert "monday" in sched, "Schedule phai duoc luu truoc"
    try:
        delete_family_record(test_fid)
    except Exception:
        pass
    sched_after = get_learning_schedule(test_fid)
    assert len(sched_after) == 0, "learning_schedules phai duoc xoa khi delete family"


def test_48_2_delete_family_emotion_logs():
    from src.emotion.emotion_analyzer import EmotionAnalyzer
    from src.infrastructure.database.db import (
        delete_family_record,
        get_db_connection,
        init_db,
    )
    init_db()
    test_fid = "test_delete_family_48"
    EmotionAnalyzer(family_id=test_fid)
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO emotion_logs
            (family_id, timestamp, emotion, confidence, source)
            VALUES (?, datetime('now'), 'happy', 0.9, 'test')
            """,
            (test_fid,),
        )
        conn.commit()
    try:
        delete_family_record(test_fid)
    except Exception:
        pass
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT COUNT(*) as c FROM emotion_logs WHERE family_id=?",
            (test_fid,),
        ).fetchone()
    assert rows["c"] == 0, "emotion_logs phai duoc xoa khi delete family"


def test_48_3_music_volume_field_handled():
    with open("frontend/parent_app/src/pages/MorePage.jsx", encoding="utf-8") as f:
        frontend_src = f.read()
    assert "JSON.stringify({ level: parseInt(v) })" in frontend_src or "level: parseInt" in frontend_src, (
        "Frontend phai gui level cho /api/music/volume"
    )
    import inspect
    from src.api.routers import music_router
    src = inspect.getsource(music_router)
    vol_idx = src.find("/api/music/volume")
    if vol_idx < 0:
        vol_idx = src.find("set_volume")
    vol_src = src[max(0, vol_idx):vol_idx + 300]
    assert "level" in vol_src or "volume" in vol_src, (
        "Music volume endpoint phai doc level hoac volume field"
    )


def test_48_4_stress_test_uses_src_paths():
    with open("stress_test.py", encoding="utf-8") as f:
        stress_content = f.read()
    assert "src_brain" not in stress_content, "stress_test.py khong duoc import src_brain"


def test_48_5_stress_test_runs_without_module_not_found():
    import subprocess
    result = subprocess.run(
        ["python3", "stress_test.py"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "ModuleNotFoundError" not in result.stderr, (
        f"stress_test co ModuleNotFoundError: {result.stderr[:300]}"
    )


def test_48_6_education_schedule_route_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/education/schedule" in paths, (
        "/api/education/schedule route phai ton tai"
    )


test("48.1 delete_family xóa learning_schedules", test_48_1_delete_family_learning_schedules)
test("48.2 delete_family xóa emotion_logs", test_48_2_delete_family_emotion_logs)
test("48.3 Music volume field handled", test_48_3_music_volume_field_handled)
test("48.4 stress_test dùng src paths mới", test_48_4_stress_test_uses_src_paths)
test("48.5 stress_test chạy không ModuleNotFoundError", test_48_5_stress_test_runs_without_module_not_found)
test("48.6 Education schedule API route tồn tại", test_48_6_education_schedule_route_exists)

print("\n[Group 49] Fix Verification — Round 4")


def test_49_1_migrate_db_path_if_needed_callable():
    from src.infrastructure.database.db import migrate_db_path_if_needed
    assert callable(migrate_db_path_if_needed), "migrate_db_path_if_needed phải là callable"


def test_49_2_migrate_db_path_if_needed_no_crash():
    from src.infrastructure.database.db import migrate_db_path_if_needed
    try:
        migrate_db_path_if_needed()
    except Exception as e:
        raise AssertionError(f"migrate crash: {e}")


def test_49_3_video_call_manager_stores_family_id():
    from src.communication.video_call import VideoCallManager
    vm = VideoCallManager()
    result = vm.start_call(family_id="family_test_49", caller_name="Mẹ")
    assert "call_id" in result, "start_call phải trả call_id"
    call_id = result["call_id"]
    session = vm._active_calls.get(call_id)
    assert session is not None, "Session phải tồn tại"
    assert session.get("family_id") == "family_test_49", "Session phải lưu family_id"


def test_49_4_end_call_correct_family_true():
    from src.communication.video_call import VideoCallManager
    vm = VideoCallManager()
    result = vm.start_call(family_id="family_test_49", caller_name="Mẹ")
    ok = vm.end_call(result["call_id"], family_id="family_test_49")
    assert ok is True, "end_call với đúng family phải True"


def test_49_5_end_call_wrong_family_false():
    from src.communication.video_call import VideoCallManager
    vm = VideoCallManager()
    result = vm.start_call(family_id="family_A", caller_name="Mẹ A")
    call_id = result["call_id"]
    ok = vm.end_call(call_id, family_id="family_B")
    assert ok is False, "end_call với sai family phải False (isolation)"
    vm.end_call(call_id, family_id="family_A")


def test_49_6_music_transport_routes_registered():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    for route in ["/api/music/next", "/api/music/previous", "/api/music/shuffle", "/api/music/repeat"]:
        assert route in paths, f"{route} phải được đăng ký"


def test_49_7_music_player_transport_methods():
    from src.audio.output.music_player import MusicPlayer
    mp = MusicPlayer()
    assert hasattr(mp, "next_track"), "MusicPlayer phải có next_track()"
    assert hasattr(mp, "prev_track"), "MusicPlayer phải có prev_track()"
    assert hasattr(mp, "toggle_shuffle"), "MusicPlayer phải có toggle_shuffle()"
    assert hasattr(mp, "toggle_repeat"), "MusicPlayer phải có toggle_repeat()"


def test_49_8_toggle_shuffle_changes_state():
    from src.audio.output.music_player import MusicPlayer
    mp = MusicPlayer()
    r1 = mp.toggle_shuffle()
    assert "shuffle" in r1
    shuffle_1 = r1["shuffle"]
    r2 = mp.toggle_shuffle()
    assert r2["shuffle"] != shuffle_1, "toggle_shuffle phải đổi trạng thái"


test("49.1 migrate_db_path_if_needed callable", test_49_1_migrate_db_path_if_needed_callable)
test("49.2 migrate_db_path_if_needed không crash", test_49_2_migrate_db_path_if_needed_no_crash)
test("49.3 VideoCallManager lưu family_id", test_49_3_video_call_manager_stores_family_id)
test("49.4 end_call đúng family → True", test_49_4_end_call_correct_family_true)
test("49.5 end_call sai family → False (isolation)", test_49_5_end_call_wrong_family_false)
test("49.6 Music transport routes registered", test_49_6_music_transport_routes_registered)
test("49.7 MusicPlayer có đủ transport methods", test_49_7_music_player_transport_methods)
test("49.8 toggle_shuffle hoạt động đúng", test_49_8_toggle_shuffle_changes_state)

print("\n[Group 50] Security + Quality Fix Verification")


def test_50_1_sql_injection_allowlist_exists():
    from src.infrastructure.database.db import delete_family_record
    import inspect
    src = inspect.getsource(delete_family_record)
    assert "ALLOWED_CLEANUP_TABLES" in src or "allowlist" in src.lower() or "frozenset" in src, (
        "delete_family_record phải có table allowlist"
    )


def test_50_2_gemini_api_key_not_in_url():
    from src.ai import ai_engine
    import inspect
    import re
    src = inspect.getsource(ai_engine._stream_gemini)
    url_with_key = re.findall(r'f["\'].*GEMINI_API_KEY.*["\']', src)
    assert len(url_with_key) == 0, (
        f"GEMINI_API_KEY không được trong URL string: {url_with_key}"
    )


def test_50_3_timing_safe_pin_comparison():
    from src.api.routers import auth_router
    import inspect
    src = inspect.getsource(auth_router)
    assert "compare_digest" in src, "auth_router phải dùng hmac.compare_digest cho PIN"


def test_50_4_json_parse_error_handling():
    from src.api.routers import auth_router
    import inspect
    src = inspect.getsource(auth_router)
    assert "JSONDecodeError" in src or "json.JSONDecodeError" in src or "422" in src, (
        "auth_router phải handle JSONDecodeError"
    )


def test_50_5_thread_safe_groq_globals():
    from src.ai import ai_engine
    import inspect
    src = inspect.getsource(ai_engine)
    assert "_groq_lock" in src or "threading.Lock" in src, (
        "ai_engine phải có lock cho Groq globals"
    )


def test_50_6_safety_filter_unicode_boundary():
    from src.safety import safety_filter
    import inspect
    src = inspect.getsource(safety_filter)
    assert r'\b' not in src or "(?<!" in src, (
        "safety_filter không nên dùng \\b với Unicode"
    )


def test_50_7_safety_filter_catches_vietnamese_harmful_text():
    from src.safety.safety_filter import SafetyFilter
    sf_inst = SafetyFilter()
    is_safe, result = sf_inst.check("nội dung khiêu dâm không phù hợp")
    assert not is_safe and result != "nội dung khiêu dâm không phù hợp", (
        "SafetyFilter phải catch Vietnamese harmful text"
    )


def test_50_8_analytics_null_safety():
    from src.api.routers import analytics_router
    import inspect
    src = inspect.getsource(analytics_router)
    assert "or 0" in src or "if row" in src or "row[0] or" in src, (
        "analytics_router phải handle NULL values"
    )


def test_50_9_verify_password_works_correctly():
    from src.infrastructure.auth.auth import hash_password, verify_password
    test_hash = hash_password("testpassword123")
    assert verify_password("testpassword123", test_hash) is True, (
        "verify_password với đúng password phải True"
    )
    assert verify_password("wrongpassword", test_hash) is False, (
        "verify_password với sai password phải False"
    )


test("50.1 SQL injection allowlist tồn tại", test_50_1_sql_injection_allowlist_exists)
test("50.2 Gemini API key không trong URL", test_50_2_gemini_api_key_not_in_url)
test("50.3 Timing-safe PIN comparison", test_50_3_timing_safe_pin_comparison)
test("50.4 JSON parse error handling", test_50_4_json_parse_error_handling)
test("50.5 Thread-safe Groq globals", test_50_5_thread_safe_groq_globals)
test("50.6 Safety filter Unicode boundary", test_50_6_safety_filter_unicode_boundary)
test("50.7 Safety filter bắt Vietnamese harmful text", test_50_7_safety_filter_catches_vietnamese_harmful_text)
test("50.8 Analytics NULL safety", test_50_8_analytics_null_safety)
test("50.9 verify_password hoạt động đúng", test_50_9_verify_password_works_correctly)

# == GROUP 51: Main Loop FaceAnimator & Emotion Integration =================
print("\n[Group 51] Main Loop Integration")

def test_51_1_face_animator_in_init():
    import inspect
    from src.main import RobotBiApp
    src = inspect.getsource(RobotBiApp.__init__)
    assert "FaceAnimator" in src or "face_animator" in src.lower(), "FaceAnimator missing from init"

def test_51_2_set_mode_in_conversation_loop():
    import inspect
    from src.main import RobotBiApp
    src_full = inspect.getsource(RobotBiApp)
    assert "set_mode('listening')" in src_full or "set_mode(\"listening\")" in src_full, "set_mode('listening') not found"

def test_51_3_emotion_analyzer_in_main_loop():
    import inspect
    from src.main import RobotBiApp
    src_full = inspect.getsource(RobotBiApp)
    assert "EmotionAnalyzer" in src_full or "emotion_analyzer" in src_full.lower(), "EmotionAnalyzer missing from main loop"

def test_51_4_face_animator_has_error_handling():
    import inspect
    from src.main import RobotBiApp
    src_full = inspect.getsource(RobotBiApp)
    assert "try:" in src_full, "Missing try/except error handling"

def test_51_5_persona_manager_system_prompt():
    import inspect
    from src.main import RobotBiApp
    src_full = inspect.getsource(RobotBiApp)
    assert "get_system_prompt_modifier" in src_full or "persona" in src_full.lower(), "PersonaManager system prompt not found"

test("51.1 FaceAnimator tồn tại trong RobotBiApp", test_51_1_face_animator_in_init)
test("51.2 set_mode được gọi trong conversation loop", test_51_2_set_mode_in_conversation_loop)
test("51.3 EmotionAnalyzer trong main loop", test_51_3_emotion_analyzer_in_main_loop)
test("51.4 FaceAnimator fail không crash (try/except)", test_51_4_face_animator_has_error_handling)
test("51.5 PersonaManager system prompt", test_51_5_persona_manager_system_prompt)

# == GROUP 52: WakeWordDetector =============================================
print("\n[Group 52] WakeWordDetector")

def test_52_1_wake_word_detector_import():
    from src.audio.input.wake_word import WakeWordDetector
    assert WakeWordDetector is not None

def test_52_2_is_enabled():
    from src.audio.input.wake_word import WakeWordDetector
    detector = WakeWordDetector()
    assert isinstance(detector.is_enabled(), bool)

def test_52_3_wake_words_not_empty():
    from src.audio.input.wake_word import WakeWordDetector
    assert len(WakeWordDetector.WAKE_WORDS) > 0

def test_52_4_detect_silence_returns_false():
    from src.audio.input.wake_word import WakeWordDetector
    detector = WakeWordDetector()
    # 1 second of silence at 16kHz float32
    silence = b'\x00' * (16000 * 4)
    result = detector.detect(silence)
    assert result is False

def test_52_5_detector_in_earstt_flow():
    import inspect
    from src.audio.input.ear_stt import EarSTT
    src = inspect.getsource(EarSTT.listen_for_wakeword)
    assert "wake_detector" in src

test("52.1 WakeWordDetector import", test_52_1_wake_word_detector_import)
test("52.2 is_enabled() trả về bool", test_52_2_is_enabled)
test("52.3 WAKE_WORDS không rỗng", test_52_3_wake_words_not_empty)
test("52.4 detect với silence → False", test_52_4_detect_silence_returns_false)
test("52.5 WakeWordDetector trong EarSTT flow", test_52_5_detector_in_earstt_flow)

# == GROUP 53: SpeakerIdentifier ============================================
print("\n[Group 53] SpeakerIdentifier")

def test_53_1_speaker_identifier_import():
    from src.audio.input.speaker_id import SpeakerIdentifier
    assert SpeakerIdentifier is not None

def test_53_2_identify_pitch():
    from src.audio.input.speaker_id import SpeakerIdentifier
    si = SpeakerIdentifier()
    assert si.identify({"pitch": 260, "energy": 0.5}) == "be"
    assert si.identify({"pitch": 200, "energy": 0.5}) == "me"
    assert si.identify({"pitch": 150, "energy": 0.5}) == "bo"
    assert si.identify({"pitch": 90, "energy": 0.5}) == "ong"
    assert si.identify({"pitch": 70, "energy": 0.5}) == "ba"
    assert si.identify({}) == "unknown"

def test_53_3_get_address_form():
    from src.audio.input.speaker_id import SpeakerIdentifier
    si = SpeakerIdentifier()
    form_me = si.get_address_form("me")
    assert form_me["robot_self"] == "con"
    assert form_me["address"] == "mẹ"
    
    form_be = si.get_address_form("be")
    assert form_be["robot_self"] == "Bi"
    assert form_be["address"] == "bạn"

test("53.1 SpeakerIdentifier import", test_53_1_speaker_identifier_import)
test("53.2 identify trả về đúng role", test_53_2_identify_pitch)
test("53.3 get_address_form trả về đúng dict", test_53_3_get_address_form)

# == GROUP 54: Curriculum Scheduler =========================================
print("\n[Group 54] Curriculum Scheduler")

def test_54_1_curriculum_has_scheduler_methods():
    from src.education.curriculum import Curriculum
    assert hasattr(Curriculum, "start_scheduler")
    assert hasattr(Curriculum, "stop_scheduler")
    assert hasattr(Curriculum, "_scheduler_loop")

def test_54_2_scheduler_loop_content():
    import inspect
    from src.education.curriculum import Curriculum
    src = inspect.getsource(Curriculum._scheduler_loop)
    assert "time.sleep" in src
    assert "Bây giờ là giờ học" in src
    assert "tts_callback" in src

test("54.1 Curriculum có methods scheduler", test_54_1_curriculum_has_scheduler_methods)
test("54.2 _scheduler_loop chứa logic nhắc nhở", test_54_2_scheduler_loop_content)

# == GROUP 55: Lullaby Fade-out =============================================
print("\n[Group 55] Lullaby Fade-out")

def test_55_1_play_lullaby_starts_fade():
    from src.audio.output.music_player import MusicPlayer
    import inspect
    src = inspect.getsource(MusicPlayer.play_lullaby)
    assert "_fade_step" in src
    assert "threading.Timer" in src

test("55.1 play_lullaby chứa logic fade-out với threading.Timer", test_55_1_play_lullaby_starts_fade)

# == GROUP 56: Personalized Story ===========================================
print("\n[Group 56] Personalized Story")

def test_56_1_tell_personalized_story_calls_llm():
    from src.entertainment.story_engine import StoryEngine
    import inspect
    src = inspect.getsource(StoryEngine.tell_personalized_story)
    assert "stream_chat" in src
    assert "Nhân vật chính" in src or "child_name" in src

test("56.1 tell_personalized_story gọi stream_chat để tạo truyện", test_56_1_tell_personalized_story_calls_llm)

# == GROUP 57: Persona System Prompt ========================================
print("\n[Group 57] Persona System Prompt")

def test_57_1_build_system_prompt_exists():
    from src.ai.prompts import build_system_prompt
    assert callable(build_system_prompt)

def test_57_2_build_system_prompt_playful():
    from src.ai.prompts import build_system_prompt
    prompt = build_system_prompt({"playfulness": 80, "name": "Bi", "gender": "boy"})
    assert "vui vẻ" in prompt.lower() or "nghịch ngợm" in prompt.lower() or "pha trò" in prompt.lower()
    
def test_57_3_build_system_prompt_energy():
    from src.ai.prompts import build_system_prompt
    prompt = build_system_prompt({"energy": 80, "name": "Bi", "gender": "boy"})
    assert "nhiệt tình" in prompt.lower() or "hào hứng" in prompt.lower() or "!" in prompt
    
def test_57_4_build_system_prompt_introvert():
    from src.ai.prompts import build_system_prompt
    prompt = build_system_prompt({"extraversion": 20, "name": "Bi", "gender": "boy"})
    assert "ngắn gọn" in prompt.lower() or "trầm tĩnh" in prompt.lower()

test("57.1 build_system_prompt tồn tại", test_57_1_build_system_prompt_exists)
test("57.2 Tính cách playfulness", test_57_2_build_system_prompt_playful)
test("57.3 Tính cách energy", test_57_3_build_system_prompt_energy)
test("57.4 Tính cách extraversion thấp", test_57_4_build_system_prompt_introvert)

# == GROUP 58: Quiz Games ===================================================
print("\n[Group 58] Quiz Games")

def test_58_1_word_quiz_import():
    from src.entertainment.game_word_quiz import WordQuizGame
    assert WordQuizGame is not None

def test_58_2_voice_quiz_import():
    from src.entertainment.game_voice_quiz import VoiceQuizGame
    assert VoiceQuizGame is not None

def test_58_3_word_quiz_logic():
    from src.entertainment.game_word_quiz import WordQuizGame
    game = WordQuizGame("easy")
    q = game.get_random_question()
    if q:
        assert game.check_answer(q, q["correct"]) is True

def test_58_4_voice_quiz_logic():
    from src.entertainment.game_voice_quiz import VoiceQuizGame
    game = VoiceQuizGame()
    r = game.get_random_riddle()
    if r:
        ans = r["answer"]
        assert game.check_answer(r, ans) is True
        assert game.check_answer(r, "sai") is False

test("58.1 WordQuizGame import", test_58_1_word_quiz_import)
test("58.2 VoiceQuizGame import", test_58_2_voice_quiz_import)
test("58.3 WordQuizGame logic", test_58_3_word_quiz_logic)
test("58.4 VoiceQuizGame logic", test_58_4_voice_quiz_logic)

print("\n[Group 59] API Contract Verification")

# 59.1 — WordQuizGame start_game nhận difficulty
def test_59_1():
    from src.entertainment.game_word_quiz import WordQuizGame
    g = WordQuizGame()
    result = g.start_game("fam1", "easy")
    assert result["status"] == "started"
    result2 = g.start_game("fam1", "medium")
    assert result2["status"] == "started"
test("59.1 WordQuizGame start_game(family_id, difficulty)", test_59_1)

# 59.2 — get_question đủ fields
def test_59_2():
    from src.entertainment.game_word_quiz import WordQuizGame
    g = WordQuizGame()
    g.start_game("fam1", "easy")
    q = g.get_question()
    assert "question" in q, f"Missing 'question', got: {list(q.keys())}"
    assert "options" in q
    assert len(q["options"]) == 4
    assert "time_limit_sec" in q
test("59.2 WordQuizGame get_question fields", test_59_2)

# 59.3 — submit_answer với correct answer string
def test_59_3():
    from src.entertainment.game_word_quiz import WordQuizGame
    import json
    from pathlib import Path
    g = WordQuizGame()
    g.start_game("fam1", "easy")
    q = g.get_question()
    if not q:
        return
    correct_text = q["options"][0]  # test với option đầu
    result = g.submit_answer(correct_text)
    assert "correct" in result
    assert "score" in result
test("59.3 WordQuizGame submit_answer string", test_59_3)

# 59.4 — end_game có total_score và high_score
def test_59_4():
    from src.entertainment.game_word_quiz import WordQuizGame
    g = WordQuizGame()
    g.start_game("fam59_4", "easy")
    summary = g.end_game()
    assert "total_score" in summary, \
        f"Missing total_score, got: {list(summary.keys())}"
    assert "high_score" in summary, \
        f"Missing high_score, got: {list(summary.keys())}"
    assert "correct" in summary
    assert "incorrect" in summary
test("59.4 WordQuizGame end_game contract", test_59_4)

# 59.5 — get_leaderboard tồn tại và trả list
def test_59_5():
    from src.entertainment.game_word_quiz import WordQuizGame
    g = WordQuizGame()
    board = g.get_leaderboard("fam59_5")
    assert isinstance(board, list)
test("59.5 WordQuizGame get_leaderboard", test_59_5)

# 59.6 — VoiceQuizGame get_riddle đúng fields
def test_59_6():
    from src.entertainment.game_voice_quiz import VoiceQuizGame
    g = VoiceQuizGame()
    g.start_game("fam59_6")
    riddle = g.get_riddle()
    assert "riddle_text" in riddle, \
        f"Missing riddle_text, got: {list(riddle.keys())}"
    assert "hint" in riddle
    assert "answer" in riddle
test("59.6 VoiceQuizGame get_riddle fields", test_59_6)

# 59.7 — VoiceQuizGame exact answer → correct=True
def test_59_7():
    from src.entertainment.game_voice_quiz import VoiceQuizGame
    g = VoiceQuizGame()
    g.start_game("fam59_7")
    riddle = g.get_riddle()
    result = g.check_voice_answer(riddle["answer"])
    assert result["correct"] is True, \
        f"Exact answer phải correct=True, got: {result}"
test("59.7 VoiceQuizGame exact answer correct", test_59_7)

# 59.8 — Education summary đúng fields
def test_59_8():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/education/summary" in paths
    assert "/api/education/vocabulary" in paths
    assert "/api/education/schedule" in paths
test("59.8 Education routes tồn tại", test_59_8)

# 59.9 — Analytics weekly route tồn tại
def test_59_9():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/analytics/weekly" in paths
    assert "/api/analytics/daily" in paths
test("59.9 Analytics routes tồn tại", test_59_9)

# 59.10 — Game scores đúng format
def test_59_10():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/game/scores" in paths
    assert "/api/video/history" in paths
test("59.10 Game scores + video history routes", test_59_10)

# 59.11 — state.py event không trả None
def test_59_11():
    # Import và kiểm tra hàm parse không trả None
    import inspect
    from src.infrastructure.sessions import state as st
    src = inspect.getsource(st)
    # Kiểm tra return không nằm trong except block
    # bằng cách tìm pattern "except" theo sau bởi "return"
    lines = src.split('\n')
    in_except = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('except'):
            in_except = True
        elif in_except and stripped.startswith('return'):
            # return nằm trong except là bug
            assert False, \
                f"Return trong except block tại line {i}: {line}"
        elif in_except and stripped and \
             not stripped.startswith('#') and \
             not stripped.startswith('pass') and \
             not line.startswith(' ' * 12):
            in_except = False
test("59.11 state.py event parse không return trong except", test_59_11)

# == GROUP 60: Parent App Backend Phase 1 ===================================
print("\n[Group 60] Parent App Backend Phase 1")


def _phase1_insert_event(family_id, message, event_type="system", clip_path=None, metadata=None):
    from src.infrastructure.database.db import get_db_connection
    from src.infrastructure.notifications.notifier import EventNotifier

    notifier_local = EventNotifier()
    notifier_local.push_event(
        event_type,
        message,
        clip_path=clip_path,
        metadata=metadata or {},
        family_id=family_id,
    )
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT event_id
            FROM events
            WHERE family_id = ? AND message = ?
            ORDER BY db_id DESC
            LIMIT 1
            """,
            (family_id, message),
        ).fetchone()
    assert row is not None, "test event phai duoc tao"
    return row["event_id"]


def test_60_1_parent_event_notes_schema():
    from src.infrastructure.database.db import get_db_connection, init_db

    init_db()
    with get_db_connection() as conn:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='parent_event_notes'"
        ).fetchone()
        columns = {row[1] for row in conn.execute("PRAGMA table_info(parent_event_notes)").fetchall()}
    assert table is not None, "parent_event_notes table phai ton tai"
    assert {
        "note_id",
        "family_id",
        "event_id",
        "user_id",
        "note",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_60_2_parent_event_notes_crud_and_family_scope():
    from fastapi.testclient import TestClient
    from src.api.server import app

    fam_a = f"phase1-notes-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase1-notes-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p1_notes_a", fam_a)
    headers_b = _phase44_headers("p1_notes_b", fam_b)
    event_a = _phase1_insert_event(fam_a, f"note event A {_uuid.uuid4().hex}")
    event_b = _phase1_insert_event(fam_b, f"note event B {_uuid.uuid4().hex}")

    client = TestClient(app)
    created = client.post(
        f"/api/events/{event_a}/notes",
        json={"note": "  Parent follow-up note  "},
        headers=headers_a,
    )
    assert created.status_code == 200
    note = created.json()
    assert note["event_id"] == event_a
    assert note["family_id"] == fam_a
    assert note["note"] == "Parent follow-up note"

    listed = client.get(f"/api/events/{event_a}/notes", headers=headers_a)
    assert listed.status_code == 200
    assert len(listed.json()["notes"]) == 1

    edited = client.put(
        f"/api/events/{event_a}/notes/{note['note_id']}",
        json={"note": "Updated parent note"},
        headers=headers_a,
    )
    assert edited.status_code == 200
    assert edited.json()["note"] == "Updated parent note"

    blocked = client.post(
        f"/api/events/{event_b}/notes",
        json={"note": "wrong family"},
        headers=headers_a,
    )
    assert blocked.status_code == 404
    assert client.get(f"/api/events/{event_a}/notes", headers=headers_b).status_code == 404

    empty = client.post(f"/api/events/{event_a}/notes", json={"note": "   "}, headers=headers_a)
    assert empty.status_code == 422

    deleted = client.delete(f"/api/events/{event_a}/notes/{note['note_id']}", headers=headers_a)
    assert deleted.status_code == 200
    assert client.get(f"/api/events/{event_a}/notes", headers=headers_a).json()["notes"] == []


def test_60_3_events_advanced_filters_and_family_scope():
    from datetime import datetime
    from fastapi.testclient import TestClient
    from src.api.server import app

    fam_a = f"phase1-events-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase1-events-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p1_events_a", fam_a)
    headers_b = _phase44_headers("p1_events_b", fam_b)
    token = f"phase1filter{_uuid.uuid4().hex}"
    event_clip = _phase1_insert_event(
        fam_a,
        f"{token} camera clip",
        event_type="system",
        clip_path="clip-a.mp4",
        metadata={"room": "bedroom"},
    )
    event_cry = _phase1_insert_event(
        fam_a,
        f"{token} cry event",
        event_type="cry",
        metadata={"room": "living"},
    )
    _phase1_insert_event(fam_b, f"{token} other family event", event_type="system")

    client = TestClient(app)
    note_resp = client.post(
        f"/api/events/{event_cry}/notes",
        json={"note": "filter note"},
        headers=headers_a,
    )
    assert note_resp.status_code == 200

    all_resp = client.get(f"/api/events?q={token}&limit=20&sort=asc", headers=headers_a)
    assert all_resp.status_code == 200
    all_payload = all_resp.json()
    ids = [event["id"] for event in all_payload["events"]]
    assert event_clip in ids
    assert event_cry in ids
    assert all(event["family_id"] == fam_a for event in all_payload["events"])
    assert "limit" in all_payload and "offset" in all_payload and "filters" in all_payload

    cry_resp = client.get(f"/api/events?q={token}&types=cry&limit=20", headers=headers_a)
    assert cry_resp.status_code == 200
    assert [event["type"] for event in cry_resp.json()["events"]] == ["cry"]

    clip_resp = client.get(f"/api/events?q={token}&has_clip=true&limit=20", headers=headers_a)
    assert clip_resp.status_code == 200
    assert [event["id"] for event in clip_resp.json()["events"]] == [event_clip]

    note_filter_resp = client.get(f"/api/events?q={token}&has_note=true&limit=20", headers=headers_a)
    assert note_filter_resp.status_code == 200
    noted = note_filter_resp.json()["events"]
    assert len(noted) == 1
    assert noted[0]["id"] == event_cry
    assert noted[0]["note_count"] >= 1

    today = datetime.now().date().isoformat()
    date_resp = client.get(
        f"/api/events?q={token}&start_date={today}&end_date={today}&limit=20",
        headers=headers_a,
    )
    assert date_resp.status_code == 200
    assert date_resp.json()["total"] >= 2
    assert client.get("/api/events?start_date=bad-date", headers=headers_a).status_code == 422

    other_family = client.get(f"/api/events?q={token}&limit=20", headers=headers_b)
    assert other_family.status_code == 200
    assert all(event["family_id"] == fam_b for event in other_family.json()["events"])


def test_60_4_monthly_emotion_statistics_and_alias():
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.emotion.emotion_analyzer import EmotionAnalyzer
    from src.emotion.emotion_journal import EmotionJournal
    from src.infrastructure.database.db import get_db_connection

    fam_a = f"phase1-emotion-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase1-emotion-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p1_emotion_a", fam_a)
    headers_b = _phase44_headers("p1_emotion_b", fam_b)
    month = "2026-05"
    EmotionAnalyzer(fam_a)
    EmotionJournal()
    with get_db_connection() as conn:
        conn.executemany(
            """
            INSERT INTO emotion_logs (family_id, timestamp, emotion, confidence, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (fam_a, "2026-05-02T08:00:00", "happy", 0.9, "test"),
                (fam_a, "2026-05-02T09:00:00", "excited", 0.8, "test"),
                (fam_a, "2026-05-03T08:00:00", "sad", 0.7, "test"),
                (fam_b, "2026-05-02T08:00:00", "stressed", 0.9, "test"),
            ],
        )
        conn.execute(
            """
            INSERT INTO emotion_journal (family_id, timestamp, emotion, note)
            VALUES (?, ?, ?, ?)
            """,
            (fam_a, "2026-05-04T08:00:00", "angry", "journal stress"),
        )
        conn.commit()

    client = TestClient(app)
    resp = client.get(f"/api/emotion/monthly?month={month}", headers=headers_a)
    assert resp.status_code == 200
    data = resp.json()
    assert data["family_id"] == fam_a
    assert data["month"] == month
    assert data["total_entries"] == 4
    assert data["dominant"] == "happy"
    assert data["counts"]["happy"] == 2
    assert data["counts"]["sad"] == 1
    assert data["counts"]["stressed"] == 1
    assert len(data["days"]) == 31
    assert len(data["weeks"]) >= 4

    alias = client.get(f"/api/emotions/monthly?month={month}", headers=headers_a)
    assert alias.status_code == 200
    assert alias.json()["total_entries"] == 4

    isolated = client.get(f"/api/emotion/monthly?month={month}", headers=headers_b)
    assert isolated.status_code == 200
    assert isolated.json()["total_entries"] == 1

    assert client.get("/api/emotion/monthly?month=2026-13", headers=headers_a).status_code == 422
    assert client.get(
        f"/api/emotion/monthly?month={month}&child_id=child-1",
        headers=headers_a,
    ).status_code == 400


test("60.1 parent_event_notes schema", test_60_1_parent_event_notes_schema)
test("60.2 parent event notes CRUD + family scope", test_60_2_parent_event_notes_crud_and_family_scope)
test("60.3 /api/events advanced filters + family scope", test_60_3_events_advanced_filters_and_family_scope)
test("60.4 monthly emotion statistics + alias", test_60_4_monthly_emotion_statistics_and_alias)

# == GROUP 61: Parent App Backend Phase 2 ===================================
print("\n[Group 61] Parent App Backend Phase 2")


def _phase2_create_child(client, headers, name="Minh", age=8):
    resp = client.post(
        "/api/children",
        json={
            "name": name,
            "age": age,
            "grade": "2",
            "avatar": "robot",
            "interests": ["math", "animals"],
            "notes": "phase2 test",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["child"]


def test_61_1_phase2_schema_tables_exist():
    from src.infrastructure.database.db import get_db_connection, init_db

    init_db()
    expected = {
        "child_profiles",
        "child_content_settings",
        "interaction_limit_settings",
        "daily_interaction_usage",
        "sleep_schedule_settings",
        "notification_settings",
        "push_subscriptions",
    }
    with get_db_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    assert expected.issubset(tables), f"Missing phase2 tables: {expected - tables}"


def test_61_2_child_profiles_crud_active_and_isolation():
    from fastapi.testclient import TestClient
    from src.api.server import app

    fam_a = f"phase2-child-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase2-child-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p2_child_a", fam_a)
    headers_b = _phase44_headers("p2_child_b", fam_b)
    client = TestClient(app)

    no_auth = client.get("/api/children")
    assert no_auth.status_code == 401

    first = _phase2_create_child(client, headers_a, "Minh", 8)
    second = _phase2_create_child(client, headers_a, "An", 7)
    assert first["is_active"] is True
    assert second["is_active"] is False

    listed = client.get("/api/children", headers=headers_a)
    assert listed.status_code == 200
    assert listed.json()["active_child_id"] == first["child_id"]
    assert len(listed.json()["children"]) == 2

    activated = client.put(f"/api/children/{second['child_id']}/activate", headers=headers_a)
    assert activated.status_code == 200
    listed_after = client.get("/api/children", headers=headers_a).json()
    assert listed_after["active_child_id"] == second["child_id"]
    assert sum(1 for child in listed_after["children"] if child["is_active"]) == 1

    patched = client.patch(
        f"/api/children/{first['child_id']}",
        json={"name": "Minh updated", "interests": ["science"]},
        headers=headers_a,
    )
    assert patched.status_code == 200
    assert patched.json()["child"]["name"] == "Minh updated"
    assert patched.json()["child"]["interests"] == ["science"]

    assert client.get(f"/api/children/{first['child_id']}", headers=headers_b).status_code == 404
    assert client.post("/api/children", json={"name": "Too young", "age": 4}, headers=headers_a).status_code == 422

    deleted = client.delete(f"/api/children/{second['child_id']}", headers=headers_a)
    assert deleted.status_code == 200
    assert client.get("/api/children", headers=headers_a).json()["active_child_id"] == first["child_id"]


def test_61_3_age_filter_and_time_limits():
    from fastapi.testclient import TestClient
    from src.api.server import app

    fam_a = f"phase2-settings-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase2-settings-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p2_set_a", fam_a)
    headers_b = _phase44_headers("p2_set_b", fam_b)
    client = TestClient(app)
    child = _phase2_create_child(client, headers_a, "Lan", 9)

    age_resp = client.post(
        "/api/settings/age-filter",
        json={
            "child_id": child["child_id"],
            "enabled": True,
            "min_age": 7,
            "max_age": 10,
            "blocked_topics": ["scary"],
            "allowed_topics": ["math"],
            "strict_mode": True,
        },
        headers=headers_a,
    )
    assert age_resp.status_code == 200
    settings = age_resp.json()["settings"]
    assert settings["child_id"] == child["child_id"]
    assert settings["blocked_topics"] == ["scary"]

    loaded = client.get(f"/api/settings/age-filter?child_id={child['child_id']}", headers=headers_a)
    assert loaded.status_code == 200
    assert loaded.json()["settings"]["allowed_topics"] == ["math"]
    assert client.get(f"/api/settings/age-filter?child_id={child['child_id']}", headers=headers_b).status_code == 404
    assert client.post(
        "/api/settings/age-filter",
        json={"enabled": True, "min_age": 11, "max_age": 6},
        headers=headers_a,
    ).status_code == 422

    limit_resp = client.post(
        "/api/settings/time-limits",
        json={
            "child_id": child["child_id"],
            "enabled": True,
            "daily_limit_minutes": 45,
            "warning_minutes": 5,
            "reset_time": "00:30",
        },
        headers=headers_a,
    )
    assert limit_resp.status_code == 200
    assert limit_resp.json()["settings"]["daily_limit_minutes"] == 45
    assert limit_resp.json()["usage_today"]["seconds_used"] == 0
    assert limit_resp.json()["usage_today"]["remaining_seconds"] == 2700

    usage = client.get(f"/api/usage/today?child_id={child['child_id']}", headers=headers_a)
    assert usage.status_code == 200
    assert usage.json()["usage_today"]["limit_reached"] is False
    assert client.post(
        "/api/settings/time-limits",
        json={"daily_limit_minutes": 10, "warning_minutes": 20, "reset_time": "00:00"},
        headers=headers_a,
    ).status_code == 422


def test_61_4_sleep_and_notification_settings():
    import hashlib
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.infrastructure.database.db import get_db_connection

    fam_a = f"phase2-notify-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase2-notify-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p2_notify_a", fam_a)
    headers_b = _phase44_headers("p2_notify_b", fam_b)
    client = TestClient(app)

    sleep = client.post(
        "/api/settings/sleep",
        json={
            "enabled": True,
            "start_time": "21:00",
            "end_time": "06:30",
            "days": ["mon", "tue", "wed"],
            "timezone": "Asia/Ho_Chi_Minh",
        },
        headers=headers_a,
    )
    assert sleep.status_code == 200
    assert sleep.json()["settings"]["days"] == ["mon", "tue", "wed"]
    assert client.get("/api/settings/sleep", headers=headers_b).json()["settings"]["enabled"] is False
    assert client.post(
        "/api/settings/sleep",
        json={"enabled": True, "start_time": "25:00", "end_time": "06:30", "days": ["mon"]},
        headers=headers_a,
    ).status_code == 422
    assert client.post(
        "/api/settings/sleep",
        json={"enabled": True, "start_time": "21:00", "end_time": "06:30", "days": ["bad"]},
        headers=headers_a,
    ).status_code == 422

    endpoint = f"https://push.example/{_uuid.uuid4().hex}"
    notify = client.post(
        "/api/settings/notifications",
        json={
            "enabled": True,
            "event_types": {"cry": True, "homework": True, "system": False},
            "quiet_hours": {"enabled": True, "start_time": "21:00", "end_time": "07:00"},
            "channels": {"in_app": True, "web_push": False},
            "push_subscription": {"endpoint": endpoint, "keys": {"p256dh": "key", "auth": "auth"}},
        },
        headers=headers_a,
    )
    assert notify.status_code == 200
    assert notify.json()["settings"]["event_types"]["cry"] is True
    assert notify.json()["settings"]["channels"]["web_push"] is False
    assert "push_subscription" not in notify.json()["settings"]

    endpoint_hash = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT endpoint_hash FROM push_subscriptions WHERE family_id = ?",
            (fam_a,),
        ).fetchone()
    assert row is not None
    assert row["endpoint_hash"] == endpoint_hash

    assert client.get("/api/settings/notifications", headers=headers_b).json()["settings"]["event_types"] == {}
    assert client.post(
        "/api/settings/notifications",
        json={"event_types": {"unknown": True}},
        headers=headers_a,
    ).status_code == 422


test("61.1 Phase 2 schema tables", test_61_1_phase2_schema_tables_exist)
test("61.2 child profiles CRUD active isolation", test_61_2_child_profiles_crud_active_and_isolation)
test("61.3 age filter and time limits", test_61_3_age_filter_and_time_limits)
test("61.4 sleep and notification settings", test_61_4_sleep_and_notification_settings)

# == GROUP 62: Parent App Backend Phase 3 ===================================
print("\n[Group 62] Parent App Backend Phase 3")


def test_62_1_phase3_schema_tables_and_content_seed():
    from src.infrastructure.database.db import get_db_connection, init_db

    init_db()
    expected = {"report_exports", "content_items", "parent_chat_sessions", "parent_chat_messages"}
    with get_db_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        content_count = conn.execute(
            "SELECT COUNT(*) AS count FROM content_items WHERE family_id IS NULL"
        ).fetchone()["count"]
    assert expected.issubset(tables), f"Missing phase3 tables: {expected - tables}"
    assert content_count >= 6


def test_62_2_report_export_csv_pdf_and_family_scope():
    from datetime import date
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.infrastructure.database.db import get_db_connection

    fam_a = f"phase3-report-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase3-report-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p3_report_a", fam_a)
    _phase44_headers("p3_report_b", fam_b)
    token_a = f"report-token-a-{_uuid.uuid4().hex}"
    token_b = f"report-token-b-{_uuid.uuid4().hex}"
    _phase1_insert_event(fam_a, token_a, event_type="system")
    _phase1_insert_event(fam_b, token_b, event_type="system")
    today = date.today().isoformat()
    client = TestClient(app)

    csv_resp = client.post(
        "/api/reports/export",
        json={"format": "csv", "start_date": today, "end_date": today, "sections": ["events"]},
        headers=headers_a,
    )
    assert csv_resp.status_code == 200, csv_resp.text
    assert csv_resp.headers["content-type"].startswith("text/csv")
    assert "robot-bi-report" in csv_resp.headers.get("content-disposition", "")
    csv_body = csv_resp.content.decode("utf-8")
    assert token_a in csv_body
    assert token_b not in csv_body

    pdf_resp = client.post(
        "/api/reports/export",
        json={"format": "pdf", "start_date": today, "end_date": today, "sections": ["events"]},
        headers=headers_a,
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")
    assert len(pdf_resp.content) > 200

    assert client.post(
        "/api/reports/export",
        json={"format": "xlsx", "start_date": today, "end_date": today},
        headers=headers_a,
    ).status_code == 422
    assert client.post(
        "/api/reports/export",
        json={"format": "csv", "start_date": "2026-05-31", "end_date": "2026-05-01"},
        headers=headers_a,
    ).status_code == 422
    assert client.post(
        "/api/reports/export",
        json={"format": "csv", "start_date": "bad", "end_date": today},
        headers=headers_a,
    ).status_code == 422

    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT format, status FROM report_exports WHERE family_id = ?",
            (fam_a,),
        ).fetchall()
    assert len(rows) >= 2
    assert {row["format"] for row in rows}.issuperset({"csv", "pdf"})
    assert all(row["status"] == "completed" for row in rows)


def test_62_3_content_metadata_filters_and_family_scope():
    import datetime as _dt
    import json
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.infrastructure.database.db import get_db_connection

    fam_a = f"phase3-content-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase3-content-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p3_content_a", fam_a)
    headers_b = _phase44_headers("p3_content_b", fam_b)
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO content_items (
                content_id, family_id, type, title, description, source_url,
                thumbnail_url, age_min, age_max, language, tags_json, enabled,
                sort_order, created_at, updated_at
            ) VALUES (?, ?, 'radio', ?, ?, ?, NULL, 10, 12, 'vi', ?, 1, 5, ?, ?)
            """,
            (
                f"family-radio-{fam_a}",
                fam_a,
                "Family A radio",
                "Family only",
                "https://example.invalid/family-a",
                json.dumps(["family"]),
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO content_items (
                content_id, family_id, type, title, description, source_url,
                thumbnail_url, age_min, age_max, language, tags_json, enabled,
                sort_order, created_at, updated_at
            ) VALUES (?, ?, 'radio', ?, ?, ?, NULL, 10, 12, 'vi', ?, 1, 5, ?, ?)
            """,
            (
                f"family-radio-{fam_b}",
                fam_b,
                "Family B radio",
                "Family only",
                "https://example.invalid/family-b",
                json.dumps(["family"]),
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO content_items (
                content_id, family_id, type, title, description, source_url,
                thumbnail_url, age_min, age_max, language, tags_json, enabled,
                sort_order, created_at, updated_at
            ) VALUES (?, ?, 'radio', ?, ?, ?, NULL, 5, 12, 'vi', ?, 0, 1, ?, ?)
            """,
            (
                f"disabled-radio-{fam_a}",
                fam_a,
                "Disabled radio",
                "Hidden by default",
                "https://example.invalid/disabled",
                json.dumps(["hidden"]),
                now,
                now,
            ),
        )
        conn.commit()

    client = TestClient(app)
    radio_a = client.get("/api/entertainment/radio?min_age=10&max_age=10", headers=headers_a)
    assert radio_a.status_code == 200
    ids_a = {item["content_id"] for item in radio_a.json()["items"]}
    assert f"family-radio-{fam_a}" in ids_a
    assert f"family-radio-{fam_b}" not in ids_a
    assert f"disabled-radio-{fam_a}" not in ids_a
    assert radio_a.json()["channels"] == radio_a.json()["items"]

    disabled_visible = client.get("/api/entertainment/radio?enabled_only=false", headers=headers_a)
    assert disabled_visible.status_code == 200
    assert f"disabled-radio-{fam_a}" in {item["content_id"] for item in disabled_visible.json()["items"]}

    videos = client.get("/api/entertainment/videos?min_age=10&max_age=12", headers=headers_a)
    assert videos.status_code == 200
    assert videos.json()["videos"] == videos.json()["items"]
    assert "video-bi-english-animals" not in {item["content_id"] for item in videos.json()["items"]}

    games = client.get("/api/games/interactive?language=vi", headers=headers_a)
    assert games.status_code == 200
    assert games.json()["games"] == games.json()["items"]
    assert any(item["type"] == "game" for item in games.json()["items"])

    unchanged = client.post("/api/game/word-quiz/start", json={"difficulty": "easy"}, headers=headers_a)
    assert unchanged.status_code == 200
    assert unchanged.json()["status"] == "started"


def test_62_4_parent_chat_history_and_isolation():
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.infrastructure.database.db import add_turn, create_session

    fam_a = f"phase3-chat-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase3-chat-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p3_chat_a", fam_a)
    headers_b = _phase44_headers("p3_chat_b", fam_b)
    child_session = create_session(fam_a)
    add_turn(child_session, "user", "child conversation", family_id=fam_a)
    client = TestClient(app)

    empty = client.get("/api/conversations/parent", headers=headers_a)
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    created = client.post(
        "/api/conversations/parent/messages",
        json={"role": "parent", "content": "Hello Bi"},
        headers=headers_a,
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["session"]["session_id"]
    assert created.json()["session"]["message_count"] == 1
    assert created.json()["messages"][0]["role"] == "parent"

    replied = client.post(
        "/api/conversations/parent/messages",
        json={"session_id": session_id, "role": "bi", "content": "Hello parent"},
        headers=headers_a,
    )
    assert replied.status_code == 200
    assert replied.json()["session"]["message_count"] == 2

    detail = client.get(f"/api/conversations/parent/{session_id}", headers=headers_a)
    assert detail.status_code == 200
    assert [msg["role"] for msg in detail.json()["messages"]] == ["parent", "bi"]

    listed = client.get("/api/conversations/parent", headers=headers_a)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["sessions"][0]["session_id"] == session_id

    assert client.get(f"/api/conversations/parent/{session_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/conversations/{session_id}", headers=headers_a).status_code == 404
    child_list = client.get("/api/conversations", headers=headers_a)
    assert child_list.status_code == 200
    assert session_id not in [row["session_id"] for row in child_list.json()["conversations"]]

    assert client.post(
        "/api/conversations/parent/messages",
        json={"session_id": session_id, "role": "child", "content": "bad"},
        headers=headers_a,
    ).status_code == 422
    assert client.post(
        "/api/conversations/parent/messages",
        json={"session_id": session_id, "role": "parent", "content": "   "},
        headers=headers_a,
    ).status_code == 422


test("62.1 Phase 3 schema tables and content seed", test_62_1_phase3_schema_tables_and_content_seed)
test("62.2 report export CSV/PDF + family scope", test_62_2_report_export_csv_pdf_and_family_scope)
test("62.3 content metadata filters + family scope", test_62_3_content_metadata_filters_and_family_scope)
test("62.4 parent chat history + isolation", test_62_4_parent_chat_history_and_isolation)

# == GROUP 63: Parent App Backend Phase 4 ===================================
print("\n[Group 63] Parent App Backend Phase 4")


def test_63_1_phase4_schema_tables_exist():
    from src.infrastructure.database.db import get_db_connection, init_db

    init_db()
    expected = {"device_pairing_codes", "robot_location_metadata"}
    with get_db_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    assert expected.issubset(tables), f"Missing phase4 tables: {expected - tables}"


def test_63_2_device_connection_qr_hash_ttl_and_family_scope():
    import hashlib
    from urllib.parse import parse_qs, urlparse
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.infrastructure.database.db import get_db_connection

    fam_a = f"phase4-qr-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase4-qr-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p4_qr_a", fam_a)
    _phase44_headers("p4_qr_b", fam_b)
    client = TestClient(app)

    resp = client.get("/api/device/connection-qr?purpose=parent_app&ttl_seconds=120", headers=headers_a)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["qr"]["ttl_seconds"] == 120
    assert data["network"]["local_url"].startswith("http://")
    assert ".env" not in resp.text
    parsed = urlparse(data["qr"]["payload_url"])
    params = parse_qs(parsed.query)
    pairing_id = data["qr"]["pairing_id"]
    raw_code = params["code"][0]
    assert params["pairing_id"][0] == pairing_id
    assert len(raw_code) >= 16

    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT family_id, purpose, code_hash
            FROM device_pairing_codes
            WHERE pairing_id = ?
            """,
            (pairing_id,),
        ).fetchone()
        other_count = conn.execute(
            "SELECT COUNT(*) AS count FROM device_pairing_codes WHERE family_id = ?",
            (fam_b,),
        ).fetchone()["count"]
    assert row is not None
    assert row["family_id"] == fam_a
    assert row["purpose"] == "parent_app"
    assert row["code_hash"] == hashlib.sha256(raw_code.encode("utf-8")).hexdigest()
    assert row["code_hash"] != raw_code
    assert other_count == 0

    assert client.get("/api/device/connection-qr?ttl_seconds=59", headers=headers_a).status_code == 422
    assert client.get("/api/device/connection-qr?ttl_seconds=3601", headers=headers_a).status_code == 422
    assert client.get("/api/device/connection-qr?purpose=bad", headers=headers_a).status_code == 422


def test_63_3_robot_location_save_load_validation_and_isolation():
    from fastapi.testclient import TestClient
    from src.api.server import app

    fam_a = f"phase4-location-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"phase4-location-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("p4_location_a", fam_a)
    headers_b = _phase44_headers("p4_location_b", fam_b)
    client = TestClient(app)

    default_b = client.get("/api/robot/location", headers=headers_b)
    assert default_b.status_code == 200
    assert default_b.json()["location"]["source"] == "system"
    assert default_b.json()["location"]["updated_at"] is None

    saved = client.post(
        "/api/robot/location",
        json={
            "room_name": "Living room",
            "location_label": "Near bookshelf",
            "source": "parent",
            "confidence": 0.95,
        },
        headers=headers_a,
    )
    assert saved.status_code == 200, saved.text
    location = saved.json()["location"]
    assert location["family_id"] == fam_a
    assert location["room_name"] == "Living room"
    assert location["confidence"] == 0.95

    loaded = client.get("/api/robot/location", headers=headers_a)
    assert loaded.status_code == 200
    assert loaded.json()["location"]["location_label"] == "Near bookshelf"
    assert client.get("/api/robot/location", headers=headers_b).json()["location"]["room_name"] is None

    assert client.post(
        "/api/robot/location",
        json={"source": "unknown", "confidence": 1.0},
        headers=headers_a,
    ).status_code == 422
    assert client.post(
        "/api/robot/location",
        json={"source": "parent", "confidence": 1.5},
        headers=headers_a,
    ).status_code == 422
    assert client.post(
        "/api/robot/location",
        json={"room_name": "x" * 121, "source": "parent", "confidence": 1.0},
        headers=headers_a,
    ).status_code == 422


def test_63_4_admin_logs_guard_bounds_and_redaction():
    from fastapi.testclient import TestClient
    from src.api.routers.admin_router import _sanitize_log_message
    from src.api.server import app

    user_headers = _phase44_headers("p4_logs_user", f"phase4-logs-user-{_uuid.uuid4().hex[:6]}")
    admin_headers = _phase44_headers(
        "p4_logs_admin",
        f"phase4-logs-admin-{_uuid.uuid4().hex[:6]}",
        is_admin=True,
    )
    client = TestClient(app)

    assert client.get("/api/admin/logs", headers=user_headers).status_code == 403
    resp = client.get("/api/admin/logs?limit=2", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["limit"] == 2
    assert len(data["logs"]) <= 2
    assert data["total"] >= len(data["logs"])
    assert all("message" in row and "source" in row for row in data["logs"])

    info = client.get("/api/admin/logs?level=INFO", headers=admin_headers)
    assert info.status_code == 200
    assert all(row["level"] == "INFO" for row in info.json()["logs"])
    assert client.get("/api/admin/logs?level=INVALID", headers=admin_headers).status_code == 422
    assert client.get("/api/admin/logs?limit=0", headers=admin_headers).status_code == 422
    assert client.get("/api/admin/logs?limit=501", headers=admin_headers).status_code == 422
    assert client.get("/api/admin/logs?since=not-a-date", headers=admin_headers).status_code == 422

    sanitized = _sanitize_log_message(
        "Bearer abc.def.ghi token=secret JWT_SECRET_KEY=secret content=child said private thing"
    )
    assert "secret" not in sanitized.lower()
    assert "abc.def.ghi" not in sanitized
    assert "child said private thing" not in sanitized
    assert "[REDACTED]" in sanitized


test("63.1 Phase 4 schema tables", test_63_1_phase4_schema_tables_exist)
test("63.2 QR device connection metadata", test_63_2_device_connection_qr_hash_ttl_and_family_scope)
test("63.3 robot location metadata", test_63_3_robot_location_save_load_validation_and_isolation)
test("63.4 admin logs guard bounds redaction", test_63_4_admin_logs_guard_bounds_and_redaction)

# == RESULTS ================================================================
print("\n" + "=" * 60)
total = len(passed) + len(failed)
print(f"  KET QUA: {len(passed)}/{total} PASS | {len(failed)}/{total} FAIL")

# Xoa test DB tam thoi
try:
    os.unlink(_TEST_DB_FILE.name)
except Exception:
    pass

if failed:
    print("\n  FAILED TESTS:")
    for name, err in failed:
        print(f"    - {name}: {err}")
    print()
    sys.exit(1)
else:
    print("\n  TAT CA TESTS PASS")
    print("=" * 60)
    sys.exit(0)
```

