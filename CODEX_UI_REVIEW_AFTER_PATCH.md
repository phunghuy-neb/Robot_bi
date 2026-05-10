# CODEX UI Review After Patch

## Tổng Kết

**Not ready.** Motor safety core path is mostly fixed, but there are still production-relevant gaps: motor stop fallback does not actually run on `apiFetch()` failure, `/api/motor/register` is still public when `ROBOT_REGISTER_TOKEN` is unset, conversation thread UI is only partially wired, and desktop Wi-Fi still has unescaped IP in `innerHTML`.

## Bảng Lỗi Cũ

| Area | Status | Ghi chú |
|---|---|---|
| `sendMotorStopNow()` independent unlock | Fixed | `frontend/parent_app/index.html:3030` does not check `robotControlUnlocked`. |
| `lockRobotControl()` sends stop | Fixed | Calls `sendMotorStopNow('lock')` before setting locked state. |
| Leave Monitor sends stop | Fixed | `switchTab()` calls `lockRobotControl()` when leaving `monitor`. |
| 60s timeout sends stop | Fixed | Timer calls `lockRobotControl()`. |
| `beforeunload` stop | Partially fixed | Calls `sendMotorStopNow('unload')`, but uses async `fetch` via `apiFetch`; not reliable unload best-effort like `sendBeacon`/`keepalive`. |
| Emergency stop visible | Fixed | Button is outside unlocked-only block and always visible in motor card. |
| Emergency stop calls correct function | Fixed | Calls `sendMotorStopNow('emergency')`. |
| Joystick stop endpoint | Fixed | Backend has `/api/motor/joystick` with `{left,right}` and maps to `drive(left,right)`. |
| Motor stop fallback | Still broken | `.catch()` fallback will usually not run because `apiFetch()` catches errors and resolves `null`. |
| `startWifiScan` `listEl` crash | Fixed | No `listEl` reference remains in offline branch. |
| Wi-Fi scan offline crash | Fixed | Offline branch updates both scan containers and toasts. |
| `wifi_error:*` resets loading | Fixed | Handler replaces scan loading with error UI. |
| Mobile More fetches Wi-Fi status | Fixed | `loadMore()` calls `loadWifiStatus()` on mobile. |
| Connected SSID badge | Partially fixed | Badge logic exists, but `openWifiScreen()` calls status/list concurrently and desktop `loadWifiDesktop()` does not set `_wifiCurrentSsid`, so badge can be missed. |
| Placeholder fields clear | Partially fixed | Mobile uses “Chưa hỗ trợ”; desktop still uses `—`. |
| `loadThreads()` fetches conversations | Fixed | Fetches `/api/conversations?limit=20`. |
| `showThreadDetail()` exists | Fixed | Function exists and fetches `/api/conversations/{session_id}`. |
| Journal click opens detail | Partially fixed | Thread rows from “Xem tất cả” open detail; default Journal conversation cards from `/api/chats` are still not clickable. |
| Back button | Fixed | Detail view back button calls `loadThreads()`. |
| Homework/detail flow | Partially fixed | Homework list still loads, but rows are not wired to `showThreadDetail(session_id)`. |
| `/api/motor/register` public without token | Still broken | It remains open if `ROBOT_REGISTER_TOKEN` is unset by design. |
| `hmac.compare_digest` | Fixed | Used correctly when expected token exists. |
| SSID/IP escaping | Partially fixed | SSID mostly safe; desktop detail IP still rendered unescaped in `innerHTML`. |
| 320px responsive | Partially fixed | Some CSS added, but `.task-add-row` class is not applied and summary grid is still inline 2-column. |
| 390px responsive | Fixed enough | No obvious static overflow issue found. |
| 1024px nav | Partially fixed | Still bottom nav; acceptable only if 1024 is considered tablet, not desktop. |
| 1366px centering | Still broken | `.page-content` has max-width but no `margin: 0 auto`, so content remains left-biased. |

## Critical Còn Lại

### `/api/motor/register` vẫn public khi chưa set token

- File/vị trí: `src/api/routers/wifi_router.py:23`
- Mô tả: `/api/motor/register` vẫn mở nếu `ROBOT_REGISTER_TOKEN` không được set.
- Vì sao nghiêm trọng: production có thể bị đăng ký motor endpoint trái phép.
- Cách sửa đề xuất: fail closed ngoài dev, hoặc gate theo environment mode rõ ràng.

### Desktop Wi-Fi detail còn render IP không escape

- File/vị trí: `frontend/parent_app/index.html:4082`
- Mô tả: desktop Wi-Fi detail render `${ip}` trong `innerHTML` mà không qua `escapeHTML()`.
- Vì sao nghiêm trọng: dữ liệu status có thể đến từ ESP32/backend JSON, vẫn còn injection risk.
- Cách sửa đề xuất: escape toàn bộ field interpolated hoặc render bằng DOM node/textContent.

## High Còn Lại

### Motor stop fallback không chạy thực tế

- File/vị trí: `frontend/parent_app/index.html:3035`
- Mô tả: fallback `/api/motor/stop` nằm trong `.catch()`, nhưng `apiFetch()` thường nuốt lỗi và resolve `null`.
- Ảnh hưởng: nếu `/api/motor/joystick` fail logic/API, fallback stop không được gọi.
- Cách sửa đề xuất: kiểm tra `result?.ok`; nếu false/null thì gọi `/api/motor/stop`.

### Journal default chưa dùng conversation threads

- File/vị trí: `frontend/parent_app/index.html:3265`
- Mô tả: default Journal vẫn load `/api/chats`; chỉ link “Xem tất cả” mới gọi `loadThreads()`.
- Ảnh hưởng: protected thread detail đã khôi phục nhưng chưa phải UI hội thoại chính.
- Cách sửa đề xuất: cho Journal conversation section gọi `loadThreads()` mặc định hoặc làm `/api/chats` rows click được khi có `session_id`.

### Homework rows chưa mở detail

- File/vị trí: `frontend/parent_app/index.html:3206`
- Mô tả: homework list vẫn load nhưng row không có click handler sang `showThreadDetail(s.session_id)`.
- Ảnh hưởng: homework/detail flow mới chỉ dừng ở list.
- Cách sửa đề xuất: add click handler cho homework row, hoặc mở Journal detail modal/subview.

### Responsive 320px fix chưa ăn vào DOM

- File/vị trí: `frontend/parent_app/index.html:2081`, `frontend/parent_app/index.html:2162`
- Mô tả: summary grid vẫn inline `grid-template-columns:1fr 1fr`; CSS `.task-add-row` không match vì task row chưa có class này.
- Ảnh hưởng: 320px vẫn có thể chật/vỡ chữ.
- Cách sửa đề xuất: đưa summary/task add row vào class thật và media query 1 cột cho màn nhỏ.

## Patch Plan Nếu Còn Lỗi

1. Make `/api/motor/register` fail closed outside dev, and update firmware to send `X-Robot-Register-Token`.
2. Change `sendMotorStopNow()` to await/check joystick result and call `/api/motor/stop` when `!result?.ok`; use `fetch(..., {keepalive:true})` or `sendBeacon` for unload stop.
3. Escape all interpolated Wi-Fi fields in desktop `innerHTML`, especially detail IP, and avoid `innerHTML` for dynamic device data where possible.
4. Wire Journal default conversations to `loadThreads()` or make `/api/chats` rows clickable to thread detail when `session_id` exists.
5. Add click handlers for homework rows to `showThreadDetail(s.session_id)`.
6. Apply responsive classes to the actual Learning summary/task rows and center desktop `.page-content` with `margin: 0 auto`.
