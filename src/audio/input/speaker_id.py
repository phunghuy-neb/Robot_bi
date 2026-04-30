class SpeakerIdentifier:
    KNOWN_ROLES = ["be", "bo", "me", "ong", "ba"]

    def identify(self, audio_features: dict) -> str:
        """
        Nhận biết vai trò người nói từ đặc trưng giọng.
        Returns: "be" | "me" | "bo" | "ong" | "ba" | "unknown"
        Dùng pitch analysis đơn giản:
        - Pitch cao + energy thấp → "be"
        - Pitch trung bình → "me"/"bo"
        - Pitch thấp → "ong"/"ba"
        """
        if not audio_features:
            return "unknown"
            
        pitch = audio_features.get("pitch", 0)
        energy = audio_features.get("energy", 0)
        
        # Simple heuristic mapping based on mock pitch ranges
        if pitch > 250:
            return "be"
        elif 180 <= pitch <= 250:
            return "me"
        elif 100 <= pitch < 180:
            return "bo"
        elif 80 <= pitch < 100:
            return "ong"
        elif pitch < 80 and pitch > 0:
            return "ba"
            
        return "unknown"

    def get_address_form(self, role: str) -> dict:
        """
        Trả về cách xưng hô phù hợp.
        VD: role="me" → {robot_self: "con", address: "mẹ"}
            role="be" → {robot_self: "Bi", address: "bạn"}
        """
        forms = {
            "be": {"robot_self": "Bi", "address": "bạn"},
            "me": {"robot_self": "con", "address": "mẹ"},
            "bo": {"robot_self": "con", "address": "bố"},
            "ong": {"robot_self": "cháu", "address": "ông"},
            "ba": {"robot_self": "cháu", "address": "bà"},
            "unknown": {"robot_self": "Bi", "address": "bạn"}
        }
        return forms.get(role, forms["unknown"])
