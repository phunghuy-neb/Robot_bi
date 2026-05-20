"""
augment_audio.py — Augment wake word dataset để simulate môi trường thật.

Usage:
    python scripts/augment_audio.py                    # augment cả positive + negative
    python scripts/augment_audio.py --dir positive     # chỉ augment positive
    python scripts/augment_audio.py --factor 3         # tạo 3x dataset

Augmentations:
    - Noise addition (white, pink, fan, TV-like)
    - Speed variation (0.85x – 1.20x)
    - Pitch shift (via resample trick)
    - Gain variation (volume)
    - Room reverb simulation (exponential decay)
    - Phone mic simulation (bandpass + distortion)

Output: thêm files _augN vào cùng thư mục (không xóa originals).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import scipy.signal
import soundfile as sf

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "wakeword"
SAMPLE_RATE = 16000


# ── Core augmentation functions ───────────────────────────────────────────────

def add_noise(audio: np.ndarray, snr_db: float) -> np.ndarray:
    """Add white Gaussian noise at given SNR."""
    signal_power = np.mean(audio ** 2)
    if signal_power < 1e-12:
        return audio
    noise_power = signal_power / (10 ** (snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power), len(audio))
    return (audio + noise).astype(np.float32)


def add_background_noise(audio: np.ndarray, noise_type: str, level: float = 0.03) -> np.ndarray:
    """Add simulated background noise (fan, TV, kitchen)."""
    n = len(audio)
    rng = np.random.default_rng()

    if noise_type == "fan":
        # Fan: colored noise (low-frequency dominant)
        white = rng.normal(0, 1, n)
        b, a = scipy.signal.butter(1, 0.1, btype='low')
        noise = scipy.signal.lfilter(b, a, white)
    elif noise_type == "tv":
        # TV-like: broadband with some speech-frequency peaks
        white = rng.normal(0, 1, n)
        b, a = scipy.signal.butter(2, [0.05, 0.4], btype='band')
        noise = scipy.signal.lfilter(b, a, white)
    elif noise_type == "kitchen":
        # Kitchen: high-frequency water/sizzle
        white = rng.normal(0, 1, n)
        b, a = scipy.signal.butter(2, 0.3, btype='high')
        noise = scipy.signal.lfilter(b, a, white)
    else:  # white
        noise = rng.normal(0, 1, n)

    noise = noise / (np.abs(noise).max() + 1e-9)
    return (audio + noise * level).astype(np.float32)


def change_speed(audio: np.ndarray, rate: float) -> np.ndarray:
    """Change speed (and pitch) via resampling. rate > 1 = faster."""
    n_out = max(1, int(len(audio) / rate))
    resampled = scipy.signal.resample(audio, n_out)
    return resampled.astype(np.float32)


def pitch_shift_approx(audio: np.ndarray, semitones: float) -> np.ndarray:
    """
    Approximate pitch shift via oversample → resample back.
    Changes pitch without significantly changing speed.
    ±2 semitones is accurate enough for wake word variation.
    """
    factor = 2 ** (semitones / 12)
    n_up = int(len(audio) * factor)
    upsampled = scipy.signal.resample(audio, n_up)
    # Resample back to original length
    back = scipy.signal.resample(upsampled, len(audio))
    return back.astype(np.float32)


def change_gain(audio: np.ndarray, db: float) -> np.ndarray:
    """Apply gain in dB."""
    factor = 10 ** (db / 20)
    return np.clip(audio * factor, -1.0, 1.0).astype(np.float32)


def apply_reverb(audio: np.ndarray, room_size: float = 0.3, damping: float = 0.5) -> np.ndarray:
    """Simple room reverb using exponential decay impulse response."""
    ir_len = int(SAMPLE_RATE * room_size)
    t = np.linspace(0, room_size, ir_len)
    ir = np.exp(-damping * t / room_size) * np.random.randn(ir_len)
    ir = (ir / np.abs(ir).max()).astype(np.float32)
    reverbed = scipy.signal.fftconvolve(audio, ir, mode='full')[:len(audio)]
    # Mix dry + wet
    wet_level = 0.25
    mixed = audio * (1 - wet_level) + reverbed * wet_level
    return np.clip(mixed, -1.0, 1.0).astype(np.float32)


def phone_mic_sim(audio: np.ndarray) -> np.ndarray:
    """Simulate phone/laptop mic: bandpass + slight compression."""
    # Bandpass 300–3400 Hz (telephone range)
    b, a = scipy.signal.butter(4, [300 / (SAMPLE_RATE / 2), 3400 / (SAMPLE_RATE / 2)], btype='band')
    filtered = scipy.signal.lfilter(b, a, audio)
    # Soft clipping compression
    compressed = np.tanh(filtered * 2) * 0.5
    return compressed.astype(np.float32)


def far_mic_sim(audio: np.ndarray) -> np.ndarray:
    """Simulate far microphone: attenuate + light reverb."""
    attenuated = audio * 0.4
    return apply_reverb(attenuated, room_size=0.5, damping=0.3)


# ── Augmentation pipeline ─────────────────────────────────────────────────────

AUGMENTATIONS = [
    ("noise_low",    lambda a: add_noise(a, snr_db=25)),
    ("noise_med",    lambda a: add_noise(a, snr_db=15)),
    ("noise_high",   lambda a: add_noise(a, snr_db=8)),
    ("bg_fan",       lambda a: add_background_noise(a, "fan",     level=0.02)),
    ("bg_tv",        lambda a: add_background_noise(a, "tv",      level=0.03)),
    ("bg_kitchen",   lambda a: add_background_noise(a, "kitchen", level=0.025)),
    ("speed_slow",   lambda a: change_speed(a, rate=0.85)),
    ("speed_fast",   lambda a: change_speed(a, rate=1.20)),
    ("pitch_up2",    lambda a: pitch_shift_approx(a, semitones=+2)),
    ("pitch_dn2",    lambda a: pitch_shift_approx(a, semitones=-2)),
    ("pitch_up4",    lambda a: pitch_shift_approx(a, semitones=+4)),   # child-ish
    ("gain_low",     lambda a: change_gain(a, db=-8)),
    ("gain_high",    lambda a: change_gain(a, db=+6)),
    ("reverb_sm",    lambda a: apply_reverb(a, room_size=0.2, damping=0.6)),
    ("reverb_lg",    lambda a: apply_reverb(a, room_size=0.6, damping=0.3)),
    ("phone_mic",    lambda a: phone_mic_sim(a)),
    ("far_mic",      lambda a: far_mic_sim(a)),
    ("noise_reverb", lambda a: apply_reverb(add_noise(a, snr_db=18), room_size=0.3)),
]


def augment_file(wav_path: Path, augmentations: list, prefix: str) -> int:
    """Apply selected augmentations to one WAV file. Returns count created."""
    try:
        audio, sr = sf.read(str(wav_path), dtype='float32')
    except Exception as e:
        print(f"  ✗ Cannot read {wav_path.name}: {e}")
        return 0

    if audio.ndim > 1:
        audio = audio[:, 0]  # mono

    # Resample if needed
    if sr != SAMPLE_RATE:
        n_new = int(len(audio) * SAMPLE_RATE / sr)
        audio = scipy.signal.resample(audio, n_new).astype(np.float32)

    created = 0
    stem = wav_path.stem

    for aug_name, aug_fn in augmentations:
        out_path = wav_path.parent / f"{stem}_{aug_name}.wav"
        if out_path.exists():
            continue
        try:
            aug_audio = aug_fn(audio)
            # Normalize to prevent clipping
            peak = np.abs(aug_audio).max()
            if peak > 0.95:
                aug_audio = aug_audio / peak * 0.92
            sf.write(str(out_path), aug_audio, SAMPLE_RATE)
            created += 1
        except Exception as e:
            print(f"  ✗ {aug_name} failed on {wav_path.name}: {e}")

    return created


def augment_directory(data_dir: Path, factor: int, label: str) -> int:
    """Augment all WAV files in a directory. factor controls how many augmentations per file."""
    # Only augment original files (not already-augmented ones)
    originals = [f for f in data_dir.glob("*.wav") if "_aug" not in f.stem
                 and not any(aug in f.stem for aug, _ in AUGMENTATIONS)]

    if not originals:
        print(f"  No original WAV files found in {data_dir}")
        return 0

    # Select augmentations based on factor
    selected = AUGMENTATIONS[:min(factor * 3, len(AUGMENTATIONS))]

    print(f"\n[{label.upper()}] {len(originals)} original files × {len(selected)} augmentations...")
    total = 0
    for i, wav_path in enumerate(originals):
        count = augment_file(wav_path, selected, label)
        total += count
        if (i + 1) % 30 == 0:
            print(f"  Processed {i + 1}/{len(originals)} files, {total} augmented...")

    return total


def main():
    parser = argparse.ArgumentParser(description="Augment wake word audio dataset")
    parser.add_argument("--dir", choices=["positive", "negative", "both"], default="both")
    parser.add_argument("--factor", type=int, default=4,
                        help="Augmentation factor: how many aug types per file (1-6, default=4)")
    args = parser.parse_args()

    factor = max(1, min(6, args.factor))
    total_created = 0

    print("=" * 60)
    print("Robot Bi — Wake Word Dataset Augmentation")
    print(f"Factor: {factor} augmentation types per file")
    print("=" * 60)

    if args.dir in ("positive", "both"):
        pos_dir = DATA_DIR / "positive"
        if pos_dir.exists():
            n = augment_directory(pos_dir, factor, "positive")
            total_created += n
            print(f"[POSITIVE] Created {n} augmented files")
        else:
            print(f"[POSITIVE] Directory not found: {pos_dir}")
            print("  Run: python scripts/generate_wakeword_dataset.py first")

    if args.dir in ("negative", "both"):
        neg_dir = DATA_DIR / "negative"
        if neg_dir.exists():
            n = augment_directory(neg_dir, factor, "negative")
            total_created += n
            print(f"[NEGATIVE] Created {n} augmented files")
        else:
            print(f"[NEGATIVE] Directory not found: {neg_dir}")

    pos_total = len(list((DATA_DIR / "positive").glob("*.wav"))) if (DATA_DIR / "positive").exists() else 0
    neg_total = len(list((DATA_DIR / "negative").glob("*.wav"))) if (DATA_DIR / "negative").exists() else 0

    print("\n" + "=" * 60)
    print(f"Augmentation complete. Created {total_created} new files.")
    print(f"  Positive total: {pos_total} files")
    print(f"  Negative total: {neg_total} files")
    print()
    print("Bước tiếp theo:")
    print("  python scripts/train_wakeword.py")


if __name__ == "__main__":
    main()
