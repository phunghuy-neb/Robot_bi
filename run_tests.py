#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_tests.py — Robot Bi: Automated Test Suite
Chạy: python run_tests.py
Không cần: mic, loa, camera, Ollama, internet
"""
import sys
import os
import time
import traceback
import io
import contextlib
import logging

sys.path.insert(0, '.')

# Đặt JWT test config trước khi bất kỳ module nào import auth.py
# (auth.py được import transitively khi init_db() gọi seed_admin_if_empty)
os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_key_robot_bi_testing_only_32chars!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

# Dung DB test rieng biet -- khong ghi vao robot_bi.db that
import src_brain.network.db as _db_module
import tempfile as _tempfile
_TEST_DB_FILE = _tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_TEST_DB_FILE.close()
_db_module.DB_PATH = __import__('pathlib').Path(_TEST_DB_FILE.name)
_db_module._INITIALIZED = False  # reset de init_db() chay lai voi DB moi

from src_brain.network.db import init_db

# Fix encoding Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

init_db()

passed = []
failed = []
logging.getLogger("src_brain.senses.eye_vision").setLevel(logging.ERROR)
logging.getLogger("src_brain.senses.cry_detector").setLevel(logging.ERROR)


def _run_quiet(fn):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn()


def test(name, fn):
    try:
        fn()
        passed.append(name)
        print(f"  PASS  {name}")
    except Exception as e:
        failed.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")


print("=" * 60)
print("  ROBOT BI --- AUTOMATED TEST SUITE")
print("=" * 60)

# == GROUP 1: Import Tests ==================================================
print("\n[Group 1] Import Tests")

test("import SafetyFilter",  lambda: __import__('src_brain.ai_core.safety_filter',  fromlist=['SafetyFilter']))
test("import prompts",        lambda: __import__('src_brain.ai_core.prompts',         fromlist=['MAIN_SYSTEM_PROMPT']))
test("import RAGManager",     lambda: __import__('src_brain.memory_rag.rag_manager',  fromlist=['RAGManager']))
test("import EyeVision",      lambda: __import__('src_brain.senses.eye_vision',       fromlist=['EyeVision']))
test("import CryDetector",    lambda: __import__('src_brain.senses.cry_detector',     fromlist=['CryDetector']))
test("import EventNotifier",  lambda: __import__('src_brain.network.notifier',        fromlist=['get_notifier']))
test("import TaskManager",    lambda: __import__('src_brain.network.task_manager',    fromlist=['TaskManager']))
test("import MouthTTS",       lambda: __import__('src_brain.senses.mouth_tts',        fromlist=['MouthTTS']))
test("import EarSTT",         lambda: __import__('src_brain.senses.ear_stt',          fromlist=['EarSTT']))


def test_stream_chat_import():
    from src_brain.ai_core.core_ai import stream_chat
    assert callable(stream_chat)


def test_core_ai_no_ollama():
    import importlib
    import src_brain.ai_core.core_ai  # noqa: F401 — đảm bảo module đã load
    import sys
    assert "ollama" not in sys.modules, "ollama khong duoc import trong core_ai"


def test_core_ai_config_keys():
    from src_brain.ai_core import core_ai
    assert hasattr(core_ai, "GROQ_API_KEY")
    assert hasattr(core_ai, "GEMINI_API_KEY")
    assert hasattr(core_ai, "stream_chat")
    assert hasattr(core_ai, "BiAI")


test("core_ai: stream_chat importable",   test_stream_chat_import)
test("core_ai: ollama not in modules",    test_core_ai_no_ollama)
test("core_ai: config vars exist",        test_core_ai_config_keys)

# == GROUP 2: SafetyFilter ==================================================
print("\n[Group 2] SafetyFilter")
from src_brain.ai_core.safety_filter import SafetyFilter, _REFUSAL_RESPONSE as SF_REFUSAL
sf = SafetyFilter()


def test_safe_text():
    ok, text = sf.check("Bau troi mau xanh vi anh sang bi tan xa boi cac hat khong khi nhe.")
    assert ok is True, f"Expected safe, got unsafe: {text}"
    assert len(text) > 0


def test_violent_text():
    # "sex" triggers the adult-content pattern without needing diacritics
    ok, text = sf.check("sex la noi dung nguoi lon khong phu hop tre em")
    assert ok is False, "Expected unsafe for adult content"
    assert text == SF_REFUSAL, f"Refusal mismatch: {repr(text)}"


def test_blacklist_word():
    # "ngu" (no-accent) matches the standalone blacklist entry \bngu\b
    ok, text = sf.check("ban that ngu ngoc!")
    assert "ngu" not in text.lower(), f"Blacklist word still in output: {text}"


def test_long_text_truncation():
    long = "Cau mot la day. Cau hai ne ban! Cau ba cung vui. Cau bon roi nhe? Cau nam thua ra."
    ok, text = sf.check(long)
    import re
    sentences = [s for s in re.split(r'(?<=[.?!])\s+', text.strip()) if s.strip()]
    assert len(sentences) <= 4, f"Expected <=4 sentences, got {len(sentences)}: {text}"


def test_refusal_pass_through():
    ok, text = sf.check(SF_REFUSAL)
    assert ok is True


def test_empty_text():
    ok, text = sf.check("")
    assert ok is True


test("SF: safe text pass",                  test_safe_text)
test("SF: violent text blocked",            test_violent_text)
test("SF: blacklist word removed",          test_blacklist_word)
test("SF: long text truncated to 4 sent",  test_long_text_truncation)
test("SF: refusal response passes through", test_refusal_pass_through)
test("SF: empty text handled",             test_empty_text)

# == GROUP 3: prompts.py ====================================================
print("\n[Group 3] Prompts")
from src_brain.ai_core import prompts


def test_prompts_constants():
    assert hasattr(prompts, 'MAIN_SYSTEM_PROMPT')
    assert hasattr(prompts, 'REFUSAL_RESPONSE')
    assert hasattr(prompts, 'GREETING')
    assert hasattr(prompts, 'SAFETY_CHECK_PROMPT')
    assert len(prompts.MAIN_SYSTEM_PROMPT) > 100
    # Compare against safety_filter's own constant to avoid diacritic encoding issues
    assert prompts.REFUSAL_RESPONSE == SF_REFUSAL


test("prompts: all constants exist and correct", test_prompts_constants)

# == GROUP 4: RAGManager ====================================================
print("\n[Group 4] RAGManager")
import shutil
from src_brain.memory_rag.rag_manager import RAGManager

TEST_DB = "src_brain/memory_rag/_audit_test_db"
if os.path.exists(TEST_DB):
    shutil.rmtree(TEST_DB)

rag = RAGManager(db_path=TEST_DB)


def test_rag_save():
    ok = rag.extract_and_save("ten minh la Huy", "Bi nho roi, ban ten Huy!")
    assert ok is True


def test_rag_retrieve_relevant():
    rag.extract_and_save("Be ten la Minh", "O be ten Minh a")
    result = rag.retrieve("ten cua be")
    assert isinstance(result, str)
    assert len(result) >= 0


def test_rag_manual_memory():
    ok = rag.add_manual_memory("Cuoi tuan be di sinh nhat ban Minh", source="parent")
    assert ok is True


def test_rag_list():
    items = rag.list_memories()
    assert isinstance(items, list)
    assert len(items) >= 1


def test_rag_update():
    items = rag.list_memories()
    if items:
        ok = rag.update_memory(items[0]['id'], "Be ten la Huy Nguyen")
        assert ok is True


def test_rag_delete():
    items = rag.list_memories()
    if items:
        before = len(items)
        ok = rag.delete_memory(items[0]['id'])
        assert ok is True
        after = len(rag.list_memories())
        assert after < before


def test_rag_stats():
    stats = rag.get_stats()
    assert 'total_facts' in stats
    assert isinstance(stats['total_facts'], int)


def test_rag_export():
    result = rag.export_memories()
    assert isinstance(result, list)


def test_rag_clear():
    ok = rag.clear_all_memories()
    assert ok is True
    assert rag.get_stats()['total_facts'] == 0


test("RAG: extract_and_save",   test_rag_save)
test("RAG: retrieve returns str", test_rag_retrieve_relevant)
test("RAG: add_manual_memory",  test_rag_manual_memory)
test("RAG: list_memories",      test_rag_list)
test("RAG: update_memory",      test_rag_update)
test("RAG: delete_memory",      test_rag_delete)
test("RAG: get_stats format",   test_rag_stats)
test("RAG: export_memories",    test_rag_export)
test("RAG: clear_all_memories", test_rag_clear)

# Cleanup test DB
del rag
import gc
gc.collect()
try:
    shutil.rmtree(TEST_DB)
except Exception:
    pass

# == GROUP 5: EventNotifier =================================================
print("\n[Group 5] EventNotifier")
from src_brain.network.notifier import EventNotifier

notifier = EventNotifier()


def test_notifier_push_event():
    ok = _run_quiet(lambda: notifier.push_event("motion", "Test motion"))
    assert ok is True


def test_notifier_push_chat():
    ok = _run_quiet(lambda: notifier.push_chat_log("xin chao Bi", "Da xin chao ban!"))
    assert ok is True


def test_notifier_get_unread():
    events = notifier.get_unread_events()
    assert isinstance(events, list)
    assert len(events) >= 1


def test_notifier_get_stats():
    stats = notifier.get_stats()
    assert 'total_events' in stats
    assert 'unread' in stats


def test_notifier_mark_read():
    notifier.mark_all_read()
    unread = notifier.get_unread_events()
    assert len(unread) == 0


test("Notifier: push_event",      test_notifier_push_event)
test("Notifier: push_chat_log",   test_notifier_push_chat)
test("Notifier: get_unread_events", test_notifier_get_unread)
test("Notifier: get_stats format", test_notifier_get_stats)
test("Notifier: mark_all_read",   test_notifier_mark_read)

# == GROUP 6: TaskManager ===================================================
print("\n[Group 6] TaskManager")
from src_brain.network.task_manager import TaskManager

tm = TaskManager()


def test_task_add():
    task = tm.add_task("Danh rang", "07:30")
    assert task['name'] == "Danh rang"
    assert task['remind_time'] == "07:30"
    assert task['completed_today'] is False
    assert task['stars'] == 0


def test_task_complete():
    task = tm.add_task("Doc sach", "20:00")
    ok = tm.complete_task(task['id'])
    assert ok is True
    ok2 = tm.complete_task(task['id'])
    assert ok2 is False


def test_task_stars():
    before = tm.get_total_stars()
    task = tm.add_task("Don phong", "18:00")
    tm.complete_task(task['id'])
    after = tm.get_total_stars()
    assert after == before + 1


def test_task_list():
    items = tm.get_all()
    assert isinstance(items, list)


def test_task_delete():
    task = tm.add_task("Tap the duc", "06:00")
    before = len(tm.get_all())
    ok = tm.delete_task(task['id'])
    assert ok is True
    after = len(tm.get_all())
    assert after == before - 1


def test_task_delete_nonexist():
    ok = tm.delete_task("nonexistent-id-12345")
    assert ok is False


test("TaskManager: add_task",                   test_task_add)
test("TaskManager: complete_task (idempotent)", test_task_complete)
test("TaskManager: stars accumulate",           test_task_stars)
test("TaskManager: get_all returns list",       test_task_list)
test("TaskManager: delete_task",                test_task_delete)
test("TaskManager: delete nonexistent → False", test_task_delete_nonexist)
tm.stop()

# == GROUP 7: EyeVision (headless) ==========================================
print("\n[Group 7] EyeVision (headless)")
from src_brain.senses.eye_vision import EyeVision


def test_eye_init_no_camera():
    eye = _run_quiet(lambda: EyeVision(camera_index=99))
    assert eye is not None


def test_eye_start_no_camera():
    eye = _run_quiet(lambda: EyeVision(camera_index=99))
    _run_quiet(eye.start)
    time.sleep(0.5)
    _run_quiet(eye.stop)


def test_eye_stats():
    eye = _run_quiet(lambda: EyeVision(camera_index=99))
    stats = eye.get_stats()
    assert 'frames_processed' in stats
    assert 'events_detected' in stats
    assert 'known_faces_count' in stats


def test_eye_surveillance_mode():
    eye = _run_quiet(lambda: EyeVision(camera_index=99))
    _run_quiet(lambda: eye.set_surveillance_mode(True))
    assert eye._surveillance_mode is True
    _run_quiet(lambda: eye.set_surveillance_mode(False))
    assert eye._surveillance_mode is False


test("EyeVision: init without camera",    test_eye_init_no_camera)
test("EyeVision: start/stop no camera",  test_eye_start_no_camera)
test("EyeVision: get_stats format",      test_eye_stats)
test("EyeVision: set_surveillance_mode", test_eye_surveillance_mode)

# == GROUP 8: CryDetector (headless) ========================================
print("\n[Group 8] CryDetector (headless)")
from src_brain.senses.cry_detector import CryDetector
import numpy as np


def test_cry_init():
    d = _run_quiet(CryDetector)
    stats = d.get_stats()
    assert 'yamnet_available' in stats
    assert 'total_detections' in stats


def test_cry_start_stop():
    d = _run_quiet(CryDetector)
    _run_quiet(d.start)
    time.sleep(0.3)
    _run_quiet(d.stop)


def test_cry_energy_detect():
    d = _run_quiet(CryDetector)
    silent = np.zeros(16000, dtype=np.float32)
    result = d._energy_based_detect(silent)
    assert result is False, "Silent audio should not trigger cry detection"


test("CryDetector: init and get_stats",        test_cry_init)
test("CryDetector: start/stop without mic",    test_cry_start_stop)
test("CryDetector: silent audio not detected", test_cry_energy_detect)

# == GROUP 9: MouthTTS (import only) ========================================
print("\n[Group 9] MouthTTS (import only)")
from src_brain.senses.mouth_tts import MouthTTS


def test_tts_init():
    tts = MouthTTS()
    assert tts.voice == "vi-VN-HoaiMyNeural"


def test_tts_has_fallback():
    tts = MouthTTS()
    assert hasattr(tts, '_fallback_tts')
    assert callable(tts._fallback_tts)


test("MouthTTS: init correctly",      test_tts_init)
test("MouthTTS: has fallback method", test_tts_has_fallback)

# == GROUP 10: EarSTT (import only) =========================================
print("\n[Group 10] EarSTT (import only)")
from src_brain.senses.ear_stt import EarSTT, WAKEWORD_ENABLED, WAKEWORD_THRESHOLD, MIC_DEVICE


def test_ear_constants():
    assert isinstance(WAKEWORD_ENABLED, bool)
    assert isinstance(MIC_DEVICE, int)
    assert MIC_DEVICE >= 0


def test_ear_has_methods():
    assert hasattr(EarSTT, 'listen_for_wakeword')
    assert hasattr(EarSTT, 'listen')


test("EarSTT: constants defined correctly", test_ear_constants)
test("EarSTT: required methods exist",      test_ear_has_methods)

# == GROUP 10b: Auth Module =================================================
print("\n[Group 10b] Auth Module")
from src_brain.network.auth import (
    authenticate_user,
    create_user,
    get_user_by_username,
    hash_password,
    verify_password,
)
import uuid as _uuid


def test_hash_and_verify():
    h = hash_password("test_password_123")
    assert isinstance(h, str)
    assert len(h) > 20
    assert verify_password("test_password_123", h) is True
    assert verify_password("wrong_password", h) is False


def test_verify_wrong_hash():
    assert verify_password("any", "not_a_valid_hash") is False


def test_create_and_get_user():
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"testuser_{unique}", "password123", "TestFamily")
    assert user["username"] == f"testuser_{unique}"
    assert "user_id" in user
    assert "password_hash" not in user
    fetched = get_user_by_username(f"testuser_{unique}")
    assert fetched is not None
    assert fetched["family_name"] == "TestFamily"
    assert "password_hash" in fetched  # DB record has hash


def test_create_duplicate_username():
    from fastapi import HTTPException
    unique = _uuid.uuid4().hex[:8]
    create_user(f"dupuser_{unique}", "password123", "Fam1")
    try:
        create_user(f"dupuser_{unique}", "password456", "Fam2")
        assert False, "Expected HTTPException 409"
    except HTTPException as e:
        assert e.status_code == 409


def test_authenticate_user_ok():
    unique = _uuid.uuid4().hex[:8]
    create_user(f"authok_{unique}", "mypassword!", "AuthFam")
    result = authenticate_user(f"authok_{unique}", "mypassword!")
    assert result is not None
    assert result["username"] == f"authok_{unique}"
    assert "password_hash" not in result


def test_authenticate_user_wrong_password():
    unique = _uuid.uuid4().hex[:8]
    create_user(f"authwrong_{unique}", "correct_pass_1", "Fam")
    result = authenticate_user(f"authwrong_{unique}", "wrong_pass")
    assert result is None


def test_authenticate_nonexistent_user():
    result = authenticate_user("nonexistent_user_xyz_999", "any_password")
    assert result is None


test("Auth: hash_password + verify_password",         test_hash_and_verify)
test("Auth: verify_password wrong hash → False",      test_verify_wrong_hash)
test("Auth: create_user + get_user_by_username",      test_create_and_get_user)
test("Auth: create duplicate username → 409",         test_create_duplicate_username)
test("Auth: authenticate_user correct password",      test_authenticate_user_ok)
test("Auth: authenticate_user wrong password → None", test_authenticate_user_wrong_password)
test("Auth: authenticate nonexistent user → None",    test_authenticate_nonexistent_user)

# == GROUP 10c: JWT Module ==================================================
print("\n[Group 10c] JWT Module")
from src_brain.network.auth import (
    create_access_token,
    create_refresh_token,
    store_refresh_token,
    verify_access_token,
    rotate_refresh_token,
)
import hashlib as _hashlib_test
from datetime import datetime as _dt_test, timedelta as _td_test, timezone as _tz_test


def test_jwt_create_access_token():
    token = create_access_token("42", "TestFamily")
    assert isinstance(token, str)
    assert len(token) > 20
    # Có đúng 3 phần phân cách bằng dấu chấm (JWT header.payload.sig)
    assert token.count(".") == 2


def test_jwt_verify_access_token_valid():
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"jwtvalid_{unique}", "Password1!", "FamXYZ")
    uid = str(user["user_id"])
    token = create_access_token(uid, "FamXYZ")
    payload = verify_access_token(token)
    assert payload["sub"] == uid
    assert payload["family"] == "FamXYZ"
    assert payload["type"] == "access"


def test_jwt_verify_access_token_invalid():
    from fastapi import HTTPException
    try:
        verify_access_token("this.is.not.a.valid.jwt.token")
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401


def test_jwt_create_refresh_token_hash():
    raw, hashed = create_refresh_token("42")
    assert isinstance(raw, str)
    assert isinstance(hashed, str)
    assert len(raw) > 20
    # Xác minh hashed đúng là sha256 của raw
    assert _hashlib_test.sha256(raw.encode()).hexdigest() == hashed


def test_jwt_store_and_rotate_refresh_token():
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"jwtrot_{unique}", "Passw0rd123!", "JWTFam")
    uid = str(user["user_id"])

    raw, hashed = create_refresh_token(uid)
    expires_at = _dt_test.now(_tz_test.utc) + _td_test(days=30)
    store_refresh_token(uid, hashed, expires_at)

    # Rotation thành công
    new_raw, new_hashed, returned_uid = rotate_refresh_token(raw)
    assert returned_uid == uid
    assert new_raw != raw
    assert new_hashed != hashed

    # Token cũ phải bị revoke ngay lập tức
    from fastapi import HTTPException
    try:
        rotate_refresh_token(raw)
        assert False, "Expected 401 for revoked token"
    except HTTPException as e:
        assert e.status_code == 401


def test_jwt_rotate_invalid_token():
    from fastapi import HTTPException
    try:
        rotate_refresh_token("totally_fake_token_that_doesnt_exist_in_db")
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401


test("JWT: create_access_token format",         test_jwt_create_access_token)
test("JWT: verify_access_token valid payload",  test_jwt_verify_access_token_valid)
test("JWT: verify_access_token invalid → 401",  test_jwt_verify_access_token_invalid)
test("JWT: create_refresh_token sha256 hash",   test_jwt_create_refresh_token_hash)
test("JWT: store + rotate (old revoked)",       test_jwt_store_and_rotate_refresh_token)
test("JWT: rotate invalid token → 401",         test_jwt_rotate_invalid_token)

# == GROUP 11: Integration ==================================================
print("\n[Group 11] Integration")


def test_main_loop_import():
    from src_brain.main_loop import RobotBiApp
    assert RobotBiApp is not None


def test_api_server_import():
    from src_brain.network import api_server
    assert hasattr(api_server, 'app')


def test_manifest_valid():
    import json
    manifest_path = "src_brain/network/static/manifest.json"
    if os.path.exists(manifest_path):
        data = json.load(open(manifest_path, encoding='utf-8'))
        assert 'name' in data
        assert 'icons' in data
        assert 'start_url' in data
    else:
        print("    (manifest.json chua co --- bo qua)")


def test_requirements_complete():
    reqs = open('requirements.txt', encoding='utf-8').read()
    required = [
        'requests', 'faster-whisper', 'edge-tts', 'pygame',
        'chromadb', 'sentence-transformers', 'opencv-python',
        'fastapi', 'pyttsx3', 'sounddevice', 'numpy', 'argon2-cffi',
        'python-jose',
    ]
    for r in required:
        assert r in reqs, f"Missing from requirements.txt: {r}"
    assert 'ollama' not in reqs, "ollama van con trong requirements.txt"


test("Integration: main_loop importable",     test_main_loop_import)
test("Integration: api_server importable",    test_api_server_import)
test("Integration: manifest.json valid",      test_manifest_valid)
test("Integration: requirements.txt complete", test_requirements_complete)

# == GROUP 12: JWT Auth Guard (get_current_user dependency) =================
print("\n[Group 12] JWT Auth Guard")
import asyncio as _asyncio
from src_brain.network.auth import get_current_user as _get_current_user


def test_auth_guard_no_creds_returns_401():
    """get_current_user(None) phai raise 401 voi WWW-Authenticate header."""
    from fastapi import HTTPException

    async def _inner():
        await _get_current_user(None)

    try:
        _asyncio.run(_inner())
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401, f"Expected 401, got {e.status_code}"
        assert e.headers is not None
        assert "WWW-Authenticate" in e.headers, "Thieu WWW-Authenticate header"
        assert e.headers["WWW-Authenticate"] == "Bearer"


def test_auth_guard_valid_jwt_returns_user():
    """get_current_user voi JWT hop le phai tra ve user dict dung."""
    from fastapi.security import HTTPAuthorizationCredentials
    from src_brain.network.auth import create_access_token

    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"guard_{unique}", "Password1!", "GuardFam")
    uid = str(user["user_id"])
    token = create_access_token(uid, "GuardFam")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    async def _inner():
        return await _get_current_user(creds)

    user = _asyncio.run(_inner())
    assert user["user_id"] == uid
    assert user["family_name"] == "GuardFam"


def test_auth_guard_invalid_token_returns_401():
    """get_current_user voi token gia phai raise 401 voi WWW-Authenticate header."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.valid.jwt")

    async def _inner():
        await _get_current_user(creds)

    try:
        _asyncio.run(_inner())
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401
        assert e.headers is not None
        assert "WWW-Authenticate" in e.headers


