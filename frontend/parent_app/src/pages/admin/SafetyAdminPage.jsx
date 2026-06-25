import { useState, useEffect, useCallback } from 'react';
import {
  adminGetSafetyConfig, adminSetSafetyBlocklist, adminSetSafetyTopics,
  adminSetSafetyPolicy, adminGetSafetyStats, adminResetSafetyStats, showToast,
} from '../../services/api.js';

const card = { background: 'var(--card,#fff)', borderRadius: 14, padding: 18, marginBottom: 16 };
const h3 = { margin: '0 0 4px', fontSize: 16, fontWeight: 800 };
const hint = { fontSize: 13, color: 'var(--muted,#64748b)', margin: '0 0 12px' };
const inp = { padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', fontSize: 14, width: '100%' };

// Trình sửa danh sách dạng "chip" — thêm bằng Enter, bỏ bằng ✕.
function TagEditor({ items, onAdd, onRemove, placeholder, accent }) {
  const [val, setVal] = useState('');
  function submit(e) {
    e.preventDefault();
    const v = val.trim();
    if (v) { onAdd(v); setVal(''); }
  }
  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
        {items.length === 0 && <span style={{ fontSize: 13, color: 'var(--muted,#94a3b8)' }}>Chưa có mục nào.</span>}
        {items.map(t => (
          <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 999, background: '#f1f5f9', fontSize: 13 }}>
            {t}
            <button onClick={() => onRemove(t)} title="Bỏ"
              style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: '#dc2626', fontWeight: 800 }}>✕</button>
          </span>
        ))}
      </div>
      <form onSubmit={submit} style={{ display: 'flex', gap: 8 }}>
        <input style={inp} value={val} placeholder={placeholder} onChange={e => setVal(e.target.value)} />
        <button type="submit" style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: accent, color: '#fff', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' }}>+ Thêm</button>
      </form>
    </div>
  );
}

