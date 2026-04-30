"""
db.py - SQLite storage helpers for Robot Bi network persistence.
"""

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent.parent
OLD_DB_PATHS = [
    REPO_ROOT / "src_brain" / "network" / "robot_bi.db",
    REPO_ROOT / "src_brain" / "network" / "data" / "robot_bi.db",
    REPO_ROOT / "robot_bi.db",
]
NEW_DB_PATH = REPO_ROOT / "runtime" / "robot_bi.db"
DB_PATH = NEW_DB_PATH

_INIT_LOCK = threading.Lock()
_INITIALIZED = False


def migrate_db_path_if_needed() -> None:
    """
    One-time migration: copy DB tu path cu sang runtime/robot_bi.db.

    Chi copy khi DB moi chua ton tai hoac gan nhu rong, va co DB cu co data.
    DB cu duoc giu nguyen de rollback an toan.
    """
    import shutil

    if NEW_DB_PATH.exists() and NEW_DB_PATH.stat().st_size > 8192:
        return

    old_db = None
    for path in OLD_DB_PATHS:
        if not path.exists():
            continue
        size = path.stat().st_size
        if size <= 8192:
            continue
        if old_db is None or size > old_db.stat().st_size:
            old_db = path

    if old_db is None:
        return

    NEW_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(old_db, NEW_DB_PATH)
    logger.info(
        "[DB] Migrated DB from %s to %s (%d bytes)",
        old_db,
        NEW_DB_PATH,
        NEW_DB_PATH.stat().st_size,
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_family_id(family_id: str | None) -> str:
    fid = (family_id or "").strip()
    return fid or os.getenv("FAMILY_ID", "default")


def _ensure_family_exists_conn(conn, family_id: str | None, display_name: str | None = None) -> str:
    fid = _normalize_family_id(family_id)
    label = (display_name or fid).strip() or fid
    conn.execute(
        """
        INSERT OR IGNORE INTO families (family_id, display_name, created_at)
        VALUES (?, ?, ?)
        """,
        (fid, label, _utc_now_iso()),
    )
    return fid


def ensure_family_exists(family_id: str | None, display_name: str | None = None) -> str:
    """Create the family row if missing and return the normalized family_id."""
    with get_db_connection() as conn:
        fid = _ensure_family_exists_conn(conn, family_id, display_name)
        conn.commit()
        return fid


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
    migrate_db_path_if_needed()
    if _INITIALIZED:
        return

    with _INIT_LOCK:
        if _INITIALIZED:
            return

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with get_db_connection() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS families (
                    family_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                '''
            )
            _ensure_family_exists_conn(conn, "default", "default")

            # Tao bang events
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS events (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL DEFAULT 'default'
                        REFERENCES families(family_id) ON DELETE CASCADE,
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
            event_cols = {row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()}
            if "family_id" not in event_cols:
                conn.execute("ALTER TABLE events ADD COLUMN family_id TEXT DEFAULT 'default'")
            conn.execute(
                """
                UPDATE events
                SET family_id = 'default'
                WHERE family_id IS NULL OR family_id = ''
                """
            )

            # Tao bang tasks - khop voi task_manager.py
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS tasks (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL DEFAULT 'default'
                        REFERENCES families(family_id) ON DELETE CASCADE,
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
            if "family_id" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN family_id TEXT DEFAULT 'default'")
            if "completed_date" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN completed_date TEXT")
            if "last_reminded_date" not in task_cols:
                conn.execute("ALTER TABLE tasks ADD COLUMN last_reminded_date TEXT")
            conn.execute(
                """
                UPDATE tasks
                SET family_id = 'default'
                WHERE family_id IS NULL OR family_id = ''
                """
            )
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
                "CREATE INDEX IF NOT EXISTS idx_events_family_db ON events(family_id, db_id)",
                "CREATE INDEX IF NOT EXISTS idx_tasks_family_db ON tasks(family_id, db_id)",
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
                    family_name TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    is_active INTEGER DEFAULT 1,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    token_version INTEGER NOT NULL DEFAULT 0
                )
                '''
            )
            user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "is_admin" not in user_cols:
                conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                """
                INSERT OR IGNORE INTO families (family_id, display_name, created_at)
                SELECT DISTINCT family_name, family_name, ?
                FROM users
                WHERE family_name IS NOT NULL AND family_name != ''
                """,
                (_utc_now_iso(),),
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
                    family_id TEXT NOT NULL DEFAULT 'default'
                        REFERENCES families(family_id) ON DELETE CASCADE,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    title TEXT,
                    turn_count INTEGER DEFAULT 0,
                    is_homework INTEGER NOT NULL DEFAULT 0,
                    homework_marked_at TEXT DEFAULT NULL
                )
                '''
            )
            conversation_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()
            }
            if "family_id" not in conversation_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN family_id TEXT DEFAULT 'default'")
            if "is_homework" not in conversation_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN is_homework INTEGER NOT NULL DEFAULT 0")
            if "homework_marked_at" not in conversation_cols:
                conn.execute("ALTER TABLE conversations ADD COLUMN homework_marked_at TEXT DEFAULT NULL")
            conn.execute(
                """
                UPDATE conversations
                SET family_id = 'default',
                    is_homework = COALESCE(is_homework, 0)
                WHERE family_id IS NULL OR family_id = '' OR is_homework IS NULL
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO families (family_id, display_name, created_at)
                SELECT DISTINCT family_id, family_id, ?
                FROM conversations
                WHERE family_id IS NOT NULL AND family_id != ''
                """,
                (_utc_now_iso(),),
            )

            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
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
            conn.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_conversations_family_started
                ON conversations(family_id, started_at)
                '''
            )
            conn.execute(
                '''
                CREATE INDEX IF NOT EXISTS idx_conversations_family_homework_started
                ON conversations(family_id, is_homework, started_at)
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS learning_schedules (
                    family_id TEXT NOT NULL,
                    day_of_week TEXT NOT NULL,
                    subject TEXT,
                    time TEXT,
                    updated_at TEXT,
                    PRIMARY KEY (family_id, day_of_week)
                )
                '''
            )
            for trigger_sql in (
                '''
                CREATE TRIGGER IF NOT EXISTS trg_users_family_auto
                BEFORE INSERT ON users
                WHEN NEW.family_name IS NOT NULL AND NEW.family_name != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_name, NEW.family_name, datetime('now'));
                END
                ''',
                '''
                CREATE TRIGGER IF NOT EXISTS trg_conversations_family_auto
                BEFORE INSERT ON conversations
                WHEN NEW.family_id IS NOT NULL AND NEW.family_id != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_id, NEW.family_id, datetime('now'));
                END
                ''',
                '''
                CREATE TRIGGER IF NOT EXISTS trg_events_family_auto
                BEFORE INSERT ON events
                WHEN NEW.family_id IS NOT NULL AND NEW.family_id != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_id, NEW.family_id, datetime('now'));
                END
                ''',
                '''
                CREATE TRIGGER IF NOT EXISTS trg_tasks_family_auto
                BEFORE INSERT ON tasks
                WHEN NEW.family_id IS NOT NULL AND NEW.family_id != ''
                BEGIN
                    INSERT OR IGNORE INTO families(family_id, display_name, created_at)
                    VALUES (NEW.family_id, NEW.family_id, datetime('now'));
                END
                ''',
            ):
                conn.execute(trigger_sql)

            _migrate_turns_role_constraint(conn)

            # Normalize legacy capitalized 'Admin' family to lowercase 'admin'
            _migrate_admin_family_case(conn)

            conn.commit()

            # Migrate du lieu cu
            _migrate_legacy_events(conn)
            _migrate_legacy_tasks(conn)

        cleanup_expired_login_attempts(ttl_minutes=1440)

        # Seed admin user neu bang users trong (idempotent)
        try:
            from src.infrastructure.auth.auth import seed_admin_if_empty

            seed_admin_if_empty()
        except Exception as _e:
            logger.warning("[DB] seed_admin_if_empty bo qua: %s", _e)

        _INITIALIZED = True
        logger.info("[DB] Database da duoc khoi tao thanh cong.")


