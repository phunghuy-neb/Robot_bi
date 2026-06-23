# Robot Bi — Frontend Parent App

## frontend/parent_app/package.json

```json
{
  "name": "robot-bi-parent-app",
  "private": true,
  "version": "2.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18",
    "react-dom": "^18"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4",
    "vite": "^5"
  }
}
```

## frontend/parent_app/vite.config.js

```javascript
﻿import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    proxy: {
      '/api': {
        target: 'https://localhost:8443',
        changeOrigin: true,
        secure: false
      },
      '/auth': {
        target: 'https://localhost:8443',
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: 'wss://localhost:8443',
        ws: true,
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist'
  }
});
```

## frontend/parent_app/index.html

```html
<!DOCTYPE html>
<html lang="vi">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>Robot Bi</title>
    <link rel="manifest" href="/static/manifest.json" />
    <meta name="theme-color" content="#2563eb" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-title" content="Robot Bi" />
    <link rel="apple-touch-icon" href="/static/icon-192.png" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

## frontend/parent_app/src/main.jsx

```jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

## frontend/parent_app/src/App.jsx

```jsx
import { useState, useEffect, useCallback } from 'react';
import {
  checkExistingSession,
  connectWebSocket,
  disconnectWebSocket,
  logout,
  showToast,
  stopCamera,
  stopMomMic,
  stopAudioMonitor,
} from './services/api.js';

import Sidebar from './components/Sidebar.jsx';
import BottomNav from './components/BottomNav.jsx';
import Toast from './components/Toast.jsx';
import SettingsOverlay from './components/SettingsOverlay.jsx';
import LoginPage from './pages/LoginPage.jsx';
import HomePage from './pages/HomePage.jsx';
import MonitorPage from './pages/MonitorPage.jsx';
import LearningPage from './pages/LearningPage.jsx';
import JournalPage from './pages/JournalPage.jsx';
import MorePage from './pages/MorePage.jsx';

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [activeTab, setActiveTab] = useState('home');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [robotStatus, setRobotStatus] = useState('connecting');
  const [user, setUser] = useState({ username: '', isAdmin: false });
  const [activeChild, setActiveChild] = useState(null);
  const [lastWsEvent, setLastWsEvent] = useState(null);

  // Check for existing session on mount
  useEffect(() => {
    checkExistingSession().then(userData => {
      if (userData) {
        setUser(userData);
        setIsLoggedIn(true);
      }
      setIsCheckingAuth(false);
    });
  }, []);

  // Connect WebSocket when logged in
  useEffect(() => {
    if (!isLoggedIn) return;
    connectWebSocket(
      (evt) => setLastWsEvent(evt),
      (status) => setRobotStatus(status)
    );
    return () => disconnectWebSocket();
  }, [isLoggedIn]);

  // Cleanup camera and audio on page unload
  useEffect(() => {
    window.addEventListener('beforeunload', () => { stopCamera(); stopAudioMonitor(); });
  }, []);

  const handleLogin = useCallback((userData) => {
    setUser(userData);
    setIsLoggedIn(true);
    setRobotStatus('connecting');
  }, []);

  const handleLogout = useCallback(async () => {
    stopCamera();
    disconnectWebSocket();
    await logout();
    setIsLoggedIn(false);
    setUser({ username: '', isAdmin: false });
    setActiveChild(null);
    setRobotStatus('connecting');
    setActiveTab('home');
  }, []);

  const handleTabChange = useCallback((tabId) => {
    stopCamera();
    stopMomMic();
    setActiveTab(tabId);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleSwitchChild = useCallback(() => {
    showToast('Chọn hồ sơ trẻ: Sắp hỗ trợ');
  }, []);

  if (isCheckingAuth) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100dvh', background: 'var(--bg)' }}>
        <div className="spinner" />
      </div>
    );
  }

  if (!isLoggedIn) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const tabComponents = {
    home: <HomePage user={user} lastWsEvent={lastWsEvent} />,
    monitor: <MonitorPage lastWsEvent={lastWsEvent} />,
    learning: <LearningPage activeChild={activeChild} />,
    journal: <JournalPage />,
    more: <MorePage />,
  };

  return (
    <div className="app-layout">
      <Sidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        robotStatus={robotStatus}
        user={user}
        activeChild={activeChild}
        onOpenSettings={() => setSettingsOpen(true)}
        onLogout={handleLogout}
        onSwitchChild={handleSwitchChild}
      />

      <main className="main-content">
        {tabComponents[activeTab]}
      </main>

      <BottomNav activeTab={activeTab} onTabChange={handleTabChange} />

      {settingsOpen && (
        <SettingsOverlay
          isAdmin={user.isAdmin}
          onClose={() => setSettingsOpen(false)}
        />
      )}

      <Toast />
    </div>
  );
}
```

## frontend/parent_app/src/styles.css

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Be+Vietnam+Pro:wght@400;500;600;700;800;900&display=swap');

