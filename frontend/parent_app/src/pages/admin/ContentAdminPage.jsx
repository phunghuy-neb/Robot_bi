import { useState, useEffect, useCallback } from 'react';
import {
  adminListContent, adminCreateContent, adminUpdateContent, adminDeleteContent,
  adminRadioSearch, showToast,
} from '../../services/api.js';
import Toggle from '../../components/admin/Toggle.jsx';

const TYPES = [
  { key: 'radio', label: '📻 Radio' },
  { key: 'video', label: '🎬 Video' },
  { key: 'game', label: '🎮 Trò chơi' },
];
const GAME_PRESETS = [
  {
    label: 'Word Quiz',
    title: 'Đố từ vựng',
    description: 'Bi đố từ vựng tiếng Việt và tiếng Anh — trả lời ngay trong Parent App.',
    source_url: '/api/game/word-quiz/start',
    tags: 'vocabulary, quiz',
  },
  {
    label: 'Voice Quiz nhập đáp án',
    title: 'Đố vui bằng giọng nói',
    description: 'Bi đưa câu đố; bé nhập câu trả lời khi chưa dùng mic/loa.',
    source_url: '/api/game/voice-quiz/start',
    tags: 'voice, quiz',
  },
];
const EMPTY = { type: 'radio', title: '', description: '', source_url: '', thumbnail_url: '', age_min: 5, age_max: 12, language: 'vi', tags: '', enabled: true, sort_order: 0 };

