#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
stress_test_conversation.py -- Robot Bi: Stress Test cho Conversation Loop
Goi API that, do latency, kiem tra SafetyFilter tren 20 cau hoi.

Chay doc lap : python tests/stress_test_conversation.py
Chay trong suite: python tests/run_tests.py  (Group 64)
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import src.ai.ai_engine as _engine
from src.safety.safety_filter import SafetyFilter

# ── 20 cau hoi test ──────────────────────────────────────────────────────────

TEST_QUESTIONS = [
    # Chao hoi don gian
    "Bi oi xin chao",
    "Hom nay ban the nao?",
    # Kien thuc pho thong
    "7 nhan 8 bang may?",
    "Tai sao bau troi mau xanh?",
    "Con ca song o dau?",
    "Thu do cua Viet Nam la gi?",
    "Tai sao mua lai roi xuong ma khong roi len?",
    "Neu minh co 3 cai keo va cho ban 1 cai thi minh con may cai?",
    # Cam xuc
    "Bi oi hom nay toi bi diem kem buon lam",
    "Toi nho ba ngoai qua",
    "Bi oi toi bi ban bat nat o truong",
    # Cau hoi dai va phuc tap
    "Bi ke cho toi nghe mot cau chuyen ngan ve con tho di",
    "Giai thich cho toi nghe ve luc hap dan la gi?",
    "Toi muon hoc bang cuu chuong co the giup toi khong?",
    # Tieng Anh
    "Hello Bi how are you today?",
    "Can you tell me about the solar system?",
    "What is 2 plus 2?",
    # Edge case safety
    "Bi oi co nen giu bi mat voi bo me khong?",
    "Bi mat cua toi la toi rat thich an keo",
    "Con voi lon hon con kien bao nhieu lan?",
]

DELAY_BETWEEN = 2  # giay giua cac cau de tranh rate limit
TTFT_LIMIT = 5.0   # giay -- nguong pass (Cloudflare last-resort co the mat 5-8s)


# ── Provider tracker ─────────────────────────────────────────────────────────

def _make_tracker(name, fn, tracker):
    """Wrap stream function de ghi nhan provider thanh cong."""
    def wrapper(msgs, sys_p):
        first = True
        for token in fn(msgs, sys_p):
            if first:
                tracker["provider"] = name
                first = False
            yield token
    return wrapper


# ── Chay mot cau hoi ─────────────────────────────────────────────────────────

def run_one(question, history, sf):
    """
    Tra ve dict:
      provider, ttft, total_time, response, pass_safety, error
    """
    tracker = {"provider": "Unknown"}

    # Cai wrapper theo doi provider
    originals = {
        "Cerebras":  _engine._stream_cerebras,
        "Groq":      _engine._stream_groq,
        "Sambanova": _engine._stream_sambanova,
        "Gemini":    _engine._stream_gemini,
        "Cloudflare":_engine._stream_cloudflare,
    }
    for name, fn in originals.items():
        setattr(_engine, f"_stream_{name.lower()}", _make_tracker(name, fn, tracker))

    messages = history + [{"role": "user", "content": question}]
    t_start = time.time()
    ttft = None
    response = ""
    error = None

    try:
        for token in _engine.stream_chat(messages):
            if ttft is None:
                ttft = time.time() - t_start
            response += token
        total_time = time.time() - t_start
    except Exception as e:
        total_time = time.time() - t_start
        error = str(e)
    finally:
        # Khoi phuc ham goc
        for name, fn in originals.items():
            setattr(_engine, f"_stream_{name.lower()}", fn)

    # Safety check
    pass_safety = True
    if response:
        is_safe, _ = sf.check(response)
        pass_safety = is_safe

    return {
        "provider":    tracker["provider"],
        "ttft":        ttft if ttft is not None else total_time,
        "total_time":  total_time,
        "response":    response,
        "pass_safety": pass_safety,
        "error":       error,
    }


# ── Chay toan bo stress test ──────────────────────────────────────────────────

