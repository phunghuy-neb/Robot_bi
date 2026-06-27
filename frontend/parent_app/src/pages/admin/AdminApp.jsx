import { useState } from 'react';
import UsersAdminPage from './UsersAdminPage.jsx';
import ApiKeysPage from './ApiKeysPage.jsx';
import ExamsAdminPage from './ExamsAdminPage.jsx';
import YouTubeAdminPage from './YouTubeAdminPage.jsx';
import SafetyAdminPage from './SafetyAdminPage.jsx';
import ContentAdminPage from './ContentAdminPage.jsx';
import LogsAdminPage from './LogsAdminPage.jsx';
import StatsAdminPage from './StatsAdminPage.jsx';
import PersonaAdminPage from './PersonaAdminPage.jsx';
import Toast from '../../components/Toast.jsx';

// Khu vực Admin — hiển thị khi đăng nhập bằng tài khoản is_admin.
// Tất cả mục trong sidebar đang trỏ tới màn hình quản trị thật.
const SECTIONS = [
  { key: 'users',     label: 'Tài khoản',     icon: '👤' },
  { key: 'apikeys',   label: 'API key',       icon: '🔑' },
  { key: 'exams',     label: 'Đề thi',        icon: '📝' },
  { key: 'youtube',   label: 'Kênh YouTube',  icon: '📺' },
  { key: 'safety',    label: 'An toàn trẻ',   icon: '🛡️' },
  { key: 'persona',   label: 'Tính cách Bi',  icon: '🤖' },
  { key: 'content',   label: 'Nội dung',      icon: '🎬' },
  { key: 'logs',      label: 'Nhật ký',       icon: '📋' },
  { key: 'stats',     label: 'Thống kê',      icon: '📊' },
];

export default function AdminApp({ user, onLogout }) {
  const [section, setSection] = useState('users');
  const active = SECTIONS.find(s => s.key === section) || SECTIONS[0];

  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          🛠️ Robot Bi Admin
        </div>
        <nav className="admin-nav">
          {SECTIONS.map(s => (
            <button
              key={s.key}
              className={`admin-nav-item${section === s.key ? ' active' : ''}`}
              onClick={() => setSection(s.key)}
            >
              <span className="admin-nav-icon">{s.icon}</span>
              <span className="admin-nav-label">{s.label}</span>
            </button>
          ))}
        </nav>
        <div className="admin-sidebar-footer">
          <div className="admin-user">👋 {user?.username}</div>
          <button className="admin-logout" onClick={onLogout}>Đăng xuất</button>
        </div>
      </aside>

      <main className="admin-main">
        <h1 className="admin-page-title">
          {active.icon} {active.label}
        </h1>
        {section === 'users' && <UsersAdminPage currentUsername={user?.username} />}
        {section === 'apikeys' && <ApiKeysPage />}
        {section === 'exams' && <ExamsAdminPage />}
        {section === 'youtube' && <YouTubeAdminPage />}
        {section === 'safety' && <SafetyAdminPage />}
        {section === 'content' && <ContentAdminPage />}
        {section === 'logs' && <LogsAdminPage />}
        {section === 'stats' && <StatsAdminPage />}
        {section === 'persona' && <PersonaAdminPage />}
      </main>

      <Toast />
    </div>
  );
}
