"""
auth_router.py — Auth endpoints cho Robot Bi API.
  POST /api/auth/login       — PIN login (rate-limited)
  POST /api/auth/logout      — PIN logout
  POST /api/auth/logout-all  — Revoke tất cả refresh token (JWT)
  POST /auth/register        — Đăng ký username+password
  POST /auth/login/v2        — Đăng nhập username+password → JWT
  POST /auth/refresh         — Đổi refresh token lấy access+refresh mới
  POST /auth/logout          — Đăng xuất JWT
"""
import logging
import math
import os
import re as _re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from src.infrastructure.auth.auth import get_current_user, verify_password
from src.infrastructure.database.db import (
    get_db_connection,
    get_user_by_id,
    revoke_all_tokens_for_user,
    update_user_password,
)
import src.infrastructure.sessions.state as _state

logger = logging.getLogger(__name__)

router = APIRouter()
REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "false").lower() == "true"


@router.post("/api/auth/login")
async def login(request: Request, pin: str = Body(..., embed=True)):
    """Đăng nhập bằng PIN. Trả về session token. Rate-limited: 5 lần sai → khóa 15 phút."""
    client_ip = request.client.host
    now = datetime.now(timezone.utc)

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE locked_until IS NOT NULL AND locked_until <= ?",
            (now.isoformat(),),
        )
        conn.commit()

        row = conn.execute(
            "SELECT attempt_count, locked_until FROM login_attempts WHERE ip_address = ?",
            (client_ip,),
        ).fetchone()

        if row and row["locked_until"]:
            locked_until_str = row["locked_until"]
            locked_until = datetime.fromisoformat(locked_until_str)
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Quá nhiều lần thử. Vui lòng thử lại sau {remaining_minutes} phút.",
                )

        if pin == _state.AUTH_PIN:
            conn.execute(
                "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
                "WHERE ip_address = ?",
                (client_ip,),
            )
            conn.commit()
            token = secrets.token_hex(16)
            _state.SESSION_TOKENS.add(token)
            return {"token": token}

        if row:
            current_count = row["attempt_count"] or 0
            new_count = current_count + 1
            if new_count >= 5:
                locked_until_val = (now + timedelta(minutes=15)).isoformat()
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = ?, locked_until = ? "
                    "WHERE ip_address = ?",
                    (new_count, locked_until_val, client_ip),
                )
            elif current_count == 0:
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = 1, first_attempt_at = ? "
                    "WHERE ip_address = ?",
                    (now.isoformat(), client_ip),
                )
            else:
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = ? WHERE ip_address = ?",
                    (new_count, client_ip),
                )
        else:
            conn.execute(
                "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                "VALUES (?, 1, ?, NULL)",
                (client_ip, now.isoformat()),
            )
        conn.commit()

    raise HTTPException(status_code=401, detail="PIN sai")


@router.post("/auth/register")
async def register_user(request: Request):
    """Đăng ký tài khoản username + password mới. family_name do server gán từ FAMILY_ID env."""
    from src.infrastructure.auth.auth import create_user

    if not REGISTRATION_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Dang ky bi tat. Lien he admin de duoc cap tai khoan.",
        )

    client_ip = request.client.host if request.client else "unknown"
    reg_key = f"register:{client_ip}"
    now = datetime.now(timezone.utc)

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE locked_until IS NOT NULL AND locked_until <= ?",
            (now.isoformat(),),
        )
        row = conn.execute(
            "SELECT attempt_count, locked_until FROM login_attempts WHERE ip_address = ?",
            (reg_key,),
        ).fetchone()

        if row and row["locked_until"]:
            locked_until = datetime.fromisoformat(row["locked_until"])
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                conn.commit()
                raise HTTPException(
                    status_code=429,
                    detail=f"Qua nhieu lan thu. Vui long thu lai sau {remaining_minutes} phut.",
                )

        current_count = row["attempt_count"] if row else 0
        new_count = current_count + 1
        locked_until_val = (now + timedelta(minutes=15)).isoformat() if new_count >= 5 else None
        if row:
            conn.execute(
                "UPDATE login_attempts SET attempt_count = ?, locked_until = ? WHERE ip_address = ?",
                (new_count, locked_until_val, reg_key),
            )
        else:
            conn.execute(
                "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                "VALUES (?, 1, ?, ?)",
                (reg_key, now.isoformat(), locked_until_val),
            )
        conn.commit()

    body = await request.json()
    username: str = body.get("username", "").strip()
    password: str = body.get("password", "")
    # family_name KHÔNG đọc từ client — server tự gán để tránh spoofing
    family_name: str = os.getenv("FAMILY_ID", "default")

    if not username or not _re.fullmatch(r"[a-zA-Z0-9_]{3,50}", username):
        raise HTTPException(
            status_code=422,
            detail="username phai tu 3-50 ky tu, chi duoc dung a-zA-Z0-9_",
        )
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="password phai co it nhat 8 ky tu")

    user = create_user(username, password, family_name)
    with get_db_connection() as conn:
        conn.execute("DELETE FROM login_attempts WHERE ip_address = ?", (reg_key,))
        conn.commit()
    return user


