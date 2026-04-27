"""
auth.py — Authentication helpers for Robot Bi.
Handles user creation, password hashing (Argon2id via argon2-cffi), and authentication.
"""

import hashlib as _hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("auth")

try:
    from fastapi import Security as _FastAPISecurity
    from fastapi.security import (
        HTTPAuthorizationCredentials as _HTTPAuthorizationCredentials,
        HTTPBearer as _HTTPBearer,
    )
    _http_bearer = _HTTPBearer(auto_error=False)
    _FASTAPI_SECURITY_AVAILABLE = True
except ImportError:
    _FastAPISecurity = None
    _HTTPAuthorizationCredentials = None
    _http_bearer = None
    _FASTAPI_SECURITY_AVAILABLE = False
    logger.warning("[Auth] fastapi.security khong co san — get_current_user bi vo hieu hoa")

try:
    from jose import jwt as _jose_jwt
    _JOSE_AVAILABLE = True
except ImportError:
    _JOSE_AVAILABLE = False
    logger.warning("[Auth] python-jose chua duoc cai dat — JWT bi vo hieu hoa. Chay: pip install 'python-jose[cryptography]'")

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

    _ph = PasswordHasher()  # Default: Argon2id, time_cost=3, memory_cost=65536
    _ARGON2_AVAILABLE = True
except ImportError:
    _ARGON2_AVAILABLE = False
    logger.warning("[Auth] argon2-cffi chua duoc cai dat — hash password bi vo hieu hoa")

from src_brain.network.db import get_db_connection


def hash_password(plain: str) -> str:
    """Hash plaintext password dung Argon2id."""
    if not _ARGON2_AVAILABLE:
        raise RuntimeError("argon2-cffi chua duoc cai dat. Chay: pip install argon2-cffi")
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """So sanh password plain voi Argon2id hash da luu. Tra False neu sai hoac loi."""
    if not _ARGON2_AVAILABLE:
        return False
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_user(username: str, password: str, family_name: str) -> dict:
    """
    Tao user moi. Raise HTTPException(409) neu username da ton tai.
    Tra ve dict user (khong co password_hash).
    """
    from fastapi import HTTPException

    password_hash = hash_password(password)

    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT user_id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Username da ton tai")

        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, family_name) VALUES (?, ?, ?)",
            (username, password_hash, family_name),
        )
        conn.commit()
        user_id = cursor.lastrowid

    return {
        "user_id": user_id,
        "username": username,
        "family_name": family_name,
    }


def get_user_by_username(username: str) -> dict | None:
    """Lay user theo username. Tra None neu khong tim thay."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, password_hash, family_name, created_at, is_active "
            "FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    return dict(row) if row is not None else None


def authenticate_user(username: str, password: str) -> dict | None:
    """
    Xac thuc user bang username + password.
    Tra ve dict user (khong co password_hash) neu hop le va dang active, nguoc lai tra None.
    """
    user = get_user_by_username(username)
    if user is None:
        return None
    if not user.get("is_active"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "family_name": user["family_name"],
    }


def seed_admin_if_empty() -> None:
    """
    Tao admin user tu .env neu bang users dang trong.
    Idempotent — co the goi nhieu lan ma khong co hieu ung phu.
    Khong log plaintext password, khong crash khi thieu env.
    """
    admin_username = os.getenv("ADMIN_USERNAME", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()

    if not admin_username or not admin_password:
        logger.warning(
            "[Auth] ADMIN_USERNAME/ADMIN_PASSWORD chua duoc cau hinh trong .env "
            "— bo qua seed admin"
        )
        return

    if not _ARGON2_AVAILABLE:
        logger.warning("[Auth] argon2-cffi khong co — khong the seed admin")
        return

    with get_db_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()["cnt"]
        if count > 0:
            return  # Da co users — bo qua

        password_hash = hash_password(admin_password)
        conn.execute(
            "INSERT INTO users (username, password_hash, family_name) VALUES (?, ?, ?)",
            (admin_username, password_hash, "Admin"),
        )
        conn.commit()

    logger.info("[Auth] Admin user da duoc tao thanh cong.")


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _get_jwt_config() -> tuple[str, str]:
    """Doc JWT config tu env. Raise RuntimeError neu thieu hoac sai thuat toan."""
    jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
    jwt_alg = os.getenv("JWT_ALGORITHM", "HS256").strip()
    if not jwt_secret:
        raise RuntimeError(
            "[Auth] JWT_SECRET_KEY chua duoc cau hinh trong .env. "
            "Them JWT_SECRET_KEY=<secret> vao file .env."
        )
    if jwt_alg != "HS256":
        raise RuntimeError(
            f"[Auth] JWT_ALGORITHM phai la HS256, nhan duoc: {jwt_alg!r}"
        )
    return jwt_secret, jwt_alg


def create_access_token(user_id: str, family_name: str) -> str:
    """
    Tao JWT access token.
    Payload: sub=user_id, family=family_name, type="access", tv=token_version, exp=now+60min.
    """
    if not _JOSE_AVAILABLE:
        raise RuntimeError("python-jose chua duoc cai dat. Chay: pip install 'python-jose[cryptography]'")
    jwt_secret, jwt_alg = _get_jwt_config()
    from src_brain.network.db import get_token_version
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "family": family_name,
        "type": "access",
        "tv": get_token_version(str(user_id)),
        "iat": now,
        "exp": now + timedelta(minutes=60),
    }
    return _jose_jwt.encode(payload, jwt_secret, algorithm=jwt_alg)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    Tao refresh token.
    Tra ve (raw_token, hashed_token):
      - raw_token: tra cho client (chi dung 1 lan)
      - hashed_token: sha256 hex, luu vao DB
    """
    import secrets as _sec
    raw_token = _sec.token_urlsafe(32)
    hashed_token = _hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, hashed_token


