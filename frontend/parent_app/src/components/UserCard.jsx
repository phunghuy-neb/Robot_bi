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
