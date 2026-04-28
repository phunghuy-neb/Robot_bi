"""
streaming_router.py — WebSocket + Mom Direct Talk endpoints cho Robot Bi API.
  WS   /ws                — Real-time event push
  WS   /api/audio/stream  — Mic room → browser (audio monitoring)
  POST /api/mom/start     — Mẹ bắt đầu nói
  POST /api/mom/stop      — Mẹ dừng nói
  GET  /api/mom/status    — Trạng thái mom (no auth)
  WS   /api/mom/audio     — Browser mẹ → loa robot
"""
import asyncio
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from src_brain.network.auth import get_current_user
import src_brain.network.state as _state

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Audio monitoring constants ─────────────────────────────────────────────
AUDIO_SAMPLE_RATE  = 16000
AUDIO_CHANNELS     = 1
AUDIO_CHUNK_MS     = 100
AUDIO_CHUNK_FRAMES = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)
_mic_raw = os.getenv("MIC_DEVICE", "").strip()
AUDIO_MIC_DEVICE   = int(_mic_raw) if _mic_raw.isdigit() else 1

try:
    import numpy as np
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False

try:
    from scipy import signal as _scipy_signal
    _SCIPY_AVAILABLE = True
except ImportError:
    _SCIPY_AVAILABLE = False


async def _ws_verify_token(token: Optional[str] = Query(None), auth: Optional[str] = Query(None)) -> dict:
    """Shared WebSocket auth helper — accepts ?token= or ?auth= query param."""
    t = token or auth
    if not t:
        raise WebSocketDisconnect(code=1008)
    from src_brain.network.auth import verify_access_token
    try:
        return verify_access_token(t)
    except Exception:
        raise WebSocketDisconnect(code=1008)


# ── WebSocket: Event push ─────────────────────────────────────────────────

@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token", "")
    try:
        from src_brain.network.auth import verify_access_token
        payload = verify_access_token(token)
    except Exception:
        await websocket.close(code=1008)
        return
    family_id = payload["family"]
    await _state._ws_manager.connect(websocket, family_id=family_id)
    if _state._notifier:
        try:
            unread = _state._fetch_events_from_db(
                unread_only=True,
                limit=20,
                newest_first=True,
                family_id=family_id,
            )
            unread.reverse()
            for evt in unread:
                await websocket.send_json(evt)
        except Exception:
            pass
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _state._ws_manager.disconnect(websocket)


# ── WebSocket: Audio Monitoring ───────────────────────────────────────────

@router.websocket("/api/audio/stream")
async def audio_stream(websocket: WebSocket, token: Optional[str] = Query(None), auth: Optional[str] = Query(None)):
    """
    Stream audio từ mic phòng → browser (1 chiều).
    Format: PCM 16-bit little-endian, 16kHz, mono.
    Auth qua query param: /api/audio/stream?token=JWT_ACCESS_TOKEN
    """
    try:
        await _ws_verify_token(token, auth)
    except WebSocketDisconnect:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    logger.info("[Bi - Tai Giam Sat] Client ket noi audio stream")

    if not _SD_AVAILABLE:
        logger.warning("[Bi - Tai Giam Sat] sounddevice/numpy khong co san — dong stream")
        await websocket.close(code=1011)
        return

    loop = asyncio.get_event_loop()
    audio_queue: asyncio.Queue = asyncio.Queue(maxsize=10)

    async def _safe_put(q, item):
        try:
            q.put_nowait(item)
        except asyncio.QueueFull:
            logger.debug("[Audio] queue full, dropping frame")

    def audio_callback(indata, frames, time_info, status):
        pcm = (indata[:, 0] * 32767).astype(np.int16)
        raw_bytes = pcm.tobytes()
        loop.call_soon_threadsafe(
            loop.create_task,
            _safe_put(audio_queue, raw_bytes),
        )

    stream = None
    try:
        stream = sd.InputStream(
            samplerate=AUDIO_SAMPLE_RATE,
            channels=AUDIO_CHANNELS,
            dtype="float32",
            blocksize=AUDIO_CHUNK_FRAMES,
            device=AUDIO_MIC_DEVICE,
            callback=audio_callback,
        )
        stream.start()
        logger.info("[Bi - Tai Giam Sat] Bat dau stream audio mic")

        while True:
            try:
                raw_bytes = await asyncio.wait_for(audio_queue.get(), timeout=5.0)
                await websocket.send_bytes(raw_bytes)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_bytes(b"")
                except Exception:
                    break
            except Exception:
                break

    except Exception as e:
        logger.error("[Bi - Tai Giam Sat] Loi mic: %s", e)
    finally:
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        logger.info("[Bi - Tai Giam Sat] Client ngat ket noi audio stream")


