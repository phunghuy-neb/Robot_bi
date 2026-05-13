# Implementation Plan: Redesign Giao Diện Parent App Robot Bi

**Branch**: `001-parent-app-redesign` | **Date**: 2026-05-13 | **Spec**: [spec.md](spec.md)

---

## Summary

Migrate `frontend/parent_app/` từ legacy single-file HTML/CSS/JS (~4,000 dòng inline) sang React + Vite SPA với 5-tab navigation, "Công nghệ ấm áp" design system, và 18 tính năng UI mới (phần lớn mock/placeholder vì backend làm sau). Legacy `index.html` trở thành Vite mount shell. Tất cả chức năng backend hiện có (auth, WebSocket, camera, music, conversations, events, analytics, games, flashcards, motor, WiFi, admin) được tái hiện đúng trong `src/services/api.js`.

---

## Technical Context

**Stack**: React 18 + Vite 5

**Dependencies**:
```json
{
  "dependencies": { "react": "^18", "react-dom": "^18" },
  "devDependencies": { "@vitejs/plugin-react": "^4", "vite": "^5" }
}
```

**Storage**: `localStorage` cho token (`bi_token`, `bi_refresh`, `bi_active_child`); backend SQLite không đổi

**Testing**: Manual browser testing + `npm run build` cho build errors; `python tests/run_tests.py` cho backend regression

**Target Platform**: Modern browser (Chrome/Firefox/Safari/Edge), desktop + mobile responsive

**Project Type**: React SPA — tab-based navigation via `useState`, no URL router required

**Performance Goals**: Trang chủ render đầy đủ trong 3 giây sau login; không có API call blocking render

**Constraints**: Không sửa src/, firmware/, frontend/robot_display/, tests/, runtime/, logs/, .env; không thêm backend routes; không thay đổi API contracts

---

## Constitution Check

| Gate | Status | Notes |
|------|--------|-------|
| Protected Fixes không bị ảnh hưởng | PASS | doLogin, apiFetch, connectWS, JWT, mom-talk tái hiện đúng trong api.js |
| Child safety/privacy | PASS | Chỉ làm frontend UI; không thay đổi safety filter logic |
| Auth/JWT behavior | PASS | Tất cả auth logic migrate sang src/services/api.js — behavior giữ nguyên |
| Multi-family isolation | PASS | Tất cả API call giữ nguyên family_id scoping |
| SQLite DB path/schema | PASS | Không đụng backend |
| File Creation Policy | PASS | Không tạo file Markdown mới ở root |
| SYSTEM_MAP.md Policy | PASS | Cập nhật SAU implementation |
| Không gọi endpoint chưa tồn tại | PASS | Mock adapters cho tất cả tính năng chưa có backend |
| Không thêm backend framework | PASS | Chỉ React+Vite trong frontend/parent_app/ |

---

## Project Structure

### Target (sau migration)

```text
frontend/parent_app/
├── package.json           <- React + Vite dependencies
├── vite.config.js         <- Vite config (base: './', build: outDir: 'dist')
├── index.html             <- Vite mount shell (<div id="root">)
├── src/
│   ├── main.jsx           <- React entry point (ReactDOM.createRoot)
│   ├── App.jsx            <- Root component: auth gate + tab router + layout
│   ├── styles.css         <- Global CSS (design tokens, base styles, responsive)
│   ├── services/
│   │   └── api.js         <- ALL API/WebSocket/auth behavior (preserved from legacy)
│   ├── data/
│   │   └── mockData.js    <- Vietnamese mock data for all Tier 2 features
│   ├── components/
│   │   ├── Sidebar.jsx         <- Desktop sidebar (5 tabs + bottom section)
│   │   ├── BottomNav.jsx       <- Mobile bottom nav (5 tabs)
│   │   ├── RobotStatusCard.jsx <- Online/offline/connecting states
│   │   ├── UserCard.jsx        <- Username, role, child profile
│   │   ├── SettingsOverlay.jsx <- Full-screen settings panel
│   │   ├── FeatureBadge.jsx    <- coming-soon / mock-data / no-backend
│   │   ├── SectionState.jsx    <- loading / error / empty states
│   │   └── Toast.jsx           <- Toast notification
│   └── pages/
│       ├── LoginPage.jsx   <- Login form
│       ├── HomePage.jsx    <- Trang chủ (US1)
│       ├── MonitorPage.jsx <- Giám sát (US2 secondary)
│       ├── LearningPage.jsx <- Học tập
│       ├── JournalPage.jsx <- Nhật ký (US2)
│       └── MorePage.jsx    <- Thêm (US4)
├── manifest.json          <- PWA manifest (không sửa trừ khi cần)
├── sw.js                  <- Service worker (không sửa trừ khi cần)
├── icon-192.png           <- Không sửa
└── icon-512.png           <- Không sửa
```

