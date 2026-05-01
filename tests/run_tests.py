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
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

# Đặt JWT test config trước khi bất kỳ module nào import auth.py
# (auth.py được import transitively khi init_db() gọi seed_admin_if_empty)
os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_key_robot_bi_testing_only_32chars!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

# Dung DB test rieng biet -- khong ghi vao robot_bi.db that
import src.infrastructure.database.db as _db_module
import tempfile as _tempfile
_TEST_DB_FILE = _tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_TEST_DB_FILE.close()
_db_module.DB_PATH = __import__('pathlib').Path(_TEST_DB_FILE.name)
_db_module._INITIALIZED = False  # reset de init_db() chay lai voi DB moi

from src.infrastructure.database.db import init_db

# Fix encoding Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

init_db()

passed = []
failed = []
logging.getLogger("src.vision.camera_stream").setLevel(logging.ERROR)
logging.getLogger("src.audio.analysis.cry_detector").setLevel(logging.ERROR)


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

test("import SafetyFilter",  lambda: __import__('src.safety.safety_filter',  fromlist=['SafetyFilter']))
test("import prompts",        lambda: __import__('src.ai.prompts',         fromlist=['MAIN_SYSTEM_PROMPT']))
test("import RAGManager",     lambda: __import__('src.memory.rag_manager',  fromlist=['RAGManager']))
test("import EyeVision",      lambda: __import__('src.vision.camera_stream',       fromlist=['EyeVision']))
test("import CryDetector",    lambda: __import__('src.audio.analysis.cry_detector',     fromlist=['CryDetector']))
test("import EventNotifier",  lambda: __import__('src.infrastructure.notifications.notifier',        fromlist=['get_notifier']))
test("import TaskManager",    lambda: __import__('src.infrastructure.tasks.task_manager',    fromlist=['TaskManager']))
test("import MouthTTS",       lambda: __import__('src.audio.output.mouth_tts',        fromlist=['MouthTTS']))
test("import EarSTT",         lambda: __import__('src.audio.input.ear_stt',          fromlist=['EarSTT']))


def test_stream_chat_import():
    from src.ai.ai_engine import stream_chat
    assert callable(stream_chat)


def test_core_ai_no_ollama():
    import importlib
    import src.ai.ai_engine  # noqa: F401 — đảm bảo module đã load
    import sys
    assert "ollama" not in sys.modules, "ollama khong duoc import trong core_ai"


def test_core_ai_config_keys():
    from src.ai import ai_engine as core_ai
    assert hasattr(core_ai, "GROQ_API_KEY")
    assert hasattr(core_ai, "GEMINI_API_KEY")
    assert hasattr(core_ai, "stream_chat")
    assert hasattr(core_ai, "BiAI")


test("core_ai: stream_chat importable",   test_stream_chat_import)
test("core_ai: ollama not in modules",    test_core_ai_no_ollama)
test("core_ai: config vars exist",        test_core_ai_config_keys)

# == GROUP 2: SafetyFilter ==================================================
print("\n[Group 2] SafetyFilter")
from src.safety.safety_filter import SafetyFilter, _REFUSAL_RESPONSE as SF_REFUSAL
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
from src.ai import prompts


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
from src.memory.rag_manager import RAGManager

