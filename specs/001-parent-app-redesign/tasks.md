# Tasks: Redesign Giao Diện Parent App Robot Bi

**Input**: Design documents from `specs/001-parent-app-redesign/`

**Prerequisites**: plan.md ✓ | spec.md ✓ | research.md ✓ | data-model.md ✓

**Target stack**: React + Vite
**Tests**: Không có automated test tasks (frontend UI, kiểm tra thủ công + `npm run build`).
**Scope**: `frontend/parent_app/` — package.json, vite.config.js, index.html (Vite shell), src/.
**Hard boundaries**: Không sửa src/, firmware/, frontend/robot_display/, tests/, runtime/, logs/, .env, root .md files.

## Format: `[ID] [P?] [Story?] Description — file`

- **[P]**: Có thể chạy song song (không phụ thuộc nhau)
- **[USn]**: User Story trong spec.md (US1–US5)

---

## Phase 1: Audit & Preservation Map

**Purpose**: Hiểu rõ behavior cần bảo tồn trước khi thay legacy code. Không viết code trong phase này.

**Goal**: Preservation checklist hoàn chỉnh — biết chính xác hàm nào cần tái hiện trong api.js.

- [ ] T001 Đọc `frontend/parent_app/index.html` và liệt kê: (a) tất cả function JS được export/gọi từ HTML, (b) tất cả API endpoints được gọi (`apiFetch`/`fetch`), (c) WebSocket behavior (`connectWS`, `setStatus`, `onRealtimeEvent`), (d) localStorage keys được đọc/ghi, (e) HTML element IDs được dùng trong JS — `frontend/parent_app/index.html` (read only)

- [ ] T002 Xác nhận rằng các hàm protected sau tồn tại và ghi rõ dòng số + behavior: `doLogin`, `doLogout`, `tryRefreshToken`, `apiFetch`, `connectWS`, `setStatus`, `startMomMic`, `stopMomMic`, `loadThreads`, `showThreadDetail`, `toast` — `frontend/parent_app/index.html` (read only)

- [ ] T003 Liệt kê tất cả API call URLs từ code (`apiFetch('/api/...')`) để tạo Tier 1 list; xác nhận không có endpoint nào đang được gọi là non-existing — `frontend/parent_app/index.html` (read only)

**Checkpoint Phase 1**: Preservation map hoàn chỉnh. Biết chính xác hàm và endpoint cần tái hiện trong api.js. Chỉ bắt đầu Phase 2 sau khi T001–T003 xong.

---

## Phase 2: Vite Project Setup

**Purpose**: Tạo scaffolding React+Vite. Legacy `index.html` chưa bị thay trong phase này.

**Goal**: `npm run dev` và `npm run build` chạy được; Vite shell render `<div id="root">`.

- [ ] T004 Tạo `frontend/parent_app/package.json` với dependencies: `react@^18`, `react-dom@^18`; devDependencies: `@vitejs/plugin-react@^4`, `vite@^5`; scripts: `dev: vite`, `build: vite build`, `preview: vite preview` — `frontend/parent_app/package.json`

- [ ] T005 Tạo `frontend/parent_app/vite.config.js`: import `defineConfig` từ vite và `react` từ @vitejs/plugin-react; config: `plugins: [react()]`, `base: './'`, `build: { outDir: 'dist' }` — `frontend/parent_app/vite.config.js`

- [ ] T006 Thay `frontend/parent_app/index.html` bằng Vite mount shell: minimal HTML5 boilerplate với `<meta charset="UTF-8">`, `<meta name="viewport" content="width=device-width,initial-scale=1">`, `<title>Robot Bi</title>`, `<div id="root"></div>`, `<script type="module" src="/src/main.jsx"></script>` — GIỮ NGUYÊN sau khi api.js đã verify (Phase 3 checkpoint trước) — `frontend/parent_app/index.html`

- [ ] T007 Tạo `frontend/parent_app/src/main.jsx`: import React, ReactDOM, App, styles.css; `ReactDOM.createRoot(document.getElementById('root')).render(<App />)` — `frontend/parent_app/src/main.jsx`

**Checkpoint Phase 2**: `npm install && npm run build` thành công (App.jsx có thể là placeholder). Không cần backend connection ở bước này.

---

## Phase 3: Service Layer & Mock Data

**Purpose**: Tái hiện đúng tất cả protected behavior từ legacy index.html vào api.js. Phase này là HIGH RISK — phải verify kỹ trước khi tiếp.

