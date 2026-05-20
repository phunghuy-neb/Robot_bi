#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
debug_rag.py -- Robot Bi: Chẩn đoán RAG Memory
================================================
Mục đích: tìm root cause của 2 vấn đề:
  Vấn đề 1: Bi không nhớ thông tin từ session trước sau restart
  Vấn đề 2: Bi nhắc thông tin không liên quan (nhớ bà ngoại khi hỏi tên)

Chạy: python tests/debug_rag.py
Không sửa bất kỳ logic nào -- chỉ đọc và in kết quả.
"""

import sys
import os
import time
import threading
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

# ── Setup logging để thấy DEBUG từ rag_manager ───────────────────────────────
import logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(name)s | %(levelname)s | %(message)s",
)
logging.getLogger("rag_manager").setLevel(logging.DEBUG)

from src.memory.rag_manager import RAGManager, _MIN_SIMILARITY, _FACT_PATTERNS

SEP  = "=" * 64
SEP2 = "-" * 64

TEST_DB = "runtime/_debug_rag_tmp"
REAL_DB = "runtime/chroma_db"


def section(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def ok(msg):   print(f"  [OK]  {msg}")
def warn(msg): print(f"  [!!]  {msg}")
def info(msg): print(f"  [--]  {msg}")
def fail(msg): print(f"  [XX]  {msg}")


# ════════════════════════════════════════════════════════════════════════════════
# BLOCK A — Kiểm tra extract_facts() có trích xuất đúng không
# ════════════════════════════════════════════════════════════════════════════════

def check_extract_facts():
    section("BLOCK A — _extract_facts() regex extraction")

    rag = RAGManager(db_path=TEST_DB)

    test_cases = [
        # (user_text, bi_text, mo_ta, ky_vong_co_fact)
        ("tên mình là An",              "Bi nhớ rồi, bạn tên An!",          "tên rõ ràng",         True),
        ("mình thích ăn phở",           "Phở ngon lắm!",                    "sở thích ăn",         True),
        ("mình có nuôi mèo tên Mimi",   "Mèo Mimi cute quá!",               "vật nuôi",            True),
        ("tôi nhớ bà ngoại",            "Bi hiểu, nhớ bà thật buồn nhỉ",    "CẢM XÚC — fallback?", None),
        ("bi ơi xin chào",              "Xin chào bé!",                     "chào hỏi",            None),
        ("tại sao bầu trời xanh?",      "Vì ánh sáng mặt trời...",          "câu hỏi — KHÔNG lưu", False),
        ("hôm nay mình học lớp 3",      "Lớp 3 thú vị lắm!",               "lớp học",             True),
        ("mình đang buồn lắm",          "Bi hiểu cảm giác đó",             "cảm xúc",             None),
    ]

    print()
    for user_text, bi_text, mo_ta, ky_vong in test_cases:
        facts = rag._extract_facts(user_text, bi_text)
        if facts:
            status = ok if ky_vong is not False else warn
            status(f'"{user_text}"')
            for f in facts:
                print(f"         → Fact: {repr(f)}")
        else:
            status = ok if ky_vong is False else (warn if ky_vong is True else info)
            status(f'"{user_text}" → KHÔNG trích xuất được fact nào ({mo_ta})')

    del rag


# ════════════════════════════════════════════════════════════════════════════════
# BLOCK B — Kiểm tra daemon thread race condition (vấn đề 1)
# ════════════════════════════════════════════════════════════════════════════════

def check_daemon_thread_race():
    section("BLOCK B — Daemon thread race condition khi app exit nhanh")

    rag = RAGManager(db_path=TEST_DB)
    results = {"saved": False}

    def save_in_daemon():
        time.sleep(0.3)  # giả lập ChromaDB encode/save mất 300ms
        result = rag.extract_and_save("tên mình là TestDaemon", "OK", family_id="default")
        results["saved"] = result

    t = threading.Thread(target=save_in_daemon, daemon=True)
    t.start()

    # Không join — giống app exit ngay sau khi start thread
    # Chờ rất ít để thấy thread có kịp save không
    time.sleep(0.05)  # 50ms — app "thoát" trước khi thread xong

    count_before_join = rag._count_memories("default")
    info(f"Memories sau 50ms (chưa join): {count_before_join}")

    # Bây giờ join để xem nếu chờ đủ thì có save không
    t.join(timeout=2.0)
    count_after_join = rag._count_memories("default")
    info(f"Memories sau join đủ:         {count_after_join}")

    if count_before_join < count_after_join:
        warn("RACE CONDITION XÁC NHẬN: nếu app exit trước khi thread xong → memory bị mất!")
        warn("extract_and_save chạy trong daemon thread — bị kill khi main thread thoát.")
    else:
        ok("Thread kịp save trước khi check (không có race ở test này)")

    del rag


# ════════════════════════════════════════════════════════════════════════════════
# BLOCK C — Kiểm tra ChromaDB thực sự lưu và persist không
# ════════════════════════════════════════════════════════════════════════════════

def check_chroma_persist():
    section("BLOCK C — ChromaDB persist: lưu xong → tạo instance mới → query lại")

    db_path = TEST_DB + "_persist"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)

    # Session 1: lưu memory
    rag1 = RAGManager(db_path=db_path)
    saved = rag1.extract_and_save("tên mình là PersistTest", "OK", family_id="default")
    count1 = rag1._count_memories("default")
    info(f"Session 1: extract_and_save={saved}, count={count1}")
    del rag1  # "đóng app"

    time.sleep(0.2)  # đợi ChromaDB flush

    # Session 2: instance mới (giống restart app)
    rag2 = RAGManager(db_path=db_path)
    count2 = rag2._count_memories("default")
    context = rag2.retrieve("tên bé là gì", family_id="default")
    info(f"Session 2 (sau restart): count={count2}")
    info(f"retrieve('tên bé là gì'): {repr(context[:80]) if context else 'RONG'}")

    if count2 > 0 and "PersistTest" in context:
        ok("ChromaDB PERSIST hoạt động đúng — data sống qua restart")
    elif count2 > 0:
        warn(f"Data persist OK (count={count2}) nhưng retrieve KHÔNG tìm thấy 'PersistTest'")
        warn("→ Có thể similarity score < 0.50 cho query 'tên bé là gì'")
    else:
        fail("ChromaDB KHÔNG persist — data mất sau khi del instance!")

    del rag2
    shutil.rmtree(db_path, ignore_errors=True)


# ════════════════════════════════════════════════════════════════════════════════
# BLOCK D — Kiểm tra family_id isolation (vấn đề 2 — filter)
# ════════════════════════════════════════════════════════════════════════════════

def check_family_isolation():
    section("BLOCK D — Family ID isolation")

    rag = RAGManager(db_path=TEST_DB)
    rag.clear_all_memories("family_A")
    rag.clear_all_memories("family_B")

    rag.extract_and_save("tên mình là Alice", "OK", family_id="family_A")
    rag.extract_and_save("tên mình là Bob",   "OK", family_id="family_B")

    ctx_A = rag.retrieve("tên bé", family_id="family_A")
    ctx_B = rag.retrieve("tên bé", family_id="family_B")

    info(f"family_A retrieve: {repr(ctx_A[:60]) if ctx_A else 'RONG'}")
    info(f"family_B retrieve: {repr(ctx_B[:60]) if ctx_B else 'RONG'}")

    leak_A_in_B = ctx_B and "Alice" in ctx_B
    leak_B_in_A = ctx_A and "Bob" in ctx_A

    if leak_A_in_B or leak_B_in_A:
        fail(f"FAMILY ISOLATION BỊ LỌT! Alice in B={leak_A_in_B}, Bob in A={leak_B_in_A}")
    else:
        ok("Family isolation hoạt động đúng — không bị cross-family leak")

    del rag


# ════════════════════════════════════════════════════════════════════════════════
# BLOCK E — Raw ChromaDB query: top-5 scores cho các query thực tế (vấn đề 2)
# ════════════════════════════════════════════════════════════════════════════════

def check_raw_scores():
    section("BLOCK E — Raw similarity scores: query thực tế vs memories")

    rag = RAGManager(db_path=TEST_DB)
    rag.clear_all_memories("debug")

    # Seed memories giả lập session cũ
    memories_to_save = [
        ("tôi nhớ bà ngoại",              "Ôi nhớ bà ngoại rồi..."),
        ("tên mình là Nam",               "Bi nhớ rồi, bé tên Nam!"),
        ("mình thích ăn phở",             "Phở ngon lắm!"),
        ("hôm nay mình buồn",             "Bi hiểu cảm giác đó"),
        ("mình đang học lớp 5 trường ABC","Lớp 5 thú vị lắm!"),
    ]
    for u, b in memories_to_save:
        rag.extract_and_save(u, b, family_id="debug")

    all_memories = rag.list_memories("debug")
    print(f"\n  Đã lưu {len(all_memories)} memories:")
    for m in all_memories:
        print(f"    [{m['source']}] {repr(m['fact'])}")

    # Query thực tế và print raw scores
    queries = [
        "tên bé là gì",
        "bi ơi xin chào",
        "bầu trời màu gì",
        "tôi nhớ bà ngoại",
    ]

    print(f"\n  Threshold hiện tại: _MIN_SIMILARITY = {_MIN_SIMILARITY}")
    print()

    for query in queries:
        print(f"  Query: '{query}'")
        total = rag._count_memories("debug")
        if total == 0:
            print("    (không có memory nào)")
            continue

        q_emb = rag._embed(query)
        results = rag._collection.query(
            query_embeddings=[q_emb],
            n_results=min(5, total),
            where={"family_id": "debug"},
            include=["documents", "distances"],
        )
        docs      = results.get("documents", [[]])[0]
        distances = results.get("distances",  [[]])[0]

        if not docs:
            print("    (không có kết quả)")
            continue

        for doc, dist in zip(docs, distances):
            sim = 1.0 - dist
            flag = "INJECT" if sim >= _MIN_SIMILARITY else "skip "
            marker = "  <-- VẤN ĐỀ 2!" if (sim >= _MIN_SIMILARITY and "bà ngoại" in doc and query != "tôi nhớ bà ngoại") else ""
            print(f"    [{flag}] sim={sim:.3f}  {repr(doc[:50])}{marker}")
        print()

    del rag


# ════════════════════════════════════════════════════════════════════════════════
# BLOCK F — Kiểm tra main.py: extract_and_save được gọi đúng chỗ không
# ════════════════════════════════════════════════════════════════════════════════

def check_main_integration():
    section("BLOCK F — main.py integration: điểm gọi extract_and_save")

    main_path = os.path.join(os.path.dirname(__file__), "..", "src", "main.py")
    with open(main_path, encoding="utf-8") as f:
        source = f.read()

    lines = source.splitlines()

    # Tìm tất cả điểm gọi extract_and_save
    save_calls = [(i+1, l.strip()) for i, l in enumerate(lines) if "extract_and_save" in l]
    # Tìm điểm gọi retrieve
    retrieve_calls = [(i+1, l.strip()) for i, l in enumerate(lines) if "rag.retrieve" in l and "def " not in l]

    print()
    info(f"Điểm gọi extract_and_save ({len(save_calls)} chỗ):")
    for lineno, line in save_calls:
        print(f"    L{lineno}: {line}")

    # Kiểm tra có dùng daemon thread không
    daemon_lines = [(i+1, l.strip()) for i, l in enumerate(lines)
                    if "daemon=True" in l and "extract_and_save" in source[max(0, source.find(l)-200):source.find(l)+10]]

    if any("extract_and_save" in source[max(0,i*10-300):i*10+50] for i, _ in daemon_lines):
        pass

    # Tìm đoạn Thread + extract_and_save
    thread_block_start = None
    for i, l in enumerate(lines):
        if "threading.Thread" in l and i+3 < len(lines):
            block = "\n".join(lines[i:i+5])
            if "extract_and_save" in block:
                thread_block_start = i + 1
                is_daemon = "daemon=True" in block
                if is_daemon:
                    warn(f"L{thread_block_start}: extract_and_save chạy trong DAEMON thread!")
                    warn("Nếu app exit ngay sau conversation → thread bị kill → memory KHÔNG được lưu!")
                else:
                    ok(f"L{thread_block_start}: extract_and_save chạy trong non-daemon thread")

    print()
    info(f"Điểm gọi rag.retrieve ({len(retrieve_calls)} chỗ):")
    for lineno, line in retrieve_calls:
        print(f"    L{lineno}: {line}")

    # Kiểm tra retrieve có truyền family_id không
    for lineno, line in retrieve_calls:
        if "family_id" in line:
            ok(f"L{lineno}: retrieve() có truyền family_id")
        else:
            warn(f"L{lineno}: retrieve() KHÔNG truyền family_id — sẽ dùng 'default'!")


# ════════════════════════════════════════════════════════════════════════════════
# BLOCK G — Query REAL ChromaDB (nếu có) để xem dữ liệu thực
# ════════════════════════════════════════════════════════════════════════════════

def check_real_db():
    section("BLOCK G — Real ChromaDB: top-5 memories từ DB thật")

    if not os.path.exists(REAL_DB):
        info(f"Không tìm thấy real DB tại {REAL_DB} — bỏ qua block này")
        return

    try:
        rag = RAGManager(db_path=REAL_DB)
        stats = rag.get_stats()
        print()
        info(f"DB path : {REAL_DB}")
        info(f"Total   : {stats['total_facts']} memories")
        info(f"Oldest  : {stats['oldest_timestamp']}")
        info(f"Newest  : {stats['newest_timestamp']}")

        memories = rag.list_memories()
        if not memories:
            info("DB rỗng — chưa có memory nào được lưu")
            del rag
            return

        print(f"\n  Top {min(5, len(memories))} memories gần nhất:")
        for m in memories[:5]:
            print(f"    [{m['timestamp'][:19]}] [{m['source']}] {repr(m['fact'][:60])}")

        # Query thực để xem robot đang retrieve gì
        test_queries = ["tên bé là gì", "xin chào", "nhớ bà ngoại"]
        print()
        for q in test_queries:
            ctx = rag.retrieve(q)
            if ctx:
                warn(f"retrieve('{q}') → {repr(ctx[:80])}")
            else:
                info(f"retrieve('{q}') → (rỗng — dưới threshold)")

        del rag
    except Exception as e:
        fail(f"Không đọc được real DB: {e}")


# ════════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(SEP)
    print("  DEBUG RAG MEMORY — Robot Bi")
    print(SEP)

    # Dọn DB test cũ
    if os.path.exists(TEST_DB):
        shutil.rmtree(TEST_DB)

    try:
        check_extract_facts()
        check_daemon_thread_race()
        check_chroma_persist()
        check_family_isolation()
        check_raw_scores()
        check_main_integration()
        check_real_db()
    finally:
        # Cleanup
        for path in [TEST_DB, TEST_DB + "_persist"]:
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                except Exception:
                    pass

    print(f"\n{SEP}")
    print("  DEBUG HOÀN TẤT — Xem [!!] và [XX] ở trên để biết root cause")
    print(SEP)
