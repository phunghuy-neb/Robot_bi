import sys
import os
import time
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
from src.audio.input.microphone_utils import parse_optional_device_index
from src.audio.output.mouth_tts import MouthTTS
from src.ai.ai_engine import BiAI
from src.memory.rag_manager import RAGManager
from src.safety.safety_filter import SafetyFilter
from src.safety.pii_filter import PIIFilter
from src.safety.emotion_risk_detector import EmotionRiskDetector
from src.safety.manipulation_guard import ManipulationGuard
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
from src.ai.persona_manager import PersonaManager, ConversationContext
from src.emotion.emotion_analyzer import EmotionAnalyzer
from src.emotion.emotion_alert import EmotionAlert
from src.wakeword.wakeword_service import WakeWordService
from src.wakeword.wakeword_router import WakeWordRouter
from src.living.living_state import LivingStateEngine, BiState
from src.living.micro_moments import MicroMomentsEngine
from src.living.proactive_behaviors import ProactiveBehaviorsEngine
from src.web_search.search_engine import WebSearchEngine

FAMILY_ID = os.getenv("FAMILY_ID", "default")

# Giận dỗi phrases — hờn dỗi nhẹ, không drama, không guilt-trip
_POUTING_PHRASES = [
    "Ừ thôi, Bi ngồi đây tự chơi vậy~",
    "Bi tự nghĩ trò gì hay hay đây...",
    "Hm... yên tĩnh quá, Bi ngồi một mình thôi~",
    "Ừ mà không sao, Bi tự vui cũng được~",
]
_WELCOME_BACK_PHRASES = [
    "Oa, bé đến rồi! Vui quá!",
    "Bé ơi, có bé là vui hơn nhiều~",
    "Á có bé rồi! Bi đang nghĩ trò gì vui cùng bé nè~",
    "Yay! Bé quay lại rồi! Bi vui lắm~",
]

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


