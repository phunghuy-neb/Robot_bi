"""
check_and_fix_users.py - Kiem tra va tao admin user neu chua co
Chay: python check_and_fix_users.py
"""
import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from src_brain.network.db import init_db, get_db_connection

init_db()

print("=" * 50)
print("KIEM TRA BANG USERS")
print("=" * 50)

with get_db_connection() as conn:
    rows = conn.execute(
        'SELECT user_id, username, family_name, is_active FROM users'
    ).fetchall()
    print(f"So luong user trong DB: {len(rows)}")
    for r in rows:
        print(f"  - ID={r['user_id']} | username={r['username']} | active={r['is_active']}")

admin_username = os.getenv("ADMIN_USERNAME", "").strip()
admin_password = os.getenv("ADMIN_PASSWORD", "").strip()

print()
print("THONG TIN TU .env:")
print(f"  ADMIN_USERNAME = '{admin_username}'")
print(f"  ADMIN_PASSWORD = '{('*' * len(admin_password)) if admin_password else '(TRONG)'}'")

if not admin_username or not admin_password:
    print()
    print("LOI: ADMIN_USERNAME hoac ADMIN_PASSWORD chua duoc cau hinh trong .env")
    print("Them vao file .env roi chay lai script nay.")
    sys.exit(1)

# Kiem tra username da ton tai chua
with get_db_connection() as conn:
    existing = conn.execute(
        'SELECT user_id FROM users WHERE username = ?', (admin_username,)
    ).fetchone()

if existing:
    print()
    print(f"User '{admin_username}' DA TON TAI trong DB (ID={existing['user_id']}).")
    print("Co the mat khau khong khop. Dat lai mat khau...")
    
    from src_brain.network.auth import hash_password
    new_hash = hash_password(admin_password)
    
    with get_db_connection() as conn:
        conn.execute(
            'UPDATE users SET password_hash = ?, is_active = 1 WHERE username = ?',
            (new_hash, admin_username)
        )
        conn.commit()
    
    print(f"Da cap nhat mat khau cho user '{admin_username}'.")
else:
    print()
    print(f"User '{admin_username}' CHUA CO trong DB. Dang tao...")
    
    from src_brain.network.auth import create_user
    user = create_user(admin_username, admin_password, "Admin")
    print(f"Da tao user: {user}")

print()
print("KIEM TRA LAI:")
with get_db_connection() as conn:
    rows = conn.execute(
        'SELECT user_id, username, family_name, is_active FROM users'
    ).fetchall()
    for r in rows:
        print(f"  - ID={r['user_id']} | username={r['username']} | active={r['is_active']}")

print()
print("XONG. Thu dang nhap lai voi:")
print(f"  Username: {admin_username}")
print(f"  Password: (mat khau trong .env)")

with get_db_connection() as conn:
    conn.execute("DELETE FROM users WHERE username != 'admin'")
    conn.commit()
    print("Da xoa user rac.")