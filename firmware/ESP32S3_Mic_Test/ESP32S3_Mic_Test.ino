/*
  Robot Bi - ESP32-S3 dual INMP441 + MAX98357A autonomous test

  Target:
    ESP32-S3 N16R8
    Arduino ESP32 core 3.x

  Wiring:
    GPIO4 -> SCK on both INMP441 microphones + BCLK on MAX98357A
    GPIO5 -> WS on both INMP441 microphones + LRC on MAX98357A
    GPIO6 -> SD on both INMP441 microphones
    GPIO7 -> DIN on MAX98357A

    3V3 -> VDD on both microphones
    GND -> GND on both microphones
    GND -> L/R on the left microphone
    3V3 -> L/R on the right microphone

    5V  -> VIN on MAX98357A
    GND -> GND on MAX98357A
    Speaker -> SPK+ and SPK- (never connect SPK- to GND)

  Test cycle:
    1 long beep  -> speak after the beep for 5 seconds
    2 short beeps -> recording finished
    1 short beep  -> playback of the left microphone
    2 short beeps -> playback of the right microphone
    3 short beeps -> cycle finished; the next cycle starts after 3 seconds

  The firmware records first and plays back later. It never routes live
  microphone audio to the speaker, which avoids direct acoustic feedback.
*/

#include <Arduino.h>
#include "ESP_I2S.h"
#include "esp32-hal-psram.h"
#include <math.h>

constexpr int I2S_BCLK_PIN = 4;
constexpr int I2S_WS_PIN = 5;
constexpr int I2S_MIC_DATA_PIN = 6;
constexpr int I2S_AMP_DATA_PIN = 7;

constexpr uint32_t SAMPLE_RATE_HZ = 16000;
constexpr uint32_t RECORD_SECONDS = 5;
constexpr size_t RECORD_FRAME_COUNT = SAMPLE_RATE_HZ * RECORD_SECONDS;
constexpr size_t STEREO_SAMPLE_COUNT = RECORD_FRAME_COUNT * 2;
constexpr size_t RECORD_BUFFER_BYTES = STEREO_SAMPLE_COUNT * sizeof(int32_t);
constexpr size_t IO_FRAMES = 256;

constexpr float BEEP_FREQUENCY_HZ = 880.0f;
constexpr int32_t BEEP_AMPLITUDE = INT32_MAX / 24;
constexpr uint32_t SHORT_BEEP_MS = 120;
constexpr uint32_t LONG_BEEP_MS = 650;
constexpr uint32_t BEEP_GAP_MS = 130;
constexpr uint32_t ACOUSTIC_SETTLE_MS = 600;
constexpr uint32_t BETWEEN_PLAYBACK_MS = 900;
constexpr uint32_t BETWEEN_CYCLES_MS = 3000;

// Reduce recorded audio by 12 dB before playback.
constexpr int PLAYBACK_ATTENUATION_BITS = 2;

I2SClass audioI2S;
int32_t *recording = nullptr;
int32_t ioBuffer[IO_FRAMES * 2];

void fatalError(const char *message) {
  Serial.print("FATAL: ");
  Serial.println(message);

  // A repeating low double-beep indicates a permanent setup error.
  while (true) {
    for (int repeat = 0; repeat < 2; ++repeat) {
      for (size_t frame = 0; frame < IO_FRAMES; ++frame) {
        float phase = 2.0f * PI * 330.0f * frame / SAMPLE_RATE_HZ;
        int32_t sample = static_cast<int32_t>(sinf(phase) * BEEP_AMPLITUDE);
        ioBuffer[frame * 2] = sample;
        ioBuffer[frame * 2 + 1] = sample;
      }
      audioI2S.write(reinterpret_cast<uint8_t *>(ioBuffer), sizeof(ioBuffer));
      delay(120);
    }
    delay(1200);
  }
}

