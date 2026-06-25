# WAKEWORD_DATASET_GUIDE.md — Hướng Dẫn Thu Dataset "Bi ơi"

> Phiên bản: 1.0 | Robot Bi Sprint 0.3
>
> File này hướng dẫn user thu âm dataset để train custom wake word "Bi ơi"
> cho Robot Bi sử dụng openWakeWord framework.
>
> **Không cần kỹ thuật chuyên sâu.** Chỉ cần điện thoại có mic.

---

## Tại sao cần dataset?

Wake word "Bi ơi" là tên riêng — không có trong bất kỳ pre-trained model nào.
Để robot nhận ra đúng, cần train một model nhỏ chuyên biệt với:
- **Positive samples**: Nhiều cách nói "Bi ơi" khác nhau
- **Negative samples**: Mọi âm thanh khác (không phải wake word)

---

## Yêu cầu tối thiểu

| Loại         | Tối thiểu | Lý tưởng |
|---|---|---|
| Positive (có "Bi ơi") | 50 file | 100–150 file |
| Negative (không có)   | 100 file | 200+ file |

Dưới 50 positive → model sẽ không đủ tin cậy.

---

## Cấu trúc thư mục

```
data/
└── wakeword/
    ├── positive/          ← file WAV chứa "Bi ơi"
    │   ├── bi_oi_001.wav
    │   ├── bi_oi_002.wav
    │   └── ...
    └── negative/          ← file WAV KHÔNG chứa "Bi ơi"
        ├── neg_001.wav
        ├── neg_002.wav
        └── ...
```

Tạo thư mục:
```bash
mkdir -p data/wakeword/positive data/wakeword/negative
```

---

## 1. POSITIVE SAMPLES — "Bi ơi"

### Bao nhiêu sample?
- **Tối thiểu: 50 file**
- **Lý tưởng: 100–150 file**
- Mỗi file: 1 lần nói "Bi ơi" (có thể thêm khoảng lặng trước/sau ~0.5s)

### Các variation cần thu

Thu đủ các variation sau để model robust:

#### Người nói (ít nhất 2–3 người khác nhau)
- [ ] Trẻ em (5–10 tuổi) — người dùng chính
- [ ] Người lớn giọng nữ (mẹ, cô)
- [ ] Người lớn giọng nam (bố, chú)

#### Tốc độ
- [ ] Bình thường: "Bi ơi" (tự nhiên)
- [ ] Nhanh: "Biơi" (gọi nhanh)
- [ ] Chậm: "Bi... ơi" (gọi kéo dài)

#### Âm lượng / khoảng cách mic
- [ ] Gần mic (0.5m): giọng bình thường
- [ ] Xa mic (1.5–2m): giọng bình thường hoặc to hơn chút
- [ ] Thì thầm: "Bi ơi" (nhỏ nhẹ)
- [ ] To: "Bi ơi!" (gọi to)

#### Cảm xúc / ngữ điệu
- [ ] Bình thường: tự nhiên, nhẹ nhàng
- [ ] Vui vẻ: "Bi ơi!" hào hứng
- [ ] Buồn / mệt: "Bi ơi..." nhẹ, chậm
- [ ] Tò mò: ngữ điệu hỏi nhẹ
- [ ] Trong lúc nói chuyện: thêm vào giữa câu ("à, Bi ơi, con muốn hỏi...")

#### Biến thể phát âm (phương ngữ)
- [ ] "Bi ơi" (chuẩn, miền Bắc)
- [ ] "Bi ui" (miền Nam)
- [ ] "Bi hơi" (lỡ lời, nói nhanh)
- [ ] Nhấn âm khác nhau: "BI ơi" / "bi ƠI"

#### Nền âm thanh (thu ở các môi trường khác nhau)
- [ ] Phòng yên tĩnh
- [ ] Phòng có tiếng TV nhỏ
- [ ] Bếp có tiếng nước / nấu ăn
- [ ] Phòng ngủ buổi tối (hơi vang)

### Script gợi ý khi thu

Đọc theo danh sách này, mỗi dòng = 1 file:
```
1.  "Bi ơi"
2.  "Bi ơi" (nhanh)
3.  "Bi ơi" (chậm)
4.  "Bi ơi" (thì thầm)
5.  "Bi ơi!" (to)
6.  "Bi ơi con muốn hỏi" (thêm context phía sau)
7.  "Ơ Bi ơi" (thêm từ phía trước)
8.  "Bi ui" (biến thể Nam)
9.  "Bi hơi" (nói nhanh)
10. "Bi ơi" (giọng mệt)
... lặp lại với người khác, môi trường khác
```

---

## 2. NEGATIVE SAMPLES — "Không phải Bi ơi"

### Bao nhiêu sample?
- **Tối thiểu: 100 file**
- **Lý tưởng: 200+ file**
- Càng đa dạng càng tốt

### Nguồn âm thanh negative

Thu hoặc dùng các clip sẵn có:

#### Tiếng người (không nói "Bi ơi")
- [ ] Hội thoại bình thường trong nhà
- [ ] Kể chuyện, đọc sách cho bé
- [ ] Các tên khác: "Mèo ơi", "chó ơi", "bé ơi", "con ơi"
- [ ] Từ gần âm: "về ơi", "đi ơi", "mi ơi", "ti ơi"
- [ ] Tiếng Anh nói chuyện
- [ ] Câu hỏi thông thường: "Hôm nay ăn gì?", "Con làm bài chưa?"
- [ ] Tiếng khóc, cười, hắt hơi

