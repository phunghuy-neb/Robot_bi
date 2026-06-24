import { useState } from 'react';
import UsersAdminPage from './UsersAdminPage.jsx';
import Toast from '../../components/Toast.jsx';

// Khu vực Admin — hiển thị khi đăng nhập bằng tài khoản is_admin.
// Mỗi mục tương ứng một phase; mục chưa làm hiện placeholder "Sắp có".
const SECTIONS = [
  { key: 'users',     label: 'Tài khoản',     icon: '👤', ready: true },
  { key: 'apikeys',   label: 'API key',       icon: '🔑', ready: false },
  { key: 'exams',     label: 'Đề thi',        icon: '📝', ready: false },
  { key: 'youtube',   label: 'Kênh YouTube',  icon: '📺', ready: false },
  { key: 'safety',    label: 'An toàn trẻ',   icon: '🛡️', ready: false },
  { key: 'content',   label: 'Nội dung',      icon: '🎬', ready: false },
  { key: 'logs',      label: 'Nhật ký',       icon: '📋', ready: false },
  { key: 'stats',     label: 'Thống kê',      icon: '📊', ready: false },
];

export default function AdminApp({ user, onLogout }) {
  const [section, setSection] = useState('users');
  const active = SECTIONS.find(s => s.key === section) || SECTIONS[0];

  return (
    <div style={{ display: 'flex', minHeight: '100dvh', background: 'var(--bg, #f5f6fa)' }}>
      {/* Sidebar */}
      <aside style={{
        width: 220, flexShrink: 0, background: '#1e293b', color: '#e2e8f0',
        display: 'flex', flexDirection: 'column', padding: '16px 10px',
      }}>
        <div style={{ fontWeight: 800, fontSize: 18, padding: '6px 10px 16px' }}>
          🛠️ Robot Bi Admin
        </div>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
          {SECTIONS.map(s => (
            <button key={s.key} onClick={() => setSection(s.key)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
                borderRadius: 10, border: 'none', cursor: 'pointer', textAlign: 'left',
                fontSize: 14, fontWeight: 600,
                background: section === s.key ? '#334155' : 'transparent',
                color: section === s.key ? '#fff' : '#cbd5e1',
              }}>
              <span style={{ fontSize: 16 }}>{s.icon}</span>
              <span style={{ flex: 1 }}>{s.label}</span>
              {!s.ready && <span style={{ fontSize: 10, opacity: 0.6 }}>sắp có</span>}
            </button>
          ))}
        </nav>
        <div style={{ borderTop: '1px solid #334155', paddingTop: 12, marginTop: 12, fontSize: 13 }}>
          <div style={{ opacity: 0.7, marginBottom: 8 }}>👋 {user?.username}</div>
          <button onClick={onLogout} style={{
            width: '100%', padding: '8px', borderRadius: 8, border: '1px solid #475569',
            background: 'transparent', color: '#e2e8f0', cursor: 'pointer', fontWeight: 600,
          }}>Đăng xuất</button>
        </div>
      </aside>

      {/* Content */}
      <main style={{ flex: 1, padding: '24px 28px', overflowX: 'auto' }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, marginBottom: 18 }}>
          {active.icon} {active.label}
        </h1>
        {section === 'users' && <UsersAdminPage currentUsername={user?.username} />}
        {section !== 'users' && (
          <div style={{
            padding: 40, textAlign: 'center', color: 'var(--muted, #64748b)',
            background: 'var(--card, #fff)', borderRadius: 14,
          }}>
            Mục "{active.label}" sẽ được bổ sung ở phase tiếp theo.
          </div>
        )}
      </main>

      <Toast />
    </div>
  );
}