/* ── Design Tokens ── */
:root {
  --primary: #6366F1;
  --primary-dark: #4F46E5;
  --primary-soft: #EDE9FE;
  --accent: #8B5CF6;
  --accent-soft: #F3E8FF;
  --success: #22c55e;
  --warning: #f59e0b;
  --danger: #ef4444;
  --info: #0ea5e9;
  --bg: #F4F7FE;
  --card: #FFFFFF;
  --border: #E2E8F0;
  --text: #1E293B;
  --text-secondary: #64748B;
  --muted: #94A3B8;
  --radius-lg: 24px;
  --radius-modal: 28px;
  --radius-md: 20px;
  --radius-sm: 16px;
  --shadow: 0px 10px 30px -5px rgba(112, 144, 176, 0.12);
  --side-w: 248px;
  --nav-h: 72px;
  /* Legacy compat */
  --font-body: 14px;
  --font-btn: 16px;
  --font-section: 18px;
  --font-heading: 24px;
  --tap-min: 48px;
  /* Gradients */
  --grad-primary: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%);
  --grad-hero: linear-gradient(135deg, #FFE4E6 0%, #E0E7FF 100%);
  --grad-mint: linear-gradient(135deg, #D1FAE5 0%, #CCFBF1 100%);
  --grad-blue: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%);
  --grad-orange-pink: linear-gradient(135deg, #FFEDD5 0%, #FFE4E6 100%);
  --grad-purple-soft: linear-gradient(135deg, #F3E8FF 0%, #EDE9FE 100%);
  --grad-hot: linear-gradient(135deg, #FB7185 0%, #F97316 100%);
}

/* ── Base Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

body {
  font-family: Inter, 'Be Vietnam Pro', system-ui, sans-serif;
  font-size: 14px;
  font-weight: 500;
  background: var(--bg);
  color: var(--text);
  min-height: 100dvh;
  line-height: 22px;
}

button { min-height: var(--tap-min); cursor: pointer; font-family: inherit; }
a { min-height: var(--tap-min); display: inline-flex; align-items: center; }
img { max-width: 100%; }

/* ── Layout ── */
.app-layout { display: flex; min-height: 100dvh; }

.side-nav { display: none; }

.bottom-nav {
  display: flex;
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: calc(var(--nav-h) + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--card);
  border-radius: 24px 24px 0 0;
  border-top: 1px solid var(--border);
  z-index: 100;
  box-shadow: 0 -4px 24px rgba(112, 144, 176, 0.10);
  align-items: center;
}

.main-content {
  flex: 1;
  padding-bottom: calc(var(--nav-h) + env(safe-area-inset-bottom) + 16px);
  min-height: 100dvh;
}

@media (min-width: 768px) {
  .side-nav {
    display: flex;
    flex-direction: column;
    width: var(--side-w);
    min-height: 100dvh;
    background: var(--card);
    border-radius: 0 24px 24px 0;
    position: fixed;
    left: 0; top: 0;
    z-index: 100;
    box-shadow: 4px 0 24px rgba(112, 144, 176, 0.08);
  }
  .bottom-nav { display: none; }
  .main-content { margin-left: var(--side-w); padding-bottom: 32px; }
}

/* ── Sidebar ── */
.side-nav-logo {
  display: flex; align-items: center; gap: 10px;
  padding: 28px 20px 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 8px;
}
.side-nav-logo .logo-icon { font-size: 26px; }
.side-nav-logo strong { font-size: 17px; font-weight: 800; color: var(--primary); }

.side-nav-tabs { flex: 1; padding: 4px 0; }

.side-nav-item {
  display: flex; align-items: center; gap: 8px;
  padding: 16px 20px;
  width: 100%; border: none;
  background: none;
  font-size: 14px; font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer; text-align: left;
  transition: background 0.18s, color 0.18s;
  min-height: var(--tap-min);
}

.side-nav-item:hover { background: var(--primary-soft); color: var(--primary); }
.side-nav-item.active { background: var(--grad-primary); color: #fff; }
.side-nav-item .nav-icon { font-size: 18px; width: 22px; text-align: center; }

.side-nav-bottom {
  margin-top: auto;
  padding: 12px 16px 16px;
  border-top: 1px solid var(--border);
  display: flex; flex-direction: column; gap: 6px;
}

.side-nav-action {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  width: 100%; border: none; background: none;
  font-size: 14px; font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background 0.18s;
  min-height: var(--tap-min);
}
.side-nav-action:hover { background: var(--bg); }
.side-nav-action.danger { color: var(--danger); }
.side-nav-action.danger:hover { background: #fef2f2; }

/* ── Bottom Nav ── */
.bottom-nav-item {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 3px;
  cursor: pointer; padding: 8px 4px;
  border: none; background: none;
  color: var(--muted); font-size: 11px; font-weight: 600;
  transition: color 0.2s; min-height: 56px;
}
.bottom-nav-item .nav-icon { font-size: 22px; line-height: 1; }
.bottom-nav-item.active { color: var(--primary); }

/* ── Robot Status Card ── */
.robot-status-card {
  border-radius: var(--radius-sm); padding: 10px 12px;
  border: 1.5px solid var(--border); background: #f8fafc; margin-bottom: 2px;
}
.robot-status-card.online { border-color: #86efac; background: #f0fdf4; }
.robot-status-card.offline { border-color: #fca5a5; background: #fef2f2; }
.robot-status-card.connecting { border-color: #fcd34d; background: #fffbeb; }

.robot-status-row { display: flex; align-items: center; gap: 8px; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--muted); flex-shrink: 0; }
.status-dot.online { background: var(--success); box-shadow: 0 0 0 3px rgba(34,197,94,0.2); animation: pulse 2s infinite; }
.status-dot.offline { background: var(--danger); }
.status-dot.connecting { background: var(--warning); animation: pulse 1.2s infinite; }

@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

.robot-status-label { font-size: 13px; font-weight: 700; color: var(--text); }
.robot-status-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }

/* ── User Card ── */
.user-card {
  border-radius: var(--radius-sm); padding: 10px 12px;
  border: 1px solid var(--border); background: #f8fafc;
  cursor: pointer; transition: background 0.15s;
}
.user-card:hover { background: var(--primary-soft); }
.user-card-row { display: flex; align-items: center; gap: 8px; }
.user-avatar { font-size: 22px; }
.user-name { font-size: 13px; font-weight: 700; color: var(--text); }
.user-role { font-size: 11px; color: var(--muted); }
.user-child { font-size: 11px; color: var(--primary); font-weight: 600; margin-top: 2px; }

/* ── Cards ── */
.card {
  background: var(--card);
  border-radius: var(--radius-lg);
  padding: 20px; margin-bottom: 14px;
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}

.card-header {
  display: flex; align-items: center;
  justify-content: space-between; margin-bottom: 14px;
}

.card-title {
  font-size: 16px; font-weight: 700; line-height: 24px;
  color: var(--text); display: flex; align-items: center; gap: 8px;
}

.card-sub { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }

/* ── Feature Badges ── */
.feature-badge {
  font-size: 11px; font-weight: 700;
  padding: 2px 10px; border-radius: 999px;
  border: 1.5px solid; display: inline-block; white-space: nowrap;
}
.feature-badge.coming-soon { background: #f1f5f9; color: var(--muted); border-color: #e2e8f0; }
.feature-badge.mock-data { background: #fffbeb; color: #b45309; border-color: #fcd34d; }
.feature-badge.no-backend { background: #fef2f2; color: #dc2626; border-color: #fca5a5; }

/* ── Section States ── */
.section-state { text-align: center; padding: 32px 16px; color: var(--muted); }
.section-state .state-icon { font-size: 40px; display: block; margin-bottom: 12px; }
.section-state .state-text { font-size: 14px; color: var(--text-secondary); }
.section-state .retry-btn {
  background: var(--grad-primary); color: white; border: none;
  border-radius: var(--radius-sm); padding: 10px 24px;
  font-size: 14px; font-weight: 600; margin-top: 14px;
  min-height: var(--tap-min); cursor: pointer; transition: opacity 0.15s;
}
.section-state .retry-btn:hover { opacity: 0.85; }

.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border); border-top-color: var(--primary);
  border-radius: 50%; animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Toast ── */
.toast-container {
  position: fixed;
  bottom: calc(var(--nav-h) + 20px); left: 50%;
  transform: translateX(-50%); z-index: 1000; pointer-events: none;
}
@media (min-width: 768px) { .toast-container { bottom: 32px; } }

.toast {
  background: #1e293b; color: white;
  padding: 12px 22px; border-radius: var(--radius-md);
  font-size: 14px; font-weight: 500;
  box-shadow: var(--shadow); max-width: 340px;
  text-align: center; white-space: pre-line; pointer-events: auto;
}

/* ── Page Header ── */
.page-header { padding: 24px 20px 16px; background: var(--grad-primary); color: white; }
.page-title { font-size: 24px; font-weight: 700; line-height: 32px; }
.page-subtitle { font-size: 12px; opacity: 0.85; margin-top: 4px; font-weight: 500; }
.page-body { padding: 16px 16px 0; }

/* ── HomePage Hero ── */
.home-hero {
  padding: 28px 20px 24px;
  background: var(--grad-hero);
  border-radius: 0 0 24px 24px;
}
.home-greeting { font-size: 24px; font-weight: 700; line-height: 32px; color: var(--text); margin-bottom: 4px; }
.home-date { font-size: 12px; color: var(--text-secondary); font-weight: 500; }

/* ── Metric Cards ── */
.today-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 4px;
}
@media (min-width: 900px) { .today-grid { grid-template-columns: repeat(4, 1fr); } }

.metric-card {
  background: var(--card); border-radius: var(--radius-lg); padding: 16px;
  border: 1px solid var(--border); box-shadow: var(--shadow);
  display: flex; flex-direction: column; gap: 4px;
}
.metric-card.grad-blue { background: var(--grad-blue); border-color: #BAE6FD; }
.metric-card.grad-orange-pink { background: var(--grad-orange-pink); border-color: #FED7AA; }
.metric-card.grad-mint { background: var(--grad-mint); border-color: #A7F3D0; }
.metric-card.grad-purple-soft { background: var(--grad-purple-soft); border-color: #DDD6FE; }

.metric-icon { font-size: 20px; margin-bottom: 2px; display: flex; align-items: center; gap: 6px; }
.metric-num { font-size: 22px; font-weight: 800; color: var(--text); line-height: 1.1; }
.metric-label { font-size: 12px; color: var(--text-secondary); font-weight: 500; line-height: 18px; }
.metric-value-text { font-size: 14px; font-weight: 700; color: var(--text); }

.metric-online-dot {
  display: inline-block; width: 10px; height: 10px; border-radius: 50%;
  background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,0.22);
  animation: pulse 2s infinite;
}

/* ── Alert Card ── */
.alert-card {
  background: #fffbeb; border: 1.5px solid #fcd34d;
  border-radius: var(--radius-lg); padding: 14px 16px; margin-bottom: 12px;
  display: flex; gap: 10px; align-items: flex-start;
}
.alert-icon { font-size: 22px; flex-shrink: 0; }
.alert-text { font-size: 14px; font-weight: 600; color: #92400e; }
.alert-sub { font-size: 12px; color: #b45309; margin-top: 2px; }

/* ── Events List ── */
.event-list { display: flex; flex-direction: column; gap: 8px; }
.event-row {
  display: flex; align-items: center; gap: 12px; padding: 12px;
  background: #f8fafc; border-radius: var(--radius-sm);
  border: 1px solid var(--border); cursor: pointer; transition: background 0.15s;
}
.event-row:hover { background: var(--primary-soft); }
.event-icon {
  width: 38px; height: 38px; border-radius: 12px;
  background: var(--primary-soft); display: flex; align-items: center;
  justify-content: center; font-size: 17px; flex-shrink: 0;
}
.event-body { flex: 1; min-width: 0; }
.event-title { font-size: 14px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.event-time { font-size: 12px; color: var(--muted); margin-top: 2px; }

/* ── Login Page ── */
.login-page {
  position: fixed; inset: 0;
  background: var(--grad-hero);
  display: flex; align-items: center; justify-content: center; z-index: 9999;
}
.login-box {
  background: white; border-radius: var(--radius-modal);
  padding: 40px 32px; width: 360px; max-width: 90vw;
  box-shadow: 0 20px 60px rgba(112, 144, 176, 0.20);
}
.login-logo { font-size: 48px; text-align: center; margin-bottom: 8px; }
.login-title { font-size: 22px; font-weight: 800; color: var(--primary); text-align: center; margin-bottom: 4px; }
.login-subtitle { font-size: 14px; color: var(--muted); text-align: center; margin-bottom: 28px; }

.form-group { margin-bottom: 14px; }
.form-label { display: block; font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.form-input {
  width: 100%; padding: 13px 16px; font-size: 14px;
  border: 2px solid var(--border); border-radius: var(--radius-sm);
  outline: none; font-family: inherit; transition: border-color 0.18s; color: var(--text);
}
.form-input:focus { border-color: var(--primary); }

.btn-primary {
  width: 100%; padding: 14px;
  background: var(--grad-primary); color: white;
  border: none; border-radius: var(--radius-sm);
  font-size: 16px; font-weight: 700; cursor: pointer;
  min-height: var(--tap-min); transition: opacity 0.18s;
}
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; }

.login-error {
  margin-top: 12px; padding: 10px 14px;
  background: #fef2f2; border: 1px solid #fca5a5;
  border-radius: var(--radius-sm); color: var(--danger); font-size: 14px; text-align: center;
}

/* ── Settings Overlay ── */
.settings-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: flex-end;
}
@media (min-width: 768px) {
  .settings-overlay { align-items: stretch; justify-content: flex-end; }
}

.settings-panel {
  background: var(--bg);
  border-radius: var(--radius-modal) var(--radius-modal) 0 0;
  overflow-y: auto; padding: 24px 20px 32px;
  max-height: 90dvh; width: 100%;
  box-shadow: 0 -8px 40px rgba(112, 144, 176, 0.14);
}
@media (min-width: 768px) {
  .settings-panel {
    width: 500px; height: 100dvh; max-height: none;
    border-radius: var(--radius-modal) 0 0 0; padding-top: 32px;
  }
}

.settings-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border);
}
.settings-title { font-size: 24px; font-weight: 700; color: var(--text); }
.settings-close {
  width: 40px; height: 40px; border: none; background: var(--card);
  border-radius: var(--radius-sm); font-size: 18px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; min-height: 40px;
  box-shadow: var(--shadow); transition: background 0.15s;
}
.settings-close:hover { background: var(--bg); }

.settings-section {
  background: var(--card); border-radius: var(--radius-sm);
  padding: 16px; margin-bottom: 12px; box-shadow: var(--shadow);
}

.settings-section-title {
  font-size: 18px; font-weight: 700; line-height: 26px;
  color: var(--text); margin-bottom: 12px;
  display: flex; align-items: center; gap: 8px;
}

.settings-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: var(--card);
  border-radius: var(--radius-sm); border: 1px solid var(--border); margin-bottom: 8px;
}
.settings-row-label { font-size: 14px; font-weight: 600; color: var(--text); }
.settings-row-sub { font-size: 12px; color: var(--muted); margin-top: 2px; }

.btn-outline {
  padding: 10px 20px; border: 2px solid var(--primary);
  background: none; color: var(--primary);
  border-radius: var(--radius-sm); font-size: 14px; font-weight: 600;
  cursor: pointer; min-height: var(--tap-min); transition: background 0.15s;
}
.btn-outline:hover { background: var(--primary-soft); }

/* ── Monitor Page ── */
.camera-section {
  background: #0f172a; border-radius: var(--radius-lg); overflow: hidden;
  aspect-ratio: 16/9; display: flex; align-items: center;
  justify-content: center; margin-bottom: 14px;
}
.camera-placeholder { text-align: center; color: #64748b; }
.camera-placeholder .cam-icon { font-size: 48px; display: block; margin-bottom: 10px; }
.camera-placeholder p { font-size: 15px; }
.camera-feed { width: 100%; height: 100%; object-fit: contain; }
.mom-mic-controls { display: flex; gap: 10px; flex-wrap: wrap; }

.btn-action {
  padding: 12px 20px; border: none; border-radius: var(--radius-sm);
  font-size: 16px; font-weight: 700; cursor: pointer; min-height: var(--tap-min);
  transition: opacity 0.18s; display: flex; align-items: center; gap: 8px;
}
.btn-action.primary { background: var(--grad-primary); color: white; }
.btn-action.primary:hover { opacity: 0.9; }
.btn-action.danger { background: var(--danger); color: white; }
.btn-action.secondary { background: var(--bg); color: var(--text); border: 1.5px solid var(--border); }

/* ── Motor Controls ── */
.motor-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; max-width: 240px; }
.motor-btn {
  aspect-ratio: 1; border: none; background: var(--bg);
  border-radius: var(--radius-sm); font-size: 22px; cursor: pointer;
  border: 1.5px solid var(--border); transition: background 0.1s; min-height: 60px;
}
.motor-btn:hover { background: var(--primary-soft); }
.motor-btn.stop { background: #fef2f2; border-color: #fca5a5; }

/* ── Pill Filter Tabs ── */
.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }
.filter-select {
  padding: 10px 14px; border: 1.5px solid var(--border);
  border-radius: var(--radius-sm); font-size: 14px;
  font-family: inherit; color: var(--text); background: var(--card);
  min-height: var(--tap-min); cursor: pointer;
}
.filter-select:focus { border-color: var(--primary); outline: none; }
.filter-date {
  padding: 10px 14px; border: 1.5px solid var(--border);
  border-radius: var(--radius-sm); font-size: 14px;
  font-family: inherit; color: var(--text); background: var(--card);
  min-height: var(--tap-min);
}

.pill-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
.pill-tab {
  padding: 8px 18px; border-radius: var(--radius-sm);
  border: 1.5px solid var(--border); background: var(--card);
  font-size: 14px; font-weight: 600; color: var(--text-secondary);
  cursor: pointer; min-height: 40px;
  transition: background 0.18s, color 0.18s, border-color 0.18s;
}
.pill-tab:hover { background: var(--primary-soft); color: var(--primary); border-color: var(--primary); }
.pill-tab.active { background: var(--grad-primary); color: white; border-color: transparent; }

/* ── Journal Timeline ── */
.thread-timeline {
  position: relative;
  padding-left: 20px;
  border-left: 2px dashed #CBD5E1;
}

.thread-item {
  display: flex; align-items: center; gap: 12px; padding: 14px;
  background: var(--card); border-radius: var(--radius-sm);
  border: 1px solid var(--border); cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s;
  margin-bottom: 10px; box-shadow: var(--shadow); position: relative;
}
.thread-item::before {
  content: '';
  position: absolute; left: -27px; top: 50%; transform: translateY(-50%);
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--primary); border: 2px solid white;
  box-shadow: 0 0 0 2px var(--primary);
}
.thread-item.homework::before { background: var(--warning); box-shadow: 0 0 0 2px var(--warning); }
.thread-item:hover { background: var(--primary-soft); box-shadow: 0 8px 24px rgba(112,144,176,0.14); }
.thread-icon { font-size: 20px; flex-shrink: 0; }
.thread-body { flex: 1; min-width: 0; }
.thread-title { font-size: 14px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.thread-meta { font-size: 12px; color: var(--muted); margin-top: 3px; }
.thread-arrow { font-size: 18px; color: var(--muted); }

/* Chat bubbles */
.chat-bubble-wrap { display: flex; flex-direction: column; gap: 12px; }
.chat-entry { display: flex; flex-direction: column; gap: 4px; }
.chat-who { font-size: 12px; font-weight: 700; color: var(--muted); }
.bubble {
  max-width: 80%; padding: 10px 14px; border-radius: 16px;
  font-size: 14px; line-height: 1.5; box-shadow: var(--shadow);
}
.bubble.user { background: var(--grad-primary); color: white; align-self: flex-end; border-radius: 16px 16px 4px 16px; }
.bubble.bi { background: var(--card); color: var(--text); align-self: flex-start; border: 1px solid var(--border); border-radius: 16px 16px 16px 4px; }

/* ── Emotion Bar Chart ── */
.emotion-chart { display: flex; flex-direction: column; gap: 12px; }
.emotion-week { display: flex; align-items: center; gap: 8px; }
.emotion-week-label { font-size: 12px; color: var(--muted); width: 60px; flex-shrink: 0; }
.bar-row { flex: 1; display: flex; height: 14px; border-radius: 8px; overflow: hidden; gap: 1px; }
.bar-seg { height: 100%; transition: width 0.3s; }
.bar-seg.happy { background: #34D399; }
.bar-seg.neutral { background: #93C5FD; }
.bar-seg.sad { background: #FCD34D; }
.bar-seg.stressed { background: #FDA4AF; }
.emotion-legend { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-secondary); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; }

/* ── Learning Page ── */
.quick-actions-grid {
  display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 16px;
}
@media (max-width: 480px) { .quick-actions-grid { grid-template-columns: repeat(2,1fr); } }

.quick-action-btn {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 8px;
  aspect-ratio: 1; border: none; border-radius: var(--radius-sm);
  font-size: 12px; font-weight: 700; color: var(--text);
  cursor: pointer; padding: 12px 8px;
  transition: transform 0.18s, box-shadow 0.18s;
  box-shadow: var(--shadow); min-height: 80px;
}
.quick-action-btn:hover { transform: translateY(-2px); box-shadow: 0 12px 32px rgba(112,144,176,0.16); }
.quick-action-btn .qa-icon { font-size: 26px; }

/* Circular progress ring */
.progress-ring-wrap { display: flex; align-items: center; gap: 20px; padding: 4px 0 12px; }
.progress-ring { position: relative; width: 80px; height: 80px; flex-shrink: 0; }
.progress-ring svg { transform: rotate(-90deg); }
.progress-ring-label {
  position: absolute; inset: 0; display: flex; align-items: center;
  justify-content: center; font-size: 16px; font-weight: 800; color: var(--primary);
}
.progress-ring-title { font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.progress-ring-sub { font-size: 12px; color: var(--text-secondary); }

/* Lesson card */
.lesson-card {
  display: flex; gap: 14px; align-items: center;
  background: var(--card); border-radius: var(--radius-lg);
  padding: 16px; box-shadow: var(--shadow);
  border: 1px solid var(--border); margin-bottom: 14px;
}
.lesson-thumb {
  width: 64px; height: 64px; border-radius: var(--radius-sm);
  background: var(--grad-purple-soft); display: flex;
  align-items: center; justify-content: center; font-size: 30px; flex-shrink: 0;
}
.lesson-body { flex: 1; min-width: 0; }
.lesson-title { font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.lesson-meta { font-size: 12px; color: var(--text-secondary); margin-bottom: 10px; }
.btn-start {
  background: var(--grad-primary); color: white; border: none;
  border-radius: var(--radius-sm); padding: 10px 18px;
  font-size: 14px; font-weight: 700; cursor: pointer;
  min-height: 44px; transition: opacity 0.15s; flex-shrink: 0;
}
.btn-start:hover { opacity: 0.88; }

.vocab-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(110px,1fr)); gap: 10px; }
.vocab-card {
  background: var(--bg); border: 1.5px solid var(--border);
  border-radius: var(--radius-sm); padding: 14px 10px;
  text-align: center; cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.vocab-card:hover { border-color: var(--primary); background: var(--primary-soft); }
.vocab-emoji { font-size: 26px; display: block; margin-bottom: 6px; }
.vocab-word { font-size: 14px; font-weight: 700; color: var(--text); }
.vocab-meaning { font-size: 12px; color: var(--muted); margin-top: 2px; }

.task-item {
  display: flex; align-items: center; gap: 12px; padding: 12px 14px;
  background: var(--card); border-radius: var(--radius-sm);
  border: 1.5px solid var(--border); margin-bottom: 8px; box-shadow: var(--shadow);
}
.task-item.done { opacity: 0.6; }
.task-check { width: 22px; height: 22px; border-radius: 50%; border: 2px solid var(--primary); background: none; cursor: pointer; flex-shrink: 0; }
.task-check.done { background: var(--success); border-color: var(--success); }
.task-name { flex: 1; font-size: 14px; font-weight: 500; color: var(--text); }
.task-stars { font-size: 12px; color: var(--warning); }

/* ── More Page ── */
.more-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }

.more-card {
  border-radius: var(--radius-lg); aspect-ratio: 1;
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 10px;
  cursor: pointer; position: relative; overflow: hidden;
  border: none; transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: var(--shadow); padding: 16px; font-family: inherit;
}
.more-card:hover { transform: translateY(-2px); box-shadow: 0 12px 32px rgba(112,144,176,0.18); }
.more-card-icon { font-size: 32px; }
.more-card-label { font-size: 16px; font-weight: 700; color: var(--text); text-align: center; }
.more-card-sub { font-size: 12px; color: var(--text-secondary); text-align: center; }

.hot-badge {
  position: absolute; top: 10px; right: 10px;
  background: var(--grad-hot); color: white;
  font-size: 10px; font-weight: 800;
  padding: 3px 8px; border-radius: 999px; letter-spacing: 0.5px;
}

.music-player-card {
  background: var(--grad-primary); border-radius: var(--radius-lg);
  padding: 24px; color: white; margin-bottom: 14px;
}
.music-track-label { font-size: 10px; text-transform: uppercase; opacity: 0.7; margin-bottom: 6px; letter-spacing: 1px; font-weight: 700; }
.music-track-title { font-size: 18px; font-weight: 700; margin-bottom: 2px; }
.music-track-artist { font-size: 14px; opacity: 0.8; }
.music-controls { display: flex; gap: 10px; margin-top: 16px; align-items: center; }

.music-btn {
  width: 44px; height: 44px; border-radius: 50%; border: none;
  background: rgba(255,255,255,0.18); color: white; font-size: 17px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  min-height: 44px; transition: background 0.15s;
}
.music-btn:hover { background: rgba(255,255,255,0.28); }
.music-btn.play { width: 52px; height: 52px; background: white; color: var(--primary); font-size: 20px; }

.media-card {
  background: var(--card); border: 1.5px solid var(--border);
  border-radius: var(--radius-sm); padding: 14px;
  display: flex; gap: 12px; align-items: center; margin-bottom: 8px;
  box-shadow: var(--shadow);
}
.media-thumb { font-size: 30px; flex-shrink: 0; }
.media-body { flex: 1; min-width: 0; }
.media-title { font-size: 14px; font-weight: 600; color: var(--text); }
.media-meta { font-size: 12px; color: var(--muted); margin-top: 3px; }
.media-action { flex-shrink: 0; }

/* ── Buttons ── */
.btn-sm {
  padding: 8px 16px; border-radius: var(--radius-sm);
  font-size: 14px; font-weight: 600; border: none; cursor: pointer;
  min-height: 36px; transition: opacity 0.15s;
}
.btn-sm.primary { background: var(--grad-primary); color: white; }
.btn-sm.primary:hover { opacity: 0.88; }
.btn-sm.secondary { background: var(--bg); color: var(--text); border: 1.5px solid var(--border); }
.btn-sm.secondary:hover { background: var(--primary-soft); color: var(--primary); border-color: var(--primary); }
.btn-sm:disabled { opacity: 0.4; cursor: not-allowed; }

/* ── Weekly Report ── */
.weekly-stat-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.weekly-stat {
  flex: 1; min-width: 80px; text-align: center; padding: 14px 8px;
  background: var(--bg); border-radius: var(--radius-sm); border: 1px solid var(--border);
}
.weekly-stat-num { font-size: 20px; font-weight: 800; color: var(--primary); }
.weekly-stat-label { font-size: 12px; color: var(--muted); margin-top: 3px; }

/* ── Profile Cards (Settings) ── */
.profile-card {
  display: flex; align-items: center; gap: 14px; padding: 16px;
  background: var(--bg); border-radius: var(--radius-sm);
  border: 1.5px solid var(--border); margin-bottom: 10px;
}
.profile-avatar { font-size: 34px; }
.profile-name { font-size: 16px; font-weight: 700; color: var(--text); }
.profile-info { font-size: 12px; color: var(--muted); margin-top: 3px; }

/* ── System Log ── */
.log-item {
  display: flex; gap: 10px; padding: 10px 12px;
  border-bottom: 1px solid #334155;
  font-size: 12px; font-family: 'Courier New', monospace;
}
.log-level { font-weight: 700; width: 60px; flex-shrink: 0; }
.log-level.INFO { color: var(--info); }
.log-level.WARNING { color: var(--warning); }
.log-level.ERROR { color: var(--danger); }
.log-msg { flex: 1; color: #e2e8f0; }
.log-time { color: #64748b; font-size: 10px; }

/* ── Back button ── */
.btn-back {
  display: flex; align-items: center; gap: 6px;
  background: none; border: none; color: var(--primary);
  font-size: 14px; font-weight: 600; cursor: pointer;
  padding: 8px 0; min-height: auto; margin-bottom: 12px;
}

/* ── Responsive ── */
@media (min-width: 768px) {
  .page-body { padding: 20px 24px 0; }
  .home-hero { padding: 32px 28px 28px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

## frontend/parent_app/src/services/api.js

```javascript
// Robot Bi Parent App — API Service Layer
// Tier 1: Real backend (preserved behavior from legacy index.html)
// Tier 2: Wired to backend with mock fallback when backend returns no data

import {
  mockChildProfiles,
  mockRadioChannels,
  mockVideoLessons,
  mockMonthlyEmotions,
  mockInteractiveGames,
  mockSystemLogs,
} from '../data/mockData.js';

// —— Auth Storage ——
let _token = localStorage.getItem('bi_token') || '';
let _refreshToken = localStorage.getItem('bi_refresh') || '';
let _refreshPromise = null;

function authHeader() {
  return _token ? { Authorization: 'Bearer ' + _token } : {};
}

// —— Toast ——
export let toastFn = null;
export function registerToast(fn) { toastFn = fn; }
export function showToast(msg) { toastFn && toastFn(msg); }

// —— Utilities ——
export function getBaseUrl() { return window.location.origin; }
export function getToken() { return _token; }

// —— Auth: login ——
export async function login(username, password) {
  const r = await fetch('/auth/login/v2', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || 'Sai tên đăng nhập hoặc mật khẩu.');
  }
  const data = await r.json();
  _token = data.access_token;
  _refreshToken = data.refresh_token;
  localStorage.setItem('bi_token', _token);
  localStorage.setItem('bi_refresh', _refreshToken);
  return { username: data.username || username, isAdmin: data.is_admin || false };
}

// —— Auth: logout ——
export async function logout() {
  try {
    if (_token && _refreshToken) {
      await fetch('/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        body: JSON.stringify({ refresh_token: _refreshToken }),
      });
    }
  } catch (_) {}
  _token = '';
  _refreshToken = '';
  localStorage.removeItem('bi_token');
  localStorage.removeItem('bi_refresh');
}

// —— Auth: refresh token ——
export async function refreshToken() {
  if (_refreshPromise) return _refreshPromise;
  _refreshPromise = (async () => {
    try {
      if (!_refreshToken) return false;
      const rr = await fetch('/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: _refreshToken }),
      });
      if (!rr.ok) return false;
      const data = await rr.json();
      _token = data.access_token;
      _refreshToken = data.refresh_token;
      localStorage.setItem('bi_token', _token);
      localStorage.setItem('bi_refresh', _refreshToken);
      return true;
    } catch (_) {
      return false;
    } finally {
      _refreshPromise = null;
    }
  })();
  return _refreshPromise;
}

// —— Check existing session on app load ——
export async function checkExistingSession() {
  if (!_token) return null;
  try {
    const r = await fetch('/api/auth/me', { headers: authHeader() });
    if (r.ok) {
      const data = await r.json();
      return { username: data.username, isAdmin: data.is_admin || false };
    }
    const ok = await refreshToken();
    if (ok) {
      const r2 = await fetch('/api/auth/me', { headers: authHeader() });
      if (r2.ok) {
        const data = await r2.json();
        return { username: data.username, isAdmin: data.is_admin || false };
      }
    }
    _token = '';
    localStorage.removeItem('bi_token');
    return null;
  } catch (_) {
    return null;
  }
}

// —— apiFetch with 401 → refresh → retry → logout ——
export async function apiFetch(path, opts = {}) {
  try {
    const h1 = { ...authHeader(), ...(opts.headers || {}) };
    const r = await fetch(path, { ...opts, headers: h1 });
    if (r.status === 401) {
      if (_refreshToken) {
        const ok = await refreshToken();
        if (!ok) { await logout(); return null; }
        const h2 = { ...authHeader(), ...(opts.headers || {}) };
        const retry = await fetch(path, { ...opts, headers: h2 });
        if (retry.ok) return await retry.json();
      }
      await logout();
      return null;
    }
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch (_) {
    return null;
  }
}

// —— WebSocket: robot status ——
let _ws = null;
let _wsDelay = 1000;
let _wsLoggedOut = false;
let _wsReconnectTimer = null;
let _wsOnEvent = null;
let _wsOnStatusChange = null;

export function connectWebSocket(onEvent, onStatusChange) {
  _wsOnEvent = onEvent;
  _wsOnStatusChange = onStatusChange;
  _wsLoggedOut = false;
  _doConnect();
}

function _doConnect() {
  if (_wsLoggedOut || !_token) return;
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  _ws = new WebSocket(`${proto}//${location.host}/ws?token=${encodeURIComponent(_token)}`);
  _ws.onopen = () => {
    _wsDelay = 1000;
    _wsOnStatusChange && _wsOnStatusChange('online');
  };
  _ws.onmessage = e => {
    try { _wsOnEvent && _wsOnEvent(JSON.parse(e.data)); } catch (_) {}
  };
  _ws.onclose = () => {
    _wsOnStatusChange && _wsOnStatusChange('offline');
    if (_wsLoggedOut) return;
    _wsReconnectTimer = setTimeout(_doConnect, Math.min(_wsDelay, 12000));
    _wsDelay = Math.min(_wsDelay * 1.5, 12000);
  };
  _ws.onerror = () => _ws && _ws.close();
}

export function disconnectWebSocket() {
  _wsLoggedOut = true;
  if (_wsReconnectTimer) { clearTimeout(_wsReconnectTimer); _wsReconnectTimer = null; }
  if (_ws) { _ws.close(); _ws = null; }
}

// —— Mom-talk audio (protected behavior) ——
let _momMicActive = false;
let _momMediaStream = null;
let _momAudioWs = null;
let _momScriptProcessor = null;
let _momAudioCtx = null;

export async function startMomMic() {
  if (!_token) throw new Error('Vui lòng đăng nhập trước');
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('Trình duyệt không hỗ trợ mic. Dùng Chrome/Firefox và truy cập qua HTTPS.');
  }
  try {
    _momMediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    const sr = await apiFetch('/api/mom/start', { method: 'POST' });
    if (!sr) throw new Error('Không thể báo server');
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    _momAudioWs = new WebSocket(`${proto}//${location.host}/api/mom/audio?token=${encodeURIComponent(_token)}`);
    _momAudioWs.binaryType = 'arraybuffer';
    await new Promise((res, rej) => {
      _momAudioWs.onopen = res;
      _momAudioWs.onerror = () => rej(new Error('WebSocket lỗi'));
      setTimeout(() => rej(new Error('Timeout')), 5000);
    });
    _momAudioCtx = new AudioContext({ sampleRate: 16000 });
    const source = _momAudioCtx.createMediaStreamSource(_momMediaStream);
    _momScriptProcessor = _momAudioCtx.createScriptProcessor(512, 1, 1);
    _momScriptProcessor.onaudioprocess = event => {
      if (!_momMicActive || !_momAudioWs || _momAudioWs.readyState !== WebSocket.OPEN) return;
      _momAudioWs.send(event.inputBuffer.getChannelData(0).buffer.slice(0));
    };
    const sg = _momAudioCtx.createGain();
    sg.gain.value = 0;
    source.connect(_momScriptProcessor);
    _momScriptProcessor.connect(sg);
    sg.connect(_momAudioCtx.destination);
    _momMicActive = true;
    return true;
  } catch (err) {
    stopMomMic();
    throw err;
  }
}

export function stopMomMic() {
  _momMicActive = false;
  if (_momScriptProcessor) { _momScriptProcessor.disconnect(); _momScriptProcessor = null; }
  if (_momAudioCtx) { _momAudioCtx.close(); _momAudioCtx = null; }
  if (_momMediaStream) { _momMediaStream.getTracks().forEach(t => t.stop()); _momMediaStream = null; }
  if (_momAudioWs) { _momAudioWs.close(); _momAudioWs = null; }
  if (_token) fetch('/api/mom/stop', { method: 'POST', headers: authHeader() }).catch(() => {});
}

export function isMomMicActive() { return _momMicActive; }

// —— Conversations (Tier 1) ——
export async function getConversations(limit = 20) {
  return apiFetch(`/api/conversations?limit=${limit}`);
}

export async function getConversation(id) {
  return apiFetch(`/api/conversations/${id}`);
}

// —— Tier 2: Backend-wired adapters with mock fallback ——

export async function getChildProfiles() {
  const data = await apiFetch('/api/children');
  if (data?.children?.length) {
    return data.children.map(c => ({
      id: c.child_id,
      name: c.name,
      age: c.age ?? 0,
      grade: c.grade || '',
      avatar: c.avatar || '👤',
      dailyLimit: 0,
    }));
  }
  return mockChildProfiles();
}

export async function exportReport(fmt) {
  // TODO: backend integration — POST /api/reports/export
  return null;
}

export async function getMonthlyEmotions(month) {
  const query = month ? `?month=${encodeURIComponent(month)}` : '';
  const data = await apiFetch(`/api/emotions/monthly${query}`);
  const weeks = data?.weeks;
  if (weeks?.length) {
    return weeks.map((w, i) => {
      const total = w.count || (w.happy + w.neutral + w.sad + w.stressed) || 1;
      const pct = v => Math.round((v / total) * 100);
      return {
        week: `Tuần ${i + 1}`,
        happy: pct(w.happy || 0),
        neutral: pct(w.neutral || 0),
        sad: pct(w.sad || 0),
        stressed: pct(w.stressed || 0),
      };
    });
  }
  return mockMonthlyEmotions(month);
}

export async function getRoomLocation() {
  // BLOCKED: no component renders this data yet
  return null;
}

export async function getRadioChannels() {
  const data = await apiFetch('/api/entertainment/radio');
  const items = data?.channels || data?.items || [];
  if (items.length) {
    return items.map(ch => ({
      id: ch.content_id,
      name: ch.title,
      icon: '📻',
      genre: ch.tags?.[0] || ch.description || '',
      frequency: '',
    }));
  }
  return mockRadioChannels();
}

export async function getVideoLessons() {
  const data = await apiFetch('/api/entertainment/videos');
  const items = data?.videos || data?.items || [];
  if (items.length) {
    return items.map(v => ({
      id: v.content_id,
      title: v.title,
      thumbnail: v.thumbnail_url || '🎬',
      subject: v.tags?.[0] || '',
      duration: '',
      age: (v.age_min != null && v.age_max != null) ? `${v.age_min}-${v.age_max}` : '',
    }));
  }
  return mockVideoLessons();
}

export async function getInteractiveGames() {
  const data = await apiFetch('/api/games/interactive');
  const items = data?.games || data?.items || [];
  if (items.length) {
    return items.map(g => ({
      id: g.content_id,
      name: g.title,
      icon: '🎮',
      description: g.description || '',
      difficulty: 'Trung bình',
      age: (g.age_min != null && g.age_max != null) ? `${g.age_min}-${g.age_max}` : '',
    }));
  }
  return mockInteractiveGames();
}

export async function getSystemLogs() {
  const data = await apiFetch('/api/admin/logs');
  if (data?.logs) {
    return data.logs.map((entry, i) => ({
      id: i + 1,
      level: entry.level,
      message: entry.message,
      timestamp: entry.timestamp,
      source: entry.component || entry.source || '',
    }));
  }
  return mockSystemLogs();
}

export async function savePushSettings(settings) {
  // TODO: backend integration — POST /api/settings/notifications
  return null;
}

export async function saveSleepSchedule(schedule) {
  // TODO: backend integration — POST /api/settings/sleep
  return null;
}

export async function saveTimeLimits(limits) {
  // TODO: backend integration — POST /api/settings/time-limits
  return null;
}

export async function saveAgeFilter(filter) {
  // TODO: backend integration — POST /api/settings/age-filter
  return null;
}

export async function getParentChatHistory() {
  // BLOCKED: no component renders this data yet
  return null;
}

// Camera stop signal — dispatches event so MonitorPage can set camOn=false
export function stopCamera() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('bi:stopcamera'));
  }
}

// Audio monitor cleanup alias
export function stopAudioMonitor() { stopMomMic(); }
```

## frontend/parent_app/src/data/mockData.js

```javascript
[FILE NOT FOUND: frontend/parent_app/src/data/mockData.js]
```

## frontend/parent_app/src/components/BottomNav.jsx

```jsx
const TABS = [
  { id: 'home', icon: '🏠', label: 'Trang chủ' },
  { id: 'monitor', icon: '📹', label: 'Giám sát' },
  { id: 'learning', icon: '📚', label: 'Học' },
  { id: 'journal', icon: '📔', label: 'Nhật ký' },
  { id: 'more', icon: '➕', label: 'Thêm' },
];

export default function BottomNav({ activeTab, onTabChange }) {
  return (
    <nav className="bottom-nav">
      {TABS.map(t => (
        <button
          key={t.id}
          className={`bottom-nav-item${activeTab === t.id ? ' active' : ''}`}
          onClick={() => onTabChange(t.id)}
        >
          <span className="nav-icon">{t.icon}</span>
          {t.label}
        </button>
      ))}
    </nav>
  );
}
```

## frontend/parent_app/src/components/FeatureBadge.jsx

```jsx
const LABELS = {
  'coming-soon': 'Sắp hỗ trợ',
  'mock-data': 'Dữ liệu mẫu',
  'no-backend': 'Chưa kết nối backend',
};

export default function FeatureBadge({ type }) {
  return (
    <span className={`feature-badge ${type}`}>
      {LABELS[type] || type}
    </span>
  );
}
```

## frontend/parent_app/src/components/RobotStatusCard.jsx

```jsx
export default function RobotStatusCard({ status }) {
  const labels = {
    online: 'Đang hoạt động',
    offline: 'Mất kết nối',
    connecting: 'Đang kết nối...',
  };

  const subs = {
    online: 'Robot Bi đang sẵn sàng',
    offline: 'Mất tín hiệu từ robot',
    connecting: 'Đang thử kết nối lại',
  };

  return (
    <div className={`robot-status-card ${status}`}>
      <div className="robot-status-row">
        <div className={`status-dot ${status}`} />
        <span className="robot-status-label">{labels[status] || status}</span>
      </div>
      <div className="robot-status-sub">{subs[status] || ''}</div>
    </div>
  );
}
```

## frontend/parent_app/src/components/SectionState.jsx

```jsx
export default function SectionState({
  state,
  loadingText = 'Đang tải...',
  errorText = 'Không tải được dữ liệu.',
  emptyText = 'Chưa có dữ liệu.',
  emptyIcon = '📭',
  onRetry,
}) {
  if (state === 'loading') {
    return (
      <div className="section-state">
        <div className="spinner" />
        <span className="state-text">{loadingText}</span>
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="section-state">
        <span className="state-icon">⚠️</span>
        <span className="state-text">{errorText}</span>
        {onRetry && (
          <button className="retry-btn" onClick={onRetry}>
            Thử lại
          </button>
        )}
      </div>
    );
  }

  if (state === 'empty') {
    return (
      <div className="section-state">
        <span className="state-icon">{emptyIcon}</span>
        <span className="state-text">{emptyText}</span>
      </div>
    );
  }

  return null;
}
```

## frontend/parent_app/src/components/SettingsOverlay.jsx

```jsx
import { useState, useEffect } from 'react';
import {
  apiFetch,
  getChildProfiles,
  getSystemLogs,
  showToast,
} from '../services/api.js';
import SectionState from './SectionState.jsx';
import FeatureBadge from './FeatureBadge.jsx';

export default function SettingsOverlay({ isAdmin, onClose }) {
  const [childProfiles, setChildProfiles] = useState([]);
  const [childLoading, setChildLoading] = useState(true);
  const [persona, setPersona] = useState(null);
  const [personaLoading, setPersonaLoading] = useState(false);
  const [families, setFamilies] = useState([]);
  const [familiesState, setFamiliesState] = useState('idle');
  const [systemLogs, setSystemLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [adminExpanded, setAdminExpanded] = useState(false);

  // Sleep schedule state (UI only, coming-soon)
  const [sleepStart, setSleepStart] = useState('21:00');
  const [sleepEnd, setSleepEnd] = useState('06:30');
  // Time limit state
  const [dailyLimit, setDailyLimit] = useState(60);
  // Age filter state
  const [ageFilter, setAgeFilter] = useState('6-9');

  useEffect(() => {
    loadChildProfiles();
  }, []);

  async function loadChildProfiles() {
    setChildLoading(true);
    const data = await getChildProfiles();
    setChildProfiles(data || []);
    setChildLoading(false);
  }

  async function loadPersona() {
    setPersonaLoading(true);
    const data = await apiFetch('/api/persona');
    setPersona(data?.persona || data);
    setPersonaLoading(false);
  }

  async function loadFamilies() {
    setFamiliesState('loading');
    const data = await apiFetch('/api/admin/families');
    if (data) {
      setFamilies(Array.isArray(data) ? data : data.families || []);
      setFamiliesState('data');
    } else {
      setFamiliesState('error');
    }
  }

  async function loadSystemLogs() {
    setLogsLoading(true);
    const data = await getSystemLogs();
    setSystemLogs(data || []);
    setLogsLoading(false);
  }

  function handleExpandAdmin() {
    if (!adminExpanded) {
      setAdminExpanded(true);
      loadPersona();
      loadFamilies();
      loadSystemLogs();
    } else {
      setAdminExpanded(false);
    }
  }

  return (
    <div className="settings-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="settings-panel">
        {/* Header */}
        <div className="settings-header">
          <span className="settings-title">⚙️ Cài đặt</span>
          <button className="settings-close" onClick={onClose} title="Đóng">✕</button>
        </div>

        {/* Section 1: Hồ sơ trẻ */}
        <div className="settings-section">
          <div className="settings-section-title">
            👧 Hồ sơ trẻ
            <FeatureBadge type="mock-data" />
          </div>
          {childLoading ? (
            <SectionState state="loading" loadingText="Đang tải hồ sơ..." />
          ) : childProfiles.length === 0 ? (
            <SectionState state="empty" emptyText="Chưa có hồ sơ trẻ." emptyIcon="👧" />
          ) : (
            childProfiles.map(child => (
              <div key={child.id} className="profile-card">
                <div className="profile-avatar">{child.avatar}</div>
                <div>
                  <div className="profile-name">{child.name}</div>
                  <div className="profile-info">
                    {child.age} tuổi · {child.grade} · Giới hạn {child.dailyLimit} phút/ngày
                  </div>
                </div>
              </div>
            ))
          )}
          <button
            className="btn-outline"
            style={{ marginTop: 10, width: '100%' }}
            onClick={() => showToast('Quản lý hồ sơ: Sắp hỗ trợ')}
          >
            ➕ Thêm hồ sơ
          </button>
        </div>

        {/* Section 2: Thông báo & Nhắc nhở */}
        <div className="settings-section">
          <div className="settings-section-title">
            🔔 Thông báo & Nhắc nhở
            <FeatureBadge type="coming-soon" />
          </div>
          <div className="settings-row">
            <div>
              <div className="settings-row-label">Thông báo hoạt động bất thường</div>
              <div className="settings-row-sub">Nhận cảnh báo khi bé khóc hoặc có sự kiện bất thường</div>
            </div>
            <button className="btn-sm secondary" onClick={() => showToast('Thông báo: Sắp hỗ trợ')}>
              Bật/Tắt
            </button>
          </div>
          <div className="settings-row">
            <div>
              <div className="settings-row-label">Nhắc nhở nhiệm vụ</div>
              <div className="settings-row-sub">Thông báo khi Bi nhắc bé làm nhiệm vụ</div>
            </div>
            <button className="btn-sm secondary" onClick={() => showToast('Nhắc nhở: Sắp hỗ trợ')}>
              Bật/Tắt
            </button>
          </div>
        </div>

        {/* Section 3: Giờ hoạt động robot */}
        <div className="settings-section">
          <div className="settings-section-title">
            ⏰ Giờ hoạt động robot
            <FeatureBadge type="coming-soon" />
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
            <div>
              <div className="form-label">Giờ tắt (ngủ)</div>
              <input
                type="time"
                className="form-input"
                style={{ width: 'auto' }}
                value={sleepStart}
                onChange={e => setSleepStart(e.target.value)}
              />
            </div>
            <div>
              <div className="form-label">Giờ bật (thức)</div>
              <input
                type="time"
                className="form-input"
                style={{ width: 'auto' }}
                value={sleepEnd}
                onChange={e => setSleepEnd(e.target.value)}
              />
            </div>
          </div>
          <button
            className="btn-outline"
            onClick={() => showToast('Giờ hoạt động: Sắp hỗ trợ')}
          >
            💾 Lưu lịch
          </button>
        </div>

        {/* Section 4: Nội dung & An toàn */}
        <div className="settings-section">
          <div className="settings-section-title">
            🛡️ Nội dung & An toàn
            <FeatureBadge type="coming-soon" />
          </div>
          <div style={{ marginBottom: 12 }}>
            <div className="form-label">Giới hạn thời gian mỗi ngày: {dailyLimit} phút</div>
            <input
              type="range"
              min={15}
              max={180}
              step={15}
              value={dailyLimit}
              onChange={e => setDailyLimit(Number(e.target.value))}
              style={{ width: '100%', marginTop: 8 }}
            />
          </div>
          <div style={{ marginBottom: 12 }}>
            <div className="form-label">Bộ lọc chủ đề theo tuổi</div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
              {['3-5', '5-7', '6-9', '8-12'].map(range => (
                <button
                  key={range}
                  className={`btn-sm ${ageFilter === range ? 'primary' : 'secondary'}`}
                  onClick={() => setAgeFilter(range)}
                >
                  {range} tuổi
                </button>
              ))}
            </div>
          </div>
          <button
            className="btn-outline"
            onClick={() => showToast('Nội dung & An toàn: Sắp hỗ trợ')}
          >
            💾 Lưu cài đặt
          </button>
        </div>

        {/* Section 5: Kết nối thiết bị / QR */}
        <div className="settings-section">
          <div className="settings-section-title">
            📡 Kết nối thiết bị
            <FeatureBadge type="coming-soon" />
          </div>
          <div
            style={{
              width: 120, height: 120, background: 'var(--bg)', border: '2px dashed var(--border)',
              borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 40, marginBottom: 10,
            }}
          >
            📱
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>
            Mã QR kết nối thiết bị — Sắp hỗ trợ
          </p>
        </div>

        {/* Section 6: Chế độ kỹ thuật — admin only */}
        {isAdmin && (
          <div className="settings-section">
            <button
              className="settings-section-title"
              style={{ background: 'none', border: 'none', cursor: 'pointer', width: '100%', textAlign: 'left', padding: 0 }}
              onClick={handleExpandAdmin}
            >
              🔧 Chế độ kỹ thuật / Quản trị
              <span style={{ marginLeft: 8, color: 'var(--muted)', fontSize: 14 }}>
                {adminExpanded ? '▲' : '▼'}
              </span>
            </button>

            {adminExpanded && (
              <div style={{ marginTop: 14 }}>
                {/* System logs */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                    📋 Nhật ký hệ thống
                    <FeatureBadge type="no-backend" />
                  </div>
                  {logsLoading ? (
                    <SectionState state="loading" loadingText="Đang tải nhật ký..." />
                  ) : systemLogs.length === 0 ? (
                    <SectionState state="empty" emptyText="Không có nhật ký." emptyIcon="📋" />
                  ) : (
                    <div style={{ background: '#0f172a', borderRadius: 12, padding: 12, overflow: 'auto', maxHeight: 240 }}>
                      {systemLogs.map(log => (
                        <div key={log.id} className="log-item">
                          <span className={`log-level ${log.level}`}>[{log.level}]</span>
                          <span className="log-msg">{log.message}</span>
                          <span className="log-time" style={{ color: '#64748b' }}>
                            {log.source}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Persona settings (real API) */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>🤖 Cài đặt Persona</div>
                  {personaLoading ? (
                    <SectionState state="loading" loadingText="Đang tải persona..." />
                  ) : persona ? (
                    <div className="profile-card">
                      <div className="profile-avatar">🤖</div>
                      <div>
                        <div className="profile-name">{persona.name || 'Bi'}</div>
                        <div className="profile-info">Giọng: {persona.voice || '—'}</div>
                      </div>
                    </div>
                  ) : (
                    <SectionState state="error" errorText="Không tải được persona." onRetry={loadPersona} />
                  )}
                </div>

                {/* Admin families (real API) */}
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>👨‍👩‍👧‍👦 Quản lý gia đình</div>
                  {familiesState === 'idle' && null}
                  {familiesState === 'loading' && <SectionState state="loading" loadingText="Đang tải danh sách gia đình..." />}
                  {familiesState === 'error' && <SectionState state="error" errorText="Không tải được danh sách gia đình." onRetry={loadFamilies} />}
                  {familiesState === 'data' && (
                    families.length === 0 ? (
                      <SectionState state="empty" emptyText="Chưa có gia đình nào." emptyIcon="👨‍👩‍👧" />
                    ) : (
                      families.map((f, i) => (
                        <div key={f.family_id || i} className="profile-card">
                          <div className="profile-avatar">👨‍👩‍👧</div>
                          <div>
                            <div className="profile-name">{f.display_name || f.family_id}</div>
                            <div className="profile-info">ID: {f.family_id}</div>
                          </div>
                        </div>
                      ))
                    )
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
```

## frontend/parent_app/src/components/Sidebar.jsx

```jsx
import RobotStatusCard from './RobotStatusCard.jsx';
import UserCard from './UserCard.jsx';

const TABS = [
  { id: 'home', icon: '🏠', label: 'Trang chủ' },
  { id: 'monitor', icon: '📹', label: 'Giám sát' },
  { id: 'learning', icon: '📚', label: 'Học tập' },
  { id: 'journal', icon: '📔', label: 'Nhật ký' },
  { id: 'more', icon: '➕', label: 'Thêm' },
];

export default function Sidebar({
  activeTab,
  onTabChange,
  robotStatus,
  user,
  activeChild,
  onOpenSettings,
  onLogout,
  onSwitchChild,
}) {
  return (
    <nav className="side-nav">
      <div className="side-nav-logo">
        <span className="logo-icon">🤖</span>
        <strong>Robot Bi</strong>
      </div>

      <div className="side-nav-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`side-nav-item${activeTab === t.id ? ' active' : ''}`}
            onClick={() => onTabChange(t.id)}
          >
            <span className="nav-icon">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      {/* Bottom section — locked order: robot status → user card → settings → logout */}
      <div className="side-nav-bottom">
        <RobotStatusCard status={robotStatus} />
        <UserCard user={user} activeChild={activeChild} onSwitchChild={onSwitchChild} />
        <button className="side-nav-action" onClick={onOpenSettings}>
          ⚙️ Cài đặt
        </button>
        <button className="side-nav-action danger" onClick={onLogout}>
          🚪 Đăng xuất
        </button>
      </div>
    </nav>
  );
}
```

## frontend/parent_app/src/components/Toast.jsx

```jsx
import { useState, useEffect } from 'react';
import { registerToast } from '../services/api.js';

export default function Toast() {
  const [message, setMessage] = useState(null);

  useEffect(() => {
    registerToast((msg) => {
      setMessage(msg);
    });
  }, []);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(null), 3000);
    return () => clearTimeout(timer);
  }, [message]);

  if (!message) return null;

  return (
    <div className="toast-container notif-banner">
      <div className="toast">{message}</div>
    </div>
  );
}
```

## frontend/parent_app/src/components/UserCard.jsx

```jsx
export default function UserCard({ user, activeChild, onSwitchChild }) {
  return (
    <div className="user-card" onClick={onSwitchChild} title="Nhấn để chọn hồ sơ trẻ">
      <div className="user-card-row">
        <span className="user-avatar">👤</span>
        <div>
          <div className="user-name">{user?.username || 'Phụ huynh'}</div>
          <div className="user-role">{user?.isAdmin ? '🛡️ Admin' : 'Phụ huynh'}</div>
          {activeChild && (
            <div className="user-child">👧 {activeChild.name}</div>
          )}
        </div>
      </div>
    </div>
  );
}
```

## frontend/parent_app/src/pages/HomePage.jsx

```jsx
import { useState, useEffect } from 'react';
import { apiFetch } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import FeatureBadge from '../components/FeatureBadge.jsx';

function fmtTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch (_) { return ts; }
}

const EVENT_ICONS = {
  chat: '💬', homework: '📚', game: '🎮', safety_filter: '⚠️',
  cry: '😢', offline: '📴', battery_low: '🔋', default: '📌',
};

export default function HomePage({ user, lastWsEvent }) {
  const [weeklyState, setWeeklyState] = useState('loading');
  const [weekly, setWeekly] = useState(null);
  const [eventsState, setEventsState] = useState('loading');
  const [events, setEvents] = useState([]);
  const [todaySummary, setTodaySummary] = useState(null);
  const [alert, setAlert] = useState(null);

  const today = new Date().toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!lastWsEvent) return;
    if (lastWsEvent.type === 'safety_filter' || lastWsEvent.type === 'cry') {
      setAlert(lastWsEvent);
    }
    // Refresh events on any realtime event
    loadEvents();
  }, [lastWsEvent]);

  async function loadData() {
    loadWeekly();
    loadEvents();
    loadTodaySummary();
  }

  async function loadWeekly() {
    setWeeklyState('loading');
    const data = await apiFetch('/api/analytics/weekly');
    if (data) {
      setWeekly(data);
      setWeeklyState('data');
    } else {
      setWeeklyState('error');
    }
  }

  async function loadTodaySummary() {
    const [dailyData, taskData, emotionData] = await Promise.all([
      apiFetch('/api/analytics/daily'),
      apiFetch('/api/tasks'),
      apiFetch('/api/emotion/today'),
    ]);
    setTodaySummary({
      sessions: dailyData?.conversations ?? 0,
      learningMinutes: dailyData?.learning_minutes ?? 0,
      emotion: emotionData?.dominant || emotionData?.dominant_emotion || '😊',
      tasksCompleted: taskData ? taskData.filter(t => t.completed_today).length : 0,
      totalTasks: taskData?.length ?? 0,
    });
  }

  async function loadEvents() {
    setEventsState('loading');
    const data = await apiFetch('/api/events?limit=5');
    const list = data?.events || [];
    if (list.length > 0) {
      setEvents(list);
      setEventsState('data');
    } else if (data) {
      setEventsState('empty');
    } else {
      setEventsState('error');
    }
  }

  return (
    <div>
      {/* Hero header */}
      <div className="home-hero">
        <div className="home-greeting">Xin chào, Mẹ yêu! 💖</div>
        <div className="home-date">{today}</div>
      </div>

      <div className="page-body">
        {/* Alert card — only visible on safety/cry events */}
        {alert && (
          <div className="alert-card">
            <div className="alert-icon">⚠️</div>
            <div>
              <div className="alert-text">Cảnh báo: {alert.type === 'cry' ? 'Bé đang khóc!' : 'Nội dung bị lọc'}</div>
              <div className="alert-sub">{alert.message || ''}</div>
            </div>
          </div>
        )}

        {/* Today summary grid */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 'var(--font-section)', fontWeight: 700, marginBottom: 10, color: 'var(--text)' }}>
            📊 Tóm tắt hôm nay
          </div>
          <div className="today-grid">
            <div className="metric-card grad-blue">
              <div className="metric-num">
                {todaySummary?.sessions ?? '—'}
                <span className="metric-online-dot" />
              </div>
              <div className="metric-label">Lượt trò chuyện</div>
            </div>
            <div className="metric-card grad-orange-pink">
              <div className="metric-num">{todaySummary?.learningMinutes ?? '—'}</div>
              <div className="metric-label">8 hoạt động</div>
            </div>
            <div className="metric-card grad-mint">
              <div className="metric-num" style={{ fontSize: 22 }}>{todaySummary?.emotion ?? '😊'}</div>
              <div className="metric-label">Vui vẻ</div>
            </div>
            <div className="metric-card grad-purple-soft">
              <div className="metric-num">
                {todaySummary ? `${todaySummary.tasksCompleted}/${todaySummary.totalTasks}` : '—'}
              </div>
              <div className="metric-label">3/5 hoàn thành</div>
            </div>
          </div>
        </div>

        {/* Weekly report */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📈 Báo cáo tuần</span>
            <button className="btn-sm secondary" onClick={loadWeekly} style={{ minHeight: 36 }}>↻</button>
          </div>
          {weeklyState === 'loading' && <SectionState state="loading" loadingText="Đang tải báo cáo tuần..." />}
          {weeklyState === 'error' && <SectionState state="error" errorText="Không tải được báo cáo tuần." onRetry={loadWeekly} />}
          {weeklyState === 'data' && weekly && (
            <div className="weekly-stat-row">
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.total_sessions ?? weekly.sessions ?? weekly.conversations ?? 0}</div>
                <div className="weekly-stat-label">Lượt hội thoại</div>
              </div>
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.total_minutes ?? weekly.minutes ?? weekly.hours ?? 0}</div>
                <div className="weekly-stat-label">Phút học</div>
              </div>
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.homework_count ?? 0}</div>
                <div className="weekly-stat-label">Bài tập</div>
              </div>
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.task_completion ?? weekly.tasks_completed ?? 0}</div>
                <div className="weekly-stat-label">Hoàn thành</div>
              </div>
            </div>
          )}
        </div>

        {/* Room location — coming soon */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📍 Vị trí phòng robot</span>
            <FeatureBadge type="coming-soon" />
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>
            Tính năng định vị phòng đang được phát triển.
          </p>
        </div>

        {/* Recent events */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🔔 Hoạt động gần nhất</span>
            <button className="btn-sm secondary" onClick={loadEvents} style={{ minHeight: 36 }}>↻</button>
          </div>
          {eventsState === 'loading' && <SectionState state="loading" loadingText="Đang tải sự kiện..." />}
          {eventsState === 'error' && <SectionState state="error" errorText="Không tải được sự kiện." onRetry={loadEvents} />}
          {eventsState === 'empty' && <SectionState state="empty" emptyText="Bi đang chờ bé ra chơi! 🤖" emptyIcon="🤖" />}
          {eventsState === 'data' && (
            <div className="event-list">
              {events.map((evt, i) => (
                <div key={evt.id || i} className="event-row">
                  <div className="event-icon">
                    {EVENT_ICONS[evt.type] || EVENT_ICONS.default}
                  </div>
                  <div className="event-body">
                    <div className="event-title">{evt.message || evt.type || 'Sự kiện'}</div>
                    <div className="event-time">{fmtTime(evt.timestamp || evt.created_at)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

## frontend/parent_app/src/pages/JournalPage.jsx

```jsx
import { useState, useEffect } from 'react';
import { getConversations, getConversation, getMonthlyEmotions, showToast } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import FeatureBadge from '../components/FeatureBadge.jsx';

function fmtTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch (_) { return ts; }
}

export default function JournalPage() {
  const [filterType, setFilterType] = useState('all');
  const [filterDate, setFilterDate] = useState('');
  const [threadsState, setThreadsState] = useState('loading');
  const [threads, setThreads] = useState([]);
  const [selectedThread, setSelectedThread] = useState(null);
  const [threadDetail, setThreadDetail] = useState(null);
  const [threadLoading, setThreadLoading] = useState(false);
  const [emotionData, setEmotionData] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    loadThreads();
    loadEmotions();
  }, []);

  async function loadThreads() {
    setThreadsState('loading');
    setSelectedThread(null);
    setThreadDetail(null);
    const data = await getConversations(20);
    const list = data?.conversations || [];
    if (list.length > 0) {
      setThreads(list);
      setThreadsState('data');
    } else if (data) {
      setThreadsState('empty');
    } else {
      setThreadsState('error');
    }
  }

  async function loadEmotions() {
    const data = await getMonthlyEmotions();
    if (data) setEmotionData(data);
  }

  async function openThread(id) {
    setThreadLoading(true);
    setSelectedThread(id);
    const data = await getConversation(id);
    setThreadDetail(data);
    setThreadLoading(false);
  }

  // Client-side filter
  const filteredThreads = threads.filter(c => {
    if (filterDate) {
      const d = new Date(c.started_at);
      const fd = new Date(filterDate);
      if (d.toDateString() !== fd.toDateString()) return false;
    }
    if (filterType !== 'all') {
      if (filterType === 'homework' && !c.is_homework) return false;
    }
    return true;
  });

  return (
    <div>
      <div className="page-header">
        <div className="page-title">📔 Nhật ký</div>
        <div className="page-subtitle">Lịch sử hoạt động và hội thoại</div>
      </div>

      <div className="page-body">
        {/* Filter bar */}
        <div className="filter-bar">
          <div className="pill-tabs">
            {[['all', 'Tất cả'], ['chat', 'Trò chuyện'], ['homework', 'Bài tập']].map(([val, label]) => (
              <button
                key={val}
                className={`pill-tab${filterType === val ? ' active' : ''}`}
                onClick={() => setFilterType(val)}
              >
                {label}
              </button>
            ))}
          </div>

          <input
            type="date"
            className="filter-date"
            value={filterDate}
            onChange={e => setFilterDate(e.target.value)}
          />

          <button
            className="btn-sm secondary"
            onClick={() => { setFilterType('all'); setFilterDate(''); }}
          >
            Xóa lọc
          </button>

          {/* Export button */}
          <button
            className="btn-sm primary"
            onClick={() => showToast('Xuất báo cáo: Tính năng đang phát triển')}
          >
            📤 Xuất PDF/CSV <FeatureBadge type="coming-soon" />
          </button>

          <button
            className="btn-sm secondary"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            🔍 Bộ lọc nâng cao
          </button>
        </div>

        {showAdvanced && (
          <div className="card" style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <FeatureBadge type="coming-soon" />
              <span style={{ color: 'var(--muted)', fontSize: 14 }}>Lọc theo thiết bị — Sắp hỗ trợ</span>
            </div>
          </div>
        )}

        {/* Conversations */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">💬 Hội thoại</span>
            <button className="btn-sm secondary" onClick={loadThreads} style={{ minHeight: 36 }}>↻</button>
          </div>

          {selectedThread ? (
            threadLoading ? (
              <SectionState state="loading" loadingText="Đang tải hội thoại..." />
            ) : threadDetail ? (
              <div>
                <button className="btn-back" onClick={() => { setSelectedThread(null); setThreadDetail(null); }}>
                  ← Quay lại
                </button>
                <div style={{ fontWeight: 700, fontSize: 'var(--font-section)', marginBottom: 14 }}>
                  {threadDetail.session?.title || 'Hội thoại'}
                </div>
                <div style={{ marginBottom: 8, color: 'var(--muted)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button disabled title="Sắp hỗ trợ" style={{ opacity: 0.4, cursor: 'not-allowed', padding: '6px 12px', borderRadius: 8, border: '1.5px solid var(--border)', background: 'none', fontSize: 13 }}>
                    ▶ Phát lại
                  </button>
                  <FeatureBadge type="coming-soon" />
                </div>
                <div className="chat-bubble-wrap">
                  {(threadDetail.turns || []).map((turn, i) => (
                    <div key={i} className="chat-entry">
                      <div className="chat-who">{turn.role === 'user' ? '👦 Bé' : '🤖 Bi'}</div>
                      <div className={`bubble ${turn.role === 'user' ? 'user' : 'bi'}`}>
                        {turn.content}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <SectionState state="error" errorText="Không tải được hội thoại." onRetry={() => openThread(selectedThread)} />
            )
          ) : (
            <>
              {threadsState === 'loading' && <SectionState state="loading" loadingText="Đang tải hội thoại..." />}
              {threadsState === 'error' && <SectionState state="error" errorText="Không tải được hội thoại." onRetry={loadThreads} />}
              {threadsState === 'empty' && <SectionState state="empty" emptyText="Chưa có hội thoại nào" emptyIcon="💬" />}
              {threadsState === 'data' && (
                filteredThreads.length === 0 ? (
                  <SectionState state="empty" emptyText="Không có kết quả phù hợp với bộ lọc." emptyIcon="🔍" />
                ) : (
                  <div className="thread-timeline">
                    {filteredThreads.map(c => (
                      <div key={c.session_id} className="thread-item" onClick={() => openThread(c.session_id)}>
                        <span className="thread-icon">
                          {c.is_homework ? '📚' : '💬'}
                        </span>
                        <div className="thread-body">
                          <div className="thread-title">{c.title || 'Hội thoại không tiêu đề'}</div>
                          <div className="thread-meta">
                            {fmtTime(c.started_at)} · {c.turn_count || 0} lượt
                          </div>
                        </div>
                        <span className="thread-arrow">›</span>
                      </div>
                    ))}
                  </div>
                )
              )}
            </>
          )}
        </div>

        {/* Monthly emotion chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📊 Cảm xúc theo tháng</span>
            <FeatureBadge type="mock-data" />
          </div>
          {emotionData.length > 0 ? (
            <>
              <div className="emotion-chart">
                {emotionData.map((week, i) => (
                  <div key={i} className="emotion-week">
                    <span className="emotion-week-label">{week.week}</span>
                    <div className="bar-row">
                      <div className="bar-seg happy" style={{ width: `${week.happy}%` }} title={`Vui: ${week.happy}%`} />
                      <div className="bar-seg neutral" style={{ width: `${week.neutral}%` }} title={`Bình thường: ${week.neutral}%`} />
                      <div className="bar-seg sad" style={{ width: `${week.sad}%` }} title={`Buồn: ${week.sad}%`} />
                      <div className="bar-seg stressed" style={{ width: `${week.stressed}%` }} title={`Căng thẳng: ${week.stressed}%`} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="emotion-legend">
                <div className="legend-item"><div className="legend-dot" style={{ background: '#22c55e' }} />Vui vẻ</div>
                <div className="legend-item"><div className="legend-dot" style={{ background: '#94a3b8' }} />Bình thường</div>
                <div className="legend-item"><div className="legend-dot" style={{ background: '#f59e0b' }} />Buồn</div>
                <div className="legend-item"><div className="legend-dot" style={{ background: '#ef4444' }} />Căng thẳng</div>
              </div>
            </>
          ) : (
            <SectionState state="loading" loadingText="Đang tải dữ liệu cảm xúc..." />
          )}
        </div>
      </div>
    </div>
  );
}
```

## frontend/parent_app/src/pages/LearningPage.jsx

```jsx
import { useState, useEffect } from 'react';
import { apiFetch, showToast } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import FeatureBadge from '../components/FeatureBadge.jsx';

export default function LearningPage({ activeChild }) {
  const [vocabState, setVocabState] = useState('loading');
  const [vocab, setVocab] = useState([]);
  const [vocabSearch, setVocabSearch] = useState('');
  const [tasksState, setTasksState] = useState('loading');
  const [tasks, setTasks] = useState([]);
  const [storiesState, setStoriesState] = useState('loading');
  const [stories, setStories] = useState([]);

  useEffect(() => {
    loadVocab();
    loadTasks();
    loadStories();
  }, []);

  async function loadVocab() {
    setVocabState('loading');
    const data = await apiFetch('/api/education/vocabulary');
    const words = data?.words || [];
    if (words.length > 0) { setVocab(words); setVocabState('data'); }
    else if (data) setVocabState('empty');
    else setVocabState('error');
  }

  async function loadTasks() {
    setTasksState('loading');
    const data = await apiFetch('/api/tasks');
    if (Array.isArray(data) && data.length > 0) { setTasks(data); setTasksState('data'); }
    else if (Array.isArray(data)) setTasksState('empty');
    else setTasksState('error');
  }

  async function loadStories() {
    setStoriesState('loading');
    const data = await apiFetch('/api/story/list');
    const list = data?.stories || data || [];
    if (Array.isArray(list) && list.length > 0) { setStories(list); setStoriesState('data'); }
    else if (data) setStoriesState('empty');
    else setStoriesState('error');
  }

  async function completeTask(id) {
    const r = await apiFetch(`/api/tasks/${id}/complete`, { method: 'POST' });
    if (r?.ok) {
      showToast('✅ Hoàn thành! +1 ⭐');
      loadTasks();
    } else {
      showToast('Nhiệm vụ đã hoàn thành rồi!');
    }
  }

  async function startGame(type) {
    const path = type === 'flashcard'
      ? '/api/education/flashcard/start'
      : `/api/game/${type}/start`;
    const r = await apiFetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    if (r) showToast('🎮 Trò chơi bắt đầu!');
    else showToast('⚠️ Chức năng này sẽ được kết nối sau.');
  }

  function speakWord(word) {
    apiFetch('/api/puppet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: word }),
    });
    showToast(`🔊 Bi đọc: ${word}`);
  }

  const filteredVocab = vocab.filter(w =>
    w.word?.toLowerCase().includes(vocabSearch.toLowerCase()) ||
    w.meaning?.toLowerCase().includes(vocabSearch.toLowerCase())
  );

  return (
    <div>
      <div className="page-header">
        <div className="page-title">📚 Học tập</div>
        <div className="page-subtitle">Từ vựng · Nhiệm vụ · Luyện tập · Truyện</div>
      </div>

      <div className="page-body">
        {/* Quick action shortcuts */}
        <div className="quick-actions-grid">
          <button className="quick-action-btn" onClick={() => document.querySelector('.vocab-grid')?.scrollIntoView({ behavior: 'smooth' })}>
            <span>📖</span>
            <span>Từ vựng</span>
          </button>
          <button className="quick-action-btn" onClick={() => startGame('flashcard')}>
            <span>🃏</span>
            <span>Flashcard</span>
          </button>
          <button className="quick-action-btn" onClick={() => showToast('Video: Chuyển sang tab Thêm')}>
            <span>🎬</span>
            <span>Video</span>
          </button>
          <button className="quick-action-btn" onClick={() => startGame('word-quiz')}>
            <span>🎮</span>
            <span>Trò chơi</span>
          </button>
        </div>

        {/* Progress ring + featured lesson */}
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div className="progress-ring-wrap">
            <svg className="progress-ring" viewBox="0 0 120 120" width="100" height="100">
              <circle cx="60" cy="60" r="50" fill="none" stroke="var(--primary-soft)" strokeWidth="12" />
              <circle cx="60" cy="60" r="50" fill="none" stroke="var(--primary)" strokeWidth="12"
                strokeDasharray="314" strokeDashoffset="78.5"
                strokeLinecap="round"
                style={{ transform: 'rotate(-90deg)', transformOrigin: '60px 60px' }}
              />
            </svg>
            <div className="progress-ring-label">75%</div>
          </div>
          <div className="lesson-card" style={{ flex: 1 }}>
            <div className="lesson-thumb">🔤</div>
            <div className="lesson-body">
              <div className="lesson-title">Từ vựng chủ đề Gia đình</div>
              <div className="lesson-meta">10 từ · 5–7 tuổi</div>
            </div>
            <button className="btn-start" onClick={() => startGame('vocabulary')}>Bắt đầu</button>
          </div>
        </div>

        {/* Vocabulary section */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🔤 Từ vựng</span>
            <button className="btn-sm secondary" onClick={loadVocab} style={{ minHeight: 36 }}>↻</button>
          </div>

          {vocabState === 'data' && (
            <input
              type="text"
              className="form-input"
              style={{ marginBottom: 12 }}
              placeholder="🔍 Tìm từ vựng..."
              value={vocabSearch}
              onChange={e => setVocabSearch(e.target.value)}
            />
          )}

          {vocabState === 'loading' && <SectionState state="loading" loadingText="Đang tải từ vựng..." />}
          {vocabState === 'error' && <SectionState state="error" errorText="Không tải được từ vựng." onRetry={loadVocab} />}
          {vocabState === 'empty' && <SectionState state="empty" emptyText="Chưa có từ vựng nào." emptyIcon="📚" />}
          {vocabState === 'data' && (
            filteredVocab.length === 0 ? (
              <SectionState state="empty" emptyText="Không tìm thấy từ phù hợp." emptyIcon="🔍" />
            ) : (
              <div className="vocab-grid">
                {filteredVocab.map((w, i) => (
                  <div key={i} className="vocab-card" onClick={() => speakWord(w.word)}>
                    <span className="vocab-emoji">{w.emoji || '📖'}</span>
                    <div className="vocab-word">{w.word}</div>
                    <div className="vocab-meaning">{w.meaning}</div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>

        {/* Quiz / Luyện tập */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🎮 Luyện tập</span>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button className="btn-action primary" onClick={() => startGame('word-quiz')}>
              📝 Bắt đầu Word Quiz
            </button>
            <button className="btn-action primary" onClick={() => startGame('voice-quiz')}>
              🎤 Bắt đầu Voice Quiz
            </button>
          </div>
        </div>

        {/* Tasks */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">✅ Nhiệm vụ hôm nay</span>
            <button className="btn-sm secondary" onClick={loadTasks} style={{ minHeight: 36 }}>↻</button>
          </div>
          {tasksState === 'loading' && <SectionState state="loading" loadingText="Đang tải nhiệm vụ..." />}
          {tasksState === 'error' && <SectionState state="error" errorText="Không tải được nhiệm vụ." onRetry={loadTasks} />}
          {tasksState === 'empty' && <SectionState state="empty" emptyText="Chưa có nhiệm vụ nào hôm nay." emptyIcon="📋" />}
          {tasksState === 'data' && (
            tasks.map(task => (
              <div key={task.task_id} className={`task-item${task.completed_today ? ' done' : ''}`}>
                <button
                  className={`task-check${task.completed_today ? ' done' : ''}`}
                  onClick={() => !task.completed_today && completeTask(task.task_id)}
                  title={task.completed_today ? 'Đã hoàn thành' : 'Đánh dấu hoàn thành'}
                >
                  {task.completed_today ? '✓' : ''}
                </button>
                <span className="task-name">{task.name}</span>
                <span className="task-stars">{'⭐'.repeat(task.stars || 0)}</span>
              </div>
            ))
          )}
        </div>

        {/* Stories */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📖 Truyện kể</span>
            <button className="btn-sm secondary" onClick={loadStories} style={{ minHeight: 36 }}>↻</button>
          </div>
          {storiesState === 'loading' && <SectionState state="loading" loadingText="Đang tải truyện..." />}
          {storiesState === 'error' && <SectionState state="error" errorText="Không tải được truyện." onRetry={loadStories} />}
          {storiesState === 'empty' && <SectionState state="empty" emptyText="Chưa có truyện nào." emptyIcon="📚" />}
          {storiesState === 'data' && (
            stories.slice(0, 6).map((s, i) => (
              <div key={i} className="media-card">
                <div className="media-thumb">{s.emoji || '📖'}</div>
                <div className="media-body">
                  <div className="media-title">{s.title}</div>
                  <div className="media-meta">{s.duration || ''} {s.age ? `· ${s.age}` : ''}</div>
                </div>
                <button
                  className="btn-sm primary media-action"
                  onClick={() => {
                    apiFetch('/api/story/tell', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ story_id: s.id || null }),
                    });
                    showToast(`📖 Bi đang kể: "${s.title}"`);
                  }}
                >
                  ▶ Kể
                </button>
              </div>
            ))
          )}
        </div>

        {/* Chat với Bi — coming soon */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">💬 Chat với Bi</span>
            <FeatureBadge type="coming-soon" />
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>
            Lịch sử chat phụ huynh ↔ Bi — Sắp hỗ trợ.
          </p>
        </div>
      </div>
    </div>
  );
}
```

## frontend/parent_app/src/pages/LoginPage.jsx

```jsx
import { useState } from 'react';
import { login } from '../services/api.js';

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setError('');
    setLoading(true);
    try {
      const userData = await login(username.trim(), password);
      onLogin(userData);
    } catch (err) {
      setError(err.message || 'Sai tên đăng nhập hoặc mật khẩu.');
      setPassword('');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-box">
        <div className="login-logo">🤖</div>
        <h2 className="login-title">Robot Bi</h2>
        <p className="login-subtitle">Ứng dụng quản lý phụ huynh</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="loginUsername">Tên đăng nhập</label>
            <input
              id="loginUsername"
              type="text"
              className="form-input"
              placeholder="Nhập tên đăng nhập"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="loginPassword">Mật khẩu</label>
            <input
              id="loginPassword"
              type="password"
              className="form-input"
              placeholder="Nhập mật khẩu"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Đang đăng nhập...' : '🔐 Đăng nhập'}
          </button>

          {error && <div className="login-error">{error}</div>}
        </form>
      </div>
    </div>
  );
}
```

## frontend/parent_app/src/pages/MonitorPage.jsx

```jsx
import { useState, useEffect } from 'react';
import { apiFetch, startMomMic, stopMomMic, isMomMicActive, showToast, getToken } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';

export default function MonitorPage() {
  const [camOn, setCamOn] = useState(false);
  const [camError, setCamError] = useState(false);
  const [momMicOn, setMomMicOn] = useState(false);
  const [weeklyState, setWeeklyState] = useState('loading');
  const [weekly, setWeekly] = useState(null);
  const [eventsState, setEventsState] = useState('loading');
  const [events, setEvents] = useState([]);

  useEffect(() => {
    loadWeekly();
    loadEvents();
  }, []);

  // Listen for external camera-stop signal (tab switch, logout, beforeunload)
  useEffect(() => {
    function handleCameraStop() { setCamOn(false); }
    window.addEventListener('bi:stopcamera', handleCameraStop);
    return () => window.removeEventListener('bi:stopcamera', handleCameraStop);
  }, []);

  async function loadWeekly() {
    setWeeklyState('loading');
    const data = await apiFetch('/api/analytics/weekly');
    if (data) { setWeekly(data); setWeeklyState('data'); }
    else setWeeklyState('error');
  }

  async function loadEvents() {
    setEventsState('loading');
    const data = await apiFetch('/api/events?limit=20');
    const list = data?.events || [];
    if (list.length > 0) { setEvents(list); setEventsState('data'); }
    else if (data) setEventsState('empty');
    else setEventsState('error');
  }

  async function handleStartMomMic() {
    try {
      await startMomMic();
      setMomMicOn(true);
      showToast('🎤 Mẹ đang nói — Bi đang tạm dừng');
    } catch (err) {
      showToast('Không thể bật mic: ' + err.message);
    }
  }

  function handleStopMomMic() {
    stopMomMic();
    setMomMicOn(false);
    showToast('Bi đang hoạt động bình thường');
  }

  function handleToggleCam() {
    setCamOn(prev => !prev);
    setCamError(false);
  }

  async function sendMotor(vx, vy) {
    const speed = 70;
    const forward = -vy * speed;
    const turn = vx * speed;
    const left = Math.round(forward + turn);
    const right = Math.round(forward - turn);
    await apiFetch('/api/motor/joystick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ left, right }),
    });
  }

  const token = getToken();

  return (
    <div>
      <div className="page-header">
        <div className="page-title">📹 Giám sát</div>
        <div className="page-subtitle">Camera · Điều khiển · Báo cáo</div>
      </div>

      <div className="page-body">
        {/* Camera section */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📷 Camera</span>
            <button className="btn-sm primary" onClick={handleToggleCam}>
              {camOn ? '⏹ Tắt Camera' : '▶ Bật Camera'}
            </button>
          </div>

          <div className="camera-section">
            {camOn && !camError ? (
              <img
                className="camera-feed"
                src={`/api/camera?auth=${encodeURIComponent(token)}`}
                alt="Camera feed"
                onError={() => { setCamError(true); }}
              />
            ) : (
              <div className="camera-placeholder">
                <span className="cam-icon">{camError ? '❌' : '📷'}</span>
                <p>{camError ? 'Camera không khả dụng' : 'Nhấn "Bật Camera" để xem'}</p>
              </div>
            )}
          </div>
        </div>

        {/* Mom-talk controls */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🎤 Nói chuyện với Bi</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 14 }}>
            Nhấn để bật micro và nói chuyện trực tiếp với robot.
          </p>
          <div className="mom-mic-controls">
            {!momMicOn ? (
              <button className="btn-action primary" onClick={handleStartMomMic}>
                🎤 Nói chuyện với Bi
              </button>
            ) : (
              <button className="btn-action danger" onClick={handleStopMomMic}>
                ⏹ Dừng — Trả lại cho Bi
              </button>
            )}
          </div>
          {momMicOn && (
            <p style={{ color: 'var(--danger)', fontSize: 14, marginTop: 10, fontWeight: 600 }}>
              🟠 Mẹ đang nói — Bi đang tạm dừng
            </p>
          )}
        </div>

        {/* Motor controls */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🕹️ Điều khiển robot</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 14 }}>
            Điều khiển hướng di chuyển của Robot Bi.
          </p>
          <div className="motor-grid">
            <div />
            <button className="motor-btn" onClick={() => sendMotor(0, -1)} title="Tiến">⬆️</button>
            <div />
            <button className="motor-btn" onClick={() => sendMotor(-1, 0)} title="Trái">⬅️</button>
            <button className="motor-btn stop" onClick={() => sendMotor(0, 0)} title="Dừng">⏹</button>
            <button className="motor-btn" onClick={() => sendMotor(1, 0)} title="Phải">➡️</button>
            <div />
            <button className="motor-btn" onClick={() => sendMotor(0, 1)} title="Lùi">⬇️</button>
            <div />
          </div>
        </div>

        {/* Weekly report detail */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📈 Báo cáo tuần chi tiết</span>
            <button className="btn-sm secondary" onClick={loadWeekly} style={{ minHeight: 36 }}>↻</button>
          </div>
          {weeklyState === 'loading' && <SectionState state="loading" loadingText="Đang tải báo cáo..." />}
          {weeklyState === 'error' && <SectionState state="error" errorText="Không tải được báo cáo tuần." onRetry={loadWeekly} />}
          {weeklyState === 'data' && weekly && (
            <div className="weekly-stat-row">
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.total_sessions ?? weekly.conversations ?? 0}</div>
                <div className="weekly-stat-label">Hội thoại</div>
              </div>
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.total_minutes ?? weekly.hours ?? 0}</div>
                <div className="weekly-stat-label">Phút học</div>
              </div>
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.homework_count ?? 0}</div>
                <div className="weekly-stat-label">Bài tập</div>
              </div>
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.task_completion ?? weekly.tasks_completed ?? 0}</div>
                <div className="weekly-stat-label">Hoàn thành</div>
              </div>
            </div>
          )}
        </div>

        {/* Recent events */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🔔 Sự kiện gần đây</span>
            <button className="btn-sm secondary" onClick={loadEvents} style={{ minHeight: 36 }}>↻</button>
          </div>
          {eventsState === 'loading' && <SectionState state="loading" loadingText="Đang tải sự kiện..." />}
          {eventsState === 'error' && <SectionState state="error" errorText="Không tải được sự kiện." onRetry={loadEvents} />}
          {eventsState === 'empty' && <SectionState state="empty" emptyText="Chưa có sự kiện nào." emptyIcon="📭" />}
          {eventsState === 'data' && (
            <div className="event-list">
              {events.map((evt, i) => (
                <div key={evt.id || i} className="event-row">
                  <div className="event-icon">📌</div>
                  <div className="event-body">
                    <div className="event-title">{evt.message || evt.type || 'Sự kiện'}</div>
                    <div className="event-time">
                      {evt.timestamp ? new Date(evt.timestamp).toLocaleString('vi-VN') : ''}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

## frontend/parent_app/src/pages/MorePage.jsx

```jsx
import { useState, useEffect } from 'react';
import { apiFetch, getRadioChannels, getVideoLessons, getInteractiveGames, showToast } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import FeatureBadge from '../components/FeatureBadge.jsx';

const DEMO_SONGS = {
  kids_vn: [{ title: 'Cá vàng bơi', artist: 'Nhạc thiếu nhi VN', icon: '🐠' }, { title: 'Đàn vịt con', artist: 'Nhạc thiếu nhi VN', icon: '🦆' }],
  kids_en: [{ title: 'Twinkle Twinkle', artist: 'Nursery Rhyme', icon: '⭐' }, { title: 'ABC Song', artist: 'Learning Songs', icon: '📚' }],
  lullaby: [{ title: 'Ru con', artist: 'Nhạc dân ca', icon: '🌙' }, { title: 'Con cò bay lả', artist: 'Dân ca', icon: '🐦' }],
};

const PLAYLIST_CATS = { kids_vn: 'vietnamese', kids_en: 'english', lullaby: 'lullabies' };

export default function MorePage() {
  const [musicPlaying, setMusicPlaying] = useState(false);
  const [currentPlaylist, setCurrentPlaylist] = useState('kids_vn');
  const [songs, setSongs] = useState(DEMO_SONGS['kids_vn']);
  const [currentTrack, setCurrentTrack] = useState(null);
  const [radioChannels, setRadioChannels] = useState([]);
  const [videoLessons, setVideoLessons] = useState([]);
  const [games, setGames] = useState([]);

  useEffect(() => {
    loadRadio();
    loadVideos();
    loadGames();
  }, []);

  async function loadPlaylist(type) {
    setCurrentPlaylist(type);
    const cat = PLAYLIST_CATS[type] || 'vietnamese';
    const data = await apiFetch(`/api/music/playlist?category=${cat}`);
    setSongs(data?.tracks || DEMO_SONGS[type] || []);
  }

  async function loadRadio() {
    const data = await getRadioChannels();
    if (data) setRadioChannels(data);
  }

  async function loadVideos() {
    const data = await getVideoLessons();
    if (data) setVideoLessons(data);
  }

  async function loadGames() {
    const data = await getInteractiveGames();
    if (data) setGames(data);
  }

  function toggleMusicPlay() {
    const newState = !musicPlaying;
    setMusicPlaying(newState);
    apiFetch(`/api/music/${newState ? 'play' : 'stop'}`, { method: 'POST' }).catch(() => {});
  }

  function musicCmd(cmd) {
    apiFetch(`/api/music/${cmd === 'prev' ? 'previous' : cmd}`, { method: 'POST' }).catch(() => {});
    showToast(`🎵 ${cmd}`);
  }

  function setVolume(v) {
    apiFetch('/api/music/volume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level: parseInt(v) }),
    }).catch(() => {});
  }

  function playTrack(song, type) {
    setCurrentTrack(song);
    setMusicPlaying(true);
    apiFetch('/api/music/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ track_id: song.id, category: PLAYLIST_CATS[type] }),
    });
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">➕ Thêm</div>
        <div className="page-subtitle">Nhạc · Radio · Video học · Trò chơi</div>
      </div>

      <div className="page-body">
        {/* Feature shortcut cards */}
        <div className="more-grid">
          <div className="more-card" style={{ background: 'linear-gradient(135deg, #FFE4E6 0%, #FECDD3 100%)' }}>
            <span>📻</span>
            <div>Radio</div>
          </div>
          <div className="more-card" style={{ background: 'var(--grad-mint)' }}>
            <span>🎵</span>
            <div>Âm nhạc</div>
          </div>
          <div className="more-card" style={{ background: 'var(--grad-purple-soft)' }}>
            <span>📖</span>
            <div>Truyện kể</div>
          </div>
          <div className="more-card" style={{ background: 'var(--grad-hot)', color: '#fff', position: 'relative' }}>
            <span className="hot-badge">HOT</span>
            <span>🎮</span>
            <div>Trò chơi</div>
          </div>
          <div className="more-card" style={{ background: 'var(--grad-blue)' }}>
            <span>🎬</span>
            <div>Video học</div>
          </div>
        </div>

        {/* Music player (real API) */}
        <div className="music-player-card">
          <div className="music-track-label">🎵 Đang phát</div>
          <div className="music-track-title">{currentTrack?.title || 'Chọn bài hát...'}</div>
          <div className="music-track-artist">{currentTrack?.artist || '—'}</div>
          <div className="music-controls">
            <button className="music-btn" onClick={() => musicCmd('prev')} title="Bài trước">⏮</button>
            <button className="music-btn play" onClick={toggleMusicPlay} title={musicPlaying ? 'Dừng' : 'Phát'}>
              {musicPlaying ? '⏸' : '▶'}
            </button>
            <button className="music-btn" onClick={() => musicCmd('next')} title="Bài tiếp">⏭</button>
            <button className="music-btn" onClick={() => musicCmd('shuffle')} title="Ngẫu nhiên">🔀</button>
          </div>
          <div className="music-volume-row">
            <span title="Âm lượng">🔊</span>
            <input type="range" min="0" max="100" defaultValue="50" onChange={e => setVolume(e.target.value)} title="Âm lượng" style={{ flex: 1 }} />
          </div>
        </div>

        {/* Playlist tabs */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📋 Danh sách phát</span>
          </div>
          <div className="filter-bar" style={{ marginBottom: 12 }}>
            {[['kids_vn', '🇻🇳 VN'], ['kids_en', '🇬🇧 Anh'], ['lullaby', '🌙 Ru ngủ']].map(([type, label]) => (
              <button
                key={type}
                className={`btn-sm ${currentPlaylist === type ? 'primary' : 'secondary'}`}
                onClick={() => loadPlaylist(type)}
              >
                {label}
              </button>
            ))}
          </div>
          {songs.length === 0 ? (
            <SectionState state="empty" emptyText="Chưa có bài hát." emptyIcon="🎵" />
          ) : (
            songs.map((s, i) => (
              <div key={i} className="media-card">
                <div className="media-thumb">{s.icon || '🎵'}</div>
                <div className="media-body">
                  <div className="media-title">{s.title}</div>
                  <div className="media-meta">{s.artist}</div>
                </div>
                <button className="btn-sm primary media-action" onClick={() => playTrack(s, currentPlaylist)}>
                  ▶
                </button>
              </div>
            ))
          )}
        </div>

        {/* Radio — mock data */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📻 Radio</span>
            <FeatureBadge type="mock-data" />
          </div>
          {radioChannels.length === 0 ? (
            <SectionState state="loading" loadingText="Đang tải kênh radio..." />
          ) : (
            radioChannels.map(ch => (
              <div key={ch.id} className="media-card">
                <div className="media-thumb">{ch.icon}</div>
                <div className="media-body">
                  <div className="media-title">{ch.name}</div>
                  <div className="media-meta">{ch.genre} · {ch.frequency}</div>
                </div>
                <button
                  className="btn-sm primary media-action"
                  onClick={() => showToast('Radio: Sắp hỗ trợ')}
                >
                  ▶ Nghe
                </button>
              </div>
            ))
          )}
        </div>

        {/* Video học — mock data */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🎬 Video học</span>
            <FeatureBadge type="mock-data" />
          </div>
          {videoLessons.length === 0 ? (
            <SectionState state="loading" loadingText="Đang tải video..." />
          ) : (
            videoLessons.map(v => (
              <div key={v.id} className="media-card">
                <div className="media-thumb">{v.thumbnail}</div>
                <div className="media-body">
                  <div className="media-title">{v.title}</div>
                  <div className="media-meta">{v.subject} · {v.duration} · {v.age}</div>
                </div>
                <button
                  className="btn-sm primary media-action"
                  onClick={() => showToast('Video: Sắp hỗ trợ')}
                >
                  ▶ Xem
                </button>
              </div>
            ))
          )}
        </div>

        {/* Interactive games — coming soon */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🎮 Trò chơi tương tác</span>
            <FeatureBadge type="coming-soon" />
          </div>
          {games.length === 0 ? (
            <SectionState state="loading" loadingText="Đang tải trò chơi..." />
          ) : (
            games.map(g => (
              <div key={g.id} className="media-card">
                <div className="media-thumb">{g.icon}</div>
                <div className="media-body">
                  <div className="media-title">{g.name}</div>
                  <div className="media-meta">{g.description} · {g.difficulty} · {g.age}</div>
                </div>
                <button
                  className="btn-sm secondary media-action"
                  disabled
                  title="Sắp hỗ trợ"
                >
                  Sắp ra
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
```

## frontend/robot_display/index.html

```html
<!DOCTYPE html>
<html lang="vi">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=480, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <base href=".">
  <title>Robot Bi — Display</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin="anonymous">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">
  <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    /* ===== BASE ===== */
    *,
    *::before,
    *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    :root {
      --bg: #0a0e1a;
      --cyan: #00d4ff;
      --gold: #ffd700;
      --green: #00ff88;
      --purple: #c084fc;
      --white: #ffffff;
      --accent: var(--cyan);
      --glow: 0 0 20px var(--cyan), 0 0 40px rgba(0, 212, 255, 0.4);
      --face-size: 220px;
    }

    html,
    body {
      width: 480px;
      height: 320px;
      overflow: hidden;
      background: var(--bg);
      font-family: 'Nunito', sans-serif;
      color: var(--white);
      user-select: none;
    }

    /* ===== PARTICLES ===== */
    #particles {
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 0;
    }

    .particle {
      position: absolute;
      width: 2px;
      height: 2px;
      border-radius: 50%;
      background: var(--cyan);
      opacity: 0;
      animation: float-particle linear infinite;
    }

    @keyframes float-particle {
      0% {
        transform: translateY(320px) translateX(0);
        opacity: 0;
      }

      10% {
        opacity: 0.6;
      }

      90% {
        opacity: 0.3;
      }

      100% {
        transform: translateY(-10px) translateX(var(--dx, 20px));
        opacity: 0;
      }
    }

    /* ===== MAIN STAGE ===== */
    #stage {
      position: relative;
      width: 480px;
      height: 320px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 1;
      transition: filter 0.8s ease;
    }

    #stage.sleeping {
      filter: brightness(0.3);
    }

    /* ===== FACE CONTAINER ===== */
    #face-wrap {
      position: relative;
      width: var(--face-size);
      height: var(--face-size);
      transition: transform 0.3s ease;
    }

    #face-wrap.breathe {
      animation: breathe 4s ease-in-out infinite;
    }

    @keyframes breathe {

      0%,
      100% {
        transform: scale(1);
      }

      50% {
        transform: scale(1.04);
      }
    }

    /* ===== SVG FACE ===== */
    #robot-face {
      width: 100%;
      height: 100%;
      overflow: visible;
    }

    /* Eye glow filter */
    #robot-face defs .eye-glow feFlood {
      flood-color: var(--accent);
    }

    /* Pupils (JS moves via transform) */
    .pupil {
      transition: transform 0.5s ease, r 0.3s ease;
    }

    /* Eye blink — scaleY on eye group */
    .eye-group {
      transform-box: fill-box;
      transform-origin: center;
      transition: transform 0.08s ease;
    }

    .eye-group.blink {
      animation: blink-anim 0.15s ease-in-out;
    }

    @keyframes blink-anim {

      0%,
      100% {
        transform: scaleY(1);
      }

      50% {
        transform: scaleY(0.05);
      }
    }

    /* Happy eyes (talking) */
    .eye-arc {
      opacity: 0;
      transition: opacity 0.3s;
    }

    .happy .eye-arc {
      opacity: 1;
    }

    .happy .eye-circle {
      opacity: 0;
    }

    /* Pulse rings (listening) */
    .pulse-ring {
      transform-box: fill-box;
      transform-origin: center;
      opacity: 0;
      animation: none;
    }

    .listening .pulse-ring {
      animation: pulse-ring 1.5s ease-out infinite;
    }

    .pulse-ring:nth-child(2) {
      animation-delay: 0.5s;
    }

    .pulse-ring:nth-child(3) {
      animation-delay: 1s;
    }

    @keyframes pulse-ring {
      0% {
        transform: scale(1);
        opacity: 0.7;
      }

      100% {
        transform: scale(1.8);
        opacity: 0;
      }
    }

    /* Spinner ring (thinking) */
    .spinner-ring {
      transform-box: fill-box;
      transform-origin: center;
      opacity: 0;
      stroke-dasharray: 60 200;
      stroke-dashoffset: 0;
      transition: opacity 0.3s;
    }

    .thinking .spinner-ring {
      opacity: 1;
      animation: spin-ring 1.5s linear infinite;
    }

    @keyframes spin-ring {
      to {
        stroke-dashoffset: -260;
      }
    }

    /* Mouth animations */
    #mouth-path {
      transition: d 0.2s ease;
    }

    #stage.talking #mouth-path {
      animation: mouth-talk 0.35s ease-in-out infinite alternate;
    }

    @keyframes mouth-talk {
      from {
        d: path("M 110 162 Q 140 168 170 162");
      }

      to {
        d: path("M 110 162 Q 140 185 170 162");
      }
    }

    /* ===== STATUS TEXT ===== */
    #status-text {
      margin-top: 10px;
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 1px;
      color: var(--accent);
      opacity: 0;
      transition: opacity 0.3s, color 0.3s;
      text-shadow: 0 0 10px var(--accent);
      min-height: 20px;
      text-align: center;
    }

    #status-text.visible {
      opacity: 1;
    }

    /* ===== DOTS (thinking) ===== */
    #dots {
      display: flex;
      gap: 6px;
      margin-top: 4px;
      opacity: 0;
      transition: opacity 0.3s;
    }

    #dots.visible {
      opacity: 1;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--purple);
      animation: dot-bounce 0.8s ease-in-out infinite;
    }

    .dot:nth-child(2) {
      animation-delay: 0.15s;
    }

    .dot:nth-child(3) {
      animation-delay: 0.30s;
    }

    @keyframes dot-bounce {

      0%,
      100% {
        transform: translateY(0);
      }

      50% {
        transform: translateY(-6px);
      }
    }

    /* ===== AUDIO WAVES (talking) ===== */
    #audio-wave {
      display: flex;
      gap: 3px;
      align-items: flex-end;
      margin-top: 6px;
      opacity: 0;
      transition: opacity 0.3s;
      height: 16px;
    }

    #audio-wave.visible {
      opacity: 1;
    }

    .wave-bar {
      width: 4px;
      border-radius: 2px;
      background: var(--gold);
      animation: wave-bar 0.6s ease-in-out infinite alternate;
    }

    .wave-bar:nth-child(1) {
      height: 4px;
      animation-delay: 0.0s;
    }

    .wave-bar:nth-child(2) {
      height: 10px;
      animation-delay: 0.1s;
    }

    .wave-bar:nth-child(3) {
      height: 14px;
      animation-delay: 0.2s;
    }

    .wave-bar:nth-child(4) {
      height: 8px;
      animation-delay: 0.3s;
    }

    .wave-bar:nth-child(5) {
      height: 12px;
      animation-delay: 0.4s;
    }

    .wave-bar:nth-child(6) {
      height: 6px;
      animation-delay: 0.5s;
    }

    .wave-bar:nth-child(7) {
      height: 10px;
      animation-delay: 0.15s;
    }

    @keyframes wave-bar {
      from {
        transform: scaleY(0.4);
      }

      to {
        transform: scaleY(1.2);
      }
    }

    /* ===== ZZZ (sleeping) ===== */
    #zzz-container {
      position: absolute;
      top: 30px;
      right: 40px;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.5s;
    }

    #zzz-container.visible {
      opacity: 1;
    }

    .zzz-letter {
      font-size: 18px;
      font-weight: 900;
      color: var(--purple);
      position: absolute;
      animation: zzz-float 2.5s ease-in-out infinite;
      opacity: 0;
      text-shadow: 0 0 8px var(--purple);
    }

    .zzz-letter:nth-child(1) {
      font-size: 12px;
      bottom: 0;
      right: 0;
      animation-delay: 0s;
    }

    .zzz-letter:nth-child(2) {
      font-size: 16px;
      bottom: 15px;
      right: -8px;
      animation-delay: 0.8s;
    }

    .zzz-letter:nth-child(3) {
      font-size: 20px;
      bottom: 35px;
      right: -18px;
      animation-delay: 1.6s;
    }

    @keyframes zzz-float {
      0% {
        transform: translate(0, 0) rotate(-15deg);
        opacity: 0;
      }

      20% {
        opacity: 1;
      }

      80% {
        opacity: 0.6;
      }

      100% {
        transform: translate(-10px, -30px) rotate(10deg);
        opacity: 0;
      }
    }

    /* ===== FLASHCARD OVERLAY ===== */
    #flashcard-overlay {
      position: fixed;
      inset: 0;
      background: #f8f9fa;
      z-index: 100;
      display: none;
      flex-direction: column;
      align-items: center;
      justify-content: space-between;
      padding: 14px 20px 10px;
      color: #1a1a2e;
    }

    #flashcard-overlay.active {
      display: flex;
    }

    #fc-emoji {
      font-size: 80px;
      line-height: 1;
      text-align: center;
      flex: 0 0 auto;
    }

    #fc-word {
      font-size: 48px;
      font-weight: 900;
      color: #1a1a2e;
      line-height: 1.1;
      text-align: center;
    }

    #fc-phonetic {
      font-size: 18px;
      color: #555;
      margin-top: 2px;
    }

    #fc-meaning {
      font-size: 20px;
      font-weight: 700;
      color: #0066cc;
      margin-top: 4px;
    }

    #fc-progress-wrap {
      width: 100%;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
    }

    #fc-bar-bg {
      flex: 1;
      height: 6px;
      background: #ddd;
      border-radius: 3px;
      overflow: hidden;
    }

    #fc-bar {
      height: 100%;
      background: linear-gradient(90deg, #00d4ff, #0066cc);
      border-radius: 3px;
      transition: width 0.4s ease;
    }

    #fc-count {
      font-size: 13px;
      color: #777;
      white-space: nowrap;
    }

    #fc-say-btn {
      margin-top: 6px;
      padding: 5px 14px;
      border: 2px solid #0066cc;
      border-radius: 20px;
      background: transparent;
      color: #0066cc;
      font-family: 'Nunito', sans-serif;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s, color 0.2s;
    }

    #fc-say-btn:hover {
      background: #0066cc;
      color: #fff;
    }

    /* ===== REWARD ===== */
    #reward-overlay {
      position: fixed;
      inset: 0;
      z-index: 200;
      pointer-events: none;
      display: none;
    }

    #reward-overlay.active {
      display: block;
    }

    .confetti-piece {
      position: absolute;
      width: 8px;
      height: 8px;
      border-radius: 2px;
      animation: confetti-fall 1.5s ease-in forwards;
    }

    @keyframes confetti-fall {
      0% {
        transform: translateY(-20px) rotate(0deg);
        opacity: 1;
      }

      100% {
        transform: translateY(340px) rotate(720deg);
        opacity: 0;
      }
    }

    #reward-text {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      font-size: 32px;
      font-weight: 900;
      color: var(--gold);
      text-shadow: 0 0 20px var(--gold), 2px 2px 0 #a00;
      animation: reward-pop 1.8s ease-out forwards;
      white-space: nowrap;
    }

    @keyframes reward-pop {
      0% {
        transform: translate(-50%, -50%) scale(0);
        opacity: 0;
      }

      30% {
        transform: translate(-50%, -50%) scale(1.3);
        opacity: 1;
      }

      70% {
        transform: translate(-50%, -50%) scale(1);
        opacity: 1;
      }

      100% {
        transform: translate(-50%, -80%) scale(0.8);
        opacity: 0;
      }
    }

    #mini-bi {
      position: absolute;
      bottom: 60px;
      right: 20px;
      font-size: 36px;
      animation: mini-bi-bounce 1.8s ease-out forwards;
      opacity: 0;
    }

    @keyframes mini-bi-bounce {
      0% {
        transform: translateY(20px) scale(0);
        opacity: 0;
      }

      20% {
        transform: translateY(0) scale(1.2);
        opacity: 1;
      }

      50% {
        transform: translateY(-8px) scale(1);
        opacity: 1;
      }

      70% {
        transform: translateY(0) scale(1);
        opacity: 1;
      }

      100% {
        transform: translateY(-20px) scale(0.8);
        opacity: 0;
      }
    }

    /* ===== DEMO CONTROLS ===== */
    #demo-bar {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: rgba(0, 0, 0, 0.85);
      padding: 5px 8px;
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      align-items: center;
      z-index: 300;
      opacity: 0;
      transform: translateY(100%);
      transition: opacity 0.3s, transform 0.3s;
    }

    #demo-bar.visible {
      opacity: 1;
      transform: translateY(0);
    }

    .demo-btn {
      padding: 3px 8px;
      border: 1px solid var(--cyan);
      border-radius: 10px;
      background: transparent;
      color: var(--cyan);
      font-family: 'Nunito', sans-serif;
      font-size: 10px;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.15s, color 0.15s;
    }

    .demo-btn:hover {
      background: var(--cyan);
      color: #000;
    }

    .demo-btn.gold {
      border-color: var(--gold);
      color: var(--gold);
    }

    .demo-btn.gold:hover {
      background: var(--gold);
      color: #000;
    }

    .demo-btn.green {
      border-color: var(--green);
      color: var(--green);
    }

    .demo-btn.green:hover {
      background: var(--green);
      color: #000;
    }

    #hint-label {
      font-size: 9px;
      color: #666;
      margin-left: auto;
    }

    /* ── Battery ── */
    #battery {
      position: fixed;
      bottom: 38px;
      right: 8px;
      font-size: 11px;
      font-weight: 700;
      color: #00d4ff;
      z-index: 10;
      display: none;
      text-shadow: 0 0 6px currentColor;
    }

    #battery.warn {
      color: #ffd700;
    }

    #battery.low {
      color: #ff4444;
      animation: bat-blink 1s step-end infinite;
    }

    @keyframes bat-blink {
      50% {
        opacity: 0;
      }
    }

    /* ── Story bubble ── */
    #story-bubble {
      position: absolute;
      top: 18px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      border-radius: 20px;
      padding: 8px 14px;
      max-width: 420px;
      font-size: 13px;
      color: #f0e8d0;
      text-align: center;
      opacity: 0;
      transition: opacity 0.4s;
      backdrop-filter: blur(4px);
      pointer-events: none;
      line-height: 1.4;
    }

    #story-bubble.visible {
      opacity: 1;
    }

    /* ── Game HUD ── */
    #game-hud {
      position: absolute;
      top: 10px;
      display: flex;
      gap: 14px;
      opacity: 0;
      transition: opacity 0.3s;
      pointer-events: none;
    }

    #game-hud.visible {
      opacity: 1;
    }

    #game-score-el,
    #game-timer-el {
      background: rgba(0, 0, 0, 0.5);
      border-radius: 20px;
      padding: 4px 12px;
      font-size: 14px;
      font-weight: 800;
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* ── Music notes ── */
    .music-note {
      position: absolute;
      font-size: 18px;
      pointer-events: none;
      animation: note-float 2s ease-out forwards;
    }

    @keyframes note-float {
      0% {
        transform: translate(0, 0) rotate(0deg) scale(1);
        opacity: 1;
      }

      100% {
        transform: translate(var(--nx, 20px), -60px) rotate(30deg) scale(0.5);
        opacity: 0;
      }
    }

    /* ── Warm story overlay ── */
    #story-warm-overlay {
      position: fixed;
      inset: 0;
      background: rgba(255, 180, 60, 0.06);
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.8s;
      z-index: 0;
    }

    #story-warm-overlay.visible {
      opacity: 1;
    }

    /* ── Holiday overlay ── */
    #holiday-overlay {
      position: fixed;
      inset: 0;
      z-index: 50;
      pointer-events: none;
      overflow: hidden;
    }

    .snow-flake {
      position: absolute;
      top: -10px;
      color: white;
      font-size: 14px;
      pointer-events: none;
      animation: snow-fall linear infinite;
      opacity: 0.7;
    }

    @keyframes snow-fall {
      to {
        transform: translateY(340px) rotate(360deg);
        opacity: 0;
      }
    }

    .heart-float {
      position: absolute;
      font-size: 20px;
      pointer-events: none;
      animation: heart-rise 3s ease-out forwards;
      opacity: 0;
    }

    @keyframes heart-rise {
      0% {
        transform: translateY(0) scale(0.8);
        opacity: 0;
      }

      20% {
        opacity: 1;
      }

      100% {
        transform: translateY(-300px) scale(1.2);
        opacity: 0;
      }
    }

    .balloon {
      position: absolute;
      font-size: 28px;
      pointer-events: none;
      animation: balloon-rise linear infinite;
    }

    @keyframes balloon-rise {
      from {
        transform: translateY(340px);
        opacity: 1;
      }

      to {
        transform: translateY(-30px);
        opacity: 0;
      }
    }

    .holiday-msg {
      position: fixed;
      top: 14px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(0, 0, 0, 0.65);
      color: white;
      padding: 8px 18px;
      border-radius: 20px;
      font-size: 15px;
      font-weight: 800;
      white-space: nowrap;
      z-index: 55;
      animation: msg-in 0.5s ease;
      cursor: pointer;
    }

    @keyframes msg-in {
      from {
        transform: translateX(-50%) scale(0.5);
        opacity: 0;
      }

      to {
        transform: translateX(-50%) scale(1);
        opacity: 1;
      }
    }

    /* ── Pronunciation result ── */
    #pronun-result {
      position: absolute;
      bottom: 210px;
      left: 50%;
      transform: translateX(-50%);
      padding: 10px 20px;
      border-radius: 20px;
      font-size: 15px;
      font-weight: 800;
      white-space: nowrap;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s;
      z-index: 110;
    }

    #pronun-result.visible {
      opacity: 1;
    }

    #pronun-result.correct {
      background: #22c55e;
      color: white;
    }

    #pronun-result.close {
      background: #f59e0b;
      color: white;
    }

    #pronun-result.wrong {
      background: #ef4444;
      color: white;
    }

    /* ── Streak in flashcard ── */
    #fc-streak {
      position: absolute;
      top: 10px;
      right: 12px;
      font-size: 16px;
      font-weight: 900;
      color: #ef4444;
      background: rgba(255, 255, 255, 0.9);
      border-radius: 14px;
      padding: 3px 10px;
      display: none;
    }

    #fc-subject {
      position: absolute;
      top: 10px;
      left: 12px;
      font-size: 20px;
      background: rgba(255, 255, 255, 0.9);
      border-radius: 10px;
      padding: 3px 8px;
    }
  </style>
