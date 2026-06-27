import { useState, useEffect } from 'react';
import {
  getFamilyMembers, addFamilyMember, createChildAccount, removeFamilyMember,
  setMemberRole, getFamilyPermissions, setFamilyPermissions,
  getChildProfiles, showToast,
} from '../services/api.js';
import SectionState from './SectionState.jsx';

const PERM_LABELS = [
  ['child_can_monitor', 'Cho con xem Giám sát (camera)'],
  ['child_can_journal', 'Cho con xem Nhật ký'],
  ['child_can_notifications', 'Con xem Thông báo'],
  ['child_can_sleep', 'Con xem Giờ hoạt động'],
  ['child_can_safety', 'Con xem Nội dung & An toàn'],
  ['child_can_device', 'Con xem Kết nối thiết bị'],
  ['child_can_members', 'Con xem Thành viên'],
];

const ROLE_BADGE = { owner: '👑 Chủ', parent: '👨‍👩‍👧 Người lớn', child: '🧒 Con' };

export default function FamilyMembers() {
  const [state, setState] = useState('loading');
  const [members, setMembers] = useState([]);
  const [childProfiles, setChildProfiles] = useState([]);
  const [perms, setPerms] = useState({});
  const [newUsername, setNewUsername] = useState('');
  const [childPin, setChildPin] = useState('');
  const [childProfileId, setChildProfileId] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { loadAll(); }, []);

  async function loadAll() {
    setState('loading');
    const [m, profs, p] = await Promise.all([
      getFamilyMembers(), getChildProfiles(), getFamilyPermissions(),
    ]);
    if (!m) { setState('error'); return; }
    setMembers(m.members || []);
    setChildProfiles(profs || []);
    setPerms(p?.permissions || {});
    setState('data');
  }

  // Hồ sơ trẻ chưa có tài khoản con (đã gắn child_profile_id ở members)
  const linkedIds = new Set(members.filter(x => x.child_profile_id).map(x => x.child_profile_id));
  const freeProfiles = childProfiles.filter(p => !linkedIds.has(p.id));

  async function handleAddAdult(e) {
    e.preventDefault();
    const username = newUsername.trim();
    if (!username) return;
    setBusy(true);
    const r = await addFamilyMember(username, 'parent');
    setBusy(false);
    if (r?.ok) { showToast('✅ Đã thêm thành viên'); setNewUsername(''); loadAll(); }
    else showToast('❌ Không thêm được (kiểm tra username / tài khoản đã thuộc gia đình khác)');
  }

  async function handleAddChild(e) {
    e.preventDefault();
    if (!childProfileId || !/^\d{4,6}$/.test(childPin)) {
      showToast('Chọn hồ sơ và đặt PIN 4-6 chữ số');
      return;
    }
    setBusy(true);
    const r = await createChildAccount(childProfileId, childPin);
    setBusy(false);
    if (r?.ok) { showToast('✅ Đã tạo tài khoản cho bé'); setChildPin(''); setChildProfileId(''); loadAll(); }
    else showToast('❌ Không tạo được tài khoản con');
  }

  async function handleRemove(m) {
    if (!window.confirm(`Gỡ "${m.username}" khỏi gia đình?`)) return;
    const r = await removeFamilyMember(m.user_id);
    if (r?.ok) { showToast('🗑 Đã gỡ thành viên'); loadAll(); }
    else showToast('❌ Không gỡ được (không thể tự xóa hoặc owner cuối cùng)');
  }

  async function handleChangeRole(m, role) {
    const r = await setMemberRole(m.user_id, role);
    if (r?.ok) loadAll();
    else showToast('❌ Không đổi được vai trò');
  }

  async function togglePerm(key) {
    const next = { ...perms, [key]: perms[key] ? 0 : 1 };
    setPerms(next);
    const r = await setFamilyPermissions({ [key]: !perms[key] });
    if (r?.permissions) setPerms(r.permissions);
    else { showToast('❌ Lưu quyền thất bại'); loadAll(); }
  }

  return (
    <div className="settings-section">
      <div className="settings-section-title">👨‍👩‍👧 Thành viên gia đình</div>

      {state === 'loading' && <SectionState state="loading" loadingText="Đang tải thành viên..." />}
      {state === 'error' && <SectionState state="error" errorText="Không tải được." onRetry={loadAll} />}
      {state === 'data' && (
        <>
          {members.map(m => (
            <div key={m.user_id} className="profile-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div className="profile-name">{m.username}</div>
                <div className="profile-info">{ROLE_BADGE[m.role] || m.role}</div>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                {m.role !== 'child' && (
                  <select className="filter-select" value={m.role} onChange={e => handleChangeRole(m, e.target.value)}>
                    <option value="owner">Chủ</option>
                    <option value="parent">Người lớn</option>
                  </select>
                )}
                <button className="btn-sm" style={{ color: 'var(--danger,#e53e3e)', border: '1px solid var(--danger,#e53e3e)', background: 'none' }} onClick={() => handleRemove(m)}>🗑</button>
              </div>
            </div>
          ))}

          {/* Thêm người lớn (tài khoản đã đăng ký) */}
          <form onSubmit={handleAddAdult} style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <input className="form-input" placeholder="Username người lớn đã đăng ký" value={newUsername}
              onChange={e => setNewUsername(e.target.value)} style={{ flex: 1 }} />
            <button type="submit" className="btn-sm primary" disabled={busy || !newUsername.trim()}>➕ Thêm</button>
          </form>

          {/* Tạo tài khoản con từ hồ sơ trẻ */}
          <form onSubmit={handleAddChild} style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
            <div className="form-label">Tạo tài khoản cho bé (chọn hồ sơ + PIN)</div>
            {freeProfiles.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--muted)' }}>
                Mọi hồ sơ trẻ đã có tài khoản, hoặc chưa có hồ sơ (thêm ở mục Hồ sơ trẻ).
              </div>
            ) : (
              <div style={{ display: 'flex', gap: 8 }}>
                <select className="filter-select" value={childProfileId} onChange={e => setChildProfileId(e.target.value)} style={{ flex: 1 }}>
                  <option value="">— Chọn hồ sơ —</option>
                  {freeProfiles.map(p => <option key={p.id} value={p.id}>{p.avatar || '👧'} {p.name}</option>)}
                </select>
                <input className="form-input" inputMode="numeric" maxLength={6} placeholder="PIN 4-6 số"
                  value={childPin} onChange={e => setChildPin(e.target.value.replace(/\D/g, ''))} style={{ width: 110 }} />
                <button type="submit" className="btn-sm primary" disabled={busy}>Tạo</button>
              </div>
            )}
          </form>

          {/* Quyền của con */}
          <div className="form-label" style={{ marginTop: 16 }}>Con được xem gì (mặc định ẩn)</div>
          {PERM_LABELS.map(([key, label]) => (
            <div key={key} className="settings-row">
              <div className="settings-row-label">{label}</div>
              <button className={`btn-sm ${perms[key] ? 'primary' : 'secondary'}`} onClick={() => togglePerm(key)}>
                {perms[key] ? '✅ Bật' : 'Tắt'}
              </button>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