# ── REST: Mom Direct Talk ─────────────────────────────────────────────────

@router.post("/api/mom/start")
async def mom_start_talking(_current_user: dict = Depends(get_current_user)):
    """Mẹ bắt đầu nói — Bi tạm dừng AI, chờ nhận audio từ mẹ."""
    _state._mom_talking = True
    logger.info("[Me] ===== ME BAT DAU NOI — BI TAM DUNG =====")
    logger.info("[Me] Me bat dau noi chuyen truc tiep")
    return {"status": "mom_talking", "message": "Bi đang nhường loa cho mẹ"}


@router.post("/api/mom/stop")
async def mom_stop_talking(_current_user: dict = Depends(get_current_user)):
    """Mẹ dừng nói — Bi hoạt động bình thường lại."""
    _state._mom_talking = False
    logger.info("[Me] ===== ME DUNG NOI — BI HOAT DONG LAI =====")
    logger.info("[Me] Me ngung noi — Bi hoat dong binh thuong")
    return {"status": "bi_active", "message": "Bi đang hoạt động trở lại"}


@router.get("/api/mom/status")
async def mom_status():
    """Trả về trạng thái hiện tại (không cần auth — main_loop poll nội bộ)."""
    return {"mom_talking": _state._mom_talking}


# ── WebSocket: Mom Audio ──────────────────────────────────────────────────

@router.websocket("/api/mom/audio")
async def mom_audio_receive(websocket: WebSocket, token: Optional[str] = Query(None), auth: Optional[str] = Query(None)):
    """
    Nhận audio PCM float32 từ browser điện thoại mẹ → phát qua loa robot.
    Format: PCM float32, 16000Hz, mono (Web Audio API getUserMedia).
    Auth: /api/mom/audio?token=JWT_ACCESS_TOKEN
    """
    try:
        await _ws_verify_token(token, auth)
    except WebSocketDisconnect:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _state._mom_audio_clients.append(websocket)
    logger.info("[Me] Ket noi audio tu dien thoai me")

    import pygame
    import numpy as np
    import io as _io
    import wave as _wave

    MOM_CHANNEL = 7

    def _get_mixer_freq():
        info = pygame.mixer.get_init()
        return info[0] if info else 44100

    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.init()

    if pygame.mixer.get_num_channels() <= MOM_CHANNEL:
        pygame.mixer.set_num_channels(MOM_CHANNEL + 1)

    mom_channel = pygame.mixer.Channel(MOM_CHANNEL)

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_bytes(), timeout=10.0
                )
                if not data or len(data) == 0:
                    continue
                if not _state._mom_talking:
                    continue

                float_array = np.frombuffer(data, dtype=np.float32)
                if len(float_array) < 16:
                    continue
                float_array = np.clip(float_array, -1.0, 1.0)

                mixer_freq = _get_mixer_freq()
                src_freq = 16000

                if mixer_freq != src_freq:
                    if _SCIPY_AVAILABLE:
                        num_samples = int(len(float_array) * mixer_freq / src_freq)
                        float_array = _scipy_signal.resample(float_array, num_samples)
                    else:
                        num_samples = int(len(float_array) * mixer_freq / src_freq)
                        indices = np.linspace(0, len(float_array) - 1, num_samples)
                        float_array = np.interp(indices, np.arange(len(float_array)), float_array)

                int16_mono = (float_array * 32767).astype(np.int16)

                mixer_channels = pygame.mixer.get_init()[2] if pygame.mixer.get_init() else 2
                if mixer_channels == 2:
                    int16_stereo = np.column_stack([int16_mono, int16_mono])
                    pcm_bytes = int16_stereo.tobytes()
                else:
                    pcm_bytes = int16_mono.tobytes()

                buf = _io.BytesIO()
                with _wave.open(buf, 'wb') as wf:
                    wf.setnchannels(mixer_channels)
                    wf.setsampwidth(2)
                    wf.setframerate(mixer_freq)
                    wf.writeframes(pcm_bytes)
                buf.seek(0)

                sound = pygame.mixer.Sound(buf)
                sound.set_volume(1.0)
                mom_channel.play(sound)

            except asyncio.TimeoutError:
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break
            except Exception as e:
                logger.error("[Me] Loi nhan audio: %s", e)
                break

    finally:
        if websocket in _state._mom_audio_clients:
            _state._mom_audio_clients.remove(websocket)
        logger.info("[Me] Ngat ket noi audio tu me")
