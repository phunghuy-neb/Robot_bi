"""
db.py - SQLite storage helpers for Robot Bi network persistence.
"""

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).with_name("robot_bi.db")

_INIT_LOCK = threading.Lock()
_INITIALIZED = False


@contextmanager
def get_db_connection():
    """Trả về connection với WAL mode bật"""
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Khởi tạo database và migrate dữ liệu từ JSON cũ nếu cần."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    with _INIT_LOCK:
        if _INITIALIZED:
            return

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with get_db_connection() as conn:
            # Tạo bảng events
            conn.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    timestamp TEXT,
                    type TEXT NOT NULL,
                    message TEXT,
                    clip_path TEXT,
                    metadata_json TEXT,
                    is_read INTEGER NOT NULL DEFAULT 0,
                    import_key TEXT
                )
            ''')

            # Tạo bảng tasks (schema chuẩn hóa)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    last_reminded TEXT
                )
            ''')

            # Tạo bảng login_attempts (rate limiting cho /api/auth/login và /auth/login/v2)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS login_attempts (
                    ip_address TEXT PRIMARY KEY,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    first_attempt_at TEXT,
                    locked_until TEXT
                )
            ''')

            # Tạo bảng users (username+password auth)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    family_name TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    is_active INTEGER DEFAULT 1
                )
            ''')

            # Tạo bảng auth_tokens (JWT refresh token rotation)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS auth_tokens (
                    token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    refresh_token_hash TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    is_revoked INTEGER NOT NULL DEFAULT 0
                )
            ''')

            conn.commit()

            # Migrate dữ liệu cũ
            _migrate_legacy_events(conn)
            _migrate_legacy_tasks(conn)

        # Seed admin user nếu bảng users trống (idempotent)
        try:
            from src_brain.network.auth import seed_admin_if_empty
            seed_admin_if_empty()
        except Exception as _e:
            print(f"[DB] seed_admin_if_empty bo qua: {_e}")

        _INITIALIZED = True
        print("[DB] Database đã được khởi tạo thành công.")


def _migrate_legacy_events(conn):
    """Migrate dữ liệu từ event_queue.json cũ sang bảng events"""
    json_path = Path(__file__).with_name("event_queue.json")
    if not json_path.exists():
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            events = json.load(f)

        for event in events:
            conn.execute('''
                INSERT OR IGNORE INTO events 
                (event_id, timestamp, type, message, clip_path, metadata_json, is_read)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.get('id'),
                event.get('timestamp'),
                event.get('type'),
                event.get('message'),
                event.get('clip_path'),
                json.dumps(event.get('metadata', {}), ensure_ascii=False),
                1 if event.get('read', False) else 0
            ))
        conn.commit()
        print(f"[DB] Đã migrate {len(events)} events từ file JSON cũ.")
    except Exception as e:
        print(f"[DB] Lỗi migrate events: {e}")


def _migrate_legacy_tasks(conn):
    """Migrate dữ liệu từ tasks.json cũ sang bảng tasks"""
    json_path = Path(__file__).with_name("tasks.json")
    if not json_path.exists():
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            tasks = json.load(f)

        for task in tasks:
            task_id = task.get('id')
            if not task_id:
                continue

            # Hỗ trợ cả 'title' và 'name' từ dữ liệu cũ
            title = task.get('title') or task.get('name') or "Không có tiêu đề"

            conn.execute('''
                INSERT OR IGNORE INTO tasks 
                (task_id, title, status, created_at, last_reminded)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                task_id,
                title,
                task.get('status', 'pending'),
                task.get('created_at'),
                task.get('last_reminded')
            ))
        conn.commit()
        print(f"[DB] Đã migrate {len(tasks)} tasks từ file JSON cũ.")
    except Exception as e:
        print(f"[DB] Lỗi migrate tasks: {e}")