CAMERA_ENABLED = _env_flag("CAMERA_ENABLED", False)
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0") or "0")
CRY_DETECTION_ENABLED = _env_flag("CRY_DETECTION_ENABLED", True)
CRY_MIC_DEVICE = parse_optional_device_index(os.getenv("CRY_MIC_DEVICE"))


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
        self._chunk_lock = threading.Lock()
        self._loop = asyncio.new_event_loop()
        self._current_session_id = None
        self._family_id = FAMILY_ID

        # Daemon thread xử lý audio queue: play → unload → xóa file
        self._worker_thread = threading.Thread(
            target=self._audio_worker_loop, daemon=True
        )
        self._worker_thread.start()

        self.safety = SafetyFilter()
        self._pii = PIIFilter()
        self._risk = EmotionRiskDetector()
        self._manip = ManipulationGuard()

        # Notifier (Sprint 5: WebSocket thật)
        self.notifier = get_notifier()

        # Web Search Engine (Tavily → Brave fallback)
        self._web_search = WebSearchEngine()

        # Living State Engine (Sprint 1.1) + idle behavior engines
        self._living = LivingStateEngine()
        self._micro = MicroMomentsEngine()
        self._proactive = ProactiveBehaviorsEngine()
        self._last_homework_at: float = 0.0
        self._micro_speaking: bool = False
        self._pouting_announced: bool = False

        # Camera is optional hardware and disabled by default.
        self.eye = None
        if CAMERA_ENABLED:
            try:
                from src.vision.camera_stream import EyeVision

                self.eye = EyeVision(
                    camera_index=CAMERA_INDEX,
                    on_event_callback=self._on_vision_event,
                )
                self.eye.start()
            except Exception as camera_error:
                self.eye = None
                logger.warning("[Init] Camera unavailable: %s", camera_error)

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

        # CryDetector uses a second microphone and never reuses the STT mic.
        self.cry_detector = None
        if CRY_DETECTION_ENABLED:
            self.cry_detector = CryDetector(
                on_cry_callback=self._on_cry_detected,
                mic_index=CRY_MIC_DEVICE,
                excluded_mic_indexes={self.ear.mic_device},
            )
            self.cry_detector.start()

        # Wake word service (Sprint 0.3) — disabled by default (WAKEWORD_ENABLED=false)
        try:
            self._wakeword_svc = WakeWordService()
            # Sync mic device from EarSTT probe so both use the same mic
            self._wakeword_svc.mic_device   = self.ear.mic_device
            self._wakeword_svc.mic_channels = self.ear.mic_channels
            self._wakeword = WakeWordRouter(service=self._wakeword_svc)
        except Exception as _ww_err:
            logger.warning("[Init] WakeWord unavailable: %s", _ww_err)
            self._wakeword_svc = None
            self._wakeword = None

        # Parent App API Server (Sprint 5)
        init_server(self.notifier, self.rag)

        # Task Manager với TTS callback (Sprint 6)
        init_task_manager(tts_callback=self._speak_text)
        self._task_manager = _network_state._task_manager
        start_api_server()
        self._puppet_queue = get_puppet_queue()

        atexit.register(self._shutdown)

        logger.info("[Hệ thống] Robot Bi đã khởi động và sẵn sàng!")

    def _next_chunk_idx(self) -> int:
        """Thread-safe monotonic chunk index. Never reset — ensures no filename collision."""
        with self._chunk_lock:
            idx = self._chunk_counter
            self._chunk_counter += 1
            return idx

    def _speak_text(self, text: str) -> None:
        """Phát text qua TTS — dùng cho TaskManager reminder.
        Dùng asyncio.run() thay vì self._loop để tránh xung đột khi gọi từ reminder thread.
        """
        audio_file = asyncio.run(
            self.mouth._generate_audio(text, chunk_index=self._next_chunk_idx())
        )
        if audio_file:
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
        if event_type in ("motion", "known_face"):
            self._proactive.on_presence()
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

    def _handle_puppet_queue(self) -> bool:
        """
        Xử lý tất cả puppet commands đang chờ trong queue.
        Được gọi sau mỗi lượt nói chuyện và khi listen() trả về rỗng.
        SRS 4.5: "Phụ huynh gõ câu bất kỳ trên app, Bi đọc to ngay tại nhà"
        Returns True if any puppet audio was played.
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
                self.mouth._generate_audio(clean, chunk_index=self._next_chunk_idx())
            )
            if audio_file:
                self.audio_queue.put(audio_file)
                queued += 1
        if queued > 0:
            self.audio_queue.join()
        return queued > 0

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
                self._last_homework_at = time.time()
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

    def _living_interaction_start(self) -> None:
        try:
            self._living.on_interaction_start()
            self._proactive.on_interaction()
        except Exception as e:
            logger.warning("[LivingState] interaction_start failed: %s", e)

    def _living_thinking_context(self) -> str | None:
        try:
            hint = self._living.get_state_context_hint()
            self._living.on_thinking_start()
            return hint
        except Exception as e:
            logger.warning("[LivingState] thinking_start failed: %s", e)
            return None

    def _living_reply_done(self) -> None:
        try:
            self._living.on_reply_done()
        except Exception as e:
            logger.warning("[LivingState] reply_done failed: %s", e)

    def _living_turn_aborted(self) -> None:
        try:
            self._living.on_turn_aborted()
        except Exception as e:
            logger.warning("[LivingState] turn_aborted failed: %s", e)

    def _complete_direct_response_turn(self) -> None:
        self._living_reply_done()
        if self._wakeword and self._wakeword.is_enabled():
            self._wakeword.on_reply_done()
        self._close_current_session()

    def _speak_micro_moment(self, text: str) -> None:
        """Play a micro moment TTS phrase; holds _micro_speaking=True until audio finishes."""
        self._micro_speaking = True
        try:
            self._speak_text(text)
            self.audio_queue.join()
        finally:
            self._micro_speaking = False

    def _start_idle_phrase_thread(self, text: str) -> None:
        """Start a non-blocking idle phrase and mark audio busy before the thread runs."""
        try:
            self._micro_speaking = True
            threading.Thread(target=self._speak_micro_moment, args=(text,), daemon=True).start()
        except Exception:
            self._micro_speaking = False
            raise

    def _fire_micro_moment_if_ready(self) -> None:
        """Fire a spontaneous micro moment TTS phrase when Bi is idle (non-blocking)."""
        try:
            is_hw = (time.time() - self._last_homework_at) < 5 * 60
            result = self._micro.maybe_trigger(self._living.get_state(), is_homework=is_hw)
            if result:
                _, text = result
                self._start_idle_phrase_thread(text)
        except Exception as e:
            logger.debug("[MicroMoment] skip: %s", e)

    def _fire_proactive_if_ready(self) -> bool:
        """Fire a gentle proactive prompt when child is present but silent."""
        try:
            is_hw = (time.time() - self._last_homework_at) < 5 * 60
            text = self._proactive.maybe_trigger(
                self._living.get_state(),
                is_homework=is_hw,
            )
            if not text:
                return False
            self._start_idle_phrase_thread(text)
            return True
        except Exception as e:
            logger.debug("[Proactive] skip: %s", e)
            return False

    def _fire_pouting_phrase(self) -> None:
        """Fire a single giận dỗi phrase (non-blocking); skips during sleep hours 22:00–07:00."""
        import random as _rand
        from datetime import datetime as _dt
        _hour = _dt.now().hour
        if _hour >= 22 or _hour < 7:
            return
        phrase = _rand.choice(_POUTING_PHRASES)
        self._start_idle_phrase_thread(phrase)

    def _fire_welcome_back_phrase(self) -> None:
        """Speak a welcome-back phrase synchronously before the LLM response."""
        import random as _rand
        phrase = _rand.choice(_WELCOME_BACK_PHRASES)
        self._speak_text(phrase)

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

        if self.cry_detector:
            try:
                self.cry_detector.stop()
            except Exception:
                pass
        try:
            if self._wakeword:
                self._wakeword.stop()
        except Exception:
            pass
        if self.eye:
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

    def run_text_mode(self):
        """
        Text mode: bypass hoàn toàn STT và TTS.
        Gõ câu vào terminal → Bi xử lý → reply hiện ra dạng text.
        Dùng để test ban đêm không cần mic/loa.
        Gõ 'quit' hoặc Ctrl+C để thoát.
        """
        import time as _time
        print("\n" + "="*55)
        print("  TEXT MODE — Robot Bi")
        print("  Gõ câu hỏi → Enter để gửi | 'quit' để thoát")
        print("="*55 + "\n")

        while True:
            try:
                user_text = input("Bạn: ").strip()
            except (EOFError, KeyboardInterrupt):
                self._shutdown()
                print("\n[Tạm biệt!]")
                break

            if not user_text:
                continue
            if user_text.lower() in ("quit", "exit", "thoat", "thoát"):
                self._shutdown()
                print("[Tạm biệt!]")
                break

            # --- Pipeline giống hệt run(), chỉ bỏ STT và TTS ---
            try:
                user_text_goc = user_text
                self._close_current_session()
                self._current_session_id = create_session(FAMILY_ID)
                add_turn(self._current_session_id, "user", user_text_goc)

                self._living_interaction_start()

                # Session naming (background)
                def _name(sid=self._current_session_id, ut=user_text_goc):
                    from src.infrastructure.sessions.session_namer import _generate_session_title
                    from src.infrastructure.database.db import update_session_title
                    update_session_title(sid, _generate_session_title(ut))
                threading.Thread(target=_name, daemon=True).start()

                # RAG + Web search context
                rag_context = self.rag.retrieve(user_text_goc, family_id=FAMILY_ID)
                web_context = self._web_search.search_if_needed(user_text_goc)
                _ctx_parts = [c for c in [rag_context, web_context] if c]
                if _ctx_parts:
                    user_text = "\n\n".join(_ctx_parts) + f"\n\nBé hỏi: {user_text}"

                # Persona + context modifier — passed via system_context, not injected into user_text
                persona_system_ctx: str | None = None
                if self._persona:
                    try:
                        persona_mod = self._persona.get_system_prompt_modifier()
                        context = self._persona.detect_context(user_text_goc)
                        ctx_mod = self._persona.get_context_prompt_modifier(context)
                        combined = f"{persona_mod} {ctx_mod}".strip()
                        if combined:
                            persona_system_ctx = combined
                    except Exception:
                        pass

                # Emotion analysis
                if self._emotion:
                    try:
                        emotion, confidence = self._emotion.analyze_text(user_text_goc)
                        self._emotion.record_emotion(emotion, confidence, family_id=FAMILY_ID)
                    except Exception:
                        pass

                # ── Child Safety Checks (user input) ─────────────────────────
                _pii_found, _pii_resp = self._pii.check(user_text_goc)
                if _pii_found and _pii_resp:
                    print(f"Bi: {_pii_resp}\n")
                    add_turn(self._current_session_id, "assistant", _pii_resp)
                    self._complete_direct_response_turn()
                    continue
                _risk = self._risk.check(user_text_goc)
                if _risk["log_event"]:
                    _risk_msg = f"Safety risk [{_risk['level']}]: {', '.join(_risk['triggers'])}"
                    _risk_meta = {"level": _risk["level"], "triggers": _risk["triggers"]}
                    threading.Thread(
                        target=self.notifier.push_event,
                        args=("system", _risk_msg, None, _risk_meta, FAMILY_ID),
                        daemon=True
                    ).start()
                if _risk["should_override"] and _risk["response"]:
                    print(f"Bi: {_risk['response']}\n")
                    add_turn(self._current_session_id, "assistant", _risk["response"])
                    self._complete_direct_response_turn()
                    continue
                _manip_input, _manip_input_resp = self._manip.check_user_input(user_text_goc)
                if _manip_input and _manip_input_resp:
                    print(f"Bi: {_manip_input_resp}\n")
                    add_turn(self._current_session_id, "assistant", _manip_input_resp)
                    self._complete_direct_response_turn()
                    continue

                living_context = self._living_thinking_context()
                system_ctx = "\n".join(filter(None, [persona_system_ctx, living_context])) or None

                # ── Role transition ───────────────────────────────────────────
                from src.ai.role_manager import TRANSITION_LINES, TEACHER_HOLD, TEACHER_HOLD_FINAL
                _role_event = self.brain.check_role_transition(user_text_goc)
                if _role_event in (TEACHER_HOLD, TEACHER_HOLD_FINAL):
                    _nudge = TRANSITION_LINES.get(_role_event, "")
                    print(f"Bi: {_nudge}\n")
                    add_turn(self._current_session_id, "assistant", _nudge)
                    self._close_current_session()
                    continue
                _role_pre_line = TRANSITION_LINES.get(_role_event, "") if _role_event else ""

                # Stream LLM → safety filter → in ra terminal
                print("Bi: ", end="", flush=True)
                if _role_pre_line:
                    print(_role_pre_line + " ", end="", flush=True)
                buffer = ""
                full_reply_parts = []
                sanitized_reply_parts = []
                if _role_pre_line:
                    sanitized_reply_parts.append(_role_pre_line)

                for token in self.brain.stream_chat(user_text, system_context=system_ctx):
                    buffer += token
                    full_reply_parts.append(token)
                    while True:
                        match = re.search(r"[.?!\n]", buffer)
                        if not match:
                            break
                        sentence = buffer[:match.end()].strip()
                        buffer = buffer[match.end():]
                        if sentence:
                            is_safe, clean = self.safety.check(sentence)
                            if is_safe:
                                _m_hit, _m_safe = self._manip.check_llm_output(clean)
                                if _m_hit and _m_safe:
                                    clean = _m_safe
                            if clean.strip():
                                sanitized_reply_parts.append(clean)
                                print(clean, end=" ", flush=True)

                if buffer.strip():
                    is_safe, clean = self.safety.check(buffer.strip())
                    if is_safe:
                        _m_hit, _m_safe = self._manip.check_llm_output(clean)
                        if _m_hit and _m_safe:
                            clean = _m_safe
                    if clean.strip():
                        sanitized_reply_parts.append(clean)
                        print(clean, end="", flush=True)

                print("\n")  # xuống dòng sau reply

                # Persist vào DB + RAG (giống run())
                sanitized_reply = " ".join(sanitized_reply_parts).strip()
                if sanitized_reply:
                    add_turn(self._current_session_id, "assistant", sanitized_reply)
                    self._mark_homework_if_needed(self._current_session_id, user_text_goc)
                    threading.Thread(
                        target=self.rag.extract_and_save,
                        args=(user_text_goc, sanitized_reply),
                        kwargs={"family_id": FAMILY_ID},
                        daemon=False,  # non-daemon: Python chờ thread này trước khi exit → không mất memory
                    ).start()
                    threading.Thread(
                        target=self.notifier.push_chat_log,
                        args=(user_text_goc, sanitized_reply),
                        kwargs={"family_id": FAMILY_ID},
                        daemon=True,
                    ).start()

                if sanitized_reply:
                    self._living_reply_done()
                else:
                    self._living_turn_aborted()

                self._close_current_session()

            except KeyboardInterrupt:
                self._shutdown()
                print("\n[Tạm biệt!]")
                break
            except Exception as e:
                logger.error("[TextMode] Lỗi: %s", e, exc_info=True)
                print(f"[Lỗi: {e}]\n")
                self._living_turn_aborted()
                self._close_current_session()

    def run(self):
        import time as _time
        # Start wake word background listener (no-op when disabled)
        if self._wakeword:
            self._wakeword.start()
        try:
            while True:
                try:
                    # Skip listen khi mẹ đang nói trực tiếp qua /api/mom/audio
                    if is_mom_talking():
                        _time.sleep(0.5)
                        continue

                    # ── Wake word gate (disabled by default: WAKEWORD_ENABLED=false) ──
                    if self._wakeword and self._wakeword.is_enabled():
                        if not self._wakeword.wait_for_wakeword(timeout=30.0):
                            continue  # timeout — loop again
                        self._wakeword.on_stt_start()  # LISTENING → PROCESSING

                    # Yield briefly if a micro moment TTS is still playing
                    if self._micro_speaking:
                        _time.sleep(0.3)
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
                        proactive_fired = False
                        puppet_played = self._handle_puppet_queue()
                        if not puppet_played:
                            proactive_fired = self._fire_proactive_if_ready()
                            if not proactive_fired:
                                self._fire_micro_moment_if_ready()
                        # Giận dỗi — announce once; skip when micro moment is already speaking
                        if (not proactive_fired
                                and self._living.get_state() == BiState.MISSING_KID
                                and not self._pouting_announced
                                and not self._micro_speaking):
                            self._fire_pouting_phrase()
                            self._pouting_announced = True
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
                    self._close_current_session()
                    self._current_session_id = create_session(FAMILY_ID)
                    is_first_turn_of_session = True

                    # ── RAG: Retrieve context từ trí nhớ ──────────────────────────
                    user_text_goc = user_text  # giữ lại bản gốc cho extract_and_save
                    add_turn(self._current_session_id, 'user', user_text_goc)

                    self._living_interaction_start()

                    # ── Child Safety Checks (user input) ────────────────────────
                    _pii_found, _pii_resp = self._pii.check(user_text_goc)
                    if _pii_found and _pii_resp:
                        add_turn(self._current_session_id, "assistant", _pii_resp)
                        _af = self._loop.run_until_complete(
                            self.mouth._generate_audio(_pii_resp, chunk_index=self._next_chunk_idx())
                        )
                        if _af:
                            self.audio_queue.put(_af)
                            self.audio_queue.join()
                        self._complete_direct_response_turn()
                        continue
                    _risk = self._risk.check(user_text_goc)
                    if _risk["log_event"]:
                        _risk_msg = f"Safety risk [{_risk['level']}]: {', '.join(_risk['triggers'])}"
                        _risk_meta = {"level": _risk["level"], "triggers": _risk["triggers"]}
                        threading.Thread(
                            target=self.notifier.push_event,
                            args=("system", _risk_msg, None, _risk_meta, self._family_id),
                            daemon=True
                        ).start()
                    if _risk["should_override"] and _risk["response"]:
                        add_turn(self._current_session_id, "assistant", _risk["response"])
                        _af = self._loop.run_until_complete(
                            self.mouth._generate_audio(_risk["response"], chunk_index=self._next_chunk_idx())
                        )
                        if _af:
                            self.audio_queue.put(_af)
                            self.audio_queue.join()
                        self._complete_direct_response_turn()
                        continue
                    _manip_input, _manip_input_resp = self._manip.check_user_input(user_text_goc)
                    if _manip_input and _manip_input_resp:
                        add_turn(self._current_session_id, "assistant", _manip_input_resp)
                        _af = self._loop.run_until_complete(
                            self.mouth._generate_audio(_manip_input_resp, chunk_index=self._next_chunk_idx())
                        )
                        if _af:
                            self.audio_queue.put(_af)
                            self.audio_queue.join()
                        self._complete_direct_response_turn()
                        continue

                    # Welcome back after giận dỗi (after safety, before LLM; skip for COMFORT)
                    if self._pouting_announced:
                        try:
                            _wb_ctx = self._persona.detect_context(user_text_goc) if self._persona else None
                            if _wb_ctx != ConversationContext.COMFORT:
                                self._fire_welcome_back_phrase()
                        except Exception:
                            pass
                        self._pouting_announced = False

                    if is_first_turn_of_session:
                        def _name_session(session_id=self._current_session_id, user_text=user_text_goc):
                            from src.infrastructure.sessions.session_namer import _generate_session_title
                            from src.infrastructure.database.db import update_session_title

                            title = _generate_session_title(user_text)
                            update_session_title(session_id, title)

                        threading.Thread(target=_name_session, daemon=True).start()
                        is_first_turn_of_session = False
                    rag_context = self.rag.retrieve(user_text_goc, family_id=FAMILY_ID)
                    web_context = self._web_search.search_if_needed(user_text_goc)
                    _ctx_parts = [c for c in [rag_context, web_context] if c]
                    if _ctx_parts:
                        user_text = "\n\n".join(_ctx_parts) + f"\n\nBé hỏi: {user_text}"
                    if rag_context:
                        # DEBUG: chứa PII - tắt trong production.
                        logger.debug("[Bi - Trí nhớ] %s", rag_context)
                    if web_context:
                        logger.debug("[WebSearch] Context injected len=%d", len(web_context))

                    if self._face:
                        try:
                            self._face.set_mode('thinking')
                        except Exception:
                            pass

                    persona_system_ctx: str | None = None
                    if self._persona:
                        try:
                            persona_mod = self._persona.get_system_prompt_modifier()
                            context = self._persona.detect_context(user_text_goc)
                            ctx_mod = self._persona.get_context_prompt_modifier(context)
                            combined = f"{persona_mod} {ctx_mod}".strip()
                            if combined:
                                persona_system_ctx = combined
                        except Exception as e:
                            logger.debug("[Persona] Error: %s", e)

                    living_context = self._living_thinking_context()
                    system_ctx = "\n".join(filter(None, [persona_system_ctx, living_context])) or None

                    # ── Role transition ───────────────────────────────────────
                    from src.ai.role_manager import TRANSITION_LINES, TEACHER_HOLD, TEACHER_HOLD_FINAL
                    _role_event = self.brain.check_role_transition(user_text_goc)
                    if _role_event in (TEACHER_HOLD, TEACHER_HOLD_FINAL):
                        _nudge = TRANSITION_LINES.get(_role_event, "")
                        add_turn(self._current_session_id, "assistant", _nudge)
                        _af = self._loop.run_until_complete(
                            self.mouth._generate_audio(_nudge, chunk_index=self._next_chunk_idx())
                        )
                        if _af:
                            self.audio_queue.put(_af)
                            self.audio_queue.join()
                        self._complete_direct_response_turn()
                        continue
                    _role_pre_line = TRANSITION_LINES.get(_role_event, "") if _role_event else ""

                    # TTS câu chuyển vai trước khi LLM stream (nếu có)
                    full_reply_parts = []
                    sanitized_reply_parts = []
                    if _role_pre_line:
                        sanitized_reply_parts.append(_role_pre_line)
                        _af = self._loop.run_until_complete(
                            self.mouth._generate_audio(
                                _role_pre_line, chunk_index=self._next_chunk_idx()
                            )
                        )
                        if _af:
                            self.audio_queue.put(_af)

                    # Stream tokens từ LLM, tách câu theo . ? ! \n
                    for token in self.brain.stream_chat(user_text, system_context=system_ctx):
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
                                if is_safe:
                                    _m_hit, _m_safe = self._manip.check_llm_output(clean_sentence)
                                    if _m_hit and _m_safe:
                                        clean_sentence = _m_safe
                                if not clean_sentence.strip():
                                    continue  # bỏ qua câu rỗng sau khi lọc
                                sanitized_reply_parts.append(clean_sentence)
                                _idx = self._next_chunk_idx()
                                audio_file = self._loop.run_until_complete(
                                    self.mouth._generate_audio(
                                        clean_sentence, chunk_index=_idx
                                    )
                                )
                                if audio_file is None:
                                    continue  # TTS hoàn toàn fail → bỏ qua chunk này
                                self.audio_queue.put(audio_file)
                                logger.debug("[Bi - Miệng] Chunk %d len=%d", _idx, len(clean_sentence))

                    # Phần còn lại trong buffer (câu chưa kết thúc bằng dấu câu)
                    if buffer.strip():
                        is_safe, clean_buffer = self.safety.check(buffer.strip())
                        if is_safe:
                            _m_hit, _m_safe = self._manip.check_llm_output(clean_buffer)
                            if _m_hit and _m_safe:
                                clean_buffer = _m_safe
                        if clean_buffer.strip():
                            sanitized_reply_parts.append(clean_buffer)
                            _idx = self._next_chunk_idx()
                            audio_file = self._loop.run_until_complete(
                                self.mouth._generate_audio(
                                    clean_buffer, chunk_index=_idx
                                )
                            )
                            if audio_file is not None:
                                self.audio_queue.put(audio_file)
                                logger.debug("[Bi - Miệng] Chunk %d len=%d", _idx, len(clean_buffer))

                    # Đợi worker phát hết hàng đợi trước khi nghe tiếp
                    self.audio_queue.join()

                    # Wake word cooldown — restart listener sau reply (no-op when disabled)
                    if self._wakeword and self._wakeword.is_enabled():
                        self._wakeword.on_reply_done()

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
                        self._living_reply_done()
                        threading.Thread(
                            target=self.rag.extract_and_save,
                            args=(user_text_goc, sanitized_reply),
                            kwargs={"family_id": FAMILY_ID},
                            daemon=False,  # non-daemon: Python chờ thread này trước khi exit → không mất memory
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
                        self._living_turn_aborted()
                        self._close_current_session()
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error("[MainLoop] Loi khong mong doi, bo qua iteration: %s", e, exc_info=True)
                    self._close_current_session()
                    self._living_turn_aborted()
                    # Reset wake word to IDLE on pipeline error
                    if self._wakeword and self._wakeword.is_enabled():
                        self._wakeword.on_error()
                    _time.sleep(1)
                    continue

        except KeyboardInterrupt:
            self._shutdown()
            logger.info("[Hệ thống] Robot Bi đang tắt. Tạm biệt!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--text-mode",
        action="store_true",
        help="Bypass STT/TTS — gõ input từ bàn phím, nhận reply dạng text. Dùng để test ban đêm.",
    )
    args = parser.parse_args()

    app = RobotBiApp()

    if args.text_mode:
        app.run_text_mode()
    else:
        app.run()
