"""
ear_stt.py — Module "Đôi Tai" của Robot Bi
Chức năng: Nhận diện giọng nói tiếng Việt (Speech-to-Text)
Thư viện: SpeechRecognition + PyAudio
"""

import speech_recognition as sr


class EarSTT:
    """
    Lớp đại diện cho "đôi tai" của Robot Bi.
    Lắng nghe microphone, lọc tạp âm, và chuyển giọng nói thành văn bản tiếng Việt.
    """

    LANGUAGE = "vi-VN"

    def __init__(self, energy_threshold: int = 300, pause_threshold: float = 0.8):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold

    def listen_and_transcribe(self) -> str | None:
        """
        Lắng nghe một câu từ microphone và trả về chuỗi văn bản tiếng Việt.

        Returns:
            str: Văn bản được nhận diện, hoặc None nếu thất bại.
        """
        with sr.Microphone() as source:
            print("Đang lọc tạp âm... (giữ yên lặng 1 giây)")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

            print("Bi đang nghe đây... (hãy nói ngay bây giờ)")
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
            except sr.WaitTimeoutError:
                print("Bi không nghe thấy gì — hết thời gian chờ.")
                return None

        print("Bi đang xử lý giọng nói...")
        try:
            text = self.recognizer.recognize_google(audio, language=self.LANGUAGE)
            print(f'Bi nghe được là: "{text}"')
            return text

        except sr.UnknownValueError:
            print("Bi không nghe rõ — bạn vui lòng nói lại nhé.")
            return None

        except sr.RequestError as e:
            print(f"Lỗi kết nối tới dịch vụ nhận diện giọng nói: {e}")
            return None


def listen_and_transcribe() -> str | None:
    """Hàm tiện ích — gọi trực tiếp mà không cần khởi tạo class."""
    ear = EarSTT()
    return ear.listen_and_transcribe()


if __name__ == "__main__":
    print("=" * 45)
    print("   Robot Bi — Module Nhận Diện Giọng Nói")
    print("=" * 45)
    ear = EarSTT()
    result = ear.listen_and_transcribe()
    print("-" * 45)
    if result:
        print(f"Kết quả cuối cùng: {result}")
    else:
        print("Kết quả cuối cùng: Không nhận diện được.")
    print("=" * 45)
