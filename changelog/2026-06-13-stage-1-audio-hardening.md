# Stage 1 Audio-Only Hardening

## Summary

Hardened Sprint 1.4 for the current speaker + two-microphone hardware profile
without requiring a camera.

## Changes

- Proactive behavior now uses recent voice interaction as its primary presence
  signal; optional camera events only extend presence.
- Camera startup is disabled by default and controlled by `CAMERA_ENABLED`.
- Added callback/native-rate microphone probing and 16 kHz resampling.
- Added `python -m src.audio.input.microphone_utils` for hardware diagnostics.
- EarSTT and wake-word capture use the shared callback microphone path.
- CryDetector excludes the STT microphone and supports `CRY_MIC_DEVICE`.
- Removed decorative `primary_api` config and added Cerebras quota cooldown.
- Added proper Vietnamese accents to proactive TTS phrases.
- Ignored the local `.agents/` skill mirror.
- Added a standalone ESP32-S3 N16R8 hardware test for two INMP441 microphones
  and a MAX98357A speaker. It uses beep cues, records stereo audio to PSRAM,
  then plays each microphone channel separately without live loopback.

## Verification

- Changed-file `py_compile`: PASS.
- `python tests/run_tests.py`: PASS 560/560.
- ESP32 Arduino Core 3.3.8 compile for 16 MB flash + OPI PSRAM: PASS.
- The Windows microphone probe applies only to optional PC-connected
  microphones. The robot's INMP441 microphones require the ESP32-S3 firmware
  path and are not affected by Windows microphone permissions.