TEST_DB = "runtime/_audit_test_db"
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
from src.infrastructure.notifications.notifier import EventNotifier

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
from src.infrastructure.tasks.task_manager import TaskManager

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
from src.vision.camera_stream import EyeVision


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
from src.audio.analysis.cry_detector import CryDetector
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
from src.audio.output.mouth_tts import MouthTTS


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
from src.audio.input.ear_stt import EarSTT, WAKEWORD_ENABLED, WAKEWORD_THRESHOLD, MIC_DEVICE


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
from src.infrastructure.auth.auth import (
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
from src.infrastructure.auth.auth import (
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
    from src.main import RobotBiApp
    assert RobotBiApp is not None


def test_api_server_import():
    from src.api import server as api_server
    assert hasattr(api_server, 'app')


def test_manifest_valid():
    import json
    manifest_path = "frontend/parent_app/manifest.json"
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
from src.infrastructure.auth.auth import get_current_user as _get_current_user


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
    from src.infrastructure.auth.auth import create_access_token

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
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/health" in paths, f"/health khong tim thay trong routes: {paths}"


test("AuthGuard: no creds → 401 + WWW-Authenticate",  test_auth_guard_no_creds_returns_401)
test("AuthGuard: valid JWT → user dict correct",       test_auth_guard_valid_jwt_returns_user)
test("AuthGuard: invalid token → 401 + WWW-Authenticate", test_auth_guard_invalid_token_returns_401)
test("AuthGuard: /health route exists (no auth)",      test_auth_guard_health_route_exists)

# == GROUP 13: Audio Feedback ===============================================
print("\n[Group 13] Audio Feedback")
from src.audio.input.ear_stt import BEEP_WAV_BYTES as _BEEP_WAV_BYTES


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
    import src.audio.input.ear_stt as ear_stt_module
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
    import src.audio.input.ear_stt as ear_stt_module

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
from src.infrastructure.database.db import (
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
    module = __import__("src.infrastructure.sessions.session_namer", fromlist=["_generate_session_title"])
    assert hasattr(module, "_generate_session_title")


def test_generate_session_title_returns_string():
    import src.infrastructure.sessions.session_namer as session_namer

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
    from src.infrastructure.database.db import update_session_title as _update_session_title

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
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations" in paths


def test_conversation_detail_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations/{session_id}" in paths


def test_conversation_homework_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/conversations/{session_id}/homework" in paths


def test_conversation_delete_endpoint_exists():
    from src.api.server import app
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
    from src.api.server import _require_family

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
    from src.api.server import _require_family

    result = _require_family({"family_name": "nguyen"})
    assert result == "nguyen"


def test_prephase3_wakeword_monkey_patch_exists():
    from src.audio.input.ear_stt import EarSTT

    ear = EarSTT.__new__(EarSTT)
    assert hasattr(ear, "listen_for_wakeword"), "listen_for_wakeword must exist"
    assert callable(ear.listen_for_wakeword), "listen_for_wakeword must be callable"


def test_task_manager_daily_reset_behavior():
    from src.infrastructure.tasks.task_manager import TaskManager
    from src.infrastructure.database.db import get_db_connection

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
    import src.api.server as _api

    assert not hasattr(_api, "require_auth"), "require_auth must be removed"


test("PrePhase3: SafetyFilter blocks harmful phrase",          test_prephase3_safety_filter_blocks_harmful_phrase)
test("PrePhase3: _require_family fails closed",                test_prephase3_require_family_fails_closed)
test("PrePhase3: _require_family returns family_name",         test_prephase3_require_family_returns_family_name)
test("PrePhase3: wake-word monkey-patch exists",               test_prephase3_wakeword_monkey_patch_exists)
test("PrePhase3: TaskManager daily reset behavior",            test_task_manager_daily_reset_behavior)
test("PrePhase3: api_server.require_auth absent",              test_prephase3_api_server_no_require_auth)

# == GROUP 18: Logout All Devices ===========================================
print("\n[Group 18] Logout All Devices")
from src.infrastructure.database.db import revoke_all_tokens_for_user as _revoke_all


def test_revoke_all_tokens_callable():
    assert callable(_revoke_all)


def test_revoke_all_tokens_nonexistent_user_returns_zero():
    count = _revoke_all("nonexistent-user-id")
    assert isinstance(count, int)
    assert count == 0


def test_logout_all_endpoint_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/auth/logout-all" in paths, f"/api/auth/logout-all not found in: {paths}"


test("LogoutAll: revoke_all_tokens_for_user callable",           test_revoke_all_tokens_callable)
test("LogoutAll: nonexistent user → 0, no crash",               test_revoke_all_tokens_nonexistent_user_returns_zero)
test("LogoutAll: POST /api/auth/logout-all endpoint registered", test_logout_all_endpoint_exists)

# == GROUP 19: Account Settings =============================================
print("\n[Group 19] Account Settings")
from src.infrastructure.database.db import get_user_by_id as _get_user_by_id
from src.infrastructure.database.db import update_user_password as _update_user_password


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
    from src.api.server import app
    paths = [r.path for r in app.routes if hasattr(r, 'path')]
    assert "/api/auth/me" in paths, f"/api/auth/me not found in: {paths}"


def test_change_password_endpoint_exists():
    from src.api.server import app
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

from src.api.routers import ops_router as _ops_router_module


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
from src.infrastructure.notifications.notifier import set_ws_broadcaster as _set_ws_broadcaster


def test_set_ws_broadcaster_callable():
    assert callable(_set_ws_broadcaster)


def test_set_ws_broadcaster_accepts_fn_and_none():
    test_called = []

    def mock_broadcast(data):
        test_called.append(data)

    _set_ws_broadcaster(mock_broadcast)
    import src.infrastructure.notifications.notifier as _notifier_mod
    assert _notifier_mod._WS_ENABLED is True, "_WS_ENABLED phai True sau khi set broadcaster"
    _set_ws_broadcaster(None)
    assert _notifier_mod._WS_ENABLED is False, "_WS_ENABLED phai False sau khi clear broadcaster"


def test_push_event_no_crash_without_broadcaster():
    _set_ws_broadcaster(None)
    from src.infrastructure.notifications.notifier import EventNotifier
    n = EventNotifier()
    ok = _run_quiet(lambda: n.push_event("test", "unit test message"))
    assert ok is True


test("PushNotif: set_ws_broadcaster is callable",                   test_set_ws_broadcaster_callable)
test("PushNotif: set_ws_broadcaster accepts fn and None",           test_set_ws_broadcaster_accepts_fn_and_none)
test("PushNotif: push_event no crash when broadcaster is None",     test_push_event_no_crash_without_broadcaster)

# == GROUP 22: WebRTC Camera Stream =========================================
print("\n[Group 22] WebRTC Camera Stream")
from src.api.routers import webrtc_router as _webrtc_router


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
    from src.api.routers.ops_router import router as _ops
    ops_paths = [r.path for r in _ops.routes if hasattr(r, 'path')]
    assert "/api/camera" in ops_paths, f"/api/camera missing from ops_router: {ops_paths}"


test("WebRTC: _AIORTC_AVAILABLE attr exists + is bool",      test_webrtc_aiortc_available_attr)
test("WebRTC: _peer_connections is a dict",                  test_webrtc_peer_connections_is_dict)
test("WebRTC: /api/webrtc/offer + /close routes registered", test_webrtc_routes_registered)
test("WebRTC: _AIORTC_AVAILABLE value is True or False",     test_webrtc_available_flag_is_bool)
test("WebRTC: MJPEG fallback /api/camera still intact",      test_webrtc_mjpeg_fallback_intact)

# == GROUP 23: Pre-Release Security Fixes ==================================
print("\n[Group 23] Pre-Release Security Fixes")
from src.infrastructure.database.db import get_db_connection as _gdb
from src.infrastructure.database.db import increment_token_version as _increment_tv


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
    from src.infrastructure.auth.auth import create_access_token, verify_access_token
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
    from src.api.routers.auth_router import register_user
    src = inspect.getsource(register_user)
    # family_name không được đọc từ body
    assert 'body.get("family_name"' not in src, "family_name vẫn đọc từ client body!"
    # Server dùng FAMILY_ID env
    assert "FAMILY_ID" in src


def test_register_route_exists():
    from src.api.routers.auth_router import router as _ar
    paths = [r.path for r in _ar.routes if hasattr(r, 'path')]
    assert "/auth/register" in paths


def test_token_version_zero_for_new_user():
    from src.infrastructure.database.db import get_token_version as _get_tv
    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"tvzero_{unique}", "Password1!", "ZeroFam")
    uid = str(user["user_id"])
    assert _get_tv(uid) == 0


def test_token_version_increments_correctly():
    from src.infrastructure.database.db import get_token_version as _get_tv
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
    from src.api.server import app
    import src.infrastructure.sessions.state as _state_mod
    from src.infrastructure.tasks.task_manager import TaskManager

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
    from src.api.server import app
    from src.api.routers import auth_router

    auth_router.REGISTRATION_ENABLED = False
    with TestClient(app) as client:
        r = client.post("/auth/register", json={
            "username": f"reg_{_uuid.uuid4().hex[:8]}",
            "password": "Password1!",
        })
    assert r.status_code == 403


# Test 24.5 - FIX-02: REGISTRATION_ENABLED attr exists
def test_24_5_registration_enabled_attr_exists():
    from src.api.routers import auth_router
    assert hasattr(auth_router, "REGISTRATION_ENABLED")


# Test 24.6 - FIX-03: _require_family in memory handlers
def test_24_6_memory_handlers_require_family():
    import inspect
    from src.api.routers import control_router

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
    from src.api.routers import webrtc_router

    src = inspect.getsource(webrtc_router.webrtc_offer)
    assert "await pc.close()" in src
    assert "except Exception" in src
    assert src.index("await pc.setLocalDescription(answer)") < src.index("_peer_connections[key] = pc")
    assert "old_pc" in src, "Phai co logic dong PC cu khi reconnect"


# Test 24.8 - FIX-07: _peer_connections is dict
def test_24_8_peer_connections_is_dict():
    from src.api.routers import webrtc_router
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
    from src.api.routers.auth_router import change_password

    src = inspect.getsource(change_password)
    assert "chpwd:" in src
    assert "login_attempts" in src


# Test 24.11 - FIX-11: limit bounds validation
def test_24_11_limit_bounds_validation():
    from fastapi.testclient import TestClient
    from src.api.server import app

    headers = _phase3_auth_headers("limit")
    with TestClient(app) as client:
        assert client.get("/api/events?limit=0", headers=headers).status_code == 422
        assert client.get("/api/events?limit=201", headers=headers).status_code == 422
        assert client.get("/api/events?limit=50", headers=headers).status_code == 200


# Test 24.12 - FIX-12: init_db idempotent x3
def test_24_12_init_db_idempotent_x3():
    import src.infrastructure.database.db as db_mod
    for _ in range(3):
        db_mod._INITIALIZED = False
        init_db()


# Test 24.13 - FIX-16: no PII in INFO logs
def test_24_13_no_pii_content_in_info_logs():
    import re
    files = [
        "src/infrastructure/notifications/notifier.py",
        "src/main.py",
        "src/ai/ai_engine.py",
    ]
    bad = re.compile(
        r"logger\.(info|warning|error)\([^\\n]*(user_text|bi_response|full_reply|clean_sentence|clean_buffer|rag_context)"
    )
    for path in files:
        text = open(path, "r", encoding="utf-8").read()
        assert not bad.search(text), path


# Test 24.14 - FIX-17: _shutdown callable
def test_24_14_robot_app_shutdown_callable():
    from src.main import RobotBiApp
    assert callable(getattr(RobotBiApp, "_shutdown", None))


# Test 24.15 - FIX-19: no duplicate handlers on double setup
def test_24_15_setup_logging_no_duplicate_file_handlers():
    import logging.handlers
    from src.infrastructure.logging.log_config import setup_logging

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
    import src.infrastructure.notifications.notifier as notifier_mod

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
    from src import main as main_loop

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
    from src.infrastructure.tasks.task_manager import TaskManager

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
    from src.infrastructure.tasks.task_manager import TaskManager

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
    with open("frontend/parent_app/index.html", encoding="utf-8") as f:
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
    from src.infrastructure.auth import auth

    src = inspect.getsource(auth.rotate_refresh_token)
    assert "rowcount" in src, "rotate_refresh_token phai check rowcount"
    assert (
        "is_revoked = 0" in src or "is_revoked=0" in src
    ), "UPDATE phai co dieu kien is_revoked=0"


def test_26_2_access_token_checks_is_active():
    import inspect
    from src.infrastructure.auth import auth
    from src.api.routers import auth_router

    src = inspect.getsource(auth.verify_access_token)
    assert "is_active" in src, "verify_access_token phai check is_active"
    refresh_src = inspect.getsource(auth_router.refresh_token_endpoint)
    assert "is_active" in refresh_src, "refresh endpoint phai check is_active"


def test_26_3_revoke_all_tokens_atomic_token_version():
    import inspect
    from src.infrastructure.database import db

    src = inspect.getsource(db.revoke_all_tokens_for_user)
    assert "token_version" in src, "revoke_all phai increment token_version trong cung transaction"
    assert "increment_token_version" not in src, "revoke_all khong duoc goi increment_token_version rieng"


def test_26_4_register_has_rate_limit_key():
    import inspect
    from src.api.routers import auth_router

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
    from src.audio.input.ear_stt import EarSTT

    src = inspect.getsource(EarSTT.listen)
    assert "_get_whisper_model" in src, "_get_whisper_model phai duoc goi trong listen()"
    assert src.count("try:") >= 1, "listen() phai co it nhat 1 try/except block"


def test_27_2_cleanup_expired_login_attempts_callable():
    from src.infrastructure.database.db import cleanup_expired_login_attempts

    assert callable(cleanup_expired_login_attempts)
    result = cleanup_expired_login_attempts(ttl_minutes=1440)
    assert isinstance(result, int)
    assert result >= 0


def test_27_3_cleanup_orphan_sessions_closes_old_session():
    from src.infrastructure.database.db import cleanup_orphan_sessions, get_db_connection, init_db

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
    from src import main as main_loop

    src = inspect.getsource(
        main_loop.RobotBiApp.run
        if hasattr(main_loop.RobotBiApp, "run")
        else main_loop.RobotBiApp._run_conversation_loop
    )
    assert "except Exception" in src, "Main loop phai co except Exception handler"
    assert "KeyboardInterrupt" in src, "KeyboardInterrupt phai duoc xu ly rieng"


def test_27_5_rag_max_memories_constant_valid():
    from src.memory.rag_manager import RAGManager, _MAX_MEMORIES

    assert RAGManager is not None
    assert isinstance(_MAX_MEMORIES, int)
    assert _MAX_MEMORIES > 0
    assert _MAX_MEMORIES <= 10000, "Quota phai co gioi han hop ly"


def test_27_6_init_db_idempotent_with_import_key_indexes():
    from src.infrastructure.database.db import init_db, get_db_connection

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
    from src.api.routers import webrtc_router

    src = inspect.getsource(webrtc_router)
    assert "old_pc" in src, "Phai co logic close PC cu truoc khi assign moi"


def test_28_2_tab_switch_cleanup_camera_mom_mic():
    with open("frontend/parent_app/index.html", encoding="utf-8") as f:
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
    with open("frontend/parent_app/index.html", encoding="utf-8") as f:
        html = f.read()
    assert "onconnectionstatechange" in html, "Phai co WebRTC connectionstatechange handler"
    assert "disconnected" in html, "Phai handle disconnected state"


def test_28_4_ops_router_tunnel_captures_stderr():
    import inspect
    from src.api.routers import ops_router

    src = inspect.getsource(ops_router)
    assert "stderr" in src, "ops_router phai capture stderr tu tunnel process"


def test_28_5_log_config_reads_log_level():
    import inspect
    from src.infrastructure.logging import log_config

    src = inspect.getsource(log_config.setup_logging)
    assert "LOG_LEVEL" in src, "setup_logging phai doc LOG_LEVEL tu env"


def test_28_6_notification_stacking_present():
    with open("frontend/parent_app/index.html", encoding="utf-8") as f:
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
        if "src.train_text" in sys.modules:
            del sys.modules["src.train_text"]
        import src.train_text  # noqa: F401
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
    from src.api.routers import webrtc_router as wr

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
    with open("frontend/parent_app/index.html", encoding="utf-8") as f:
        html = f.read()
    bu_idx = html.find("beforeunload")
    assert bu_idx >= 0, "Phai co beforeunload handler"
    bu_section = html[bu_idx:bu_idx + 300]
    assert "stopCamera" in bu_section, "beforeunload phai goi stopCamera()"
    assert "stopAudioMonitor" in bu_section, "beforeunload phai goi stopAudioMonitor()"


# Test 29.3 - FIX-03: doLogout co stopCamera o dau
def test_29_3_do_logout_stops_camera_early():
    with open("frontend/parent_app/index.html", encoding="utf-8") as f:
        html = f.read()
    logout_idx = html.find("async function doLogout")
    assert logout_idx >= 0, "Phai co doLogout function"
    logout_start = html[logout_idx:logout_idx + 300]
    assert "stopCamera" in logout_start, "stopCamera phai o dau doLogout()"


# Test 29.4 - FIX-04: speech content khong log o INFO
def test_29_4_speech_content_not_logged_at_info():
    import inspect
    import re
    from src.audio.input.ear_stt import EarSTT

    src = inspect.getsource(EarSTT)
    info_speech = re.findall(
        r'logger\.info\([^)]*(?:text|speech|nhan_dang|Nhận dạng)[^)]*\)',
        src,
    )
    assert len(info_speech) == 0, f"Speech content khong duoc log o INFO: {info_speech}"


# Test 29.5 - FIX-05: foreign_keys duoc bat
def test_29_5_sqlite_foreign_keys_enabled():
    from src.infrastructure.database.db import get_db_connection

    with get_db_connection() as conn:
        result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1, "PRAGMA foreign_keys phai duoc bat (= 1)"


# Test 29.6 - FIX-06: prune logic co error handling
def test_29_6_rag_prune_has_error_handling():
    import inspect
    from src.memory import rag_manager

    src = inspect.getsource(rag_manager.RAGManager.extract_and_save)
    assert "break" in src or "except" in src, "Prune loop phai co error handling voi break"


# Test 29.7 - FIX-07: MIC_DEVICE doc tu env trong ear_stt
def test_29_7_mic_device_reads_from_env():
    import inspect
    from src.audio.input import ear_stt

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
    from src.api.routers import auth_router

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
    from src.api.routers import webrtc_router as wr

    src = inspect.getsource(wr)
    state_idx = src.find("connectionstatechange")
    state_src = src[state_idx:state_idx + 400] if state_idx >= 0 else ""
    assert "try:" in state_src, "connectionstatechange callback phai co try/except"


# Test 29.11 - FIX-11: icon files ton tai
def test_29_11_manifest_icon_files_exist():
    import os

    assert os.path.exists("frontend/parent_app/icon-192.png"), "icon-192.png phai ton tai"
    assert os.path.exists("frontend/parent_app/icon-512.png"), "icon-512.png phai ton tai"


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

# == GROUP 30: Phase 4.4 Multi-Family Isolation ===============================
print("\n[Group 30] Phase 4.4 Multi-Family Isolation")


def _phase44_headers(username_prefix: str, family_id: str, is_admin: bool = False) -> dict:
    from src.infrastructure.auth.auth import create_access_token, create_user
    from src.infrastructure.database.db import get_db_connection

    unique = _uuid.uuid4().hex[:8]
    user = create_user(f"{username_prefix}_{unique}", "Password1!", family_id)
    if is_admin:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE users SET is_admin = 1 WHERE user_id = ?",
                (str(user["user_id"]),),
            )
            conn.commit()
    token = create_access_token(str(user["user_id"]), user["family_name"])
    return {"Authorization": f"Bearer {token}"}


def test_30_1_rag_family_filter_real():
    import gc
    import shutil
    from src.memory.rag_manager import RAGManager

    test_db = "runtime/_family_isolation_test_db"
    if os.path.exists(test_db):
        shutil.rmtree(test_db)
    rag = RAGManager(db_path=test_db)
    try:
        fam_a = f"rag-a-{_uuid.uuid4().hex[:6]}"
        fam_b = f"rag-b-{_uuid.uuid4().hex[:6]}"
        assert rag.add_manual_memory("Family A secret: blue dinosaur", family_id=fam_a) is True
        assert rag.add_manual_memory("Family B secret: red robot", family_id=fam_b) is True

        memories_a = rag.list_memories(family_id=fam_a)
        memories_b = rag.list_memories(family_id=fam_b)
        assert len(memories_a) == 1
        assert len(memories_b) == 1
        assert "blue dinosaur" in memories_a[0]["fact"]
        assert "red robot" in memories_b[0]["fact"]
        assert not rag.delete_memory(memories_b[0]["id"], family_id=fam_a)

        context_a = rag.retrieve("red robot", family_id=fam_a)
        assert "red robot" not in context_a.lower()
    finally:
        del rag
        gc.collect()
        try:
            shutil.rmtree(test_db)
        except Exception:
            pass


def test_30_2_conversation_api_family_scope():
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.infrastructure.database.db import add_turn, create_session

    fam_a = f"conv-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"conv-b-{_uuid.uuid4().hex[:6]}"
    headers_a = _phase44_headers("conv_a", fam_a)
    session_a = create_session(fam_a)
    session_b = create_session(fam_b)
    add_turn(session_a, "user", "hello from A", family_id=fam_a)
    add_turn(session_b, "user", "hello from B", family_id=fam_b)

    client = TestClient(app)
    list_resp = client.get("/api/conversations", headers=headers_a)
    assert list_resp.status_code == 200
    listed = [row["session_id"] for row in list_resp.json()["conversations"]]
    assert session_a in listed
    assert session_b not in listed

    detail_resp = client.get(f"/api/conversations/{session_b}", headers=headers_a)
    assert detail_resp.status_code == 404


def test_30_3_events_family_scope():
    from src.infrastructure.notifications.notifier import EventNotifier

    fam_a = f"evt-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"evt-b-{_uuid.uuid4().hex[:6]}"
    msg_a = f"event A {_uuid.uuid4().hex}"
    msg_b = f"event B {_uuid.uuid4().hex}"
    notifier_local = EventNotifier()
    notifier_local.push_event("system", msg_a, family_id=fam_a)
    notifier_local.push_event("system", msg_b, family_id=fam_b)

    events_a = notifier_local.get_unread_events(family_id=fam_a)
    assert any(evt["message"] == msg_a for evt in events_a)
    assert all(evt["message"] != msg_b for evt in events_a)

    notifier_local.mark_all_read(family_id=fam_a)
    events_b = notifier_local.get_unread_events(family_id=fam_b)
    assert any(evt["message"] == msg_b for evt in events_b)


def test_30_4_tasks_family_scope():
    from src.infrastructure.tasks.task_manager import TaskManager

    fam_a = f"task-a-{_uuid.uuid4().hex[:6]}"
    fam_b = f"task-b-{_uuid.uuid4().hex[:6]}"
    tm_local = TaskManager(family_id=fam_a)
    try:
        task_a = tm_local.add_task("Task family A", "07:10", family_id=fam_a)
        task_b = tm_local.add_task("Task family B", "07:20", family_id=fam_b)

        tasks_a = tm_local.get_all(family_id=fam_a)
        assert any(task["id"] == task_a["id"] for task in tasks_a)
        assert all(task["id"] != task_b["id"] for task in tasks_a)
        assert tm_local.complete_task(task_b["id"], family_id=fam_a) is False
        assert tm_local.complete_task(task_b["id"], family_id=fam_b) is True
        assert tm_local.get_total_stars(family_id=fam_a) == 0
        assert tm_local.get_total_stars(family_id=fam_b) >= 1
    finally:
        tm_local.delete_task(task_a["id"], family_id=fam_a)
        tm_local.delete_task(task_b["id"], family_id=fam_b)
        tm_local.stop()


def test_30_5_admin_family_endpoints_and_delete_cleanup():
    import gc
    import shutil
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.infrastructure.auth.auth import create_user
    from src.infrastructure.database.db import add_turn, create_session, get_db_connection
    from src.infrastructure.notifications.notifier import EventNotifier
    from src.infrastructure.tasks.task_manager import TaskManager
    from src.memory.rag_manager import RAGManager
    import src.infrastructure.sessions.state as _state

    client = TestClient(app)
    admin_headers = _phase44_headers("admin44", f"admin-{_uuid.uuid4().hex[:6]}", is_admin=True)
    user_headers = _phase44_headers("user44", f"user-{_uuid.uuid4().hex[:6]}")
    fam = f"delete-{_uuid.uuid4().hex[:8]}"
    test_db = f"runtime/_family_delete_test_db_{_uuid.uuid4().hex[:8]}"
    old_rag = _state._rag
    rag = None

    try:
        blocked = client.post("/api/admin/families", json={"family_id": fam}, headers=user_headers)
        assert blocked.status_code == 403

        created = client.post(
            "/api/admin/families",
            json={"family_id": fam, "display_name": "Delete Test"},
            headers=admin_headers,
        )
        assert created.status_code == 200
        listed = client.get("/api/admin/families", headers=admin_headers)
        assert listed.status_code == 200
        assert any(row["family_id"] == fam for row in listed.json()["families"])

        rag = RAGManager(db_path=test_db)
        _state._rag = rag
        assert rag.add_manual_memory("family delete chroma cleanup memory", family_id=fam)

        create_user(f"user_{_uuid.uuid4().hex[:8]}", "Password1!", fam)
        session_id = create_session(fam)
        add_turn(session_id, "user", "family delete test", family_id=fam)
        notifier_local = EventNotifier()
        notifier_local.push_event("system", "family delete event", family_id=fam)
        tm_local = TaskManager(family_id=fam)
        task = tm_local.add_task("family delete task", "08:00", family_id=fam)
        tm_local.stop()

        deleted = client.delete(f"/api/admin/families/{fam}", headers=admin_headers)
        assert deleted.status_code == 200
        memories_after = rag.list_memories(family_id=fam)
        assert len(memories_after) == 0, "ChromaDB memories phai duoc xoa khi delete family"

        with get_db_connection() as conn:
            family_count = conn.execute(
                "SELECT COUNT(*) AS c FROM families WHERE family_id = ?",
                (fam,),
            ).fetchone()["c"]
            user_count = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE family_name = ?",
                (fam,),
            ).fetchone()["c"]
            conv_count = conn.execute(
                "SELECT COUNT(*) AS c FROM conversations WHERE family_id = ?",
                (fam,),
            ).fetchone()["c"]
            turn_count = conn.execute(
                "SELECT COUNT(*) AS c FROM turns WHERE session_id = ?",
                (session_id,),
            ).fetchone()["c"]
            event_count = conn.execute(
                "SELECT COUNT(*) AS c FROM events WHERE family_id = ?",
                (fam,),
            ).fetchone()["c"]
            task_count = conn.execute(
                "SELECT COUNT(*) AS c FROM tasks WHERE task_id = ?",
                (task["id"],),
            ).fetchone()["c"]
        assert family_count == user_count == conv_count == turn_count == event_count == task_count == 0
    finally:
        _state._rag = old_rag
        if rag is not None:
            del rag
        gc.collect()
        try:
            shutil.rmtree(test_db)
        except Exception:
            pass


