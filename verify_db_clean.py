"""
verify_db_clean.py - Xac nhan DB that khong bi them user rac sau khi chay test
Chay: python verify_db_clean.py
"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from src.infrastructure.database.db import init_db, get_db_connection
init_db()

with get_db_connection() as conn:
    rows = conn.execute(
        "SELECT COUNT(*) as total FROM users"
    ).fetchone()
    total = rows["total"]

    test_users = conn.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE username LIKE 'testuser_%' "
        "OR username LIKE 'dupuser_%' OR username LIKE 'authok_%' "
        "OR username LIKE 'authwrong_%' OR username LIKE 'jwtrot_%'"
    ).fetchone()
    test_count = test_users["cnt"]

print(f"Tong user trong DB: {total}")
print(f"User rac test con lai: {test_count}")

if test_count == 0:
    print("OK: DB sach, khong co user rac.")
else:
    print(f"CANH BAO: Con {test_count} user rac — run_tests.py chua duoc fix dung.")
    print("Xoa user rac...")
    with get_db_connection() as conn:
        conn.execute(
            "DELETE FROM users WHERE username LIKE 'testuser_%' "
            "OR username LIKE 'dupuser_%' OR username LIKE 'authok_%' "
            "OR username LIKE 'authwrong_%' OR username LIKE 'jwtrot_%' "
            "OR username LIKE 'chk_%'"
        )
        conn.commit()
    print("Da xoa xong.")

with get_db_connection() as conn:
    real_users = conn.execute(
        "SELECT user_id, username, family_name FROM users"
    ).fetchall()
    print(f"\nUser that trong DB ({len(real_users)}):")
    for r in real_users:
        print(f"  - ID={r['user_id']} | {r['username']} | {r['family_name']}")
