import { useState, useEffect } from 'react';
import { adminGetStats } from '../../services/api.js';

const card = { background: 'var(--card,#fff)', borderRadius: 14, padding: 18, marginBottom: 16 };
const h3 = { margin: '0 0 12px', fontSize: 16, fontWeight: 800 };

function Stat({ label, value, color }) {
  return (
    <div style={{ minWidth: 110, padding: '12px 16px', borderRadius: 12, background: 'var(--bg,#f5f6fa)' }}>
      <div style={{ fontSize: 26, fontWeight: 800, color: color || 'var(--text,#0f172a)' }}>{value ?? 0}</div>
      <div style={{ fontSize: 12, color: 'var(--muted,#64748b)' }}>{label}</div>
    </div>
  );
}

const row = { display: 'flex', gap: 12, flexWrap: 'wrap' };

export default function StatsAdminPage() {
  const [s, setS] = useState(null);

  useEffect(() => { adminGetStats().then(setS); }, []);
  if (!s) return <div className="spinner" style={{ margin: 40 }} />;

  return (
    <div>
      <div style={card}>
        <div style={h3}>👤 Tài khoản & Gia đình</div>
        <div style={row}>
          <Stat label="Người dùng" value={s.users?.total} />
          <Stat label="Admin" value={s.users?.admins} color="#2563eb" />
          <Stat label="Đang hoạt động" value={s.users?.active} color="#16a34a" />
          <Stat label="Gia đình" value={s.families} />
          <Stat label="Hội thoại" value={s.conversations} />
        </div>
      </div>

      <div style={card}>
        <div style={h3}>📝 Học tập</div>
        <div style={row}>
          <Stat label="Đề thi" value={s.exams?.papers} />
          <Stat label="Đề chung" value={s.exams?.global} color="#2563eb" />
          <Stat label="Lượt làm" value={s.exams?.sessions} />
          <Stat label="Câu hỏi" value={s.exams?.questions} />
        </div>
      </div>

      <div style={card}>
        <div style={h3}>🎬 Nội dung & Kênh</div>
        <div style={row}>
          <Stat label="Radio" value={s.content?.radio} />
          <Stat label="Video" value={s.content?.video} />
          <Stat label="Trò chơi" value={s.content?.game} />
          <Stat label="Kênh YT chung" value={s.youtube?.global} color="#2563eb" />
          <Stat label="Kênh YT gia đình" value={s.youtube?.family} color="#7c3aed" />
        </div>
      </div>

      <div style={card}>
        <div style={h3}>🛡️ An toàn (từ lúc khởi động)</div>
        <div style={row}>
          <Stat label="Đã kiểm tra" value={s.safety?.total_checks} />
          <Stat label="Đã chặn" value={s.safety?.blocked} color="#dc2626" />
          <Stat label="Chủ đề" value={s.safety?.topic} color="#b45309" />
          <Stat label="Từ ngữ" value={s.safety?.blacklist} color="#7c3aed" />
        </div>
      </div>
    </div>
  );
}