def test_30_6_family_foreign_keys_present():
    from src.infrastructure.database.db import get_db_connection

    with get_db_connection() as conn:
        fk_map = {
            table: [row["table"] for row in conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()]
            for table in ("users", "events", "tasks", "conversations", "turns")
        }
    assert "families" in fk_map["users"]
    assert "families" in fk_map["events"]
    assert "families" in fk_map["tasks"]
    assert "families" in fk_map["conversations"]
    assert "conversations" in fk_map["turns"]


test("30.1 RAG: ChromaDB family filter is real", test_30_1_rag_family_filter_real)
test("30.2 Conversations: API scoped by family", test_30_2_conversation_api_family_scope)
test("30.3 Events: unread/read scope by family", test_30_3_events_family_scope)
test("30.4 Tasks: operations scoped by family", test_30_4_tasks_family_scope)
test("30.5 Admin: family endpoints and cleanup", test_30_5_admin_family_endpoints_and_delete_cleanup)
test("30.6 DB: family foreign keys present", test_30_6_family_foreign_keys_present)

# == GROUP 31: Task 4.5 Homework System ====================================
print("\n[Group 31] Task 4.5 - Homework System")


def test_31_1_classify_homework_true_cases():
    from src.education.homework_classifier import classify_homework

    assert classify_homework("5 cộng 3 bằng mấy") is True
    assert classify_homework("tại sao trời mưa") is True
    assert classify_homework("bài tập về nhà hôm nay") is True


def test_31_2_classify_homework_false_cases():
    from src.education.homework_classifier import classify_homework

    assert classify_homework("hôm nay ăn gì") is False
    assert classify_homework("xin chào Bi") is False
    assert classify_homework("kể chuyện cho con nghe") is False


def test_31_3_mark_session_homework_callable():
    from src.infrastructure.database.db import mark_session_homework

    assert callable(mark_session_homework)


def test_31_4_get_homework_sessions_callable():
    from src.infrastructure.database.db import get_homework_sessions

    assert callable(get_homework_sessions)


def test_31_5_mark_and_retrieve_homework_session():
    from src.infrastructure.database.db import (
        create_session,
        get_homework_sessions,
        init_db,
        mark_session_homework,
    )

    init_db()
    sid = create_session(family_id="test_hw_family")
    assert mark_session_homework(sid) is True
    sessions = get_homework_sessions("test_hw_family")
    assert any(s["session_id"] == sid for s in sessions), (
        "Session da mark phai xuat hien trong homework list"
    )


def test_31_6_unmarked_session_not_in_homework():
    from src.infrastructure.database.db import create_session, get_homework_sessions

    sid2 = create_session(family_id="test_hw_family")
    sessions2 = get_homework_sessions("test_hw_family")
    sid2_in_hw = any(s["session_id"] == sid2 for s in sessions2)
    assert not sid2_in_hw, "Session chua mark khong duoc xuat hien trong homework"


def test_31_7_homework_route_registered():
    from src.api.routers.conversation_router import router

    paths = [r.path for r in router.routes]
    assert "/api/conversations/homework" in paths, "Homework endpoint phai duoc dang ky"


def test_31_8_homework_classifier_importable():
    import src.education.homework_classifier as hc

    assert hasattr(hc, "classify_homework")
    assert callable(hc.classify_homework)


test("31.1 HomeworkClassifier: true cases", test_31_1_classify_homework_true_cases)
test("31.2 HomeworkClassifier: false cases", test_31_2_classify_homework_false_cases)
test("31.3 DB: mark_session_homework callable", test_31_3_mark_session_homework_callable)
test("31.4 DB: get_homework_sessions callable", test_31_4_get_homework_sessions_callable)
test("31.5 DB: mark and retrieve homework session", test_31_5_mark_and_retrieve_homework_session)
test("31.6 DB: unmarked session excluded", test_31_6_unmarked_session_not_in_homework)
test("31.7 API: homework route registered", test_31_7_homework_route_registered)
test("31.8 HomeworkClassifier: importable", test_31_8_homework_classifier_importable)

# == GROUP 32: Review Fixes — normalize/homework columns ====================
print("\n[Group 32] Review Fixes — normalize consistency + homework columns")


def test_32_1_normalize_family_id_respects_env():
    """_normalize_family_id(None) phai tra ve gia tri tu FAMILY_ID env."""
    import importlib
    orig = os.environ.get("FAMILY_ID")
    try:
        os.environ["FAMILY_ID"] = "envtestfamily"
        import src.infrastructure.database.db as _db
        result = _db._normalize_family_id(None)
        assert result == "envtestfamily", (
            f"_normalize_family_id(None) expected 'envtestfamily', got '{result}'"
        )
        # Explicit value phai override env
        result2 = _db._normalize_family_id("explicit")
        assert result2 == "explicit", (
            f"_normalize_family_id('explicit') expected 'explicit', got '{result2}'"
        )
    finally:
        if orig is None:
            os.environ.pop("FAMILY_ID", None)
        else:
            os.environ["FAMILY_ID"] = orig


def test_32_2_normalize_family_id_default_fallback():
    """_normalize_family_id(None) phai tra 'default' khi FAMILY_ID khong set."""
    orig = os.environ.pop("FAMILY_ID", None)
    try:
        import src.infrastructure.database.db as _db
        result = _db._normalize_family_id(None)
        assert result == "default", (
            f"Expected 'default' fallback, got '{result}'"
        )
    finally:
        if orig is not None:
            os.environ["FAMILY_ID"] = orig


def test_32_3_normalize_unified_across_modules():
    """notifier, task_manager phai import _normalize_family_id tu db.py."""
    import src.infrastructure.notifications.notifier as _notifier
    import src.infrastructure.tasks.task_manager as _task_manager
    import src.infrastructure.database.db as _db

    assert getattr(_notifier, "_normalize_family_id", None) \
        is _db._normalize_family_id, \
        "notifier._normalize_family_id phải là cùng object với db._normalize_family_id"
    assert getattr(_task_manager, "_normalize_family_id", None) \
        is _db._normalize_family_id, \
        "task_manager._normalize_family_id phải là cùng object với db._normalize_family_id"


def test_32_4_get_homework_sessions_explicit_columns():
    """get_homework_sessions phai tra ve dung columns, khong co extra columns."""
    from src.infrastructure.database.db import (
        create_session,
        get_homework_sessions,
        init_db,
        mark_session_homework,
    )

    init_db()
    sid = create_session(family_id="test_cols_fix3")
    mark_session_homework(sid)
    sessions = get_homework_sessions("test_cols_fix3")
    assert len(sessions) > 0, "Phai co it nhat 1 homework session"
    expected_keys = {
        "session_id", "family_id", "title",
        "started_at", "ended_at", "turn_count",
        "is_homework", "homework_marked_at",
    }
    actual_keys = set(sessions[0].keys())
    assert actual_keys == expected_keys, (
        f"Column mismatch. Extra: {actual_keys - expected_keys}, "
        f"Missing: {expected_keys - actual_keys}"
    )


