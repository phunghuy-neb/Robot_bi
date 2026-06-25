"""
generate_wakeword_dataset.py — Tạo synthetic dataset "Bi ơi" bằng edge-tts.

Yêu cầu: Internet (edge-tts dùng Microsoft TTS cloud), ffmpeg trong PATH.

Usage:
    python scripts/generate_wakeword_dataset.py
    python scripts/generate_wakeword_dataset.py --positive-only
    python scripts/generate_wakeword_dataset.py --negative-only
    python scripts/generate_wakeword_dataset.py --count 200

Output:
    data/wakeword/positive/  — WAV 16kHz mono
    data/wakeword/negative/  — WAV 16kHz mono

Thời gian: ~10–20 phút tùy kết nối internet.
"""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import time
from itertools import product
from pathlib import Path

import numpy as np

try:
    import soundfile as sf
except ImportError:
    print("ERROR: soundfile not installed. Run: pip install soundfile")
    sys.exit(1)

try:
    import edge_tts
except ImportError:
    print("ERROR: edge-tts not installed. Run: pip install edge-tts")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
POSITIVE_DIR = ROOT / "data" / "wakeword" / "positive"
NEGATIVE_DIR = ROOT / "data" / "wakeword" / "negative"
SAMPLE_RATE = 16000

# ── TTS config ────────────────────────────────────────────────────────────────
VOICES = {
    "female": "vi-VN-HoaiMyNeural",
    "male":   "vi-VN-NamMinhNeural",
}

POSITIVE_PHRASES = [
    "Bi ơi",
    "Bi à",
    "Bi ơi nè",
    "Bi ơi nghe nè",
    "Bi ơi con hỏi",
    "Bi ơi giúp con",
    "Ơ Bi ơi",
    "Này Bi ơi",
]

NEGATIVE_PHRASES = [
    # Similar phonetics — most important for reducing false positives
    "Bình ơi", "Ti ơi", "Mi ơi", "Về ơi", "Đi thôi", "Biết rồi",
    "Con ơi", "Mèo ơi", "Bé ơi", "Ba ơi ba", "Mẹ ơi mẹ",
    # Common Vietnamese household speech
    "Hôm nay ăn gì", "Con làm bài chưa", "Ăn cơm chưa", "Đi ngủ thôi",
    "Xin chào bạn", "Cảm ơn nhé", "Không sao đâu", "Được rồi thôi",
    "Học bài chưa con", "Mẹ về rồi đây", "Con khỏe không",
    "Chờ mẹ một chút", "Có gì không con", "Làm gì vậy con",
    # Numbers and common words
    "Một hai ba bốn năm", "Thứ hai thứ ba thứ tư",
    "Đỏ xanh vàng tím cam", "Mặt trời mặt trăng ngôi sao",
    # Longer sentences
    "Con thích ăn bánh mì không", "Hôm nay thời tiết đẹp quá",
    "Bạn có muốn chơi không", "Đi chơi công viên nhé con",
    "Mẹ yêu con nhiều lắm", "Ngủ ngon nhé con yêu",
]

# edge-tts rate/pitch/volume variation
POSITIVE_RATES   = ["-20%", "-10%", "+0%", "+10%", "+20%", "+30%"]
POSITIVE_PITCHES = ["-5Hz", "+0Hz", "+5Hz", "+10Hz", "+15Hz"]
POSITIVE_VOLUMES = ["-5%", "+0%", "+5%", "+10%"]

NEGATIVE_RATES   = ["-10%", "+0%", "+15%"]
NEGATIVE_PITCHES = ["+0Hz", "+10Hz"]


def check_ffmpeg() -> bool:
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
    """Convert mp3 → wav 16kHz mono using ffmpeg."""
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path,
         "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", wav_path],
        capture_output=True,
    )
    return r.returncode == 0


async def _tts_to_wav(text: str, voice: str, rate: str, pitch: str, volume: str,
                       wav_path: str, tmp_dir: str) -> bool:
    """Generate TTS → save as MP3 → convert to WAV. Returns success."""
    tmp_mp3 = os.path.join(tmp_dir, "tmp.mp3")
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
        await communicate.save(tmp_mp3)
        if not os.path.exists(tmp_mp3) or os.path.getsize(tmp_mp3) < 100:
            return False
        return mp3_to_wav(tmp_mp3, wav_path)
    except Exception as e:
        print(f"  ✗ TTS error ({text!r}): {e}")
        return False
    finally:
        if os.path.exists(tmp_mp3):
            os.remove(tmp_mp3)


async def generate_positive(target: int, tmp_dir: str) -> int:
    """Generate positive samples. Returns number of files created."""
    POSITIVE_DIR.mkdir(parents=True, exist_ok=True)
    existing = len(list(POSITIVE_DIR.glob("bi_oi_*.wav")))
    counter = existing + 1
    created = 0

    combos = list(product(POSITIVE_PHRASES, VOICES.items(), POSITIVE_RATES, POSITIVE_PITCHES, POSITIVE_VOLUMES))
    # Shuffle for variety if we hit target early
    import random; random.shuffle(combos)

    print(f"\n[POSITIVE] Generating up to {target} samples (existing: {existing})...")

    for phrase, (vname, voice), rate, pitch, volume in combos:
        if counter - existing - 1 >= target:
            break
        slug = phrase.lower().replace(" ", "_").replace("ơ", "o").replace("à", "a").replace("è", "e")
        fname = f"bi_oi_{vname}_{slug}_r{rate}_p{pitch}_v{volume}_{counter:04d}.wav"
        fname = fname.replace("+", "p").replace("-", "m").replace("%", "").replace("Hz", "hz")
        out_path = str(POSITIVE_DIR / fname)

        ok = await _tts_to_wav(phrase, voice, rate, pitch, volume, out_path, tmp_dir)
        if ok:
            created += 1
            counter += 1
            if created % 20 == 0:
                print(f"  {created} positive samples created...")
        await asyncio.sleep(0.3)  # avoid rate limiting

    print(f"[POSITIVE] Done: {created} new files (total: {existing + created})")
    return created