def get_learning_schedule(family_id: str) -> dict:
    """Load schedule tu DB. Tra ve dict {day: {subject, time}}."""
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT day_of_week, subject, time
            FROM learning_schedules
            WHERE family_id = ?
            """,
            (fid,),
        ).fetchall()
    return {
        row["day_of_week"]: {
            "subject": row["subject"],
            "time": row["time"],
        }
        for row in rows
    }


def save_learning_schedule(family_id: str, schedule: dict) -> bool:
    """Luu schedule vao DB."""
    try:
        fid = ensure_family_exists(family_id)
        with get_db_connection() as conn:
            for day, info in (schedule or {}).items():
                day_key = str(day)
                if info is None:
                    conn.execute(
                        """
                        DELETE FROM learning_schedules
                        WHERE family_id = ? AND day_of_week = ?
                        """,
                        (fid, day_key),
                    )
                else:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO learning_schedules
                            (family_id, day_of_week, subject, time, updated_at)
                        VALUES (?, ?, ?, ?, datetime('now'))
                        """,
                        (fid, day_key, info.get("subject"), info.get("time")),
                    )
            conn.commit()
        return True
    except Exception as e:
        logger.error("[DB] save_learning_schedule error: %s", e)
        return False


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
    if "'homework'" in create_sql and "ondeletecascade" in create_sql:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("ALTER TABLE turns RENAME TO turns_old")
    conn.execute(
        '''
        CREATE TABLE turns (
            turn_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES conversations(session_id) ON DELETE CASCADE,
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


def _migrate_admin_family_case(conn) -> None:
    """Rename legacy 'Admin' (capital A) family to lowercase 'admin' if present."""
    row = conn.execute("SELECT family_id FROM families WHERE family_id = 'Admin'").fetchone()
    if not row:
        return
    conn.execute(
        "INSERT OR IGNORE INTO families (family_id, display_name, created_at) VALUES ('admin', 'admin', ?)",
        (_utc_now_iso(),),
    )
    # FK is ON but 'admin' now exists, so these UPDATEs are safe
    conn.execute("UPDATE users SET family_name = 'admin' WHERE family_name = 'Admin'")
    conn.execute("UPDATE conversations SET family_id = 'admin' WHERE family_id = 'Admin'")
    conn.execute("UPDATE events SET family_id = 'admin' WHERE family_id = 'Admin'")
    conn.execute("UPDATE tasks SET family_id = 'admin' WHERE family_id = 'Admin'")
    conn.execute("DELETE FROM families WHERE family_id = 'Admin'")


def create_session(family_id: str) -> str:
    family_id = ensure_family_exists(family_id)
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


def _resolve_session_family_conn(conn, session_id: str) -> str | None:
    row = conn.execute(
        "SELECT family_id FROM conversations WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["family_id"] if row else None


def close_session(session_id: str, family_id: str | None = None) -> None:
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return
        conn.execute(
            '''
            UPDATE conversations
            SET ended_at = ?
            WHERE session_id = ? AND family_id = ?
            ''',
            (_utc_now_iso(), session_id, fid),
        )
        conn.commit()


def add_turn(session_id: str, role: str, content: str, family_id: str | None = None) -> str:
    if role not in {"user", "assistant", "homework"}:
        raise ValueError("Invalid turn role")
    turn_id = uuid4().hex
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            raise ValueError("Session not found")
        cur = conn.execute(
            '''
            INSERT INTO turns (turn_id, session_id, role, content, timestamp)
            SELECT ?, c.session_id, ?, ?, ?
            FROM conversations c
            WHERE c.session_id = ? AND c.family_id = ?
            ''',
            (turn_id, role, content, _utc_now_iso(), session_id, fid),
        )
        if cur.rowcount == 0:
            raise ValueError("Session not found")
        conn.execute(
            '''
            UPDATE conversations
            SET turn_count = turn_count + 1
            WHERE session_id = ? AND family_id = ?
            ''',
            (session_id, fid),
        )
        conn.commit()
    return turn_id


def get_session_turns(session_id: str, family_id: str | None = None) -> list[dict]:
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return []
        rows = conn.execute(
            '''
            SELECT t.turn_id, t.session_id, t.role, t.content, t.timestamp
            FROM turns t
            JOIN conversations c ON c.session_id = t.session_id
            WHERE t.session_id = ? AND c.family_id = ?
            ORDER BY t.timestamp ASC
            ''',
            (session_id, fid),
        ).fetchall()
    return [dict(row) for row in rows]


def update_session_title(session_id: str, title: str, family_id: str | None = None) -> None:
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return
        conn.execute(
            '''
            UPDATE conversations
            SET title = ?
            WHERE session_id = ? AND family_id = ?
            ''',
            (title, session_id, fid),
        )
        conn.commit()


def mark_session_homework(session_id: str, family_id: str | None = None) -> bool:
    if not session_id:
        return False
    with get_db_connection() as conn:
        fid = _normalize_family_id(family_id) if family_id else _resolve_session_family_conn(conn, session_id)
        if not fid:
            return False
        cur = conn.execute(
            """
            UPDATE conversations
            SET is_homework = 1,
                homework_marked_at = datetime('now')
            WHERE session_id = ? AND family_id = ?
            """,
            (session_id, fid),
        )
        conn.commit()
        return cur.rowcount > 0


def get_homework_sessions(
    family_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    fid = _normalize_family_id(family_id)
    safe_limit = max(1, min(int(limit), 50))
    safe_offset = max(0, int(offset))
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT session_id, family_id, title,
                   started_at, ended_at, turn_count,
                   is_homework, homework_marked_at
            FROM conversations
            WHERE family_id = ? AND is_homework = 1
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            (fid, safe_limit, safe_offset),
        ).fetchall()
    return [dict(row) for row in rows]


def list_families() -> list[dict]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT f.family_id, f.display_name, f.created_at,
                   COUNT(DISTINCT u.user_id) AS user_count
            FROM families f
            LEFT JOIN users u ON u.family_name = f.family_id
            GROUP BY f.family_id, f.display_name, f.created_at
            ORDER BY f.created_at ASC, f.family_id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_family_record(family_id: str, display_name: str | None = None) -> dict | None:
    fid = _normalize_family_id(family_id)
    label = (display_name or fid).strip() or fid
    with get_db_connection() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO families (family_id, display_name, created_at)
            VALUES (?, ?, ?)
            """,
            (fid, label, _utc_now_iso()),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
    return {"family_id": fid, "display_name": label}


def delete_family_record(family_id: str) -> bool:
    fid = _normalize_family_id(family_id)
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT family_id FROM families WHERE family_id = ?",
            (fid,),
        ).fetchone()
        family_exists = row is not None

        # Delete order matters: child rows before parent rows.
        # auth_tokens has no FK to families — must cascade manually via user_id.
        user_rows = conn.execute(
            "SELECT user_id FROM users WHERE family_name = ?",
            (fid,),
        ).fetchall()
        user_ids = [str(row["user_id"]) for row in user_rows]
        if user_ids:
            placeholders = ",".join("?" for _ in user_ids)
            # Step 1: auth_tokens (no FK to families; references users)
            conn.execute(
                f"DELETE FROM auth_tokens WHERE user_id IN ({placeholders})",
                tuple(user_ids),
            )

        # Step 2: turns (FK → conversations, not families directly)
        conn.execute(
            """
            DELETE FROM turns
            WHERE session_id IN (
                SELECT session_id FROM conversations WHERE family_id = ?
            )
            """,
            (fid,),
        )
        # Steps 3-5: tables with FK → families (ON DELETE CASCADE would handle
        # these if FK enforcement is active, but explicit deletes are safer)
        conn.execute("DELETE FROM conversations WHERE family_id = ?", (fid,))
        conn.execute("DELETE FROM events WHERE family_id = ?", (fid,))
        conn.execute("DELETE FROM tasks WHERE family_id = ?", (fid,))

        # Steps 6-12: newer family-scoped feature tables.
        for table_name in (
            "learning_schedules",
            "emotion_logs",
            "emotion_journal",
            "emotion_alerts",
            "persona",
            "education_sessions",
            "curriculum_schedules",
        ):
            try:
                conn.execute(f"DELETE FROM {table_name} WHERE family_id = ?", (fid,))
            except Exception:
                pass

        # Step 13: users (FK → families)
        conn.execute("DELETE FROM users WHERE family_name = ?", (fid,))
        # Step 14: families (parent row — delete last)
        cur = conn.execute("DELETE FROM families WHERE family_id = ?", (fid,))
        conn.commit()
        return family_exists and cur.rowcount > 0


def is_user_admin(user_id: str) -> bool:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT is_admin, is_active FROM users WHERE user_id = ?",
            (str(user_id),),
        ).fetchone()
    return bool(row and row["is_active"] and row["is_admin"])


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
    from src.infrastructure.auth.auth import hash_password
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