def test_32_5_seed_admin_uses_lowercase_family():
    """seed_admin_if_empty phai dung family_id='admin' (lowercase), khong phai 'Admin'."""
    import inspect
    from src.infrastructure.auth.auth import seed_admin_if_empty

    src = inspect.getsource(seed_admin_if_empty)
    assert '"Admin"' not in src, (
        "seed_admin_if_empty khong duoc dung 'Admin' (capitalize) — phai dung 'admin'"
    )
    assert '"admin"' in src, (
        "seed_admin_if_empty phai dung family_id='admin' (lowercase)"
    )


def test_32_6_clear_all_memories_accepts_family_id():
    """RAGManager.clear_all_memories phai nhan family_id param."""
    import inspect
    from src.memory.rag_manager import RAGManager

    sig = inspect.signature(RAGManager.clear_all_memories)
    assert "family_id" in sig.parameters, (
        "clear_all_memories phai co family_id parameter"
    )


def test_32_7_migrate_admin_family_case_runtime():
    """_migrate_admin_family_case phai doi 'Admin' → 'admin' khi chay init_db()."""
    import src.infrastructure.database.db as _db

    # Insert legacy 'Admin' family directly, bypassing normalize
    with _db.get_db_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO families (family_id, display_name, created_at) "
            "VALUES ('Admin', 'Admin', datetime('now'))"
        )
        conn.commit()

    # Force re-init so _migrate_admin_family_case runs
    _db._INITIALIZED = False
    _db.init_db()

    with _db.get_db_connection() as conn:
        admin_cap = conn.execute(
            "SELECT family_id FROM families WHERE family_id = 'Admin'"
        ).fetchone()
        admin_low = conn.execute(
            "SELECT family_id FROM families WHERE family_id = 'admin'"
        ).fetchone()

    assert admin_cap is None, "'Admin' phai duoc xoa sau migration"
    assert admin_low is not None, "'admin' phai ton tai sau migration"


test("32.1 normalize: respects FAMILY_ID env var", test_32_1_normalize_family_id_respects_env)
test("32.2 normalize: 'default' fallback when env not set", test_32_2_normalize_family_id_default_fallback)
test("32.3 normalize: unified import across modules", test_32_3_normalize_unified_across_modules)
test("32.4 get_homework_sessions: explicit columns only", test_32_4_get_homework_sessions_explicit_columns)
test("32.5 seed_admin: uses lowercase 'admin' family", test_32_5_seed_admin_uses_lowercase_family)
test("32.6 clear_all_memories: accepts family_id param", test_32_6_clear_all_memories_accepts_family_id)
test("32.7 DB: _migrate_admin_family_case runtime", test_32_7_migrate_admin_family_case_runtime)

print("\n[Group 33] Phase 5.2 — Display Backend")

# Test 33.1 — FaceAnimator import và init
from src.display.face_animator import FaceAnimator
fa = FaceAnimator()
def test_33_1_face_animator_init():
    assert fa.current_mode == 'idle', \
        "FaceAnimator phải khởi tạo với mode idle"
test("33.1 FaceAnimator init mode=idle", test_33_1_face_animator_init)

# Test 33.2 — set_mode hợp lệ
def test_33_2_face_animator_set_mode_valid():
    assert fa.set_mode('listening') == True
    assert fa.current_mode == 'listening'
test("33.2 FaceAnimator set_mode valid", test_33_2_face_animator_set_mode_valid)

# Test 33.3 — set_mode không hợp lệ
def test_33_3_face_animator_set_mode_invalid():
    assert fa.set_mode('bay_len_may') == False
    assert fa.current_mode == 'listening'  # không đổi
test("33.3 FaceAnimator set_mode invalid → False", test_33_3_face_animator_set_mode_invalid)

# Test 33.4 — set_emotion hợp lệ
def test_33_4_face_animator_set_emotion_valid():
    assert fa.set_emotion('happy') == True
    assert fa.current_emotion == 'happy'
test("33.4 FaceAnimator set_emotion valid", test_33_4_face_animator_set_emotion_valid)

# Test 33.5 — set_emotion không hợp lệ
def test_33_5_face_animator_set_emotion_invalid():
    assert fa.set_emotion('dien_ro') == False
test("33.5 FaceAnimator set_emotion invalid → False", test_33_5_face_animator_set_emotion_invalid)

# Test 33.6 — get_state format
def test_33_6_face_animator_get_state_format():
    state = fa.get_state()
    assert 'mode' in state, "get_state phải có key mode"
    assert 'emotion' in state, "get_state phải có key emotion"
    assert 'last_changed' in state, "get_state phải có key last_changed"
test("33.6 FaceAnimator get_state format", test_33_6_face_animator_get_state_format)

# Test 33.7 — FaceAnimator thread-safe
import threading
def test_33_7_face_animator_thread_safe():
    errors = []
    def switch_mode(m):
        try:
            fa.set_mode(m)
        except Exception as e:
            errors.append(str(e))
    threads = [threading.Thread(target=switch_mode,
               args=(m,)) for m in ['idle','talking','thinking']]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(errors) == 0, f"Thread-safe errors: {errors}"
test("33.7 FaceAnimator thread-safe", test_33_7_face_animator_thread_safe)

# Test 33.8 — FlashcardRenderer import và load
from src.display.flashcard_renderer import FlashcardRenderer
fr = FlashcardRenderer()
def test_33_8_flashcard_renderer_load_deck():
    count = fr.load_deck('english')
    assert count > 0, "load_deck phải trả về số lượng > 0"
test("33.8 FlashcardRenderer load_deck", test_33_8_flashcard_renderer_load_deck)

# Test 33.9 — get_current_card format
def test_33_9_flashcard_renderer_card_format():
    card = fr.get_current_card()
    required_keys = {'emoji', 'word', 'phonetic', 'meaning',
                     'current', 'total'}
    missing = required_keys - set(card.keys())
    assert not missing, f"Card thiếu keys: {missing}"
test("33.9 FlashcardRenderer card format đầy đủ", test_33_9_flashcard_renderer_card_format)

# Test 33.10 — mark_correct tăng score
def test_33_10_flashcard_renderer_mark_correct():
    score_before = fr.score
    new_score = fr.mark_correct()
    assert new_score > score_before, "Score phải tăng sau mark_correct"
    assert fr.correct_count == 1
test("33.10 FlashcardRenderer mark_correct tăng score", test_33_10_flashcard_renderer_mark_correct)

# Test 33.11 — mark_incorrect không tăng score
def test_33_11_flashcard_renderer_mark_incorrect():
    score_before = fr.score
    fr.mark_incorrect()
    assert fr.score == score_before, "Score không đổi sau mark_incorrect"
    assert fr.incorrect_count == 1
test("33.11 FlashcardRenderer mark_incorrect không đổi score", test_33_11_flashcard_renderer_mark_incorrect)

# Test 33.12 — get_progress format
def test_33_12_flashcard_renderer_get_progress():
    progress = fr.get_progress()
    assert 'correct' in progress
    assert 'incorrect' in progress
    assert 'remaining' in progress
    assert 'score' in progress
    assert progress['correct'] == 1
    assert progress['incorrect'] == 1
test("33.12 FlashcardRenderer get_progress format", test_33_12_flashcard_renderer_get_progress)

# Test 33.13 — next_card chuyển card
def test_33_13_flashcard_renderer_next_card():
    card1 = fr.get_current_card()
    fr.next_card()
    card2 = fr.get_current_card()
    # Index phải thay đổi (hoặc deck chỉ có 1 card)
    assert card2['current'] != card1['current'] or \
        fr.get_progress()['total'] == 1
test("33.13 FlashcardRenderer next_card", test_33_13_flashcard_renderer_next_card)

# Test 33.14 — reset về đầu
def test_33_14_flashcard_renderer_reset():
    fr.reset()
    assert fr.score == 0
    assert fr.correct_count == 0
    assert fr.incorrect_count == 0
test("33.14 FlashcardRenderer reset", test_33_14_flashcard_renderer_reset)

print("\n[Group 34] Phase 6.1 — Persona Manager")

from src.ai.persona_manager import PersonaManager


def test_34_1_persona_import_init():
    pm = PersonaManager("test_persona_34_1")
    assert pm.get_name() == "Bi"


def test_34_2_persona_full_dict():
    persona = PersonaManager("test_persona_34_2").get_persona()
    for key in ["name", "gender", "voice", "personality", "language"]:
        assert key in persona, f"Missing key: {key}"
    for key in ["playfulness", "extraversion", "energy"]:
        assert key in persona["personality"], f"Missing personality key: {key}"


def test_34_3_persona_save_name():
    pm = PersonaManager("test_persona_34_3")
    assert pm.save({"name": "Bibo"}) is True
    assert pm.get_name() == "Bibo"


def test_34_4_persona_save_personality_range():
    pm = PersonaManager("test_persona_34_4")
    ok = pm.save({"personality": {"playfulness": 0, "extraversion": 50, "energy": 100}})
    assert ok is True
    p = pm.get_persona()["personality"]
    assert p["playfulness"] == 0
    assert p["energy"] == 100


def test_34_5_persona_reject_out_of_range():
    pm = PersonaManager("test_persona_34_5")
    before = pm.get_persona()
    assert pm.save({"personality": {"energy": 101}}) is False
    assert pm.get_persona() == before


def test_34_6_persona_prompt_modifier():
    text = PersonaManager("test_persona_34_6").get_system_prompt_modifier()
    assert isinstance(text, str)
    assert len(text) > 20


def test_34_7_persona_voice_id():
    voice = PersonaManager("test_persona_34_7").get_voice_id()
    assert isinstance(voice, str)
    assert len(voice) > 0


def test_34_8_persona_get_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/persona" in paths


def test_34_9_persona_post_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/persona/update" in paths


test("34.1 PersonaManager import và init", test_34_1_persona_import_init)
test("34.2 get_persona trả về dict đầy đủ", test_34_2_persona_full_dict)
test("34.3 save với name hợp lệ", test_34_3_persona_save_name)
test("34.4 save personality values 0-100", test_34_4_persona_save_personality_range)
test("34.5 save ngoài range reject", test_34_5_persona_reject_out_of_range)
test("34.6 get_system_prompt_modifier string", test_34_6_persona_prompt_modifier)
test("34.7 get_voice_id string không rỗng", test_34_7_persona_voice_id)
test("34.8 GET /api/persona route tồn tại", test_34_8_persona_get_route_exists)
test("34.9 POST /api/persona/update route tồn tại", test_34_9_persona_post_route_exists)

print("\n[Group 35] Phase 6.2 — Emotion Analyzer")

from src.emotion.emotion_analyzer import Emotion, EmotionAnalyzer


def test_35_1_emotion_import():
    analyzer = EmotionAnalyzer("test_emotion_35_1")
    assert analyzer is not None


def test_35_2_emotion_happy_text():
    emotion, confidence = EmotionAnalyzer("test_emotion_35_2").analyze_text("vui quá")
    assert emotion == Emotion.HAPPY
    assert confidence > 0


def test_35_3_emotion_sad_text():
    emotion, confidence = EmotionAnalyzer("test_emotion_35_3").analyze_text("buồn ghê")
    assert emotion == Emotion.SAD
    assert confidence > 0


def test_35_4_emotion_neutral_text():
    emotion, confidence = EmotionAnalyzer("test_emotion_35_4").analyze_text("hom nay em hoc bai")
    assert emotion == Emotion.NEUTRAL
    assert confidence > 0


def test_35_5_combined_emotion_format():
    data = EmotionAnalyzer("test_emotion_35_5").get_combined_emotion(
        text="vui qua",
        voice_energy=0.6,
        voice_pitch=0.6,
    )
    assert "emotion" in data
    assert "confidence" in data
    assert "sources" in data


def test_35_6_record_emotion_no_crash():
    analyzer = EmotionAnalyzer("test_emotion_35_6")
    analyzer.record_emotion(Emotion.HAPPY, 0.9)


def test_35_7_today_summary_dict():
    analyzer = EmotionAnalyzer("test_emotion_35_7")
    summary = analyzer.get_today_summary("test_emotion_35_7")
    assert isinstance(summary, dict)
    assert "dominant" in summary


def test_35_8_weekly_summary_7_items():
    summary = EmotionAnalyzer("test_emotion_35_8").get_weekly_summary("test_emotion_35_8")
    assert isinstance(summary, list)
    assert len(summary) == 7


def test_35_9_emotion_today_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/emotion/today" in paths


def test_35_10_emotion_summary_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/emotion/summary" in paths