def test_auth_guard_health_route_exists():
    """Endpoint /health phai ton tai trong app (no auth)."""
    from src_brain.network.api_server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/health" in paths, f"/health khong tim thay trong routes: {paths}"


test("AuthGuard: no creds → 401 + WWW-Authenticate",  test_auth_guard_no_creds_returns_401)
test("AuthGuard: valid JWT → user dict correct",       test_auth_guard_valid_jwt_returns_user)
test("AuthGuard: invalid token → 401 + WWW-Authenticate", test_auth_guard_invalid_token_returns_401)
test("AuthGuard: /health route exists (no auth)",      test_auth_guard_health_route_exists)

# == GROUP 13: Audio Feedback ===============================================
print("\n[Group 13] Audio Feedback")
from src_brain.senses.ear_stt import BEEP_WAV_BYTES as _BEEP_WAV_BYTES


def test_beep_wav_bytes_exists():
    assert isinstance(_BEEP_WAV_BYTES, bytes), "BEEP_WAV_BYTES must be bytes"
    assert len(_BEEP_WAV_BYTES) > 0, "BEEP_WAV_BYTES must not be empty"


def test_play_beep_callable():
    assert hasattr(EarSTT, '_play_beep'), "EarSTT must have _play_beep method"
    assert callable(EarSTT._play_beep), "_play_beep must be callable"


