# HARDWARE.md — Phần Cứng Robot Bi

> Phiên bản: 1.0 | Cập nhật: 2026-05-15
> File này mô tả linh kiện, kiến trúc phần cứng, và ghi chú lắp ráp.
> Cập nhật khi mua linh kiện mới, thay thế component, hoặc thay đổi wiring.
> Cho software implementation liên quan đến phần cứng, xem `PROJECT.md` và `SYSTEM_MAP.md`.

---

## 1. Tổng Quan Kiến Trúc

Robot Bi gồm 2 khối tính toán phối hợp:

```
┌─────────────────────────────────┐         ┌──────────────────────────────┐
│         PC / Laptop             │         │        Thân Robot            │
│  - Brain: AI, API, STT, TTS     │◄──WiFi──►│  ESP32 #1 (Motor)           │
│  - Parent App web server        │         │  ESP32 S3 #2 (Audio + WiFi) │
│  - ChromaDB, SQLite             │         │  ESP32-CAM #3 (Camera)      │
│  - GPU: RTX 2060 Super          │         │  Màn hình SPI               │
│  - RAM: 16GB                    │         │  Loa MAX98357               │
└─────────────────────────────────┘         │  Mic INMP441 x2             │
                                            │  Motor + L298N              │
                                            │  Pin 18650 x3               │
                                            └──────────────────────────────┘
```

**Nguyên tắc phân vai**:
- PC làm toàn bộ AI processing — STT, LLM, TTS, Safety Filter, Vision AI
- ESP32 chỉ làm I/O — nhận lệnh từ PC, điều khiển phần cứng, gửi data về
- Giao tiếp PC ↔ Robot qua WebSocket trên WiFi nội bộ

---

## 2. Linh Kiện Hiện Có ✅

### 2.1 Máy tính (Brain)
| Component | Specs | Ghi chú |
|---|---|---|
| PC/Laptop | RAM 16GB, GPU RTX 2060 Super | Chạy toàn bộ AI stack |
| OS | Windows | Xem `PROJECT.md` cho software stack |

### 2.2 Vi điều khiển
| Component | Model | Vai trò |
|---|---|---|
| ESP32 #1 | ESP32 (standard) | Điều khiển motor L298N |
| ESP32 #2 | ESP32-S3 | Audio (loa + mic) + WiFi hub + màn hình |

**Lưu ý ESP32-S3**: Chip này có đủ sức mạnh để chạy LVGL render UI cho màn hình, xử lý I2S audio (INMP441 + MAX98357), và duy trì WebSocket với PC đồng thời.

### 2.3 Audio
| Component | Model | Ghi chú |
|---|---|---|
| Microphone | INMP441 x2 | I2S digital mic, kết nối ESP32-S3 |
| Loa + Ampli | MAX98357 | I2S amplifier, kết nối ESP32-S3 |

**Wiring INMP441 → ESP32-S3**:
```
INMP441    ESP32-S3
VDD    →   3.3V
GND    →   GND
SD     →   GPIO (I2S DATA IN)
SCK    →   GPIO (I2S CLK)
WS     →   GPIO (I2S WS)
L/R    →   GND (mic trái) / 3.3V (mic phải)
```

**Wiring MAX98357 → ESP32-S3**:
```
MAX98357   ESP32-S3
VIN    →   5V
GND    →   GND
DIN    →   GPIO (I2S DATA OUT)
BCLK   →   GPIO (I2S CLK)
LRC    →   GPIO (I2S WS)
```

### 2.4 Motor và Di Chuyển
| Component | Model | Ghi chú |
|---|---|---|
| Motor driver | L298N | Điều khiển 2 motor DC |
| Vi điều khiển motor | ESP32 #1 | Nhận lệnh WebSocket từ PC |
| Khung | Kit mô hình xe ô tô | Tạm thời để test, sẽ in 3D sau |
| Bánh xe | Theo kit hiện tại | Sẽ thay sau khi có khung 3D |

**Firmware**: `firmware/Robot_BI/Robot_BI.ino`

