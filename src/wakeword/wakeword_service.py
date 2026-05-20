"""
wakeword_service.py — Core wake word detection + state machine.

States:
  IDLE       → background listener running, waiting for "Bi ơi"
  LISTENING  → wake word just detected, STT should start immediately
  PROCESSING → STT + LLM + TTS in progress, detection blocked
  COOLDOWN   → reply done, wait cooldown_sec before listening again

Anti-spam / double-trigger protection:
  - _on_audio_chunk only runs detection when state is IDLE
  - force_trigger() only fires when state is IDLE
  - COOLDOWN auto-returns to IDLE and restarts AudioListener

Backends (priority order):
  openwakeword  Custom TFLite model — best accuracy, needs training first.
                See docs/WAKEWORD_DATASET_GUIDE.md for dataset spec.
                Falls back to whisper when model file not found.

  whisper       faster-whisper tiny + fuzzy match — already in stack.
                No training needed. Latency ~1.5s window. Good for testing.

  placeholder   No mic, no model. Use force_trigger() to simulate detection.
                Ideal for unit tests and CI.
"""

import enum
import logging
import os
import threading
import time
from typing import Optional

import numpy as np

from src.wakeword.config import (
    WAKEWORD_ENABLED,
    WAKEWORD_BACKEND,
    WAKEWORD_THRESHOLD,
    WAKEWORD_COOLDOWN_SEC,
    WAKEWORD_MODEL_PATH,
    WAKEWORD_INFERENCE_FRAMEWORK,
    WAKEWORD_CUSTOM_MODEL_PATH,
    SAMPLE_RATE,
    ENERGY_MIN,
    WHISPER_WINDOW_SEC,
    WHISPER_OVERLAP_RATIO,
)

logger = logging.getLogger(__name__)


class WakeWordState(str, enum.Enum):
    IDLE       = "IDLE"
    LISTENING  = "LISTENING"
    PROCESSING = "PROCESSING"
    COOLDOWN   = "COOLDOWN"


