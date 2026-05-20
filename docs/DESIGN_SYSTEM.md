# DESIGN_SYSTEM.md — Design System Parent App Robot Bi

> Phiên bản: 1.0 | Cập nhật: 2026-05-15
> Source of truth cho design tokens, component patterns, và UI rules của Parent App.
> AI agent phải đọc file này trước khi viết bất kỳ CSS hay JSX nào cho frontend.
> Cập nhật khi thay đổi design tokens, thêm component mới, hoặc thay đổi layout rules.

---

## 1. Stack và Entry Points

| Item | Value |
|---|---|
| Framework | React 18 + Vite 5 |
| Styles | CSS thuần — `src/styles.css` (single file, không dùng CSS modules hay Tailwind) |
| Font | Inter (primary) + Be Vietnam Pro (secondary) — import từ Google Fonts |
| Entry | `src/main.jsx` → `src/App.jsx` |
| Build output | `frontend/parent_app/dist/` |

**Quy tắc**: Tất cả CSS viết trong `styles.css`. Không dùng inline styles trừ trường hợp dynamic values (ví dụ: progress percentage). Không dùng CSS modules. Không dùng Tailwind.

---

## 2. Design Tokens — CSS Variables

Tất cả tokens định nghĩa trong `:root` của `styles.css`. **Luôn dùng CSS variables, không hardcode giá trị.**

### Colors

```css
/* Primary */
--primary: #6366F1          /* Indigo — màu chính */
--primary-dark: #4F46E5     /* Hover state */
--primary-soft: #EDE9FE     /* Background soft cho selected items */

/* Accent */
--accent: #8B5CF6           /* Purple — secondary actions */
--accent-soft: #F3E8FF      /* Accent background */

/* Semantic */
--success: #22c55e          /* Green */
--warning: #f59e0b          /* Amber */
--danger: #ef4444           /* Red */
--info: #0ea5e9             /* Sky blue */

/* Neutral */
--bg: #F4F7FE               /* Page background */
--card: #FFFFFF             /* Card background */
--border: #E2E8F0           /* Border color */
--text: #1E293B             /* Primary text */
--text-secondary: #64748B   /* Secondary text */
--muted: #94A3B8            /* Muted/placeholder text */
```

### Gradients

```css
--grad-primary: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%)   /* Primary CTA */
--grad-hero: linear-gradient(135deg, #FFE4E6 0%, #E0E7FF 100%)       /* Hero sections */
--grad-mint: linear-gradient(135deg, #D1FAE5 0%, #CCFBF1 100%)       /* Success/health */
--grad-blue: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%)       /* Info sections */
--grad-orange-pink: linear-gradient(135deg, #FFEDD5 0%, #FFE4E6 100%) /* Warm sections */
--grad-purple-soft: linear-gradient(135deg, #F3E8FF 0%, #EDE9FE 100%) /* Soft purple */
--grad-hot: linear-gradient(135deg, #FB7185 0%, #F97316 100%)         /* Hot badge */
```

### Border Radius

```css
--radius-lg: 24px     /* Cards, modals chính */
--radius-modal: 28px  /* Overlay/modal */
--radius-md: 20px     /* Medium cards */
--radius-sm: 16px     /* Buttons, small cards, inputs */
```

### Spacing và Layout

```css
--side-w: 248px       /* Sidebar width (desktop) */
--nav-h: 72px         /* Bottom nav height (mobile) */
--shadow: 0px 10px 30px -5px rgba(112, 144, 176, 0.12)  /* Card shadow */
```

### Typography Scale

```css
--font-body: 14px      /* Body text mặc định */
--font-btn: 16px       /* Button text */
--font-section: 18px   /* Section headers */
--font-heading: 24px   /* Page headings */
```

### Tap Targets

```css
--tap-min: 48px        /* Minimum tap target (WCAG AA) */
```

Tất cả `<button>` và `<a>` phải có `min-height: var(--tap-min)`.

---

## 3. Layout System

### Responsive Breakpoint

**Duy nhất một breakpoint**: `768px`
- `< 768px` → Mobile layout: bottom nav, full-width content
- `≥ 768px` → Desktop layout: sidebar, content margin-left