#### Tiếng TV / thiết bị
- [ ] TV tiếng Việt (phim, tin tức, hoạt hình)
- [ ] Nhạc thiếu nhi
- [ ] Nhạc người lớn
- [ ] Giọng robot / AI khác
- [ ] Thông báo điện thoại

#### Tiếng môi trường
- [ ] Tiếng xe cộ bên ngoài
- [ ] Tiếng quạt, điều hòa
- [ ] Tiếng nước chảy, nấu ăn
- [ ] Tiếng chó mèo
- [ ] Im lặng (noise floor)

### Nguồn negative sẵn có
OpenWakeWord cung cấp bộ negative samples lớn. Dùng lệnh:
```bash
python -m openwakeword.download_positive_clips --language vi
# hoặc tải về: https://github.com/dscripka/openWakeWord/releases
```

---

## 3. Định dạng audio

| Thông số | Yêu cầu |
|---|---|
| Format | WAV (không nén) |
| Sample rate | **16000 Hz** (16kHz) — bắt buộc |
| Channels | **Mono** (1 channel) |
| Bit depth | 16-bit PCM |
| Độ dài | 1–3 giây (positive), 1–5 giây (negative) |

### Chuyển đổi file từ điện thoại

Nếu điện thoại thu M4A/MP3:
```bash
# Cài ffmpeg (miễn phí)
# Windows: winget install ffmpeg
# macOS: brew install ffmpeg

# Chuyển đổi 1 file:
ffmpeg -i input.m4a -ar 16000 -ac 1 -c:a pcm_s16le output.wav

# Chuyển đổi cả thư mục:
for f in *.m4a; do ffmpeg -i "$f" -ar 16000 -ac 1 -c:a pcm_s16le "${f%.m4a}.wav"; done
```

---

## 4. Thu âm bằng điện thoại

### Cách đơn giản nhất

1. **Mở app ghi âm** có sẵn trên điện thoại (Voice Recorder / Ghi âm)
2. **Đặt điện thoại** cách miệng ~50cm (không cầm sát tai)
3. Ghi âm, nói "Bi ơi" 1 lần, dừng
4. Lưu file, đặt tên theo convention (xem bên dưới)
5. Lặp lại cho mỗi variation

### Naming convention

```
positive/
  bi_oi_{người}_{variation}_{số}.wav
  
  Ví dụ:
  bi_oi_child_normal_001.wav
  bi_oi_child_fast_002.wav
  bi_oi_adult_f_whisper_001.wav
  bi_oi_adult_m_loud_001.wav

negative/
  neg_{nguồn}_{số}.wav
  
  Ví dụ:
  neg_tv_001.wav
  neg_speech_001.wav
  neg_noise_001.wav
  neg_similar_words_001.wav
```

### App thu âm gợi ý (miễn phí)
- **Android**: RecForge II, Easy Voice Recorder
- **iOS**: Voice Memos (sẵn có), RecForge II
- **PC**: Audacity (miễn phí, có thể export WAV 16kHz)

---

## 5. Kiểm tra chất lượng trước khi train

Chạy script kiểm tra:
```bash
python tests/wakeword_test_harness.py --check-dataset
```

Script sẽ báo:
- Số file positive / negative
- File nào sai format
- File nào quá ngắn / quá dài
- Phân phối độ dài

---

## 6. Training

Sau khi có đủ dataset:

```bash
# Cài openWakeWord (1 lần)
pip install openwakeword

# Train
python -m openwakeword.train \
    --positive_dir data/wakeword/positive \
    --negative_dir data/wakeword/negative \
    --output_dir runtime/wakeword \
    --model_name bi_oi \
    --num_epochs 100

# Output: runtime/wakeword/bi_oi.tflite
```

Training time: ~5–15 phút trên CPU thông thường.

---

## 7. Test model sau training

```bash
python tests/wakeword_test_harness.py --test-model \
    --model runtime/wakeword/bi_oi.tflite \
    --positive_dir data/wakeword/positive \
    --negative_dir data/wakeword/negative
```

Mục tiêu:
- True Positive Rate (TPR) ≥ 85%
- False Positive Rate (FPR) ≤ 5%

Nếu chưa đạt: thêm samples và retrain.

---

## 8. Kích hoạt trong robot

Sau khi có model:
```bash
# Trong .env:
WAKEWORD_ENABLED=true
WAKEWORD_BACKEND=openwakeword
WAKEWORD_MODEL_PATH=runtime/wakeword/bi_oi.tflite
WAKEWORD_THRESHOLD=0.5
```

Test nhanh:
```bash
python -c "
from src.wakeword.wakeword_service import WakeWordService
svc = WakeWordService()
svc.start()
print('Nói Bi ơi để test...')
detected = svc.wait_for_detection(timeout=10)
print('Detected!' if detected else 'Timeout')
"
```

---

## Checklist tóm tắt

```
[ ] 50+ positive WAV (16kHz mono)
[ ] 100+ negative WAV (16kHz mono)
[ ] Có ít nhất 2 người nói khác nhau trong positive
[ ] Có variation: bình thường, nhanh, chậm, thì thầm, to
[ ] Có variation: môi trường khác nhau (yên tĩnh, có TV, ...)
[ ] File đúng format (kiểm tra với test harness)
[ ] Training chạy thành công
[ ] TPR ≥ 85%, FPR ≤ 5%
[ ] .env cập nhật WAKEWORD_ENABLED=true
```

---

*Câu hỏi? Đọc thêm: https://github.com/dscripka/openWakeWord*
