"""
db.py - SQLite storage helpers for Robot Bi network persistence.
"""

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).with_name("robot_bi.db")

_INIT_LOCK = threading.Lock()
_INITIALIZED = False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_db_connection():
    """Tra ve connection voi WAL mode bat"""
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def cleanup_expired_login_attempts(ttl_minutes: int = 60) -> int:
    """Xoa login_attempts cu hon ttl_minutes. Tra ve so rows da xoa."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            DELETE FROM login_attempts
            WHERE first_attempt_at IS NOT NULL
              AND first_attempt_at < ?
              AND (locked_until IS NULL OR locked_until <= ?)
            """,
            (cutoff, now),
        )
        conn.commit()
        return cur.rowcount


def cleanup_orphan_sessions(max_age_hours: int = 24) -> int:
    """Dong cac session cu co ended_at IS NULL. Tra ve so session da dong."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            UPDATE conversations
            SET ended_at = ?
            WHERE ended_at IS NULL
              AND started_at < ?
            """,
            (_utc_now_iso(), cutoff),
        )
        conn.commit()
        if cur.rowcount > 0:
            logger.info(
                "[DB] Dong %d orphan session cu hon %dh",
                cur.rowcount,
                max_age_hours,
            )
        return cur.rowcount


def init_db() -> None:
    """Khoi tao database va migrate du lieu tu JSON cu neu can."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    with _INIT_LOCK:
        if _INITIALIZED:
            return

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with get_db_connection() as conn:
            # Tao bang events
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS events (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    timestamp TEXT,
                    type TEXT NOT NULL,
                    message TEXT,
                    clip_path TEXT,
                    metadata_json TEXT,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    import_key TEXT UNIQUE
                )
                '''
            )

            # Tao bang tasks - khop voi task_manager.py
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS tasks (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    name TEXT NOT NULL,
                    remind_time TEXT,
                    completed_today INTEGER NOT NULL DEFAULT 0,
                    completed_date TEXT,
                    stars INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    last_reminded TEXT,
                    last_reminded_date TEXT,
                    import_key TEXT UNIQUE
                )
                '''
            )
            task_cols = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
            if "completed_date" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN completed_date TEXT")
            if "last_reminded_date" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN last_reminded_date TEXT")
            conn.execute(
                """
                UPDATE tasks
                SET completed_date = '2000-01-01'
                WHERE completed_today = 1
                  AND (completed_date IS NULL OR completed_date = '')
                """
            )
            for index_sql in (
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_import_key ON events(import_key)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_import_key ON tasks(import_key)",
            ):
                try:
                    conn.execute(index_sql)
                except Exception as e:
                    logger.warning("[DB] Bo qua import_key unique index: %s", e)

            # Tao bang login_attempts (rate limiting cho /api/auth/login va /auth/login/v2)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    ip_address TEXT PRIMARY KEY,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    first_attempt_at TEXT,
                    locked_until TEXT
                )
                '''
            )

            # Tao bang users (username+password auth)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    family_name TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    is_active INTEGER DEFAULT 1,
                    token_version INTEGER NOT NULL DEFAULT 0
                )
                '''
            )

            # Migration: them token_version neu chua co (cho DB cu)
            try:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"
                )
                conn.commit()
            except Exception as e:
                msg = str(e).lower()
                if "duplicate column" in msg or "already exists" in msg:
                    pass  # Column da ton tai
                else:
                    logger.error("[DB] Migration token_version failed: %s", e)
                    raise RuntimeError(f"DB migration that bai: {e}") from e

            # Tao bang auth_tokens (JWT refresh token rotation)
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    refresh_token_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    is_revoked INTEGER NOT NULL DEFAULT 0
                )
                '''
            )

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    family_id TEXT DEFAULT 'default',
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    title TEXT,
                    turn_count INTEGER DEFAULT 0
                )
                '''
            )

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES conversations(session_id),
                    role TEXT NOT NULL CHECK(role IN ('user','assistant','homework')),
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                '''
            )

            conn.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id)
                '''
            )

            _migrate_turns_role_constraint(conn)

            conn.commit()

            # Migrate du lieu cu
            _migrate_legacy_events(conn)
            _migrate_legacy_tasks(conn)

        cleanup_expired_login_attempts(ttl_minutes=1440)

        # Seed admin user neu bang users trong (idempotent)
        try:
            from src_brain.network.auth import seed_admin_if_empty

            seed_admin_if_empty()
        except Exception as _e:
            logger.warning("[DB] seed_admin_if_empty bo qua: %s", _e)

        _INITIALIZED = True
        logger.info("[DB] Database da duoc khoi tao thanh cong.")


def _migrate_legacy_events(conn):
    """Migrate du lieu tu event_queue.json cu sang bang events"""
    json_path = Path(__file__).with_name("event_queue.json")
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            events = json.load(f)

        for event in events:
            conn.execute(
                '''
                INSERT OR IGNORE INTO events
                (event_id, timestamp, type, message, clip_path, metadata_json, is_read)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    event.get("id"),
                    event.get("timestamp"),
                    event.get("type"),
                    event.get("message"),
                    event.get("clip_path"),
                    json.dumps(event.get("metadata", {}), ensure_ascii=False),
                    1 if event.get("read", False) else 0,
                ),
            )
        conn.commit()
        logger.info("[DB] Da migrate %d events tu file JSON cu.", len(events))
    except Exception as e:
        logger.error("[DB] Loi migrate events: %s", e)


def _migrate_legacy_tasks(conn):
    """Migrate du lieu tu tasks.json cu sang bang tasks"""
    json_path = Path(__file__).with_name("tasks.json")
    if not json_path.exists():
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            tasks = json.load(f)

        for task in tasks:
            task_id = task.get("id")
            if not task_id:
                continue

            # Ho tro ca 'name' va 'title' tu du lieu cu
            name = task.get("name") or task.get("title") or "Khong co tieu de"

            conn.execute(
                '''
                INSERT OR IGNORE INTO tasks
                (task_id, name, remind_time, completed_today, stars,
                 created_at, last_reminded, import_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    task_id,
                    name,
                    task.get("remind_time", ""),
                    1 if task.get("completed_today") else 0,
                    int(task.get("stars", 0)),
                    task.get("created_at"),
                    task.get("last_reminded"),
                    task_id,
                ),
            )
        conn.commit()
        logger.info("[DB] Da migrate %d tasks tu file JSON cu.", len(tasks))
    except Exception as e:
        logger.error("[DB] Loi migrate tasks: %s", e)


def _migrate_turns_role_constraint(conn) -> None:
    row = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table' AND name = 'turns'
        """
    ).fetchone()
    if not row:
        return

    create_sql = (row["sql"] or "").replace(" ", "").lower()
    if "'homework'" in create_sql:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("ALTER TABLE turns RENAME TO turns_old")
    conn.execute(
        '''
        CREATE TABLE turns (
            turn_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES conversations(session_id),
            role TEXT NOT NULL CHECK(role IN ('user','assistant','homework')),
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        '''
    )
    conn.execute(
        '''
        INSERT INTO turns (turn_id, session_id, role, content, timestamp)
        SELECT turn_id, session_id, role, content, timestamp
        FROM turns_old
        '''
    )
    conn.execute("DROP TABLE turns_old")
    conn.execute(
        '''
        CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id)
        '''
    )
    conn.execute("PRAGMA foreign_keys = ON")


