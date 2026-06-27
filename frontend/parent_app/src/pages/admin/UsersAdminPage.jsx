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

  if (loading) return <div className="spinner admin-loading" />;

  return (
    <div className="admin-card compact">
      <div className="admin-toolbar">
        <span className="admin-page-note">{users.length} tài khoản</span>
        <button className="admin-btn secondary small" onClick={load}>↻ Tải lại</button>
      </div>
      <div className="admin-table-scroll">
        <table className="admin-table">
          <thead>
            <tr>
              <th className="admin-th">Tài khoản</th>
              <th className="admin-th">Gia đình</th>
              <th className="admin-th">Trạng thái</th>
              <th className="admin-th">Quyền</th>
              <th className="admin-th">Tạo lúc</th>
              <th className="admin-th">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => {
              const self = u.username === currentUsername;
              const b = busy === u.user_id;
              return (
                <tr key={u.user_id} className={b ? 'admin-row-busy' : ''}>
                  <td className="admin-td">
                    <b>{u.username}</b>{self && <span className="admin-status info"> (bạn)</span>}
                  </td>
                  <td className="admin-td">{u.family_name}</td>
                  <td className="admin-td">
                    <span className={`admin-status ${u.is_active ? 'ok' : 'bad'}`}>
                      {u.is_active ? '● Hoạt động' : '● Đã khóa'}
                    </span>
                  </td>
                  <td className="admin-td">{u.is_admin ? '👑 Admin' : 'Người dùng'}</td>
                  <td className="admin-td small admin-muted">
                    {(u.created_at || '').slice(0, 10)}
                  </td>
                  <td className="admin-td nowrap">
                    <div className="admin-inline-actions">
                      <button disabled={b || self} className={`admin-btn small ${u.is_active ? 'warning' : 'success'}`} onClick={() => toggleActive(u)}>
                        {u.is_active ? 'Khóa' : 'Mở'}
                      </button>
                      <button disabled={b || self} className="admin-btn small purple" onClick={() => toggleAdmin(u)}>
                        {u.is_admin ? 'Bỏ admin' : 'Cấp admin'}
                      </button>
                      <button disabled={b} className="admin-btn small primary" onClick={() => resetPw(u)}>Đặt lại MK</button>
                      <button disabled={b || self} className="admin-btn small danger" onClick={() => del(u)}>Xóa</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
