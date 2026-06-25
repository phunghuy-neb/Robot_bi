# Huong Dan Chay Robot Bi

## Yeu Cau Truoc Khi Chay

1. Tao va dien `.env` tren may local. Khong commit `.env`.
2. Can cac bien chinh: `CEREBRAS_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `JWT_SECRET_KEY`, `AUTH_PIN`, `ADMIN_PASSWORD`.
3. Neu muon day du fallback chain, them `SAMBANOVA_API_KEY`, `CLOUDFLARE_API_KEY`, `CLOUDFLARE_ACCOUNT_ID`.
4. Can internet cho Cerebras/Groq/Gemini, edge-tts, va tunnel neu dung.

## Lenh Chinh

```bash
python sync.py
python tests/run_tests.py
python src/main.py
```

`start_robot.bat` co the dung de khoi dong robot theo launcher Windows.

## Entry Points Hien Tai

- Main app: `src/main.py`
- API server: `src/api/server.py`
- Parent App: `frontend/parent_app/`
- Robot Display: `frontend/robot_display/`
- Firmware: `firmware/Robot_BI/Robot_BI.ino`
- DB runtime: `runtime/robot_bi.db`

## Cau Hinh Phan Cung Hien Tai

May hien tai co loa va 2 microphone, khong co camera.

Trong `.env`:

```env
# De trong de Robot Bi tu chon mic that va bo qua Stereo Mix/Line In.
MIC_DEVICE=

# CryDetector dung mic thu hai, khong dung chung mic STT.
CRY_DETECTION_ENABLED=true
CRY_MIC_DEVICE=

# Khong khoi dong EyeVision khi chua gan camera.
CAMERA_ENABLED=false
CAMERA_INDEX=0
```

Lenh sau chi dung cho microphone cam truc tiep vao may tinh:

```bash
python -m src.audio.input.microphone_utils
```

Hai microphone INMP441 tren robot ket noi vao ESP32-S3, khong phu thuoc quyen
microphone cua Windows.

## Truy Cap Parent App

1. Chay robot bang `python src/main.py` hoac `start_robot.bat`.
2. Quet QR code hien trong terminal neu co.
3. Hoac mo `https://[IP-may-tinh]:8443`.

## Dang Nhap

1. Dung tai khoan admin duoc seed tu `.env` hoac tai khoan da dang ky.
2. Neu can tao tai khoan lan dau, dat `REGISTRATION_ENABLED=true`, dang ky tai khoan, sau do dat lai `REGISTRATION_ENABLED=false` va restart robot.

## Cai Parent App Len Dien Thoai

1. Mo Chrome tren Android.
2. Vao dia chi Parent App.
3. Chon menu va "Add to Home screen".

## Debug Co Ban

```bash
python tests/run_tests.py
python stress_test.py
python verify_db_clean.py
```

Khi debug module rieng, dung path hien tai trong `src/`, khong dung `src_brain/`.

## Cloudflare Named Tunnel

Mac dinh quick tunnel co the doi URL sau moi lan restart. De co URL co dinh:

1. Tao named tunnel trong Cloudflare Zero Trust.
2. Cau hinh Public Hostname tro ve `localhost:8443`.
3. Them vao `.env`:

```env
CLOUDFLARE_TUNNEL_TOKEN=...
CLOUDFLARE_TUNNEL_URL=https://subdomain.example.com
```

4. Restart robot.

## WebRTC Tren Ubuntu

```bash
pip install -r requirements-ubuntu.txt
```

Lenh cai dat dependency can duoc user cho phep truoc khi chay.

## Firmware Robot

Firmware hien tai nam tai:

```text
firmware/Robot_BI/Robot_BI.ino
firmware/ESP32S3_Mic_Test/ESP32S3_Mic_Test.ino
```

ESP32 firmware dang xu ly motor pins, WiFi setup/persistence, WebSocket motor commands, server registration, va watchdog stop behavior. Kiem tra file `.ino` truoc khi sua firmware.

Sketch `ESP32S3_Mic_Test` kiem tra 2 microphone INMP441 va loa MAX98357A tren
ESP32-S3 N16R8 ma khong can Serial Monitor. Mot beep dai bao bat dau noi; firmware
thu 5 giay vao PSRAM, sau do phat lai mic trai va mic phai rieng. Firmware khong
phat truc tiep mic ra loa trong luc thu, nen tranh vong lap gay hu rit.

## Deprecated

`src_brain/` la path cu. Khong chay command, import, hoac tao file moi trong `src_brain/`.
