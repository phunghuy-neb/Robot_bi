import { useState, useEffect } from 'react';
import { adminGetStats } from '../../services/api.js';

function Stat({ label, value, tone = '' }) {
  return (
    <div className="admin-stat-card">
      <div className={`admin-stat-value ${tone}`}>{value ?? 0}</div>
      <div className="admin-stat-label">{label}</div>
    </div>
  );
}

export default function StatsAdminPage() {
  const [s, setS] = useState(null);

  useEffect(() => { adminGetStats().then(setS); }, []);
  if (!s) return <div className="spinner admin-loading" />;

  return (
    <div>
      <div className="admin-card">
        <div className="admin-section-title">👤 Tài khoản & Gia đình</div>
        <div className="admin-stat-row">
          <Stat label="Người dùng" value={s.users?.total} />
          <Stat label="Admin" value={s.users?.admins} tone="info" />
          <Stat label="Đang hoạt động" value={s.users?.active} tone="ok" />
          <Stat label="Gia đình" value={s.families} />
          <Stat label="Hội thoại" value={s.conversations} />
        </div>
      </div>

      <div className="admin-card">
        <div className="admin-section-title">📝 Học tập</div>
        <div className="admin-stat-row">
          <Stat label="Đề thi" value={s.exams?.papers} />
          <Stat label="Đề chung" value={s.exams?.global} tone="info" />
          <Stat label="Lượt làm" value={s.exams?.sessions} />
          <Stat label="Câu hỏi" value={s.exams?.questions} />
        </div>
      </div>

      <div className="admin-card">
        <div className="admin-section-title">🎬 Nội dung & Kênh</div>
        <div className="admin-stat-row">
          <Stat label="Radio" value={s.content?.radio} />
          <Stat label="Video" value={s.content?.video} />
          <Stat label="Trò chơi" value={s.content?.game} />
          <Stat label="Kênh YT chung" value={s.youtube?.global} tone="info" />
          <Stat label="Kênh YT gia đình" value={s.youtube?.family} tone="purple" />
        </div>
      </div>

      <div className="admin-card">
        <div className="admin-section-title">🛡️ An toàn (từ lúc khởi động)</div>
        <div className="admin-stat-row">
          <Stat label="Đã kiểm tra" value={s.safety?.total_checks} />
          <Stat label="Đã chặn" value={s.safety?.blocked} tone="bad" />
          <Stat label="Chủ đề" value={s.safety?.topic} tone="warn" />
          <Stat label="Từ ngữ" value={s.safety?.blacklist} tone="purple" />
        </div>
      </div>
    </div>
  );
}
