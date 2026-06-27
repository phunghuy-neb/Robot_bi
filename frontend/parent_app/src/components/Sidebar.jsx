import RobotStatusCard from './RobotStatusCard.jsx';
import UserCard from './UserCard.jsx';

const TABS = [
  { id: 'home', icon: '🏠', label: 'Trang chủ' },
  { id: 'monitor', icon: '📹', label: 'Giám sát' },
  { id: 'learning', icon: '📊', label: 'Theo dõi học tập' },
  { id: 'learninghub', icon: '📚', label: 'Học tập' },
  { id: 'journal', icon: '📔', label: 'Nhật ký' },
  { id: 'more', icon: '➕', label: 'Thêm' },
];

export default function Sidebar({
  activeTab,
  onTabChange,
  robotStatus,
  user,
  activeChild,
  allowedTabs,
  onOpenSettings,
  onLogout,
  onSwitchChild,
}) {
  const tabs = TABS.filter(t => !allowedTabs || allowedTabs.includes(t.id));
  return (
    <nav className="side-nav">
      <div className="side-nav-logo">
        <span className="logo-icon">🤖</span>
        <strong>Robot Bi</strong>
      </div>

      <div className="side-nav-tabs">
        {tabs.map(t => (
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