@router.post("/auth/login/v2")
async def login_v2(request: Request):
    """
    Đăng nhập bằng username + password.
    Rate limiting: 5 lần sai theo username → khóa 15 phút.
    Trả về JWT access_token (60 phút) + refresh_token (30 ngày).
    """
    from src.infrastructure.auth.auth import (
        authenticate_user,
        create_access_token,
        create_refresh_token,
        store_refresh_token,
    )

    body = await request.json()
    username: str = body.get("username", "").strip()
    password: str = body.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=422, detail="Thieu username hoac password")

    rate_key = f"user:{username}"
    now = datetime.now(timezone.utc)
    authenticated_user = None

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE locked_until IS NOT NULL AND locked_until <= ?",
            (now.isoformat(),),
        )
        conn.commit()

        row = conn.execute(
            "SELECT attempt_count, locked_until FROM login_attempts WHERE ip_address = ?",
            (rate_key,),
        ).fetchone()

        if row and row["locked_until"]:
            locked_until_str = row["locked_until"]
            locked_until = datetime.fromisoformat(locked_until_str)
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Quá nhiều lần thử. Vui lòng thử lại sau {remaining_minutes} phút.",
                )

        user = authenticate_user(username, password)

        if user:
            conn.execute(
                "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
                "WHERE ip_address = ?",
                (rate_key,),
            )
            conn.commit()
            authenticated_user = user
        else:
            if row:
                current_count = row["attempt_count"] or 0
                new_count = current_count + 1
                if new_count >= 5:
                    locked_until_val = (now + timedelta(minutes=15)).isoformat()
                    conn.execute(
                        "UPDATE login_attempts SET attempt_count = ?, locked_until = ? "
                        "WHERE ip_address = ?",
                        (new_count, locked_until_val, rate_key),
                    )
                elif current_count == 0:
                    conn.execute(
                        "UPDATE login_attempts SET attempt_count = 1, first_attempt_at = ? "
                        "WHERE ip_address = ?",
                        (now.isoformat(), rate_key),
                    )
                else:
                    conn.execute(
                        "UPDATE login_attempts SET attempt_count = ? WHERE ip_address = ?",
                        (new_count, rate_key),
                    )
            else:
                conn.execute(
                    "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                    "VALUES (?, 1, ?, NULL)",
                    (rate_key, now.isoformat()),
                )
            conn.commit()

    if not authenticated_user:
        raise HTTPException(status_code=401, detail="Sai ten dang nhap hoac mat khau")

    access_token = create_access_token(
        str(authenticated_user["user_id"]), authenticated_user["family_name"]
    )
    raw_refresh, hashed_refresh = create_refresh_token(str(authenticated_user["user_id"]))
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    store_refresh_token(str(authenticated_user["user_id"]), hashed_refresh, refresh_expires_at)

    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@router.post("/auth/refresh")
async def refresh_token_endpoint(request: Request):
    """
    Đổi refresh token lấy access token + refresh token mới (rotation).
    Body: {"refresh_token": str}
    """
    from src.infrastructure.auth.auth import rotate_refresh_token, create_access_token

    body = await request.json()
    old_refresh = body.get("refresh_token", "").strip()

    if not old_refresh:
        raise HTTPException(status_code=422, detail="Thieu refresh_token")

    new_raw, _new_hashed, user_id = rotate_refresh_token(old_refresh)

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT family_name, is_active FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="User khong ton tai")
    if not row["is_active"]:
        raise HTTPException(status_code=401, detail="Tai khoan da bi vo hieu hoa")

    new_access = create_access_token(user_id, row["family_name"])

    return {
        "access_token": new_access,
        "refresh_token": new_raw,
        "token_type": "bearer",
        "expires_in": 3600,
    }


@router.post("/auth/logout")
async def logout_v2(request: Request, _current_user: dict = Depends(get_current_user)):
    """
    Đăng xuất JWT: verify access token → revoke refresh token của chính user đó.
    Header: Authorization: Bearer <access_token>
    Body: {"refresh_token": str}
    """
    import hashlib as _hl

    user_id = str(_current_user["user_id"])

    body = await request.json()
    refresh_token_str = body.get("refresh_token", "").strip()
    if not refresh_token_str:
        raise HTTPException(status_code=422, detail="Thieu refresh_token")

    hashed = _hl.sha256(refresh_token_str.encode()).hexdigest()

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_id, user_id FROM auth_tokens "
            "WHERE refresh_token_hash = ? AND is_revoked = 0",
            (hashed,),
        ).fetchone()

        if not row or str(row["user_id"]) != user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token",
            )

        conn.execute(
            "UPDATE auth_tokens SET is_revoked = 1 WHERE token_id = ?",
            (row["token_id"],),
        )
        conn.commit()

    return {"message": "Đã đăng xuất"}