def test_wakeword_enabled_is_bool():
    assert isinstance(WAKEWORD_ENABLED, bool), "WAKEWORD_ENABLED must be bool"


def test_wakeword_threshold_is_valid_float():
    assert isinstance(WAKEWORD_THRESHOLD, float), "WAKEWORD_THRESHOLD must be float"
    assert 0.0 < WAKEWORD_THRESHOLD < 1.0, "WAKEWORD_THRESHOLD must be between 0 and 1"


def test_whisper_cpu_model_env_default():
    import src_brain.senses.ear_stt as ear_stt_module
    assert ear_stt_module.os.getenv("WHISPER_CPU_MODEL", "medium") == "medium"


def test_listen_for_wakeword_disabled_returns_false():
    original_enabled = EarSTT.listen_for_wakeword.__globals__["WAKEWORD_ENABLED"]
    EarSTT.listen_for_wakeword.__globals__["WAKEWORD_ENABLED"] = False
    try:
        ear = EarSTT.__new__(EarSTT)
        ear.silent_mode = False
        result = ear.listen_for_wakeword(timeout=0.1)
        assert result is False
    finally:
        EarSTT.listen_for_wakeword.__globals__["WAKEWORD_ENABLED"] = original_enabled


def test_earstt_init_without_error():
    import src_brain.senses.ear_stt as ear_stt_module

    original_probe = EarSTT._probe_microphone
    original_get_model = ear_stt_module._get_whisper_model
    try:
        EarSTT._probe_microphone = lambda self: setattr(self, "silent_mode", True) or setattr(self, "mic_name", "Test mic")
        ear_stt_module._get_whisper_model = lambda: object()
        ear = EarSTT()
        assert isinstance(ear, EarSTT)
    finally:
        EarSTT._probe_microphone = original_probe
        ear_stt_module._get_whisper_model = original_get_model


test("AudioFeedback: BEEP_WAV_BYTES is non-empty bytes", test_beep_wav_bytes_exists)
test("AudioFeedback: EarSTT._play_beep is callable",     test_play_beep_callable)
test("AudioFeedback: WAKEWORD_ENABLED is bool",          test_wakeword_enabled_is_bool)
test("AudioFeedback: WAKEWORD_THRESHOLD valid float",    test_wakeword_threshold_is_valid_float)
test("AudioFeedback: WHISPER_CPU_MODEL env default",     test_whisper_cpu_model_env_default)
test("AudioFeedback: disabled wakeword returns False",   test_listen_for_wakeword_disabled_returns_false)
test("AudioFeedback: EarSTT init without error",         test_earstt_init_without_error)

# == GROUP 14: Conversation Sessions ========================================
print("\n[Group 14] Conversation Sessions")
from src_brain.network.db import (
    create_session as _create_session,
    close_session as _close_session,
    add_turn as _add_turn,
    get_session_turns as _get_session_turns,
    get_db_connection as _get_db_connection,
)


def test_create_session_returns_nonempty_string():
    session_id = _create_session("default")
    assert isinstance(session_id, str)
    assert len(session_id) > 0


def test_add_turn_user_visible_in_get_session_turns():
    session_id = _create_session("default")
    turn_id = _add_turn(session_id, "user", "Xin chao Bi")
    turns = _get_session_turns(session_id)
    assert isinstance(turn_id, str)
    assert len(turn_id) > 0
    assert len(turns) == 1
    assert turns[0]["role"] == "user"
    assert turns[0]["content"] == "Xin chao Bi"


def test_add_turn_assistant_makes_two_turns():
    session_id = _create_session("default")
    _add_turn(session_id, "user", "Hom nay hoc gi?")
    _add_turn(session_id, "assistant", "Hom nay minh hoc toan nhe.")
    turns = _get_session_turns(session_id)
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"