void writeSilence(uint32_t durationMs) {
  memset(ioBuffer, 0, sizeof(ioBuffer));
  size_t framesRemaining =
    static_cast<size_t>(SAMPLE_RATE_HZ) * durationMs / 1000;

  while (framesRemaining > 0) {
    size_t frames = min(framesRemaining, IO_FRAMES);
    size_t expected = frames * 2 * sizeof(int32_t);
    size_t written = audioI2S.write(  // L5: check write return
      reinterpret_cast<uint8_t *>(ioBuffer),
      expected
    );
    if (written != expected) {
      Serial.printf("WARN: writeSilence wrote %u/%u bytes\n",
                    static_cast<unsigned>(written), static_cast<unsigned>(expected));
    }
    framesRemaining -= frames;
  }
}

void playTone(float frequencyHz, uint32_t durationMs) {
  size_t framesRemaining =
    static_cast<size_t>(SAMPLE_RATE_HZ) * durationMs / 1000;
  uint32_t phaseFrame = 0;

  while (framesRemaining > 0) {
    size_t frames = min(framesRemaining, IO_FRAMES);

    for (size_t frame = 0; frame < frames; ++frame) {
      float phase =
        2.0f * PI * frequencyHz * phaseFrame / SAMPLE_RATE_HZ;
      int32_t sample =
        static_cast<int32_t>(sinf(phase) * BEEP_AMPLITUDE);
      ioBuffer[frame * 2] = sample;
      ioBuffer[frame * 2 + 1] = sample;
      ++phaseFrame;
    }

    size_t expected = frames * 2 * sizeof(int32_t);
    size_t written = audioI2S.write(  // L5: check write return
      reinterpret_cast<uint8_t *>(ioBuffer),
      expected
    );
    if (written != expected) {
      Serial.printf("WARN: playTone wrote %u/%u bytes\n",
                    static_cast<unsigned>(written), static_cast<unsigned>(expected));
    }
    framesRemaining -= frames;
  }

  writeSilence(40);
}

void playBeeps(int count, uint32_t durationMs = SHORT_BEEP_MS) {
  for (int beep = 0; beep < count; ++beep) {
    playTone(BEEP_FREQUENCY_HZ, durationMs);
    if (beep + 1 < count) {
      writeSilence(BEEP_GAP_MS);
    }
  }
}

void discardMicrophoneBacklog() {
  // Clear old microphone frames captured while the speaker was beeping.
  for (int pass = 0; pass < 6; ++pass) {
    audioI2S.readBytes(
      reinterpret_cast<char *>(ioBuffer),
      sizeof(ioBuffer)
    );
  }
}

bool recordMicrophones() {
  Serial.println("RECORDING: speak now for 5 seconds");
  size_t bytesCaptured = 0;

  while (bytesCaptured < RECORD_BUFFER_BYTES) {
    size_t remaining = RECORD_BUFFER_BYTES - bytesCaptured;
    size_t request = min(remaining, sizeof(ioBuffer));
    size_t bytesRead = audioI2S.readBytes(
      reinterpret_cast<char *>(recording) + bytesCaptured,
      request
    );

    if (bytesRead == 0) {
      Serial.printf("ERROR: microphone read failed, code=%d\n", audioI2S.lastError());
      return false;
    }
    bytesCaptured += bytesRead;
  }

  Serial.printf(
    "RECORDING COMPLETE: %u stereo frames\n",
    static_cast<unsigned>(RECORD_FRAME_COUNT)
  );
  return true;
}

void printChannelPeak(size_t channel) {
  int64_t peak = 0;

  for (size_t frame = 0; frame < RECORD_FRAME_COUNT; ++frame) {
    int32_t sample = recording[frame * 2 + channel];
    int64_t magnitude = sample < 0 ? -static_cast<int64_t>(sample) : sample;
    if (magnitude > peak) {
      peak = magnitude;
    }
  }

  Serial.printf(
    "%s peak raw: %lld\n",
    channel == 0 ? "LEFT" : "RIGHT",
    static_cast<long long>(peak)
  );
}

