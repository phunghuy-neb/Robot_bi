import { useState, useEffect, useCallback } from 'react';
import {
  getSpecialMemories,
  addSpecialMemory,
  deleteSpecialMemory,
  remindDueSpecialMemories,
  showToast,
} from '../services/api.js';

const KINDS = [
  ['birthday', '🎂 Sinh nhật'],
  ['milestone', '🏅 Cột mốc'],
  ['favorite', '💖 Sở thích'],
  ['other', '🌟 Kỷ niệm'],
];
const KIND_ICON = { birthday: '🎂', milestone: '🏅', favorite: '💖', other: '🌟' };
const EMPTY = { title: '', kind: 'other', memory_date: '', note: '' };
const inp = { padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', fontSize: 14, width: '100%' };

export default function SpecialMemories() {
  const [items, setItems] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reminding, setReminding] = useState(false);

  const load = useCallback(async () => {
    setItems(await getSpecialMemories());
    setLoaded(true);
  }, []);
  useEffect(() => { load(); }, [load]);

  async function add(e) {
    e.preventDefault();
    if (!form.title.trim()) { showToast('Hãy nhập tên kỷ niệm.'); return; }
    setBusy(true);
    const res = await addSpecialMemory(form);
    setBusy(false);
    if (res?.ok) { showToast('Đã lưu kỷ niệm — Bi sẽ ghi nhớ'); setForm(EMPTY); setOpen(false); load(); }
    else showToast('Lưu thất bại');
  }

  async function del(m) {
    if (!window.confirm(`Xóa kỷ niệm "${m.title}"?`)) return;
    setBusy(true);
    const res = await deleteSpecialMemory(m.memory_id);
    setBusy(false);
    if (res?.ok) { showToast('Đã xóa'); load(); } else showToast('Xóa thất bại');
  }

  async function remindDue() {
    setReminding(true);
    const res = await remindDueSpecialMemories();
    setReminding(false);
    if (res?.ok) {
      if ((res.created_count || 0) > 0) {
        showToast(`Đã ghi ${res.created_count} nhắc kỷ niệm vào Nhật ký`);
      } else if ((res.due_count || 0) > 0) {
        showToast('Kỷ niệm hôm nay đã có trong Nhật ký');
      } else {
        showToast('Hôm nay chưa có kỷ niệm cần nhắc');
      }
      load();
    } else {
      showToast('Không tạo được nhắc kỷ niệm');
    }
  }

  const dueItems = items.filter(m => m.due_today);

  return (
    <div className="card">
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="card-title">🌟 Kỷ niệm đặc biệt</span>
        <button className="btn-sm primary" onClick={() => setOpen(v => !v)}>{open ? 'Đóng' : '+ Thêm'}</button>
      </div>
      <div style={{ fontSize: 13, color: 'var(--muted,#64748b)', padding: '0 4px 8px' }}>
        Ghi lại sinh nhật, cột mốc, sở thích của bé — Bi sẽ nhớ và nhắc lại khi trò chuyện.
      </div>

      {open && (
        <form onSubmit={add} style={{ display: 'grid', gap: 10, padding: '8px 4px 14px', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', alignItems: 'end' }}>
          <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' }}>Tên kỷ niệm
            <input style={inp} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required />
          </label>
          <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' }}>Loại
            <select style={inp} value={form.kind} onChange={e => setForm({ ...form, kind: e.target.value })}>
              {KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' }}>Ngày (tùy chọn)
            <input style={inp} value={form.memory_date} placeholder="VD: 12/03 hoặc 2020" onChange={e => setForm({ ...form, memory_date: e.target.value })} />
          </label>
          <label style={{ display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)', gridColumn: '1 / -1' }}>Ghi chú (tùy chọn)
            <input style={inp} value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} />
          </label>
          <button type="submit" disabled={busy} style={{ padding: '9px 16px', borderRadius: 8, border: 'none', background: '#16a34a', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>Lưu kỷ niệm</button>
        </form>
      )}

      {loaded && dueItems.length > 0 && (
        <div className="special-memory-alert">
          <div>
            🔔 Hôm nay có kỷ niệm: <b>{dueItems.map(m => m.title).join(', ')}</b>
          </div>
          <button className="btn-sm secondary" onClick={remindDue} disabled={reminding}>
            {reminding ? 'Đang ghi...' : 'Ghi vào Nhật ký'}
          </button>
        </div>
      )}

      {!loaded ? (
        <SectionLoading />
      ) : items.length === 0 ? (
        <div style={{ padding: 18, textAlign: 'center', color: 'var(--muted,#64748b)' }}>Chưa có kỷ niệm nào.</div>
      ) : (
        items.map(m => (
          <div key={m.memory_id} className="media-card" style={m.due_today ? { background: '#feffd6', borderRadius: 10 } : undefined}>
            <div className="media-thumb">{m.due_today ? '🔔' : (KIND_ICON[m.kind] || '🌟')}</div>
            <div className="media-body">
              <div className="media-title">{m.title}{m.due_today ? ' · hôm nay' : ''}</div>
              <div className="media-meta">{[m.memory_date, m.note].filter(Boolean).join(' · ')}</div>
            </div>
            <button className="btn-sm" onClick={() => del(m)}
              style={{ border: 'none', background: '#dc2626', color: '#fff', fontWeight: 700, cursor: 'pointer', borderRadius: 8, padding: '6px 12px' }}>Xóa</button>
          </div>
        ))
      )}
    </div>
  );
}

function SectionLoading() {
  return <div style={{ padding: 18, textAlign: 'center', color: 'var(--muted,#64748b)' }}>Đang tải…</div>;
}
