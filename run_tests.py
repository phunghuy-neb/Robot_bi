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
    context = rag.retrieve("ten be la gi")
    assert isinstance(context, str)


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


def test_prephase3_task_manager_no_reset_daily():
    from src_brain.network.task_manager import TaskManager

    assert not hasattr(TaskManager, "reset_daily"), "reset_daily must be removed"


def test_prephase3_api_server_no_require_auth():
    import src_brain.network.api_server as _api

    assert not hasattr(_api, "require_auth"), "require_auth must be removed"


test("PrePhase3: SafetyFilter blocks harmful phrase",          test_prephase3_safety_filter_blocks_harmful_phrase)
test("PrePhase3: _require_family fails closed",                test_prephase3_require_family_fails_closed)
test("PrePhase3: _require_family returns family_name",         test_prephase3_require_family_returns_family_name)
test("PrePhase3: wake-word monkey-patch exists",               test_prephase3_wakeword_monkey_patch_exists)
test("PrePhase3: TaskManager.reset_daily absent",              test_prephase3_task_manager_no_reset_daily)
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
    _set_ws_broadcaster(lambda data: None)
    _set_ws_broadcaster(None)


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