**Goal**: Mọi Tier 1 function trong api.js hoạt động đúng như legacy counterpart. Mock adapters cho Tier 2 features không gây 404.

- [ ] T008 Tạo `frontend/parent_app/src/services/api.js` — Phần 1: Auth functions: `login(username, password)` (POST /api/auth/login, store bi_token/bi_refresh, return {username, isAdmin}), `logout()` (POST /api/auth/logout, clear localStorage), `refreshToken()` (POST /api/auth/refresh, update bi_token), `apiFetch(path, opts)` (add Authorization header, 401 → refreshToken → retry → logout if fail) — `frontend/parent_app/src/services/api.js`

- [ ] T009 Cập nhật `src/services/api.js` — Phần 2: WebSocket function: `connectWebSocket(onEvent, onStatusChange)` — mở `wss://{host}/ws?token={token}`, gọi `onStatusChange('online')` khi connect, `onStatusChange('offline')` khi disconnect/error, gọi `onEvent(data)` cho mỗi message; thêm `disconnectWebSocket()` — `frontend/parent_app/src/services/api.js`

- [ ] T010 Cập nhật `src/services/api.js` — Phần 3: Mom-talk audio functions: `startMomMic()` (POST /api/mom/start + open mom audio WebSocket `wss://host/api/mom/audio?token=...`), `stopMomMic()` (POST /api/mom/stop + close mom WS). Conversation functions: `getConversations()` (GET /api/conversations), `getConversation(id)` (GET /api/conversations/{id}) — `frontend/parent_app/src/services/api.js`

- [ ] T011 Cập nhật `src/services/api.js` — Phần 4: Toast helper: `export let toastFn = null; export function registerToast(fn) { toastFn = fn; } export function showToast(msg) { toastFn && toastFn(msg); }`. Utility: `getBaseUrl()` trả về `window.location.origin` — `frontend/parent_app/src/services/api.js`

- [ ] T012 Tạo `frontend/parent_app/src/data/mockData.js` với các mock data Vietnamese realistic: `mockChildProfiles()` (2 profiles: Bé Minh 8t, Bé Lan 6t), `mockRadioChannels()` (5 kênh: VOV1 Quốc gia, VOV2 Văn hóa...), `mockVideoLessons()` (3 video: Toán lớp 2, Tiếng Việt...), `mockMonthlyEmotions()` (4 tuần data), `mockInteractiveGames()` (3 trò: Ghép chữ, Đố vui...), `mockSystemLogs()` (5 log entries) — `frontend/parent_app/src/data/mockData.js`

- [ ] T013 Cập nhật `src/services/api.js` — Phần 5: Mock adapter functions cho Tier 2 features (xem mock adapter list trong plan.md Section 5): `getChildProfiles()`, `exportReport(fmt)`, `getMonthlyEmotions(m)`, `getRoomLocation()`, `getRadioChannels()`, `getVideoLessons()`, `getInteractiveGames()`, `getSystemLogs()`, `savePushSettings(s)`, `saveSleepSchedule(s)`, `saveTimeLimits(l)`, `saveAgeFilter(f)`, `getParentChatHistory()` — mỗi function log `[MOCK] feature: using mock data` và return mock data từ mockData.js — `frontend/parent_app/src/services/api.js`

**Checkpoint Phase 3**: Verify manually: login() gọi đúng endpoint → token stored → apiFetch('/api/status') returns data → logout() clears tokens. connectWebSocket onEvent fires. Không có 404 trong Network tab. CHỈ sau khi pass mới replace index.html (T006).

---

## Phase 4: Design System

**Purpose**: CSS foundation — tokens, typography, base styles.

**Goal**: Tất cả design tokens có giá trị đúng; body font 16px, Be Vietnam Pro loads; button tap targets ≥48px.

- [ ] T014 Tạo `frontend/parent_app/src/styles.css`: thêm `@import url(...)` cho Be Vietnam Pro (weights 400/500/600/700/800/900), CSS `:root` block với tất cả design tokens theo plan.md Section 4 (`--primary`, `--primary-dark`, `--accent`, `--success`, `--warning`, `--danger`, `--info`, `--bg`, `--card`, `--border`, `--text`, `--text-secondary`, `--muted`, `--radius-lg/md/sm`, `--shadow`, `--side-w`, `--nav-h`, `--font-body/btn/section/heading`, `--tap-min`) — `frontend/parent_app/src/styles.css`

