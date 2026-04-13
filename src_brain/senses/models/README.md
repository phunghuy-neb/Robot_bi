# Models Directory

Đặt file `yamnet.tflite` vào thư mục này để bật YAMNet cry detection.

## Download YAMNet model

```bash
# Tải về thủ công (khoảng 3.5MB):
# https://storage.googleapis.com/mediapipe-assets/yamnet.tflite

# Hoặc dùng curl:
curl -L -o src_brain/senses/models/yamnet.tflite \
  https://storage.googleapis.com/mediapipe-assets/yamnet.tflite
```

Sau khi download, `yamnet.tflite` phải nằm ở:
```
src_brain/senses/models/yamnet.tflite
```

**Kích thước:** ~3.5MB  
**Chạy offline:** hoàn toàn — chỉ cần download 1 lần  
**Fallback:** Nếu không có file này, CryDetector tự động dùng energy+ZCR detection (không cần model)
