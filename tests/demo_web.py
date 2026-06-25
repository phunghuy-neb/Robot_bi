#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
demo_web.py — Robot Bi lightweight web/API demo test.

Chạy KHÔNG cần: mic, loa, camera, GPU.
Chạy CÓ cần: .env với ít nhất 1 API key hoặc SKIP_LLM=1 để bỏ qua LLM.

  python tests/demo_web.py              # test tất cả endpoint + LLM
  SKIP_LLM=1 python tests/demo_web.py  # test endpoint nhưng bỏ qua LLM call

Kết quả in ra terminal: từng test PASS / FAIL + bản tóm tắt cuối.
"""

import sys
import os
import uuid
import json
import time

# Đảm bảo root là working dir để import src.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env cần thiết để khởi tạo auth module
os.environ.setdefault("JWT_SECRET_KEY", "demo_web_test_jwt_secret_key_robot_bi!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

# ── Dùng DB test riêng (không ghi vào robot_bi.db thật) ──────────────────────
import tempfile
import src.infrastructure.database.db as _db_module

_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db_file.close()
_db_module.DB_PATH = __import__("pathlib").Path(_db_file.name)
_db_module._INITIALIZED = False

from src.infrastructure.database.db import init_db
init_db()

# ── Helpers ──────────────────────────────────────────────────────────────────
from fastapi.testclient import TestClient
from src.api.server import app
from src.infrastructure.auth.auth import create_user, create_access_token

SKIP_LLM = os.environ.get("SKIP_LLM", "").strip() in ("1", "true", "yes")

passed = []
failed = []


def _new_family():
    return f"demo-{uuid.uuid4().hex[:8]}"


def _make_headers(prefix="demo", family_id=None):
    fam = family_id or _new_family()
    user = create_user(f"{prefix}_{uuid.uuid4().hex[:6]}", "Password1!", fam)
    token = create_access_token(str(user["user_id"]), user["family_name"])
    return {"Authorization": f"Bearer {token}"}, fam


def check(name, cond, detail=""):
    if cond:
        passed.append(name)
        print(f"  PASS  {name}")
    else:
        failed.append((name, detail))
        print(f"  FAIL  {name}: {detail}")


def run(name, fn):
    try:
        fn()
    except AssertionError as e:
        failed.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")
    except Exception as e:
        failed.append((name, f"{type(e).__name__}: {e}"))
        print(f"  FAIL  {name}: {type(e).__name__}: {e}")
    else:
        passed.append(name)
        print(f"  PASS  {name}")


# ── Shared client ─────────────────────────────────────────────────────────────
client = TestClient(app, raise_server_exceptions=False)

print("=" * 60)
print("  ROBOT BI — DEMO WEB TEST (no mic / no camera)")
print(f"  SKIP_LLM={'yes' if SKIP_LLM else 'no'}")
print("=" * 60)

# ── 1. Health & public ───────────────────────────────────────────────────────
print("\n[1] Health & public endpoints")


def test_health():
    r = client.get("/health")
    assert r.status_code == 200, f"status={r.status_code}"
    body = r.json()
    assert "status" in body, "missing 'status' key"


def test_root():
    r = client.get("/")
    assert r.status_code in (200, 307, 404), f"status={r.status_code}"


run("GET /health → 200 with status", test_health)
run("GET /        → acceptable", test_root)

# ── 2. Auth ──────────────────────────────────────────────────────────────────
print("\n[2] Auth endpoints")


def test_login_missing_fields():
    r = client.post("/api/auth/login", json={})
    assert r.status_code == 422


def test_login_wrong_password():
    r = client.post("/api/auth/login", json={"username": "nobody", "password": "wrongpw"})
    assert r.status_code in (401, 404, 422)


def test_login_v2_valid():
    fam = _new_family()
    user = create_user(f"logintest_{uuid.uuid4().hex[:6]}", "Password1!", fam)
    r = client.post("/auth/login/v2",
                    json={"username": user["username"], "password": "Password1!"})
    assert r.status_code == 200, f"status={r.status_code} body={r.text[:200]}"
    body = r.json()
    assert "access_token" in body, "no access_token"
    assert body["token_type"] == "bearer"


run("POST /api/auth/login missing fields → 422",    test_login_missing_fields)
run("POST /api/auth/login wrong pw → 401/404",      test_login_wrong_password)
run("POST /auth/login/v2 valid → 200 + token",      test_login_v2_valid)

# ── 3. Protected endpoints reject unauthenticated ────────────────────────────
print("\n[3] Auth protection")


def test_status_requires_auth():
    r = client.get("/api/status")
    assert r.status_code == 401, f"expected 401 got {r.status_code}"


def test_conversations_requires_auth():
    r = client.get("/api/conversations")
    assert r.status_code == 401, f"expected 401 got {r.status_code}"


def test_tasks_requires_auth():
    r = client.get("/api/tasks")
    assert r.status_code == 401, f"expected 401 got {r.status_code}"


run("GET /api/status without auth → 401",        test_status_requires_auth)
run("GET /api/conversations without auth → 401", test_conversations_requires_auth)
run("GET /api/tasks without auth → 401",         test_tasks_requires_auth)

# ── 4. Core API (authenticated) ──────────────────────────────────────────────
print("\n[4] Core API — authenticated")

headers, fam = _make_headers("core")


def test_status_auth():
    r = client.get("/api/status", headers=headers)
    assert r.status_code == 200, f"status={r.status_code} body={r.text[:200]}"


def test_conversations_list():
    r = client.get("/api/conversations", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "sessions" in body or "conversations" in body or isinstance(body, list), \
        f"unexpected shape: {list(body.keys())[:5]}"


def test_tasks_list():
    r = client.get("/api/tasks", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


def test_tasks_create():
    r = client.post("/api/tasks", json={"name": "Demo task", "remind_time": "08:00"},
                    headers=headers)
    # 503 is expected when TaskManager isn't started (full app not running)
    assert r.status_code in (200, 201, 503), f"status={r.status_code} body={r.text[:200]}"


def test_events_list():
    r = client.get("/api/events", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "events" in body, f"missing events key, got: {list(body.keys())[:5]}"


run("GET /api/status (auth) → 200",            test_status_auth)
run("GET /api/conversations (auth) → 200",     test_conversations_list)
run("GET /api/tasks (auth) → 200",             test_tasks_list)
run("POST /api/tasks create → 200/201",        test_tasks_create)
run("GET /api/events (auth) → 200",            test_events_list)

# ── 5. Children / Profiles ───────────────────────────────────────────────────
print("\n[5] Child profiles")

headers5, fam5 = _make_headers("child")
_created_child_id = None


def test_children_list_empty():
    r = client.get("/api/children", headers=headers5)
    assert r.status_code == 200
    body = r.json()
    assert "children" in body


def test_children_create():
    global _created_child_id
    r = client.post("/api/children",
                    json={"name": "Bé Minh", "age": 8, "grade": "3", "avatar": "👦"},
                    headers=headers5)
    assert r.status_code in (200, 201), f"status={r.status_code} body={r.text[:300]}"
    body = r.json()
    assert "ok" in body or "child_id" in body, f"unexpected body: {body}"
    # Response is {"ok": True, "child": {"child_id": ..., ...}}
    _created_child_id = (
        body.get("child_id")
        or (body.get("child") or {}).get("child_id")
    )


def test_children_list_after_create():
    r = client.get("/api/children", headers=headers5)
    assert r.status_code == 200
    children = r.json().get("children", [])
    assert any(c["name"] == "Bé Minh" for c in children), \
        f"Bé Minh not in: {[c['name'] for c in children]}"


def test_children_delete():
    if not _created_child_id:
        print("    (bỏ qua — child_id không có)")
        return
    r = client.delete(f"/api/children/{_created_child_id}", headers=headers5)
    assert r.status_code in (200, 204), f"status={r.status_code} body={r.text[:200]}"


run("GET /api/children (empty) → 200",   test_children_list_empty)
run("POST /api/children → 200/201",      test_children_create)
run("GET /api/children (has child)",     test_children_list_after_create)
run("DELETE /api/children/{id}",         test_children_delete)

# ── 6. Parent chat history (no LLM call) ────────────────────────────────────
print("\n[6] Parent chat history")

headers6, fam6 = _make_headers("pchat")


def test_parent_chat_history_empty():
    r = client.get("/api/parent-chat", headers=headers6)
    assert r.status_code == 200
    body = r.json()
    assert "chats" in body
    assert isinstance(body["chats"], list)


run("GET /api/parent-chat (empty) → 200", test_parent_chat_history_empty)

# ── 7. Video call history ────────────────────────────────────────────────────
print("\n[7] Video call history")


def test_video_history():
    r = client.get("/api/video/history", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "history" in body
    assert isinstance(body["history"], list)


run("GET /api/video/history → 200", test_video_history)

# ── 8. Education / vocabulary ────────────────────────────────────────────────
print("\n[8] Education endpoints")


def test_vocabulary_list():
    r = client.get("/api/education/vocabulary", headers=headers)
    assert r.status_code == 200


def test_story_list():
    r = client.get("/api/story/list", headers=headers)
    assert r.status_code in (200, 404)


run("GET /api/education/vocabulary → 200", test_vocabulary_list)
run("GET /api/story/list → 200/404",       test_story_list)

# ── 9. Persona ───────────────────────────────────────────────────────────────
print("\n[9] Persona endpoint")


def test_persona_get():
    r = client.get("/api/persona", headers=headers)
    assert r.status_code in (200, 404)


run("GET /api/persona → 200/404", test_persona_get)

# ── 10. Eval / LLM (can be skipped) ─────────────────────────────────────────
print("\n[10] LLM eval endpoint")

if SKIP_LLM:
    print("  SKIP  LLM tests (SKIP_LLM=1)")
else:
    def test_eval_invalid_role():
        r = client.post("/api/eval/chat",
                        json={"role": "invalid_role", "message": "Xin chào"},
                        headers=headers)
        assert r.status_code == 400, f"expected 400 got {r.status_code}"

    def test_eval_friend_role():
        print("    Đang gọi LLM (friend role)... ", end="", flush=True)
        t0 = time.time()
        r = client.post("/api/eval/chat",
                        json={
                            "role": "friend",
                            "message": "Xin chào Bi! Hôm nay trời thế nào?",
                            "child_context": {"name": "Minh", "age": 8},
                        },
                        headers=headers,
                        timeout=60)
        elapsed = time.time() - t0
        print(f"{elapsed:.1f}s")
        assert r.status_code == 200, f"status={r.status_code} body={r.text[:300]}"
        body = r.json()
        assert "response" in body, f"missing response key: {list(body.keys())}"
        reply = body["response"]
        assert isinstance(reply, str) and len(reply) > 5, f"reply too short: {reply!r}"
        print(f"    AI reply (friend): {reply[:120]}…")

    def test_eval_parent_advisor_role():
        print("    Đang gọi LLM (parent_advisor)... ", end="", flush=True)
        t0 = time.time()
        r = client.post("/api/eval/chat",
                        json={
                            "role": "parent_advisor",
                            "message": "Con tôi 7 tuổi hay xem điện thoại, làm sao hạn chế?",
                        },
                        headers=headers,
                        timeout=60)
        elapsed = time.time() - t0
        print(f"{elapsed:.1f}s")
        assert r.status_code == 200, f"status={r.status_code} body={r.text[:300]}"
        reply = r.json().get("response", "")
        assert len(reply) > 10, f"reply too short: {reply!r}"
        print(f"    AI reply (parent): {reply[:120]}…")

    run("POST /api/eval/chat invalid role → 400",       test_eval_invalid_role)
    run("POST /api/eval/chat friend role → LLM reply",  test_eval_friend_role)
    run("POST /api/eval/chat parent_advisor → reply",   test_eval_parent_advisor_role)

# ── 11. Safety filter integration ────────────────────────────────────────────
print("\n[11] Safety filter")


def test_safety_filter_import():
    from src.safety.safety_filter import SafetyFilter
    sf = SafetyFilter()
    # check(text) returns (is_safe: bool, reason: str)
    assert callable(getattr(sf, "check", None)), "SafetyFilter must have check() method"


def test_safety_filter_blocks_adult():
    from src.safety.safety_filter import SafetyFilter
    sf = SafetyFilter()
    safe, _ = sf.check("sex violence drugs adult content")
    assert safe is False, "Safety filter should block adult/violent content"


def test_safety_filter_allows_kids():
    from src.safety.safety_filter import SafetyFilter
    sf = SafetyFilter()
    safe, _ = sf.check("Hôm nay con học toán rất vui")
    assert safe is True, "Safety filter should allow normal kids content"


run("SafetyFilter importable and usable",       test_safety_filter_import)
run("SafetyFilter blocks adult content",        test_safety_filter_blocks_adult)
run("SafetyFilter allows normal kids content",  test_safety_filter_allows_kids)

# ── 12. Admin logs endpoint ───────────────────────────────────────────────────
print("\n[12] Admin logs (requires admin)")

headers_admin, fam_admin = _make_headers("admin_demo")
# Promote to admin
with _db_module.get_db_connection() as _conn:
    _conn.execute(
        "UPDATE users SET is_admin=1 WHERE username LIKE 'admin_demo%'"
    )
    _conn.commit()


def test_admin_logs_as_admin():
    r = client.get("/api/admin/logs", headers=headers_admin)
    assert r.status_code == 200, f"status={r.status_code} body={r.text[:300]}"
    body = r.json()
    assert "logs" in body
    assert isinstance(body["logs"], list)


def test_admin_logs_as_non_admin():
    r = client.get("/api/admin/logs", headers=headers)
    assert r.status_code == 403, f"expected 403 got {r.status_code}"


run("GET /api/admin/logs as admin → 200",    test_admin_logs_as_admin)
run("GET /api/admin/logs as non-admin → 403", test_admin_logs_as_non_admin)

# ── Summary ───────────────────────────────────────────────────────────────────
total = len(passed) + len(failed)
print()
print("=" * 60)
print(f"  RESULT: {len(passed)}/{total} passed, {len(failed)} failed")
if failed:
    print()
    print("  Failed tests:")
    for name, detail in failed:
        print(f"    FAIL  {name}: {detail}")
print("=" * 60)

if failed:
    sys.exit(1)
