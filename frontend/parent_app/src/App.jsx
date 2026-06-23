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

      <Toast />
    </div>
  );
}
