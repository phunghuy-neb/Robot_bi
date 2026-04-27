"""
webrtc_router.py — WebRTC signaling endpoints cho Robot Bi.
  POST /api/webrtc/offer  — SDP offer → answer (JWT required)
  POST /api/webrtc/close  — Close all peer connections (JWT required)

aiortc cần cài trên Ubuntu: pip install aiortc==1.9.0
Trên Windows (dev): _AIORTC_AVAILABLE=False → endpoints trả 503, frontend fallback MJPEG.
"""
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from src_brain.network.auth import get_current_user
import src_brain.network.state as _state

logger = logging.getLogger(__name__)

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
    _AIORTC_AVAILABLE = True
except ImportError:
    _AIORTC_AVAILABLE = False
    RTCPeerConnection = None
    VideoStreamTrack = object  # fallback base class để class body parse được

_peer_connections: dict[str, RTCPeerConnection] = {}

router = APIRouter(prefix="/api/webrtc", tags=["webrtc"])


if _AIORTC_AVAILABLE:
    class CameraVideoTrack(VideoStreamTrack):
        """Lấy frame JPEG từ _state._camera_frame, convert sang av.VideoFrame."""

        kind = "video"

        async def recv(self):
            import av
            import numpy as np
            import cv2

            pts, time_base = await self.next_timestamp()

            jpeg = _state._camera_frame
            if jpeg:
                try:
                    arr = np.frombuffer(jpeg, np.uint8)
                    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                except Exception:
                    rgb = np.zeros((480, 640, 3), dtype=np.uint8)
            else:
                rgb = np.zeros((480, 640, 3), dtype=np.uint8)

            frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
            frame.pts = pts
            frame.time_base = time_base
            return frame


@router.post("/offer")
async def webrtc_offer(request: Request, current_user: dict = Depends(get_current_user)):
    """SDP offer từ browser → tạo answer, trả về SDP answer."""
    if not _AIORTC_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="WebRTC không khả dụng trên server này. Dùng MJPEG fallback.",
        )

    body = await request.json()
    sdp = body.get("sdp", "")
    sdp_type = body.get("type", "offer")

    if not sdp:
        raise HTTPException(status_code=422, detail="Thiếu trường sdp")

    pc = RTCPeerConnection(configuration={
        "iceServers": [{"urls": "stun:stun.l.google.com:19302"}]
    })
    try:
        pc.addTrack(CameraVideoTrack())

        offer = RTCSessionDescription(sdp=sdp, type=sdp_type)
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # Chờ ICE gathering hoàn thành (tối đa 10s)
        await asyncio.wait_for(
            _ice_gathering_complete(pc),
            timeout=10.0,
        )
    except asyncio.TimeoutError:
        logger.warning("[WebRTC] ICE gathering timeout — trả answer ngay")
    except Exception as e:
        logger.error("[WebRTC] offer failed: %s", e)
        await pc.close()
        raise HTTPException(status_code=500, detail="WebRTC offer that bai")

    key = str(current_user["user_id"])
    _peer_connections[key] = pc

    @pc.on("connectionstatechange")
    async def on_state_change():
        if pc.connectionState in ("failed", "closed", "disconnected"):
            await pc.close()
            _peer_connections.pop(key, None)
            logger.info("[WebRTC] PC closed, state=%s", pc.connectionState)

    logger.info("[WebRTC] Offer processed, answer ready. Active PCs: %d", len(_peer_connections))
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}


@router.post("/close")
async def webrtc_close(current_user: dict = Depends(get_current_user)):
    """Close peer connection cua user hien tai."""
    key = str(current_user["user_id"])
    pc = _peer_connections.pop(key, None)
    closed = 0
    if pc:
        try:
            await pc.close()
        except Exception:
            pass
        closed = 1
    logger.info("[WebRTC] Closed %d peer connection(s) for user=%s", closed, key)
    return {"closed": closed}


async def _ice_gathering_complete(pc) -> None:
    """Chờ ICE gathering state chuyển sang 'complete'."""
    if pc.iceGatheringState == "complete":
        return
    loop = asyncio.get_event_loop()
    done = loop.create_future()

    @pc.on("icegatheringstatechange")
    def on_gathering():
        if pc.iceGatheringState == "complete" and not done.done():
            done.set_result(None)

    await done
