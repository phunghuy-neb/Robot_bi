import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src_brain.senses.ear_stt import EarSTT
from src_brain.senses.mouth_tts import MouthTTS
from src_brain.ai_core.core_ai import BiAI


class RobotBiApp:
    def __init__(self):
        self.ear = EarSTT()
        self.mouth = MouthTTS()
        self.brain = BiAI()
        print("[Hệ thống] Robot Bi đã khởi động và sẵn sàng!")

    def run(self):
        try:
            while True:
                user_text = self.ear.listen()
                if user_text is None or user_text == "":
                    continue
                print("[Bi - Não] Đang suy nghĩ...")
                ai_response = self.brain.chat(user_text)
                self.mouth.speak(ai_response)
        except KeyboardInterrupt:
            print("[Hệ thống] Robot Bi đang tắt. Tạm biệt!")


app = RobotBiApp()
app.run()
