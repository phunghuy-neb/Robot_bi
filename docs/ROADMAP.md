# Robot Bi — Roadmap

## Trạng thái hiện tại
- Tests: 197/197 PASS
- Phase 1-4: FROZEN
- Phase 5.1: DONE (2026-04-29)

## Phase 5 — Màn hình Robot (Đang làm)

### 5.1 Refactor thư mục ✅ DONE (2026-04-29)
- `src_brain/` → `src/` theo cấu trúc domain
- DB: `runtime/robot_bi.db`, ChromaDB: `runtime/chroma_db/`
- Frontend: `frontend/parent_app/`
- Tests: `tests/run_tests.py`

### 5.2 Giao diện màn hình robot
- [ ] Mắt biểu cảm hoạt hình
- [ ] Trạng thái (nghe/nghĩ/nói/ngủ)
- [ ] Screensaver idle
- [ ] Đổi giao diện theo ngày lễ
- [ ] Animation khen thưởng

## Phase 6 — Cảm xúc & Tính cách

### 6.1 Tính cách cơ bản
- [ ] Tên robot + giới tính tùy chỉnh
- [ ] Giận dỗi khi bị bỏ mặc
- [ ] Vui mừng khi được chơi

### 6.2 Hành vi tự động
- [ ] Idle behavior (tự chơi, ngáp)
- [ ] Chỉ ngủ khi hết pin
- [ ] Chủ động tương tác khi bé im

### 6.3 Cảm xúc thông minh
- [ ] Nhận diện cảm xúc bé qua giọng
- [ ] Calm Mode
- [ ] Nhật ký cảm xúc
- [ ] Cảnh báo mẹ

## Phase 7 — Giáo dục

### 7.1 Flashcard engine
- [ ] Tất cả môn học
- [ ] Tất cả ngôn ngữ phổ biến
- [ ] Hiển thị trên màn hình robot

### 7.2 Luyện ngôn ngữ
- [ ] Phát âm đúng/sai
- [ ] Ngữ pháp + đặt câu
- [ ] Luyện nghe

### 7.3 Progress tracking
- [ ] Tiến độ học của bé
- [ ] Lịch học theo ngày
- [ ] Báo cáo tuần cho mẹ

## Phase 8 — Giải trí

### 8.1 Nhạc
- [ ] Nhạc thiếu nhi Việt/Anh offline
- [ ] Nhún nhảy theo nhạc
- [ ] Nhạc ru ngủ giảm dần
- [ ] Spotify/YouTube + báo bản quyền

### 8.2 Kể chuyện
- [ ] Có sẵn + tự sáng tác + cá nhân hóa
- [ ] Nhạc nền khi kể chuyện

### 8.3 Game
- [ ] Đố vui giọng nói
- [ ] Đố chữ/đố ảnh trên màn hình

## Phase 9 — Hardware

### 9.1 Motor control
- [ ] Di chuyển theo lệnh
- [ ] Tránh vật cản

### 9.2 Dock sạc tự động
- [ ] IR beacon
- [ ] Tự về dock khi hết pin
- [ ] Mẹ bấm app → về dock

### 9.3 Follow me
- [ ] Bám theo bé

### 9.4 Tương tác vật lý
- [ ] Cảm biến xoa đầu
- [ ] Nút SOS
- [ ] Giật mình khi đập bàn
- [ ] Sợ độ cao

### 9.5 AEC
- [ ] Echo cancellation

## Phase 10 — Kết nối

### 10.1 Gọi video
- [ ] Nhiều người cùng lúc
- [ ] Ông bà xem được

### 10.2 Swarm
- [ ] 2 robot kết nối WiFi
- [ ] Hành vi nhóm

### 10.3 Báo cáo & Analytics
- [ ] Báo cáo tuần tự động
- [ ] Biểu đồ hoạt động
- [ ] Thư viện clip sự kiện

## Tính năng đã xác nhận BỎ
- NFC Flashcard vật lý
- SLAM tự tìm đường phức tạp
- Mã hóa LUKS/BitLocker
- Đèn LED biểu cảm
- Barge-in
