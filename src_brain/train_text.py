"""
train_text.py — Text sandbox: chat trực tiếp với Robot Bi trên terminal.
Không dùng mic hay loa. Chạy: python src_brain/train_text.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src_brain.ai_core.core_ai import stream_chat

history = []

print("Robot Bi — Text Sandbox (Groq Llama 70B / Gemini Flash-Lite)")
print("   Go 'thoat', 'exit' hoac 'quit' de ket thuc.\n")

try:
    while True:
        user_input = input("Ban: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ("thoat", "exit", "quit"):
            print("Bi: Tam biet ban nhe! Hen gap lai!")
            sys.exit(0)

        history.append({"role": "user", "content": user_input})

        print("Bi: ", end="", flush=True)
        full_reply = ""
        try:
            for token in stream_chat(history):
                full_reply += token
                print(token, end="", flush=True)
            print()
        except Exception as e:
            print(f"\nLoi: {e}")
            history.pop()
            continue

        if full_reply:
            history.append({"role": "assistant", "content": full_reply.strip()})

        # Sliding window: giu 10 luot gan nhat (20 messages)
        if len(history) > 20:
            history = history[-20:]

except KeyboardInterrupt:
    print("\nBi: Tam biet ban nhe! Hen gap lai!")
    sys.exit(0)