### 2.5 Nguồn Điện
| Component | Specs | Ghi chú |
|---|---|---|
| Pin | 18650 x3 (11.1V nominal) | Tạm thời, sẽ thay pin phù hợp hơn |
| Hạ áp (Buck converter) | 1 cái | Hạ từ 11.1V xuống 5V cho ESP32 và logic |

**Lưu ý nguồn**:
- L298N cần 6-12V cho motor → kết nối thẳng từ pin 18650
- ESP32, màn hình, audio → cần 3.3V/5V từ buck converter
- PC/Laptop dùng nguồn riêng, không lấy từ pin robot

---

## 3. Linh Kiện Cần Mua ⬜

### 3.1 Màn Hình — CHƯA CÓ

**Yêu cầu**:
- Kích thước: 3.5–4 inch
- Hướng: landscape (ngang)
- Không cần touchscreen
- Giao thức: SPI (tương thích ESP32-S3)
- Dùng để: hiển thị mặt biểu cảm, flashcard, video call

**Recommendation**:

| Option | Model | Kích thước | Ghi chú |
|---|---|---|---|
| ⭐ Tốt nhất | ILI9488 3.5" SPI TFT | 3.5" | 480x320, màu đẹp, driver phổ biến |
| Thay thế | ST7796 4" SPI TFT | 4.0" | 320x480, lớn hơn chút |
| Budget | ILI9341 3.2" SPI | 3.2" | 240x320, rẻ nhất, resolution thấp hơn |

**Recommendation cho Eilik-style** (màn hình hình chữ nhật đứng như robot Eilik):
- ILI9488 3.5" có thể xoay 90° trong firmware → dùng được cả landscape và portrait
- Tìm thêm: "ESP32 round display" nếu muốn màn hình tròn như Vector

**Wiring màn hình SPI → ESP32-S3**:
```
TFT Display   ESP32-S3
VCC       →   3.3V
GND       →   GND
CS        →   GPIO (SPI CS)
RESET     →   GPIO
DC/RS     →   GPIO
MOSI      →   GPIO (SPI MOSI)
SCK       →   GPIO (SPI CLK)
LED/BL    →   3.3V hoặc GPIO (backlight control)
```

### 3.2 Camera — CHƯA CÓ

**Yêu cầu**:
- Gắn trên thân robot
- Stream video về PC qua WiFi
- PC xử lý AI (follow me, motion detection, video call)
- Không cần xử lý AI trên camera

**Recommendation**:

| Option | Model | Ghi chú |
|---|---|---|
| ⭐ Tốt nhất | ESP32-CAM (OV2640) | Module tích hợp sẵn, stream MJPEG qua WiFi, rẻ |
| Nâng cấp | ESP32-S3-EYE | S3 chip mạnh hơn, có mic tích hợp, giá cao hơn |

**Lưu ý ESP32-CAM**:
- Module này có ESP32 riêng — là ESP32 thứ 3 trong hệ thống
- Stream MJPEG về PC qua HTTP, PC dùng OpenCV để xử lý
- Cần nguồn 5V ổn định (dễ crash nếu nguồn yếu)
- Nên dùng thêm module FTDI để nạp firmware lần đầu

### 3.3 Linh Kiện Phụ — CHƯA CÓ

| Component | Số lượng gợi ý | Dùng cho |
|---|---|---|
| Tụ điện 100µF 16V | 5-10 cái | Lọc nguồn cho motor, tránh nhiễu audio |
| Tụ điện 0.1µF ceramic | 10-20 cái | Bypass cap cho IC |
| Điện trở 10kΩ | 10 cái | Pull-up/pull-down |
| Điện trở 1kΩ | 10 cái | LED, general purpose |
| LED indicator | 5-10 cái | Debug, status |
| Breadboard | 1-2 cái | Prototyping |
| Dây jumper male-male | 40 cái | Kết nối |
| Dây jumper male-female | 40 cái | Kết nối module |
| Header pin 2.54mm | 5-10 dải | Kết nối PCB |
| Công tắc nguồn | 1 cái | Tắt mở robot |
| Jack nguồn DC 5.5mm | 2-3 cái | Sạc pin |

