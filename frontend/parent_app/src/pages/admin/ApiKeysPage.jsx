import { useState, useEffect, useCallback } from 'react';
import {
  adminGetKeys, adminSetKey, adminClearKey, adminTestKey,
  adminGetToggles, adminSetToggle, showToast,
} from '../../services/api.js';

export default function ApiKeysPage() {
  const [keys, setKeys] = useState([]);
  const [toggles, setToggles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drafts, setDrafts] = useState({});   // name -> giá trị đang nhập
  const [tests, setTests] = useState({});      // name -> kết quả test
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [k, t] = await Promise.all([adminGetKeys(), adminGetToggles()]);
    setKeys(k); setToggles(t); setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  async function saveKey(name) {
    const v = (drafts[name] || '').trim();
    if (!v) { showToast('Nhập key trước đã'); return; }
    setBusy(name);
    const res = await adminSetKey(name, v);
    setBusy(null);
    if (res) { showToast('Đã lưu key'); setDrafts(d => ({ ...d, [name]: '' })); load(); }
    else showToast('Lưu thất bại');
  }
  async function clearKey(name) {
    if (!window.confirm(`Xóa ${name} khỏi .env?`)) return;
    setBusy(name);
    const res = await adminClearKey(name);
    setBusy(null);
    if (res) { showToast('Đã xóa key'); load(); } else showToast('Xóa thất bại');
  }
  async function testKey(name) {
    setBusy(name);
    setTests(t => ({ ...t, [name]: { loading: true } }));
    const res = await adminTestKey(name);
    setBusy(null);
    setTests(t => ({ ...t, [name]: res || { ok: false, detail: 'lỗi' } }));
  }
  async function flipToggle(t) {
    setBusy(t.name);
    const res = await adminSetToggle(t.name, !t.enabled);
    setBusy(null);
    if (res) { showToast('Đã cập nhật'); load(); } else showToast('Cập nhật thất bại');
  }

  if (loading) return <div className="spinner" style={{ margin: 40 }} />;

  const card = { background: 'var(--card,#fff)', borderRadius: 14, padding: 18, marginBottom: 20 };
  const btn = (bg) => ({ padding: '7px 12px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700, color: '#fff', background: bg });

  return (
    <div>
      <div style={{ ...card, background: '#fef9c3', color: '#854d0e', fontSize: 13 }}>
        ⚠️ Chỉ quản lý <b>key public</b> ở đây. Key LLM (Gemini/Groq/Cerebras…), JWT, mật khẩu
        admin <b>không hiển thị và không sửa</b> qua web — chỉ sửa trực tiếp trong <code>.env</code>.
      </div>

      {/* Public API keys */}
      <div style={card}>
        <h3 style={{ margin: '0 0 12px', fontSize: 16 }}>🔑 API key public</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {keys.map(k => {
            const t = tests[k.name];
            return (
              <div key={k.name} style={{ borderBottom: '1px solid var(--border,#eef1f6)', paddingBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 6 }}>
                  <b style={{ fontSize: 14 }}>{k.label}</b>
                  <code style={{ fontSize: 11, color: 'var(--muted,#64748b)' }}>{k.name}</code>
                  {k.is_set
                    ? <span style={{ fontSize: 12, color: '#16a34a' }}>● đã đặt {k.masked}</span>
                    : <span style={{ fontSize: 12, color: '#dc2626' }}>● chưa đặt</span>}
                  {t && !t.loading && (
                    <span style={{ fontSize: 12, fontWeight: 700, color: t.ok ? '#16a34a' : '#dc2626' }}>
                      {t.ok ? '✅' : '❌'} {t.detail}
                    </span>
                  )}
                  {t?.loading && <span style={{ fontSize: 12 }}>⏳ đang test…</span>}
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted,#64748b)', marginBottom: 6 }}>{k.hint}</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <input type="password" placeholder="Dán key mới…" value={drafts[k.name] || ''}
                    onChange={e => setDrafts(d => ({ ...d, [k.name]: e.target.value }))}
                    style={{ flex: 1, minWidth: 200, padding: '7px 10px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)' }} />
                  <button disabled={busy === k.name} onClick={() => saveKey(k.name)} style={btn('#2563eb')}>Lưu</button>
                  <button disabled={busy === k.name} onClick={() => testKey(k.name)} style={btn('#475569')}>Test</button>
                  {k.is_set && <button disabled={busy === k.name} onClick={() => clearKey(k.name)} style={btn('#dc2626')}>Xóa</button>}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Feature toggles */}
      <div style={card}>
        <h3 style={{ margin: '0 0 12px', fontSize: 16 }}>🎚️ Công tắc tính năng</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {toggles.map(t => (
            <div key={t.name} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button disabled={busy === t.name} onClick={() => flipToggle(t)}
                style={{
                  width: 52, height: 28, borderRadius: 99, border: 'none', cursor: 'pointer',
                  background: t.enabled ? '#16a34a' : '#cbd5e1', position: 'relative', flexShrink: 0,
                }}>
                <span style={{
                  position: 'absolute', top: 3, left: t.enabled ? 27 : 3, width: 22, height: 22,
                  borderRadius: '50%', background: '#fff', transition: 'left .15s',
                }} />
              </button>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{t.label}</div>
                <code style={{ fontSize: 11, color: 'var(--muted,#64748b)' }}>{t.name}</code>
                {t.needs_restart && <span style={{ fontSize: 11, color: '#d97706', marginLeft: 8 }}>cần restart</span>}
              </div>
              <span style={{ fontSize: 13, fontWeight: 700, color: t.enabled ? '#16a34a' : '#94a3b8' }}>
                {t.enabled ? 'BẬT' : 'TẮT'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