class WakeWordService:
    """
    Wake word detection service with 4-state machine.

    Typical usage (in main.py voice loop):

        svc = WakeWordService()
        svc.mic_device   = ear.mic_device    # sync from EarSTT probe
        svc.mic_channels = ear.mic_channels
        svc.start()                          # starts background AudioListener

        # In voice loop:
        if not svc.wait_for_detection(timeout=30.0):
            continue   # timeout
        # wake detected → state is now LISTENING
        svc.set_state(WakeWordState.PROCESSING)
        user_text = ear.listen()             # EarSTT can open mic (listener stopped)
        # ... LLM + TTS ...
        svc.enter_cooldown()                 # → COOLDOWN → IDLE; restarts listener
    """

    def __init__(self):
        self._enabled      = WAKEWORD_ENABLED
        self._backend      = WAKEWORD_BACKEND
        self._threshold    = WAKEWORD_THRESHOLD
        self._cooldown_sec = WAKEWORD_COOLDOWN_SEC

        self._state      = WakeWordState.IDLE
        self._state_lock = threading.Lock()
        self._detected_event = threading.Event()

        self._listener: Optional[object] = None  # AudioListener instance
        self._oww_model    = None               # openWakeWord lazy model
        self._whisper_model = None              # faster-whisper lazy model
        self._mfcc_payload  = None              # custom MFCC+SVM model payload

        # Shared rolling buffer for whisper + custom_mfcc backends
        self._whisper_buffer: list = []
        self._whisper_window_frames = int(SAMPLE_RATE * WHISPER_WINDOW_SEC)
        self._whisper_overlap_frames = int(self._whisper_window_frames * (1 - WHISPER_OVERLAP_RATIO))

        # Mic device — override from EarSTT after probe
        self.mic_device   = int(os.getenv("MIC_DEVICE", "0") or "0")
        self.mic_channels = 1

    # ── Public API ─────────────────────────────────────────────────────────────

    def is_enabled(self) -> bool:
        return self._enabled

    def get_state(self) -> WakeWordState:
        with self._state_lock:
            return self._state

    def set_state(self, state: WakeWordState) -> None:
        with self._state_lock:
            old = self._state
            self._state = state
        logger.debug("[WakeWord] %s → %s", old.value, state.value)

    def start(self) -> None:
        """Start background audio listener (no-op in placeholder mode or disabled)."""
        if not self._enabled:
            logger.debug("[WakeWord] Disabled — start() is a no-op")
            return
        if self._backend == "placeholder":
            logger.info("[WakeWord] Placeholder mode — call force_trigger() to simulate detection")
            return
        self._restart_listener()
        logger.info("[WakeWord] Started (backend=%s, threshold=%.2f, cooldown=%.1fs)",
                    self._backend, self._threshold, self._cooldown_sec)

    def stop(self) -> None:
        """Stop background audio listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def wait_for_detection(self, timeout: float = 30.0) -> bool:
        """
        Block until wake word detected or timeout expires.

        Should only be called from the main voice loop.
        Returns True if wake word was detected (state → LISTENING).
        Returns False on timeout (caller should loop again).
        """
        if not self._enabled:
            return False

        self._detected_event.clear()
        detected = self._detected_event.wait(timeout=timeout)
        if detected:
            # State was already set to LISTENING by _on_audio_chunk / force_trigger
            pass
        return detected

    def force_trigger(self) -> bool:
        """
        Simulate wake word detection without audio.
        Only fires when state is IDLE (anti-spam protection).

        Returns True if trigger was accepted, False if rejected (not in IDLE).
        """
        with self._state_lock:
            if self._state != WakeWordState.IDLE:
                logger.debug("[WakeWord] force_trigger rejected — state=%s", self._state.value)
                return False
            self._state = WakeWordState.LISTENING

        logger.info("[WakeWord] Force trigger accepted → LISTENING")
        self._detected_event.set()
        return True

    def enter_cooldown(self) -> None:
        """
        Transition PROCESSING → COOLDOWN, then auto-return to IDLE + restart listener.
        Call after TTS reply is fully delivered.
        """
        self.set_state(WakeWordState.COOLDOWN)

        def _auto_idle():
            time.sleep(self._cooldown_sec)
            with self._state_lock:
                if self._state == WakeWordState.COOLDOWN:
                    self._state = WakeWordState.IDLE
                    logger.debug("[WakeWord] Cooldown done → IDLE")
            self._detected_event.clear()
            # Restart audio listener for next detection cycle
            if self._enabled and self._backend != "placeholder":
                self._restart_listener()

        threading.Thread(target=_auto_idle, daemon=True, name="WakeWordCooldown").start()

    def reset_to_idle(self) -> None:
        """
        Emergency reset to IDLE (use on pipeline error).
        Restarts audio listener so detection can resume.
        """
        self.set_state(WakeWordState.IDLE)
        self._detected_event.clear()
        if self._enabled and self._backend != "placeholder":
            self._restart_listener()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _restart_listener(self) -> None:
        """Create and start a fresh AudioListener (stops any existing one first)."""
        try:
            from src.wakeword.audio_listener import AudioListener
            if self._listener:
                try:
                    self._listener.stop()
                except Exception:
                    pass
            self._listener = AudioListener(
                on_chunk=self._on_audio_chunk,
                mic_device=self.mic_device,
                mic_channels=self.mic_channels,
            )
            self._listener.start()
            logger.debug("[WakeWord] AudioListener (re)started")
        except Exception as e:
            logger.warning("[WakeWord] Cannot start AudioListener: %s", e)

    def _on_audio_chunk(self, chunk: np.ndarray) -> bool:
        """
        Callback from AudioListener for each mic chunk.
        Returns True to stop the listener (detection happened).
        """
        # Gate: only detect in IDLE state
        with self._state_lock:
            if self._state != WakeWordState.IDLE:
                # Listener should not be running in non-IDLE state; stop it defensively
                return True

        # Energy gate — skip silent chunks
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        if rms < ENERGY_MIN:
            return False

        detected = False
        try:
            if self._backend == "custom_mfcc":
                detected = self._detect_custom_mfcc(chunk)
                if not detected:
                    pass  # no automatic fallback for custom_mfcc
            elif self._backend == "openwakeword":
                detected = self._detect_openwakeword(chunk)
                if not detected:
                    # Transparent fallback if model not loaded
                    detected = self._detect_whisper(chunk)
            elif self._backend == "whisper":
                detected = self._detect_whisper(chunk)
        except Exception as e:
            logger.debug("[WakeWord] Detection error: %s", e)

        if detected:
            logger.info("[WakeWord] Wake word detected! (backend=%s)", self._backend)
            with self._state_lock:
                self._state = WakeWordState.LISTENING
            self._detected_event.set()
            return True  # stop listener; mic is free for EarSTT

        return False

    def _detect_custom_mfcc(self, chunk: np.ndarray) -> bool:
        """Detect using MFCC+SVM classifier (Sprint 0.4 training pipeline)."""
        # Accumulate into rolling window (reuse whisper buffer logic)
        self._whisper_buffer.extend(chunk.tolist())
        if len(self._whisper_buffer) < self._whisper_window_frames:
            return False

        window = np.array(self._whisper_buffer[:self._whisper_window_frames], dtype=np.float32)
        self._whisper_buffer = self._whisper_buffer[self._whisper_overlap_frames:]

        payload = self._get_mfcc_payload()
        if payload is None:
            return False

        try:
            import scipy.fftpack
            import scipy.signal

            scaler = payload["scaler"]
            model  = payload["model"]
            cfg    = payload.get("config", {})
            n_mfcc = cfg.get("n_mfcc", 20)
            n_mels = cfg.get("n_mels", 40)
            n_fft  = cfg.get("n_fft",  512)
            hop    = cfg.get("hop_len", 160)

            # Pre-emphasis + STFT
            audio = np.append(window[0], window[1:] - 0.97 * window[:-1])
            _, _, Zxx = scipy.signal.stft(audio, fs=SAMPLE_RATE, nperseg=n_fft,
                                           noverlap=n_fft - hop, boundary=None)
            power = np.abs(Zxx) ** 2

            # Mel filterbank (simplified inline)
            def _hz_mel(hz): return 2595 * np.log10(1 + hz / 700)
            def _mel_hz(m):  return 700 * (10 ** (m / 2595) - 1)
            mel_pts = np.linspace(_hz_mel(0), _hz_mel(SAMPLE_RATE / 2), n_mels + 2)
            hz_pts  = _mel_hz(mel_pts)
            bins    = np.floor((n_fft + 1) * hz_pts / SAMPLE_RATE).astype(int)
            fbank   = np.zeros((n_mels, n_fft // 2 + 1))
            for m in range(1, n_mels + 1):
                lo, mid, hi = bins[m - 1], bins[m], bins[m + 1]
                for k in range(lo, mid):
                    if mid > lo: fbank[m - 1, k] = (k - lo) / (mid - lo)
                for k in range(mid, hi):
                    if hi > mid: fbank[m - 1, k] = (hi - k) / (hi - mid)

            log_mel = np.log(fbank @ power + 1e-9)
            mfcc    = scipy.fftpack.dct(log_mel, type=2, axis=0, norm='ortho')[:n_mfcc]
            delta   = np.diff(mfcc, n=1, axis=1, prepend=mfcc[:, :1])
            feat    = np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1), delta.mean(axis=1)])

            feat_s = scaler.transform(feat.reshape(1, -1))
            pred   = model.predict(feat_s)[0]
            prob   = model.predict_proba(feat_s)[0]
            score  = prob[1]

            if pred == 1 and score >= self._threshold:
                logger.debug("[WakeWord] MFCC+SVM score=%.3f >= %.3f", score, self._threshold)
                return True
        except Exception as e:
            logger.debug("[WakeWord] custom_mfcc error: %s", e)

        return False

    def _get_mfcc_payload(self):
        """Lazy load MFCC+SVM model. Returns None if unavailable."""
        if self._mfcc_payload is not None:
            return self._mfcc_payload

        if not os.path.exists(WAKEWORD_CUSTOM_MODEL_PATH):
            logger.debug(
                "[WakeWord] Custom model not found at '%s' — run scripts/train_wakeword.py",
                WAKEWORD_CUSTOM_MODEL_PATH,
            )
            return None

        try:
            import pickle
            with open(WAKEWORD_CUSTOM_MODEL_PATH, "rb") as f:
                self._mfcc_payload = pickle.load(f)
            metrics = self._mfcc_payload.get("metrics", {})
            logger.info("[WakeWord] Loaded MFCC+SVM model (F1=%.2f) from '%s'",
                        metrics.get("cv_f1_mean", 0), WAKEWORD_CUSTOM_MODEL_PATH)
            return self._mfcc_payload
        except Exception as e:
            logger.warning("[WakeWord] Cannot load custom model: %s", e)
            return None

    def _detect_openwakeword(self, chunk: np.ndarray) -> bool:
        """Detect using openWakeWord TFLite model."""
        model = self._get_oww_model()
        if model is None:
            return False

        # openWakeWord expects int16 PCM
        audio_int16 = (chunk * 32767).clip(-32768, 32767).astype(np.int16)
        prediction = model.predict(audio_int16)  # {model_name: score}

        scores = list(prediction.values())
        if scores:
            score = max(scores)
            if score >= self._threshold:
                logger.debug("[WakeWord] OWW score=%.3f >= threshold=%.3f", score, self._threshold)
                return True
        return False

    def _detect_whisper(self, chunk: np.ndarray) -> bool:
        """Detect using faster-whisper tiny fuzzy match (fallback)."""
        # Accumulate into rolling window
        self._whisper_buffer.extend(chunk.tolist())

        if len(self._whisper_buffer) < self._whisper_window_frames:
            return False  # not enough audio yet

        # Grab window, keep overlap for next call
        window = np.array(self._whisper_buffer[:self._whisper_window_frames], dtype=np.float32)
        self._whisper_buffer = self._whisper_buffer[self._whisper_overlap_frames:]

        model = self._get_whisper_model()
        if model is None:
            return False

        try:
            segments, _ = model.transcribe(window, language="vi", beam_size=1)
            text = " ".join(seg.text for seg in segments).lower()
            wake_variants = ["bi ơi", "bị ơi", "bi ui", "bi oi", "bị ui", "bi hơi"]
            hit = any(w in text for w in wake_variants)
            if hit:
                logger.debug("[WakeWord] Whisper matched: '%s'", text.strip())
            return hit
        except Exception as e:
            logger.debug("[WakeWord] Whisper transcribe error: %s", e)
            return False

    # ── Lazy model loaders ────────────────────────────────────────────────────

    def _get_oww_model(self):
        """Lazy load openWakeWord model. Returns None if unavailable."""
        if self._oww_model is not None:
            return self._oww_model

        if not os.path.exists(WAKEWORD_MODEL_PATH):
            logger.debug(
                "[WakeWord] OWW model not found at '%s' — run training first "
                "(see docs/WAKEWORD_DATASET_GUIDE.md)",
                WAKEWORD_MODEL_PATH,
            )
            return None

        try:
            from openwakeword.model import Model as OWWModel
            self._oww_model = OWWModel(
                wakeword_models=[WAKEWORD_MODEL_PATH],
                inference_framework=WAKEWORD_INFERENCE_FRAMEWORK,
            )
            logger.info("[WakeWord] Loaded openWakeWord model from '%s'", WAKEWORD_MODEL_PATH)
            return self._oww_model
        except ImportError:
            logger.warning("[WakeWord] openWakeWord not installed — `pip install openwakeword`")
            return None
        except Exception as e:
            logger.warning("[WakeWord] Cannot load OWW model: %s", e)
            return None

    def _get_whisper_model(self):
        """Lazy load faster-whisper tiny (wake word fallback)."""
        if self._whisper_model is not None:
            return self._whisper_model
        try:
            from faster_whisper import WhisperModel
            self._whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            logger.info("[WakeWord] Loaded Whisper tiny (wake word fallback)")
            return self._whisper_model
        except Exception as e:
            logger.warning("[WakeWord] Cannot load Whisper tiny: %s", e)
            return None