### 3.4 Khung Robot và Cơ Khí — TƯƠNG LAI

| Item | Ghi chú |
|---|---|
| Khung in 3D | Thiết kế sau khi confirm tất cả component sizes |
| Bánh xe phù hợp khung | Chọn sau khi có khung |
| Pin tốt hơn | Li-ion pack hoặc LiPo phù hợp kích thước khung |
| BMS (Battery Management System) | Bảo vệ pin, sạc an toàn |
| Dock sạc | Tự về dock khi pin yếu — feature tương lai |

---

## 4. Kiến Trúc Giao Tiếp

```
PC (Brain)
│
├── WebSocket Server
│   ├── ESP32 #1 (Motor) ──────── L298N ── Motor trái/phải
│   ├── ESP32-S3 #2 (Audio)
│   │   ├── I2S IN ─── INMP441 x2 (Mic)
│   │   ├── I2S OUT ── MAX98357 (Loa)
│   │   └── SPI ────── Màn hình TFT
│   └── ESP32-CAM #3 (Camera)
│       └── HTTP MJPEG stream → PC OpenCV
│
├── FastAPI Server (Parent App)
│   └── Browser ← HTTPS/WSS
│
└── Cloudflare Tunnel (Remote access)
```

**Protocols**:
| Kết nối | Protocol | Ghi chú |
|---|---|---|
| PC ↔ ESP32 Motor | WebSocket over WiFi | Lệnh di chuyển |
| PC ↔ ESP32-S3 | WebSocket over WiFi | Audio commands, display commands |
| PC ↔ ESP32-CAM | HTTP MJPEG | Camera stream |
| PC ↔ Browser | HTTPS + WebSocket | Parent App |
| ESP32-S3 ↔ INMP441 | I2S | Digital audio in |
| ESP32-S3 ↔ MAX98357 | I2S | Digital audio out |
| ESP32-S3 ↔ Màn hình | SPI | Display |

---

## 5. Lưu Ý Quan Trọng

### Nguồn điện
- Motor DC khi khởi động có thể gây voltage drop lớn → tụ 100µF song song với nguồn motor
- ESP32 và audio rất nhạy cảm với nhiễu từ motor → tách nguồn riêng qua buck converter
- ESP32-CAM cần nguồn 5V ổn định, dòng ít nhất 500mA

### Audio
- INMP441 là I2S mic, không phải analog → không cần ADC, chất lượng tốt hơn
- 2 mic có thể dùng cho beamforming đơn giản (giảm tiếng ồn môi trường)
- MAX98357 là class D amp, hiệu suất cao, ít tỏa nhiệt

### Màn hình
- SPI tốc độ cao để animation mượt — cần set SPI clock phù hợp trong firmware
- LVGL là thư viện UI tốt nhất cho ESP32 + TFT, có nhiều widget sẵn cho face animation
- Backlight control qua PWM để điều chỉnh độ sáng theo môi trường

### Camera
- ESP32-CAM cần FTDI adapter để nạp firmware lần đầu (không có USB chip tích hợp)
- Stream MJPEG về PC, PC dùng OpenCV để xử lý — không xử lý AI trên camera
- Góc camera nên hướng về phía bé, không phải hướng lên trời

---

## 6. Trạng Thái Hiện Tại

| Hạng mục | Trạng thái |
|---|---|
| PC Brain + Software | ✅ Hoạt động |
| ESP32 #1 Motor + L298N | ✅ Có firmware, đang test với kit xe |
| ESP32-S3 Audio | 🔧 Có hardware, cần firmware |
| Mic INMP441 x2 | ✅ Có, chưa tích hợp hoàn chỉnh |
| Loa MAX98357 | ✅ Có, chưa tích hợp hoàn chỉnh |
| Màn hình | ⬜ Chưa mua |
| Camera | ⬜ Chưa mua |
| Khung robot | 🔧 Tạm dùng kit xe, sẽ in 3D |
| Pin | 🔧 18650 x3 tạm thời |
| Linh kiện phụ | ⬜ Chưa đủ |
