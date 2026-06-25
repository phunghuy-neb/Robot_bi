"""
test_wakeword.py — Quick test harness cho wake word "Bi ơi".

Usage:
    python scripts/test_wakeword.py                        # real-time mic test
    python scripts/test_wakeword.py --check-dataset        # kiểm tra dataset
    python scripts/test_wakeword.py --file audio.wav       # test 1 file WAV
    python scripts/test_wakeword.py --backend whisper      # dùng whisper backend
    python scripts/test_wakeword.py --threshold 0.6        # đổi threshold

Output khi detect:
    [DETECTED] confidence=0.87 | latency=1.24s | backend=custom_mfcc

Ctrl+C để thoát.
"""

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

SAMPLE_RATE = 16000
CHUNK_MS    = 80
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_MS / 1000)


# ── Dataset check ──────────────────────────────────────────────────────────────

def check_dataset():
    """Check dataset quality and print report."""
    import soundfile as sf

    pos_dir = ROOT / "data" / "wakeword" / "positive"
    neg_dir = ROOT / "data" / "wakeword" / "negative"
    model_path = ROOT / "runtime" / "wakeword" / "bi_oi_classifier.pkl"

    print("=" * 60)
    print("Wake Word Dataset Check")
    print("=" * 60)

    def scan_dir(d: Path, label: str):
        if not d.exists():
            print(f"\n{label}: directory not found ({d})")
            return

        files = list(d.glob("*.wav"))
        print(f"\n{label}: {len(files)} WAV files")

        ok, bad_format, too_short, too_long = 0, 0, 0, 0
        durations = []

        for f in files:
            try:
                info = sf.info(str(f))
                dur = info.frames / info.samplerate
                if info.channels != 1 or info.samplerate != SAMPLE_RATE:
                    bad_format += 1
                elif dur < 0.3:
                    too_short += 1
                elif dur > 5.0:
                    too_long += 1
                else:
                    ok += 1
                    durations.append(dur)
            except Exception as e:
                bad_format += 1

        print(f"  OK: {ok}")
        if bad_format:  print(f"  Bad format/corrupt: {bad_format}")
        if too_short:   print(f"  Too short (<0.3s): {too_short}")
        if too_long:    print(f"  Too long (>5s): {too_long}")
        if durations:
            print(f"  Duration: min={min(durations):.2f}s, max={max(durations):.2f}s, "
                  f"mean={np.mean(durations):.2f}s")

    scan_dir(pos_dir, "POSITIVE")
    scan_dir(neg_dir, "NEGATIVE")

    print(f"\nModel: {'✓ exists' if model_path.exists() else '✗ not found'} ({model_path})")

    pos_count = len(list(pos_dir.glob("*.wav"))) if pos_dir.exists() else 0
    neg_count = len(list(neg_dir.glob("*.wav"))) if neg_dir.exists() else 0

    print()
    if pos_count == 0:
        print("⚠ Chưa có positive samples — chạy: python scripts/generate_wakeword_dataset.py")
    elif pos_count < 50:
        print(f"⚠ Chỉ có {pos_count} positive samples (cần 50+)")
    else:
        print(f"✓ {pos_count} positive samples (đủ để train)")

    if neg_count == 0:
        print("⚠ Chưa có negative samples")
    elif neg_count < 100:
        print(f"⚡ {neg_count} negative samples (tối thiểu 100 để giảm false positive)")
    else:
        print(f"✓ {neg_count} negative samples")

    if not model_path.exists():
        print("⚠ Model chưa train — chạy: python scripts/train_wakeword.py")


# ── Custom MFCC detection (standalone, mirrors wakeword_service.py) ───────────

def _load_custom_model(model_path: str):
    import pickle
    with open(model_path, "rb") as f:
        return pickle.load(f)