</head>

<body>

  <!-- Particles background -->
  <canvas id="particles"></canvas>

  <!-- Main stage -->
  <div id="stage">

    <!-- ZZZ sleeping indicator -->
    <div id="zzz-container">
      <span class="zzz-letter">Z</span>
      <span class="zzz-letter">Z</span>
      <span class="zzz-letter">Z</span>
    </div>

    <!-- Robot face SVG -->
    <div id="face-wrap">
      <svg id="robot-face" viewBox="0 0 280 280" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <!-- Eye glow filter -->
          <filter id="eye-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <!-- Soft glow for accent -->
          <filter id="soft-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <!-- Face gradient -->
          <radialGradient id="face-grad" cx="50%" cy="45%" r="50%">
            <stop offset="0%" stop-color="#1a2540" />
            <stop offset="100%" stop-color="#0d1225" />
          </radialGradient>
          <!-- Eye iris gradient -->
          <radialGradient id="iris-grad" cx="40%" cy="35%" r="60%">
            <stop offset="0%" stop-color="#60f0ff" />
            <stop offset="60%" stop-color="#00d4ff" />
            <stop offset="100%" stop-color="#0088cc" />
          </radialGradient>
        </defs>

        <!-- ── Face base ── -->
        <ellipse cx="140" cy="145" rx="110" ry="115" fill="url(#face-grad)" stroke="#1e3050" stroke-width="2" />

        <!-- ── Ear panels ── -->
        <rect x="18" y="105" width="20" height="50" rx="5" fill="#0d1225" stroke="#1e3050" stroke-width="1.5" />
        <rect x="242" y="105" width="20" height="50" rx="5" fill="#0d1225" stroke="#1e3050" stroke-width="1.5" />
        <!-- Ear details -->
        <rect x="22" y="113" width="12" height="8" rx="2" fill="#00d4ff" opacity="0.4" />
        <rect x="22" y="125" width="12" height="4" rx="2" fill="#00d4ff" opacity="0.3" />
        <rect x="22" y="133" width="12" height="8" rx="2" fill="#00d4ff" opacity="0.4" />
        <rect x="246" y="113" width="12" height="8" rx="2" fill="#00d4ff" opacity="0.4" />
        <rect x="246" y="125" width="12" height="4" rx="2" fill="#00d4ff" opacity="0.3" />
        <rect x="246" y="133" width="12" height="8" rx="2" fill="#00d4ff" opacity="0.4" />

        <!-- ── Head top antenna ── -->
        <rect x="135" y="24" width="10" height="18" rx="5" fill="#1e3050" />
        <circle cx="140" cy="20" r="6" fill="#00d4ff" filter="url(#soft-glow)" opacity="0.9" />

        <!-- ── LEFT EYE group ── -->
        <g class="eye-group" id="left-eye-group">
          <!-- Pulse rings (listening) -->
          <circle class="pulse-ring" cx="100" cy="130" r="30" fill="none" stroke="#00ff88" stroke-width="1.5"
            opacity="0" />
          <circle class="pulse-ring" cx="100" cy="130" r="30" fill="none" stroke="#00ff88" stroke-width="1"
            opacity="0" />
          <circle class="pulse-ring" cx="100" cy="130" r="30" fill="none" stroke="#00ff88" stroke-width="0.5"
            opacity="0" />
          <!-- Spinner ring (thinking) -->
          <circle class="spinner-ring" cx="100" cy="130" r="32" fill="none" stroke="#c084fc" stroke-width="2.5"
            stroke-linecap="round" />
          <!-- Eye socket -->
          <circle cx="100" cy="130" r="28" fill="#060a14" stroke="#1e3050" stroke-width="1.5" />
          <!-- Iris -->
          <circle class="eye-circle" cx="100" cy="130" r="22" fill="url(#iris-grad)" filter="url(#eye-glow)" />
          <!-- Shine -->
          <ellipse cx="108" cy="122" rx="5" ry="3.5" fill="rgba(255,255,255,0.8)" transform="rotate(-20,108,122)" />
          <!-- Pupil -->
          <circle class="pupil" id="left-pupil" cx="100" cy="130" r="10" fill="#030711" />
          <!-- Happy arc eye (talking mode) -->
          <path class="eye-arc" d="M 76 130 Q 100 108 124 130" fill="#00d4ff" stroke="none" />
        </g>

        <!-- ── RIGHT EYE group ── -->
        <g class="eye-group" id="right-eye-group">
          <circle class="pulse-ring" cx="180" cy="130" r="30" fill="none" stroke="#00ff88" stroke-width="1.5"
            opacity="0" />
          <circle class="pulse-ring" cx="180" cy="130" r="30" fill="none" stroke="#00ff88" stroke-width="1"
            opacity="0" />
          <circle class="pulse-ring" cx="180" cy="130" r="30" fill="none" stroke="#00ff88" stroke-width="0.5"
            opacity="0" />
          <circle class="spinner-ring" cx="180" cy="130" r="32" fill="none" stroke="#c084fc" stroke-width="2.5"
            stroke-linecap="round" />
          <circle cx="180" cy="130" r="28" fill="#060a14" stroke="#1e3050" stroke-width="1.5" />
          <circle class="eye-circle" cx="180" cy="130" r="22" fill="url(#iris-grad)" filter="url(#eye-glow)" />
          <ellipse cx="188" cy="122" rx="5" ry="3.5" fill="rgba(255,255,255,0.8)" transform="rotate(-20,188,122)" />
          <circle class="pupil" id="right-pupil" cx="180" cy="130" r="10" fill="#030711" />
          <path class="eye-arc" d="M 156 130 Q 180 108 204 130" fill="#00d4ff" stroke="none" />
        </g>

        <!-- ── MOUTH ── -->
        <path id="mouth-path" d="M 110 167 Q 140 180 170 167" fill="none" stroke="#00d4ff" stroke-width="3.5"
          stroke-linecap="round" />

        <!-- ── Cheek blush ── -->
        <ellipse cx="72" cy="160" rx="16" ry="9" fill="#ff6b9d" opacity="0.18" />
        <ellipse cx="208" cy="160" rx="16" ry="9" fill="#ff6b9d" opacity="0.18" />

        <!-- ── Chin panel ── -->
        <rect x="115" y="215" width="50" height="14" rx="5" fill="#0d1225" stroke="#1e3050" stroke-width="1" />
        <circle cx="130" cy="222" r="3" fill="#00d4ff" opacity="0.5" />
        <circle cx="140" cy="222" r="3" fill="#1e3050" />
        <circle cx="150" cy="222" r="3" fill="#00d4ff" opacity="0.5" />
      </svg>
    </div>

    <!-- Status label -->
    <div id="status-text"></div>

    <!-- Thinking dots -->
    <div id="dots">
      <div class="dot"></div>
      <div class="dot"></div>
      <div class="dot"></div>
    </div>

    <!-- Audio wave bars -->
    <div id="audio-wave">
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
      <div class="wave-bar"></div>
    </div>

  </div><!-- /stage -->

  <!-- Battery indicator -->
  <div id="battery"></div>

  <!-- Story warm tint -->
  <div id="story-warm-overlay"></div>

  <!-- Holiday overlay -->
  <div id="holiday-overlay"></div>

  <!-- Game HUD -->
  <div id="game-hud">
    <div id="game-score-el">⭐ 0</div>
    <div id="game-timer-el" style="display:none;">⏱ 30s</div>
  </div>

  <!-- Story text bubble -->
  <div id="story-bubble"></div>

  <!-- Pronunciation result -->
  <div id="pronun-result"></div>

  <!-- Flashcard overlay -->
  <div id="flashcard-overlay">
    <div id="fc-subject">📚</div>
    <div id="fc-streak">🔥 0</div>
    <div id="fc-flag" style="font-size:22px; margin-bottom:2px;">🇺🇸</div>
    <div id="fc-emoji">🐱</div>
    <div id="fc-word">CAT</div>
    <div id="fc-phonetic">/kæt/</div>
    <div id="fc-meaning">Con mèo</div>
    <div id="fc-progress-wrap">
      <div id="fc-bar-bg">
        <div id="fc-bar" style="width:30%"></div>
      </div>
      <div id="fc-count">3/10</div>
    </div>
    <button id="fc-say-btn">🔊 Nói lại</button>
  </div>

  <!-- Reward overlay -->
  <div id="reward-overlay">
    <div id="reward-text">Giỏi lắm! +⭐</div>
    <div id="mini-bi">😄</div>
  </div>

  <!-- Demo control bar -->
  <div id="demo-bar">
    <button class="demo-btn" onclick="RobotDisplay.setMode('idle')">IDLE</button>
    <button class="demo-btn green" onclick="RobotDisplay.setMode('listening')">LISTEN</button>
    <button class="demo-btn" onclick="RobotDisplay.setMode('thinking')"
      style="border-color:#c084fc;color:#c084fc">THINK</button>
    <button class="demo-btn gold" onclick="RobotDisplay.setMode('talking')">TALK</button>
    <button class="demo-btn" onclick="RobotDisplay.setMode('sleeping')"
      style="border-color:#888;color:#888">SLEEP</button>
    <span style="color:#333;font-size:10px">|</span>
    <button class="demo-btn gold"
      onclick="RobotDisplay.showFlashcard({emoji:'🐱',word:'CAT',phonetic:'/kæt/',meaning:'Con mèo',current:3,total:10})">FC</button>
    <button class="demo-btn gold" onclick="RobotDisplay.showReward()">⭐</button>
    <span style="color:#333;font-size:10px">|</span>
    <button class="demo-btn" onclick="RobotDisplay.setEmotion('happy')"
      style="border-color:#ffd700;color:#ffd700">😊</button>
    <button class="demo-btn" onclick="RobotDisplay.setEmotion('sad')"
      style="border-color:#60a0ff;color:#60a0ff">😢</button>
    <button class="demo-btn" onclick="RobotDisplay.setEmotion('excited')"
      style="border-color:#ff6bff;color:#ff6bff">🎉</button>
    <button class="demo-btn" onclick="RobotDisplay.setEmotion('angry')"
      style="border-color:#ff4444;color:#ff4444">😠</button>
    <button class="demo-btn" onclick="RobotDisplay.setEmotion('surprised')"
      style="border-color:#ffaa00;color:#ffaa00">😲</button>
    <span style="color:#333;font-size:10px">|</span>
    <button class="demo-btn gold" onclick="RobotDisplay.setMode('music')">🎵</button>
    <button class="demo-btn" onclick="RobotDisplay.setMode('storytelling')"
      style="border-color:#f0c060;color:#f0c060">📖</button>
    <button class="demo-btn green" onclick="RobotDisplay.setMode('game')">🎮</button>
    <button class="demo-btn" onclick="RobotDisplay.triggerIdle('yawn')" style="border-color:#aaa;color:#aaa">😪</button>
    <button class="demo-btn" onclick="RobotDisplay.triggerIdle('stretch')"
      style="border-color:#aaa;color:#aaa">🙆</button>
    <button class="demo-btn" onclick="RobotDisplay.triggerHoliday('christmas')"
      style="border-color:#ff6666;color:#ff6666">🎄</button>
    <button class="demo-btn" onclick="RobotDisplay.setBattery(25)"
      style="border-color:#ff4444;color:#ff4444">🔋</button>
    <span id="hint-label">SPACE / hover</span>
  </div>

  <script>
    /* ══════════════════════════════════════════════
       ROBOT DISPLAY — Core Engine
       ══════════════════════════════════════════════ */

    (function () {
      'use strict';

      // ── State ──
      let currentMode = 'idle';
      let blinkTimer, lookTimer, idleActTimer;
      let sleepTimeout; // Keep for user compatibility if used externally

      // ── Intervals and Timeouts ──
      let _musicBounceTimer = null;
      let _noteTimer = null;
      let _gameTimerInterval = null;
      let _fidgetInterval = null;
      let _faceTimeouts = [];

      function registerFaceTimeout(fn, delay) {
        const t = setTimeout(fn, delay);
        _faceTimeouts.push(t);
        return t;
      }

      // ── DOM refs ──
      const stage = document.getElementById('stage');
      const faceWrap = document.getElementById('face-wrap');
      const leftEye = document.getElementById('left-eye-group');
      const rightEye = document.getElementById('right-eye-group');
      const leftPupil = document.getElementById('left-pupil');
      const rightPupil = document.getElementById('right-pupil');
      const mouthPath = document.getElementById('mouth-path');
      const statusText = document.getElementById('status-text');
      const dotsEl = document.getElementById('dots');
      const waveEl = document.getElementById('audio-wave');
      const zzzEl = document.getElementById('zzz-container');
      const fcOverlay = document.getElementById('flashcard-overlay');
      const rewardEl = document.getElementById('reward-overlay');
      const demoBar = document.getElementById('demo-bar');

      // ── Particle canvas ──
      const canvas = document.getElementById('particles');
      const ctx = canvas.getContext('2d');
      canvas.width = 480; canvas.height = 320;
      const PARTICLES = [];
      for (let i = 0; i < 35; i++) spawnParticle(true);

      function spawnParticle(init) {
        PARTICLES.push({
          x: Math.random() * 480,
          y: init ? Math.random() * 320 : 320 + 5,
          size: Math.random() * 1.8 + 0.4,
          speed: Math.random() * 0.4 + 0.15,
          dx: (Math.random() - 0.5) * 0.3,
          alpha: Math.random() * 0.5 + 0.1,
        });
      }

      function drawParticles() {
        ctx.clearRect(0, 0, 480, 320);
        // Only draw if not in flashcard mode
        if (fcOverlay.classList.contains('active')) return;
        for (let i = PARTICLES.length - 1; i >= 0; i--) {
          const p = PARTICLES[i];
          p.y -= p.speed;
          p.x += p.dx;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(0,212,255,${p.alpha})`;
          ctx.fill();
          if (p.y < -5) { PARTICLES.splice(i, 1); spawnParticle(false); }
        }
        requestAnimationFrame(drawParticles);
      }
      drawParticles();

      // ── Eye blink ──
      function scheduleBlink() {
        clearTimeout(blinkTimer);
        const delay = 2800 + Math.random() * 1800;
        blinkTimer = setTimeout(() => {
          if (currentMode === 'sleeping') { scheduleBlink(); return; }
          [leftEye, rightEye].forEach(g => {
            g.classList.add('blink');
            setTimeout(() => g.classList.remove('blink'), 200);
          });
          scheduleBlink();
        }, delay);
      }

      // ── Pupil wander ──
      function movePupils(dx, dy) {
        const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
        const lx = clamp(100 + dx, 88, 112);
        const ly = clamp(130 + dy, 118, 142);
        const rx = clamp(180 + dx, 168, 192);
        const ry = clamp(130 + dy, 118, 142);
        leftPupil.setAttribute('cx', lx);
        leftPupil.setAttribute('cy', ly);
        rightPupil.setAttribute('cx', rx);
        rightPupil.setAttribute('cy', ry);
      }

      function scheduleLook() {
        clearTimeout(lookTimer);
        const delay = 1800 + Math.random() * 1600;
        lookTimer = setTimeout(() => {
          if (currentMode === 'sleeping' || currentMode === 'thinking') { scheduleLook(); return; }
          const dx = (Math.random() - 0.5) * 14;
          const dy = (Math.random() - 0.5) * 10;
          movePupils(dx, dy);
          scheduleLook();
        }, delay);
      }

      // ── Accent color helper ──
      function setAccent(color) {
        document.documentElement.style.setProperty('--accent', color);
      }

      // Extra cleanup called by clearAll
      function clearAllExtras() {
        if (_musicBounceTimer) { clearInterval(_musicBounceTimer); _musicBounceTimer = null; }
        if (_noteTimer) { clearInterval(_noteTimer); _noteTimer = null; }
        if (_gameTimerInterval) { clearInterval(_gameTimerInterval); _gameTimerInterval = null; }
        if (_fidgetInterval) { clearInterval(_fidgetInterval); _fidgetInterval = null; }

        _faceTimeouts.forEach(clearTimeout);
        _faceTimeouts = [];

        [leftEye, rightEye].forEach(g => { g.style.transform = ''; g.style.transition = ''; });
        faceWrap.style.transform = '';
        document.getElementById('story-warm-overlay').classList.remove('visible');
        document.getElementById('game-hud').classList.remove('visible');
        document.getElementById('story-bubble').classList.remove('visible');
        stage.style.filter = '';
        leftPupil.setAttribute('r', '10');
        rightPupil.setAttribute('r', '10');
      }

      // ── Clear all active visual states ──
      function clearAll() {
        clearAllExtras?.();
        stage.className = '';
        faceWrap.classList.remove('breathe');
        [leftEye, rightEye].forEach(g => {
          g.classList.remove('listening', 'thinking', 'happy');
        });
        mouthPath.style.animation = '';
        statusText.classList.remove('visible');
        dotsEl.classList.remove('visible');
        waveEl.classList.remove('visible');
        zzzEl.classList.remove('visible');
        // Reset mouth to default smile
        mouthPath.setAttribute('d', 'M 110 167 Q 140 180 170 167');
        // Reset pupils to center
        movePupils(0, 0);
      }

      // ══════════════════════════════════════
      // MODE IMPLEMENTATIONS
      // ══════════════════════════════════════

      const MODES = {

        idle() {
          clearAll();
          setAccent('#00d4ff');
          // Default smile stays, pupils wander naturally
        },

        listening() {
          clearAll();
          setAccent('#00ff88');
          [leftEye, rightEye].forEach(g => g.classList.add('listening'));
          movePupils(0, -3); // slightly more open
          statusText.style.color = 'var(--green)';
          statusText.textContent = 'Bi đang nghe...';
          statusText.classList.add('visible');
        },

        thinking() {
          clearAll();
          setAccent('#c084fc');
          [leftEye, rightEye].forEach(g => g.classList.add('thinking'));
          movePupils(0, -8); // pupils up = thinking
          dotsEl.classList.add('visible');
          // dot colors
          document.querySelectorAll('.dot').forEach(d => d.style.background = '#c084fc');
        },

        talking() {
          clearAll();
          setAccent('#ffd700');
          [leftEye, rightEye].forEach(g => g.classList.add('happy'));
          waveEl.classList.add('visible');
          // Mouth animate via CSS class on stage
          stage.classList.add('talking');
        },

        sleeping() {
          clearAll();
          setAccent('#9966cc');
          stage.classList.add('sleeping');
          faceWrap.classList.add('breathe');
          zzzEl.classList.add('visible');
          movePupils(0, 0); // Fix pupil position when sleeping
          // Close eyes: scaleY very small
          [leftEye, rightEye].forEach(g => {
            g.style.transform = 'scaleY(0.08)';
            g.style.transition = 'transform 0.8s ease';
          });
          // Set droopy mouth
          mouthPath.setAttribute('d', 'M 115 168 Q 140 172 165 168');
        },
      };

      // Instant eye restore (called when setMode() overrides sleep without animation)
      function wakeUpInstant() {
        [leftEye, rightEye].forEach(g => { g.style.transform = ''; });
      }

      function setMode(mode) {
        if (!MODES[mode]) { console.warn('Unknown mode:', mode); return; }
        if (currentMode === 'sleeping') wakeUpInstant();
        currentMode = mode;
        MODES[mode]();
      }

      // ══════════════════════════════════════
      // EMOTION OVERRIDES
      // ══════════════════════════════════════

      const EMOTIONS = {
        happy() {
          setMode('talking');
          registerFaceTimeout(() => setMode('idle'), 2000);
        },
        sad() {
          clearAll();
          setAccent('#6090ff');
          // Pupils down
          movePupils(0, 8);
          // Sad mouth (curve down)
          mouthPath.setAttribute('d', 'M 110 175 Q 140 163 170 175');
          statusText.style.color = '#6090ff';
          statusText.textContent = '...';
          statusText.classList.add('visible');
        },
        excited() {
          clearAll();
          setAccent('#ff6bff');
          [leftEye, rightEye].forEach(g => g.classList.add('happy'));
          // Wide mouth
          mouthPath.setAttribute('d', 'M 105 164 Q 140 190 175 164');
          // Extra glow
          stage.style.filter = 'brightness(1.1)';
          registerFaceTimeout(() => { stage.style.filter = ''; }, 2500);
        },
        angry() {
          clearAll();
          setAccent('#ff4444');
          movePupils(0, 3);
          // Frown
          mouthPath.setAttribute('d', 'M 110 178 Q 140 165 170 178');
          // Squint: compress eyes slightly
          [leftEye, rightEye].forEach(g => {
            g.style.transform = 'scaleY(0.7)';
            g.style.transition = 'transform 0.3s ease';
          });
        },
        surprised() {
          clearAll();
          setAccent('#ffaa00');
          // Big pupils
          leftPupil.setAttribute('r', '13');
          rightPupil.setAttribute('r', '13');
          // O mouth
          mouthPath.setAttribute('d', 'M 128 163 Q 140 180 152 163');
          registerFaceTimeout(() => {
            leftPupil.setAttribute('r', '10');
            rightPupil.setAttribute('r', '10');
          }, 1500);
        },
      };

      // ══════════════════════════════════════
      // FLASHCARD
      // ══════════════════════════════════════

      const LANG_FLAGS = { en: '🇺🇸', ja: '🇯🇵', ko: '🇰🇷', zh: '🇨🇳', fr: '🇫🇷' };
      const LANG_COLORS = { en: '#0066cc', ja: '#dc143c', ko: '#8b008b', zh: '#cc4400', fr: '#003399' };
      const SUBJ_ICONS_MAP = { english: '📚', math: '🔢', science: '🔬', history: '🏛️', geography: '🌍' };
      let _streak = 0;

      function showFlashcard(data) {
        document.getElementById('fc-emoji').textContent = data.emoji || '❓';
        document.getElementById('fc-word').textContent = data.word || '';
        document.getElementById('fc-phonetic').textContent = data.phonetic || '';
        document.getElementById('fc-meaning').textContent = data.meaning || '';
        const pct = data.total ? (data.current / data.total * 100) : 0;
        document.getElementById('fc-bar').style.width = pct + '%';
        document.getElementById('fc-count').textContent = (data.current || 0) + '/' + (data.total || 0);

        // Enhancements
        const lang = data.language || 'en';
        document.getElementById('fc-flag').textContent = LANG_FLAGS[lang] || '🌐';

        const subj = data.subject || 'english';
        document.getElementById('fc-subject').textContent = SUBJ_ICONS_MAP[subj] || '📚';
        document.getElementById('fc-subject').style.display = 'block';

        const color = LANG_COLORS[lang] || '#0066cc';
        document.getElementById('fc-word').style.color = color;

        const streakEl = document.getElementById('fc-streak');
        if (_streak > 0) {
          streakEl.textContent = `🔥 ${_streak}`;
          streakEl.style.display = 'block';
        } else {
          streakEl.style.display = 'none';
        }

        fcOverlay.classList.add('active');
      }

      function hideFlashcard() {
        fcOverlay.classList.remove('active');
      }

      document.getElementById('fc-say-btn').onclick = () => {
        // Visual feedback only — actual TTS triggered externally
        const btn = document.getElementById('fc-say-btn');
        btn.textContent = '🔊 ...';
        setTimeout(() => { btn.textContent = '🔊 Nói lại'; }, 800);
      };

      // ══════════════════════════════════════
      // REWARD
      // ══════════════════════════════════════

      function showReward() {
        const overlay = rewardEl;
        // Remove old confetti
        overlay.querySelectorAll('.confetti-piece').forEach(e => e.remove());
        // Reset animations
        overlay.classList.remove('active');
        void overlay.offsetWidth;
        overlay.classList.add('active');

        // Spawn confetti
        const colors = ['#ffd700', '#ff6b9d', '#00d4ff', '#00ff88', '#ff6bff', '#ffaa00'];
        for (let i = 0; i < 50; i++) {
          const el = document.createElement('div');
          el.className = 'confetti-piece';
          const side = Math.random() < 0.5;
          el.style.cssText = `
        left: ${side ? Math.random() * 100 : 380 + Math.random() * 100}px;
        background: ${colors[Math.floor(Math.random() * colors.length)]};
        animation-duration: ${1.0 + Math.random() * 0.8}s;
        animation-delay: ${Math.random() * 0.4}s;
        border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
        width: ${4 + Math.random() * 8}px;
        height: ${4 + Math.random() * 8}px;
      `;
          overlay.appendChild(el);
        }
        setTimeout(() => overlay.classList.remove('active'), 2200);
      }

      // ══════════════════════════════════════
      // DEMO BAR — show/hide
      // ══════════════════════════════════════

      let demoVisible = false;
      function showDemo() { demoBar.classList.add('visible'); demoVisible = true; }
      function hideDemo() { demoBar.classList.remove('visible'); demoVisible = false; }

      document.addEventListener('keydown', e => {
        if (e.code === 'Space') { e.preventDefault(); demoVisible ? hideDemo() : showDemo(); }
      });
      demoBar.addEventListener('mouseenter', showDemo);

      // ══════════════════════════════════════
      // IDLE BEHAVIORS (Task 6.2)
      // ══════════════════════════════════════

      const IDLE_BEHAVIORS = {
        yawn() {
          // Close eyes slowly, open mouth wide, then return
          [leftEye, rightEye].forEach(g => {
            g.style.transform = 'scaleY(0.1)';
            g.style.transition = 'transform 0.5s ease';
          });
          mouthPath.setAttribute('d', 'M 115 160 Q 140 195 165 160');
          registerFaceTimeout(() => {
            [leftEye, rightEye].forEach(g => { g.style.transform = ''; });
            mouthPath.setAttribute('d', 'M 110 167 Q 140 180 170 167');
          }, 1200);
        },
        stretch() {
          faceWrap.style.transform = 'scale(1.1)';
          faceWrap.style.transition = 'transform 0.4s ease';
          registerFaceTimeout(() => {
            faceWrap.style.transform = 'scale(1)';
            registerFaceTimeout(() => { faceWrap.style.transform = ''; faceWrap.style.transition = ''; }, 400);
          }, 600);
        },
        look_clock() {
          movePupils(10, -9); // up-right (clock direction)
          registerFaceTimeout(() => movePupils(0, 0), 1500);
        },
        fidget() {
          let count = 0;
          if (_fidgetInterval) clearInterval(_fidgetInterval);
          _fidgetInterval = setInterval(() => {
            movePupils(0, count % 2 === 0 ? -8 : 8);
            count++;
            if (count >= 6) { clearInterval(_fidgetInterval); _fidgetInterval = null; movePupils(0, 0); }
          }, 280);
        },
      };

      function triggerIdleBehavior(name) {
        const fn = IDLE_BEHAVIORS[name];
        if (fn) fn();
      }

      function scheduleIdleAct() {
        clearTimeout(idleActTimer);
        const delay = 30000 + Math.random() * 30000;
        idleActTimer = setTimeout(() => {
          if (currentMode === 'idle') {
            const acts = Object.keys(IDLE_BEHAVIORS);
            triggerIdleBehavior(acts[Math.floor(Math.random() * acts.length)]);
          }
          scheduleIdleAct();
        }, delay);
      }

      // ══════════════════════════════════════
      // BATTERY (Task 6.2)
      // ══════════════════════════════════════

      const batteryEl = document.getElementById('battery');
      function setBatteryDisplay(pct) {
        if (pct == null) { batteryEl.style.display = 'none'; return; }
        pct = Math.max(0, Math.min(100, parseInt(pct)));
        const icon = pct > 70 ? '🔋' : pct > 20 ? '🪫' : '🔴';
        batteryEl.textContent = `${icon} ${pct}%`;
        batteryEl.className = pct > 50 ? '' : (pct > 20 ? 'warn' : 'low');
        batteryEl.style.display = 'block';
        if (pct < 20) setMode('sleeping'); // battery low → sleep
      }

      // ══════════════════════════════════════
      // WAKE-UP ANIMATION (Task 6.2)
      // ══════════════════════════════════════

      function wakeUpAnimation() {
        // Eyes open from scaleY(0.08) → 1 over 0.6s
        [leftEye, rightEye].forEach(g => {
          g.style.transition = 'transform 0.6s ease';
          g.style.transform = 'scaleY(1)';
          registerFaceTimeout(() => { g.style.transform = ''; g.style.transition = ''; }, 650);
        });
        // Quick stretch
        registerFaceTimeout(() => IDLE_BEHAVIORS.stretch(), 400);
      }

      // ══════════════════════════════════════
      // NEW MODES: music, storytelling, game
      // ══════════════════════════════════════

      let _bpm = 120;

      Object.assign(MODES, {
        music() {
          clearAll();
          setAccent('#ffd700');
          // Half-closed eyes (enjoying music)
          [leftEye, rightEye].forEach(g => {
            g.style.transform = 'scaleY(0.65)';
            g.style.transition = 'transform 0.3s ease';
          });
          // Bounce to BPM
          const interval = Math.round(60000 / _bpm);
          let up = true;
          _musicBounceTimer = setInterval(() => {
            faceWrap.style.transform = up ? 'translateY(-6px)' : 'translateY(2px)';
            faceWrap.style.transition = `transform ${interval * 0.4}ms ease`;
            up = !up;
          }, interval);
          // Spawn music notes
          _noteTimer = setInterval(() => spawnMusicNote(), 800);
        },

        storytelling() {
          clearAll();
          setAccent('#f0c060');
          document.getElementById('story-warm-overlay').classList.add('visible');
          // Dreamy eyes: look slightly up-left
          movePupils(-5, -6);
          mouthPath.setAttribute('d', 'M 112 167 Q 140 176 168 167');
        },

        game() {
          clearAll();
          setAccent('#00ff88');
          [leftEye, rightEye].forEach(g => g.classList.add('happy'));
          document.getElementById('game-hud').classList.add('visible');
          mouthPath.setAttribute('d', 'M 105 164 Q 140 188 175 164');
        },
      });

      function spawnMusicNote() {
        const notes = ['♪', '♫', '♬', '🎵'];
        const el = document.createElement('div');
        el.className = 'music-note';
        el.textContent = notes[Math.floor(Math.random() * notes.length)];
        el.style.cssText = `left:${80 + Math.random() * 320}px; top:${100 + Math.random() * 100}px;
      --nx:${(Math.random() - 0.5) * 60}px; color:var(--gold); z-index:10;`;
        stage.appendChild(el);
        setTimeout(() => el.remove(), 2000);
      }

      // ══════════════════════════════════════
      // PRONUNCIATION
      // ══════════════════════════════════════

      let _pronunTimer = null;
      function showPronunciationResult(score) {
        const el = document.getElementById('pronun-result');
        if (_pronunTimer) clearTimeout(_pronunTimer);
        el.className = 'pronun-result';
        if (score >= 80) {
          el.textContent = '✅ Phát âm chuẩn!';
          el.className = 'visible correct';
          _streak++;
          showReward();
        } else if (score >= 50) {
          el.textContent = '🟡 Gần đúng! Thử lại nhé';
          el.className = 'visible close';
          _streak = 0;
        } else {
          el.textContent = '❌ Bi nói lại nhé!';
          el.className = 'visible wrong';
          _streak = 0;
        }
        el.id = 'pronun-result';
        _pronunTimer = setTimeout(() => { el.className = ''; el.id = 'pronun-result'; }, 2500);
      }

      // ══════════════════════════════════════
      // HOLIDAY SYSTEM (Task 6.3)
      // ══════════════════════════════════════

      const holidayOverlay = document.getElementById('holiday-overlay');
      let _activeHoliday = null;
      let _holidayCleanup = null;

      const HOLIDAYS = {
        christmas: {
          check(m, d) { return m === 12 && d === 25; },
          activate() {
            // Snow + Santa hat hint
            const frag = document.createDocumentFragment();
            for (let i = 0; i < 25; i++) {
              const flake = document.createElement('div');
              flake.className = 'snow-flake';
              flake.textContent = ['❄', '❅', '❆'][Math.floor(Math.random() * 3)];
              flake.style.cssText = `left:${Math.random() * 480}px; animation-duration:${3 + Math.random() * 4}s; animation-delay:${Math.random() * 4}s; font-size:${10 + Math.random() * 10}px;`;
              frag.appendChild(flake);
            }
            holidayOverlay.appendChild(frag);
            showHolidayMsg('🎄 Giáng sinh vui vẻ! 🎅');
            setAccent('#ff6666');
          },
        },
        newyear: {
          check(m, d) { return m === 1 && d === 1; },
          activate() {
            showHolidayMsg('🎆 Chúc Mừng Năm Mới! 🎇');
            showReward();
            setAccent('#ffd700');
          },
        },
        valentine: {
          check(m, d) { return m === 2 && d === 14; },
          activate() {
            const frag = document.createDocumentFragment();
            for (let i = 0; i < 8; i++) {
              const heart = document.createElement('div');
              heart.className = 'heart-float';
              heart.textContent = '💝';
              heart.style.cssText = `left:${20 + Math.random() * 440}px; bottom:60px; animation-delay:${Math.random() * 4}s;`;
              frag.appendChild(heart);
            }
            holidayOverlay.appendChild(frag);
            showHolidayMsg('💕 Chúc mừng Valentine! 💕');
            setAccent('#ff6b9d');
          },
        },
        womensday: {
          check(m, d) { return m === 3 && d === 8; },
          activate() { showHolidayMsg('🌸 Chúc mừng ngày 8/3! 🌸'); setAccent('#ff6bff'); },
        },
        childrensday: {
          check(m, d) { return m === 6 && d === 1; },
          activate() {
            const frag = document.createDocumentFragment();
            ['🎈', '🎀', '🎉', '🎊'].forEach((e, i) => {
              const b = document.createElement('div');
              b.className = 'balloon';
              b.textContent = e;
              b.style.cssText = `left:${60 + i * 110}px; animation-duration:${4 + i}s; animation-delay:${i * 0.5}s;`;
              frag.appendChild(b);
            });
            holidayOverlay.appendChild(frag);
            showHolidayMsg('🎈 Chúc mừng Quốc tế Thiếu nhi! 🎈');
            setAccent('#00ff88');
          },
        },
        halloween: {
          check(m, d) { return m === 10 && d === 31; },
          activate() {
            showHolidayMsg('🎃 Happy Halloween! 👻');
            setAccent('#ff7700');
            stage.style.filter = 'brightness(0.7) hue-rotate(30deg)';
            setTimeout(() => { stage.style.filter = ''; }, 8000);
          },
        },
      };

      function showHolidayMsg(text) {
        const existing = document.querySelector('.holiday-msg');
        if (existing) existing.remove();
        const el = document.createElement('div');
        el.className = 'holiday-msg';
        el.textContent = text;
        el.addEventListener('click', () => el.remove());
        document.body.appendChild(el);
        setTimeout(() => { if (el.parentNode) el.remove(); }, 8000);
      }

      function clearHoliday() {
        holidayOverlay.innerHTML = '';
        document.querySelector('.holiday-msg')?.remove();
        if (_holidayCleanup) _holidayCleanup();
        _activeHoliday = null;
        _holidayCleanup = null;
      }

      function triggerHoliday(name) {
        clearHoliday();
        const h = HOLIDAYS[name];
        if (!h) return;
        _activeHoliday = name;
        h.activate();
      }

      function detectTodayHoliday() {
        const now = new Date();
        const m = now.getMonth() + 1;
        const d = now.getDate();
        for (const [name, h] of Object.entries(HOLIDAYS)) {
          if (h.check(m, d)) { triggerHoliday(name); return name; }
        }
        return null;
      }

      // ══════════════════════════════════════
      // PUBLIC API
      // ══════════════════════════════════════

      window.RobotDisplay = {
        setMode,
        getMode() { return currentMode; },
        showFlashcard,
        hideFlashcard,
        showReward,
        setEmotion(emotion) {
          const fn = EMOTIONS[emotion];
          if (!fn) { console.warn('Unknown emotion:', emotion); return; }
          fn();
        },
        setBattery(pct) { setBatteryDisplay(pct); },
        triggerIdle(name) { triggerIdleBehavior(name); },
        wakeUp() { wakeUpAnimation(); if (currentMode === 'sleeping') { setMode('idle'); } },
        setBPM(bpm) {
          _bpm = bpm;
          if (currentMode === 'music') { clearAll(); MODES.music(); }
        },
        updateStoryText(text) {
          const el = document.getElementById('story-bubble');
          el.textContent = text;
          el.classList.add('visible');
        },
        updateGameScore(score) { document.getElementById('game-score-el').textContent = `⭐ ${score}`; },
        updateTimer(seconds) {
          const el = document.getElementById('game-timer-el');
          el.style.display = 'block';
          el.textContent = `⏱ ${seconds}s`;
          if (_gameTimerInterval) clearInterval(_gameTimerInterval);
          let s = seconds;
          _gameTimerInterval = setInterval(() => {
            s--;
            el.textContent = `⏱ ${s}s`;
            if (s <= 0) { clearInterval(_gameTimerInterval); _gameTimerInterval = null; el.style.display = 'none'; }
          }, 1000);
        },
        updateStreak(count) {
          _streak = count;
          document.getElementById('fc-streak').textContent = `🔥 ${count}`;
          document.getElementById('fc-streak').style.display = count > 0 ? 'block' : 'none';
        },
        showPronunciationResult,
        triggerHoliday,
        getActiveHoliday() { return _activeHoliday; },
        triggerBirthday(name) {
          showHolidayMsg(`🎂 Chúc mừng sinh nhật ${name || ''}! 🎉`);
          showReward();
          setAccent('#ffd700');
        },
      };

      // ══════════════════════════════════════
      // BOOT
      // ══════════════════════════════════════

      scheduleBlink();
      scheduleLook();
      scheduleIdleAct();
      setMode('idle');
      detectTodayHoliday();

    })();
  </script>
</body>

</html>
```