- [ ] T015 Thêm vào `src/styles.css`: base styles: `* { box-sizing: border-box; margin: 0; padding: 0; }`, `body { font-family: 'Be Vietnam Pro', system-ui, sans-serif; font-size: var(--font-body); background: var(--bg); color: var(--text); }`, `button { min-height: var(--tap-min); cursor: pointer; }`, `a { min-height: var(--tap-min); }` — `frontend/parent_app/src/styles.css`

- [ ] T016 [P] Thêm vào `src/styles.css`: feature badge styles — `.feature-badge` base (font-size 11px, font-weight 700, padding 2px 8px, border-radius 20px, border 1.5px solid, display inline-block); `.feature-badge.coming-soon` (bg #f1f5f9, color #94a3b8, border #e2e8f0); `.feature-badge.mock-data` (bg #fffbeb, color #b45309, border #fcd34d); `.feature-badge.no-backend` (bg #fef2f2, color #dc2626, border #fca5a5) — `frontend/parent_app/src/styles.css`

- [ ] T017 [P] Thêm vào `src/styles.css`: state styles — `.section-state` (text-align center, padding 24px 16px, color var(--muted)); `.section-state .state-icon` (font-size 36px, display block, margin-bottom 10px); `.section-state.error .retry-btn` (background var(--primary), color white, border-radius var(--radius-sm), padding 10px 20px, font-size 16px, margin-top 12px, min-height var(--tap-min), border none); card styles: `.card` (background var(--card), border-radius var(--radius-lg), border 1px solid var(--border), box-shadow var(--shadow), padding 20px) — `frontend/parent_app/src/styles.css`

- [ ] T018 Thêm vào `src/styles.css`: responsive layout — `.app-layout` (display flex, min-height 100vh); `.side-nav` (display none — mobile default); `.bottom-nav` (display flex, position fixed, bottom 0, width 100%, height var(--nav-h), bg var(--card), border-top 1px solid var(--border)); `.main-content` (flex 1, padding-bottom calc(var(--nav-h) + 12px)); `@media (min-width: 768px)` block: `.side-nav` (display flex, flex-direction column, width var(--side-w), min-height 100vh, bg var(--card), border-right 1px solid var(--border), position fixed, left 0, top 0); `.bottom-nav` (display none); `.main-content` (margin-left var(--side-w), padding-bottom 24px) — `frontend/parent_app/src/styles.css`

**Checkpoint Phase 4**: Import styles.css trong App.jsx, check browser — font loads, background #f3f7ff, no layout errors.

---

## Phase 5: Layout Shell & Navigation

**Purpose**: App shell với sidebar, bottom nav, routing logic.

**Goal**: 5 tabs switch đúng; sidebar bottom order locked; robot status card nhận state từ WS.

- [ ] T019 Tạo `frontend/parent_app/src/App.jsx`: top-level component với state (xem data-model.md App.jsx state), useEffect gọi `connectWebSocket(handleWsEvent, setRobotStatus)` sau login, render `<LoginPage>` nếu chưa login, render layout shell (Sidebar + main content + BottomNav + SettingsOverlay + Toast) nếu đã login — `frontend/parent_app/src/App.jsx`

- [ ] T020 Tạo `frontend/parent_app/src/components/RobotStatusCard.jsx`: nhận prop `status` ('online'|'offline'|'connecting'), render card với dot, label, sub-label. CSS classes: `.robot-status-card` base + `.robot-status-card.online` (border #86efac, bg #f0fdf4), `.offline` (border #fca5a5, bg #fef2f2), `.connecting` (border #fcd34d, bg #fffbeb). Online → "Đang hoạt động", offline → "Mất kết nối", connecting → "Đang kết nối..." — `frontend/parent_app/src/components/RobotStatusCard.jsx`

- [ ] T021 Tạo `frontend/parent_app/src/components/UserCard.jsx`: nhận props `user` ({username, isAdmin}) và `activeChild`. Render: avatar emoji (👤 default), username, role ("Admin" nếu isAdmin, "Phụ huynh" otherwise), child name nếu có. onClick → prop `onSwitchChild()` — `frontend/parent_app/src/components/UserCard.jsx`

- [ ] T022 Tạo `frontend/parent_app/src/components/Sidebar.jsx`: nhận props `activeTab`, `onTabChange`, `robotStatus`, `user`, `activeChild`, `onOpenSettings`, `onLogout`, `onSwitchChild`. Render: logo "🤖 Robot Bi", 5 nav buttons (Trang chủ/Giám sát/Học tập/Nhật ký/Thêm), bottom section (RobotStatusCard → UserCard → Cài đặt button → Đăng xuất button) theo đúng thứ tự locked — `frontend/parent_app/src/components/Sidebar.jsx`

- [ ] T023 Tạo `frontend/parent_app/src/components/BottomNav.jsx`: nhận props `activeTab`, `onTabChange`. Render 5 tab buttons (icon + Vietnamese label ≤4 chars: Nhà/Giám sát/Học/Nhật ký/Thêm), min-height 56px, active highlight — `frontend/parent_app/src/components/BottomNav.jsx`

- [ ] T024 [P] Tạo `frontend/parent_app/src/components/FeatureBadge.jsx`: nhận prop `type` ('coming-soon'|'mock-data'|'no-backend'), render `<span className={'feature-badge ' + type}>` với label đúng: "Sắp hỗ trợ" / "Dữ liệu mẫu" / "Chưa kết nối backend" — `frontend/parent_app/src/components/FeatureBadge.jsx`

- [ ] T025 [P] Tạo `frontend/parent_app/src/components/SectionState.jsx`: nhận props `state` ('loading'|'error'|'empty'), `loadingText`, `errorText`, `emptyText`, `emptyIcon`, `onRetry`. Render tương ứng: spinner + text / ⚠️ + text + retry button / icon + text — `frontend/parent_app/src/components/SectionState.jsx`

- [ ] T026 [P] Tạo `frontend/parent_app/src/components/Toast.jsx`: nhận prop `message`, render fixed toast overlay; auto-dismiss sau 3s. Register `showToast` via `registerToast()` từ api.js trong useEffect — `frontend/parent_app/src/components/Toast.jsx`

**Checkpoint Phase 5**: Đăng nhập → 5 tabs switch hoạt động → sidebar đúng thứ tự → robot status card show 'connecting' → user card show username.

---

## Phase 6: LoginPage

**Purpose**: Trang đăng nhập bảo tồn đúng behavior của doLogin/doLogout.

**Goal**: Login với username/password → JWT stored → App state updated → chuyển sang app layout.

- [ ] T027 [US1] Tạo `frontend/parent_app/src/pages/LoginPage.jsx`: form đăng nhập với input username, input password, button "Đăng nhập" (min-height 48px, font-size 18px). Submit gọi `login(username, password)` từ api.js → nếu success gọi `props.onLogin({username, isAdmin})` → nếu fail hiện error message. Thêm CSS `.login-page` vào styles.css — `frontend/parent_app/src/pages/LoginPage.jsx`

**Checkpoint Phase 6**: Login với tài khoản thật → JWT được lưu vào localStorage → app layout hiện ra → logout xóa token → login page hiện lại.

---

## Phase 7: Trang chủ — US1

**Goal**: Phụ huynh thấy trạng thái robot + tóm tắt trong 3 giây, không cần scroll (desktop 1280px).

**Independent Test**: Mở Trang chủ → robot status badge visible → today grid 4 metrics → weekly report card tải từ /api/analytics/weekly → room location card có badge → recent events list.

- [ ] T028 [US1] Tạo `frontend/parent_app/src/pages/HomePage.jsx`: layout với hero header (robot status badge, greeting "Xin chào {username}!"), today summary grid (4 metrics: sessions, learning time, emotion, tasks), weekly report card, room location card, recent events list. useEffect gọi `apiFetch('/api/analytics/weekly')` và `apiFetch('/api/events')` — `frontend/parent_app/src/pages/HomePage.jsx`

- [ ] T029 [US1] Thêm weekly report card vào HomePage: gọi `/api/analytics/weekly`, render total_sessions, total_minutes, homework_count, task_completion. `<SectionState state="loading">` khi tải, `<SectionState state="error" onRetry=...>` khi lỗi, `<SectionState state="empty">` khi không có data — `frontend/parent_app/src/pages/HomePage.jsx`

- [ ] T030 [US1] Thêm room location card vào HomePage: card với `<FeatureBadge type="coming-soon" />`, text "Tính năng định vị phòng đang được phát triển" — KHÔNG gọi API — `frontend/parent_app/src/pages/HomePage.jsx`

- [ ] T031 [US1] Thêm alert card vào HomePage: ẩn mặc định; hiện khi nhận realtime event type 'safety_filter' hoặc 'cry' từ `props.lastEvent`; card CSS background #fffbeb, border #fcd34d — `frontend/parent_app/src/pages/HomePage.jsx`

- [ ] T032 [US1] Thêm recent events list vào HomePage: gọi `/api/events`, render 5 events gần nhất, loading/error/empty states, empty text "Bi đang chờ bé ra chơi! 🤖" — `frontend/parent_app/src/pages/HomePage.jsx`

- [ ] T033 [P] [US1] Thêm CSS vào `src/styles.css` cho HomePage: `.home-hero` gradient header, `.today-grid` (2 cột mobile / 4 cột desktop), `.metric-card` (bg white, radius var(--radius-md), padding 16px), `.metric-num` (font-size 24px, font-weight 700), `.metric-label` (font-size 13px, color var(--text-secondary)) — `frontend/parent_app/src/styles.css`

**Checkpoint Phase 7**: Trang chủ load → weekly report từ API → today grid render → alert card hidden → room location badge đúng. Không 404.

---

## Phase 8: Nhật ký — US2

**Goal**: Tab Nhật ký có timeline sự kiện + bộ lọc client-side + mock features với badge đúng.

**Independent Test**: Mở Nhật ký → events tải → filter theo loại hoạt động → export button toast coming-soon → monthly chart với mock-data badge.

- [ ] T034 [US2] Tạo `frontend/parent_app/src/pages/JournalPage.jsx`: layout với filter bar (type select + date input), conversations list, events list, memories section, emotion monthly chart, export button — `frontend/parent_app/src/pages/JournalPage.jsx`

- [ ] T035 [US2] Thêm filter bar vào JournalPage: `<select>` với options (Tất cả / Trò chuyện / Sự kiện / Bài tập), `<input type="date">` optional; filter chạy client-side trên data đã load — KHÔNG gọi API mới — `frontend/parent_app/src/pages/JournalPage.jsx`

- [ ] T036 [US2] Thêm conversations list vào JournalPage: gọi `getConversations()` từ api.js (GET /api/conversations), render thread list; nhấn item gọi `getConversation(id)` và mở detail modal — `frontend/parent_app/src/pages/JournalPage.jsx`

- [ ] T037 [US2] Thêm emotion monthly chart vào JournalPage: gọi `getMonthlyEmotions()` từ api.js (mock), render CSS bar chart từ 4-week mock data, `<FeatureBadge type="mock-data" />` — KHÔNG gọi API thật — `frontend/parent_app/src/pages/JournalPage.jsx`

- [ ] T038 [US2] Thêm export button vào JournalPage header: button "📤 Xuất PDF/CSV" min-height 48px; click handler: `showToast('Xuất báo cáo: Tính năng đang phát triển')` + `<FeatureBadge type="coming-soon" />` hiện gần button — KHÔNG gọi API — `frontend/parent_app/src/pages/JournalPage.jsx`

- [ ] T039 [P] [US2] Thêm parent notes UI inline vào mỗi event item: small "📝 Ghi chú" button; click toggle textarea; submit: `showToast('Ghi chú: Sắp hỗ trợ')` — KHÔNG POST API — `frontend/parent_app/src/pages/JournalPage.jsx`

- [ ] T040 [P] [US2] Thêm audio playback disabled button vào mỗi conversation item: `<button disabled title="Sắp hỗ trợ">▶ Phát lại</button>`, opacity 0.4, cursor not-allowed — `frontend/parent_app/src/pages/JournalPage.jsx`

- [ ] T041 [US2] Thêm "Bộ lọc nâng cao" button vào filter bar: click hiện dropdown với `<FeatureBadge type="coming-soon" />` và text "Lọc theo thiết bị — Sắp hỗ trợ" — KHÔNG gọi API — `frontend/parent_app/src/pages/JournalPage.jsx`

**Checkpoint Phase 8**: Tab Nhật ký: filter bar hoạt động, conversations tải, emotion chart mock badge đúng, export toast, audio disabled, advanced filter badge. Không 404.

---

## Phase 9: Giám sát — US2 secondary

**Goal**: Tab Giám sát với camera feed + weekly report detail + mom-talk + motor control.

**Independent Test**: Mở Giám sát → camera section (hoặc unavailable placeholder) → weekly report detail từ API → mom-talk button visible.

- [ ] T042 [US2] Tạo `frontend/parent_app/src/pages/MonitorPage.jsx`: layout với camera section, mom-talk controls, weekly report detail card, emotion summary, motor control panel, recent conversations — `frontend/parent_app/src/pages/MonitorPage.jsx`

- [ ] T043 [US2] Thêm camera section vào MonitorPage: render `<img src="/api/camera">` cho MJPEG; nếu lỗi hiện "Camera không khả dụng" placeholder; nút "Bật Camera" / "Tắt Camera" gọi toggle state — `frontend/parent_app/src/pages/MonitorPage.jsx`

- [ ] T044 [US2] Thêm mom-talk controls vào MonitorPage: button "🎤 Nói chuyện với Bi" gọi `startMomMic()`, button "⏹ Dừng" gọi `stopMomMic()` — behavior giống hệt legacy — `frontend/parent_app/src/pages/MonitorPage.jsx`

- [ ] T045 [US2] Thêm weekly report detail vào MonitorPage: gọi `/api/analytics/weekly`, render breakdown đầy đủ (sessions, minutes, emotion bar); loading/error/empty states — `frontend/parent_app/src/pages/MonitorPage.jsx`

- [ ] T046 [P] [US2] Thêm motor control panel vào MonitorPage: direction buttons (lên/xuống/trái/phải/dừng), speed control; mỗi button gọi `apiFetch('/api/motor/move', {...})` — giữ nguyên endpoint behavior — `frontend/parent_app/src/pages/MonitorPage.jsx`

**Checkpoint Phase 9**: Giám sát tab: camera loads/placeholder, mom-talk buttons fire API, weekly report detail, motor controls functional.

---

## Phase 10: Học tập

**Goal**: Tab Học tập với flashcards, vocab, stories, quiz games, tasks, chat với Bi placeholder.

- [ ] T047 Tạo `frontend/parent_app/src/pages/LearningPage.jsx`: sections: Progress Overview, Flashcard session, Vocabulary grid, Learning schedule, Stories, Luyện tập (word quiz / voice quiz), Task list, Chat với Bi placeholder — `frontend/parent_app/src/pages/LearningPage.jsx`

- [ ] T048 Thêm flashcard + vocab + stories sections vào LearningPage: gọi `/api/education/vocabulary`, `/api/stories`, `/api/education/schedule` — render grids/lists; loading/error/empty states — `frontend/parent_app/src/pages/LearningPage.jsx`

- [ ] T049 Thêm quiz games section "Luyện tập" vào LearningPage: "Bắt đầu Word Quiz" gọi `/api/game/word-quiz/start`, "Bắt đầu Voice Quiz" gọi `/api/game/voice-quiz/start` — giữ nguyên game flow — `frontend/parent_app/src/pages/LearningPage.jsx`

- [ ] T050 Thêm task list vào LearningPage: gọi `/api/tasks`, render tasks với completion toggle (PUT /api/tasks/{id}/complete) và star count — `frontend/parent_app/src/pages/LearningPage.jsx`

- [ ] T051 [P] Thêm "Chat với Bi" section vào LearningPage: card với `<FeatureBadge type="coming-soon" />`, text "Lịch sử chat phụ huynh ↔ Bi — Sắp hỗ trợ" — KHÔNG gọi API — `frontend/parent_app/src/pages/LearningPage.jsx`

**Checkpoint Phase 10**: Học tập tab: vocab/stories/schedule tải từ API, quiz buttons fire, tasks render, chat placeholder badge đúng.

---

## Phase 11: Thêm — US4

**Goal**: Tab Thêm với Music player (API hiện có) + Radio/Video/Games placeholders với badge.

**Independent Test**: Mở Thêm → Music player controls functional → Radio/Video/Games badge "Dữ liệu mẫu"/"Sắp hỗ trợ" → không 404.

- [ ] T052 [US4] Tạo `frontend/parent_app/src/pages/MorePage.jsx`: sections: Music player (API hiện có), Radio (mock), Video học (mock), Trò chơi tương tác (coming-soon) — `frontend/parent_app/src/pages/MorePage.jsx`

- [ ] T053 [US4] Thêm music player section vào MorePage: gọi `/api/music/status` để load state, buttons play/pause/next/prev/shuffle/volume gọi `/api/music/*` — giữ nguyên music API behavior — `frontend/parent_app/src/pages/MorePage.jsx`

- [ ] T054 [US4] Thêm Radio section vào MorePage: gọi `getRadioChannels()` (mock), render channel list với `<FeatureBadge type="mock-data" />`, play button hiện toast "Radio: Sắp hỗ trợ" — KHÔNG gọi audio API — `frontend/parent_app/src/pages/MorePage.jsx`

- [ ] T055 [US4] Thêm Video học section vào MorePage: gọi `getVideoLessons()` (mock), render video cards với `<FeatureBadge type="mock-data" />`, play button hiện toast "Video: Sắp hỗ trợ" — KHÔNG stream video — `frontend/parent_app/src/pages/MorePage.jsx`

- [ ] T056 [P] [US4] Thêm Trò chơi tương tác section vào MorePage: card với `<FeatureBadge type="coming-soon" />`, gọi `getInteractiveGames()` (mock), render game cards disabled — `frontend/parent_app/src/pages/MorePage.jsx`

**Checkpoint Phase 11**: Thêm tab: music player controls functional, radio/video mock data visible với đúng badge, games coming-soon. Không 404.

---

## Phase 12: Cài đặt — US3 & US5

**Goal**: Settings overlay với đầy đủ sections, admin section chỉ hiện với isAdmin.

**Independent Test**: Nhấn Cài đặt → overlay mở → cuộn qua các section → form có label tiếng Việt → badge đúng → Chế độ kỹ thuật chỉ hiện với admin.

- [ ] T057 [US3] Tạo `frontend/parent_app/src/components/SettingsOverlay.jsx`: full-screen overlay panel (z-index 500), close button, 6 sections: (1) Hồ sơ trẻ [mock-data], (2) Thông báo & Nhắc nhở [coming-soon], (3) Giờ hoạt động robot [coming-soon], (4) Nội dung & An toàn [coming-soon], (5) Kết nối thiết bị / QR [coming-soon], (6) Chế độ kỹ thuật (chỉ hiện khi `props.isAdmin`) — `frontend/parent_app/src/components/SettingsOverlay.jsx`

- [ ] T058 [US3] Thêm Hồ sơ trẻ section vào SettingsOverlay: gọi `getChildProfiles()` (mock), render profile cards với badge "Dữ liệu mẫu"; "Thêm hồ sơ" button hiện toast "Quản lý hồ sơ: Sắp hỗ trợ" — KHÔNG POST API — `frontend/parent_app/src/components/SettingsOverlay.jsx`

- [ ] T059 [US3] Thêm sleep schedule + time limits + age filter sections vào SettingsOverlay: time-picker, slider, toggle group UIs với `<FeatureBadge type="coming-soon" />` và save handlers: `showToast('... Sắp hỗ trợ')` — KHÔNG POST API — `frontend/parent_app/src/components/SettingsOverlay.jsx`

- [ ] T060 [US3] Thêm QR code section vào SettingsOverlay: placeholder div với `<FeatureBadge type="coming-soon" />` và text "Mã QR kết nối thiết bị — Sắp hỗ trợ" — KHÔNG gọi API — `frontend/parent_app/src/components/SettingsOverlay.jsx`

- [ ] T061 [US5] Thêm Chế độ kỹ thuật section vào SettingsOverlay (chỉ render khi `props.isAdmin`): (a) System logs: gọi `getSystemLogs()` (mock), render với `<FeatureBadge type="no-backend" />`; (b) Persona settings: gọi `/api/persona` thật; (c) Admin families: gọi `/api/admin/families` thật; render với loading/error/empty states — `frontend/parent_app/src/components/SettingsOverlay.jsx`

- [ ] T062 [P] Thêm CSS vào `src/styles.css` cho SettingsOverlay: `.settings-overlay` (position fixed, inset 0, z-index 500, bg rgba(0,0,0,.5), display flex, align-items flex-end @mobile / justify-content flex-end @desktop); `.settings-panel` (bg var(--card), border-radius var(--radius-lg) var(--radius-lg) 0 0 @mobile / width 480px height 100% @desktop, overflow-y auto, padding 24px); `.settings-section-title` (font-size var(--font-section), font-weight 700, margin-bottom 12px) — `frontend/parent_app/src/styles.css`

**Checkpoint Phase 12**: Settings overlay mở/đóng, 6 sections visible, badges đúng, admin section chỉ hiện khi isAdmin, persona + families APIs call thật.

---

## Phase 13: Responsive & Accessibility Pass

**Goal**: Đảm bảo 375px mobile layout đúng; font/contrast/tap targets đúng spec.

- [ ] T063 Kiểm tra toàn bộ app ở 375px (Chrome DevTools): sidebar ẩn → bottom nav hiện đủ 5 tabs → không có horizontal overflow → tất cả cards readable → buttons ≥48px — update CSS nếu bất kỳ item nào fail — `frontend/parent_app/src/styles.css`

- [ ] T064 Kiểm tra desktop 1280px: sidebar visible, bottom nav ẩn, Trang chủ render không cần scroll, tất cả 5 tabs functional — fix layout issues nếu có — `frontend/parent_app/src/styles.css`

- [ ] T065 [P] Verify font sizes: body ≥16px, buttons ≥18px, section titles ≥20px, page headings ≥24px; contrast ≥4.5:1 cho essential text; không có icon-only buttons cho action quan trọng — kiểm tra qua DevTools, sửa CSS nếu cần — `frontend/parent_app/src/styles.css`

- [ ] T066 [P] Verify tất cả screens có loading/error/empty states: đặc biệt HomePage (weekly report + events), JournalPage (conversations + events), MonitorPage (camera + weekly), LearningPage (vocab + tasks) — kiểm tra và bổ sung `<SectionState>` nếu thiếu — các page files trong `src/pages/`

**Checkpoint Phase 13**: App chạy đúng trên 375px và 1280px. Font/contrast/tap targets pass. Tất cả sections có 3 states.

---

## Phase 14: Build Verification

**Goal**: `npm run build` thành công; không có console errors; tất cả Tier 1 APIs functional.

- [ ] T067 Chạy `npm run build` trong `frontend/parent_app/` — fix bất kỳ build error nào (JSX syntax, import paths, undefined vars) — `frontend/parent_app/src/`

- [ ] T068 Mở browser, đăng nhập, kiểm tra Network tab: không có 404/500 nào; tất cả Tier 1 API calls return data; không có mock function tự gọi real endpoint — `frontend/parent_app/src/services/api.js`

- [ ] T069 Chạy `python tests/run_tests.py` — xác nhận backend tests vẫn pass (không có regression từ frontend change) — `tests/run_tests.py` (read-only check)

**Checkpoint Phase 14**: Build success, zero 404/500 console errors, backend tests pass.

---

## Phase 15: SYSTEM_MAP.md Update & Handoff

**Goal**: Cập nhật tài liệu phản ánh đúng thực trạng sau implementation.

- [ ] T070 Cập nhật `SYSTEM_MAP.md` Section 6 (Frontend Structure): thay mô tả legacy bằng React+Vite implementation đúng theo plan.md Section 11 format. Mô tả Tier 1 APIs active và Tier 2 UI placeholders với badge. KHÔNG claim backend features chưa implement là done — `SYSTEM_MAP.md`

- [ ] T071 Cập nhật `frontend/parent_app/` entry trong SYSTEM_MAP.md Section 6 file table để phản ánh đúng cấu trúc mới: `src/`, `dist/`, `package.json`, `vite.config.js`, `index.html` (Vite shell) — `SYSTEM_MAP.md`

- [ ] T072 Cập nhật `.claude/handoff.md`: Last Completed Task, Files Recently Touched — `.claude/handoff.md`

**Checkpoint Phase 15**: SYSTEM_MAP.md mô tả đúng React+Vite implementation. Handoff updated.

---

## Dependency Graph

```
Phase 1 (Audit) → Phase 2 (Vite setup) → Phase 3 (api.js) → Phase 4 (CSS) → Phase 5 (Layout)
                                                                                      ↓
Phase 6 (Login) ←──────────────────────────────────────────────────────────────── Phase 5
                ↓
Phase 7 (Trang chủ) ]
Phase 8 (Nhật ký)   ]  ← Phase 5 (layout) + Phase 3 (api.js) + Phase 4 (CSS)
Phase 9 (Giám sát)  ]  — Phases 7-11 CÓ THỂ làm song song sau khi Phase 6 done
Phase 10 (Học tập)  ]
Phase 11 (Thêm)     ]
Phase 12 (Cài đặt)  ]
                ↓
Phase 13 (Responsive) → Phase 14 (Build verification) → Phase 15 (SYSTEM_MAP)
```

## Parallel Execution

Phases 7–12 (page components) có thể làm song song sau khi Phases 3–6 hoàn thành:
- Agent A: HomePage + JournalPage
- Agent B: MonitorPage + LearningPage
- Agent C: MorePage + SettingsOverlay

Trong mỗi phase, tasks đánh dấu `[P]` có thể chạy song song.

## Implementation Strategy

**MVP scope (minimum to verify migration works)**:
1. Phase 1–6: Audit + Vite setup + api.js + Layout + Login
2. Phase 7: HomePage (US1 core)
3. Phase 14: Build verification

**Full scope**: All phases T001–T072.

---

*Tasks updated: 2026-05-13 | Target: React + Vite migration | Feature: 001-parent-app-redesign*