def create_session(family_id: str) -> str:
    session_id = uuid4().hex
    with get_db_connection() as conn:
        conn.execute(
            '''
            INSERT INTO conversations (session_id, family_id, started_at)
            VALUES (?, ?, ?)
            ''',
            (session_id, family_id, _utc_now_iso()),
        )
        conn.commit()
    return session_id


def close_session(session_id: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            '''
            UPDATE conversations
            SET ended_at = ?
            WHERE session_id = ?
            ''',
            (_utc_now_iso(), session_id),
        )
        conn.commit()


def add_turn(session_id: str, role: str, content: str) -> str:
    if role not in {"user", "assistant", "homework"}:
        raise ValueError("Invalid turn role")
    turn_id = uuid4().hex
    with get_db_connection() as conn:
        conn.execute(
            '''
            INSERT INTO turns (turn_id, session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (turn_id, session_id, role, content, _utc_now_iso()),
        )
        conn.execute(
            '''
            UPDATE conversations
            SET turn_count = turn_count + 1
            WHERE session_id = ?
            ''',
            (session_id,),
        )
        conn.commit()
    return turn_id


def get_session_turns(session_id: str) -> list[dict]:
    with get_db_connection() as conn:
        rows = conn.execute(
            '''
            SELECT turn_id, session_id, role, content, timestamp
            FROM turns
            WHERE session_id = ?
            ORDER BY timestamp ASC
            ''',
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_session_title(session_id: str, title: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            '''
            UPDATE conversations
            SET title = ?
            WHERE session_id = ?
            ''',
            (title, session_id),
        )
        conn.commit()


def get_token_version(user_id: str) -> int:
    """Trả về token_version hiện tại của user. Trả 0 nếu user không tồn tại."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT token_version FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
    return int(row["token_version"]) if row else 0


def increment_token_version(user_id: str) -> int:
    """Tăng token_version, vô hiệu hóa tất cả access token hiện có. Trả về version mới."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE users SET token_version = token_version + 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT token_version FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row["token_version"]) if row else 0


def get_user_by_id(user_id: str) -> dict | None:
    """Trả về dict {user_id, username, family_name, created_at} hoặc None."""
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, family_name, created_at FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def update_user_password(user_id: str, new_password: str) -> bool:
    """Hash new_password va update DB. Token version do revoke_all_tokens_for_user() tang."""
    from src_brain.network.auth import hash_password
    new_hash = hash_password(new_password)
    with get_db_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash=? WHERE user_id=?",
            (new_hash, user_id),
        )
        conn.commit()
    return cur.rowcount > 0


def revoke_all_tokens_for_user(user_id: str) -> int:
    """Revoke tất cả refresh token + tăng token_version. Trả về số refresh token bị revoke."""
    with get_db_connection() as conn:
        cur = conn.execute(
            "UPDATE auth_tokens SET is_revoked=1 WHERE user_id=? AND is_revoked=0",
            (user_id,)
        )
        count = cur.rowcount
        conn.execute(
            "UPDATE users SET token_version = token_version + 1 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        return count
