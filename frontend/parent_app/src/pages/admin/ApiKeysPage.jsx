import { useState, useEffect, useCallback } from 'react';
import {
  adminGetKeys, adminSetKey, adminClearKey, adminTestKey,
  adminGetToggles, adminSetToggle, showToast,
} from '../../services/api.js';
import Toggle from '../../components/admin/Toggle.jsx';

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

  if (loading) return <div className="spinner admin-loading" />;

  return (
    <div>
      <div className="admin-card warning">
        ⚠️ Chỉ quản lý <b>key public</b> ở đây. Key LLM (Gemini/Groq/Cerebras…), JWT, mật khẩu
        admin <b>không hiển thị và không sửa</b> qua web — chỉ sửa trực tiếp trong <code>.env</code>.
      </div>

      <div className="admin-card">
        <h3 className="admin-section-title">🔑 API key public</h3>
        <div className="admin-stack">
          {keys.map(k => {
            const t = tests[k.name];
            return (
              <div key={k.name} className="admin-list-item">
                <div className="admin-row">
                  <b>{k.label}</b>
                  <code className="admin-code">{k.name}</code>
                  {k.is_set
                    ? <span className="admin-status ok">● đã đặt {k.masked}</span>
                    : <span className="admin-status bad">● chưa đặt</span>}
                  {t && !t.loading && (
                    <span className={`admin-status ${t.ok ? 'ok' : 'bad'}`}>
                      {t.ok ? '✅' : '❌'} {t.detail}
                    </span>
                  )}
                  {t?.loading && <span className="admin-status muted">⏳ đang test…</span>}
                </div>
                <div className="admin-detail">{k.hint}</div>
                <div className="admin-row fill">
                  <input
                    className="admin-input compact grow"
                    type="password"
                    placeholder="Dán key mới…"
                    value={drafts[k.name] || ''}
                    onChange={e => setDrafts(d => ({ ...d, [k.name]: e.target.value }))}
                  />
                  <button disabled={busy === k.name} className="admin-btn primary small" onClick={() => saveKey(k.name)}>Lưu</button>
                  <button disabled={busy === k.name} className="admin-btn secondary small" onClick={() => testKey(k.name)}>Test</button>
                  {k.is_set && <button disabled={busy === k.name} className="admin-btn danger small" onClick={() => clearKey(k.name)}>Xóa</button>}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="admin-card">
        <h3 className="admin-section-title">🎚️ Công tắc tính năng</h3>
        <div className="admin-stack">
          {toggles.map(t => (
            <div key={t.name} className="admin-row">
              <Toggle checked={!!t.enabled} disabled={busy === t.name} label={t.label} onChange={() => flipToggle(t)} />
              <div className="admin-grow">
                <div><b>{t.label}</b></div>
                <code className="admin-code">{t.name}</code>
                {t.needs_restart && <span className="admin-status warn"> cần restart</span>}
              </div>
              <span className={`admin-status ${t.enabled ? 'ok' : 'muted'}`}>
                {t.enabled ? 'BẬT' : 'TẮT'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
