"""
train_text.py — Text sandbox: chat trực tiếp với Qwen 2.5:1.5b trên terminal.
Không dùng mic hay loa. Chạy: python train_text.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import ollama
from src_brain.ai_core.prompts import MAIN_SYSTEM_PROMPT as _SYSTEM_PROMPT

MODEL = "qwen2.5:7b"

conversation_history = [{"role": "system", "content": _SYSTEM_PROMPT}]

print(f"🤖 Robot Bi — Text Sandbox ({MODEL})")
print("   Gõ 'thoát', 'exit' hoặc 'quit' để kết thúc.\n")

try:
    while True:
        user_input = input("👦 Bạn: ").strip()

        if not user_input:
            continue

        # Thoát sạch khi người dùng gõ lệnh thoát
        if user_input.lower() in ("thoát", "exit", "quit"):
            print("🤖 Bi: Tạm biệt bạn nhé! Hẹn gặp lại!")
            sys.exit(0)

        conversation_history.append({"role": "user", "content": user_input})

        try:
            response = ollama.chat(model=MODEL, messages=conversation_history)
            reply = response["message"]["content"].strip()
        except ollama.ResponseError as e:
            print(f"❌ Lỗi model: {e}\n   Hãy chạy: ollama pull {MODEL}")
            conversation_history.pop()  # Huỷ user message vừa append vì không có reply
            continue
        except ConnectionRefusedError:
            print("❌ Không kết nối được Ollama. Hãy chạy: ollama serve")
            conversation_history.pop()
            continue

        print(f"🤖 Bi: {reply}\n")

        conversation_history.append({"role": "assistant", "content": reply})

        # Sliding window: giữ system prompt (index 0) + 20 phần tử cuối (10 lượt)
        if len(conversation_history) > 21:
            conversation_history = [conversation_history[0]] + conversation_history[-20:]

except KeyboardInterrupt:
    print("\n🤖 Bi: Tạm biệt bạn nhé! Hẹn gặp lại!")
    sys.exit(0)
