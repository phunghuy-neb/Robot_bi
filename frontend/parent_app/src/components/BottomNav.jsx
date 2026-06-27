const TABS = [
  { id: 'home', icon: '🏠', label: 'Trang chủ' },
  { id: 'monitor', icon: '📹', label: 'Giám sát' },
  { id: 'learning', icon: '📊', label: 'Theo dõi' },
  { id: 'learninghub', icon: '📚', label: 'Học' },
  { id: 'journal', icon: '📔', label: 'Nhật ký' },
  { id: 'more', icon: '➕', label: 'Thêm' },
];

export default function BottomNav({ activeTab, onTabChange, allowedTabs }) {
  const tabs = TABS.filter(t => !allowedTabs || allowedTabs.includes(t.id));
  return (
    <nav className="bottom-nav">
      {tabs.map(t => (
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