def _compute_mfcc(audio: np.ndarray, sr: int = SAMPLE_RATE,
                  n_mfcc: int = 20, n_mels: int = 40,
                  n_fft: int = 512, hop_len: int = 160) -> np.ndarray:
    """Same MFCC computation as train_wakeword.py + wakeword_service.py."""
    import scipy.fftpack
    import scipy.signal

    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio / peak

    audio = np.append(audio[0], audio[1:] - 0.97 * audio[:-1]).astype(np.float32)

    _, _, Zxx = scipy.signal.stft(audio, fs=sr, nperseg=n_fft,
                                   noverlap=n_fft - hop_len, boundary=None)
    power = np.abs(Zxx) ** 2

    # Build mel bank
    def hz_to_mel(hz): return 2595 * np.log10(1 + hz / 700)
    def mel_to_hz(m):  return 700 * (10 ** (m / 2595) - 1)

    mel_pts = np.linspace(hz_to_mel(0), hz_to_mel(sr / 2), n_mels + 2)
    hz_pts  = mel_to_hz(mel_pts)
    bins    = np.floor((n_fft + 1) * hz_pts / sr).astype(int)

    fbank = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        lo, mid, hi = bins[m - 1], bins[m], bins[m + 1]
        for k in range(lo, mid):
            if mid > lo: fbank[m - 1, k] = (k - lo) / (mid - lo)
        for k in range(mid, hi):
            if hi > mid: fbank[m - 1, k] = (hi - k) / (hi - mid)

    mel   = fbank @ power
    log_m = np.log(mel + 1e-9)
    mfcc  = scipy.fftpack.dct(log_m, type=2, axis=0, norm='ortho')[:n_mfcc]
    delta = np.diff(mfcc, n=1, axis=1, prepend=mfcc[:, :1])

    return np.concatenate([mfcc.mean(axis=1), mfcc.std(axis=1), delta.mean(axis=1)])


# ── File test mode ─────────────────────────────────────────────────────────────

def test_file(wav_path: str, backend: str, threshold: float, model_path: str):
    """Test detection on a single WAV file."""
    import soundfile as sf

    audio, sr = sf.read(wav_path, dtype='float32')
    if audio.ndim > 1:
        audio = audio[:, 0]

    print(f"Testing: {wav_path} ({len(audio)/sr:.2f}s)")

    if backend == "custom_mfcc":
        if not os.path.exists(model_path):
            print(f"Model not found: {model_path}")
            print("Run: python scripts/train_wakeword.py")
            return

        payload = _load_custom_model(model_path)
        scaler  = payload["scaler"]
        model   = payload["model"]
        cfg     = payload.get("config", {})

        feat = _compute_mfcc(audio, sr,
                             n_mfcc=cfg.get("n_mfcc", 20),
                             n_mels=cfg.get("n_mels", 40),
                             n_fft=cfg.get("n_fft", 512),
                             hop_len=cfg.get("hop_len", 160))

        feat_scaled = scaler.transform(feat.reshape(1, -1))
        pred = model.predict(feat_scaled)[0]
        prob = model.predict_proba(feat_scaled)[0]
        confidence = prob[1]  # probability of class=1 (positive)

        result = "DETECTED" if pred == 1 and confidence >= threshold else "not detected"
        print(f"  [{result}] confidence={confidence:.3f} | threshold={threshold}")

    elif backend == "whisper":
        from faster_whisper import WhisperModel
        wm = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = wm.transcribe(audio, language="vi", beam_size=1)
        text = " ".join(s.text for s in segments).lower()
        wake_variants = ["bi ơi", "bị ơi", "bi ui", "bi oi", "bị ui"]
        hit = any(w in text for w in wake_variants)
        print(f"  Transcript: {text!r}")
        print(f"  {'[DETECTED]' if hit else 'not detected'}")


# ── Real-time mic test ─────────────────────────────────────────────────────────

