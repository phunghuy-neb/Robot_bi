import { useState, useEffect, useCallback } from 'react';
import {
  adminListUsers, adminSetUserActive, adminSetUserAdmin,
  adminResetPassword, adminDeleteUser, showToast,
} from '../../services/api.js';

export default function UsersAdminPage({ currentUsername }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null); // user_id đang xử lý

  const load = useCallback(async () => {
    setLoading(true);
    setUsers(await adminListUsers());
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function run(userId, fn, okMsg) {
    setBusy(userId);
    const res = await fn();
    setBusy(null);
    if (res) { showToast(okMsg); load(); }
    else showToast('Thao tác thất bại');
  }

  function toggleActive(u) {
    run(u.user_id, () => adminSetUserActive(u.user_id, !u.is_active),
      u.is_active ? 'Đã khóa tài khoản' : 'Đã mở khóa');
  }
  function toggleAdmin(u) {
    run(u.user_id, () => adminSetUserAdmin(u.user_id, !u.is_admin),
      u.is_admin ? 'Đã bỏ quyền admin' : 'Đã cấp quyền admin');
  }
  function resetPw(u) {
    const pw = window.prompt(`Mật khẩu mới cho "${u.username}" (≥6 ký tự):`);
    if (!pw) return;
    if (pw.length < 6) { showToast('Mật khẩu phải ≥6 ký tự'); return; }
    run(u.user_id, () => adminResetPassword(u.user_id, pw), 'Đã đặt lại mật khẩu');
  }
  function del(u) {
    if (!window.confirm(`Xóa vĩnh viễn tài khoản "${u.username}"?`)) return;
    run(u.user_id, () => adminDeleteUser(u.user_id), 'Đã xóa tài khoản');
  }

  if (loading) return <div className="spinner" style={{ margin: 40 }} />;

  const th = { textAlign: 'left', padding: '10px 12px', fontSize: 13, color: 'var(--muted,#64748b)', borderBottom: '2px solid var(--border,#e2e8f0)' };
  const td = { padding: '10px 12px', borderBottom: '1px solid var(--border,#eef1f6)', fontSize: 14 };
  const btn = (bg) => ({ padding: '5px 10px', borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 700, color: '#fff', background: bg });

  return (
    <div style={{ background: 'var(--card,#fff)', borderRadius: 14, padding: 12, overflowX: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, padding: '0 4px' }}>
        <span style={{ fontSize: 13, color: 'var(--muted,#64748b)' }}>{users.length} tài khoản</span>
        <button onClick={load} style={btn('#475569')}>↻ Tải lại</button>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
        <thead>
          <tr>
            <th style={th}>Tài khoản</th>
            <th style={th}>Gia đình</th>
            <th style={th}>Trạng thái</th>
            <th style={th}>Quyền</th>
            <th style={th}>Tạo lúc</th>
            <th style={th}>Hành động</th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => {
            const self = u.username === currentUsername;
            const b = busy === u.user_id;
            return (
              <tr key={u.user_id} style={{ opacity: b ? 0.5 : 1 }}>
                <td style={td}>
                  <b>{u.username}</b>{self && <span style={{ fontSize: 11, color: '#2563eb' }}> (bạn)</span>}
                </td>
                <td style={td}>{u.family_name}</td>
                <td style={td}>
                  <span style={{ color: u.is_active ? '#16a34a' : '#dc2626', fontWeight: 700 }}>
                    {u.is_active ? '● Hoạt động' : '● Đã khóa'}
                  </span>
                </td>
                <td style={td}>{u.is_admin ? '👑 Admin' : 'Người dùng'}</td>
                <td style={{ ...td, fontSize: 12, color: 'var(--muted,#64748b)' }}>
                  {(u.created_at || '').slice(0, 10)}
                </td>
                <td style={{ ...td, whiteSpace: 'nowrap' }}>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    <button disabled={b || self} onClick={() => toggleActive(u)}
                      style={{ ...btn(u.is_active ? '#d97706' : '#16a34a'), opacity: self ? 0.4 : 1 }}>
                      {u.is_active ? 'Khóa' : 'Mở'}
                    </button>
                    <button disabled={b || self} onClick={() => toggleAdmin(u)}
                      style={{ ...btn('#7c3aed'), opacity: self ? 0.4 : 1 }}>
                      {u.is_admin ? 'Bỏ admin' : 'Cấp admin'}
                    </button>
                    <button disabled={b} onClick={() => resetPw(u)} style={btn('#2563eb')}>Đặt lại MK</button>
                    <button disabled={b || self} onClick={() => del(u)}
                      style={{ ...btn('#dc2626'), opacity: self ? 0.4 : 1 }}>Xóa</button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