async def generate_negative(target: int, tmp_dir: str) -> int:
    """Generate negative samples. Returns number of files created."""
    NEGATIVE_DIR.mkdir(parents=True, exist_ok=True)
    existing = len(list(NEGATIVE_DIR.glob("neg_*.wav")))
    counter = existing + 1
    created = 0

    combos = list(product(NEGATIVE_PHRASES, VOICES.items(), NEGATIVE_RATES, NEGATIVE_PITCHES))
    import random; random.shuffle(combos)

    print(f"\n[NEGATIVE] Generating up to {target} samples (existing: {existing})...")

    for phrase, (vname, voice), rate, pitch in combos:
        if counter - existing - 1 >= target:
            break
        slug = phrase[:15].lower().replace(" ", "_")
        for c in "ơàáạảãăâđêếềệểễôốồổỗùúụủũưừứựửữ":
            slug = slug.replace(c, "x")
        fname = f"neg_{vname}_{slug}_{counter:04d}.wav"
        out_path = str(NEGATIVE_DIR / fname)

        ok = await _tts_to_wav(phrase, voice, rate, pitch, "+0%", out_path, tmp_dir)
        if ok:
            created += 1
            counter += 1
            if created % 20 == 0:
                print(f"  {created} negative samples created...")
        await asyncio.sleep(0.3)

    # Also generate silence + noise negative samples (no TTS needed)
    noise_count = min(30, target // 5)
    print(f"[NEGATIVE] Generating {noise_count} noise-only samples...")
    noise_created = _generate_noise_negatives(noise_count, existing + created + 1)
    created += noise_created

    print(f"[NEGATIVE] Done: {created} new files (total: {existing + created})")
    return created


def _generate_noise_negatives(count: int, start_idx: int) -> int:
    """Generate pure noise/silence negative samples using numpy."""
    NEGATIVE_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    rng = np.random.default_rng(42)

    noise_types = ["whitenoise", "silence", "pinknoise", "brownnoise"]

    for i in range(count):
        duration = rng.uniform(1.0, 3.0)
        n_samples = int(SAMPLE_RATE * duration)
        noise_type = noise_types[i % len(noise_types)]

        if noise_type == "silence":
            audio = rng.normal(0, 0.0005, n_samples).astype(np.float32)
        elif noise_type == "whitenoise":
            audio = rng.normal(0, rng.uniform(0.01, 0.05), n_samples).astype(np.float32)
        elif noise_type == "pinknoise":
            white = rng.normal(0, 1, n_samples)
            # Simple pink noise approximation via cumulative sum
            audio = np.cumsum(white) * 0.01
            audio = (audio / (np.abs(audio).max() + 1e-9) * 0.03).astype(np.float32)
        else:  # brownnoise
            white = rng.normal(0, 1, n_samples)
            audio = np.cumsum(white) * 0.001
            audio = (audio / (np.abs(audio).max() + 1e-9) * 0.02).astype(np.float32)

        fname = f"neg_noise_{noise_type}_{start_idx + i:04d}.wav"
        sf.write(str(NEGATIVE_DIR / fname), audio, SAMPLE_RATE)
        created += 1

    return created


async def main():
    parser = argparse.ArgumentParser(description="Tạo synthetic wake word dataset")
    parser.add_argument("--positive-only", action="store_true")
    parser.add_argument("--negative-only", action="store_true")
    parser.add_argument("--count", type=int, default=None,
                        help="Override target count (applies to both positive and negative)")
    args = parser.parse_args()

    print("=" * 60)
    print("Robot Bi — Wake Word Dataset Generator")
    print("=" * 60)

    if not check_ffmpeg():
        print("\nERROR: ffmpeg not found in PATH.")
        print("Install: winget install ffmpeg  (hoặc tải từ https://ffmpeg.org)")
        print("Sau đó restart terminal và chạy lại.")
        sys.exit(1)
    print("✓ ffmpeg found")

    pos_target = args.count or 300
    neg_target = args.count or 150

    with tempfile.TemporaryDirectory() as tmp_dir:
        t0 = time.time()
        total = 0

        if not args.negative_only:
            total += await generate_positive(pos_target, tmp_dir)

        if not args.positive_only:
            total += await generate_negative(neg_target, tmp_dir)

        elapsed = time.time() - t0

    pos_count = len(list(POSITIVE_DIR.glob("*.wav")))
    neg_count = len(list(NEGATIVE_DIR.glob("*.wav")))

    print("\n" + "=" * 60)
    print(f"Dataset generation complete ({elapsed:.0f}s)")
    print(f"  Positive: {pos_count} files → {POSITIVE_DIR}")
    print(f"  Negative: {neg_count} files → {NEGATIVE_DIR}")
    print()
    if pos_count < 50:
        print("⚠ Cần ít nhất 50 positive samples để train. Thêm sample hoặc tăng --count.")
    elif pos_count < 150:
        print("⚡ Đủ để train prototype. Thêm sample sau để tăng accuracy.")
    else:
        print("✓ Dataset đủ tốt để train v0.")
    print()
    print("Bước tiếp theo:")
    print("  python scripts/augment_audio.py")
    print("  python scripts/train_wakeword.py")


if __name__ == "__main__":
    asyncio.run(main())