def test_realtime(backend: str, threshold: float, model_path: str, timeout: int):
    """Real-time mic detection test."""
    try:
        import sounddevice as sd
    except ImportError:
        print("ERROR: sounddevice not installed. Run: pip install sounddevice")
        sys.exit(1)

    print("=" * 60)
    print(f"Real-time Wake Word Test — backend={backend}, threshold={threshold}")
    print("Nói 'Bi ơi' để test. Ctrl+C để thoát.")
    print("=" * 60)

    payload    = None
    scaler     = None
    clf_model  = None
    whisper_m  = None

    if backend == "custom_mfcc":
        if not os.path.exists(model_path):
            print(f"Model not found: {model_path}")
            print("Run: python scripts/train_wakeword.py")
            sys.exit(1)
        payload   = _load_custom_model(model_path)
        scaler    = payload["scaler"]
        clf_model = payload["model"]
        cfg       = payload.get("config", {})
        print(f"Model loaded: F1={payload['metrics'].get('cv_f1_mean', '?'):.2f}")

    elif backend == "whisper":
        from faster_whisper import WhisperModel
        print("Loading whisper tiny...")
        whisper_m = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("Loaded.")

    # Rolling buffer for accumulating audio
    buffer = []
    window_sec = 1.5
    window_frames = int(SAMPLE_RATE * window_sec)
    overlap_frames = window_frames // 2

    last_detected_at = 0
    cooldown_sec = 2.0
    detect_count = 0
    start_time = time.time()

    def audio_callback(indata, frames, time_info, status):
        nonlocal buffer
        chunk = indata[:, 0].astype(np.float32)  # mono
        buffer.extend(chunk.tolist())

    print("\nListening...\n")

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            blocksize=CHUNK_FRAMES, callback=audio_callback):
            while True:
                time.sleep(0.05)

                if len(buffer) < window_frames:
                    continue

                now = time.time()
                if now - last_detected_at < cooldown_sec:
                    continue  # in cooldown

                window = np.array(buffer[-window_frames:], dtype=np.float32)
                buffer = buffer[-overlap_frames:]  # keep overlap

                # Energy gate
                rms = np.sqrt(np.mean(window ** 2))
                if rms < 0.001:
                    continue

                t_detect_start = time.time()
                detected = False
                confidence = 0.0

                if backend == "custom_mfcc":
                    feat = _compute_mfcc(window, SAMPLE_RATE,
                                         n_mfcc=cfg.get("n_mfcc", 20),
                                         n_mels=cfg.get("n_mels", 40),
                                         n_fft=cfg.get("n_fft", 512),
                                         hop_len=cfg.get("hop_len", 160))
                    feat_s = scaler.transform(feat.reshape(1, -1))
                    pred = clf_model.predict(feat_s)[0]
                    prob = clf_model.predict_proba(feat_s)[0]
                    confidence = prob[1]
                    detected = pred == 1 and confidence >= threshold

                elif backend == "whisper":
                    from faster_whisper import WhisperModel
                    segs, _ = whisper_m.transcribe(window, language="vi", beam_size=1)
                    text = " ".join(s.text for s in segs).lower()
                    wake_v = ["bi ơi", "bị ơi", "bi ui", "bi oi"]
                    detected = any(w in text for w in wake_v)
                    confidence = 1.0 if detected else 0.0

                latency = time.time() - t_detect_start
                elapsed_total = now - start_time

                if detected:
                    detect_count += 1
                    last_detected_at = time.time()
                    print(f"[{elapsed_total:6.1f}s] *** DETECTED *** "
                          f"confidence={confidence:.3f} | latency={latency:.3f}s | "
                          f"count={detect_count}")
                else:
                    # Show periodic "listening" heartbeat
                    if int(elapsed_total) % 5 == 0 and elapsed_total > 1:
                        print(f"[{elapsed_total:6.1f}s] listening... "
                              f"(rms={rms:.4f}, conf={confidence:.3f})",
                              end="\r")

                if timeout > 0 and elapsed_total > timeout:
                    print(f"\nTimeout ({timeout}s). Detected {detect_count} times.")
                    break

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n\nSession ended. {detect_count} detections in {elapsed:.0f}s.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    default_model = str(ROOT / "runtime" / "wakeword" / "bi_oi_classifier.pkl")

    parser = argparse.ArgumentParser(description="Test wake word detector")
    parser.add_argument("--check-dataset",  action="store_true", help="Kiểm tra dataset")
    parser.add_argument("--file",           type=str,   default=None,  help="Test một file WAV")
    parser.add_argument("--backend",        type=str,   default="custom_mfcc",
                        choices=["custom_mfcc", "whisper"], help="Backend sử dụng")
    parser.add_argument("--threshold",      type=float, default=0.5,   help="Detection threshold")
    parser.add_argument("--model-path",     type=str,   default=default_model)
    parser.add_argument("--timeout",        type=int,   default=0,
                        help="Auto-stop after N seconds (0 = infinite)")
    args = parser.parse_args()

    if args.check_dataset:
        check_dataset()
        return

    if args.file:
        test_file(args.file, args.backend, args.threshold, args.model_path)
        return

    test_realtime(args.backend, args.threshold, args.model_path, args.timeout)


if __name__ == "__main__":
    main()
