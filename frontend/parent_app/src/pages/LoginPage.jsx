import { useState } from 'react';
import { login } from '../services/api.js';

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setError('');
    setLoading(true);
    try {
      const userData = await login(username.trim(), password);
      onLogin(userData);
    } catch (err) {
      setError(err.message || 'Sai tên đăng nhập hoặc mật khẩu.');
      setPassword('');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-box">
        <div className="login-logo">🤖</div>
        <h2 className="login-title">Robot Bi</h2>
        <p className="login-subtitle">Ứng dụng quản lý phụ huynh</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="loginUsername">Tên đăng nhập</label>
            <input
              id="loginUsername"
              type="text"
              className="form-input"
              placeholder="Nhập tên đăng nhập"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="loginPassword">Mật khẩu</label>
            <input
              id="loginPassword"
              type="password"
              className="form-input"
              placeholder="Nhập mật khẩu"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Đang đăng nhập...' : '🔐 Đăng nhập'}
          </button>

          {error && <div className="login-error">{error}</div>}
        </form>
      </div>
    </div>
  );
}