### Documentation (this feature)

```text
specs/001-parent-app-redesign/
├── plan.md         <- This file
├── spec.md
├── research.md
├── data-model.md
├── checklists/requirements.md
└── tasks.md
```

---

## Phase 0: Pre-Migration Audit

### 1. Existing Function Preservation Strategy

**Quy tắc bảo tồn hành vi:**

1. **Audit trước khi xóa**: Trước khi thay `index.html` bằng Vite shell, phải hoàn thành preservation checklist (tasks T001–T003).
2. **api.js là home mới của protected functions**: Tất cả behavior từ `doLogin`, `doLogout`, `apiFetch`, `connectWS`, `startMomMic`, `stopMomMic`, `loadThreads`, `showThreadDetail` được tái hiện trong `src/services/api.js`.
3. **Không xóa behavior**: Chỉ di chuyển — không rút gọn, không thay đổi logic.
4. **Test sau migrate**: Sau khi api.js hoàn chỉnh, verify đăng nhập/đăng xuất/WebSocket/API calls trước khi xóa legacy HTML.

**Protected functions và target trong React:**

| Legacy function | api.js export | React hook/usage |
|---|---|---|
| `doLogin(u, p)` | `login(u, p)` | `useAuth().login()` |
| `doLogout()` | `logout()` | `useAuth().logout()` |
| `tryRefreshToken()` | `refreshToken()` | auto-called trong apiFetch |
| `apiFetch(path, opts)` | `apiFetch(path, opts)` | called by all page components |
| `connectWS()` | `connectWebSocket(onEvent)` | `useWebSocket()` hook or App.jsx |
| `setStatus(online)` | exposed via WS event | RobotStatusCard nhận state từ App |
| `startMomMic()` / `stopMomMic()` | `startMomMic()` / `stopMomMic()` | MonitorPage |
| `loadThreads()` | `getConversations()` | JournalPage |
| `showThreadDetail(id)` | `getConversation(id)` | JournalPage modal state |
| `toast(msg)` | `showToast(msg)` | Toast component via context |

---

## Phase 1: Design & Architecture

### 2. Proposed Information Architecture

```
Parent App (React SPA)
│
├── [LoginPage]  (nếu chưa login)
│
└── [App Layout] (nếu đã login)
    ├── [Sidebar — Desktop ≥768px]
    │   ├── Logo
    │   ├── Tab: Trang chủ
    │   ├── Tab: Giám sát
    │   ├── Tab: Học tập
    │   ├── Tab: Nhật ký
    │   ├── Tab: Thêm
    │   └── Bottom (locked order):
    │       ├── RobotStatusCard
    │       ├── UserCard
    │       ├── Nút Cài đặt
    │       └── Nút Đăng xuất
    │
    ├── [BottomNav — Mobile <768px]
    │   └── 5 tabs (icon + label)
    │
    ├── [Main content — active tab]
    │   ├── HomePage
    │   ├── MonitorPage
    │   ├── LearningPage
    │   ├── JournalPage
    │   └── MorePage
    │
    └── [SettingsOverlay]  (modal khi nhấn Cài đặt)
        ├── Hồ sơ trẻ          [mock-data]
        ├── Thông báo           [coming-soon]
        ├── Giờ hoạt động       [coming-soon]
        ├── Nội dung & An toàn  [coming-soon]
        ├── Kết nối thiết bị    [coming-soon]
        └── Chế độ kỹ thuật     (admin only)
            ├── Nhật ký hệ thống [no-backend]
            ├── Persona settings (API hiện có)
            └── Quản lý gia đình (API hiện có)
```

### 3. Component Structure

