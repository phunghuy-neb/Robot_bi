import speech_recognition as sr


class EarSTT:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()

    def listen(self):
        try:
            with self.mic as source:
                print("[Bi - Tai] Đang đo tiếng ồn môi trường...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("[Bi - Tai] Đã sẵn sàng! Bạn hãy nói gì đó đi...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                text = self.recognizer.recognize_google(audio, language="vi-VN")
                return text.lower()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            print("[Bi - Tai] Lỗi: Không thể kết nối đến dịch vụ nhận dạng giọng nói.")
            return ""


if __name__ == "__main__":
    ear = EarSTT()
    while True:
        result = ear.listen()
        print(f"[Bi - Tai] Nghe được: {result}")