@router.post("/api/auth/logout")
async def logout(token: str = Body(..., embed=True)):
    """Đăng xuất, huỷ session token."""
    _state.SESSION_TOKENS.discard(token)
    return {"ok": True}


@router.post("/api/auth/logout-all")
async def logout_all(current_user: dict = Depends(get_current_user)):
    """Revoke tất cả refresh token của user hiện tại (đăng xuất tất cả thiết bị)."""
    user_id = current_user["user_id"]
    revoked = revoke_all_tokens_for_user(user_id)
    logger.info("[Auth] logout-all: user %s revoked %d tokens", user_id, revoked)
    return {"revoked": revoked}


@router.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Trả về thông tin tài khoản của user hiện tại."""
    user = get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User không tồn tại")
    return {
        "username": user["username"],
        "family_name": user["family_name"],
        "created_at": user["created_at"],
    }


@router.put("/api/auth/change-password")
async def change_password(request: Request, current_user: dict = Depends(get_current_user)):
    """Đổi mật khẩu. Revoke tất cả refresh token sau khi đổi thành công."""
    body = await request.json()
    current_pw: str = body.get("current_password", "")
    new_pw: str = body.get("new_password", "")
    user_id = str(current_user["user_id"])
    rate_key = f"chpwd:{user_id}"
    now = datetime.now(timezone.utc)

    if not current_pw or not new_pw:
        raise HTTPException(status_code=400, detail="Thiếu current_password hoặc new_password")

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE login_attempts SET attempt_count = 0, locked_until = NULL "
            "WHERE ip_address = ? AND locked_until IS NOT NULL AND locked_until <= ?",
            (rate_key, now.isoformat()),
        )
        conn.commit()

        attempts = conn.execute(
            "SELECT attempt_count, first_attempt_at, locked_until FROM login_attempts WHERE ip_address = ?",
            (rate_key,),
        ).fetchone()

        if attempts and attempts["first_attempt_at"]:
            first_attempt_at = datetime.fromisoformat(attempts["first_attempt_at"])
            if first_attempt_at.tzinfo is None:
                first_attempt_at = first_attempt_at.replace(tzinfo=timezone.utc)
            if now - first_attempt_at > timedelta(minutes=15):
                conn.execute("DELETE FROM login_attempts WHERE ip_address = ?", (rate_key,))
                conn.commit()
                attempts = None

        if attempts and attempts["locked_until"]:
            locked_until = datetime.fromisoformat(attempts["locked_until"])
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            if locked_until > now:
                remaining_seconds = (locked_until - now).total_seconds()
                remaining_minutes = math.ceil(remaining_seconds / 60)
                raise HTTPException(
                    status_code=429,
                    detail=f"Qua nhieu lan thu. Vui long thu lai sau {remaining_minutes} phut.",
                )

        row = conn.execute(
            "SELECT password_hash FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()

    if not row or not verify_password(current_pw, row["password_hash"]):
        with get_db_connection() as conn:
            attempts = conn.execute(
                "SELECT attempt_count FROM login_attempts WHERE ip_address = ?",
                (rate_key,),
            ).fetchone()
            new_count = (int(attempts["attempt_count"]) if attempts else 0) + 1
            locked_until = (now + timedelta(minutes=15)).isoformat() if new_count >= 5 else None
            if attempts:
                conn.execute(
                    "UPDATE login_attempts SET attempt_count = ?, locked_until = ? WHERE ip_address = ?",
                    (new_count, locked_until, rate_key),
                )
            else:
                conn.execute(
                    "INSERT INTO login_attempts (ip_address, attempt_count, first_attempt_at, locked_until) "
                    "VALUES (?, ?, ?, ?)",
                    (rate_key, new_count, now.isoformat(), locked_until),
                )
            conn.commit()
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")

    if len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải có ít nhất 8 ký tự")

    update_user_password(user_id, new_pw)
    revoke_all_tokens_for_user(user_id)
    with get_db_connection() as conn:
        conn.execute("DELETE FROM login_attempts WHERE ip_address = ?", (rate_key,))
        conn.commit()
    logger.info("[Auth] change-password: user %s password updated", user_id)
    return {"ok": True, "message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."}