**App.jsx state:**
```javascript
// Core app state
const [isLoggedIn, setIsLoggedIn] = useState(false);
const [activeTab, setActiveTab] = useState('home');
const [settingsOpen, setSettingsOpen] = useState(false);
const [robotStatus, setRobotStatus] = useState('connecting'); // 'online'|'offline'|'connecting'
const [user, setUser] = useState({ username: '', isAdmin: false });
const [activeChild, setActiveChild] = useState(null);
const [toastMsg, setToastMsg] = useState(null);
```

**Tab IDs** (mapping spec FR-001):
- `'home'` → HomePage
- `'monitor'` → MonitorPage
- `'learning'` → LearningPage
- `'journal'` → JournalPage
- `'more'` → MorePage

**Sidebar bottom order** (FR-002, locked):
1. `<RobotStatusCard status={robotStatus} />`
2. `<UserCard user={user} activeChild={activeChild} />`
3. `<button onClick={() => setSettingsOpen(true)}>⚙️ Cài đặt</button>`
4. `<button onClick={handleLogout}>🚪 Đăng xuất</button>`

### 4. Design Token Usage

**`src/styles.css` — CSS custom properties:**

```css
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800;900&display=swap');

:root {
  --primary: #2563eb;     --primary-dark: #1d4ed8;   --primary-soft: #dbeafe;
  --accent: #7c3aed;      --accent-soft: #ede9fe;
  --success: #22c55e;     --warning: #f59e0b;
  --danger: #ef4444;      --info: #0ea5e9;
  --bg: #f3f7ff;          --card: #ffffff;           --border: #e5eefb;
  --text: #0f172a;        --text-secondary: #475569; --muted: #94a3b8;
  --radius-lg: 22px;      --radius-md: 16px;         --radius-sm: 12px;
  --shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
  --side-w: 240px;        --nav-h: 68px;
  --font-body: 16px;      --font-btn: 18px;
  --font-section: 20px;   --font-heading: 24px;
  --tap-min: 48px;
}

body { font-family: 'Be Vietnam Pro', 'Plus Jakarta Sans', system-ui, sans-serif; font-size: var(--font-body); }
button, a, [role="button"] { min-height: var(--tap-min); }
```

### 5. Mock Data / API Adapter Strategy

**`src/services/api.js` exports:**
- All Tier 1 functions (login, logout, apiFetch, connectWebSocket, startMomMic, stopMomMic, getConversations, getConversation)
- All Tier 2 mock adapters (getChildProfiles, exportReport, getMonthlyEmotions, getRoomLocation, getRadioChannels, getVideoLessons, getSystemLogs, etc.)

**`src/data/mockData.js` exports:**
- Vietnamese realistic mock data for: child profiles, radio channels, video lessons, monthly emotion data, interactive games, system logs

**Pattern:**
```javascript
// src/services/api.js
import { mockChildProfiles, mockRadioChannels } from '../data/mockData.js';

export async function getChildProfiles() {
  // TODO: return apiFetch('/api/children');
  console.info('[MOCK] child-profiles: using mock data');
  return mockChildProfiles();
}
```

**Complete mock adapter list:**

| Feature | api.js function | Badge | Future endpoint |
|---|---|---|---|
| Child profiles | `getChildProfiles()` | mock-data | GET /api/children |
| Export PDF/CSV | `exportReport(fmt)` | coming-soon | POST /api/reports/export |
| Parent notes | `addParentNote(id, note)` | coming-soon | POST /api/events/{id}/notes |
| Monthly emotion | `getMonthlyEmotions(m)` | mock-data | GET /api/emotions/monthly |
| Room location | `getRoomLocation()` | coming-soon | GET /api/robot/location |
| Radio channels | `getRadioChannels()` | mock-data | GET /api/entertainment/radio |
| Video lessons | `getVideoLessons()` | mock-data | GET /api/entertainment/videos |
| QR code | placeholder | coming-soon | GET /api/device/qr |
| System logs | `getSystemLogs()` | no-backend | GET /api/admin/logs |
| Push settings | `savePushSettings(s)` | coming-soon | POST /api/settings/notifications |
| Sleep schedule | `saveSleepSchedule(s)` | coming-soon | POST /api/settings/sleep |
| Time limits | `saveTimeLimits(l)` | coming-soon | POST /api/settings/time-limits |
| Age filter | `saveAgeFilter(f)` | coming-soon | POST /api/settings/age-filter |
| Parent chat | `getParentChatHistory()` | coming-soon | GET /api/conversations/parent |
| Interactive games | `getInteractiveGames()` | coming-soon | GET /api/games/interactive |