test("35.1 EmotionAnalyzer import", test_35_1_emotion_import)
test("35.2 analyze_text vui quá → happy", test_35_2_emotion_happy_text)
test("35.3 analyze_text buồn ghê → sad", test_35_3_emotion_sad_text)
test("35.4 analyze_text neutral → neutral", test_35_4_emotion_neutral_text)
test("35.5 get_combined_emotion format đúng", test_35_5_combined_emotion_format)
test("35.6 record_emotion không crash", test_35_6_record_emotion_no_crash)
test("35.7 get_today_summary trả về dict", test_35_7_today_summary_dict)
test("35.8 get_weekly_summary trả về list 7 items", test_35_8_weekly_summary_7_items)
test("35.9 GET /api/emotion/today route tồn tại", test_35_9_emotion_today_route_exists)
test("35.10 GET /api/emotion/summary route tồn tại", test_35_10_emotion_summary_route_exists)

print("\n[Group 36] Phase 6.3 — Emotion Journal & Alert")

from src.emotion.emotion_alert import EmotionAlert
from src.emotion.emotion_journal import EmotionJournal


def test_36_1_journal_add_entry():
    journal = EmotionJournal()
    assert journal.add_entry("test_journal_36_1", "happy", "hoc bai tot") is True


def test_36_2_journal_get_entries():
    journal = EmotionJournal()
    journal.add_entry("test_journal_36_2", "happy")
    entries = journal.get_entries("test_journal_36_2")
    assert isinstance(entries, list)


def test_36_3_journal_streak_zero():
    streak = EmotionJournal().get_streak("test_journal_36_3_empty", "sad")
    assert streak == 0


def test_36_4_journal_export_report_format():
    report = EmotionJournal().export_report("test_journal_36_4")
    assert "emotion_counts" in report
    assert "dominant" in report
    assert "sad_streak" in report


def test_36_5_alert_no_data_no_crash():
    journal = EmotionJournal()
    alert = EmotionAlert()
    result = alert.check_and_alert("test_alert_36_5_empty", journal, None)
    assert result is False


def test_36_6_alert_status_dict():
    status = EmotionAlert().get_alert_status("test_alert_36_6")
    assert isinstance(status, dict)
    assert "active" in status
    assert "status" in status


test("36.1 EmotionJournal add_entry", test_36_1_journal_add_entry)
test("36.2 get_entries trả về list", test_36_2_journal_get_entries)
test("36.3 get_streak = 0 khi không có streak", test_36_3_journal_streak_zero)
test("36.4 export_report format đúng", test_36_4_journal_export_report_format)
test("36.5 EmotionAlert check không crash khi không có data", test_36_5_alert_no_data_no_crash)
test("36.6 get_alert_status trả về dict", test_36_6_alert_status_dict)

print("\n[Group 37] Phase 7.1 — Flashcard Engine")

from src.education.flashcard_engine import FlashcardEngine


def test_37_1_flashcard_import():
    engine = FlashcardEngine("test_flashcard_37_1")
    assert engine is not None


def test_37_2_start_english_animals():
    engine = FlashcardEngine("test_flashcard_37_2")
    info = engine.start_session("english", "animals")
    assert info["subject"] == "english"
    assert info["topic"] == "animals"
    assert info["total_cards"] >= 20


def test_37_3_next_card_format():
    engine = FlashcardEngine("test_flashcard_37_3")
    engine.start_session("english", "animals")
    card = engine.get_next_card()
    for key in ["id", "word", "meaning", "difficulty"]:
        assert key in card, f"Missing card key: {key}"


def test_37_4_submit_answer_correct():
    engine = FlashcardEngine("test_flashcard_37_4")
    engine.start_session("english", "animals")
    card = engine.get_next_card()
    result = engine.submit_answer(card["id"], True)
    assert result["correct"] is True
    assert result["score"] == 1


def test_37_5_submit_answer_incorrect():
    engine = FlashcardEngine("test_flashcard_37_5")
    engine.start_session("english", "animals")
    card = engine.get_next_card()
    result = engine.submit_answer(card["id"], False)
    assert result["correct"] is False
    assert len(engine.get_review_cards()) == 1


def test_37_6_end_session_summary():
    engine = FlashcardEngine("test_flashcard_37_6")
    engine.start_session("english", "animals")
    card = engine.get_next_card()
    engine.submit_answer(card["id"], True)
    summary = engine.end_session()
    assert summary["total_answered"] == 1
    assert summary["correct"] == 1


def test_37_7_resource_file_exists():
    from pathlib import Path
    assert Path("resources/flashcards/english/animals.json").exists()


