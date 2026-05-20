"""
config.py — Wake word configuration constants (all from environment / .env).

Environment variables:
  WAKEWORD_ENABLED              = "false"         # Enable wake word gate
  WAKEWORD_BACKEND              = "openwakeword"  # openwakeword | custom_mfcc | whisper | placeholder
  WAKEWORD_THRESHOLD            = "0.5"           # Detection confidence threshold
  WAKEWORD_COOLDOWN_SEC         = "1.5"           # Seconds to ignore after each reply
  WAKEWORD_MODEL_PATH           = "runtime/wakeword/bi_oi.tflite"
  WAKEWORD_INFERENCE_FRAMEWORK  = "tflite"        # tflite | onnx
  WAKEWORD_CUSTOM_MODEL_PATH    = "runtime/wakeword/bi_oi_classifier.pkl"

Backends:
  custom_mfcc   Sprint 0.4 — MFCC+SVM classifier trained on synthetic data.
                Requires: pip install scikit-learn
                Requires: model at WAKEWORD_CUSTOM_MODEL_PATH (scripts/train_wakeword.py)
                CPU-friendly. ~1.5s window. 75-85% accuracy with synthetic dataset.

  openwakeword  TFLite custom model (future — needs large training dataset).
                Requires: pip install openwakeword
                Requires: model file at WAKEWORD_MODEL_PATH (see docs/WAKEWORD_DATASET_GUIDE.md)

  whisper       Fallback — faster-whisper tiny + fuzzy match.
                Already in stack (no new dep). Higher latency (~1.5s window).
                Works without a trained model.

  placeholder   Testing only — no mic, no model.
                Trigger manually with WakeWordService.force_trigger().
"""

import os

# ── Feature switch ─────────────────────────────────────────────────────────────
WAKEWORD_ENABLED = os.getenv("WAKEWORD_ENABLED", "false").lower() == "true"

# ── Backend ────────────────────────────────────────────────────────────────────
WAKEWORD_BACKEND = os.getenv("WAKEWORD_BACKEND", "openwakeword")
# Valid: "openwakeword" | "whisper" | "placeholder"

# ── Detection tuning ──────────────────────────────────────────────────────────
WAKEWORD_THRESHOLD    = float(os.getenv("WAKEWORD_THRESHOLD",    "0.5"))
WAKEWORD_COOLDOWN_SEC = float(os.getenv("WAKEWORD_COOLDOWN_SEC", "1.5"))

# ── Model path ────────────────────────────────────────────────────────────────
WAKEWORD_MODEL_PATH = os.getenv(
    "WAKEWORD_MODEL_PATH",
    os.path.join("runtime", "wakeword", "bi_oi.tflite"),
)
WAKEWORD_INFERENCE_FRAMEWORK = os.getenv("WAKEWORD_INFERENCE_FRAMEWORK", "tflite")

# Custom MFCC+SVM model path (Sprint 0.4 — scripts/train_wakeword.py)
WAKEWORD_CUSTOM_MODEL_PATH = os.getenv(
    "WAKEWORD_CUSTOM_MODEL_PATH",
    os.path.join("runtime", "wakeword", "bi_oi_classifier.pkl"),
)

# ── Audio constants ───────────────────────────────────────────────────────────
SAMPLE_RATE  = 16000
CHANNELS     = 1
CHUNK_MS     = 80                                  # 80ms per chunk
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_MS / 1000)  # 1280 frames @ 16kHz

# ── Energy gate — skip chunks below this RMS (silence) ────────────────────────
ENERGY_MIN = 0.0005

# ── Whisper fallback — rolling window size ────────────────────────────────────
WHISPER_WINDOW_SEC    = 1.5
WHISPER_OVERLAP_RATIO = 0.5   # 50% overlap between windows