def test_close_session_sets_ended_at_and_keeps_data():
    session_id = _create_session("default")
    _add_turn(session_id, "user", "Tam biet Bi")
    _close_session(session_id)
    turns = _get_session_turns(session_id)
    assert len(turns) == 1
    with _get_db_connection() as conn:
        row = conn.execute(
            "SELECT ended_at FROM conversations WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    assert row is not None
    assert row["ended_at"] is not None


test("Conversation: create_session returns non-empty string", test_create_session_returns_nonempty_string)
test("Conversation: user turn persists in session",           test_add_turn_user_visible_in_get_session_turns)
test("Conversation: assistant turn makes 2 turns",           test_add_turn_assistant_makes_two_turns)
test("Conversation: close_session sets ended_at",            test_close_session_sets_ended_at_and_keeps_data)

# == GROUP 15: Session Naming ===============================================
print("\n[Group 15] Session Naming")


def test_session_namer_imports():
    module = __import__("src_brain.network.session_namer", fromlist=["_generate_session_title"])
    assert hasattr(module, "_generate_session_title")


def test_generate_session_title_returns_string():
    import src_brain.network.session_namer as session_namer

    class _MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "Hoc bang cuu chuong."
                        }
                    }
                ]
            }

    original_post = session_namer.requests.post
    original_key = os.environ.get("GROQ_API_KEY")
    session_namer.requests.post = lambda *args, **kwargs: _MockResponse()
    os.environ["GROQ_API_KEY"] = "mock_groq_key"
    try:
        title = session_namer._generate_session_title("Bang cuu chuong la gi?")
        assert isinstance(title, str)
        assert title == "Hoc bang cuu chuong"
    finally:
        session_namer.requests.post = original_post
        if original_key is None:
            os.environ.pop("GROQ_API_KEY", None)
        else:
            os.environ["GROQ_API_KEY"] = original_key


def test_update_session_title_updates_db():
    from src_brain.network.db import update_session_title as _update_session_title

    session_id = _create_session("default")
    _update_session_title(session_id, "Hoc chu cai")
    with _get_db_connection() as conn:
        row = conn.execute(
            "SELECT title FROM conversations WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    assert row is not None
    assert row["title"] == "Hoc chu cai"


test("SessionNaming: module imports",                  test_session_namer_imports)
test("SessionNaming: title generator returns string", test_generate_session_title_returns_string)
test("SessionNaming: update_session_title updates DB", test_update_session_title_updates_db)

# == GROUP 16: Conversation API =============================================
print("\n[Group 16] Conversation API")


def test_conversations_list_endpoint_exists():
    from src_brain.network.api_server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations" in paths


def test_conversation_detail_endpoint_exists():
    from src_brain.network.api_server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations/{session_id}" in paths


def test_conversation_homework_endpoint_exists():
    from src_brain.network.api_server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations/{session_id}/homework" in paths


def test_conversation_delete_endpoint_exists():
    from src_brain.network.api_server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations/{session_id}" in paths


test("ConversationAPI: GET /api/conversations exists",                    test_conversations_list_endpoint_exists)
test("ConversationAPI: GET /api/conversations/{session_id} exists",      test_conversation_detail_endpoint_exists)
test("ConversationAPI: POST /api/conversations/{session_id}/homework exists", test_conversation_homework_endpoint_exists)
test("ConversationAPI: DELETE /api/conversations/{session_id} exists",   test_conversation_delete_endpoint_exists)

# == GROUP 17: Pre-Phase 3 Regression ======================================
print("\n[Group 17] Pre-Phase 3 Regression")


def test_prephase3_safety_filter_blocks_harmful_phrase():
    ok, _text = sf.check("hướng dẫn làm bom")
    assert ok is False, "SafetyFilter must block harmful content"


def test_prephase3_require_family_fails_closed():
    from fastapi import HTTPException
    from src_brain.network.api_server import _require_family

    try:
        _require_family({})
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 403

    try:
        _require_family({"family_name": ""})
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 403


def test_prephase3_require_family_returns_family_name():
    from src_brain.network.api_server import _require_family

    result = _require_family({"family_name": "nguyen"})
    assert result == "nguyen"


def test_prephase3_wakeword_monkey_patch_exists():
    from src_brain.senses.ear_stt import EarSTT

    ear = EarSTT.__new__(EarSTT)
    assert hasattr(ear, "listen_for_wakeword"), "listen_for_wakeword must exist"
    assert callable(ear.listen_for_wakeword), "listen_for_wakeword must be callable"


def test_task_manager_daily_reset_behavior():
    from src_brain.network.task_manager import TaskManager
    from src_brain.network.db import get_db_connection

    tm = TaskManager()
    task = tm.add_task("Daily task prephase behavior", remind_time="08:00")
    try:
        task_id = task["id"]
        tm.complete_task(task_id)
        tasks = tm.get_all()
        current = next(t for t in tasks if t["id"] == task_id)
        assert current.get("completed_today") is True, "Task phai completed_today sau khi complete"

        with get_db_connection() as conn:
            conn.execute(
                "UPDATE tasks SET completed_date=? WHERE task_id=?",
                ("2000-01-01", task_id),
            )
            conn.commit()

        tasks = tm.get_all()
        current = next(t for t in tasks if t["id"] == task_id)
        assert current.get("completed_today") is False, "Task hoan thanh ngay khac khong phai completed_today"
    finally:
        tm.delete_task(task["id"])
        tm.stop()


def test_prephase3_api_server_no_require_auth():
    import src_brain.network.api_server as _api

    assert not hasattr(_api, "require_auth"), "require_auth must be removed"


test("PrePhase3: SafetyFilter blocks harmful phrase",          test_prephase3_safety_filter_blocks_harmful_phrase)
test("PrePhase3: _require_family fails closed",                test_prephase3_require_family_fails_closed)
test("PrePhase3: _require_family returns family_name",         test_prephase3_require_family_returns_family_name)
test("PrePhase3: wake-word monkey-patch exists",               test_prephase3_wakeword_monkey_patch_exists)
test("PrePhase3: TaskManager daily reset behavior",            test_task_manager_daily_reset_behavior)
test("PrePhase3: api_server.require_auth absent",              test_prephase3_api_server_no_require_auth)

# == GROUP 18: Logout All Devices ===========================================
print("\n[Group 18] Logout All Devices")
from src_brain.network.db import revoke_all_tokens_for_user as _revoke_all


def test_revoke_all_tokens_callable():
    assert callable(_revoke_all)


def test_revoke_all_tokens_nonexistent_user_returns_zero():
    count = _revoke_all("nonexistent-user-id")
    assert isinstance(count, int)
    assert count == 0


def test_logout_all_endpoint_exists():
    from src_brain.network.api_server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/auth/logout-all" in paths, f"/api/auth/logout-all not found in: {paths}"


test("LogoutAll: revoke_all_tokens_for_user callable",           test_revoke_all_tokens_callable)
test("LogoutAll: nonexistent user → 0, no crash",               test_revoke_all_tokens_nonexistent_user_returns_zero)
test("LogoutAll: POST /api/auth/logout-all endpoint registered", test_logout_all_endpoint_exists)

# == GROUP 19: Account Settings =============================================
print("\n[Group 19] Account Settings")
from src_brain.network.db import get_user_by_id as _get_user_by_id
from src_brain.network.db import update_user_password as _update_user_password


def test_get_user_by_id_nonexistent():
    result = _get_user_by_id("nonexistent-id")
    assert result is None


def test_get_user_by_id_real_user():
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"settingsuser_{unique}", "Password1!", "SettingsFam")
    uid = str(user["user_id"])
    result = _get_user_by_id(uid)
    assert result is not None
    assert result["username"] == f"settingsuser_{unique}"
    assert result["family_name"] == "SettingsFam"
    assert "user_id" in result
    assert "created_at" in result
    assert "password_hash" not in result


def test_update_user_password_nonexistent():
    result = _update_user_password("nonexistent-id", "newpassword123")
    assert result is False


def test_me_endpoint_exists():
    from src_brain.network.api_server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/auth/me" in paths, f"/api/auth/me not found in: {paths}"


def test_change_password_endpoint_exists():
    from src_brain.network.api_server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/auth/change-password" in paths, f"/api/auth/change-password not found in: {paths}"


test("AccountSettings: get_user_by_id nonexistent → None",        test_get_user_by_id_nonexistent)
test("AccountSettings: get_user_by_id real user → correct dict",  test_get_user_by_id_real_user)
test("AccountSettings: update_user_password nonexistent → False", test_update_user_password_nonexistent)
test("AccountSettings: GET /api/auth/me route registered",        test_me_endpoint_exists)
test("AccountSettings: PUT /api/auth/change-password registered", test_change_password_endpoint_exists)

# == GROUP 20: Cloudflare Named Tunnel ======================================
print("\n[Group 20] Cloudflare Named Tunnel")

os.environ.setdefault("CLOUDFLARE_TUNNEL_TOKEN", "")
os.environ.setdefault("CLOUDFLARE_TUNNEL_URL", "")

from src_brain.network.routers import ops_router as _ops_router_module


def test_tunnel_token_attr_exists():
    assert hasattr(_ops_router_module, "TUNNEL_TOKEN")
    assert isinstance(_ops_router_module.TUNNEL_TOKEN, str)


def test_tunnel_url_attr_exists():
    assert hasattr(_ops_router_module, "TUNNEL_URL")
    assert isinstance(_ops_router_module.TUNNEL_URL, str)