void playRecordedChannel(size_t channel) {
  Serial.println(channel == 0 ? "PLAYBACK: LEFT microphone" : "PLAYBACK: RIGHT microphone");
  size_t frameOffset = 0;

  while (frameOffset < RECORD_FRAME_COUNT) {
    size_t frames = min(RECORD_FRAME_COUNT - frameOffset, IO_FRAMES);

    for (size_t frame = 0; frame < frames; ++frame) {
      int32_t sample =
        recording[(frameOffset + frame) * 2 + channel]
        >> PLAYBACK_ATTENUATION_BITS;

      // Duplicate the selected microphone into both speaker slots.
      ioBuffer[frame * 2] = sample;
      ioBuffer[frame * 2 + 1] = sample;
    }

    size_t expected = frames * 2 * sizeof(int32_t);
    size_t written = audioI2S.write(  // L5: check write return
      reinterpret_cast<uint8_t *>(ioBuffer),
      expected
    );
    if (written != expected) {
      Serial.printf("WARN: playback wrote %u/%u bytes\n",
                    static_cast<unsigned>(written), static_cast<unsigned>(expected));
    }
    frameOffset += frames;
  }

  writeSilence(100);
}

void runTestCycle() {
  Serial.println();
  Serial.println("=== NEW AUDIO TEST CYCLE ===");

  // One long beep: start speaking when this beep ends.
  playBeeps(1, LONG_BEEP_MS);
  writeSilence(ACOUSTIC_SETTLE_MS);
  discardMicrophoneBacklog();

  bool recorded = recordMicrophones();
  if (!recorded) {
    playBeeps(4);
    writeSilence(BETWEEN_CYCLES_MS);
    return;
  }

  printChannelPeak(0);
  printChannelPeak(1);

  // Two short beeps: recording has ended.
  writeSilence(300);
  playBeeps(2);
  writeSilence(BETWEEN_PLAYBACK_MS);

  // One short beep: left microphone playback follows.
  playBeeps(1);
  writeSilence(350);
  playRecordedChannel(0);
  writeSilence(BETWEEN_PLAYBACK_MS);

  // Two short beeps: right microphone playback follows.
  playBeeps(2);
  writeSilence(350);
  playRecordedChannel(1);
  writeSilence(500);

  // Three short beeps: cycle complete.
  playBeeps(3);
  writeSilence(BETWEEN_CYCLES_MS);
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println();
  Serial.println("Robot Bi autonomous dual-mic + speaker test");
  Serial.println("BCLK=4, WS=5, MIC_DATA=6, AMP_DATA=7");

  if (!psramFound()) {
    Serial.println("ERROR: PSRAM not detected.");
    Serial.println("Select Tools > PSRAM > OPI PSRAM, then upload again.");
  }

  recording = static_cast<int32_t *>(ps_malloc(RECORD_BUFFER_BYTES));
  if (recording == nullptr) {
    Serial.printf(
      "ERROR: cannot allocate %u bytes for recording\n",
      static_cast<unsigned>(RECORD_BUFFER_BYTES)
    );
  }

  audioI2S.setPins(
    I2S_BCLK_PIN,
    I2S_WS_PIN,
    I2S_AMP_DATA_PIN,
    I2S_MIC_DATA_PIN
  );

  bool started = audioI2S.begin(
    I2S_MODE_STD,
    SAMPLE_RATE_HZ,
    I2S_DATA_BIT_WIDTH_32BIT,
    I2S_SLOT_MODE_STEREO,
    I2S_STD_SLOT_BOTH
  );

  if (!started) {
    // L4: keep printing so Serial monitor shows the halt reason
    for (;;) {
      Serial.printf("ERROR: I2S initialization failed, code=%d — halted\n", audioI2S.lastError());
      delay(5000);
    }
  }

  if (recording == nullptr) {
    fatalError("PSRAM recording buffer unavailable");
  }

  memset(recording, 0, RECORD_BUFFER_BYTES);
  writeSilence(500);

  // Three startup beeps indicate that firmware, PSRAM, I2S, and speaker started.
  playBeeps(3);
  writeSilence(1500);

  Serial.println("READY");
}

void loop() {
  runTestCycle();
}
