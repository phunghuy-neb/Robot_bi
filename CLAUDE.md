# CLAUDE.md — Dự án Robot Bi (Gia sư AI Offline)

## 🎯 Mission
Xây dựng một Robot gia sư thông minh cho trẻ em (Bo). Hệ thống hoạt động 100% Offline trên máy tính cá nhân để đảm bảo quyền riêng tư tuyệt đối cho trẻ.

## 🏗️ Architecture
- Ngôn ngữ: Python 3.10+
- Tai (STT): SpeechRecognition
- Miệng (TTS): Edge-TTS (Chạy background queue)
- Não (LLM): Ollama (Model: Qwen 2.5 7B) - Streaming Mode
- Trí nhớ (RAG): ChromaDB + SentenceTransformers

## 🚫 Boundaries (Ranh giới tuyệt đối)
1. KHÔNG được gửi bất kỳ dữ liệu âm thanh/văn bản nào ra API bên ngoài (ngoại trừ Edge-TTS tạm thời chấp nhận).
2. Tốc độ phản hồi (Time to First Audio) phải < 2 giây. Luôn dùng Streaming kiến trúc.
3. KHÔNG tự ý thay đổi thư viện cốt lõi nếu không có trong handoff.md.

## 🔗 Context Files
Đọc `.claude/handoff.md` trước khi bắt đầu bất kỳ dòng code nào.