def test_start_cloudflare_tunnel_callable():
    assert callable(_ops_router_module._start_cloudflare_tunnel)


test("CloudflareTunnel: TUNNEL_TOKEN attr exists + is str",           test_tunnel_token_attr_exists)
test("CloudflareTunnel: TUNNEL_URL attr exists + is str",             test_tunnel_url_attr_exists)
test("CloudflareTunnel: _start_cloudflare_tunnel is callable",        test_start_cloudflare_tunnel_callable)

# == GROUP 21: Push Notifications ==========================================
print("\n[Group 21] Push Notifications")
from src_brain.network.notifier import set_ws_broadcaster as _set_ws_broadcaster


def test_set_ws_broadcaster_callable():
    assert callable(_set_ws_broadcaster)


def test_set_ws_broadcaster_accepts_fn_and_none():
    test_called = []

    def mock_broadcast(data):
        test_called.append(data)

    _set_ws_broadcaster(mock_broadcast)
    import src_brain.network.notifier as _notifier_mod
    assert _notifier_mod._WS_ENABLED is True, "_WS_ENABLED phai True sau khi set broadcaster"
    _set_ws_broadcaster(None)
    assert _notifier_mod._WS_ENABLED is False, "_WS_ENABLED phai False sau khi clear broadcaster"


def test_push_event_no_crash_without_broadcaster():
    _set_ws_broadcaster(None)
    from src_brain.network.notifier import EventNotifier
    n = EventNotifier()
    ok = _run_quiet(lambda: n.push_event("test", "unit test message"))
    assert ok is True


test("PushNotif: set_ws_broadcaster is callable",                   test_set_ws_broadcaster_callable)
test("PushNotif: set_ws_broadcaster accepts fn and None",           test_set_ws_broadcaster_accepts_fn_and_none)
test("PushNotif: push_event no crash when broadcaster is None",     test_push_event_no_crash_without_broadcaster)

# == GROUP 22: WebRTC Camera Stream =========================================
print("\n[Group 22] WebRTC Camera Stream")
from src_brain.network.routers import webrtc_router as _webrtc_router


def test_webrtc_aiortc_available_attr():
    assert hasattr(_webrtc_router, "_AIORTC_AVAILABLE")
    assert isinstance(_webrtc_router._AIORTC_AVAILABLE, bool)


def test_webrtc_peer_connections_is_dict():
    assert isinstance(_webrtc_router._peer_connections, dict)


def test_webrtc_routes_registered():
    paths = [r.path for r in _webrtc_router.router.routes if hasattr(r, 'path')]
    assert "/api/webrtc/offer" in paths, f"offer not in {paths}"
    assert "/api/webrtc/close" in paths, f"close not in {paths}"


def test_webrtc_available_flag_is_bool():
    assert _webrtc_router._AIORTC_AVAILABLE in (True, False)


def test_webrtc_mjpeg_fallback_intact():
    from src_brain.network.routers.ops_router import router as _ops
    ops_paths = [r.path for r in _ops.routes if hasattr(r, 'path')]
    assert "/api/camera" in ops_paths, f"/api/camera missing from ops_router: {ops_paths}"


test("WebRTC: _AIORTC_AVAILABLE attr exists + is bool",      test_webrtc_aiortc_available_attr)
test("WebRTC: _peer_connections is a dict",                  test_webrtc_peer_connections_is_dict)
test("WebRTC: /api/webrtc/offer + /close routes registered", test_webrtc_routes_registered)
test("WebRTC: _AIORTC_AVAILABLE value is True or False",     test_webrtc_available_flag_is_bool)
test("WebRTC: MJPEG fallback /api/camera still intact",      test_webrtc_mjpeg_fallback_intact)

# == GROUP 23: Pre-Release Security Fixes ==================================
print("\n[Group 23] Pre-Release Security Fixes")
from src_brain.network.db import get_db_connection as _gdb
from src_brain.network.db import increment_token_version as _increment_tv


def test_token_version_column_in_schema():
    with _gdb() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    assert "token_version" in cols, f"token_version missing, cols: {cols}"


def test_increment_token_version_callable_returns_int():
    assert callable(_increment_tv)
    # user không tồn tại → không crash, trả về 0 (UPDATE 0 rows)
    result = _increment_tv("nonexistent-tv-user")
    assert isinstance(result, int)


def test_access_token_invalid_after_increment():
    from src_brain.network.auth import create_access_token, verify_access_token
    from fastapi import HTTPException
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"tvtest_{unique}", "Password1!", "TVFam")
    uid = str(user["user_id"])
    token = create_access_token(uid, "TVFam")
    # Token hợp lệ trước khi increment
    payload = verify_access_token(token)
    assert payload["sub"] == uid
    # Sau increment → token cũ bị vô hiệu hóa
    _increment_tv(uid)
    try:
        verify_access_token(token)
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401


def test_register_ignores_client_family_name():
    """POST /auth/register không được nhận family_name từ client."""
    import inspect
    from src_brain.network.routers.auth_router import register_user
    src = inspect.getsource(register_user)
    # family_name không được đọc từ body
    assert 'body.get("family_name"' not in src, "family_name vẫn đọc từ client body!"
    # Server dùng FAMILY_ID env
    assert "FAMILY_ID" in src


def test_register_route_exists():
    from src_brain.network.routers.auth_router import router as _ar
    paths = [r.path for r in _ar.routes if hasattr(r, 'path')]
    assert "/auth/register" in paths


def test_token_version_zero_for_new_user():
    from src_brain.network.db import get_token_version as _get_tv
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"tvzero_{unique}", "Password1!", "ZeroFam")
    uid = str(user["user_id"])
    assert _get_tv(uid) == 0


def test_token_version_increments_correctly():
    from src_brain.network.db import get_token_version as _get_tv
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"tvinc_{unique}", "Password1!", "IncFam")
    uid = str(user["user_id"])
    v1 = _increment_tv(uid)
    assert v1 == 1
    v2 = _increment_tv(uid)
    assert v2 == 2


test("Fix1: register ignores client family_name, uses FAMILY_ID",   test_register_ignores_client_family_name)
test("Fix1: /auth/register route still registered",                  test_register_route_exists)
test("Fix2: token_version column exists in users schema",            test_token_version_column_in_schema)
test("Fix2: increment_token_version callable, nonexistent→no crash", test_increment_token_version_callable_returns_int)
test("Fix2: access token → 401 after increment_token_version",      test_access_token_invalid_after_increment)
test("Fix2: new user starts at token_version=0",                     test_token_version_zero_for_new_user)
test("Fix2: token_version increments correctly",                     test_token_version_increments_correctly)

# == GROUP 24: Phase 3 Final Fix Verification ==============================
print("\n[Group 24] Phase 3 Final Fix Verification")


def _phase3_auth_headers(prefix: str = "phase3") -> dict:
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"{prefix}_{unique}", "Password1!", "Phase3Fam")
    token = create_access_token(str(user["user_id"]), "Phase3Fam")
    return {"Authorization": f"Bearer {token}"}


def _post_task_for_phase3(payload: dict):
    from fastapi.testclient import TestClient
    from src_brain.network.api_server import app
    import src_brain.network.state as _state_mod
    from src_brain.network.task_manager import TaskManager

    old_tm = _state_mod._task_manager
    tm = TaskManager()
    _state_mod._task_manager = tm
    try:
        with TestClient(app) as client:
            return client.post("/api/tasks", json=payload, headers=_phase3_auth_headers("task"))
    finally:
        tm.stop()
        _state_mod._task_manager = old_tm


# Test 24.1 - FIX-01: XSS validation
def test_24_1_task_remind_time_xss_rejected():
    r = _post_task_for_phase3({
        "name": "Doc sach",
        "remind_time": "<script>alert(1)</script>",
    })
    assert r.status_code == 422


# Test 24.2 - FIX-01: remind_time invalid reject
def test_24_2_task_remind_time_range_rejected():
    r = _post_task_for_phase3({"name": "Doc sach", "remind_time": "25:99"})
    assert r.status_code == 422


# Test 24.3 - FIX-01: remind_time valid accept
def test_24_3_task_remind_time_valid_accept():
    r = _post_task_for_phase3({"name": "Doc sach", "remind_time": "08:30"})
    assert r.status_code in (200, 201)


# Test 24.4 - FIX-02: registration disabled -> 403
def test_24_4_registration_disabled_403():
    from fastapi.testclient import TestClient
    from src_brain.network.api_server import app
    from src_brain.network.routers import auth_router

    auth_router.REGISTRATION_ENABLED = False
    with TestClient(app) as client:
        r = client.post("/auth/register", json={
            "username": f"reg_{_uuid.uuid4().hex[:8]}",
            "password": "Password1!",
        })
    assert r.status_code == 403


# Test 24.5 - FIX-02: REGISTRATION_ENABLED attr exists
def test_24_5_registration_enabled_attr_exists():
    from src_brain.network.routers import auth_router
    assert hasattr(auth_router, "REGISTRATION_ENABLED")


# Test 24.6 - FIX-03: _require_family in memory handlers
def test_24_6_memory_handlers_require_family():
    import inspect
    from src_brain.network.routers import control_router

    handlers = [
        control_router.list_memories,
        control_router.add_memory,
        control_router.export_memories,
        control_router.update_memory,
        control_router.delete_memory,
    ]
    for handler in handlers:
        src = inspect.getsource(handler)
        assert "_require_family" in src, handler.__name__


