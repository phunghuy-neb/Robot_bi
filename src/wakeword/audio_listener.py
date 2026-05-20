"""
audio_listener.py — Continuous microphone capture for wake word detection.

Runs in a background daemon thread. Reads audio chunks and passes them to a
callback. Designed to stop cleanly when detection fires (so EarSTT can then
open the same mic without conflict).

Usage:
    listener = AudioListener(
        on_chunk=lambda chunk: True if detected else False,
        mic_device=1,
    )
    listener.start()
    # ... detection callback fires, listener stops itself ...
    # ... or: ...
    listener.stop()  # explicit stop
"""

import logging
import threading
import time
from typing import Callable, Optional

import numpy as np

from src.wakeword.config import SAMPLE_RATE, CHUNK_FRAMES, CHANNELS

logger = logging.getLogger(__name__)


class AudioListener:
    """
    Background thread that continuously reads mic chunks and calls on_chunk().

    The on_chunk callback receives a float32 numpy array and returns:
      True  → stop the listener (detection fired or explicit stop request)
      False → keep listening

    The listener holds the mic open while running. It MUST be stopped before
    EarSTT (or anything else) tries to open the same microphone.
    """

    def __init__(
        self,
        on_chunk: Callable[[np.ndarray], bool],
        mic_device: int = 0,
        mic_channels: int = 1,
    ):
        self._on_chunk    = on_chunk
        self._mic_device  = mic_device
        self._mic_channels = mic_channels
        self._stop_event  = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background capture thread."""
        if self._thread and self._thread.is_alive():
            return  # already running
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name="WakeWordAudio",
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the capture thread to stop and wait up to 3 seconds."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _capture_loop(self) -> None:
        """Open mic stream, feed chunks to callback, close on stop or detection."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.warning("[WakeWord/AudioListener] sounddevice not available — listener disabled")
            return

        stream = None
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=self._mic_channels,
                dtype="float32",
                blocksize=CHUNK_FRAMES,
                device=self._mic_device,
            )
            stream.start()
        except Exception as e:
            logger.warning("[WakeWord/AudioListener] Cannot open mic (device=%s): %s", self._mic_device, e)
            return

        logger.debug("[WakeWord/AudioListener] Started (device=%s, %dms chunks)", self._mic_device, CHUNK_FRAMES * 1000 // SAMPLE_RATE)

        try:
            while not self._stop_event.is_set():
                try:
                    chunk, _ = stream.read(CHUNK_FRAMES)
                    audio = np.asarray(chunk, dtype=np.float32).flatten()
                    should_stop = self._on_chunk(audio)
                    if should_stop:
                        logger.debug("[WakeWord/AudioListener] Callback requested stop")
                        break
                except Exception as e:
                    logger.debug("[WakeWord/AudioListener] Chunk error: %s", e)
                    time.sleep(0.01)
        finally:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
            logger.debug("[WakeWord/AudioListener] Stopped")
