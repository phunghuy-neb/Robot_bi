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
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.auth.auth import get_current_user
from src.api.routers.conversation_router import _require_family
from src.infrastructure.database.db import (
    create_parent_event_note,
    delete_parent_event_note,
    event_exists_for_family,
    list_parent_event_notes,
    update_parent_event_note,
)
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


# Request helpers

class ParentEventNoteIn(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)


def _parse_event_types(types: Optional[str]) -> list[str] | None:
    if not types:
        return None
    parsed = [value.strip() for value in types.split(",") if value.strip()]
    if len(parsed) > 20:
        raise HTTPException(status_code=422, detail="types supports at most 20 values")
    return parsed or None


def _validate_event_date(value: Optional[str], field_name: str) -> Optional[str]:
    if not value:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field_name} must use YYYY-MM-DD")
    return value


def _clean_parent_note(note: str) -> str:
    cleaned = (note or "").strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="note must not be empty")
    return cleaned


# REST: Status

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
    types: Optional[str] = Query(default=None, max_length=500),
    unread_only: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    has_clip: Optional[bool] = None,
    has_note: Optional[bool] = None,
    q: Optional[str] = Query(default=None, min_length=1, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    sort: str = Query(default="desc", max_length=4),
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    event_types = _parse_event_types(types)
    start = _validate_event_date(start_date, "start_date")
    end = _validate_event_date(end_date, "end_date")
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start_date must be before or equal to end_date")
    sort_value = (sort or "desc").lower()
    if sort_value not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="sort must be asc or desc")

    events = _state._fetch_events_from_db(
        event_type=type,
        event_types=event_types,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
        newest_first=(sort_value == "desc"),
        family_id=family_id,
        start_date=start,
        end_date=end,
        has_clip=has_clip,
        has_note=has_note,
        q=q,
        include_note_count=True,
    )
    total = _state._count_events_from_db(
        event_type=type,
        event_types=event_types,
        unread_only=unread_only,
        family_id=family_id,
        start_date=start,
        end_date=end,
        has_clip=has_clip,
        has_note=has_note,
        q=q,
    )
    return {
        "events": events,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "type": type,
            "types": event_types,
            "unread_only": unread_only,
            "start_date": start,
            "end_date": end,
            "has_clip": has_clip,
            "has_note": has_note,
            "q": q,
            "sort": sort_value,
        },
    }


@router.post("/api/events/read_all")
async def mark_read(_current_user: dict = Depends(get_current_user)):
    family_id = _require_family(_current_user)
    if _state._notifier:
        _state._notifier.mark_all_read(family_id=family_id)
    return {"status": "ok"}


# REST: Event Notes

@router.get("/api/events/{event_id}/notes")
async def get_event_notes(
    event_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    return {"notes": list_parent_event_notes(family_id, event_id)}


@router.post("/api/events/{event_id}/notes")
async def add_event_note(
    event_id: str,
    payload: ParentEventNoteIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    note = create_parent_event_note(
        family_id=family_id,
        event_id=event_id,
        user_id=str(_current_user.get("user_id") or ""),
        note=_clean_parent_note(payload.note),
    )
    return note


@router.put("/api/events/{event_id}/notes/{note_id}")
async def edit_event_note(
    event_id: str,
    note_id: str,
    payload: ParentEventNoteIn,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    note = update_parent_event_note(
        family_id=family_id,
        event_id=event_id,
        note_id=note_id,
        note=_clean_parent_note(payload.note),
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/api/events/{event_id}/notes/{note_id}")
async def remove_event_note(
    event_id: str,
    note_id: str,
    _current_user: dict = Depends(get_current_user),
):
    family_id = _require_family(_current_user)
    if not event_exists_for_family(family_id, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    if not delete_parent_event_note(family_id, event_id, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return {"status": "ok"}


# REST: Chat Log

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
