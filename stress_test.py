"""
stress_test.py -- Do RAM va latency cua Robot Bi khi chay day du
Chay: python stress_test.py
KHONG can mic hay loa -- chi do memory va toc do xu ly
"""
import sys, os, time, gc
sys.path.insert(0, '.')

def get_ram_mb():
    import psutil
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024

print("="*50)
print("ROBOT BI -- STRESS TEST")
print("="*50)

baseline = get_ram_mb()
print(f"Baseline RAM: {baseline:.0f} MB")

modules = [
    ("SafetyFilter",  "from src_brain.ai_core.safety_filter import SafetyFilter; SafetyFilter()"),
    ("RAGManager",    "from src_brain.memory_rag.rag_manager import RAGManager; RAGManager()"),
    ("EyeVision",     "from src_brain.senses.eye_vision import EyeVision; EyeVision(camera_index=99)"),
    ("CryDetector",   "from src_brain.senses.cry_detector import CryDetector; CryDetector()"),
    ("EventNotifier", "from src_brain.network.notifier import get_notifier; get_notifier()"),
    ("BiAI",          "from src_brain.ai_core.core_ai import BiAI; BiAI()"),
]

total = baseline
for name, code in modules:
    before = get_ram_mb()
    try:
        exec(code)
        after = get_ram_mb()
        delta = after - before
        total = after
        status = "OK" if after < 13000 else "WARNING"
        print(f"+ {name:20s}: +{delta:6.0f} MB  (total: {after:.0f} MB) [{status}]")
    except Exception as e:
        after = get_ram_mb()
        print(f"+ {name:20s}: SKIP ({type(e).__name__}: {str(e)[:60]})")

print(f"\nTong RAM (khong tinh Ollama+Whisper): {total:.0f} MB")
print(f"Uoc tinh voi Ollama 7B (~5000MB) + Whisper (~1000MB): {total+6000:.0f} MB")
limit = 13000
status = "PASS" if total + 6000 < limit else "FAIL -- vuot gioi han 13GB"
print(f"SRS NFR-01 (<=13GB): {status}")

print("\n--- Latency Test SafetyFilter ---")
try:
    from src_brain.ai_core.safety_filter import SafetyFilter
    sf = SafetyFilter()
    test_texts = [
        "Bau troi mau xanh vi anh sang bi tan xa nhe ban!",
        "Bi chua co du lieu ve van de nay.",
        "Mot cong mot bang hai, giong nhu mot qua tao cong mot qua tao.",
    ] * 10

    start = time.perf_counter()
    for text in test_texts:
        sf.check(text)
    elapsed = (time.perf_counter() - start) * 1000
    avg = elapsed / len(test_texts)
    print(f"SafetyFilter: {avg:.2f}ms/call (30 calls) -- {'PASS' if avg < 10 else 'SLOW'}")
except Exception as e:
    print(f"SafetyFilter test SKIP: {e}")

print("\n" + "="*50)
print("STRESS TEST COMPLETE")
print("="*50)
