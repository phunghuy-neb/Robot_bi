import { useState, useEffect, useCallback } from 'react';
import { showToast } from '../services/api.js';

// Quản lý danh sách kênh YouTube ĐÃ DUYỆT (allowlist).
// Dùng chung cho Admin (global) và Parent App (gia đình) — chỉ khác hàm API truyền vào.
const EMPTY = { channel_id: '', label: '', language: 'vi', age_min: 5, age_max: 12, tags: '' };

export default function YouTubeChannelManager({ loadFn, addFn, removeFn, accent = '#dc2626' }) {
  const [meta, setMeta] = useState({});
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await loadFn();
    setChannels(data?.channels || []);
    setMeta(data || {});
    setLoading(false);
  }, [loadFn]);
  useEffect(() => { load(); }, [load]);

  async function add(e) {
    e.preventDefault();
    const cid = form.channel_id.trim();
    if (!cid.startsWith('UC') || cid.length < 10) {
      showToast('channel_id phải bắt đầu bằng UC… (mở kênh → Share → Copy channel ID)');
      return;
    }
    setBusy(true);
    const res = await addFn({
      channel_id: cid,
      label: form.label.trim(),
      language: (form.language || 'vi').trim().toLowerCase(),
      age_min: Number(form.age_min) || 0,
      age_max: Number(form.age_max) || 18,
      tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
    });
    setBusy(false);
    if (res?.ok) { showToast('Đã thêm kênh'); setForm(EMPTY); load(); }
    else showToast('Thêm kênh thất bại (kiểm tra channel_id)');
  }

  async function del(ch) {
    if (!window.confirm(`Bỏ kênh "${ch.label || ch.channel_id}" khỏi danh sách?`)) return;
    setBusy(true);
    const res = await removeFn(ch.channel_id);
    setBusy(false);
    if (res?.ok) { showToast('Đã bỏ kênh'); load(); } else showToast('Bỏ kênh thất bại');
  }

  if (loading) return <div className="spinner" style={{ margin: 40 }} />;

  const inp = { padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', fontSize: 14 };
  const th = { textAlign: 'left', padding: '10px 12px', fontSize: 13, color: 'var(--muted,#64748b)', borderBottom: '2px solid var(--border,#e2e8f0)' };
  const td = { padding: '10px 12px', borderBottom: '1px solid var(--border,#eef1f6)', fontSize: 14 };

  const notReady = meta.available === false;

  return (
    <div>
      {notReady && (
        <div style={{ padding: '10px 14px', borderRadius: 10, background: '#fef3c7', color: '#92400e', fontSize: 13, marginBottom: 14 }}>
          ⚠️ Chưa bật YouTube: cần đặt <code>YOUTUBE_API_KEY</code> trong .env (Admin → API key) và bật công tắc. Bạn vẫn có thể thêm kênh trước; video sẽ hiện khi đã bật key.
        </div>
      )}

      <form onSubmit={add} style={{ background: 'var(--card,#fff)', borderRadius: 14, padding: 16, marginBottom: 16, display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', alignItems: 'end' }}>
        <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' }}>
          Channel ID (UC…)
          <input style={inp} value={form.channel_id} placeholder="UCxxxxxxxxxxxx"
            onChange={e => setForm({ ...form, channel_id: e.target.value })} required />
        </label>
        <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' }}>
          Tên hiển thị
          <input style={inp} value={form.label} placeholder="VD: POPS Kids"
            onChange={e => setForm({ ...form, label: e.target.value })} />
        </label>
        <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' }}>
          Ngôn ngữ
          <input style={inp} value={form.language} placeholder="vi"
            onChange={e => setForm({ ...form, language: e.target.value })} />
        </label>
        <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' }}>
          Tuổi từ
          <input style={inp} type="number" min={0} max={18} value={form.age_min}
            onChange={e => setForm({ ...form, age_min: e.target.value })} />
        </label>
        <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' }}>
          đến
          <input style={inp} type="number" min={0} max={18} value={form.age_max}
            onChange={e => setForm({ ...form, age_max: e.target.value })} />
        </label>
        <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' }}>
          Thẻ (cách nhau dấu phẩy)
          <input style={inp} value={form.tags} placeholder="english, math"
            onChange={e => setForm({ ...form, tags: e.target.value })} />
        </label>
        <button type="submit" disabled={busy} style={{ padding: '9px 16px', borderRadius: 8, border: 'none', background: accent, color: '#fff', fontWeight: 700, cursor: 'pointer' }}>
          + Thêm kênh
        </button>
      </form>

      <div style={{ background: 'var(--card,#fff)', borderRadius: 14, padding: 12, overflowX: 'auto' }}>
        {channels.length === 0 ? (
          <div style={{ padding: 28, textAlign: 'center', color: 'var(--muted,#64748b)' }}>Chưa có kênh nào trong danh sách.</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 640 }}>
            <thead>
              <tr><th style={th}>Tên</th><th style={th}>Channel ID</th><th style={th}>Ngôn ngữ</th><th style={th}>Tuổi</th><th style={th}>Thẻ</th><th style={th}></th></tr>
            </thead>
            <tbody>
              {channels.map(ch => (
                <tr key={ch.channel_id}>
                  <td style={td}><b>{ch.label || '(chưa đặt tên)'}</b></td>
                  <td style={{ ...td, fontFamily: 'monospace', fontSize: 12 }}>
                    <a href={`https://www.youtube.com/channel/${ch.channel_id}`} target="_blank" rel="noreferrer">{ch.channel_id}</a>
                  </td>
                  <td style={td}>{ch.language}</td>
                  <td style={td}>{ch.age_min}–{ch.age_max}</td>
                  <td style={{ ...td, fontSize: 12, color: 'var(--muted,#64748b)' }}>{(ch.tags || []).join(', ')}</td>
                  <td style={td}>
                    <button disabled={busy} onClick={() => del(ch)}
                      style={{ padding: '5px 10px', borderRadius: 8, border: 'none', background: '#dc2626', color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: 12 }}>Bỏ</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