def store_refresh_token(user_id: str, hashed_token: str, expires_at: datetime) -> str:
    """
    Luu hashed refresh token vao bang auth_tokens (is_revoked=0).
    Tra ve token_id (str).
    """
    with get_db_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO auth_tokens (user_id, refresh_token_hash, expires_at, is_revoked) "
            "VALUES (?, ?, ?, 0)",
            (str(user_id), hashed_token, expires_at.isoformat()),
        )
        conn.commit()
        return str(cursor.lastrowid)


def verify_access_token(token: str) -> dict:
    """
    Decode va xac thuc JWT access token.
    Tra ve payload dict neu hop le.
    Raise HTTPException(401) neu loi, het han, hoac sai type.
    """
    from fastapi import HTTPException

    if not _JOSE_AVAILABLE:
        raise HTTPException(status_code=401, detail="JWT chua duoc cau hinh")
    try:
        jwt_secret, jwt_alg = _get_jwt_config()
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))

    try:
        payload = _jose_jwt.decode(token, jwt_secret, algorithms=[jwt_alg])
    except Exception:
        raise HTTPException(status_code=401, detail="Token khong hop le hoac da het han")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Sai loai token")

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_version, is_active FROM users WHERE user_id = ?",
            (str(payload.get("sub", "")),),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="User khong ton tai")

    if not row["is_active"]:
        raise HTTPException(status_code=401, detail="Tai khoan da bi vo hieu hoa")

    if int(row["token_version"]) != int(payload.get("tv", 0)):
        raise HTTPException(status_code=401, detail="Token da bi vo hieu hoa")

    return payload


def rotate_refresh_token(old_raw_token: str) -> tuple[str, str, str]:
    """
    Rotation refresh token — thuc hien atomic trong cung transaction:
    1. Hash old_raw_token → tim record WHERE refresh_token_hash = hash AND is_revoked = 0
    2. Neu khong tim thay hoac het han → raise HTTPException(401)
    3. Mark old token: is_revoked = 1
    4. Tao va luu new refresh token (expires_at = now_utc + 30 ngay)
    Tra ve (new_raw_token, new_hashed_token, user_id).
    """
    from fastapi import HTTPException
    import secrets as _sec

    old_hashed = _hashlib.sha256(old_raw_token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    new_expires_at = now + timedelta(days=30)

    new_raw = _sec.token_urlsafe(32)
    new_hashed = _hashlib.sha256(new_raw.encode()).hexdigest()

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_id, user_id, expires_at, is_revoked "
            "FROM auth_tokens WHERE refresh_token_hash = ?",
            (old_hashed,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        if row["is_revoked"]:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        expires_at_str = row["expires_at"]
        expires_at = datetime.fromisoformat(expires_at_str)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        user_id = str(row["user_id"])

        # Atomic: exactly one concurrent caller can revoke this refresh token.
        cur = conn.execute(
            "UPDATE auth_tokens SET is_revoked = 1 WHERE token_id = ? AND is_revoked = 0",
            (row["token_id"],),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        conn.execute(
            "INSERT INTO auth_tokens (user_id, refresh_token_hash, expires_at, is_revoked) "
            "VALUES (?, ?, ?, 0)",
            (user_id, new_hashed, new_expires_at.isoformat()),
        )
        conn.commit()

    return new_raw, new_hashed, user_id


# ── JWT FastAPI Dependency ────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[_HTTPAuthorizationCredentials] = (
        _FastAPISecurity(_http_bearer) if _FASTAPI_SECURITY_AVAILABLE else None
    ),
) -> dict:
    """
    FastAPI dependency: xac thuc JWT Bearer token tu Authorization header.
    Tra ve {"user_id": str, "family_name": str} neu hop le.
    Raise HTTPException(401) voi WWW-Authenticate: Bearer neu thieu hoac invalid.
    Su dung: Depends(get_current_user) trong route handler.
    """
    from fastapi import HTTPException

    if not _FASTAPI_SECURITY_AVAILABLE:
        raise HTTPException(
            status_code=500,
            detail="fastapi.security khong co san",
        )
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_access_token(credentials.credentials)
    except HTTPException:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "user_id": payload["sub"],
        "family_name": payload["family"],
    }