### 6. Accessibility Strategy

- Font size: body 16px, buttons 18px, section titles 20px, page headings 24px (via CSS tokens)
- Tap targets: all `<button>` and `<a>` elements ≥48px height (via global CSS rule)
- Contrast: `--text #0f172a` on `--bg #f3f7ff` ≈16:1 (PASS); `--text-secondary #475569` on white ≈7.5:1 (PASS)
- No icon-only buttons: all interactive elements have Vietnamese text label
- All sections have 3 states: loading (spinner), error (message + retry), empty (friendly empty state)
- `<SectionState>` reusable component handles all 3 states

### 7. Responsive Strategy

**Single breakpoint at 768px (mobile-first):**

```css
/* Mobile default */
.side-nav { display: none; }
.bottom-nav { display: flex; }

/* Desktop ≥768px */
@media (min-width: 768px) {
  .side-nav { display: flex; flex-direction: column; width: var(--side-w); }
  .bottom-nav { display: none; }
  .main-content { margin-left: var(--side-w); }
}
```

- Mobile: bottom nav 5 tabs, each ≥56px, sidebar hidden
- Desktop: sidebar 240px fixed left, no bottom nav
- Modals: full-screen mobile, max-width 480px centered desktop
- Settings overlay: bottom drawer mobile, side panel desktop

### 8. Integration Boundary

**Tier 1 — Existing API (call immediately):**

| Feature | Endpoint | Notes |
|---|---|---|
| Auth | `/api/auth/login`, `/refresh`, `/logout` | PROTECTED |
| Robot status | `ws://host/ws?token=...` | PROTECTED WebSocket |
| Camera | `/api/camera`, `/api/webrtc/offer` | |
| Conversations | `/api/conversations`, `/{id}` | PROTECTED |
| Events | `/api/events` | |
| Weekly analytics | `/api/analytics/weekly` | |
| Emotion summary | `/api/emotion/today` | |
| Music | `/api/music/*` | |
| Games (quiz) | `/api/game/*` | |
| Flashcards | `/api/education/*` | |
| Stories | `/api/stories/*` | |
| Tasks | `/api/tasks/*` | |
| Motor | `/api/motor/*` | |
| WiFi | `/api/wifi/status` | |
| Memories/RAG | `/api/memories` | |
| Admin families | `/api/admin/families` | Admin only |
| Persona | `/api/persona` | |
| Puppet | `/api/puppet` | |
| Mom talk | `/api/mom/start`, `/stop`, WS | PROTECTED |

**Tier 2 — UI Mock (backend deferred):** See mock adapter table in section 5.

### 9. Risk List and Rollback Strategy

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Protected behavior regressions when porting to api.js | High | High | Complete preservation checklist before removing legacy HTML; test login+WS+camera after api.js done |
| R2 | Vite base path issue — app loads but API calls broken | Medium | High | `base: './'` in vite.config.js; test against real backend after first build |
| R3 | React state renders stale token / misses WebSocket reconnect | Medium | Medium | connectWebSocket() in useEffect cleanup; token refresh in apiFetch interceptor |
| R4 | CSS variable name conflicts (legacy CSS in new React components) | Low | Low | All new CSS scoped in styles.css; no legacy CSS reuse |
| R5 | npm run build fails due to JSX syntax errors | Medium | Medium | Use ESLint; test build after each phase |
| R6 | Backend StaticFiles still serving old index.html | Low | Medium | After build: verify ops_router.py StaticFiles path points to `dist/` not root |
| R7 | `bi_token` / `bi_refresh` localStorage keys preserved | Low | High | api.js uses same key names as legacy code |

**Rollback strategy:**
1. **Git baseline**: Commit original `frontend/parent_app/` before any changes.
2. **Phase-by-phase commits**: Commit after each phase passes verification.
3. **Rollback**: `git checkout main -- frontend/parent_app/`
4. **Never remove legacy index.html** until React app fully verified on login+all tabs.

