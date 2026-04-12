"""
rag_manager.py — Robot Bi: Hải Mã (Bộ nhớ dài hạn RAG)
=========================================================
Chức năng:
  - Lưu trữ facts trích xuất từ hội thoại vào ChromaDB (vector database cục bộ).
  - Truy vấn facts liên quan đến câu hỏi của bé để inject vào LLM context.
  - Hoàn toàn offline sau lần tải model embedding lần đầu.

Model embedding: paraphrase-multilingual-MiniLM-L12-v2
  - Hỗ trợ tiếng Việt tốt, kích thước ~420MB
  - Tải tự động vào ~/.cache/huggingface lần đầu, sau đó dùng local

Chạy test độc lập:
    python src_brain/memory_rag/rag_manager.py
"""

import os
import re
import uuid
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("rag_manager")

# ── Cấu hình ──────────────────────────────────────────────────────────────────
_DEFAULT_DB_PATH    = "src_brain/memory_rag/chroma_db"
_EMBED_MODEL_NAME   = "paraphrase-multilingual-MiniLM-L12-v2"
_COLLECTION_NAME    = "bi_memory"
_MIN_SIMILARITY = 0.35   # cosine similarity tối thiểu để xem là "liên quan" (0.0–1.0)

# ── Patterns trích xuất facts ─────────────────────────────────────────────────
# Mỗi pattern: (tên_loại_fact, list_regex)
_FACT_PATTERNS = [
    ("tên", [
        r"(?:tên|tên mình|tên em|tên con|tên bé|tên tôi|tên mình là|gọi mình là|tên là)\s+([\w\s]+)",
        r"(?:mình|tôi|em|con|bé)\s+(?:tên là|là|tên)\s+([\w\s]+)",
    ]),
    ("sở thích", [
        r"(?:thích|yêu thích|mê|ghiền|hay|thường)\s+([\w\s]+)",
        r"(?:môn|món|trò chơi|game|nhạc|phim)\s+(?:yêu thích|thích nhất|hay chơi|hay xem)\s+(?:là|của mình là)?\s*([\w\s]+)",
    ]),
    ("vật nuôi", [
        r"(?:có|nuôi|đang nuôi|có nuôi)\s+(?:một con |con )?(chó|mèo|hamster|thỏ|chim|cá|rùa|vẹt|gà)[^.]*",
        r"(?:chó|mèo|hamster|thỏ|chim|cá|rùa)\s+(?:tên là|tên|của mình là|của tôi là)\s+([\w\s]+)",
    ]),
    ("bạn bè", [
        r"(?:bạn thân|bạn tốt|bạn của mình|bạn của tôi|bạn tên)\s+([\w\s]+)",
        r"(?:chơi với|học với|ngồi cạnh)\s+([\w\s]+)",
    ]),
    ("sự kiện", [
        r"(?:hôm nay|ngày mai|tuần này|cuối tuần|hôm qua)\s+.{5,60}",
        r"(?:sinh nhật|tiệc|đi chơi|đi học|đi du lịch)\s+.{5,50}",
    ]),
    ("gia đình", [
        r"(?:bố|ba|mẹ|anh|chị|em|ông|bà)\s+(?:tên|tên là|của mình)\s+([\w\s]+)",
        r"(?:có|có một)\s+(?:người anh|người chị|em trai|em gái|anh trai|chị gái)",
    ]),
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Class RAGManager
# ═══════════════════════════════════════════════════════════════════════════════

class RAGManager:
    """
    Quản lý trí nhớ dài hạn của Robot Bi bằng ChromaDB + sentence-transformers.

    Luồng hoạt động:
      1. extract_and_save(user_text, bi_text) — trích xuất facts, embed, lưu
      2. retrieve(query)                       — tìm facts liên quan, trả về context string
      3. Inject context string vào prompt LLM trước khi gọi stream_chat()
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        """
        Khởi tạo ChromaDB persistent client và load embedding model.

        Args:
            db_path: Đường dẫn thư mục lưu ChromaDB (tự tạo nếu chưa có).
        """
        self._db_path = os.path.abspath(db_path)
        os.makedirs(self._db_path, exist_ok=True)

        # ── Khởi tạo ChromaDB ─────────────────────────────────────────────────
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=self._db_path)
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB khởi tạo tại: %s", self._db_path)
        except ImportError:
            raise RuntimeError(
                "Thiếu thư viện 'chromadb'. Chạy: pip install chromadb"
            )

        # ── Load embedding model ───────────────────────────────────────────────
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Đang tải embedding model '%s'...", _EMBED_MODEL_NAME)
            self._embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
            logger.info("Embedding model sẵn sàng.")
        except ImportError:
            raise RuntimeError(
                "Thiếu thư viện 'sentence-transformers'. "
                "Chạy: pip install sentence-transformers"
            )

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        """Chuyển text thành vector embedding."""
        return self._embed_model.encode(text, convert_to_numpy=True).tolist()

    def _extract_facts(self, user_text: str, bi_text: str) -> list[str]:
        """
        Trích xuất facts từ cặp hội thoại (user + bi) bằng regex.
        KHÔNG gọi LLM để giữ latency thấp.

        Returns:
            Danh sách các fact string đã trích xuất (có thể rỗng).
        """
        combined_text = f"{user_text} {bi_text}".lower()
        facts = []

        for fact_type, patterns in _FACT_PATTERNS:
            for pattern in patterns:
                matches = re.findall(pattern, combined_text, re.IGNORECASE)
                for m in matches:
                    if isinstance(m, tuple):
                        m = " ".join(x for x in m if x).strip()
                    else:
                        m = m.strip()

                    if len(m) < 2 or len(m) > 100:
                        continue

                    # Format fact thành câu hoàn chỉnh
                    if fact_type == "tên":
                        fact = f"Bé tên là {m.title()}"
                    elif fact_type == "sở thích":
                        fact = f"Bé thích {m}"
                    elif fact_type == "vật nuôi":
                        fact = f"Bé có {m}"
                    elif fact_type == "bạn bè":
                        fact = f"Bạn của bé tên {m}"
                    elif fact_type == "sự kiện":
                        fact = m  # giữ nguyên câu sự kiện
                    elif fact_type == "gia đình":
                        fact = f"Gia đình bé: {m}"
                    else:
                        fact = m

                    if fact not in facts:
                        facts.append(fact)

        # Nếu không tìm được facts qua regex, lưu toàn bộ user_text nếu đủ ngắn
        if not facts and len(user_text.strip()) >= 10 and len(user_text.strip()) <= 200:
            # Chỉ lưu nếu user_text trông như một fact (không phải câu hỏi)
            if not re.search(r'\?|sao|tại sao|thế nào|như thế|ở đâu|khi nào|bao nhiêu', user_text, re.IGNORECASE):
                facts.append(user_text.strip())

        return facts

    # ── Public API ────────────────────────────────────────────────────────────

    def extract_and_save(self, user_text: str, bi_text: str) -> bool:
        """
        Trích xuất facts từ cặp hội thoại và lưu vào ChromaDB.

        Args:
            user_text: Câu bé nói.
            bi_text:   Câu Bi trả lời.

        Returns:
            True nếu có ít nhất 1 fact được lưu, False nếu không tìm được fact nào.
        """
        if not user_text or not user_text.strip():
            return False

        facts = self._extract_facts(user_text, bi_text)
        if not facts:
            logger.debug("Không tìm được fact nào trong: '%s'", user_text[:60])
            return False

        ids        = []
        embeddings = []
        documents  = []
        metadatas  = []

        for fact in facts:
            fact_id = str(uuid.uuid4())
            ids.append(fact_id)
            embeddings.append(self._embed(fact))
            documents.append(fact)
            metadatas.append({
                "timestamp":   datetime.now().isoformat(),
                "source":      "conversation",
                "user_input":  user_text[:200],
                "bi_response": bi_text[:200],
            })

        try:
            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info("Đã lưu %d fact(s): %s", len(facts), facts)
            return True
        except Exception as e:
            logger.error("Lỗi khi lưu fact vào ChromaDB: %s", e)
            return False

    def retrieve(self, query: str, k: int = 3) -> str:
        """
        Tìm kiếm top-k facts liên quan đến query, trả về context string.

        Args:
            query: Câu hỏi/yêu cầu của bé.
            k:     Số facts tối đa trả về.

        Returns:
            String context sẵn sàng inject vào LLM prompt.
            Ví dụ: "[Trí nhớ của Bi] Bé tên là An. Bé thích khủng long."
            Trả về "" nếu không có fact liên quan (score < threshold).
        """
        if not query or not query.strip():
            return ""

        total_items = self._collection.count()
        if total_items == 0:
            return ""

        try:
            query_embedding = self._embed(query)
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(k, total_items),
                include=["documents", "distances"],
            )

            docs      = results.get("documents", [[]])[0]
            distances = results.get("distances",  [[]])[0]

            # ChromaDB với cosine space: distance = 1 - cosine_similarity
            # → similarity = 1 - distance
            relevant_facts = []
            for doc, dist in zip(docs, distances):
                similarity = 1.0 - dist
                if similarity >= _MIN_SIMILARITY:
                    relevant_facts.append(doc)
                    logger.debug("Fact (sim=%.2f): %s", similarity, doc[:60])

            if not relevant_facts:
                return ""

            context = "[Trí nhớ của Bi] " + " ".join(relevant_facts)
            logger.info("Retrieve %d fact(s) cho query: '%s'", len(relevant_facts), query[:60])
            return context

        except Exception as e:
            logger.error("Lỗi khi truy vấn ChromaDB: %s", e)
            return ""

    def list_memories(self) -> list[dict]:
        """
        Trả về toàn bộ facts đã lưu, sắp xếp theo timestamp mới nhất.

        Returns:
            Danh sách dict: {"id", "fact", "timestamp", "source"}
        """
        try:
            total = self._collection.count()
            if total == 0:
                return []

            results = self._collection.get(
                include=["documents", "metadatas"],
                limit=total,
            )

            items = []
            for doc_id, doc, meta in zip(
                results["ids"], results["documents"], results["metadatas"]
            ):
                items.append({
                    "id":        doc_id,
                    "fact":      doc,
                    "timestamp": meta.get("timestamp", ""),
                    "source":    meta.get("source", ""),
                })

            # Sắp xếp mới nhất trước
            items.sort(key=lambda x: x["timestamp"], reverse=True)
            return items

        except Exception as e:
            logger.error("Lỗi khi lấy danh sách memories: %s", e)
            return []

    def delete_memory(self, memory_id: str) -> bool:
        """
        Xóa fact theo ID.

        Args:
            memory_id: UUID của fact cần xóa.

        Returns:
            True nếu xóa thành công, False nếu không tìm thấy hoặc lỗi.
        """
        if not memory_id:
            return False
        try:
            self._collection.delete(ids=[memory_id])
            logger.info("Đã xóa memory ID: %s", memory_id)
            return True
        except Exception as e:
            logger.error("Lỗi khi xóa memory '%s': %s", memory_id, e)
            return False

    def get_stats(self) -> dict:
        """
        Thống kê tổng quan về trí nhớ.

        Returns:
            dict: {"total_facts", "oldest_timestamp", "newest_timestamp"}
        """
        try:
            total = self._collection.count()
            if total == 0:
                return {"total_facts": 0, "oldest_timestamp": None, "newest_timestamp": None}

            results = self._collection.get(include=["metadatas"], limit=total)
            timestamps = [
                m.get("timestamp", "") for m in results["metadatas"] if m.get("timestamp")
            ]
            timestamps.sort()

            return {
                "total_facts":       total,
                "oldest_timestamp":  timestamps[0]  if timestamps else None,
                "newest_timestamp":  timestamps[-1] if timestamps else None,
            }
        except Exception as e:
            logger.error("Lỗi khi lấy stats: %s", e)
            return {"total_facts": 0, "oldest_timestamp": None, "newest_timestamp": None}


# ═══════════════════════════════════════════════════════════════════════════════
#  Test độc lập — 4 unit tests
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import shutil
    import sys

    # Fix encoding cho Windows console
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    logging.basicConfig(
        level=logging.WARNING,  # Giảm noise khi test
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    TEST_DB_PATH = "src_brain/memory_rag/_test_db"

    # Dọn dẹp DB test cũ nếu có
    if os.path.exists(TEST_DB_PATH):
        shutil.rmtree(TEST_DB_PATH)

    print("=" * 55)
    print("  TEST rag_manager.py — ChromaDB RAG Unit Tests")
    print("=" * 55)

    rag = RAGManager(db_path=TEST_DB_PATH)
    passed = 0
    failed = 0

    # ── Test 1: Save ────────────────────────────────────────────────────────
    print("\n[Test 1] extract_and_save — lưu 3 facts...")
    ok1 = rag.extract_and_save("tên mình là An", "Bi nhớ rồi, bạn tên An!")
    ok2 = rag.extract_and_save("mình thích khủng long lắm", "Khủng long thật thú vị!")
    ok3 = rag.extract_and_save("mình có nuôi mèo tên Mimi", "Mèo Mimi nghe cute quá!")

    if ok1 and ok2 and ok3:
        print("  ✅ PASS — đã lưu 3 facts thành công")
        passed += 1
    else:
        print(f"  ❌ FAIL — ok1={ok1}, ok2={ok2}, ok3={ok3}")
        failed += 1

    # ── Test 2: Retrieve ─────────────────────────────────────────────────────
    print("\n[Test 2] retrieve — query 'tên bé là gì' phải chứa 'An'...")
    context = rag.retrieve("tên bé là gì")
    print(f"  Context: {repr(context)}")

    if "An" in context:
        print("  ✅ PASS — context có chứa 'An'")
        passed += 1
    else:
        print("  ❌ FAIL — context KHÔNG chứa 'An'")
        failed += 1

    # ── Test 3: List ─────────────────────────────────────────────────────────
    print("\n[Test 3] list_memories — phải có ít nhất 3 entries...")
    memories = rag.list_memories()
    print(f"  Số facts: {len(memories)}")
    for m in memories:
        print(f"    [{m['timestamp'][:19]}] {m['fact']}")

    if len(memories) >= 3:
        print("  ✅ PASS — có đủ 3 entries")
        passed += 1
    else:
        print(f"  ❌ FAIL — chỉ có {len(memories)} entries")
        failed += 1

    # ── Test 4: Delete ───────────────────────────────────────────────────────
    print("\n[Test 4] delete_memory — xóa 1 entry, list còn ít hơn...")
    if memories:
        del_id = memories[0]["id"]
        del_ok = rag.delete_memory(del_id)
        memories_after = rag.list_memories()
        print(f"  Sau xóa: {len(memories_after)} entries (trước: {len(memories)})")

        if del_ok and len(memories_after) < len(memories):
            print("  ✅ PASS — xóa thành công, danh sách giảm")
            passed += 1
        else:
            print(f"  ❌ FAIL — del_ok={del_ok}, trước={len(memories)}, sau={len(memories_after)}")
            failed += 1
    else:
        print("  ❌ FAIL — không có entry để xóa")
        failed += 1

    # ── Kết quả ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print(f"  Kết quả: {passed}/4 tests PASSED, {failed}/4 FAILED")
    print("=" * 55)

    # Dọn dẹp DB test — phải xóa client trước để giải phóng file lock ChromaDB
    del rag
    import gc
    gc.collect()
    if os.path.exists(TEST_DB_PATH):
        try:
            shutil.rmtree(TEST_DB_PATH)
        except PermissionError:
            print(f"  (Không xóa được {TEST_DB_PATH} do file lock — bỏ qua)")

    if failed > 0:
        sys.exit(1)
    print("\n✅ STEP 2 COMPLETE — rag_manager.py implemented, 6 methods")
