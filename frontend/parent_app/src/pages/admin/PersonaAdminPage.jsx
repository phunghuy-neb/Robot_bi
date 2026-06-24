import { useState, useEffect } from 'react';
import { adminGetPersona, adminSetPersona, showToast } from '../../services/api.js';

const card = { background: 'var(--card,#fff)', borderRadius: 14, padding: 18, marginBottom: 16 };
const inp = { padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', fontSize: 14, width: '100%' };
const lbl = { display: 'grid', gap: 4, fontSize: 12, color: 'var(--muted,#64748b)' };

const GENDERS = [['neutral', 'Trung tính'], ['female', 'Nữ'], ['male', 'Nam']];
const LANGS = [['vi', 'Tiếng Việt'], ['en', 'English'], ['ja', '日本語'], ['ko', '한국어'], ['zh', '中文'], ['fr', 'Français'], ['de', 'Deutsch'], ['es', 'Español']];
const TRAITS = [['playfulness', 'Tinh nghịch'], ['extraversion', 'Hướng ngoại'], ['energy', 'Năng lượng']];

export default function PersonaAdminPage() {
  const [p, setP] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => { adminGetPersona().then(setP); }, []);
  if (!p) return <div className="spinner" style={{ margin: 40 }} />;

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
      <p style={{ fontSize: 13, color: 'var(--muted,#64748b)', margin: '0 0 14px' }}>
        Tính cách & giọng <b>mặc định</b> của Bi. Gia đình <b>chưa tự cấu hình</b> sẽ kế thừa cấu hình
        này; gia đình đã tùy chỉnh riêng vẫn giữ của họ. (Vai trò trò chuyện — bạn/thầy/cha mẹ — được
        chọn tự động theo ngữ cảnh, không cấu hình ở đây.)
      </p>

      <div style={card}>
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
          <label style={lbl}>Tên<input style={inp} value={p.name || ''} onChange={e => set('name', e.target.value)} /></label>
          <label style={lbl}>Giới tính
            <select style={inp} value={p.gender || 'neutral'} onChange={e => set('gender', e.target.value)}>
              {GENDERS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label style={lbl}>Ngôn ngữ
            <select style={inp} value={p.language || 'vi'} onChange={e => set('language', e.target.value)}>
              {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label style={{ ...lbl, gridColumn: '1 / -1' }}>Giọng đọc (edge-tts voice)
            <input style={inp} value={p.voice || ''} onChange={e => set('voice', e.target.value)} placeholder="vi-VN-HoaiMyNeural" />
          </label>
        </div>

        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>Tính cách</div>
          {TRAITS.map(([k, l]) => (
            <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <span style={{ width: 110, fontSize: 13 }}>{l}</span>
              <input type="range" min={0} max={100} value={p.personality?.[k] ?? 50}
                onChange={e => setTrait(k, Number(e.target.value))} style={{ flex: 1 }} />
              <span style={{ width: 36, textAlign: 'right', fontWeight: 700 }}>{p.personality?.[k] ?? 50}</span>
            </div>
          ))}
        </div>

        <button onClick={save} disabled={saving} style={{ marginTop: 14, padding: '9px 18px', borderRadius: 8, border: 'none', background: '#2563eb', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>
          {saving ? 'Đang lưu…' : 'Lưu persona mặc định'}
        </button>
      </div>
    </div>
  );
}