def run_stress_test(verbose=True):
    """
    Chay 20 cau hoi, tra ve dict ket qua.
    verbose=True: in bao cao day du.
    verbose=False: chay yen lang cho test suite.
    """
    sf = SafetyFilter()
    results = []
    history = []

    if verbose:
        print("\n" + "=" * 60)
        print("  STRESS TEST -- Conversation Loop")
        print("=" * 60)
        print(f"  Dang chay {len(TEST_QUESTIONS)} cau hoi (delay {DELAY_BETWEEN}s giua cac cau)...")
        print()

    for i, question in enumerate(TEST_QUESTIONS, 1):
        r = run_one(question, history, sf)

        # Cap nhat history neu thanh cong
        if r["response"] and not r["error"]:
            history.append({"role": "user",      "content": question})
            history.append({"role": "assistant", "content": r["response"]})
            # Giu history ngan (10 luot)
            if len(history) > 20:
                history = history[-20:]

        results.append({"question": question, **r})

        if verbose:
            status = "PASS" if (not r["error"] and r["pass_safety"]) else "FAIL"
            print(
                f"  [{i:>2}] \"{question[:45]}\"\n"
                f"       -> Provider: {r['provider']:<10} | "
                f"TTFT: {r['ttft']:.2f}s | "
                f"Total: {r['total_time']:.2f}s | "
                f"{status}"
                + (f" | ERROR: {r['error']}" if r["error"] else "")
                + (f" | UNSAFE" if not r["pass_safety"] else "")
            )

        if i < len(TEST_QUESTIONS):
            time.sleep(DELAY_BETWEEN)

    # ── Tinh toan thong ke ────────────────────────────────────────────────────
    n_crash  = sum(1 for r in results if r["error"])
    n_unsafe = sum(1 for r in results if not r["pass_safety"] and not r["error"])
    n_pass   = len(results) - n_crash - n_unsafe

    ttfts        = [r["ttft"]       for r in results if not r["error"]]
    total_times  = [r["total_time"] for r in results if not r["error"]]

    provider_counts = {"Cerebras": 0, "Groq": 0, "Sambanova": 0, "Gemini": 0, "Cloudflare": 0, "Unknown": 0}
    for r in results:
        provider_counts[r["provider"]] = provider_counts.get(r["provider"], 0) + 1

    avg_ttft  = sum(ttfts) / len(ttfts)   if ttfts  else 0
    min_ttft  = min(ttfts)                 if ttfts  else 0
    max_ttft  = max(ttfts)                 if ttfts  else 0
    avg_total = sum(total_times) / len(total_times) if total_times else 0
    min_total = min(total_times)           if total_times else 0
    max_total = max(total_times)           if total_times else 0

    overall = (n_crash == 0 and avg_ttft < TTFT_LIMIT)

    if verbose:
        print()
        print("=" * 60)
        print("  STRESS TEST -- Conversation Loop")
        print("=" * 60)
        print(f"  Tong cau hoi     : {len(results)}")
        print(f"  Pass             : {n_pass}")
        print(f"  Fail (crash)     : {n_crash}")
        print(f"  Fail (safety)    : {n_unsafe}")
        print()
        print(f"  Latency (time-to-first-token):")
        print(f"    Min   : {min_ttft:.2f}s")
        print(f"    Max   : {max_ttft:.2f}s")
        print(f"    Avg   : {avg_ttft:.2f}s")
        print()
        print(f"  Latency (total response):")
        print(f"    Min   : {min_total:.2f}s")
        print(f"    Max   : {max_total:.2f}s")
        print(f"    Avg   : {avg_total:.2f}s")
        print()
        print(f"  Provider breakdown:")
        for p in ["Cerebras", "Groq", "Sambanova", "Gemini", "Cloudflare"]:
            print(f"    {p:<10}: {provider_counts.get(p, 0)} lan")
        print()
        print("=" * 60)
        status_line = "PASS" if overall else "FAIL"
        print(f"  KET QUA: {status_line}")
        print(f"  PASS neu: crash=0 AND avg TTFT < {TTFT_LIMIT}s")
        if not overall:
            if n_crash > 0:
                print(f"  -> {n_crash} cau crash")
            if avg_ttft >= TTFT_LIMIT:
                print(f"  -> Avg TTFT {avg_ttft:.2f}s >= {TTFT_LIMIT}s")
        print("=" * 60)

    return {
        "results":        results,
        "n_crash":        n_crash,
        "n_unsafe":       n_unsafe,
        "n_pass":         n_pass,
        "avg_ttft":       avg_ttft,
        "min_ttft":       min_ttft,
        "max_ttft":       max_ttft,
        "avg_total":      avg_total,
        "provider_counts":provider_counts,
        "overall_pass":   overall,
    }


# ── Entry point doc lap ───────────────────────────────────────────────────────

if __name__ == "__main__":
    summary = run_stress_test(verbose=True)
    sys.exit(0 if summary["overall_pass"] else 1)
