import { useState, useEffect, useCallback } from 'react';
import {
  adminGetSafetyConfig, adminSetSafetyBlocklist, adminSetSafetyTopics,
  adminSetSafetyPolicy, adminGetSafetyStats, adminResetSafetyStats, showToast,
} from '../../services/api.js';

// Trình sửa danh sách dạng "chip" — thêm bằng Enter, bỏ bằng ✕.
function TagEditor({ items, onAdd, onRemove, placeholder, tone }) {
  const [val, setVal] = useState('');
  function submit(e) {
    e.preventDefault();
    const v = val.trim();
    if (v) { onAdd(v); setVal(''); }
  }
  return (
    <div>
      <div className="admin-tag-list">
        {items.length === 0 && <span className="admin-page-note">Chưa có mục nào.</span>}
        {items.map(t => (
          <span key={t} className="admin-tag">
            {t}
            <button className="admin-icon-btn" onClick={() => onRemove(t)} title="Bỏ">✕</button>
          </span>
        ))}
      </div>
      <form onSubmit={submit} className="admin-row fill">
        <input className="admin-input compact grow" value={val} placeholder={placeholder} onChange={e => setVal(e.target.value)} />
        <button type="submit" className={`admin-btn ${tone}`}>+ Thêm</button>
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

  if (!cfg || !policy) return <div className="spinner admin-loading" />;

  const A = policy.age || {}, T = policy.time || {}, S = policy.sleep || {};
  const setA = (k, v) => setPolicy(p => ({ ...p, age: { ...p.age, [k]: v } }));
  const setT = (k, v) => setPolicy(p => ({ ...p, time: { ...p.time, [k]: v } }));
  const setS = (k, v) => setPolicy(p => ({ ...p, sleep: { ...p.sleep, [k]: v } }));
  const c = stats.counts || {};

  return (
    <div>
      <div className="admin-card">
        <div className="admin-section-title tight">🚫 Blocklist từ ngữ (global)</div>
        <p className="admin-page-note">Từ/cụm sẽ bị thay bằng "…" trong câu trả lời, áp cho mọi gia đình.
          Bổ sung cho {cfg.hardcoded_blacklist_count} từ mặc định sẵn có — không thay thế.</p>
        <TagEditor tone="danger" placeholder="Nhập từ rồi Enter…" items={cfg.blocklist_words}
          onAdd={w => saveBlocklist([...cfg.blocklist_words, w])}
          onRemove={w => saveBlocklist(cfg.blocklist_words.filter(x => x !== w))} />
      </div>

      <div className="admin-card">
        <div className="admin-section-title tight">⛔ Chủ đề cấm (global)</div>
        <p className="admin-page-note">Câu chứa các cụm này sẽ bị từ chối ngay (câu trả lời an toàn chuẩn).
          Khớp cả khi gõ có dấu lẫn không dấu.</p>
        <TagEditor tone="warning" placeholder="VD: ma túy, cờ bạc…" items={cfg.blocked_topics}
          onAdd={t => saveTopics([...cfg.blocked_topics, t])}
          onRemove={t => saveTopics(cfg.blocked_topics.filter(x => x !== t))} />
      </div>

      <div className="admin-card">
        <div className="admin-section-title tight">🧭 Chính sách mặc định (cho gia đình chưa tự cấu hình)</div>
        <p className="admin-page-note">Áp dụng làm mặc định cho bộ lọc tuổi, giới hạn thời gian và giờ ngủ.
          Gia đình đã tự đặt sẽ giữ cấu hình riêng của họ.</p>
        <div className="admin-form-grid">
          <label className="admin-field">Tuổi tối thiểu<input className="admin-input" type="number" min={0} max={18} value={A.min_age ?? 5} onChange={e => setA('min_age', Number(e.target.value))} /></label>
          <label className="admin-field">Tuổi tối đa<input className="admin-input" type="number" min={0} max={18} value={A.max_age ?? 12} onChange={e => setA('max_age', Number(e.target.value))} /></label>
          <label className="admin-field">Chế độ nghiêm ngặt
            <select className="admin-select" value={A.strict_mode ? '1' : '0'} onChange={e => setA('strict_mode', e.target.value === '1')}>
              <option value="1">Bật</option><option value="0">Tắt</option>
            </select>
          </label>
          <label className="admin-field">Phút/ngày<input className="admin-input" type="number" min={1} max={480} value={T.daily_limit_minutes ?? 60} onChange={e => setT('daily_limit_minutes', Number(e.target.value))} /></label>
          <label className="admin-field">Cảnh báo trước (phút)<input className="admin-input" type="number" min={0} max={120} value={T.warning_minutes ?? 10} onChange={e => setT('warning_minutes', Number(e.target.value))} /></label>
          <label className="admin-field">Giờ reset (HH:MM)<input className="admin-input" value={T.reset_time ?? '00:00'} onChange={e => setT('reset_time', e.target.value)} /></label>
          <label className="admin-field">Bắt đầu ngủ (HH:MM)<input className="admin-input" value={S.start_time ?? '21:00'} onChange={e => setS('start_time', e.target.value)} /></label>
          <label className="admin-field">Kết thúc ngủ (HH:MM)<input className="admin-input" value={S.end_time ?? '06:30'} onChange={e => setS('end_time', e.target.value)} /></label>
        </div>
        <button onClick={savePolicy} disabled={savingPolicy} className="admin-btn primary">
          {savingPolicy ? 'Đang lưu…' : 'Lưu chính sách'}
        </button>
      </div>

      <div className="admin-card">
        <div className="admin-toolbar">
          <div className="admin-section-title tight">📊 Theo dõi an toàn</div>
          <div className="admin-inline-actions">
            <button onClick={refreshStats} className="admin-btn ghost small">↻ Làm mới</button>
            <button onClick={resetStats} className="admin-btn secondary small">Xóa số liệu</button>
          </div>
        </div>
        <div className="admin-stat-row">
          <Stat label="Đã kiểm tra" value={c.total_checks || 0} />
          <Stat label="Đã chặn" value={c.blocked || 0} tone="bad" />
          <Stat label="Chủ đề" value={c.topic || 0} tone="warn" />
          <Stat label="Từ ngữ" value={c.blacklist || 0} tone="purple" />
        </div>
        <div className="admin-table-scroll">
          {(stats.recent || []).length === 0 ? (
            <div className="admin-empty">Chưa có lượt chặn nào.</div>
          ) : (
            <table className="admin-table compact">
              <thead><tr>
                <th className="admin-th">Thời điểm</th>
                <th className="admin-th">Lớp</th>
                <th className="admin-th">Trigger</th>
              </tr></thead>
              <tbody>
                {stats.recent.map((e, i) => (
                  <tr key={i}>
                    <td className="admin-td small">{(e.timestamp || '').replace('T', ' ').slice(0, 19)}</td>
                    <td className="admin-td">{e.layer === 'topic' ? '⛔ Chủ đề' : '🚫 Từ ngữ'}</td>
                    <td className="admin-td admin-mono">{e.trigger}</td>
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

function Stat({ label, value, tone }) {
  return (
    <div className="admin-stat-card">
      <div className={`admin-stat-value ${tone || ''}`}>{value}</div>
      <div className="admin-stat-label">{label}</div>
    </div>
  );
}
