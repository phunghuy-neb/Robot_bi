# src/wakeword — Wake Word Module

Wake word detection for Robot Bi. Detects "Bi ơi" and triggers the voice pipeline.

## Module Structure

```
src/wakeword/
├── __init__.py          Re-exports public API
├── config.py            All config constants (from .env / env vars)
├── audio_listener.py    Background mic stream (feeds chunks to WakeWordService)
├── wakeword_service.py  State machine + detection backends
├── wakeword_router.py   Thin shim for main.py integration
└── README.md            This file
```

## State Machine

```
IDLE
  ↓  "Bi ơi" detected
LISTENING
  ↓  STT opens mic (on_stt_start)
PROCESSING
  ↓  TTS reply done (on_reply_done)
COOLDOWN  ──[cooldown_sec]──→  IDLE
```

Detection is only active in IDLE state. All other states ignore audio input.
This prevents double-trigger and overlap.

## Backends

| Backend        | Status           | Notes                                          |
|----------------|------------------|------------------------------------------------|
| openwakeword   | Ready (no model) | Best accuracy; needs trained .tflite model     |
| whisper        | Ready            | Fallback using faster-whisper tiny; no training needed |
| placeholder    | Ready            | Testing only; call `force_trigger()` manually  |

Backend selection: `WAKEWORD_BACKEND=openwakeword` (env var).

## Training the "Bi ơi" Model

1. Collect dataset per `docs/WAKEWORD_DATASET_GUIDE.md`
2. Run training:
   ```bash
   pip install openwakeword
   python -m openwakeword.train --positive_dir data/wakeword/positive \
       --negative_dir data/wakeword/negative \
       --output_dir runtime/wakeword \
       --model_name bi_oi
   ```
3. Output: `runtime/wakeword/bi_oi.tflite`
4. Set: `WAKEWORD_MODEL_PATH=runtime/wakeword/bi_oi.tflite`
5. Set: `WAKEWORD_ENABLED=true`

## Environment Variables

| Variable                    | Default                              | Description                  |
|-----------------------------|--------------------------------------|------------------------------|
| WAKEWORD_ENABLED            | false                                | Enable wake word gate        |
| WAKEWORD_BACKEND            | openwakeword                         | Detection backend            |
| WAKEWORD_THRESHOLD          | 0.5                                  | Confidence threshold         |
| WAKEWORD_COOLDOWN_SEC       | 1.5                                  | Post-reply cooldown          |
| WAKEWORD_MODEL_PATH         | runtime/wakeword/bi_oi.tflite        | Path to trained model        |
| WAKEWORD_INFERENCE_FRAMEWORK| tflite                               | tflite or onnx               |

## Quick Test (placeholder mode)

```python
import os
os.environ["WAKEWORD_ENABLED"] = "true"
os.environ["WAKEWORD_BACKEND"] = "placeholder"

from src.wakeword.wakeword_service import WakeWordService, WakeWordState
from src.wakeword.wakeword_router import WakeWordRouter

svc = WakeWordService()
router = WakeWordRouter(svc)
router.start()

# Simulate "Bi ơi"
svc.force_trigger()

# Blocks instantly (already triggered)
detected = router.wait_for_wakeword(timeout=1.0)
assert detected is True
assert svc.get_state() == WakeWordState.LISTENING

router.on_stt_start()
assert svc.get_state() == WakeWordState.PROCESSING

router.on_reply_done()
assert svc.get_state() == WakeWordState.COOLDOWN
```
