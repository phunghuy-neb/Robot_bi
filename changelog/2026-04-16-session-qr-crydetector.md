# Session 2026-04-16 - QR + CryDetector logging

## Muc tieu
- Khoi phuc QR Code trong output `start_robot.bat`.
- Chan spam log `CryDetector` khi may khong co microphone hop le.

## Da thay doi
- `src_brain/network/api_server.py`
- `src_brain/senses/cry_detector.py`
- `PROJECT.md`
- `.claude/handoff.md`

## Chi tiet
- Doi render QR sang ASCII thuan (`##` / space) de hien thi on dinh tren Windows console, khong phu thuoc Unicode block.
- Ap dung cung mot renderer cho QR Parent App va QR Cloudflare Tunnel.
- Them xu ly rieng cho loi microphone khong hop le trong `CryDetector`: log `info` 1 lan roi dung detector thay vi warning lap vo han.
- Chuan hoa dong fallback YAMNet thanh ASCII-safe de tranh loi encoding tren console `cp1252`.

## Xac nhan
- Chay `start_robot.bat`: QR da hien lai trong terminal.
- `CryDetector` khong con spam `Error querying device -1`.
- Chay `python run_tests.py`: `54/54 PASS`.