```css
/* Mobile default */
.side-nav { display: none; }
.bottom-nav { display: flex; }
.main-content { padding-bottom: calc(var(--nav-h) + env(safe-area-inset-bottom) + 16px); }

/* Desktop */
@media (min-width: 768px) {
  .side-nav { display: flex; width: var(--side-w); position: fixed; }
  .bottom-nav { display: none; }
  .main-content { margin-left: var(--side-w); padding-bottom: 32px; }
}
```

### App Shell Structure

```jsx
<div className="app-layout">          {/* flex container, min-height: 100dvh */}
  <Sidebar />                          {/* fixed left, desktop only */}
  <main className="main-content">     {/* flex: 1, margin-left on desktop */}
    {/* Page content */}
  </main>
  <BottomNav />                        {/* fixed bottom, mobile only */}
</div>
```

### Page Content Padding

```css
.page-body {
  padding: 16px 16px 0;   /* Mobile */
}
@media (min-width: 768px) {
  .page-body { padding: 20px 24px 0; }
}
```

---

## 4. Navigation

### Sidebar (Desktop ≥768px)

**Structure**:
```
Sidebar
├── Logo section (Robot Bi branding)
├── Tab navigation (5 tabs, flex: 1)
└── Bottom section (locked order):
    ├── RobotStatusCard
    ├── UserCard
    ├── Cài đặt button
    └── Đăng xuất button
```

**5 tabs**:
1. 🏠 Trang chủ (`home`)
2. 📷 Giám sát (`monitor`)
3. 📚 Học tập (`learning`)
4. 📓 Nhật ký (`journal`)
5. ⋯ Thêm (`more`)

**Active state**: `background: var(--grad-primary); color: #fff`
**Hover state**: `background: var(--primary-soft); color: var(--primary)`

### Bottom Nav (Mobile <768px)

5 tabs tương tự sidebar, layout horizontal, fixed bottom.
**Active state**: `color: var(--primary)`

---

## 5. Component Patterns

### Card

```css
.card {
  background: var(--card);
  border-radius: var(--radius-lg);  /* 24px */
  padding: 20px;
  margin-bottom: 14px;
  box-shadow: var(--shadow);
}
```

Dùng cho: tất cả content sections trong pages.

### Buttons

**Primary (CTA)**:
```css
.btn-sm.primary {
  background: var(--grad-primary);
  color: white;
  border-radius: var(--radius-sm);
  padding: 8px 16px;
  font-size: 14px; font-weight: 600;
  min-height: 36px;
}
```

**Secondary**:
```css
.btn-sm.secondary {
  background: var(--bg);
  color: var(--text);
  border: 1.5px solid var(--border);
}
.btn-sm.secondary:hover { background: var(--primary-soft); color: var(--primary); }
```

**Disabled**: `opacity: 0.4; cursor: not-allowed`

**Hover convention**: `opacity: 0.88` cho gradient buttons.

### Robot Status Card

3 states với border + background khác nhau:
```css
.robot-status-card.online    { border-color: #86efac; background: #f0fdf4; }
.robot-status-card.offline   { border-color: #fca5a5; background: #fef2f2; }
.robot-status-card.connecting { border-color: #fcd34d; background: #fffbeb; }
```

Status dot animation:
```css
.status-dot.online    { background: var(--success); animation: pulse 2s infinite; }
.status-dot.connecting { background: var(--warning); animation: pulse 1.2s infinite; }
```

### Lesson Card

```css
.lesson-card {
  display: flex; gap: 14px; align-items: center;
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 16px;
  border: 1px solid var(--border);
}
/* Thumbnail: 64x64px, border-radius: var(--radius-sm), background: var(--grad-purple-soft) */
```

### Task Item

```css
.task-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
}
.task-item.done { opacity: 0.6; }
```

### Vocab Card

Grid layout: `repeat(auto-fill, minmax(110px, 1fr))`

### More Page Grid

2 columns: `grid-template-columns: 1fr 1fr`
Cards có `aspect-ratio: 1` (hình vuông).

### Music Player Card

```css
.music-player-card {
  background: var(--grad-primary);
  border-radius: var(--radius-lg);
  padding: 24px;
  color: white;
}
```

Control buttons: circular, `rgba(255,255,255,0.18)` background.
Play button: `white` background, `color: var(--primary)`.

