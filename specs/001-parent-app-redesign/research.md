# Research: Parent App UI Redesign

**Feature**: 001-parent-app-redesign | **Date**: 2026-05-13

---

## Decision: React + Vite Migration

**Decision**: Migrate `frontend/parent_app/` từ legacy single-file HTML/CSS/JS sang React + Vite. Legacy `index.html` trở thành Vite mount shell; toàn bộ UI nằm trong `src/`.

**Rationale**: Codebase cũ (~4,000+ dòng HTML/CSS/JS inline) đã đạt ngưỡng không maintainable — không thể scale thêm 18 tính năng mới mà không phá existing behavior. React component model cho phép chia nhỏ tabs thành isolated pages, dễ test và review từng phần. Vite build đảm bảo proper module isolation — loại bỏ rủi ro global variable collision vốn là risk R1 trong kiến trúc single-file.

**Alternatives considered**:
- Giữ single-file HTML/CSS/JS: không scale được; 4,000+ dòng inline đã gây R1-R7 risks; không thể component-isolate protected functions.
- ES modules without bundler: yêu cầu CORS-safe HTTP serve cho từng .js file, phức tạp hơn Vite setup, không có HMR hay build optimization.
- Vue / Svelte: React phù hợp hơn vì ecosystem lớn hơn cho Vietnam dev community; không có lý do kỹ thuật để chọn framework khác.

**Migration approach**: Legacy `index.html` được audit trước để lập preservation checklist cho tất cả protected functions. Sau đó `index.html` trở thành Vite shell (`<div id="root">`). Tất cả UI chuyển sang `src/`. Không giữ legacy UI song song.

---

## Decision: Vite Build Configuration

**Decision**: Vite với React plugin. `base: './'` cho phép FastAPI serve build output từ `frontend/parent_app/dist/` mà không cần thay đổi backend static mount config.

**Config**:
```javascript
// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()], base: './', build: { outDir: 'dist' } });
```

**Backend serve path**: FastAPI hiện serve `frontend/parent_app/` trực tiếp qua StaticFiles mount. Sau Vite migration, serve `frontend/parent_app/dist/` thay thế — thay đổi này là 1 dòng trong `src/api/routers/ops_router.py`. Đây là implementation detail — không thay đổi trong phase này (spec artifacts only).

---

## Decision: Mobile-First Single Breakpoint

**Decision**: Một breakpoint duy nhất tại 768px (mobile-first).

**Rationale**: App phục vụ phụ huynh trên 2 ngữ cảnh chính: điện thoại (kiểm tra nhanh) và desktop/laptop (xem chi tiết). Không cần breakpoint trung gian (tablet). Bottom nav trên mobile là pattern quen thuộc nhất với người dùng Việt Nam.

**Alternatives considered**:
- 3 breakpoints (mobile/tablet/desktop): không cần thiết, tablet dùng được với desktop layout.
- Desktop-first: không phù hợp với "mobile-first" requirement.

---

## Decision: Google Fonts CDN cho Typography

**Decision**: Load Be Vietnam Pro từ Google Fonts CDN via `@import` trong `src/styles.css`. Fallback: Plus Jakarta Sans, rồi system sans-serif.

**Rationale**: Be Vietnam Pro là font tiếng Việt có dấu tốt, thiết kế hiện đại, miễn phí. `@import` trong CSS bundle là chuẩn với Vite. Fallback đảm bảo app vẫn đọc được khi offline.

**CSS import**:
```css
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800;900&display=swap');
```

**Alternatives considered**:
- `<link>` trong index.html shell: vẫn hoạt động nhưng tách biệt font declaration khỏi styles.css, khó maintain hơn.
- Self-host font: tốt hơn cho offline nhưng tăng bundle setup; `@import` CDN đủ cho dự án này.
- Plus Jakarta Sans: cũng tốt, nhưng Be Vietnam Pro có hỗ trợ tiếng Việt tốt hơn.

---

## Decision: CSS Custom Properties cho Design Token

**Decision**: Định nghĩa tất cả design tokens trong `:root` của `src/styles.css`. Không dùng CSS-in-JS, CSS Modules, hay Tailwind — vanilla CSS với custom properties là đủ cho dự án này.

**Rationale**: CSS custom properties (`var(--primary)`, etc.) có thể dùng xuyên suốt tất cả React components mà không cần CSS-in-JS runtime. Đơn giản, hiệu quả, không có dependency overhead. Consistent với design token spec đã được xác định.

