# HARDWARE.md — Phần Cứng Robot Bi

> Phiên bản: 1.1 | Cập nhật: 2026-05-19
> File này mô tả linh kiện, kiến trúc phần cứng, và ghi chú lắp ráp.
> Cập nhật khi mua linh kiện mới, thay thế component, hoặc thay đổi wiring.
> Cho software implementation liên quan đến phần cứng, xem `PROJECT.md` và `SYSTEM_MAP.md`.

---

## 1. Tổng Quan Kiến Trúc

### Kiến Trúc Prototype (Hiện Tại)

```
┌─────────────────────────────────┐         ┌──────────────────────────────┐
│      Brain Server (PC/Laptop)   │         │        Thân Robot            │
│  - Brain: AI, API, STT, TTS     │◄──WiFi──►│  ESP32 #1 (Motor + Safety)  │
│  - Parent App web server        │         │  ESP32-S3 (Audio + Display) │
│  - ChromaDB, SQLite             │         │  Màn hình SPI               │
│  - GPU: RTX 2060 Super          │         │  Loa MAX98357               │
│  - RAM: 16GB                    │         │  Mic INMP441 x2             │
└─────────────────────────────────┘         │  Motor + L298N              │
        ▲                                   │  Pin 18650 x3               │
        │ USB / MJPEG                        └──────────────────────────────┘
  USB Webcam (test)
```

### Kiến Trúc Sản Xuất (Hướng Tương Lai)

```
┌─────────────────────────────────┐
│      Brain Server (PC/Laptop)   │
│  - AI, STT, TTS, LLM, Safety   │
│  - FastAPI, Storage             │
└─────────────┬───────────────────┘
              │ WiFi
              ▼
┌─────────────────────────────────┐
│    Gateway (Orange Pi hoặc TĐ)  │
│  - Body manager                 │
│  - WebRTC camera stream         │
│  - OTA firmware updates         │
│  - Health monitor               │
│  - WiFi reconnect               │
│  - Bridge ESP32 Motor + ESP32-S3│
└──────┬──────────────┬───────────┘
       │              │
       ▼              ▼
ESP32 Motor      ESP32-S3           Camera IMX219
(di chuyển,     (mặt/audio/        → Gateway WebRTC
 safety)         cảm ứng)
```

**Nguyên tắc phân vai**:
- Brain Server làm toàn bộ AI processing — STT, LLM, TTS, Safety Filter, Vision AI
- Gateway quản lý thân robot — không làm AI, chỉ làm I/O, điều phối, OTA
- ESP32 chỉ làm phần cứng — nhận lệnh, điều khiển motor/audio/display
- USB webcam chỉ dùng cho prototype — không phải hướng sản phẩm

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

**Prototype (test nhanh)**:
- USB webcam gắn vào PC — không cần phần cứng robot
- Đủ để test motion detection, follow me logic, video call flow

**Sản xuất (hướng cuối cùng)**:
- Camera tích hợp trong thân robot
- Stream qua Gateway → WebRTC → Brain Server
- Brain Server xử lý AI (OpenCV, motion detection, follow me, video call)

**Recommendation sản xuất**:

| Option | Model | Ghi chú |
|---|---|---|
| ⭐ Tốt nhất | IMX219 | Chất lượng tốt, hỗ trợ libcamera, phổ biến với Orange Pi/RPi |
| Thay thế | OV5647 | Rẻ hơn, chất lượng thấp hơn |

**Lưu ý**:
- Camera kết nối với Gateway (không kết nối trực tiếp với Brain Server)
- Gateway stream qua WebRTC — độ trễ thấp hơn MJPEG đáng kể
- Không xử lý AI trên camera hoặc Gateway

**Prototype (nếu cần camera trên robot trước khi có Gateway)**:
- ESP32-CAM (OV2640) vẫn dùng được — stream MJPEG về Brain Server
- Đây là giải pháp tạm thời, không phải hướng sản xuất

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

### 3.3B Gateway — Linh Kiện Mới Cho Sản Xuất

| Component | Gợi ý | Vai trò |
|---|---|---|
| Gateway board | Orange Pi Zero 2W hoặc tương đương | Body manager, WebRTC, OTA, bridge |
| Nguồn cho Gateway | 5V / 2A ổn định | Tách riêng với motor |
| Kết nối Gateway ↔ ESP32 | UART hoặc WiFi | Tuỳ thiết kế firmware |

**Lưu ý**: Gateway cần chạy Linux để hỗ trợ WebRTC và OTA firmware. Raspberry Pi cũng phù hợp nếu không cần tối ưu chi phí.

### 3.4 Khung Robot và Cơ Khí — TƯƠNG LAI

| Item | Ghi chú |
|---|---|
| Khung in 3D | Thiết kế sau khi confirm tất cả component sizes |
| Bánh xe phù hợp khung | Chọn sau khi có khung |
| Pin tốt hơn | Li-ion pack hoặc LiPo phù hợp kích thước khung |
| Hệ thống quản lý pin | Bảo vệ pin, sạc an toàn |
| Dock sạc — "Nhà của Bi" | Tự về dock khi pin yếu; IR beacon hoặc cơ chế tương đương |
| IR beacon cho auto-dock | Robot nhận diện vị trí dock để tự tìm về |
| Cảm biến tránh vật cản | Cần trước khi làm follow me; có thể dùng ultrasonic hoặc IR |

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

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Brain Server (PC) + Software | ✅ Hoạt động | Chạy toàn bộ AI stack |
| ESP32 Motor + L298N | ✅ Có firmware, đang test | Kit xe tạm thời |
| ESP32-S3 Audio | 🔧 Có hardware, cần firmware | I2S mic + loa chưa tích hợp hoàn chỉnh |
| Mic INMP441 x2 | ✅ Có | Chưa tích hợp hoàn chỉnh |
| Loa MAX98357 | ✅ Có | Chưa tích hợp hoàn chỉnh |
| Màn hình TFT SPI | ⬜ Chưa mua | Gợi ý: ILI9488 3.5" |
| Camera | ⬜ Chưa mua | Prototype: USB webcam; Sản xuất: IMX219 qua Gateway |
| Gateway (body manager) | ⬜ Chưa có | Sản xuất: Orange Pi hoặc tương đương |
| Dock sạc (nhà của Bi) | ⬜ Chưa có | Cần IR beacon cho auto-dock |
| Cảm biến tránh vật cản | ⬜ Chưa mua | Cần trước follow me |
| Khung robot | 🔧 Tạm dùng kit xe | Sẽ in 3D sau khi confirm kích thước |
| Pin | 🔧 18650 x3 tạm thời | Nâng cấp sau khi có khung |
| Linh kiện phụ (tụ, điện trở...) | ⬜ Chưa đủ | Xem danh sách mục 3.3 |