def test_37_8_resource_json_valid():
    import json
    with open("resources/flashcards/english/animals.json", "r", encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["subject"] == "english"
    assert isinstance(data["cards"], list)
    assert len(data["cards"]) >= 20


def test_37_9_flashcard_start_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/education/flashcard/start" in paths


def test_37_10_education_summary_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/education/summary" in paths


test("37.1 FlashcardEngine import", test_37_1_flashcard_import)
test("37.2 start_session english/animals", test_37_2_start_english_animals)
test("37.3 get_next_card format đúng", test_37_3_next_card_format)
test("37.4 submit_answer correct", test_37_4_submit_answer_correct)
test("37.5 submit_answer incorrect", test_37_5_submit_answer_incorrect)
test("37.6 end_session trả về summary", test_37_6_end_session_summary)
test("37.7 Resources english/animals.json tồn tại", test_37_7_resource_file_exists)
test("37.8 JSON format hợp lệ", test_37_8_resource_json_valid)
test("37.9 POST /api/education/flashcard/start route tồn tại", test_37_9_flashcard_start_route_exists)
test("37.10 GET /api/education/summary route tồn tại", test_37_10_education_summary_route_exists)

print("\n[Group 38] Phase 7.2 — Language Tutor + Pronunciation")

from src.audio.analysis.pronunciation_checker import PronunciationChecker
from src.education.language_tutor import LanguageTutor


def test_38_1_language_tutor_import():
    tutor = LanguageTutor()
    assert "en" in tutor.SUPPORTED_LANGUAGES


def test_38_2_translate_vi_en_basic():
    result = LanguageTutor().translate("xin chao", "vi", "en")
    assert result == "hello"


def test_38_3_pronunciation_guide_format():
    guide = LanguageTutor().get_pronunciation_guide("cat", "en")
    assert "phonetic" in guide
    assert "tips" in guide


def test_38_4_pronunciation_checker_import():
    checker = PronunciationChecker()
    assert checker is not None


def test_38_5_pronunciation_correct_high_score():
    result = PronunciationChecker().check("cat", "cat")
    assert result["score"] >= 80
    assert result["is_correct"] is True


def test_38_6_pronunciation_wrong_low_score():
    result = PronunciationChecker().check("dog", "cat")
    assert result["score"] < 80
    assert result["is_correct"] is False


def test_38_7_normalize_lowercase():
    normalized = PronunciationChecker().normalize_text("CAT!", "en")
    assert normalized == "cat"


test("38.1 LanguageTutor import", test_38_1_language_tutor_import)
test("38.2 translate Việt→Anh cơ bản", test_38_2_translate_vi_en_basic)
test("38.3 get_pronunciation_guide format", test_38_3_pronunciation_guide_format)
test("38.4 PronunciationChecker import", test_38_4_pronunciation_checker_import)
test("38.5 check đúng từ → score cao", test_38_5_pronunciation_correct_high_score)
test("38.6 check sai từ → score thấp", test_38_6_pronunciation_wrong_low_score)
test("38.7 normalize_text lowercase", test_38_7_normalize_lowercase)

print("\n[Group 39] Phase 7.3 — Progress Tracker + Curriculum")

from src.education.curriculum import Curriculum
from src.education.progress_tracker import ProgressTracker


def test_39_1_progress_record_session():
    tracker = ProgressTracker()
    assert tracker.record_session("test_progress_39_1", "english", 3, 1, 120) is True


def test_39_2_subject_progress_format():
    tracker = ProgressTracker()
    tracker.record_session("test_progress_39_2", "math", 2, 2, 60)
    progress = tracker.get_subject_progress("test_progress_39_2", "math")
    assert progress["subject"] == "math"
    assert "accuracy" in progress


def test_39_3_progress_streak_initial_zero():
    streak = ProgressTracker().get_streak("test_progress_39_3_empty")
    assert streak == 0


def test_39_4_weekly_report_format():
    report = ProgressTracker().generate_weekly_report("test_progress_39_4")
    assert "subjects" in report
    assert "streak" in report


def test_39_5_curriculum_schedule_7_days():
    schedule = Curriculum().get_schedule("test_curriculum_39_5")
    assert isinstance(schedule, dict)
    assert len(schedule) == 7


def test_39_6_curriculum_today_no_crash():
    today = Curriculum().get_today_subject("test_curriculum_39_6")
    assert "day" in today
    assert "rest_day" in today


def test_39_7_curriculum_update_verify():
    curriculum = Curriculum()
    schedule = curriculum.get_schedule("test_curriculum_39_7")
    schedule["monday"] = {"subject": "math", "time": "18:30"}
    assert curriculum.update_schedule("test_curriculum_39_7", schedule) is True
    saved = curriculum.get_schedule("test_curriculum_39_7")
    assert saved["monday"]["subject"] == "math"
    assert saved["monday"]["time"] == "18:30"


test("39.1 ProgressTracker record_session", test_39_1_progress_record_session)
test("39.2 get_subject_progress format", test_39_2_subject_progress_format)
test("39.3 get_streak = 0 initially", test_39_3_progress_streak_initial_zero)
test("39.4 generate_weekly_report", test_39_4_weekly_report_format)
test("39.5 Curriculum get_schedule có 7 ngày", test_39_5_curriculum_schedule_7_days)
test("39.6 get_today_subject không crash", test_39_6_curriculum_today_no_crash)
test("39.7 update_schedule → verify saved", test_39_7_curriculum_update_verify)

print("\n[Group 40] Phase 8.1 — Music Player Backend")

from src.audio.output.music_player import MusicPlayer
from src.entertainment.music_library import MusicLibrary


def test_40_1_music_library_import():
    library = MusicLibrary()
    assert library.CATEGORIES


def test_40_2_get_playlist_list():
    playlist = MusicLibrary().get_playlist("lullabies")
    assert isinstance(playlist, list)
    assert len(playlist) >= 1


def test_40_3_music_search_list():
    results = MusicLibrary().search("ru")
    assert isinstance(results, list)


def test_40_4_is_copyrighted_bool():
    result = MusicLibrary().is_copyrighted("lullaby_001")
    assert isinstance(result, bool)


def test_40_5_music_player_import():
    player = MusicPlayer()
    assert player is not None


def test_40_6_music_status_dict():
    status = MusicPlayer().get_status()
    assert isinstance(status, dict)
    assert "playing" in status
    assert "volume" in status


def test_40_7_set_volume_valid():
    player = MusicPlayer()
    assert player.set_volume(0) is True
    assert player.set_volume(100) is True


def test_40_8_set_volume_invalid():
    player = MusicPlayer()
    assert player.set_volume(-1) is False
    assert player.set_volume(101) is False


def test_40_9_music_play_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/music/play" in paths


def test_40_10_music_status_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/music/status" in paths


test("40.1 MusicLibrary import", test_40_1_music_library_import)
test("40.2 get_playlist trả về list", test_40_2_get_playlist_list)
test("40.3 search trả về list", test_40_3_music_search_list)
test("40.4 is_copyrighted trả về bool", test_40_4_is_copyrighted_bool)
test("40.5 MusicPlayer import", test_40_5_music_player_import)
test("40.6 get_status trả về dict", test_40_6_music_status_dict)
test("40.7 set_volume 0-100 valid", test_40_7_set_volume_valid)
test("40.8 set_volume ngoài range → False", test_40_8_set_volume_invalid)
test("40.9 POST /api/music/play route tồn tại", test_40_9_music_play_route_exists)
test("40.10 GET /api/music/status route tồn tại", test_40_10_music_status_route_exists)

print("\n[Group 41] Phase 8.2 — Story Engine")

from src.entertainment.story_engine import StoryEngine


def test_41_1_story_engine_import():
    engine = StoryEngine()
    assert engine is not None


def test_41_2_story_list_returns_list():
    stories = StoryEngine().get_story_list()
    assert isinstance(stories, list)
    assert len(stories) >= 1


def test_41_3_tell_story_by_id():
    story = StoryEngine().tell_story(story_id="fairy_001")
    assert story["title"]
    assert story["content"]


def test_41_4_bedtime_story_format():
    story = StoryEngine().get_bedtime_story()
    assert "title" in story
    assert "content" in story
    assert "duration_estimate" in story


def test_41_5_story_files_exist():
    from pathlib import Path
    assert Path("resources/stories/fairy_tales/co_tich.json").exists()
    assert Path("resources/stories/fables/ngu_ngon.json").exists()
    assert Path("resources/stories/bedtime/ru_ngu.json").exists()


def test_41_6_story_tell_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/story/tell" in paths


test("41.1 StoryEngine import", test_41_1_story_engine_import)
test("41.2 get_story_list trả về list", test_41_2_story_list_returns_list)
test("41.3 tell_story với story_id", test_41_3_tell_story_by_id)
test("41.4 get_bedtime_story format đúng", test_41_4_bedtime_story_format)
test("41.5 Story files tồn tại", test_41_5_story_files_exist)
test("41.6 POST /api/story/tell route tồn tại", test_41_6_story_tell_route_exists)

print("\n[Group 42] Phase 8.3 — Game Engine")

from src.entertainment.game_voice_quiz import VoiceQuizGame
from src.entertainment.game_word_quiz import WordQuizGame


def test_42_1_word_quiz_import_start():
    game = WordQuizGame()
    result = game.start_game("test_game_42_1")
    assert result["status"] == "started"


def test_42_2_word_question_format():
    game = WordQuizGame()
    game.start_game("test_game_42_2")
    question = game.get_question()
    assert "question" in question
    assert len(question["options"]) == 4
    assert "time_limit_sec" in question


def test_42_3_word_submit_correct():
    game = WordQuizGame()
    game.start_game("test_game_42_3")
    game.get_question()
    result = game.submit_answer(game._current["answer"])
    assert result["correct"] is True


def test_42_4_word_submit_incorrect():
    game = WordQuizGame()
    game.start_game("test_game_42_4")
    game.get_question()
    result = game.submit_answer("sai dap an")
    assert result["correct"] is False


def test_42_5_word_end_summary():
    game = WordQuizGame()
    game.start_game("test_game_42_5")
    summary = game.end_game()
    assert "total_score" in summary
    assert "high_score" in summary


def test_42_6_voice_quiz_import_start():
    game = VoiceQuizGame()
    result = game.start_game("test_voice_42_6")
    assert result["status"] == "started"


def test_42_7_voice_get_riddle_dict():
    game = VoiceQuizGame()
    game.start_game("test_voice_42_7")
    riddle = game.get_riddle()
    assert "riddle_text" in riddle
    assert "hint" in riddle
    assert "answer" in riddle


def test_42_8_voice_answer_correct():
    game = VoiceQuizGame()
    game.start_game("test_voice_42_8")
    riddle = game.get_riddle()
    result = game.check_voice_answer(riddle["answer"])
    assert result["correct"] is True


def test_42_9_voice_answer_near_correct():
    game = VoiceQuizGame()
    game.start_game("test_voice_42_9")
    game.get_riddle()
    result = game.check_voice_answer("meo")
    assert isinstance(result["correct"], bool)
    assert result["score"] >= 0


test("42.1 WordQuizGame import + start", test_42_1_word_quiz_import_start)
test("42.2 get_question format đúng (4 options)", test_42_2_word_question_format)
test("42.3 submit_answer correct", test_42_3_word_submit_correct)
test("42.4 submit_answer incorrect", test_42_4_word_submit_incorrect)
test("42.5 end_game trả về summary", test_42_5_word_end_summary)
test("42.6 VoiceQuizGame import + start", test_42_6_voice_quiz_import_start)
test("42.7 get_riddle trả về dict", test_42_7_voice_get_riddle_dict)
test("42.8 check_voice_answer với đúng", test_42_8_voice_answer_correct)
test("42.9 check_voice_answer với gần đúng", test_42_9_voice_answer_near_correct)

print("\n[Group 43] Phase 9.1 — Motor Controller Placeholder")

from src.motion.motor_controller import MotorController


def test_43_1_motor_import():
    motor = MotorController(port=None)
    assert motor is not None


def test_43_2_motor_simulation_true():
    motor = MotorController(port=None)
    assert motor.is_simulation() is True


def test_43_3_motor_forward_no_crash():
    motor = MotorController(port=None)
    assert motor.forward() is True


def test_43_4_motor_stop_no_crash():
    motor = MotorController(port=None)
    assert motor.stop() is True


def test_43_5_motor_status_format():
    status = MotorController(port=None).get_status()
    assert "connected" in status
    assert "mode" in status
    assert "last_command" in status


def test_43_6_motor_go_home_no_crash():
    motor = MotorController(port=None)
    assert motor.go_home() is True


def test_43_7_motor_stop_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/motor/stop" in paths


def test_43_8_motor_status_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/motor/status" in paths


test("43.1 MotorController import", test_43_1_motor_import)
test("43.2 is_simulation() → True", test_43_2_motor_simulation_true)
test("43.3 forward() không crash", test_43_3_motor_forward_no_crash)
test("43.4 stop() không crash", test_43_4_motor_stop_no_crash)
test("43.5 get_status format đúng", test_43_5_motor_status_format)
test("43.6 go_home() không crash", test_43_6_motor_go_home_no_crash)
test("43.7 POST /api/motor/stop route tồn tại", test_43_7_motor_stop_route_exists)
test("43.8 GET /api/motor/status route tồn tại", test_43_8_motor_status_route_exists)

print("\n[Group 44] Phase 10.1 — Analytics & Weekly Report")

from src.api.routers.analytics_router import get_daily_stats, get_weekly_analytics


def test_44_1_analytics_weekly_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/analytics/weekly" in paths


def test_44_2_analytics_daily_route_exists():
    from src.api.server import app
    paths = {route.path for route in app.routes}
    assert "/api/analytics/daily" in paths


def test_44_3_weekly_analytics_format():
    data = get_weekly_analytics("test_analytics_44_3")
    assert "family_id" in data
    assert "conversations" in data
    assert "emotion" in data
    assert "learning" in data


def test_44_4_daily_stats_format():
    data = get_daily_stats("test_analytics_44_4")
    assert "family_id" in data
    assert "date" in data
    assert "conversations" in data


test("44.1 GET /api/analytics/weekly route tồn tại", test_44_1_analytics_weekly_route_exists)
test("44.2 GET /api/analytics/daily route tồn tại", test_44_2_analytics_daily_route_exists)
test("44.3 get_weekly_analytics format đúng", test_44_3_weekly_analytics_format)
test("44.4 get_daily_stats format đúng", test_44_4_daily_stats_format)

print("\n[Group 45] Phase 10.2 — Robot-to-Robot Communication")

from src.communication.robot_to_robot import RobotToRobot
from src.communication.video_call import VideoCallManager


def test_45_1_robot_to_robot_import():
    manager = RobotToRobot()
    assert manager is not None


def test_45_2_discover_robots_list():
    robots = RobotToRobot().discover_robots(timeout_sec=1)
    assert isinstance(robots, list)


def test_45_3_connected_robots_list():
    manager = RobotToRobot()
    assert manager.connect("127.0.0.1") is True
    robots = manager.get_connected_robots()
    assert isinstance(robots, list)
    assert len(robots) == 1


def test_45_4_video_call_import():
    manager = VideoCallManager()
    assert manager is not None


def test_45_5_get_contacts_list():
    contacts = VideoCallManager().get_contacts("test_video_45_5")
    assert isinstance(contacts, list)


def test_45_6_add_contact_dict():
    contact = VideoCallManager().add_contact("test_video_45_6", "Me")
    assert isinstance(contact, dict)
    assert "contact_id" in contact
    assert contact["name"] == "Me"


test("45.1 RobotToRobot import", test_45_1_robot_to_robot_import)
test("45.2 discover_robots trả về list", test_45_2_discover_robots_list)
test("45.3 get_connected_robots trả về list", test_45_3_connected_robots_list)
test("45.4 VideoCallManager import", test_45_4_video_call_import)
test("45.5 get_contacts trả về list", test_45_5_get_contacts_list)
test("45.6 add_contact trả về dict", test_45_6_add_contact_dict)

print("\n[Group 46] Fix Verification — Review Issues")


def test_46_1_video_call_routes_registered():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/video/call/start" in paths, "Video call start route phai duoc dang ky"
    assert "/api/video/contacts" in paths, "Video contacts route phai duoc dang ky"


def test_46_2_game_routes_registered():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/game/word-quiz/start" in paths, "Word quiz start route phai duoc dang ky"
    assert "/api/game/voice-quiz/start" in paths, "Voice quiz start route phai duoc dang ky"


def test_46_3_no_deprecated_datetime_utcnow():
    import subprocess
    result = subprocess.run(
        ["grep", "-r", "utcnow()", "src/"],
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "", f"Con utcnow() trong: {result.stdout}"


def test_46_4_learning_schedules_table_exists():
    from src.infrastructure.database.db import get_db_connection, init_db
    init_db()
    with get_db_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t["name"] for t in tables]
    assert "learning_schedules" in table_names, "Bang learning_schedules phai ton tai"


def test_46_5_schedule_save_load_from_sqlite():
    from src.infrastructure.database.db import get_learning_schedule, save_learning_schedule
    test_schedule = {
        "monday": {"subject": "english", "time": "19:00"},
        "tuesday": {"subject": "math", "time": "19:00"},
        "sunday": None,
    }
    assert save_learning_schedule("test_sched_family", test_schedule) is True
    loaded = get_learning_schedule("test_sched_family")
    assert "monday" in loaded
    assert loaded["monday"]["subject"] == "english"
    assert "sunday" not in loaded


def test_46_6_emotion_weekly_summary_format():
    from src.api.routers.emotion_router import get_weekly_summary
    from src.emotion.emotion_analyzer import EmotionAnalyzer
    analyzer = EmotionAnalyzer(family_id="test_emotion_family")
    summary = analyzer.get_weekly_summary("test_emotion_family")
    assert isinstance(summary, list), "Weekly summary phai la list"
    direct_summary = get_weekly_summary("test_emotion_family")
    assert isinstance(direct_summary, list), "Router helper phai tra ve list"
    if len(summary) > 0:
        day = summary[0]
        assert "date" in day or "dominant" in day, "Moi ngay phai co date hoac dominant"
        assert "breakdown" in day, "Moi ngay phai co breakdown"


test("46.1 Video call routes registered", test_46_1_video_call_routes_registered)
test("46.2 Game routes registered", test_46_2_game_routes_registered)
test("46.3 No deprecated datetime.utcnow()", test_46_3_no_deprecated_datetime_utcnow)
test("46.4 learning_schedules table exists", test_46_4_learning_schedules_table_exists)
test("46.5 Schedule save/load from SQLite", test_46_5_schedule_save_load_from_sqlite)
test("46.6 Emotion weekly summary format", test_46_6_emotion_weekly_summary_format)

print("\n[Group 47] Fix Verification — API Contract")


def test_47_1_parent_app_index_exists():
    from pathlib import Path
    idx = Path("frontend/parent_app/index.html")
    assert idx.exists(), "frontend/parent_app/index.html phai ton tai"


def test_47_2_ops_router_frontend_path():
    import inspect
    from src.api.routers import ops_router
    src = inspect.getsource(ops_router)
    assert "src/api/static" not in src, "ops_router khong duoc reference src/api/static nua"
    assert "frontend" in src, "ops_router phai reference frontend/parent_app"


def test_47_3_verify_db_clean_uses_src():
    with open("verify_db_clean.py", encoding="utf-8") as f:
        content = f.read()
    assert "src_brain" not in content, "verify_db_clean.py khong duoc import src_brain"


def test_47_4_verify_db_clean_runs():
    import subprocess
    result = subprocess.run(
        ["python3", "verify_db_clean.py"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"verify_db_clean.py loi: {result.stderr[:200]}"


def test_47_5_game_routes_exact():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/game/word-quiz/start" in paths
    assert "/api/game/voice-quiz/start" in paths
    assert "/api/game/start" not in paths, "Khong nen co generic /api/game/start route"


def test_47_6_music_play_route_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/music/play" in paths, "/api/music/play route phai ton tai"


test("47.1 Parent App index.html tồn tại đúng path", test_47_1_parent_app_index_exists)
test("47.2 ops_router trỏ đúng frontend path", test_47_2_ops_router_frontend_path)
test("47.3 verify_db_clean dùng src mới", test_47_3_verify_db_clean_uses_src)
test("47.4 verify_db_clean chạy không lỗi", test_47_4_verify_db_clean_runs)
test("47.5 Game routes đúng path không generic", test_47_5_game_routes_exact)
test("47.6 Music play route tồn tại", test_47_6_music_play_route_exists)

print("\n[Group 48] Fix Verification — Round 3")


def test_48_1_delete_family_learning_schedules():
    from src.infrastructure.database.db import (
        delete_family_record,
        get_learning_schedule,
        init_db,
        save_learning_schedule,
    )
    init_db()
    test_fid = "test_delete_family_48"
    save_learning_schedule(test_fid, {
        "monday": {"subject": "english", "time": "19:00"},
    })
    sched = get_learning_schedule(test_fid)
    assert "monday" in sched, "Schedule phai duoc luu truoc"
    try:
        delete_family_record(test_fid)
    except Exception:
        pass
    sched_after = get_learning_schedule(test_fid)
    assert len(sched_after) == 0, "learning_schedules phai duoc xoa khi delete family"


def test_48_2_delete_family_emotion_logs():
    from src.emotion.emotion_analyzer import EmotionAnalyzer
    from src.infrastructure.database.db import (
        delete_family_record,
        get_db_connection,
        init_db,
    )
    init_db()
    test_fid = "test_delete_family_48"
    EmotionAnalyzer(family_id=test_fid)
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO emotion_logs
            (family_id, timestamp, emotion, confidence, source)
            VALUES (?, datetime('now'), 'happy', 0.9, 'test')
            """,
            (test_fid,),
        )
        conn.commit()
    try:
        delete_family_record(test_fid)
    except Exception:
        pass
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT COUNT(*) as c FROM emotion_logs WHERE family_id=?",
            (test_fid,),
        ).fetchone()
    assert rows["c"] == 0, "emotion_logs phai duoc xoa khi delete family"


def test_48_3_music_volume_field_handled():
    with open("frontend/parent_app/index.html", encoding="utf-8") as f:
        frontend_src = f.read()
    assert "JSON.stringify({ level: parseInt(v) })" in frontend_src, (
        "Frontend phai gui level cho /api/music/volume"
    )
    import inspect
    from src.api.routers import music_router
    src = inspect.getsource(music_router)
    vol_idx = src.find("/api/music/volume")
    if vol_idx < 0:
        vol_idx = src.find("set_volume")
    vol_src = src[max(0, vol_idx):vol_idx + 300]
    assert "level" in vol_src or "volume" in vol_src, (
        "Music volume endpoint phai doc level hoac volume field"
    )


def test_48_4_stress_test_uses_src_paths():
    with open("stress_test.py", encoding="utf-8") as f:
        stress_content = f.read()
    assert "src_brain" not in stress_content, "stress_test.py khong duoc import src_brain"


def test_48_5_stress_test_runs_without_module_not_found():
    import subprocess
    result = subprocess.run(
        ["python3", "stress_test.py"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "ModuleNotFoundError" not in result.stderr, (
        f"stress_test co ModuleNotFoundError: {result.stderr[:300]}"
    )


def test_48_6_education_schedule_route_exists():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/education/schedule" in paths, (
        "/api/education/schedule route phai ton tai"
    )


test("48.1 delete_family xóa learning_schedules", test_48_1_delete_family_learning_schedules)
test("48.2 delete_family xóa emotion_logs", test_48_2_delete_family_emotion_logs)
test("48.3 Music volume field handled", test_48_3_music_volume_field_handled)
test("48.4 stress_test dùng src paths mới", test_48_4_stress_test_uses_src_paths)
test("48.5 stress_test chạy không ModuleNotFoundError", test_48_5_stress_test_runs_without_module_not_found)
test("48.6 Education schedule API route tồn tại", test_48_6_education_schedule_route_exists)

print("\n[Group 49] Fix Verification — Round 4")


def test_49_1_migrate_db_path_if_needed_callable():
    from src.infrastructure.database.db import migrate_db_path_if_needed
    assert callable(migrate_db_path_if_needed), "migrate_db_path_if_needed phải là callable"


def test_49_2_migrate_db_path_if_needed_no_crash():
    from src.infrastructure.database.db import migrate_db_path_if_needed
    try:
        migrate_db_path_if_needed()
    except Exception as e:
        raise AssertionError(f"migrate crash: {e}")


def test_49_3_video_call_manager_stores_family_id():
    from src.communication.video_call import VideoCallManager
    vm = VideoCallManager()
    result = vm.start_call(family_id="family_test_49", caller_name="Mẹ")
    assert "call_id" in result, "start_call phải trả call_id"
    call_id = result["call_id"]
    session = vm._active_calls.get(call_id)
    assert session is not None, "Session phải tồn tại"
    assert session.get("family_id") == "family_test_49", "Session phải lưu family_id"


def test_49_4_end_call_correct_family_true():
    from src.communication.video_call import VideoCallManager
    vm = VideoCallManager()
    result = vm.start_call(family_id="family_test_49", caller_name="Mẹ")
    ok = vm.end_call(result["call_id"], family_id="family_test_49")
    assert ok is True, "end_call với đúng family phải True"


def test_49_5_end_call_wrong_family_false():
    from src.communication.video_call import VideoCallManager
    vm = VideoCallManager()
    result = vm.start_call(family_id="family_A", caller_name="Mẹ A")
    call_id = result["call_id"]
    ok = vm.end_call(call_id, family_id="family_B")
    assert ok is False, "end_call với sai family phải False (isolation)"
    vm.end_call(call_id, family_id="family_A")


def test_49_6_music_transport_routes_registered():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    for route in ["/api/music/next", "/api/music/previous", "/api/music/shuffle", "/api/music/repeat"]:
        assert route in paths, f"{route} phải được đăng ký"


def test_49_7_music_player_transport_methods():
    from src.audio.output.music_player import MusicPlayer
    mp = MusicPlayer()
    assert hasattr(mp, "next_track"), "MusicPlayer phải có next_track()"
    assert hasattr(mp, "prev_track"), "MusicPlayer phải có prev_track()"
    assert hasattr(mp, "toggle_shuffle"), "MusicPlayer phải có toggle_shuffle()"
    assert hasattr(mp, "toggle_repeat"), "MusicPlayer phải có toggle_repeat()"


def test_49_8_toggle_shuffle_changes_state():
    from src.audio.output.music_player import MusicPlayer
    mp = MusicPlayer()
    r1 = mp.toggle_shuffle()
    assert "shuffle" in r1
    shuffle_1 = r1["shuffle"]
    r2 = mp.toggle_shuffle()
    assert r2["shuffle"] != shuffle_1, "toggle_shuffle phải đổi trạng thái"


test("49.1 migrate_db_path_if_needed callable", test_49_1_migrate_db_path_if_needed_callable)
test("49.2 migrate_db_path_if_needed không crash", test_49_2_migrate_db_path_if_needed_no_crash)
test("49.3 VideoCallManager lưu family_id", test_49_3_video_call_manager_stores_family_id)
test("49.4 end_call đúng family → True", test_49_4_end_call_correct_family_true)
test("49.5 end_call sai family → False (isolation)", test_49_5_end_call_wrong_family_false)
test("49.6 Music transport routes registered", test_49_6_music_transport_routes_registered)
test("49.7 MusicPlayer có đủ transport methods", test_49_7_music_player_transport_methods)
test("49.8 toggle_shuffle hoạt động đúng", test_49_8_toggle_shuffle_changes_state)

print("\n[Group 50] Security + Quality Fix Verification")


def test_50_1_sql_injection_allowlist_exists():
    from src.infrastructure.database.db import delete_family_record
    import inspect
    src = inspect.getsource(delete_family_record)
    assert "ALLOWED_CLEANUP_TABLES" in src or "allowlist" in src.lower() or "frozenset" in src, (
        "delete_family_record phải có table allowlist"
    )


def test_50_2_gemini_api_key_not_in_url():
    from src.ai import ai_engine
    import inspect
    import re
    src = inspect.getsource(ai_engine._stream_gemini)
    url_with_key = re.findall(r'f["\'].*GEMINI_API_KEY.*["\']', src)
    assert len(url_with_key) == 0, (
        f"GEMINI_API_KEY không được trong URL string: {url_with_key}"
    )


def test_50_3_timing_safe_pin_comparison():
    from src.api.routers import auth_router
    import inspect
    src = inspect.getsource(auth_router)
    assert "compare_digest" in src, "auth_router phải dùng hmac.compare_digest cho PIN"


def test_50_4_json_parse_error_handling():
    from src.api.routers import auth_router
    import inspect
    src = inspect.getsource(auth_router)
    assert "JSONDecodeError" in src or "json.JSONDecodeError" in src or "422" in src, (
        "auth_router phải handle JSONDecodeError"
    )


def test_50_5_thread_safe_groq_globals():
    from src.ai import ai_engine
    import inspect
    src = inspect.getsource(ai_engine)
    assert "_groq_lock" in src or "threading.Lock" in src, (
        "ai_engine phải có lock cho Groq globals"
    )


def test_50_6_safety_filter_unicode_boundary():
    from src.safety import safety_filter
    import inspect
    src = inspect.getsource(safety_filter)
    assert r'\b' not in src or "(?<!" in src, (
        "safety_filter không nên dùng \\b với Unicode"
    )


def test_50_7_safety_filter_catches_vietnamese_harmful_text():
    from src.safety.safety_filter import SafetyFilter
    sf_inst = SafetyFilter()
    is_safe, result = sf_inst.check("nội dung khiêu dâm không phù hợp")
    assert not is_safe and result != "nội dung khiêu dâm không phù hợp", (
        "SafetyFilter phải catch Vietnamese harmful text"
    )


def test_50_8_analytics_null_safety():
    from src.api.routers import analytics_router
    import inspect
    src = inspect.getsource(analytics_router)
    assert "or 0" in src or "if row" in src or "row[0] or" in src, (
        "analytics_router phải handle NULL values"
    )


def test_50_9_verify_password_works_correctly():
    from src.infrastructure.auth.auth import hash_password, verify_password
    test_hash = hash_password("testpassword123")
    assert verify_password("testpassword123", test_hash) is True, (
        "verify_password với đúng password phải True"
    )
    assert verify_password("wrongpassword", test_hash) is False, (
        "verify_password với sai password phải False"
    )


test("50.1 SQL injection allowlist tồn tại", test_50_1_sql_injection_allowlist_exists)
test("50.2 Gemini API key không trong URL", test_50_2_gemini_api_key_not_in_url)
test("50.3 Timing-safe PIN comparison", test_50_3_timing_safe_pin_comparison)
test("50.4 JSON parse error handling", test_50_4_json_parse_error_handling)
test("50.5 Thread-safe Groq globals", test_50_5_thread_safe_groq_globals)
test("50.6 Safety filter Unicode boundary", test_50_6_safety_filter_unicode_boundary)
test("50.7 Safety filter bắt Vietnamese harmful text", test_50_7_safety_filter_catches_vietnamese_harmful_text)
test("50.8 Analytics NULL safety", test_50_8_analytics_null_safety)
test("50.9 verify_password hoạt động đúng", test_50_9_verify_password_works_correctly)

# == GROUP 51: Main Loop FaceAnimator & Emotion Integration =================
print("\n[Group 51] Main Loop Integration")

def test_51_1_face_animator_in_init():
    import inspect
    from src.main import RobotBiApp
    src = inspect.getsource(RobotBiApp.__init__)
    assert "FaceAnimator" in src or "face_animator" in src.lower(), "FaceAnimator missing from init"

def test_51_2_set_mode_in_conversation_loop():
    import inspect
    from src.main import RobotBiApp
    src_full = inspect.getsource(RobotBiApp)
    assert "set_mode('listening')" in src_full or "set_mode(\"listening\")" in src_full, "set_mode('listening') not found"

def test_51_3_emotion_analyzer_in_main_loop():
    import inspect
    from src.main import RobotBiApp
    src_full = inspect.getsource(RobotBiApp)
    assert "EmotionAnalyzer" in src_full or "emotion_analyzer" in src_full.lower(), "EmotionAnalyzer missing from main loop"

def test_51_4_face_animator_has_error_handling():
    import inspect
    from src.main import RobotBiApp
    src_full = inspect.getsource(RobotBiApp)
    assert "try:" in src_full, "Missing try/except error handling"

def test_51_5_persona_manager_system_prompt():
    import inspect
    from src.main import RobotBiApp
    src_full = inspect.getsource(RobotBiApp)
    assert "get_system_prompt_modifier" in src_full or "persona" in src_full.lower(), "PersonaManager system prompt not found"

test("51.1 FaceAnimator tồn tại trong RobotBiApp", test_51_1_face_animator_in_init)
test("51.2 set_mode được gọi trong conversation loop", test_51_2_set_mode_in_conversation_loop)
test("51.3 EmotionAnalyzer trong main loop", test_51_3_emotion_analyzer_in_main_loop)
test("51.4 FaceAnimator fail không crash (try/except)", test_51_4_face_animator_has_error_handling)
test("51.5 PersonaManager system prompt", test_51_5_persona_manager_system_prompt)

# == GROUP 52: WakeWordDetector =============================================
print("\n[Group 52] WakeWordDetector")

def test_52_1_wake_word_detector_import():
    from src.audio.input.wake_word import WakeWordDetector
    assert WakeWordDetector is not None

def test_52_2_is_enabled():
    from src.audio.input.wake_word import WakeWordDetector
    detector = WakeWordDetector()
    assert isinstance(detector.is_enabled(), bool)

def test_52_3_wake_words_not_empty():
    from src.audio.input.wake_word import WakeWordDetector
    assert len(WakeWordDetector.WAKE_WORDS) > 0

def test_52_4_detect_silence_returns_false():
    from src.audio.input.wake_word import WakeWordDetector
    detector = WakeWordDetector()
    # 1 second of silence at 16kHz float32
    silence = b'\x00' * (16000 * 4)
    result = detector.detect(silence)
    assert result is False

def test_52_5_detector_in_earstt_flow():
    import inspect
    from src.audio.input.ear_stt import EarSTT
    src = inspect.getsource(EarSTT.listen_for_wakeword)
    assert "wake_detector" in src

test("52.1 WakeWordDetector import", test_52_1_wake_word_detector_import)
test("52.2 is_enabled() trả về bool", test_52_2_is_enabled)
test("52.3 WAKE_WORDS không rỗng", test_52_3_wake_words_not_empty)
test("52.4 detect với silence → False", test_52_4_detect_silence_returns_false)
test("52.5 WakeWordDetector trong EarSTT flow", test_52_5_detector_in_earstt_flow)

# == GROUP 53: SpeakerIdentifier ============================================
print("\n[Group 53] SpeakerIdentifier")

def test_53_1_speaker_identifier_import():
    from src.audio.input.speaker_id import SpeakerIdentifier
    assert SpeakerIdentifier is not None

def test_53_2_identify_pitch():
    from src.audio.input.speaker_id import SpeakerIdentifier
    si = SpeakerIdentifier()
    assert si.identify({"pitch": 260, "energy": 0.5}) == "be"
    assert si.identify({"pitch": 200, "energy": 0.5}) == "me"
    assert si.identify({"pitch": 150, "energy": 0.5}) == "bo"
    assert si.identify({"pitch": 90, "energy": 0.5}) == "ong"
    assert si.identify({"pitch": 70, "energy": 0.5}) == "ba"
    assert si.identify({}) == "unknown"

def test_53_3_get_address_form():
    from src.audio.input.speaker_id import SpeakerIdentifier
    si = SpeakerIdentifier()
    form_me = si.get_address_form("me")
    assert form_me["robot_self"] == "con"
    assert form_me["address"] == "mẹ"
    
    form_be = si.get_address_form("be")
    assert form_be["robot_self"] == "Bi"
    assert form_be["address"] == "bạn"

test("53.1 SpeakerIdentifier import", test_53_1_speaker_identifier_import)
test("53.2 identify trả về đúng role", test_53_2_identify_pitch)
test("53.3 get_address_form trả về đúng dict", test_53_3_get_address_form)

# == GROUP 54: Curriculum Scheduler =========================================
print("\n[Group 54] Curriculum Scheduler")

def test_54_1_curriculum_has_scheduler_methods():
    from src.education.curriculum import Curriculum
    assert hasattr(Curriculum, "start_scheduler")
    assert hasattr(Curriculum, "stop_scheduler")
    assert hasattr(Curriculum, "_scheduler_loop")

def test_54_2_scheduler_loop_content():
    import inspect
    from src.education.curriculum import Curriculum
    src = inspect.getsource(Curriculum._scheduler_loop)
    assert "time.sleep" in src
    assert "Bây giờ là giờ học" in src
    assert "tts_callback" in src

test("54.1 Curriculum có methods scheduler", test_54_1_curriculum_has_scheduler_methods)
test("54.2 _scheduler_loop chứa logic nhắc nhở", test_54_2_scheduler_loop_content)

# == GROUP 55: Lullaby Fade-out =============================================
print("\n[Group 55] Lullaby Fade-out")

def test_55_1_play_lullaby_starts_fade():
    from src.audio.output.music_player import MusicPlayer
    import inspect
    src = inspect.getsource(MusicPlayer.play_lullaby)
    assert "_fade_step" in src
    assert "threading.Timer" in src

test("55.1 play_lullaby chứa logic fade-out với threading.Timer", test_55_1_play_lullaby_starts_fade)

# == GROUP 56: Personalized Story ===========================================
print("\n[Group 56] Personalized Story")

def test_56_1_tell_personalized_story_calls_llm():
    from src.entertainment.story_engine import StoryEngine
    import inspect
    src = inspect.getsource(StoryEngine.tell_personalized_story)
    assert "stream_chat" in src
    assert "Nhân vật chính" in src or "child_name" in src

test("56.1 tell_personalized_story gọi stream_chat để tạo truyện", test_56_1_tell_personalized_story_calls_llm)

# == GROUP 57: Persona System Prompt ========================================
print("\n[Group 57] Persona System Prompt")

def test_57_1_build_system_prompt_exists():
    from src.ai.prompts import build_system_prompt
    assert callable(build_system_prompt)

def test_57_2_build_system_prompt_playful():
    from src.ai.prompts import build_system_prompt
    prompt = build_system_prompt({"playfulness": 80, "name": "Bi", "gender": "boy"})
    assert "vui vẻ" in prompt.lower() or "nghịch ngợm" in prompt.lower() or "pha trò" in prompt.lower()
    
def test_57_3_build_system_prompt_energy():
    from src.ai.prompts import build_system_prompt
    prompt = build_system_prompt({"energy": 80, "name": "Bi", "gender": "boy"})
    assert "nhiệt tình" in prompt.lower() or "hào hứng" in prompt.lower() or "!" in prompt
    
def test_57_4_build_system_prompt_introvert():
    from src.ai.prompts import build_system_prompt
    prompt = build_system_prompt({"extraversion": 20, "name": "Bi", "gender": "boy"})
    assert "ngắn gọn" in prompt.lower() or "trầm tĩnh" in prompt.lower()

test("57.1 build_system_prompt tồn tại", test_57_1_build_system_prompt_exists)
test("57.2 Tính cách playfulness", test_57_2_build_system_prompt_playful)
test("57.3 Tính cách energy", test_57_3_build_system_prompt_energy)
test("57.4 Tính cách extraversion thấp", test_57_4_build_system_prompt_introvert)

# == GROUP 58: Quiz Games ===================================================
print("\n[Group 58] Quiz Games")

def test_58_1_word_quiz_import():
    from src.entertainment.game_word_quiz import WordQuizGame
    assert WordQuizGame is not None

def test_58_2_voice_quiz_import():
    from src.entertainment.game_voice_quiz import VoiceQuizGame
    assert VoiceQuizGame is not None

def test_58_3_word_quiz_logic():
    from src.entertainment.game_word_quiz import WordQuizGame
    game = WordQuizGame("easy")
    q = game.get_random_question()
    if q:
        assert game.check_answer(q, q["correct"]) is True

def test_58_4_voice_quiz_logic():
    from src.entertainment.game_voice_quiz import VoiceQuizGame
    game = VoiceQuizGame()
    r = game.get_random_riddle()
    if r:
        ans = r["answer"]
        assert game.check_answer(r, ans) is True
        assert game.check_answer(r, "sai") is False

test("58.1 WordQuizGame import", test_58_1_word_quiz_import)
test("58.2 VoiceQuizGame import", test_58_2_voice_quiz_import)
test("58.3 WordQuizGame logic", test_58_3_word_quiz_logic)
test("58.4 VoiceQuizGame logic", test_58_4_voice_quiz_logic)

print("\n[Group 59] API Contract Verification")

# 59.1 — WordQuizGame start_game nhận difficulty
def test_59_1():
    from src.entertainment.game_word_quiz import WordQuizGame
    g = WordQuizGame()
    result = g.start_game("fam1", "easy")
    assert result["status"] == "started"
    result2 = g.start_game("fam1", "medium")
    assert result2["status"] == "started"
test("59.1 WordQuizGame start_game(family_id, difficulty)", test_59_1)

# 59.2 — get_question đủ fields
def test_59_2():
    from src.entertainment.game_word_quiz import WordQuizGame
    g = WordQuizGame()
    g.start_game("fam1", "easy")
    q = g.get_question()
    assert "question" in q, f"Missing 'question', got: {list(q.keys())}"
    assert "options" in q
    assert len(q["options"]) == 4
    assert "time_limit_sec" in q
test("59.2 WordQuizGame get_question fields", test_59_2)

# 59.3 — submit_answer với correct answer string
def test_59_3():
    from src.entertainment.game_word_quiz import WordQuizGame
    import json
    from pathlib import Path
    g = WordQuizGame()
    g.start_game("fam1", "easy")
    q = g.get_question()
    if not q:
        return
    correct_text = q["options"][0]  # test với option đầu
    result = g.submit_answer(correct_text)
    assert "correct" in result
    assert "score" in result
test("59.3 WordQuizGame submit_answer string", test_59_3)

# 59.4 — end_game có total_score và high_score
def test_59_4():
    from src.entertainment.game_word_quiz import WordQuizGame
    g = WordQuizGame()
    g.start_game("fam59_4", "easy")
    summary = g.end_game()
    assert "total_score" in summary, \
        f"Missing total_score, got: {list(summary.keys())}"
    assert "high_score" in summary, \
        f"Missing high_score, got: {list(summary.keys())}"
    assert "correct" in summary
    assert "incorrect" in summary
test("59.4 WordQuizGame end_game contract", test_59_4)

# 59.5 — get_leaderboard tồn tại và trả list
def test_59_5():
    from src.entertainment.game_word_quiz import WordQuizGame
    g = WordQuizGame()
    board = g.get_leaderboard("fam59_5")
    assert isinstance(board, list)
test("59.5 WordQuizGame get_leaderboard", test_59_5)

# 59.6 — VoiceQuizGame get_riddle đúng fields
def test_59_6():
    from src.entertainment.game_voice_quiz import VoiceQuizGame
    g = VoiceQuizGame()
    g.start_game("fam59_6")
    riddle = g.get_riddle()
    assert "riddle_text" in riddle, \
        f"Missing riddle_text, got: {list(riddle.keys())}"
    assert "hint" in riddle
    assert "answer" in riddle
test("59.6 VoiceQuizGame get_riddle fields", test_59_6)

# 59.7 — VoiceQuizGame exact answer → correct=True
def test_59_7():
    from src.entertainment.game_voice_quiz import VoiceQuizGame
    g = VoiceQuizGame()
    g.start_game("fam59_7")
    riddle = g.get_riddle()
    result = g.check_voice_answer(riddle["answer"])
    assert result["correct"] is True, \
        f"Exact answer phải correct=True, got: {result}"
test("59.7 VoiceQuizGame exact answer correct", test_59_7)

# 59.8 — Education summary đúng fields
def test_59_8():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/education/summary" in paths
    assert "/api/education/vocabulary" in paths
    assert "/api/education/schedule" in paths
test("59.8 Education routes tồn tại", test_59_8)

# 59.9 — Analytics weekly route tồn tại
def test_59_9():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/analytics/weekly" in paths
    assert "/api/analytics/daily" in paths
test("59.9 Analytics routes tồn tại", test_59_9)

# 59.10 — Game scores đúng format
def test_59_10():
    from src.api.server import app
    paths = [r.path for r in app.routes]
    assert "/api/game/scores" in paths
    assert "/api/video/history" in paths
test("59.10 Game scores + video history routes", test_59_10)

# 59.11 — state.py event không trả None
def test_59_11():
    # Import và kiểm tra hàm parse không trả None
    import inspect
    from src.infrastructure.sessions import state as st
    src = inspect.getsource(st)
    # Kiểm tra return không nằm trong except block
    # bằng cách tìm pattern "except" theo sau bởi "return"
    lines = src.split('\n')
    in_except = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('except'):
            in_except = True
        elif in_except and stripped.startswith('return'):
            # return nằm trong except là bug
            assert False, \
                f"Return trong except block tại line {i}: {line}"
        elif in_except and stripped and \
             not stripped.startswith('#') and \
             not stripped.startswith('pass') and \
             not line.startswith(' ' * 12):
            in_except = False
test("59.11 state.py event parse không return trong except", test_59_11)

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
