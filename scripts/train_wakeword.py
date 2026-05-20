"""
train_wakeword.py — Train MFCC + SVM classifier cho wake word "Bi ơi".

Strategy: MFCC feature extraction (scipy+numpy) + SVM với RBF kernel.
Output: runtime/wakeword/bi_oi_classifier.pkl

Không cần GPU. Không cần dataset khổng lồ.
Train time: ~2–10 phút trên CPU với 500–2000 samples.

Usage:
    python scripts/train_wakeword.py
    python scripts/train_wakeword.py --eval-only          # chỉ đánh giá model có sẵn
    python scripts/train_wakeword.py --show-confusion     # in confusion matrix

Requirements:
    pip install scikit-learn
    (soundfile, numpy, scipy đã có trong requirements.txt)

Target accuracy: 75–85% (usable prototype)
"""

import argparse
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import scipy.fftpack
import scipy.signal
import soundfile as sf

ROOT = Path(__file__).parent.parent
POSITIVE_DIR = ROOT / "data" / "wakeword" / "positive"
NEGATIVE_DIR = ROOT / "data" / "wakeword" / "negative"
MODEL_OUTPUT  = ROOT / "runtime" / "wakeword" / "bi_oi_classifier.pkl"
SAMPLE_RATE   = 16000

# MFCC config — must match wakeword_service.py
N_MFCC    = 20
N_MELS    = 40
N_FFT     = 512
HOP_LEN   = 160   # 10ms at 16kHz


# ── MFCC feature extraction (scipy + numpy, no librosa needed) ────────────────

def _mel_filterbank(sr: int, n_fft: int, n_mels: int,
                    fmin: float = 0.0, fmax: float = None) -> np.ndarray:
    """Build mel filterbank matrix. Returns (n_mels, n_fft//2+1)."""
    if fmax is None:
        fmax = sr / 2

    def hz_to_mel(hz):
        return 2595 * np.log10(1 + hz / 700)

    def mel_to_hz(mel):
        return 700 * (10 ** (mel / 2595) - 1)

    mel_low  = hz_to_mel(fmin)
    mel_high = hz_to_mel(fmax)
    mel_pts  = np.linspace(mel_low, mel_high, n_mels + 2)
    hz_pts   = mel_to_hz(mel_pts)
    bins     = np.floor((n_fft + 1) * hz_pts / sr).astype(int)

    fbank = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        lo, mid, hi = bins[m - 1], bins[m], bins[m + 1]
        for k in range(lo, mid):
            if mid > lo:
                fbank[m - 1, k] = (k - lo) / (mid - lo)
        for k in range(mid, hi):
            if hi > mid:
                fbank[m - 1, k] = (hi - k) / (hi - mid)
    return fbank


_MEL_BANK = None  # cached globally