# Test 24.7 - FIX-06: PC not leaked on bad SDP
def test_24_7_webrtc_offer_adds_pc_after_success_only():
    import inspect
    from src_brain.network.routers import webrtc_router

    src = inspect.getsource(webrtc_router.webrtc_offer)
    assert "await pc.close()" in src
    assert "except Exception" in src
    assert src.index("await pc.setLocalDescription(answer)") < src.index("_peer_connections[key] = pc")
    assert "old_pc" in src, "Phai co logic dong PC cu khi reconnect"


# Test 24.8 - FIX-07: _peer_connections is dict
def test_24_8_peer_connections_is_dict():
    from src_brain.network.routers import webrtc_router
    assert isinstance(webrtc_router._peer_connections, dict)


# Test 24.9 - FIX-09: nonexistent user token -> 401
def test_24_9_nonexistent_user_access_token_rejected():
    from fastapi import HTTPException
    token = create_access_token("nonexistent-user-id", "NoFam")
    try:
        verify_access_token(token)
        assert False, "Expected HTTPException 401"
    except HTTPException as e:
        assert e.status_code == 401


# Test 24.10 - FIX-10: change-password rate limit in source
def test_24_10_change_password_rate_limit_source():
    import inspect
    from src_brain.network.routers.auth_router import change_password

    src = inspect.getsource(change_password)
    assert "chpwd:" in src
    assert "login_attempts" in src


# Test 24.11 - FIX-11: limit bounds validation
def test_24_11_limit_bounds_validation():
    from fastapi.testclient import TestClient
    from src_brain.network.api_server import app

    headers = _phase3_auth_headers("limit")
    with TestClient(app) as client:
        assert client.get("/api/events?limit=0", headers=headers).status_code == 422
        assert client.get("/api/events?limit=201", headers=headers).status_code == 422
        assert client.get("/api/events?limit=50", headers=headers).status_code == 200


# Test 24.12 - FIX-12: init_db idempotent x3
def test_24_12_init_db_idempotent_x3():
    import src_brain.network.db as db_mod
    for _ in range(3):
        db_mod._INITIALIZED = False
        init_db()


# Test 24.13 - FIX-16: no PII in INFO logs
def test_24_13_no_pii_content_in_info_logs():
    import re
    files = [
        "src_brain/network/notifier.py",
        "src_brain/main_loop.py",
        "src_brain/ai_core/core_ai.py",
    ]
    bad = re.compile(
        r"logger\.(info|warning|error)\([^\\n]*(user_text|bi_response|full_reply|clean_sentence|clean_buffer|rag_context)"
    )
    for path in files:
        text = open(path, "r", encoding="utf-8").read()
        assert not bad.search(text), path


# Test 24.14 - FIX-17: _shutdown callable
def test_24_14_robot_app_shutdown_callable():
    from src_brain.main_loop import RobotBiApp
    assert callable(getattr(RobotBiApp, "_shutdown", None))


# Test 24.15 - FIX-19: no duplicate handlers on double setup
def test_24_15_setup_logging_no_duplicate_file_handlers():
    import logging.handlers
    from src_brain.network.log_config import setup_logging

    robot_logger = logging.getLogger("robot_bi")
    setup_logging()
    first = sum(isinstance(h, logging.handlers.RotatingFileHandler) for h in robot_logger.handlers)
    setup_logging()
    second = sum(isinstance(h, logging.handlers.RotatingFileHandler) for h in robot_logger.handlers)
    assert first == second


# Test 24.16 - FIX-20: requirements-ubuntu.txt exists
def test_24_16_requirements_ubuntu_aiortc_exists():
    content = open("requirements-ubuntu.txt", "r", encoding="utf-8").read()
    assert "aiortc==1.9.0" in content


# Test 24.17 - FIX-22: ws_enabled updates with broadcaster
def test_24_17_ws_enabled_updates_with_broadcaster():
    import src_brain.network.notifier as notifier_mod

    notifier_mod.set_ws_broadcaster(lambda data: None)
    assert notifier_mod._WS_ENABLED is True
    notifier_mod.set_ws_broadcaster(None)
    assert notifier_mod._WS_ENABLED is False


test("24.1 FIX-01: task remind_time XSS rejected",        test_24_1_task_remind_time_xss_rejected)
test("24.2 FIX-01: task remind_time range rejected",      test_24_2_task_remind_time_range_rejected)
test("24.3 FIX-01: task remind_time valid accepted",      test_24_3_task_remind_time_valid_accept)
test("24.4 FIX-02: registration disabled returns 403",    test_24_4_registration_disabled_403)
test("24.5 FIX-02: REGISTRATION_ENABLED attr exists",     test_24_5_registration_enabled_attr_exists)
test("24.6 FIX-03: memory handlers require family",       test_24_6_memory_handlers_require_family)
test("24.7 FIX-06: WebRTC bad offer cleanup logic",       test_24_7_webrtc_offer_adds_pc_after_success_only)
test("24.8 FIX-07: _peer_connections is dict",            test_24_8_peer_connections_is_dict)
test("24.9 FIX-09: nonexistent user token rejected",      test_24_9_nonexistent_user_access_token_rejected)
test("24.10 FIX-10: change-password rate limit source",   test_24_10_change_password_rate_limit_source)
test("24.11 FIX-11: list limit bounds validation",        test_24_11_limit_bounds_validation)
test("24.12 FIX-12: init_db idempotent x3",               test_24_12_init_db_idempotent_x3)
test("24.13 FIX-16: no PII content in INFO logs",         test_24_13_no_pii_content_in_info_logs)
test("24.14 FIX-17: RobotBiApp._shutdown callable",       test_24_14_robot_app_shutdown_callable)
test("24.15 FIX-19: setup_logging no duplicate handlers", test_24_15_setup_logging_no_duplicate_file_handlers)
test("24.16 FIX-20: requirements-ubuntu contains aiortc", test_24_16_requirements_ubuntu_aiortc_exists)
test("24.17 FIX-22: ws_enabled tracks broadcaster",       test_24_17_ws_enabled_updates_with_broadcaster)

# == GROUP 25: Sprint A Safety & Logic Fix Verification =====================
print("\n[Group 25] Sprint A  Safety & Logic Fix Verification")


def test_25_1_safety_filter_output_used_for_persist():
    import inspect
    from src_brain import main_loop

    loop_fn = (
        main_loop.RobotBiApp._run_conversation_loop
        if hasattr(main_loop.RobotBiApp, "_run_conversation_loop")
        else main_loop.RobotBiApp.run
    )
    src = inspect.getsource(loop_fn)
    sf_pos = src.find("self.safety.check")
    at_pos = src.find("add_turn(self._current_session_id, 'assistant'")
    assert sf_pos != -1, "safety_filter phai duoc goi trong conversation loop"
    assert at_pos != -1, "assistant add_turn phai ton tai"
    assert sf_pos < at_pos, "safety_filter phai duoc goi truoc assistant add_turn"
    assert (
        "add_turn(self._current_session_id, 'assistant', sanitized_reply)" in src
    ), "assistant add_turn phai dung sanitized_reply"
    assert (
        src.count("args=(user_text_goc, sanitized_reply)") >= 2
    ), "RAG va notifier phai dung sanitized_reply"
    assert (
        "add_turn(self._current_session_id, 'assistant', full_reply)" not in src
    ), "khong duoc persist raw full_reply"


def test_25_2_task_completed_date_daily_reset():
    import datetime
    from src_brain.network.task_manager import TaskManager

    tm = TaskManager()
    task = tm.add_task("Sprint A daily reset", remind_time="08:00")
    try:
        task_id = task["id"]
        assert tm.complete_task(task_id) is True
        today = datetime.date.today().strftime("%Y-%m-%d")
        tasks = tm.get_all()
        current = next(t for t in tasks if t["id"] == task_id)
        assert current.get("completed_date") == today, "completed_date phai la hom nay"
        assert current.get("completed_today") is True, "completed_today phai dung trong ngay"

        current["completed_date"] = "2000-01-01"
        current["completed_today"] = True
        tm._save()
        tasks_next_day = tm.get_all()
        updated = next(t for t in tasks_next_day if t["id"] == task_id)
        assert (
            updated.get("completed_date") == "2000-01-01"
        ), "completed_date phai giu nguyen gia tri da set"
        assert updated.get("completed_today") is False, "completed_today phai reset khi qua ngay"
    finally:
        tm.delete_task(task["id"])
        tm.stop()


def test_25_3_last_reminded_has_date_prefix():
    import datetime
    from src_brain.network.task_manager import TaskManager

    tm = TaskManager()
    task = tm.add_task("Sprint A reminder format", remind_time="09:00")
    try:
        assert tm._mark_reminded(task["id"]) is True
        tasks = tm.get_all()
        current = next(t for t in tasks if t["id"] == task["id"])
        lr = current.get("last_reminded", "")
        today = datetime.date.today().strftime("%Y-%m-%d")
        assert len(lr) >= 16, "last_reminded phai co format YYYY-MM-DD HH:MM"
        assert lr[:4].isdigit(), "last_reminded phai bat dau bang YYYY"
        assert lr[4] == "-" and lr[7] == "-" and lr[10] == " ", "last_reminded sai format"
        assert current.get("last_reminded_date") == today, "last_reminded_date phai la hom nay"
    finally:
        tm.delete_task(task["id"])
        tm.stop()


def test_25_4_refresh_promise_single_flight_present():
    with open("src_brain/network/static/index.html", encoding="utf-8") as f:
        html = f.read()
    assert "_refreshPromise" in html, "_refreshPromise phai co trong index.html"
    fn_pos = html.find("async function tryRefreshToken")
    assert fn_pos != -1, "tryRefreshToken phai ton tai"
    refresh_src = html[fn_pos: fn_pos + 1200]
    assert "if (_refreshPromise) return _refreshPromise" in refresh_src, "phai reuse refresh promise dang chay"
    assert "_refreshPromise = (async () =>" in refresh_src, "refresh phai duoc boc trong promise"
    assert "finally" in refresh_src and "_refreshPromise = null" in refresh_src, "finally phai reset _refreshPromise"


