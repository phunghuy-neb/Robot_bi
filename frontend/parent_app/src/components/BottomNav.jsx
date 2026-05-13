const TABS = [
  { id: 'home', icon: '🏠', label: 'Nhà' },
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
