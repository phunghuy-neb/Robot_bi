import { useState, useEffect, useCallback } from 'react';
import {
  adminListContent, adminCreateContent, adminUpdateContent, adminDeleteContent, showToast,
} from '../../services/api.js';

const TYPES = [
  { key: 'radio', label: '📻 Radio' },
  { key: 'video', label: '🎬 Video' },
  { key: 'game', label: '🎮 Trò chơi' },
];
const EMPTY = { type: 'radio', title: '', description: '', source_url: '', thumbnail_url: '', age_min: 5, age_max: 12, language: 'vi', tags: '', enabled: true, sort_order: 0 };

const card = { background: 'var(--card,#fff)', borderRadius: 14, padding: 16 };
const inp = { padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', fontSize: 14, width: '100%' };
const lbl = { display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' };
const th = { textAlign: 'left', padding: '10px 12px', fontSize: 13, color: 'var(--muted,#64748b)', borderBottom: '2px solid var(--border,#e2e8f0)' };
const td = { padding: '10px 12px', borderBottom: '1px solid var(--border,#eef1f6)', fontSize: 14 };

export default function ContentAdminPage() {
  const [filter, setFilter] = useState('');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setItems(await adminListContent(filter));
    setLoading(false);
  }, [filter]);
  useEffect(() => { load(); }, [load]);

  function startEdit(it) {
    setEditId(it.content_id);
    setForm({ ...it, tags: (it.tags || []).join(', ') });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  function resetForm() { setEditId(null); setForm(EMPTY); }

  async function submit(e) {
    e.preventDefault();
    if (!form.title.trim()) { showToast('Cần tiêu đề'); return; }
    const payload = {
      type: form.type, title: form.title.trim(), description: form.description.trim(),
      source_url: form.source_url.trim(), thumbnail_url: form.thumbnail_url.trim(),
      age_min: Number(form.age_min) || 0, age_max: Number(form.age_max) || 18,
      language: (form.language || 'vi').trim(), enabled: !!form.enabled,
      sort_order: Number(form.sort_order) || 0,
      tags: String(form.tags).split(',').map(t => t.trim()).filter(Boolean),
    };
    setBusy(true);
    const res = editId ? await adminUpdateContent(editId, payload) : await adminCreateContent(payload);
    setBusy(false);
    if (res?.ok) { showToast(editId ? 'Đã cập nhật' : 'Đã thêm nội dung'); resetForm(); load(); }
    else showToast('Lưu thất bại');
  }

  async function toggleEnabled(it) {
    const res = await adminUpdateContent(it.content_id, { ...it, enabled: !it.enabled, tags: it.tags });
    if (res?.ok) load();
  }

  async function del(it) {
    if (!window.confirm(`Xóa "${it.title}"?`)) return;
    setBusy(true);
    const res = await adminDeleteContent(it.content_id);
    setBusy(false);
    if (res?.ok) { showToast('Đã xóa'); load(); } else showToast('Xóa thất bại');
  }

  return (
    <div>
      <p style={{ fontSize: 13, color: 'var(--muted,#64748b)', margin: '0 0 14px' }}>
        Nội dung <b>chung</b> (radio / video / trò chơi) hiển thị cho mọi gia đình. Mục tạo ở đây là
        global; nội dung riêng của từng gia đình không nằm trong danh sách quản trị này.
      </p>

      <form onSubmit={submit} style={{ ...card, marginBottom: 16, display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', alignItems: 'end' }}>
        <label style={lbl}>Loại
          <select style={inp} value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
            {TYPES.map(t => <option key={t.key} value={t.key}>{t.label}</option>)}
          </select>
        </label>
        <label style={lbl}>Tiêu đề<input style={inp} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required /></label>
        <label style={lbl}>URL nguồn<input style={inp} value={form.source_url} onChange={e => setForm({ ...form, source_url: e.target.value })} /></label>
        <label style={lbl}>Ảnh thumbnail (URL)<input style={inp} value={form.thumbnail_url} onChange={e => setForm({ ...form, thumbnail_url: e.target.value })} /></label>
        <label style={lbl}>Ngôn ngữ<input style={inp} value={form.language} onChange={e => setForm({ ...form, language: e.target.value })} /></label>
        <label style={lbl}>Tuổi từ<input style={inp} type="number" min={0} max={18} value={form.age_min} onChange={e => setForm({ ...form, age_min: e.target.value })} /></label>
        <label style={lbl}>đến<input style={inp} type="number" min={0} max={18} value={form.age_max} onChange={e => setForm({ ...form, age_max: e.target.value })} /></label>
        <label style={lbl}>Thứ tự<input style={inp} type="number" min={0} value={form.sort_order} onChange={e => setForm({ ...form, sort_order: e.target.value })} /></label>
        <label style={{ ...lbl, gridColumn: '1 / -1' }}>Mô tả<input style={inp} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
        <label style={lbl}>Thẻ (phẩy)<input style={inp} value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} placeholder="science, music" /></label>
        <label style={{ ...lbl, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" checked={!!form.enabled} onChange={e => setForm({ ...form, enabled: e.target.checked })} /> Bật
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="submit" disabled={busy} style={{ padding: '9px 16px', borderRadius: 8, border: 'none', background: '#16a34a', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>
            {editId ? 'Cập nhật' : '+ Thêm'}
          </button>
          {editId && <button type="button" onClick={resetForm} style={{ padding: '9px 14px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', background: 'transparent', cursor: 'pointer' }}>Hủy</button>}
        </div>
      </form>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button onClick={() => setFilter('')} style={chip(filter === '')}>Tất cả</button>
        {TYPES.map(t => <button key={t.key} onClick={() => setFilter(t.key)} style={chip(filter === t.key)}>{t.label}</button>)}
      </div>

      {loading ? <div className="spinner" style={{ margin: 40 }} /> : (
        <div style={{ ...card, overflowX: 'auto' }}>
          {items.length === 0 ? <div style={{ padding: 24, textAlign: 'center', color: 'var(--muted,#64748b)' }}>Chưa có nội dung.</div> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
              <thead><tr>
                <th style={th}>Loại</th><th style={th}>Tiêu đề</th><th style={th}>Phạm vi</th>
                <th style={th}>Tuổi</th><th style={th}>Bật</th><th style={th}></th>
              </tr></thead>
              <tbody>
                {items.map(it => (
                  <tr key={it.content_id} style={{ opacity: busy ? 0.6 : 1 }}>
                    <td style={td}>{TYPES.find(t => t.key === it.type)?.label || it.type}</td>
                    <td style={td}><b>{it.title}</b></td>
                    <td style={td}>{it.scope === 'global' ? <span style={{ color: '#2563eb' }}>🌐 Chung</span> : <span style={{ color: '#7c3aed' }}>👪 {it.family_id}</span>}</td>
                    <td style={td}>{it.age_min}–{it.age_max}</td>
                    <td style={td}>
                      <button onClick={() => toggleEnabled(it)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 18 }} title="Bật/tắt">{it.enabled ? '✅' : '⬜'}</button>
                    </td>
                    <td style={td}>
                      <button onClick={() => startEdit(it)} style={{ padding: '5px 10px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', background: 'transparent', cursor: 'pointer', fontSize: 12, marginRight: 6 }}>Sửa</button>
                      <button onClick={() => del(it)} style={{ padding: '5px 10px', borderRadius: 8, border: 'none', background: '#dc2626', color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: 12 }}>Xóa</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

function chip(active) {
  return {
    padding: '7px 14px', borderRadius: 999, cursor: 'pointer', fontSize: 13, fontWeight: 600,
    border: active ? 'none' : '1px solid var(--border,#cbd5e1)',
    background: active ? '#2563eb' : 'transparent', color: active ? '#fff' : 'var(--text,#0f172a)',
  };
}
