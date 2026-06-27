"""
family_router.py — Quản lý gia đình & phân quyền (US7, spec 006).

- POST   /api/family/create               — tạo gia đình mới → người tạo thành owner
- GET    /api/family/members              — liệt kê thành viên (owner)
- POST   /api/family/members/add          — thêm tài khoản người lớn đã đăng ký + role (owner)
- POST   /api/family/members/child        — tạo tài khoản con từ hồ sơ trẻ + PIN (owner)
- PUT    /api/family/members/{user_id}/role — đổi vai trò thành viên (owner)
- DELETE /api/family/members/{user_id}    — gỡ thành viên (owner; chặn self + owner cuối)
- GET    /api/family/permissions          — đọc quyền con (owner)
- PUT    /api/family/permissions          — cập nhật quyền con (owner)

Tất cả thao tác quản lý đều require_role('owner') và scope theo family_name của owner
(lấy từ JWT, KHÔNG nhận từ client) — đảm bảo cô lập đa gia đình.
"""
import logging
import re as _re

from fastapi import APIRouter, Body, Depends, HTTPException

from src.infrastructure.auth.auth import get_current_user, require_role
from src.infrastructure.database import db

logger = logging.getLogger(__name__)

router = APIRouter()

_PIN_RE = _re.compile(r"^\d{4,6}$")


@router.post("/api/family/create")
async def create_family(payload: dict = Body(default={}), current_user: dict = Depends(get_current_user)):
    """Người dùng tạo gia đình mới và trở thành owner. Cần đăng nhập lại để token mang role owner."""
    family_id = (payload or {}).get("family_id", "").strip()
    display_name = (payload or {}).get("display_name", "").strip()
    if not _re.fullmatch(r"[A-Za-z0-9_-]{3,50}", family_id):
        raise HTTPException(status_code=422, detail="Ma gia dinh 3-50 ky tu (a-z, 0-9, _ , -)")
    result = db.create_family(str(current_user["user_id"]), family_id, display_name)
    # Vô hiệu token cũ (role=parent) → buộc đăng nhập lại để nhận token role=owner.
    db.increment_token_version(str(current_user["user_id"]))
    return {"ok": True, **result, "relogin_required": True}


@router.get("/api/family/members")
async def list_members(current_user: dict = Depends(require_role("owner"))):
    fam = current_user["family_name"]
    return {"members": db.list_family_members(fam)}


@router.post("/api/family/members/add")
async def add_member(payload: dict = Body(...), current_user: dict = Depends(require_role("owner"))):
    fam = current_user["family_name"]
    username = (payload or {}).get("username", "").strip()
    role = (payload or {}).get("role", "parent").strip()
    if not username:
        raise HTTPException(status_code=422, detail="Thieu username")
    if role not in ("parent", "owner"):
        raise HTTPException(status_code=422, detail="Role phai la parent hoac owner")
    return {"ok": True, "member": db.add_existing_user_to_family(username, fam, role)}


@router.post("/api/family/members/child")
async def add_child(payload: dict = Body(...), current_user: dict = Depends(require_role("owner"))):
    fam = current_user["family_name"]
    child_profile_id = (payload or {}).get("child_profile_id", "").strip()
    pin = str((payload or {}).get("pin", "")).strip()
    if not child_profile_id:
        raise HTTPException(status_code=422, detail="Thieu child_profile_id")
    if not _PIN_RE.fullmatch(pin):
        raise HTTPException(status_code=422, detail="PIN phai la 4-6 chu so")
    return {"ok": True, "child": db.create_child_account(fam, child_profile_id, pin)}


@router.put("/api/family/members/{user_id}/role")
async def change_member_role(user_id: str, payload: dict = Body(...), current_user: dict = Depends(require_role("owner"))):
    fam = current_user["family_name"]
    role = (payload or {}).get("role", "").strip()
    if role not in ("owner", "parent", "child"):
        raise HTTPException(status_code=422, detail="Role khong hop le")
    # Chặn owner tự hạ quyền chính mình nếu là owner cuối.
    if str(user_id) == str(current_user["user_id"]) and role != "owner" and db.count_family_owners(fam) <= 1:
        raise HTTPException(status_code=409, detail="Khong the ha quyen owner cuoi cung")
    if not db.set_member_role(fam, str(user_id), role):
        raise HTTPException(status_code=404, detail="Khong tim thay thanh vien trong gia dinh")
    return {"ok": True}


@router.delete("/api/family/members/{user_id}")
async def remove_member(user_id: str, current_user: dict = Depends(require_role("owner"))):
    fam = current_user["family_name"]
    if str(user_id) == str(current_user["user_id"]):
        raise HTTPException(status_code=409, detail="Khong the tu xoa chinh minh")
    # Chặn xóa owner cuối cùng.
    members = {str(m["user_id"]): m for m in db.list_family_members(fam)}
    target = members.get(str(user_id))
    if not target:
        raise HTTPException(status_code=404, detail="Khong tim thay thanh vien trong gia dinh")
    if target["role"] == "owner" and db.count_family_owners(fam) <= 1:
        raise HTTPException(status_code=409, detail="Khong the xoa owner cuoi cung")
    db.remove_family_member(fam, str(user_id))
    return {"ok": True}


@router.get("/api/family/permissions")
async def get_permissions(current_user: dict = Depends(require_role("owner"))):
    return {"permissions": db.get_family_permissions(current_user["family_name"])}


@router.put("/api/family/permissions")
async def update_permissions(payload: dict = Body(...), current_user: dict = Depends(require_role("owner"))):
    perms = db.set_family_permissions(current_user["family_name"], payload or {})
    return {"ok": True, "permissions": perms}