export default function ContentAdminPage() {
  const [filter, setFilter] = useState('');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY);
  const [editId, setEditId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [radioQ, setRadioQ] = useState('');
  const [radioResults, setRadioResults] = useState(null);
  const [radioSearching, setRadioSearching] = useState(false);

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

  function applyGamePreset(preset) {
    setForm({
      ...form,
      type: 'game',
      title: form.title || preset.title,
      description: form.description || preset.description,
      source_url: preset.source_url,
      thumbnail_url: '',
      tags: preset.tags,
      enabled: true,
    });
  }

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

  async function searchRadio(e) {
    e?.preventDefault?.();
    if (!radioQ.trim()) return;
    setRadioSearching(true);
    setRadioResults(await adminRadioSearch(radioQ.trim()));
    setRadioSearching(false);
  }

  function useStation(st) {
    setEditId(null);
    setForm({
      type: 'radio', title: st.name, description: st.country || '',
      source_url: st.url, thumbnail_url: st.favicon || '', age_min: 5, age_max: 12,
      language: 'vi', tags: (st.tags || []).join(', '), enabled: true, sort_order: 0,
    });
    showToast('Đã điền vào form — kiểm tra rồi bấm Thêm');
    window.scrollTo({ top: 0, behavior: 'smooth' });
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
      <p className="admin-page-note">
        Nội dung <b>chung</b> (radio / video / trò chơi) hiển thị cho mọi gia đình. Mục tạo ở đây là
        global; nội dung riêng của từng gia đình không nằm trong danh sách quản trị này.
      </p>

      <form onSubmit={submit} className="admin-card admin-form-grid">
        <label className="admin-field">Loại
          <select className="admin-select" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
            {TYPES.map(t => <option key={t.key} value={t.key}>{t.label}</option>)}
          </select>
        </label>
        <label className="admin-field">Tiêu đề<input className="admin-input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required /></label>
        <label className="admin-field">URL nguồn<input className="admin-input" value={form.source_url} onChange={e => setForm({ ...form, source_url: e.target.value })} /></label>
        <label className="admin-field">Ảnh thumbnail (URL)<input className="admin-input" value={form.thumbnail_url} onChange={e => setForm({ ...form, thumbnail_url: e.target.value })} /></label>
        <label className="admin-field">Ngôn ngữ<input className="admin-input" value={form.language} onChange={e => setForm({ ...form, language: e.target.value })} /></label>
        <label className="admin-field">Tuổi từ<input className="admin-input" type="number" min={0} max={18} value={form.age_min} onChange={e => setForm({ ...form, age_min: e.target.value })} /></label>
        <label className="admin-field">đến<input className="admin-input" type="number" min={0} max={18} value={form.age_max} onChange={e => setForm({ ...form, age_max: e.target.value })} /></label>
        <label className="admin-field">Thứ tự<input className="admin-input" type="number" min={0} value={form.sort_order} onChange={e => setForm({ ...form, sort_order: e.target.value })} /></label>
        <label className="admin-field full">Mô tả<input className="admin-input" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></label>
        <label className="admin-field">Thẻ (phẩy)<input className="admin-input" value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })} placeholder="science, music" /></label>
        {form.type === 'game' && (
          <div className="admin-subpanel">
            <div className="admin-detail">
              Game mở trong Parent App khi URL là <code>/api/game/word-quiz/start</code> hoặc <code>/api/game/voice-quiz/start</code>.
              URL ngoài vẫn mở ở tab mới.
            </div>
            <div className="admin-inline-actions">
              {GAME_PRESETS.map(p => (
                <button key={p.source_url} type="button" onClick={() => applyGamePreset(p)}
                  className="admin-btn ghost small">
                  Dùng preset {p.label}
                </button>
              ))}
            </div>
          </div>
        )}
        <label className="admin-field inline">
          <Toggle checked={!!form.enabled} label="Bật nội dung" onChange={enabled => setForm({ ...form, enabled })} /> Bật
        </label>
        <div className="admin-actions">
          <button type="submit" disabled={busy} className="admin-btn success">
            {editId ? 'Cập nhật' : '+ Thêm'}
          </button>
          {editId && <button type="button" onClick={resetForm} className="admin-btn ghost">Hủy</button>}
        </div>
      </form>

      <details className="admin-card">
        <summary className="admin-section-title">🔎 Tìm đài radio (Radio Browser)</summary>
        <p className="admin-page-note">
          Tìm ứng viên đài; bấm "Dùng" để điền vào form ở trên — bạn duyệt & lưu thủ công (an toàn cho trẻ).
        </p>
        <form onSubmit={searchRadio} className="admin-row fill">
          <input className="admin-input compact grow" value={radioQ} placeholder="VD: kids, classical, lullaby…"
            onChange={e => setRadioQ(e.target.value)} />
          <button type="submit" disabled={radioSearching} className="admin-btn primary">
            {radioSearching ? 'Đang tìm…' : 'Tìm'}
          </button>
        </form>
        {radioResults != null && (radioResults.length === 0 ? (
          <div className="admin-page-note">Không tìm thấy đài phù hợp.</div>
        ) : (
          <div className="admin-radio-results">
            {radioResults.map((st, i) => (
              <div key={i} className="admin-result-row">
                <div className="admin-grow">
                  <div><b>{st.name}</b></div>
                  <div className="admin-detail admin-truncate">
                    {[st.country, (st.tags || []).slice(0, 3).join(', ')].filter(Boolean).join(' · ')}
                  </div>
                </div>
                <button onClick={() => useStation(st)} className="admin-btn ghost small">Dùng</button>
              </div>
            ))}
          </div>
        ))}
      </details>

      <div className="admin-chip-row">
        <button onClick={() => setFilter('')} className={`admin-chip${filter === '' ? ' active' : ''}`}>Tất cả</button>
        {TYPES.map(t => <button key={t.key} onClick={() => setFilter(t.key)} className={`admin-chip${filter === t.key ? ' active' : ''}`}>{t.label}</button>)}
      </div>

      {loading ? <div className="spinner admin-loading" /> : (
        <div className="admin-card compact admin-table-scroll">
          {items.length === 0 ? <div className="admin-empty">Chưa có nội dung.</div> : (
            <table className="admin-table">
              <thead><tr>
                <th className="admin-th">Loại</th><th className="admin-th">Tiêu đề</th><th className="admin-th">Phạm vi</th>
                <th className="admin-th">Tuổi</th><th className="admin-th">Bật</th><th className="admin-th"></th>
              </tr></thead>
              <tbody>
                {items.map(it => (
                  <tr key={it.content_id} className={busy ? 'admin-row-busy' : ''}>
                    <td className="admin-td">{TYPES.find(t => t.key === it.type)?.label || it.type}</td>
                    <td className="admin-td">
                      <b>{it.title}</b>
                      {it.type === 'game' && (
                        <div className="admin-detail">
                          {String(it.source_url || '').startsWith('/api/game/')
                            ? 'Chơi trong Parent App'
                            : (it.source_url ? 'Mở URL ngoài' : 'Chưa cấu hình URL')}
                        </div>
                      )}
                    </td>
                    <td className="admin-td">{it.scope === 'global' ? <span className="admin-status info">🌐 Chung</span> : <span className="admin-status purple">👪 {it.family_id}</span>}</td>
                    <td className="admin-td">{it.age_min}–{it.age_max}</td>
                    <td className="admin-td">
                      <Toggle checked={!!it.enabled} label={`Bật/tắt ${it.title}`} onChange={() => toggleEnabled(it)} />
                    </td>
                    <td className="admin-td">
                      <div className="admin-inline-actions">
                        <button onClick={() => startEdit(it)} className="admin-btn ghost small">Sửa</button>
                        <button onClick={() => del(it)} className="admin-btn danger small">Xóa</button>
                      </div>
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
