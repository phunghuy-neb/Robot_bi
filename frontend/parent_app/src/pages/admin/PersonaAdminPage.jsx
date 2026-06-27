import { useState, useEffect } from 'react';
import { adminGetPersona, adminSetPersona, showToast } from '../../services/api.js';

const GENDERS = [['neutral', 'Trung tính'], ['female', 'Nữ'], ['male', 'Nam']];
const LANGS = [['vi', 'Tiếng Việt'], ['en', 'English'], ['ja', '日本語'], ['ko', '한국어'], ['zh', '中文'], ['fr', 'Français'], ['de', 'Deutsch'], ['es', 'Español']];
const TRAITS = [['playfulness', 'Tinh nghịch'], ['extraversion', 'Hướng ngoại'], ['energy', 'Năng lượng']];

export default function PersonaAdminPage() {
  const [p, setP] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { adminGetPersona().then(setP); }, []);
  if (!p) return <div className="spinner admin-loading" />;

  const set = (k, v) => setP(prev => ({ ...prev, [k]: v }));
  const setTrait = (k, v) => setP(prev => ({ ...prev, personality: { ...prev.personality, [k]: v } }));

  async function save() {
    setSaving(true);
    const res = await adminSetPersona({
      name: p.name, gender: p.gender, voice: p.voice, language: p.language, personality: p.personality,
    });
    setSaving(false);
    if (res?.ok) { setP(res.persona); showToast('Đã lưu persona mặc định'); }
    else showToast('Lưu thất bại (kiểm tra giá trị)');
  }

  return (
    <div>
      <p className="admin-page-note">
        Tính cách & giọng <b>mặc định</b> của Bi. Gia đình <b>chưa tự cấu hình</b> sẽ kế thừa cấu hình
        này; gia đình đã tùy chỉnh riêng vẫn giữ của họ. (Vai trò trò chuyện — bạn/thầy/cha mẹ — được
        chọn tự động theo ngữ cảnh, không cấu hình ở đây.)
      </p>

      <div className="admin-card">
        <div className="admin-form-grid">
          <label className="admin-field">Tên<input className="admin-input" value={p.name || ''} onChange={e => set('name', e.target.value)} /></label>
          <label className="admin-field">Giới tính
            <select className="admin-select" value={p.gender || 'neutral'} onChange={e => set('gender', e.target.value)}>
              {GENDERS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="admin-field">Ngôn ngữ
            <select className="admin-select" value={p.language || 'vi'} onChange={e => set('language', e.target.value)}>
              {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="admin-field full">Giọng đọc (edge-tts voice)
            <input className="admin-input" value={p.voice || ''} onChange={e => set('voice', e.target.value)} placeholder="vi-VN-HoaiMyNeural" />
          </label>
        </div>

        <div className="admin-stack admin-section-block">
          <div className="admin-section-title tight">Tính cách</div>
          {TRAITS.map(([k, l]) => (
            <div key={k} className="admin-trait-row">
              <span className="admin-trait-name">{l}</span>
              <input type="range" min={0} max={100} value={p.personality?.[k] ?? 50}
                onChange={e => setTrait(k, Number(e.target.value))} className="admin-range" />
              <span className="admin-trait-value">{p.personality?.[k] ?? 50}</span>
            </div>
          ))}
        </div>

        <button onClick={save} disabled={saving} className="admin-btn primary">
          {saving ? 'Đang lưu…' : 'Lưu persona mặc định'}
        </button>
      </div>
    </div>
  );
}
