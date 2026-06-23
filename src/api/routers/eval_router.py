"""
eval_router.py — AI Eval endpoint cho Robot Bi.
  POST /api/eval/chat — Gọi LLM với role cụ thể, trả full response (không lưu DB).

Dùng để test 4 vai trò, so sánh prompt version, export kết quả cho Claude fix.
"""
import time
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from src.infrastructure.auth.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_ROLES = {"friend", "teacher", "parent_child", "parent_advisor"}


class ChildContext(BaseModel):
    name: Optional[str] = Field(default=None, max_length=50)
    age: Optional[int] = Field(default=None, ge=1, le=18)
    subject: Optional[str] = Field(default=None, max_length=100)


class EvalChatRequest(BaseModel):
    role: str = Field(..., description="friend | teacher | parent_child | parent_advisor")
    message: str = Field(..., min_length=1, max_length=2000)
    child_context: Optional[ChildContext] = None
    history: Optional[list] = Field(default=None, max_length=20)


@router.post("/api/eval/chat")
async def eval_chat(
    body: EvalChatRequest,
    current_user: dict = Depends(get_current_user),
):
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role phải là một trong: {', '.join(VALID_ROLES)}")

    try:
        from src.ai.ai_engine import stream_chat
        from src.ai.prompts import PROMPT_VERSION
    except ImportError:
        from src.ai.ai_engine import stream_chat
        PROMPT_VERSION = "v1"

    # Build system context từ child_context
    system_context: Optional[str] = None
    if body.child_context:
        parts = []
        if body.child_context.name:
            parts.append(f"Ten be: {body.child_context.name}")
        if body.child_context.age:
            parts.append(f"Tuoi: {body.child_context.age}")
        if body.child_context.subject:
            parts.append(f"Mon dang hoc: {body.child_context.subject}")
        if parts:
            system_context = "[CONTEXT BE] " + ", ".join(parts)

    # Build messages
    messages = []
    if body.history:
        for h in body.history[-10:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant"):
                messages.append({"role": h["role"], "content": str(h.get("content", ""))[:1000]})
    messages.append({"role": "user", "content": body.message})

    # Collect full response (eval mode — không stream)
    start_ts = time.time()
    full_response = ""
    provider_used = "unknown"

    try:
        for token in stream_chat(messages, system_context=system_context, role=body.role):
            full_response += token
            if len(full_response) > 3000:
                break
    except Exception as e:
        logger.warning("[Eval] stream_chat error: %s", e)
        raise HTTPException(status_code=503, detail=f"AI provider error: {str(e)[:200]}")

    latency_ms = int((time.time() - start_ts) * 1000)

    return {
        "response": full_response.strip(),
        "role": body.role,
        "latency_ms": latency_ms,
        "prompt_version": PROMPT_VERSION,
        "message": body.message,
    }