### System Log (Admin)

Dark theme component:
```css
.log-item {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  border-bottom: 1px solid #334155;
}
/* Level colors: INFO=#0ea5e9, WARNING=#f59e0b, ERROR=#ef4444 */
```

---

## 6. Status và Feedback

### Toast

Component `<Toast />` — singleton, triggered qua `showToast()` từ `services/api.js`.
Không render toast trực tiếp trong components.

### Spinner

```jsx
<div className="spinner" />
```

Dùng cho loading state toàn trang (auth check).

### Hot Badge

```css
.hot-badge {
  position: absolute; top: 10px; right: 10px;
  background: var(--grad-hot);
  color: white; font-size: 10px; font-weight: 800;
  padding: 3px 8px; border-radius: 999px;
}
```

### Emotion Bar Colors

```css
.bar-seg.happy   { background: #34D399; }
.bar-seg.neutral { background: #93C5FD; }
.bar-seg.sad     { background: #FCD34D; }
.bar-seg.stressed { background: #FDA4AF; }
```

---

## 7. Animation và Motion

```css
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
```

**Hover transitions**: `0.18s` cho background/color, `0.2s` cho transform.

**Card hover lift**:
```css
.some-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(112,144,176,0.16);
}
```

**Reduced motion**: Tất cả animations/transitions tắt khi `prefers-reduced-motion: reduce`.

---

## 8. React App State và Routing

### App.jsx — State chính

```jsx
isLoggedIn       // bool — auth state
isCheckingAuth   // bool — loading state khi kiểm tra session
activeTab        // string — 'home'|'monitor'|'learning'|'journal'|'more'
settingsOpen     // bool — settings overlay
robotStatus      // string — 'online'|'offline'|'connecting'
user             // {username, isAdmin}
activeChild      // null | child object
lastWsEvent      // WebSocket event object
```

### Tab Routing

Không dùng React Router. Tab routing đơn giản qua object map:

```jsx
const tabComponents = {
  home: <HomePage user={user} lastWsEvent={lastWsEvent} />,
  monitor: <MonitorPage lastWsEvent={lastWsEvent} />,
  learning: <LearningPage activeChild={activeChild} />,
  journal: <JournalPage />,
  more: <MorePage />,
};
```

### Settings Overlay

Full-screen panel (không phải modal). Sections:
- Hồ sơ trẻ
- Thông báo
- Giờ hoạt động
- Nội dung & An toàn
- Kết nối thiết bị
- Chế độ kỹ thuật (admin only — `isAdmin === true`)

### Tab Change Side Effects

Khi chuyển tab → `stopCamera()` + `stopMomMic()` + scroll to top.
Camera và audio monitor tự cleanup để tránh leak.

---

## 9. Services Layer

Tất cả API calls, WebSocket, auth đều qua `src/services/api.js`.
Components không gọi `fetch` trực tiếp.

**Key functions**:
```js
checkExistingSession()           → userData | null
connectWebSocket(onEvent, onStatus)
disconnectWebSocket()
logout()
showToast(message)
stopCamera()
stopMomMic()
stopAudioMonitor()
```

---

## 10. Rules và Conventions

### DO
- Dùng CSS class names theo convention đã có (kebab-case)
- Dùng CSS variables cho tất cả colors, spacing, radius
- Giữ `min-height: var(--tap-min)` cho tất cả interactive elements
- Dùng `dvh` thay `vh` cho mobile viewport compatibility
- Test responsive ở cả `< 768px` và `≥ 768px`
- Dùng `env(safe-area-inset-bottom)` cho bottom nav và content padding

### DON'T
- Không hardcode màu sắc (dùng CSS variables)
- Không dùng `px` cho font-size body (dùng variables)
- Không tạo CSS file mới — viết vào `styles.css`
- Không dùng `vh` thuần (dùng `dvh`)
- Không dùng inline styles trừ dynamic values
- Không import CSS modules hay styled-components
- Không dùng Tailwind utility classes

### Naming Convention

```
Component: PascalCase    → Sidebar.jsx, BottomNav.jsx
CSS class: kebab-case    → .side-nav-item, .robot-status-card
CSS variable: kebab-case → --primary, --radius-lg
State: camelCase         → isLoggedIn, activeTab
```