export default function SafetyAdminPage() {
  const [cfg, setCfg] = useState(null);
  const [stats, setStats] = useState({ counts: {}, recent: [] });
  const [policy, setPolicy] = useState(null);
  const [savingPolicy, setSavingPolicy] = useState(false);

  const load = useCallback(async () => {
    const c = await adminGetSafetyConfig();
    setCfg(c);
    setPolicy(c.policy || {});
    setStats(await adminGetSafetyStats());
  }, []);
  useEffect(() => { load(); }, [load]);

  async function saveBlocklist(next) {
    const res = await adminSetSafetyBlocklist(next);
    if (res?.ok) { setCfg(c => ({ ...c, blocklist_words: res.blocklist_words })); showToast('Đã lưu blocklist'); }
    else showToast('Lưu thất bại');
  }
  async function saveTopics(next) {
    const res = await adminSetSafetyTopics(next);
    if (res?.ok) { setCfg(c => ({ ...c, blocked_topics: res.blocked_topics })); showToast('Đã lưu chủ đề cấm'); }
    else showToast('Lưu thất bại');
  }
  async function savePolicy() {
    setSavingPolicy(true);
    const res = await adminSetSafetyPolicy(policy);
    setSavingPolicy(false);
    if (res?.ok) { setPolicy(res.policy); showToast('Đã lưu chính sách'); }
    else showToast('Lưu thất bại (kiểm tra giá trị)');
  }
  async function refreshStats() { setStats(await adminGetSafetyStats()); }
  async function resetStats() {
    if (!window.confirm('Xóa toàn bộ số liệu theo dõi?')) return;
    await adminResetSafetyStats();
    refreshStats();
  }

  if (!cfg || !policy) return <div className="spinner" style={{ margin: 40 }} />;

  const A = policy.age || {}, T = policy.time || {}, S = policy.sleep || {};
  const setA = (k, v) => setPolicy(p => ({ ...p, age: { ...p.age, [k]: v } }));
  const setT = (k, v) => setPolicy(p => ({ ...p, time: { ...p.time, [k]: v } }));
  const setS = (k, v) => setPolicy(p => ({ ...p, sleep: { ...p.sleep, [k]: v } }));
  const lbl = { display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' };
  const c = stats.counts || {};

  return (
    <div>
      {/* Blocklist từ ngữ */}
      <div style={card}>
        <div style={h3}>🚫 Blocklist từ ngữ (global)</div>
        <p style={hint}>Từ/cụm sẽ bị thay bằng "…" trong câu trả lời, áp cho mọi gia đình.
          Bổ sung cho {cfg.hardcoded_blacklist_count} từ mặc định sẵn có — không thay thế.</p>
        <TagEditor accent="#dc2626" placeholder="Nhập từ rồi Enter…" items={cfg.blocklist_words}
          onAdd={w => saveBlocklist([...cfg.blocklist_words, w])}
          onRemove={w => saveBlocklist(cfg.blocklist_words.filter(x => x !== w))} />
      </div>

      {/* Chủ đề cấm */}
      <div style={card}>
        <div style={h3}>⛔ Chủ đề cấm (global)</div>
        <p style={hint}>Câu chứa các cụm này sẽ bị từ chối ngay (câu trả lời an toàn chuẩn).
          Khớp cả khi gõ có dấu lẫn không dấu.</p>
        <TagEditor accent="#b45309" placeholder="VD: ma túy, cờ bạc…" items={cfg.blocked_topics}
          onAdd={t => saveTopics([...cfg.blocked_topics, t])}
          onRemove={t => saveTopics(cfg.blocked_topics.filter(x => x !== t))} />
      </div>

      {/* Chính sách mặc định */}
      <div style={card}>
        <div style={h3}>🧭 Chính sách mặc định (cho gia đình chưa tự cấu hình)</div>
        <p style={hint}>Áp dụng làm mặc định cho bộ lọc tuổi, giới hạn thời gian và giờ ngủ.
          Gia đình đã tự đặt sẽ giữ cấu hình riêng của họ.</p>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))' }}>
          <label style={lbl}>Tuổi tối thiểu<input style={inp} type="number" min={0} max={18} value={A.min_age ?? 5} onChange={e => setA('min_age', Number(e.target.value))} /></label>
          <label style={lbl}>Tuổi tối đa<input style={inp} type="number" min={0} max={18} value={A.max_age ?? 12} onChange={e => setA('max_age', Number(e.target.value))} /></label>
          <label style={lbl}>Chế độ nghiêm ngặt
            <select style={inp} value={A.strict_mode ? '1' : '0'} onChange={e => setA('strict_mode', e.target.value === '1')}>
              <option value="1">Bật</option><option value="0">Tắt</option>
            </select>
          </label>
          <label style={lbl}>Phút/ngày<input style={inp} type="number" min={1} max={480} value={T.daily_limit_minutes ?? 60} onChange={e => setT('daily_limit_minutes', Number(e.target.value))} /></label>
          <label style={lbl}>Cảnh báo trước (phút)<input style={inp} type="number" min={0} max={120} value={T.warning_minutes ?? 10} onChange={e => setT('warning_minutes', Number(e.target.value))} /></label>
          <label style={lbl}>Giờ reset (HH:MM)<input style={inp} value={T.reset_time ?? '00:00'} onChange={e => setT('reset_time', e.target.value)} /></label>
          <label style={lbl}>Bắt đầu ngủ (HH:MM)<input style={inp} value={S.start_time ?? '21:00'} onChange={e => setS('start_time', e.target.value)} /></label>
          <label style={lbl}>Kết thúc ngủ (HH:MM)<input style={inp} value={S.end_time ?? '06:30'} onChange={e => setS('end_time', e.target.value)} /></label>
        </div>
        <button onClick={savePolicy} disabled={savingPolicy} style={{ marginTop: 14, padding: '9px 18px', borderRadius: 8, border: 'none', background: '#2563eb', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>
          {savingPolicy ? 'Đang lưu…' : 'Lưu chính sách'}
        </button>
      </div>

      {/* Theo dõi */}
      <div style={card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <div style={h3}>📊 Theo dõi an toàn</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={refreshStats} style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', background: 'transparent', cursor: 'pointer', fontSize: 13 }}>↻ Làm mới</button>
            <button onClick={resetStats} style={{ padding: '6px 12px', borderRadius: 8, border: 'none', background: '#64748b', color: '#fff', cursor: 'pointer', fontSize: 13 }}>Xóa số liệu</button>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 12 }}>
          <Stat label="Đã kiểm tra" value={c.total_checks || 0} />
          <Stat label="Đã chặn" value={c.blocked || 0} color="#dc2626" />
          <Stat label="Chủ đề" value={c.topic || 0} color="#b45309" />
          <Stat label="Từ ngữ" value={c.blacklist || 0} color="#7c3aed" />
        </div>
        <div style={{ overflowX: 'auto' }}>
          {(stats.recent || []).length === 0 ? (
            <div style={{ padding: 18, textAlign: 'center', color: 'var(--muted,#64748b)' }}>Chưa có lượt chặn nào.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 420 }}>
              <thead><tr>
                <th style={{ textAlign: 'left', padding: '8px 10px', fontSize: 12, color: 'var(--muted,#64748b)' }}>Thời điểm</th>
                <th style={{ textAlign: 'left', padding: '8px 10px', fontSize: 12, color: 'var(--muted,#64748b)' }}>Lớp</th>
                <th style={{ textAlign: 'left', padding: '8px 10px', fontSize: 12, color: 'var(--muted,#64748b)' }}>Trigger</th>
              </tr></thead>
              <tbody>
                {stats.recent.map((e, i) => (
                  <tr key={i}>
                    <td style={{ padding: '8px 10px', fontSize: 12, borderTop: '1px solid var(--border,#eef1f6)' }}>{(e.timestamp || '').replace('T', ' ').slice(0, 19)}</td>
                    <td style={{ padding: '8px 10px', fontSize: 13, borderTop: '1px solid var(--border,#eef1f6)' }}>{e.layer === 'topic' ? '⛔ Chủ đề' : '🚫 Từ ngữ'}</td>
                    <td style={{ padding: '8px 10px', fontSize: 13, fontFamily: 'monospace', borderTop: '1px solid var(--border,#eef1f6)' }}>{e.trigger}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{ minWidth: 96 }}>
      <div style={{ fontSize: 24, fontWeight: 800, color: color || 'var(--text,#0f172a)' }}>{value}</div>
      <div style={{ fontSize: 12, color: 'var(--muted,#64748b)' }}>{label}</div>
    </div>
  );
}