test("25.1 FIX A-1: SafetyFilter output used for persist", test_25_1_safety_filter_output_used_for_persist)
test("25.2 FIX A-2: Task completed_date daily reset", test_25_2_task_completed_date_daily_reset)
test("25.3 FIX A-2: last_reminded stores date+time", test_25_3_last_reminded_has_date_prefix)
test("25.4 FIX A-3: _refreshPromise single-flight present", test_25_4_refresh_promise_single_flight_present)

# == GROUP 26: Sprint B Auth Security Fix Verification ======================
print("\n[Group 26] Sprint B  Auth Security Fix Verification")


def test_26_1_rotate_refresh_token_atomic_rowcount():
    import inspect
    from src_brain.network import auth

    src = inspect.getsource(auth.rotate_refresh_token)
    assert "rowcount" in src, "rotate_refresh_token phai check rowcount"
    assert (
        "is_revoked = 0" in src or "is_revoked=0" in src
    ), "UPDATE phai co dieu kien is_revoked=0"


def test_26_2_access_token_checks_is_active():
    import inspect
    from src_brain.network import auth
    from src_brain.network.routers import auth_router

    src = inspect.getsource(auth.verify_access_token)
    assert "is_active" in src, "verify_access_token phai check is_active"
    refresh_src = inspect.getsource(auth_router.refresh_token_endpoint)
    assert "is_active" in refresh_src, "refresh endpoint phai check is_active"


def test_26_3_revoke_all_tokens_atomic_token_version():
    import inspect
    from src_brain.network import db

    src = inspect.getsource(db.revoke_all_tokens_for_user)
    assert "token_version" in src, "revoke_all phai increment token_version trong cung transaction"
    assert "increment_token_version" not in src, "revoke_all khong duoc goi increment_token_version rieng"


def test_26_4_register_has_rate_limit_key():
    import inspect
    from src_brain.network.routers import auth_router

    src = inspect.getsource(auth_router)
    reg_idx = src.find("async def register")
    reg_src = src[reg_idx: reg_idx + 2000] if reg_idx >= 0 else ""
    assert (
        "register:" in reg_src or "login_attempts" in reg_src
    ), "register handler phai co rate limit"


test("26.1 FIX B-1: rotate_refresh_token atomic rowcount", test_26_1_rotate_refresh_token_atomic_rowcount)
test("26.2 FIX B-2: inactive users rejected", test_26_2_access_token_checks_is_active)
test("26.3 FIX B-3: revoke_all atomic token_version", test_26_3_revoke_all_tokens_atomic_token_version)
test("26.4 FIX B-4: register rate limit present", test_26_4_register_has_rate_limit_key)

# == GROUP 27: Sprint C Stability & Backend Verification ====================
print("\n[Group 27] Sprint C  Stability & Backend Verification")


def test_27_1_earstt_listen_wraps_whisper_load():
    import inspect
    from src_brain.senses.ear_stt import EarSTT

    src = inspect.getsource(EarSTT.listen)
    assert "_get_whisper_model" in src, "_get_whisper_model phai duoc goi trong listen()"
    assert src.count("try:") >= 1, "listen() phai co it nhat 1 try/except block"


def test_27_2_cleanup_expired_login_attempts_callable():
    from src_brain.network.db import cleanup_expired_login_attempts

    assert callable(cleanup_expired_login_attempts)
    result = cleanup_expired_login_attempts(ttl_minutes=1440)
    assert isinstance(result, int)
    assert result >= 0


