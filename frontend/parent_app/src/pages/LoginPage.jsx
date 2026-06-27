import { useState } from 'react';
import { login, childLogin, getChildProfilesPublic } from '../services/api.js';

export default function LoginPage({ onLogin }) {
  const [mode, setMode] = useState('parent'); // 'parent' | 'child'
  // Parent
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  // Child
  const [familyCode, setFamilyCode] = useState(() => localStorage.getItem('bi_child_family') || '');
  const [childStep, setChildStep] = useState('family'); // 'family' | 'pick' | 'pin'
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [pin, setPin] = useState('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleParentSubmit(e) {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setError(''); setLoading(true);
    try {
      onLogin(await login(username.trim(), password));
    } catch (err) {
      setError(err.message || 'Sai tên đăng nhập hoặc mật khẩu.');
      setPassword('');
    } finally { setLoading(false); }
  }

  async function handleLoadProfiles(e) {
    e.preventDefault();
    const fam = familyCode.trim();
    if (!fam) return;
    setError(''); setLoading(true);
    try {
      const list = await getChildProfilesPublic(fam);
      if (!list.length) {
        setError('Không tìm thấy hồ sơ trẻ cho mã gia đình này.');
        return;
      }
      localStorage.setItem('bi_child_family', fam);
      setProfiles(list);
      setChildStep('pick');
    } finally { setLoading(false); }
  }

  async function handleChildLogin(e) {
    e.preventDefault();
    if (!selectedProfile || pin.length < 4) return;
    setError(''); setLoading(true);
    try {
      const userData = await childLogin({
        family: familyCode.trim(),
        childProfileId: selectedProfile.id,
        pin,
      });
      onLogin(userData);
    } catch (err) {
      setError(err.message || 'PIN không đúng.');
      setPin('');
    } finally { setLoading(false); }
  }

  function switchMode(next) {
    setError(''); setPin(''); setSelectedProfile(null);
    setChildStep('family'); setMode(next);
  }

  return (
    <div className="login-page">
      <div className="login-box">
        <div className="login-logo">🤖</div>
        <h2 className="login-title">Robot Bi</h2>
        <p className="login-subtitle">
          {mode === 'parent' ? 'Ứng dụng quản lý phụ huynh' : 'Đăng nhập cho bé'}
        </p>

        {mode === 'parent' ? (
          <form onSubmit={handleParentSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="loginUsername">Tên đăng nhập</label>
              <input id="loginUsername" type="text" className="form-input" placeholder="Nhập tên đăng nhập"
                value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" autoFocus />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="loginPassword">Mật khẩu</label>
              <input id="loginPassword" type="password" className="form-input" placeholder="Nhập mật khẩu"
                value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" />
            </div>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Đang đăng nhập...' : '🔐 Đăng nhập'}
            </button>
          </form>
        ) : childStep === 'family' ? (
          <form onSubmit={handleLoadProfiles}>
            <div className="form-group">
              <label className="form-label" htmlFor="famCode">Mã gia đình</label>
              <input id="famCode" type="text" className="form-input" placeholder="Hỏi bố mẹ mã gia đình"
                value={familyCode} onChange={e => setFamilyCode(e.target.value)} autoFocus />
            </div>
            <button type="submit" className="btn-primary" disabled={loading || !familyCode.trim()}>
              {loading ? 'Đang tải...' : 'Tiếp tục →'}
            </button>
          </form>
        ) : childStep === 'pick' ? (
          <div>
            <p className="form-label" style={{ textAlign: 'center', marginBottom: 12 }}>Chọn hồ sơ của con</p>
            <div className="child-login-grid">
              {profiles.map(p => (
                <button key={p.id} type="button" className="child-login-card"
                  onClick={() => { setSelectedProfile(p); setChildStep('pin'); }}>
                  <span className="child-login-avatar">{p.avatar || '👧'}</span>
                  <span>{p.name}</span>
                </button>
              ))}
            </div>
            <button type="button" className="btn-back" onClick={() => setChildStep('family')}>← Đổi mã gia đình</button>
          </div>
        ) : (
          <form onSubmit={handleChildLogin}>
            <p className="form-label" style={{ textAlign: 'center', marginBottom: 12 }}>
              {selectedProfile?.avatar || '👧'} {selectedProfile?.name} — nhập mã PIN
            </p>
            <div className="form-group">
              <input type="password" inputMode="numeric" pattern="\d*" maxLength={6}
                className="form-input" style={{ textAlign: 'center', fontSize: 24, letterSpacing: 8 }}
                placeholder="••••" value={pin}
                onChange={e => setPin(e.target.value.replace(/\D/g, ''))} autoFocus />
            </div>
            <button type="submit" className="btn-primary" disabled={loading || pin.length < 4}>
              {loading ? 'Đang vào...' : '🚀 Vào học'}
            </button>
            <button type="button" className="btn-back" onClick={() => { setSelectedProfile(null); setPin(''); setChildStep('pick'); }}>
              ← Chọn hồ sơ khác
            </button>
          </form>
        )}

        {error && <div className="login-error">{error}</div>}

        <button type="button" className="login-mode-switch"
          onClick={() => switchMode(mode === 'parent' ? 'child' : 'parent')}>
          {mode === 'parent' ? '🧒 Đăng nhập cho bé' : '👨‍👩‍👧 Đăng nhập phụ huynh'}
        </button>
      </div>
    </div>
  );
}