def compute_mfcc_features(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Compute MFCC + delta features.
    Returns fixed-length vector: mean+std of N_MFCC coefficients = 2*N_MFCC dims.
    """
    global _MEL_BANK

    # Normalise
    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio / peak

    # Pre-emphasis
    audio = np.append(audio[0], audio[1:] - 0.97 * audio[:-1]).astype(np.float32)

    # Power spectrogram via STFT
    _, _, Zxx = scipy.signal.stft(audio, fs=sr, nperseg=N_FFT,
                                   noverlap=N_FFT - HOP_LEN, boundary=None)
    power = np.abs(Zxx) ** 2  # (freq_bins, time_frames)

    # Mel filterbank (cached)
    if _MEL_BANK is None:
        _MEL_BANK = _mel_filterbank(sr, N_FFT, N_MELS)

    mel = _MEL_BANK @ power               # (n_mels, time)
    log_mel = np.log(mel + 1e-9)

    # DCT → MFCC
    mfcc = scipy.fftpack.dct(log_mel, type=2, axis=0, norm='ortho')[:N_MFCC]  # (N_MFCC, time)

    # Delta (first-order difference)
    delta = np.diff(mfcc, n=1, axis=1, prepend=mfcc[:, :1])

    # Feature vector: mean + std of mfcc + mean of delta
    feat = np.concatenate([
        mfcc.mean(axis=1),
        mfcc.std(axis=1),
        delta.mean(axis=1),
    ])  # (3 * N_MFCC,)
    return feat.astype(np.float32)


def load_audio(path: Path) -> np.ndarray | None:
    """Load WAV file. Returns float32 mono at SAMPLE_RATE or None on error."""
    try:
        audio, sr = sf.read(str(path), dtype='float32')
        if audio.ndim > 1:
            audio = audio[:, 0]
        if sr != SAMPLE_RATE:
            n_new = int(len(audio) * SAMPLE_RATE / sr)
            audio = scipy.signal.resample(audio, n_new).astype(np.float32)
        # Minimum length check: 0.3s
        if len(audio) < SAMPLE_RATE * 0.3:
            return None
        return audio
    except Exception:
        return None


# ── Dataset loading ────────────────────────────────────────────────────────────

def load_dataset():
    """Load all WAV files. Returns (X, y) numpy arrays."""
    X, y = [], []
    errors = 0

    print(f"Loading positive samples from {POSITIVE_DIR}...")
    pos_files = list(POSITIVE_DIR.glob("*.wav"))
    for f in pos_files:
        audio = load_audio(f)
        if audio is None:
            errors += 1
            continue
        feat = compute_mfcc_features(audio)
        X.append(feat)
        y.append(1)

    print(f"Loading negative samples from {NEGATIVE_DIR}...")
    neg_files = list(NEGATIVE_DIR.glob("*.wav"))
    for f in neg_files:
        audio = load_audio(f)
        if audio is None:
            errors += 1
            continue
        feat = compute_mfcc_features(audio)
        X.append(feat)
        y.append(0)

    if errors:
        print(f"  ⚠ {errors} files could not be loaded (skipped)")

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


# ── Training ──────────────────────────────────────────────────────────────────

def train(X: np.ndarray, y: np.ndarray, show_confusion: bool = False):
    """Train SVM classifier. Returns (scaler, model, metrics_dict)."""
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC
        from sklearn.model_selection import StratifiedKFold, cross_val_score
        from sklearn.metrics import classification_report, confusion_matrix
    except ImportError:
        print("\nERROR: scikit-learn not installed.")
        print("Run: pip install scikit-learn")
        sys.exit(1)

    pos_count = y.sum()
    neg_count = (y == 0).sum()
    total = len(y)
    print(f"\nDataset: {total} samples ({pos_count} positive, {neg_count} negative)")

    if pos_count < 10:
        print("ERROR: Cần ít nhất 10 positive samples để train.")
        print("Run: python scripts/generate_wakeword_dataset.py")
        sys.exit(1)

    if neg_count < 10:
        print("ERROR: Cần ít nhất 10 negative samples để train.")
        sys.exit(1)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Cross-validation first
    print("\nCross-validation (5-fold)...")
    t0 = time.time()
    model_cv = SVC(kernel='rbf', C=10.0, gamma='scale', probability=True,
                   class_weight='balanced')
    cv_scores = cross_val_score(model_cv, X_scaled, y,
                                cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
                                scoring='f1')
    print(f"  F1 scores: {cv_scores.round(3)}")
    print(f"  Mean F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    print(f"  ({time.time() - t0:.1f}s)")

    # Train final model on all data
    print("\nTraining final model on full dataset...")
    t0 = time.time()
    model = SVC(kernel='rbf', C=10.0, gamma='scale', probability=True,
                class_weight='balanced')
    model.fit(X_scaled, y)
    print(f"  Done ({time.time() - t0:.1f}s)")

    # Evaluate on training set (sanity check)
    y_pred = model.predict(X_scaled)
    report = classification_report(y, y_pred, target_names=["negative", "positive"])
    print("\nTraining set report (not held-out — use CV scores for true accuracy):")
    print(report)

    if show_confusion:
        cm = confusion_matrix(y, y_pred)
        print("Confusion matrix (rows=true, cols=pred):")
        print(f"  TN={cm[0,0]:4d}  FP={cm[0,1]:4d}")
        print(f"  FN={cm[1,0]:4d}  TP={cm[1,1]:4d}")

    metrics = {
        "cv_f1_mean": float(cv_scores.mean()),
        "cv_f1_std":  float(cv_scores.std()),
        "n_positive": int(pos_count),
        "n_negative": int(neg_count),
        "n_mfcc":     N_MFCC,
        "sample_rate": SAMPLE_RATE,
    }
    return scaler, model, metrics


def save_model(scaler, model, metrics: dict):
    MODEL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scaler":  scaler,
        "model":   model,
        "metrics": metrics,
        "config": {
            "n_mfcc":      N_MFCC,
            "n_mels":      N_MELS,
            "n_fft":       N_FFT,
            "hop_len":     HOP_LEN,
            "sample_rate": SAMPLE_RATE,
        },
    }
    with open(MODEL_OUTPUT, "wb") as f:
        pickle.dump(payload, f)
    print(f"\n✓ Model saved to {MODEL_OUTPUT}")


def eval_existing():
    """Evaluate an already-trained model against the current dataset."""
    if not MODEL_OUTPUT.exists():
        print(f"No model found at {MODEL_OUTPUT}")
        print("Run: python scripts/train_wakeword.py")
        sys.exit(1)

    with open(MODEL_OUTPUT, "rb") as f:
        payload = pickle.load(f)

    scaler = payload["scaler"]
    model  = payload["model"]
    X, y   = load_dataset()
    X_s    = scaler.transform(X)

    from sklearn.metrics import classification_report
    y_pred = model.predict(X_s)
    print("\nEvaluation on current dataset:")
    print(classification_report(y, y_pred, target_names=["negative", "positive"]))
    print(f"Stored metrics: {payload['metrics']}")


def main():
    parser = argparse.ArgumentParser(description="Train MFCC+SVM wake word classifier")
    parser.add_argument("--eval-only",       action="store_true", help="Evaluate existing model only")
    parser.add_argument("--show-confusion",  action="store_true", help="Print confusion matrix")
    args = parser.parse_args()

    print("=" * 60)
    print("Robot Bi — Wake Word Classifier Training")
    print(f"Target: {MODEL_OUTPUT}")
    print("=" * 60)

    if args.eval_only:
        eval_existing()
        return

    # Check dataset
    if not POSITIVE_DIR.exists() or not any(POSITIVE_DIR.glob("*.wav")):
        print(f"ERROR: No positive samples found in {POSITIVE_DIR}")
        print("Run: python scripts/generate_wakeword_dataset.py")
        sys.exit(1)

    if not NEGATIVE_DIR.exists() or not any(NEGATIVE_DIR.glob("*.wav")):
        print(f"ERROR: No negative samples found in {NEGATIVE_DIR}")
        print("Run: python scripts/generate_wakeword_dataset.py")
        sys.exit(1)

    X, y = load_dataset()
    scaler, model, metrics = train(X, y, show_confusion=args.show_confusion)
    save_model(scaler, model, metrics)

    mean_f1 = metrics["cv_f1_mean"]
    print()
    if mean_f1 >= 0.80:
        print(f"✓ Excellent! CV F1 = {mean_f1:.2f} — model sẵn sàng để dùng.")
    elif mean_f1 >= 0.70:
        print(f"⚡ Usable prototype: CV F1 = {mean_f1:.2f} — đủ để test, thêm data để cải thiện.")
    else:
        print(f"⚠ F1 = {mean_f1:.2f} — cần thêm data hoặc đa dạng hơn.")
        print("  Gợi ý: thu thêm positive samples, augment mạnh hơn.")

    print()
    print("Bước tiếp theo:")
    print("  # Kích hoạt trong .env:")
    print("  WAKEWORD_ENABLED=true")
    print("  WAKEWORD_BACKEND=custom_mfcc")
    print(f"  WAKEWORD_CUSTOM_MODEL_PATH={MODEL_OUTPUT}")
    print()
    print("  # Test ngay:")
    print("  python scripts/test_wakeword.py")


if __name__ == "__main__":
    main()