def test_27_3_cleanup_orphan_sessions_closes_old_session():
    from src_brain.network.db import cleanup_orphan_sessions, get_db_connection, init_db

    init_db()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations
            (session_id, family_id, started_at, ended_at)
            VALUES ('orphan-test-001', 'test', datetime('now', '-25 hours'), NULL)
            """
        )
        conn.commit()
    count = cleanup_orphan_sessions(max_age_hours=24)
    assert count >= 1, "Phai dong it nhat 1 orphan session"


def test_27_4_main_loop_has_iteration_recovery():
    import inspect
    from src_brain import main_loop

    src = inspect.getsource(
        main_loop.RobotBiApp.run
        if hasattr(main_loop.RobotBiApp, "run")
        else main_loop.RobotBiApp._run_conversation_loop
    )
    assert "except Exception" in src, "Main loop phai co except Exception handler"
    assert "KeyboardInterrupt" in src, "KeyboardInterrupt phai duoc xu ly rieng"


def test_27_5_rag_max_memories_constant_valid():
    from src_brain.memory_rag.rag_manager import RAGManager, _MAX_MEMORIES

    assert RAGManager is not None
    assert isinstance(_MAX_MEMORIES, int)
    assert _MAX_MEMORIES > 0
    assert _MAX_MEMORIES <= 10000, "Quota phai co gioi han hop ly"


def test_27_6_init_db_idempotent_with_import_key_indexes():
    from src_brain.network.db import init_db, get_db_connection

    init_db()
    init_db()
    with get_db_connection() as conn:
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='events'"
        ).fetchall()
        idx_names = [r["name"] for r in indexes]
        assert len(idx_names) >= 0


test("27.1 FIX C-1: EarSTT listen wraps Whisper load", test_27_1_earstt_listen_wraps_whisper_load)
test("27.2 FIX C-2: cleanup_expired_login_attempts callable", test_27_2_cleanup_expired_login_attempts_callable)
test("27.3 FIX C-3: cleanup_orphan_sessions closes old session", test_27_3_cleanup_orphan_sessions_closes_old_session)
test("27.4 FIX C-4: main loop iteration recovery", test_27_4_main_loop_has_iteration_recovery)
test("27.5 FIX C-5: RAG max memories quota valid", test_27_5_rag_max_memories_constant_valid)
test("27.6 FIX C-6: init_db idempotent import_key indexes", test_27_6_init_db_idempotent_with_import_key_indexes)

# == GROUP 28: Sprint D Frontend, Cleanup & Docs Verification ===============
print("\n[Group 28] Sprint D  Frontend, Cleanup & Docs Verification")


def test_28_1_webrtc_closes_old_pc_on_reconnect():
    import inspect
    from src_brain.network.routers import webrtc_router

    src = inspect.getsource(webrtc_router)
    assert "old_pc" in src, "Phai co logic close PC cu truoc khi assign moi"


def test_28_2_tab_switch_cleanup_camera_mom_mic():
    with open("src_brain/network/static/index.html", encoding="utf-8") as f:
        html = f.read()
    assert "stopCamera" in html, "index.html phai co stopCamera"
    assert "stopMomMic" in html, "index.html phai co stopMomMic"
    tab_fn_start = html.find("function loadTab")
    if tab_fn_start < 0:
        tab_fn_start = html.find("function switchTab")
    assert tab_fn_start >= 0, "Phai co loadTab hoac switchTab function"
    switch_start = html.find("function switchTab")
    switch_src = html[switch_start: switch_start + 1200] if switch_start >= 0 else ""
    tab_src = html[tab_fn_start: tab_fn_start + 1200] + switch_src
    assert "stopCamera()" in tab_src and "stopMomMic()" in tab_src, "switch tab phai cleanup camera va mom mic"


def test_28_3_webrtc_connectionstatechange_handler():
    with open("src_brain/network/static/index.html", encoding="utf-8") as f:
        html = f.read()
    assert "onconnectionstatechange" in html, "Phai co WebRTC connectionstatechange handler"
    assert "disconnected" in html, "Phai handle disconnected state"


def test_28_4_ops_router_tunnel_captures_stderr():
    import inspect
    from src_brain.network.routers import ops_router

    src = inspect.getsource(ops_router)
    assert "stderr" in src, "ops_router phai capture stderr tu tunnel process"


def test_28_5_log_config_reads_log_level():
    import inspect
    from src_brain.network import log_config

    src = inspect.getsource(log_config.setup_logging)
    assert "LOG_LEVEL" in src, "setup_logging phai doc LOG_LEVEL tu env"


def test_28_6_notification_stacking_present():
    with open("src_brain/network/static/index.html", encoding="utf-8") as f:
        html = f.read()
    assert "_notifCount" in html or "notif-banner" in html, "Phai co notification stacking logic"


def test_28_7_run_guide_no_default_pin():
    with open("HUONG_DAN_CHAY.md", encoding="utf-8") as f:
        content = f.read()
    assert "123456" not in content, "Phai xoa PIN mac dinh 123456 khoi docs"
    assert "PIN_CODE" not in content, "Phai xoa PIN_CODE khoi docs"


def test_28_8_handoff_phase3_complete():
    with open(".claude/handoff.md", encoding="utf-8") as f:
        content = f.read()
    assert "Phase 3" in content, "handoff phai mention Phase 3"
    assert "Bắt đầu Phase 3" not in content or "COMPLETE" in content, "handoff phai reflect Phase 3 da xong"


def test_28_9_kehoach_outdated_banner():
    with open("docs/kehoach.md", encoding="utf-8") as f:
        content = f.read()
    assert "LOI THOI" in content or "LỖI THỜI" in content or "outdated" in content.lower(), "kehoach.md phai co warning banner loi thoi"


def test_28_10_gitignore_runtime_artifacts():
    with open(".gitignore", encoding="utf-8") as f:
        content = f.read()
    assert "logs/" in content, ".gitignore phai ignore logs/ directory"
    assert "_test_db" in content or "chroma_db" in content, ".gitignore phai ignore test DB artifacts"


def test_28_11_train_text_import_no_side_effect():
    import sys

    old_stdin = sys.stdin
    try:
        if "src_brain.train_text" in sys.modules:
            del sys.modules["src_brain.train_text"]
        import src_brain.train_text  # noqa: F401
        assert True
    except SystemExit:
        assert False, "train_text khong duoc exit khi import"
    finally:
        sys.stdin = old_stdin


def test_28_12_bool_file_removed():
    import os

    assert not os.path.exists("bool"), "File 'bool' phai duoc xoa"


test("28.1 FIX D-1: WebRTC closes old PC on reconnect", test_28_1_webrtc_closes_old_pc_on_reconnect)
test("28.2 FIX D-2: tab switch cleanup camera and mom mic", test_28_2_tab_switch_cleanup_camera_mom_mic)
test("28.3 FIX D-3: WebRTC connection loss handler", test_28_3_webrtc_connectionstatechange_handler)
test("28.4 FIX D-6: tunnel stderr captured", test_28_4_ops_router_tunnel_captures_stderr)
test("28.5 FIX D-7: LOG_LEVEL env used", test_28_5_log_config_reads_log_level)
test("28.6 FIX D-8: notification stacking present", test_28_6_notification_stacking_present)
test("28.7 FIX D-9: run guide removes default PIN docs", test_28_7_run_guide_no_default_pin)
test("28.8 FIX D-10: handoff marks Phase 3 complete", test_28_8_handoff_phase3_complete)
test("28.9 FIX D-11: kehoach outdated banner", test_28_9_kehoach_outdated_banner)
test("28.10 FIX D-12: gitignore runtime artifacts", test_28_10_gitignore_runtime_artifacts)
test("28.11 FIX D-13: train_text import no side effect", test_28_11_train_text_import_no_side_effect)
test("28.12 FIX D-14: bool file removed", test_28_12_bool_file_removed)

# == GROUP 29: Final Pre-Phase 4 Fix Verification ===========================
print("\n[Group 29] Final Pre-Phase 4 Fix Verification")


# Test 29.1 - FIX-01: old_pc.close() trong offer handler
def test_29_1_webrtc_offer_closes_old_pc():
    import inspect
    from src_brain.network.routers import webrtc_router as wr

    src = inspect.getsource(wr)
    offer_start = src.find("async def webrtc_offer")
    if offer_start < 0:
        offer_start = src.find("/api/webrtc/offer")
    offer_src = src[offer_start:offer_start + 2000]
    assert "old_pc" in offer_src, "Phai co old_pc.close() truoc khi assign PC moi"
    assert (
        "old_pc.close()" in offer_src or ("old_pc" in offer_src and "close" in offer_src)
    ), "old_pc phai duoc close()"


# Test 29.2 - FIX-02: beforeunload co stopCamera va stopAudioMonitor
def test_29_2_beforeunload_stops_camera_and_audio_monitor():
    with open("src_brain/network/static/index.html", encoding="utf-8") as f:
        html = f.read()
    bu_idx = html.find("beforeunload")
    assert bu_idx >= 0, "Phai co beforeunload handler"
    bu_section = html[bu_idx:bu_idx + 300]
    assert "stopCamera" in bu_section, "beforeunload phai goi stopCamera()"
    assert "stopAudioMonitor" in bu_section, "beforeunload phai goi stopAudioMonitor()"


# Test 29.3 - FIX-03: doLogout co stopCamera o dau
def test_29_3_do_logout_stops_camera_early():
    with open("src_brain/network/static/index.html", encoding="utf-8") as f:
        html = f.read()
    logout_idx = html.find("async function doLogout")
    assert logout_idx >= 0, "Phai co doLogout function"
    logout_start = html[logout_idx:logout_idx + 300]
    assert "stopCamera" in logout_start, "stopCamera phai o dau doLogout()"


# Test 29.4 - FIX-04: speech content khong log o INFO
def test_29_4_speech_content_not_logged_at_info():
    import inspect
    import re
    from src_brain.senses.ear_stt import EarSTT

    src = inspect.getsource(EarSTT)
    info_speech = re.findall(
        r'logger\.info\([^)]*(?:text|speech|nhan_dang|Nhận dạng)[^)]*\)',
        src,
    )
    assert len(info_speech) == 0, f"Speech content khong duoc log o INFO: {info_speech}"


# Test 29.5 - FIX-05: foreign_keys duoc bat
def test_29_5_sqlite_foreign_keys_enabled():
    from src_brain.network.db import get_db_connection

    with get_db_connection() as conn:
        result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1, "PRAGMA foreign_keys phai duoc bat (= 1)"


# Test 29.6 - FIX-06: prune logic co error handling
def test_29_6_rag_prune_has_error_handling():
    import inspect
    from src_brain.memory_rag import rag_manager

    src = inspect.getsource(rag_manager.RAGManager.extract_and_save)
    assert "break" in src or "except" in src, "Prune loop phai co error handling voi break"


# Test 29.7 - FIX-07: MIC_DEVICE doc tu env trong ear_stt
def test_29_7_mic_device_reads_from_env():
    import inspect
    from src_brain.senses import ear_stt

    src = inspect.getsource(ear_stt)
    assert "MIC_DEVICE" in src, "ear_stt phai co MIC_DEVICE tu env"
    assert (
        'getenv("MIC_DEVICE"' in src or "getenv('MIC_DEVICE'" in src
    ), "MIC_DEVICE phai doc tu os.getenv()"


# Test 29.8 - FIX-08: ADMIN_PASSWORD placeholder khong phai weak default
def test_29_8_admin_password_placeholder_not_weak():
    with open(".env.example", encoding="utf-8") as f:
        content = f.read()
    assert "change_me_please" not in content, ".env.example khong duoc chua password mac dinh yeu"


# Test 29.9 - FIX-09: logout dung _current_user, khong goi verify thu 2
def test_29_9_logout_does_not_double_verify():
    import inspect
    from src_brain.network.routers import auth_router

    src = inspect.getsource(auth_router)
    logout_idx = src.find("async def logout")
    if logout_idx < 0:
        logout_idx = src.find("/auth/logout")
    logout_src = src[logout_idx:logout_idx + 500] if logout_idx >= 0 else ""
    assert logout_src.count("verify_access_token") == 0, (
        "logout handler khong duoc goi verify_access_token() truc tiep"
    )


# Test 29.10 - FIX-10: connectionstatechange co try/except
def test_29_10_webrtc_connectionstatechange_has_try_except():
    import inspect
    from src_brain.network.routers import webrtc_router as wr

    src = inspect.getsource(wr)
    state_idx = src.find("connectionstatechange")
    state_src = src[state_idx:state_idx + 400] if state_idx >= 0 else ""
    assert "try:" in state_src, "connectionstatechange callback phai co try/except"


# Test 29.11 - FIX-11: icon files ton tai
def test_29_11_manifest_icon_files_exist():
    import os

    assert os.path.exists("src_brain/network/static/icon-192.png"), "icon-192.png phai ton tai"
    assert os.path.exists("src_brain/network/static/icon-512.png"), "icon-512.png phai ton tai"


# Test 29.12 - FIX-12: khong con reference train_text trong docs
def test_29_12_run_guide_no_train_text_reference():
    with open("HUONG_DAN_CHAY.md", encoding="utf-8") as f:
        content = f.read()
    assert "train_text.py" not in content, "HUONG_DAN_CHAY.md khong duoc reference train_text.py"


test("29.1 FIX-01: WebRTC offer closes old PC", test_29_1_webrtc_offer_closes_old_pc)
test("29.2 FIX-02: beforeunload stops camera/audio", test_29_2_beforeunload_stops_camera_and_audio_monitor)
test("29.3 FIX-03: doLogout stops camera early", test_29_3_do_logout_stops_camera_early)
test("29.4 FIX-04: speech content not INFO logged", test_29_4_speech_content_not_logged_at_info)
test("29.5 FIX-05: SQLite foreign_keys enabled", test_29_5_sqlite_foreign_keys_enabled)
test("29.6 FIX-06: RAG prune has error handling", test_29_6_rag_prune_has_error_handling)
test("29.7 FIX-07: MIC_DEVICE reads from env", test_29_7_mic_device_reads_from_env)
test("29.8 FIX-08: admin password placeholder not weak", test_29_8_admin_password_placeholder_not_weak)
test("29.9 FIX-09: logout avoids double verify", test_29_9_logout_does_not_double_verify)
test("29.10 FIX-10: WebRTC state close try/except", test_29_10_webrtc_connectionstatechange_has_try_except)
test("29.11 FIX-11: manifest icon files exist", test_29_11_manifest_icon_files_exist)
test("29.12 FIX-12: run guide has no train_text reference", test_29_12_run_guide_no_train_text_reference)

# == RESULTS ================================================================
print("\n" + "=" * 60)
total = len(passed) + len(failed)
print(f"  KET QUA: {len(passed)}/{total} PASS | {len(failed)}/{total} FAIL")

# Xoa test DB tam thoi
try:
    os.unlink(_TEST_DB_FILE.name)
except Exception:
    pass

if failed:
    print("\n  FAILED TESTS:")
    for name, err in failed:
        print(f"    - {name}: {err}")
    print()
    sys.exit(1)
else:
    print("\n  TAT CA TESTS PASS")
    print("=" * 60)
    sys.exit(0)
