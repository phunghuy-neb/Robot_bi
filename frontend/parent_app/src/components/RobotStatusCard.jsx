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
