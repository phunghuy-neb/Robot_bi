"""Video call session manager placeholder."""

from __future__ import annotations

import logging
import time
import uuid

logger = logging.getLogger(__name__)


class VideoCallManager:
    """Quan ly contacts va call sessions in-memory."""

    def __init__(self):
        """Khoi tao manager."""
        self.calls: dict[str, dict] = {}
        self._active_calls = self.calls
        self.contacts: dict[str, list[dict]] = {}

    def start_call(self, family_id: str, caller_name: str) -> dict:
        """Returns call session info va WebRTC offer placeholder."""
        try:
            call_id = str(uuid.uuid4())
            session = {
                "call_id": call_id,
                "family_id": family_id,
                "caller_name": caller_name,
                "started_at": time.time(),
                "participants": [],
                "offer": {"type": "offer", "sdp": ""},
                "status": "active",
            }
            self.calls[call_id] = session
            return dict(session)
        except Exception:
            logger.exception("[VideoCallManager] start_call failed")
            return {"call_id": "", "family_id": family_id, "status": "error", "offer": {"type": "offer", "sdp": ""}}

    def invite_participant(self, call_id: str, contact_id: str) -> bool:
        """Them participant vao call."""
        try:
            call = self.calls.get(call_id)
            if not call:
                return False
            if contact_id not in call["participants"]:
                call["participants"].append(contact_id)
            return True
        except Exception:
            logger.exception("[VideoCallManager] invite_participant failed")
            return False

    def end_call(self, call_id: str, family_id: str | None = None) -> bool:
        """Ket thuc call, optionally enforcing family ownership."""
        try:
            call = self.calls.get(call_id)
            if not call:
                return False
            if family_id and call.get("family_id") != family_id:
                logger.warning(
                    "[VideoCall] Family mismatch: %s != %s",
                    call.get("family_id"),
                    family_id,
                )
                return False
            del self.calls[call_id]
            return True
        except Exception:
            logger.exception("[VideoCallManager] end_call failed")
            return False

    def get_contacts(self, family_id: str) -> list[dict]:
        """Lay danh ba cua family."""
        try:
            return list(self.contacts.get(family_id, []))
        except Exception:
            logger.exception("[VideoCallManager] get_contacts failed")
            return []

    def add_contact(self, family_id: str, name: str) -> dict:
        """Them contact moi cho family."""
        try:
            contact = {"contact_id": str(uuid.uuid4()), "family_id": family_id, "name": str(name)}
            self.contacts.setdefault(family_id, []).append(contact)
            return contact
        except Exception:
            logger.exception("[VideoCallManager] add_contact failed")
            return {"contact_id": "", "family_id": family_id, "name": str(name)}
