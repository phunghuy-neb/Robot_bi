/*
  Robot Bi - ESP32-S3 MAX98357A speaker-only test

  Target:
    ESP32-S3 N16R8
    Arduino ESP32 core 3.x

  Wiring:
    GPIO4 -> BCLK on MAX98357A
    GPIO5 -> LRC/LRCLK on MAX98357A
    GPIO7 -> DIN on MAX98357A
    5V    -> VIN on MAX98357A
    GND   -> GND on MAX98357A
    3V3   -> SD/EN on MAX98357A if the module does not enable itself
    Speaker -> SPK+ and SPK- (never connect SPK- to GND)

  The test repeats five loud 1000 Hz beeps.

  No microphone or PSRAM is used.
*/

#include <Arduino.h>
#include "ESP_I2S.h"
#include <math.h>

constexpr int I2S_BCLK_PIN = 4;
constexpr int I2S_WS_PIN = 5;
constexpr int I2S_AMP_DATA_PIN = 7;

constexpr uint32_t SAMPLE_RATE_HZ = 44100;
constexpr size_t FRAMES_PER_BLOCK = 256;
// About -8.7 dBFS in signed 16-bit PCM.
constexpr int16_t TONE_AMPLITUDE = 12000;
constexpr float BEEP_FREQUENCY_HZ = 1000.0f;
constexpr uint32_t TONE_MS = 550;
constexpr uint32_t TONE_GAP_MS = 250;
constexpr uint32_t CYCLE_GAP_MS = 2000;
constexpr uint32_t FADE_MS = 12;

I2SClass speakerI2S;
int16_t sampleBuffer[FRAMES_PER_BLOCK * 2];

void writeSilence(uint32_t durationMs) {
  memset(sampleBuffer, 0, sizeof(sampleBuffer));
  size_t framesRemaining =
    static_cast<size_t>(SAMPLE_RATE_HZ) * durationMs / 1000;

  while (framesRemaining > 0) {
    size_t frames = min(framesRemaining, FRAMES_PER_BLOCK);
    size_t bytes = frames * 2 * sizeof(int16_t);
    size_t written = speakerI2S.write(
      reinterpret_cast<uint8_t *>(sampleBuffer),
      bytes
    );
    if (written != bytes) {
      Serial.printf(
        "ERROR: silence write failed, expected=%u written=%u code=%d\n",
        static_cast<unsigned>(bytes),
        static_cast<unsigned>(written),
        speakerI2S.lastError()
      );
      return;
    }
    framesRemaining -= frames;
  }
}

bool playTone(float frequencyHz, uint32_t durationMs) {
  size_t framesRemaining =
    static_cast<size_t>(SAMPLE_RATE_HZ) * durationMs / 1000;
  size_t totalFrames = framesRemaining;
  size_t fadeFrames = static_cast<size_t>(SAMPLE_RATE_HZ) * FADE_MS / 1000;
  uint32_t phaseFrame = 0;

  Serial.printf("PLAY %.0f Hz for %u ms\n", frequencyHz, durationMs);

  while (framesRemaining > 0) {
    size_t frames = min(framesRemaining, FRAMES_PER_BLOCK);

    for (size_t frame = 0; frame < frames; ++frame) {
      float phase =
        2.0f * PI * frequencyHz * phaseFrame / SAMPLE_RATE_HZ;
      size_t absoluteFrame = totalFrames - framesRemaining + frame;
      float envelope = 1.0f;
      if (absoluteFrame < fadeFrames) {
        envelope = static_cast<float>(absoluteFrame) / fadeFrames;
      } else if (absoluteFrame + fadeFrames > totalFrames) {
        envelope =
          static_cast<float>(totalFrames - absoluteFrame) / fadeFrames;
      }
      int16_t sample =
        static_cast<int16_t>(sinf(phase) * TONE_AMPLITUDE * envelope);

      // Write the same tone to both I2S slots.
      sampleBuffer[frame * 2] = sample;
      sampleBuffer[frame * 2 + 1] = sample;
      ++phaseFrame;
    }

    size_t bytes = frames * 2 * sizeof(int16_t);
    size_t written = speakerI2S.write(
      reinterpret_cast<uint8_t *>(sampleBuffer),
      bytes
    );
    if (written != bytes) {
      Serial.printf(
        "ERROR: tone write failed, expected=%u written=%u code=%d\n",
        static_cast<unsigned>(bytes),
        static_cast<unsigned>(written),
        speakerI2S.lastError()
      );
      return false;
    }
    framesRemaining -= frames;
  }

  writeSilence(60);
  return true;
}

void playCountedTones(int count, float frequencyHz) {
  for (int tone = 0; tone < count; ++tone) {
    if (!playTone(frequencyHz, TONE_MS)) {
      return;
    }
    if (tone + 1 < count) {
      writeSilence(TONE_GAP_MS);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println();
  Serial.println("Robot Bi MAX98357A speaker-only test");
  Serial.println("BCLK=GPIO4, LRC=GPIO5, DIN=GPIO7");
  Serial.println("Format: 44.1 kHz, stereo, signed 16-bit PCM");
  Serial.println("No microphone or PSRAM is required.");

  speakerI2S.setPins(
    I2S_BCLK_PIN,
    I2S_WS_PIN,
    I2S_AMP_DATA_PIN,
    -1
  );

  bool started = speakerI2S.begin(
    I2S_MODE_STD,
    SAMPLE_RATE_HZ,
    I2S_DATA_BIT_WIDTH_16BIT,
    I2S_SLOT_MODE_STEREO,
    I2S_STD_SLOT_BOTH
  );

  if (!started) {
    Serial.printf(
      "FATAL: I2S initialization failed, code=%d\n",
      speakerI2S.lastError()
    );
    while (true) {
      delay(1000);
    }
  }

  writeSilence(500);
  Serial.println("READY: tones will repeat continuously");
}

void loop() {
  Serial.println();
  Serial.println("=== FIVE LOUD BEEPS ===");
  playCountedTones(5, BEEP_FREQUENCY_HZ);
  writeSilence(CYCLE_GAP_MS);
}
