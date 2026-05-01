"""
control_router.py — Control endpoints cho Robot Bi API.
  GET  /api/status           — Trạng thái robot
  GET  /api/events           — Danh sách sự kiện
  POST /api/events/read_all  — Đánh dấu tất cả đã đọc
  GET  /api/chats            — Nhật ký hội thoại
  GET  /api/memories         — Danh sách trí nhớ
  POST /api/memories         — Thêm trí nhớ
  GET  /api/memories/export  — Export JSON backup
  PUT  /api/memories/{id}    — Sửa trí nhớ
  DELETE /api/memories/{id}  — Xóa trí nhớ
  POST /api/puppet           — Bi đọc text từ app
  GET  /api/tasks            — Danh sách nhiệm vụ
  POST /api/tasks            — Thêm nhiệm vụ
  GET  /api/tasks/stars      — Tổng sao
  POST /api/tasks/{id}/complete — Hoàn thành nhiệm vụ
  DELETE /api/tasks/{id}     — Xóa nhiệm vụ
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user
from src.api.routers.conversation_router import _require_family
import src.infrastructure.sessions.state as _state

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Pydantic models ────────────────────────────────────────────────────────

class MemoryIn(BaseModel):
    text: str


class MemoryUpdate(BaseModel):
    text: str


class PuppetIn(BaseModel):
    text: str


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Ten nhiem vu")
    remind_time: Optional[str] = Field(
        None,
        pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
        description="Dinh dang HH:MM",
    )


# ── REST: Status ──────────────────────────────────────────────────────────

@router.get("/api/status")
async def get_status():
    notifier_stats = _state._notifier.get_stats() if _state._notifier else {}
    rag_stats = _state._rag.get_stats() if _state._rag else {}
    total_stars = _state._task_manager.get_total_stars() if _state._task_manager else 0
    return {
        "status": "online",
        "ws_clients": _state._ws_manager.count,
        "puppet_queued": _state._puppet_queue.qsize(),
        "notifier": notifier_stats,
        "rag": rag_stats,
        "total_stars": total_stars,
    }


# ── REST: Events ──────────────────────────────────────────────────────────

@router.get("/api/events")
async def get_events(
    type: Optional[str] = None,
    unread_only: bool = False,
    limit: int = Query(default=20, ge=1, le=200),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not _state._notifier:
        return {"events": [], "total": 0}
    events = _state._fetch_events_from_db(
        event_type=type,
        unread_only=unread_only,
        limit=limit,
        newest_first=True,
        family_id=family_id,
    )
    total = _state._count_events_from_db(
        event_type=type,
        unread_only=unread_only,
        family_id=family_id,
    )
    return {"events": events, "total": total}


@router.post("/api/events/read_all")
async def mark_read(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._notifier:
        _state._notifier.mark_all_read(family_id=family_id)
    return {"status": "ok"}


# ── REST: Chat Log ────────────────────────────────────────────────────────

@router.get("/api/chats")
async def get_chats(
    limit: int = Query(default=20, ge=1, le=200),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not _state._notifier:
        return {"chats": [], "total": 0}
    chats = _state._fetch_events_from_db(
        event_type="chat",
        unread_only=False,
        limit=limit,
        newest_first=True,
        family_id=family_id,
    )
    total = _state._count_events_from_db(
        event_type="chat",
        unread_only=False,
        family_id=family_id,
    )
    return {"chats": chats, "total": total}


# ── REST: Memories ────────────────────────────────────────────────────────

@router.get("/api/memories")
async def list_memories(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "list")
    if not _state._rag:
        return {"memories": [], "total": 0}
    memories = _state._rag.list_memories(family_id=family_id)
    return {"memories": memories, "total": len(memories)}


@router.post("/api/memories")
async def add_memory(body: MemoryIn, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "add")
    if not body.text.strip():
        raise HTTPException(400, "text không được rỗng")
    if not _state._rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _state._rag.add_manual_memory(body.text.strip(), family_id=family_id)
    return {"status": "ok" if ok else "fail"}


# Export phải đứng trước /{memory_id} để không bị capture
@router.get("/api/memories/export")
async def export_memories(current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "export")
    if not _state._rag:
        return []
    return _state._rag.export_memories(family_id=family_id)


@router.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "update")
    if not _state._rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _state._rag.update_memory(memory_id, body.text, family_id=family_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


@router.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    family_id = _require_family(current_user)
    logger.info("[Memory] access family=%s action=%s", family_id, "delete")
    if not _state._rag:
        raise HTTPException(503, "RAG chưa khởi động")
    ok = _state._rag.delete_memory(memory_id, family_id=family_id)
    if not ok:
        raise HTTPException(404, "Không tìm thấy memory")
    return {"status": "ok"}


# ── REST: Puppet ──────────────────────────────────────────────────────────

@router.post("/api/puppet")
async def puppet_say(body: PuppetIn, _current_user: dict = Depends(get_current_user)):
    import logging as _logging
    _logger = _logging.getLogger("api_server")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "text không được rỗng")
    _state._puppet_queue.put(text)
    _logger.debug("[Puppet] Queued text_len=%d", len(text))
    return {"status": "queued", "text": text}


# ── REST: Tasks ───────────────────────────────────────────────────────────

@router.get("/api/tasks")
async def get_tasks(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if not _state._task_manager:
        return []
    return _state._task_manager.get_all(family_id=family_id)


@router.post("/api/tasks")
async def add_task(
    body: TaskCreate,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not _state._task_manager:
        raise HTTPException(503, "Task manager chưa khởi động")
    return _state._task_manager.add_task(body.name, body.remind_time, family_id=family_id)


# stars phải đứng trước /{task_id} để không bị capture
@router.get("/api/tasks/stars")
async def get_stars(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    return {
        "total_stars": (
            _state._task_manager.get_total_stars(family_id=family_id)
            if _state._task_manager else 0
        )
    }


@router.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: str, _current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._task_manager and _state._task_manager.complete_task(task_id, family_id=family_id):
        return {"ok": True, "stars": _state._task_manager.get_total_stars(family_id=family_id)}
    raise HTTPException(404, "Task không tìm thấy hoặc đã hoàn thành")


@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, _current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._task_manager and _state._task_manager.delete_task(task_id, family_id=family_id):
        return {"ok": True}
    raise HTTPException(404, "Task không tìm thấy")
