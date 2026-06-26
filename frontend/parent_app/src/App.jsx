import { useState, useEffect, useCallback } from 'react';
import {
  checkExistingSession,
  connectWebSocket,
  disconnectWebSocket,
  logout,
  getChildProfiles,
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
import AdminApp from './pages/admin/AdminApp.jsx';
import HomePage from './pages/HomePage.jsx';
import MonitorPage from './pages/MonitorPage.jsx';
import LearningPage from './pages/LearningPage.jsx';
import LearningHubPage from './pages/LearningHubPage.jsx';
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
  const [childPickerOpen, setChildPickerOpen] = useState(false);
  const [childOptions, setChildOptions] = useState([]);
  const [childPickerState, setChildPickerState] = useState('idle');
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

  const loadChildOptions = useCallback(async () => {
    setChildPickerState('loading');
    const profiles = await getChildProfiles();
    setChildOptions(profiles || []);
    setChildPickerState('data');
  }, []);

  const handleSwitchChild = useCallback(() => {
    setChildPickerOpen(true);
    loadChildOptions();
  }, [loadChildOptions]);

  const chooseChild = useCallback((child) => {
    setActiveChild(child);
    setChildPickerOpen(false);
    showToast(`Đã chọn hồ sơ: ${child.name}`);
  }, []);

  const clearActiveChild = useCallback(() => {
    setActiveChild(null);
    setChildPickerOpen(false);
    showToast('Đã bỏ chọn hồ sơ trẻ');
  }, []);

  const openChildSettings = useCallback(() => {
    setChildPickerOpen(false);
    setSettingsOpen(true);
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

  // Tài khoản admin (is_admin trong .env) → giao diện Admin riêng.
  // Tài khoản thường → Parent App như cũ.
  if (user.isAdmin) {
    return <AdminApp user={user} onLogout={handleLogout} />;
  }

  const tabComponents = {
    home: <HomePage user={user} lastWsEvent={lastWsEvent} />,
    monitor: <MonitorPage lastWsEvent={lastWsEvent} />,
    learning: <LearningPage activeChild={activeChild} />,
    learninghub: <LearningHubPage />,
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

      {childPickerOpen && (
        <div className="child-picker-overlay" onClick={e => e.target === e.currentTarget && setChildPickerOpen(false)}>
          <div className="child-picker-panel">
            <div className="child-picker-head">
              <div>
                <div className="child-picker-title">Chọn hồ sơ trẻ</div>
                <div className="child-picker-sub">Áp dụng cho các màn học tập và theo dõi trong phiên này.</div>
              </div>
              <button className="settings-close" onClick={() => setChildPickerOpen(false)} title="Đóng">✕</button>
            </div>

            {childPickerState === 'loading' ? (
              <div className="child-picker-empty">Đang tải hồ sơ...</div>
            ) : childOptions.length === 0 ? (
              <div className="child-picker-empty">Chưa có hồ sơ trẻ.</div>
            ) : (
              <div className="child-picker-list">
                {childOptions.map(child => (
                  <button
                    key={child.id}
                    className={`child-picker-option${activeChild?.id === child.id ? ' active' : ''}`}
                    onClick={() => chooseChild(child)}
                  >
                    <span className="child-picker-avatar">{child.avatar || '👧'}</span>
                    <span>
                      <strong>{child.name}</strong>
                      <small>{[child.age ? `${child.age} tuổi` : '', child.grade].filter(Boolean).join(' · ') || 'Hồ sơ trẻ'}</small>
                    </span>
                  </button>
                ))}
              </div>
            )}

            <div className="child-picker-actions">
              {activeChild && (
                <button className="btn-sm secondary" onClick={clearActiveChild}>Bỏ chọn</button>
              )}
              <button className="btn-sm primary" onClick={openChildSettings}>Quản lý hồ sơ</button>
            </div>
          </div>
        </div>
      )}

      <Toast />
    </div>
  );
}