### 10. Verification Steps

**After api.js complete:**
```
[ ] doLogin/doLogout work (JWT stored in localStorage bi_token/bi_refresh)
[ ] apiFetch sends Authorization header
[ ] 401 triggers refresh → retry → logout if refresh fails
[ ] connectWebSocket fires onEvent callback with realtime events
[ ] startMomMic / stopMomMic call correct endpoints
[ ] getConversations / getConversation return data
```

**Per-tab checklist (after each page component):**
```
[ ] Tab renders loading → data → renders without crash
[ ] All API calls use Tier 1 endpoints only (no 404 in console)
[ ] Mock sections show correct badge type
[ ] Empty/error states render correctly
[ ] Mobile 375px — no overflow, readable text
```

**Final verification checklist:**
```
[ ] SC-001: Trang chủ renders in <3s without scroll (desktop 1280px)
[ ] SC-002: All existing features work (auth, WS, camera, music, games, conversations)
[ ] SC-003: Zero 404/500 console errors
[ ] SC-004: font ≥16px everywhere; contrast ≥4.5:1; buttons ≥48px
[ ] SC-005: All tabs have loading, error, empty states
[ ] SC-006: 375px layout correct (bottom nav functional, no overflow)
[ ] SC-007: Sidebar bottom order: Robot status → User card → Cài đặt → Đăng xuất
[ ] npm run build: no errors
[ ] python tests/run_tests.py: passes (backend regression clean)
```

### 11. SYSTEM_MAP.md Update Strategy After Implementation

**When**: AFTER all phases complete and verification passes.

**What to update** (Section 6 — Frontend Structure):

```
frontend/parent_app/ contains a React + Vite SPA. Source in src/; build output in dist/.
- Navigation: 5-tab sidebar (Trang chủ, Giám sát, Học tập, Nhật ký, Thêm) + mobile bottom nav.
  Sidebar bottom order: RobotStatusCard → UserCard → Cài đặt → Đăng xuất.
- Design system: "Công nghệ ấm áp" — Be Vietnam Pro font, 16px body, 48px tap targets, WCAG AA.
- Settings overlay: full-screen panel with Hồ sơ trẻ, Thông báo, Giờ hoạt động,
  Nội dung & An toàn, Kết nối thiết bị, Chế độ kỹ thuật (admin only).
- Tier 1 APIs active: [list same as spec FR-016 to FR-045 implemented ones].
- Tier 2 UI placeholders (backend not yet implemented): [list Tier 2 features].
  All marked with "Sắp hỗ trợ", "Dữ liệu mẫu", or "Chưa kết nối backend" badges.
```

---

## Implementation Phases Summary

| Phase | Goal | Files touched | Risk |
|---|---|---|---|
| 0 | Git baseline + preservation audit | none (read-only) | None |
| 1 | Vite project setup | package.json, vite.config.js, index.html (shell) | Low |
| 2 | Service layer + mock data | src/services/api.js, src/data/mockData.js | High (protected behavior) |
| 3 | Design system | src/styles.css | Low |
| 4 | Layout shell + navigation | src/App.jsx, src/main.jsx, src/components/Sidebar.jsx, BottomNav.jsx, RobotStatusCard.jsx, UserCard.jsx | Medium |
| 5 | LoginPage | src/pages/LoginPage.jsx | Medium (auth protected) |
| 6 | Trang chủ | src/pages/HomePage.jsx | Low |
| 7 | Nhật ký | src/pages/JournalPage.jsx | Low |
| 8 | Giám sát | src/pages/MonitorPage.jsx | Medium (camera, WS) |
| 9 | Học tập | src/pages/LearningPage.jsx | Low |
| 10 | Thêm | src/pages/MorePage.jsx | Low |
| 11 | Cài đặt overlay | src/components/SettingsOverlay.jsx | Low |
| 12 | Responsive + accessibility pass | src/styles.css + components | Low |
| 13 | Final QA + SYSTEM_MAP update | SYSTEM_MAP.md, .claude/handoff.md | None |

---

*Plan updated: 2026-05-13 | Target: React + Vite | Branch: 001-parent-app-redesign | Spec: specs/001-parent-app-redesign/spec.md*
