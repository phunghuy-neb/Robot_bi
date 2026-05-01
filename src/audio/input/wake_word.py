import os
import numpy as np

class WakeWordDetector:
    WAKE_WORDS = ["bi ơi", "bị ơi", "bi ui", "bị ui", "bi hơi", "bi oi"]

    def __init__(self):
        self._enabled = os.getenv("WAKEWORD_ENABLED", "false").lower() == "true"
        self._threshold = float(os.getenv("WAKEWORD_THRESHOLD", "0.7"))
        self._model = None  # lazy load

    def detect(self, audio_data: bytes) -> bool:
        """
        Phát hiện wake word trong audio chunk.
        Dùng faster-whisper để transcribe ngắn
        rồi fuzzy match với WAKE_WORDS.
        Returns True nếu detected.
        """
        if not self.is_enabled():
            return False
            
        # Nhanh chong check silence de tranh transcribe khong can thiet
        if not audio_data:
            return False
            
        try:
            # Convert bytes to numpy array (assumed 16kHz float32 or int16)
            # Dùng np.frombuffer tạm để không crash khi test
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Simple energy check before loading model
            energy = np.mean(audio_array**2)
            if energy < 0.0001:
                return False
                
            self._lazy_load_model()
            if not self._model:
                return False
                
            segments, info = self._model.transcribe(audio_array, language="vi", beam_size=1)
            text = " ".join([seg.text for seg in segments]).lower()
            
            for word in self.WAKE_WORDS:
                if word in text:
                    return True
        except Exception:
            pass
            
        return False

    def _lazy_load_model(self):
        """Load model lần đầu khi cần."""
        if self._model is None and self._enabled:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel("tiny", device="cpu", compute_type="int8")
            except Exception:
                self._enabled = False # disable neu khong load duoc

    def is_enabled(self) -> bool:
        return self._enabled
