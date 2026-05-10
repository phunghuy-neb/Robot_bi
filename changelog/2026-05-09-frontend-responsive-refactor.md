# 2026-05-09 — Frontend Responsive Refactor

## Tóm tắt
Refactor toàn bộ giao diện web Robot Bi: responsive app shell mới, breakpoints chuẩn, WiFi screen đẹp.

## Thay đổi chính

### Viewport
- Đổi từ `user-scalable=no` sang `viewport-fit=cover` (hỗ trợ iPhone safe area).

### Design tokens mới
- `--primary-600: #1d4ed8`, `--border: #e2e8f0`, `--shadow-soft`, `--bg: #f4f8ff`.

### App shell responsive
- `.app-shell` không còn cứng `max-width: 480px` — thay bằng media queries.
- Bottom nav: full width, có `env(safe-area-inset-bottom)`.
- Page padding: thêm `env(safe-area-inset-bottom)`.

### Breakpoints mới (thay cũ 600/768/1025/1400px)
- **< 600px**: Mobile, bottom nav, 1 cột.
- **600px+**: max-width 680px, vẫn bottom nav.
- **900px+**: max-width 960px, 2-col grids bắt đầu.
- **1200px+**: Desktop/sidebar mode — ẩn bottom nav, hiện sidebar 240px, sidebar bên trái.
- **1600px+**: max-width 1280px.

### WiFi section — redesign hoàn toàn

#### Mobile
- Menu item "Mạng & Kết nối" trong tab Thêm.
- Click mở **WiFi Subscreen** (fixed overlay full screen).
- Subscreen có: back button, hero status card (gradient blue), 2 nút Quét/Kiểm tra, danh sách WiFi, accordion "Thông tin chi tiết".

#### Desktop (>= 1200px)
- Inline dashboard trong tab Thêm.
- Full-width banner trạng thái (gradient blue) + 4 metric cards.
- 2-col: WiFi list (trái) + chi tiết (phải).

### CSS mới
- `.subscreen`, `.subscreen-header`, `.back-btn`
- `.wifi-network-row`, `.wifi-network-body`, `.wifi-connected-badge`
- `.accordion-header`, `.accordion-body`, `.detail-row`
- `.wifi-dashboard`, `.wifi-mobile-only`, `.wifi-desktop-only`
- `.desktop-only`, `.mobile-only`, `.action-row`

### JS mới/cập nhật
- `openWifiScreen()`, `closeWifiScreen()` — mobile navigation.
- `openAddWifiModal()` — modal thêm WiFi thủ công mới.
- `loadWifiStatus()` → `_renderWifiHero()` + `updateWifiMenuSub()`.
- `loadWifiDesktop()` — renders desktop dashboard dynamically.
- `renderSavedWifi()`, `renderScanResult()` — viết vào cả mobile subscreen và desktop IDs.
- `startWifiScan()` — hiện loading trên cả hai.
- `checkWifiConnectivity()` — toast từ /api/status + /api/motor/status.
- `toggleWifiAccordion()` — accordion detail toggle.
- `handleWifiWsMessage()` — cập nhật cả desktop + mobile elements.

## Functions không bị ảnh hưởng
apiFetch, authHeader, tryRefreshToken, doLogin, doLogout, connectWS, toggleCamera, startWebRTC, startMJPEG, stopCamera, toggleMomMic, startMomMic, stopMomMic, _motorSend, loadMotor, initJoystick, sendJoystickCmd, lockRobotControl, unlockRobotControl, sendQuickMotorCommand, requestDockReturn, loadHome, loadMonitor, loadLearning, loadJournal.

## Test
372/374 PASS (2 fail cũ không liên quan: 47.4 verify_db_clean, 48.3 music volume).