---

## Decision: Mock Adapter Pattern cho Future Backend

**Decision**: Mọi tính năng chưa có backend đều có `api<Feature>()` adapter function trong `src/services/api.js` wrapping data từ `src/data/mockData.js`. Pattern này cho phép swap sang real `apiFetch()` chỉ bằng 1 dòng thay đổi.

**Rationale**: Tránh gọi endpoint chưa tồn tại gây lỗi 404 trong console. Chuẩn bị sẵn integration point. Dễ tìm bằng grep `// TODO:`. Tách mock data ra file riêng giúp dễ thay thế và maintain hơn inline hardcoded data.

---

## Decision: Settings as Overlay Panel (không phải tab chính)

**Decision**: Cài đặt mở như full-screen overlay (z-index 500), không phải tab thứ 6 trong sidebar.

**Rationale**: Cài đặt là tính năng secondary, không cần thiết trong daily navigation. Overlay pattern giống iOS Settings sheet, quen thuộc với user. Giữ được 5 tab chính clean.

**Mobile vs Desktop**:
- Mobile: overlay chiếm toàn màn hình, có back button.
- Desktop: overlay chiếm phần main content (không che sidebar).

---

## Decision: Admin Detection từ JWT Claims

**Decision**: `isAdmin` được lưu trong React context/state sau login từ `is_admin` field trong login response — không cần request mới.

**Rationale**: Backend đã trả về user info khi login (có `is_admin` field). React AuthContext store field này và expose cho tất cả components qua `useAuth()` hook. Không cần thêm `/api/me` request.

**Implementation**:
```javascript
// src/services/api.js — doLogin() success handler
// Returns: { token, refreshToken, username, isAdmin, ... }
// React AuthContext stores isAdmin and exposes via useAuth()
```

---

## Decision: Child Profile Switching là Local State

**Decision**: Switching hồ sơ trẻ là React state + localStorage key `bi_active_child`, không sync với backend.

**Rationale**: Backend endpoint cho child profiles chưa tồn tại. React state + localStorage đủ để demo UX và persist qua page reload. Khi backend sẵn sàng, chỉ cần thay `apiGetChildProfiles()` mock với real fetch — interface không đổi.

---

## Current API Endpoints — Verified từ SYSTEM_MAP.md

Xem chi tiết trong `plan.md` Section 10 (Integration Boundary). Tất cả endpoints Tier 1 đã được verify từ router map trong SYSTEM_MAP.md.

---

## Findings: Protected Behavior — Preservation Checklist

Các hàm sau trong legacy `index.html` phải được tái hiện đúng trong `src/services/api.js` và React components:

| Legacy function | Target in React | Protected behavior |
|---|---|---|
| `doLogin(user, pass)` | `api.login(user, pass)` in api.js | JWT access+refresh, localStorage `bi_token`/`bi_refresh`, rate-limit 5/15min |
| `doLogout()` | `api.logout()` in api.js | Clear tokens, call `/api/auth/logout` |
| `tryRefreshToken()` | `api.refreshToken()` in api.js | Refresh rotation, auto-logout on failure |
| `apiFetch(path, opts)` | `api.apiFetch(path, opts)` in api.js | Auth header, 401 → refresh → retry → logout |
| `connectWS()` | `useWebSocket()` hook or api.js | `wss://host/ws?token=...`, realtime events |
| `startMomMic()` / `stopMomMic()` | `api.startMomMic()` / `stopMomMic()` | Protected audio behavior |
| `loadThreads()` / `showThreadDetail()` | Via `api.getConversations()` + modal state | Protected conversation UI |
| `toast(msg)` | `useToast()` hook | Non-breaking toast UI |

**Audit requirement**: Before replacing `index.html`, complete a preservation checklist against this table. Each row must have a corresponding React implementation before legacy HTML is removed.

---

## Findings: Existing Font Size Issue (Legacy)

Legacy `index.html` uses 14px body — below elderly-friendly requirement. Target in React:
- Body: 16px (`--font-body`)
- Section title: 20px (no UPPERCASE)
- Important buttons: 18px
- Page headings: 24px

---

*Research complete. No NEEDS CLARIFICATION items remain. Architecture decision: React + Vite migration. Proceed to plan/tasks update.*
