"""Shared microphone selection and callback capture helpers."""

from __future__ import annotations

import math
import queue
import threading
import time
from dataclasses import dataclass
from typing import Iterable

import numpy as np


_PREFERRED_NAME_MARKERS = (
    "microphone",
    "mic ",
    " mic",
    "headset",
    "usb audio",
    "array",
)
_VIRTUAL_NAME_MARKERS = (
    "stereo mix",
    "line in",
    "loopback",
    "what u hear",
    "virtual cable",
    "cable output",
    "mapper",
)


@dataclass(frozen=True)
class MicrophoneConfig:
    device_index: int
    name: str
    sample_rate: int
    channels: int = 1


def parse_optional_device_index(raw: str | None) -> int | None:
    value = (raw or "").strip()
    return int(value) if value.isdigit() else None


def _input_channels(device_info) -> int:
    try:
        return max(0, int(device_info.get("max_input_channels", 0)))
    except (AttributeError, TypeError, ValueError):
        return 0


def rank_input_device_indexes(
    devices: Iterable,
    *,
    preferred_index: int | None = None,
    excluded_indexes: set[int] | None = None,
) -> list[int]:
    """Rank usable input devices, keeping virtual/line inputs as last resorts."""
    excluded = excluded_indexes or set()
    ranked: list[tuple[int, int]] = []

    for index, info in enumerate(devices):
        if index in excluded or _input_channels(info) <= 0:
            continue

        name = str(info.get("name", "")).lower()
        score = index
        if any(marker in name for marker in _PREFERRED_NAME_MARKERS):
            score -= 100
        if any(marker in name for marker in _VIRTUAL_NAME_MARKERS):
            score += 1000
        if preferred_index == index:
            score -= 10000
        ranked.append((score, index))

    ranked.sort()
    return [index for _, index in ranked]


def candidate_sample_rates(device_info, *, target_rate: int) -> list[int]:
    rates = [int(target_rate)]
    try:
        native_rate = int(round(float(device_info.get("default_samplerate", 0))))
    except (AttributeError, TypeError, ValueError):
        native_rate = 0
    if native_rate > 0 and native_rate not in rates:
        rates.append(native_rate)
    return rates


def resample_audio(
    audio: np.ndarray,
    source_rate: int,
    target_rate: int,
) -> np.ndarray:
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if source_rate == target_rate or samples.size == 0:
        return samples.astype(np.float32, copy=False)

    from scipy.signal import resample_poly

    divisor = math.gcd(int(source_rate), int(target_rate))
    result = resample_poly(
        samples,
        int(target_rate) // divisor,
        int(source_rate) // divisor,
    )
    return np.asarray(result, dtype=np.float32)


def probe_input_device(
    *,
    preferred_index: int | None = None,
    target_rate: int = 16000,
    excluded_indexes: set[int] | None = None,
) -> MicrophoneConfig | None:
    """Find a callback-capable input device at target or native sample rate."""
    import sounddevice as sd

    devices = sd.query_devices()
    indexes = rank_input_device_indexes(
        devices,
        preferred_index=preferred_index,
        excluded_indexes=excluded_indexes,
    )

    for index in indexes:
        info = devices[index]
        name = str(info.get("name", f"Device {index}"))
        for sample_rate in candidate_sample_rates(info, target_rate=target_rate):
            stream = None
            received_audio = threading.Event()

            def _confirm_audio(_indata, _frames, _time_info, _status):
                received_audio.set()

            try:
                blocksize = max(1, int(sample_rate * 0.05))
                stream = sd.InputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=blocksize,
                    device=index,
                    callback=_confirm_audio,
                )
                stream.start()
                if not received_audio.wait(timeout=0.5):
                    raise RuntimeError("microphone stream produced no audio frames")
                stream.stop()
                stream.close()
                # M-NEW-4: give WDM-KS time to fully release the device
                # before the caller opens it again (avoids "device already open").
                time.sleep(0.15)
                return MicrophoneConfig(
                    device_index=index,
                    name=name,
                    sample_rate=sample_rate,
                )
            except Exception:
                if stream is not None:
                    try:
                        stream.stop()
                        stream.close()
                    except Exception:
                        pass
    return None


class CallbackMicrophoneStream:
    """Queue-backed callback stream compatible with Windows WDM-KS devices."""

    def __init__(
        self,
        config: MicrophoneConfig,
        *,
        chunk_ms: int,
        queue_size: int = 20,
    ):
        self.config = config
        self.chunk_ms = chunk_ms
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=queue_size)
        self._stream = None

    def _callback(self, indata, _frames, _time_info, _status) -> None:
        audio = np.asarray(indata, dtype=np.float32)
        if audio.ndim > 1:
            audio = audio[:, 0]
        audio = audio.copy()
        try:
            self._queue.put_nowait(audio)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(audio)
            except queue.Full:
                pass

    def start(self) -> None:
        import sounddevice as sd

        blocksize = max(1, int(self.config.sample_rate * self.chunk_ms / 1000))
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype="float32",
            blocksize=blocksize,
            device=self.config.device_index,
            callback=self._callback,
        )
        self._stream.start()

    def read(self, *, timeout: float = 2.0) -> np.ndarray:
        return self._queue.get(timeout=timeout)

    def stop(self) -> None:
        if self._stream is None:
            return
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None


def diagnose_input_devices() -> MicrophoneConfig | None:
    """Print input endpoints and return the first device that produces frames."""
    import sounddevice as sd

    devices = sd.query_devices()
    print("Input devices:")
    for index, info in enumerate(devices):
        channels = _input_channels(info)
        if channels <= 0:
            continue
        host = sd.query_hostapis(info["hostapi"])["name"]
        print(
            f"- {index}: {info.get('name')} | host={host} | "
            f"channels={channels} | native_rate={info.get('default_samplerate')}"
        )

    config = probe_input_device(target_rate=16000)
    if config is None:
        print("RESULT: no microphone returned callback audio frames")
    else:
        print(
            f"RESULT: device={config.device_index} name={config.name} "
            f"capture_rate={config.sample_rate}"
        )
    return config


if __name__ == "__main__":
    diagnose_input_devices()
