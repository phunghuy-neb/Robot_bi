import { useState, useEffect, useCallback } from 'react';
import { showToast } from '../services/api.js';

// Quản lý danh sách kênh YouTube ĐÃ DUYỆT (allowlist).
// Dùng chung cho Admin (global) và Parent App (gia đình) — chỉ khác hàm API truyền vào.
const EMPTY = { channel_id: '', label: '', language: 'vi', age_min: 5, age_max: 12, tags: '' };

export default function YouTubeChannelManager({ loadFn, addFn, removeFn, buttonTone = 'danger' }) {
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

  if (loading) return <div className="spinner admin-loading" />;

  const notReady = meta.available === false;
  const submitTone = ['primary', 'secondary', 'success', 'warning', 'danger', 'purple'].includes(buttonTone)
    ? buttonTone
    : 'danger';

  return (
    <div>
      {notReady && (
        <div className="admin-card warning">
          ⚠️ Chưa bật YouTube: cần đặt <code>YOUTUBE_API_KEY</code> trong .env (Admin → API key) và bật công tắc. Bạn vẫn có thể thêm kênh trước; video sẽ hiện khi đã bật key.
        </div>
      )}

      <form onSubmit={add} className="admin-card admin-form-grid wide">
        <label className="admin-field">
          Channel ID (UC…)
          <input className="admin-input" value={form.channel_id} placeholder="UCxxxxxxxxxxxx"
            onChange={e => setForm({ ...form, channel_id: e.target.value })} required />
        </label>
        <label className="admin-field">
          Tên hiển thị
          <input className="admin-input" value={form.label} placeholder="VD: POPS Kids"
            onChange={e => setForm({ ...form, label: e.target.value })} />
        </label>
        <label className="admin-field">
          Ngôn ngữ
          <input className="admin-input" value={form.language} placeholder="vi"
            onChange={e => setForm({ ...form, language: e.target.value })} />
        </label>
        <label className="admin-field">
          Tuổi từ
          <input className="admin-input" type="number" min={0} max={18} value={form.age_min}
            onChange={e => setForm({ ...form, age_min: e.target.value })} />
        </label>
        <label className="admin-field">
          đến
          <input className="admin-input" type="number" min={0} max={18} value={form.age_max}
            onChange={e => setForm({ ...form, age_max: e.target.value })} />
        </label>
        <label className="admin-field">
          Thẻ (cách nhau dấu phẩy)
          <input className="admin-input" value={form.tags} placeholder="english, math"
            onChange={e => setForm({ ...form, tags: e.target.value })} />
        </label>
        <button type="submit" disabled={busy} className={`admin-btn ${submitTone}`}>
          + Thêm kênh
        </button>
      </form>

      <div className="admin-card compact admin-table-scroll">
        {channels.length === 0 ? (
          <div className="admin-empty">Chưa có kênh nào trong danh sách.</div>
        ) : (
          <table className="admin-table compact">
            <thead>
              <tr><th className="admin-th">Tên</th><th className="admin-th">Channel ID</th><th className="admin-th">Ngôn ngữ</th><th className="admin-th">Tuổi</th><th className="admin-th">Thẻ</th><th className="admin-th"></th></tr>
            </thead>
            <tbody>
              {channels.map(ch => (
                <tr key={ch.channel_id}>
                  <td className="admin-td"><b>{ch.label || '(chưa đặt tên)'}</b></td>
                  <td className="admin-td small admin-mono">
                    <a href={`https://www.youtube.com/channel/${ch.channel_id}`} target="_blank" rel="noreferrer">{ch.channel_id}</a>
                  </td>
                  <td className="admin-td">{ch.language}</td>
                  <td className="admin-td">{ch.age_min}–{ch.age_max}</td>
                  <td className="admin-td small admin-muted">{(ch.tags || []).join(', ')}</td>
                  <td className="admin-td">
                    <button disabled={busy} onClick={() => del(ch)}
                      className="admin-btn danger small">Bỏ</button>
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
