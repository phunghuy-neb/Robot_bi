# Deferred 6 Code Fixes — 2026-06-23

## Summary

Fixed all 6 issues previously deferred as "cần hardware" from Round 34 audit.
All fixes are code changes only; hardware verification remains pending.
Baseline unchanged: 13 PASS / 6 FAIL (6 fail = missing optional libs, pre-existing).

---

## H1 — Non-blocking motor commands (`firmware/Robot_BI/Robot_BI.ino`)

**Problem**: `cmdForward`, `cmdBackward`, `cmdLeft`, `cmdRight`, `cmdSpin` all called
`delay(dur)` blocking the entire `loop()`. While a motor command ran, `wsServer.loop()`
could not process incoming WS messages (including `stop`) and the watchdog could not fire.

**Fix**:
- Added `unsigned long motorStopAt = 0` global.
- Replaced all cmd handlers with `_timedMotorCmd()` helper that calls `setMotor*()`,
  sets `motorStopAt = millis() + dur`, and returns immediately.
- `loop()` now checks `if (motorStopAt > 0 && millis() >= motorStopAt) { motorStop(); motorStopAt = 0; }` each iteration.
- `stop` / `go_home` handlers (WS + Serial) reset `motorStopAt = 0`.

## L3 — `motorStop()` before `ESP.restart()` (`firmware/Robot_BI/Robot_BI.ino`)

**Problem**: The `add_wifi` WS handler called `ESP.restart()` without stopping motors.
If motors were running, they would continue until the watchdog fired after reboot.

**Fix**: Added `motorStop(); motorStopAt = 0;` before `delay(500); ESP.restart();`.

## L4 — Silent hang on I2S init failure (`firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino`)

**Problem**: If `audioI2S.begin()` returned false, the code entered
`while(true) { delay(1000); }` — a silent hang with no ongoing Serial indication.

**Fix**: Replaced with `for(;;) { Serial.printf("ERROR: I2S init failed, code=%d — halted\n", ...); delay(5000); }`.
Serial monitor now shows the failure reason every 5 seconds.

## L5 — `audioI2S.write()` return value ignored (`firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino`)

**Problem**: All `audioI2S.write()` calls in `writeSilence()`, `playTone()`, and
`playRecordedChannel()` discarded the return value. Partial writes would go undetected.

**Fix**: Capture return value in `written`; log `WARN: ... wrote X/Y bytes` when `written != expected`.

## M-NEW-3 — Wake word clear-before-wait race (`src/wakeword/wakeword_service.py`)

**Problem**: `wait_for_detection()` called `self._detected_event.clear()` then
`self._detected_event.wait()`. If the audio listener detected the wake word between
listener start and the `clear()` call, the detection was silently lost.

**Fix**:
- `_restart_listener()` now calls `self._detected_event.clear()` before starting the
  listener, ensuring the event is cleared atomically with listener startup.
- `wait_for_detection()` no longer calls `clear()` (avoids the race).
- `enter_cooldown()` and `reset_to_idle()` delegate their clear to `_restart_listener()`;
  placeholder/disabled path still calls `clear()` directly.

## M-NEW-4 — WDM-KS double-open (`src/audio/input/microphone_utils.py`)

**Problem**: `probe_input_device()` opened an InputStream, confirmed frames,
then called `stream.stop(); stream.close()` and immediately returned the config.
On Windows WDM-KS the device may not be fully released before the caller
(`CallbackMicrophoneStream.start()`) opens it again, causing an "already open" error.

**Fix**: Added `time.sleep(0.15)` after `stream.close()` before returning the config.
