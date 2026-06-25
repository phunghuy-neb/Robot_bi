import { useState, useEffect } from 'react';
import {
  apiFetch,
  getChildProfiles,
  addChildProfile,
  deleteChildProfile,
  getSystemLogs,
  getSleepSchedule,
  saveSleepSchedule,
  getTimeLimits,
  saveTimeLimits,
  getAgeFilter,
  saveAgeFilter,
  getNotificationSettings,
  savePushSettings,
  getDeviceConnectionUrl,
  showToast,
} from '../services/api.js';
import SectionState from './SectionState.jsx';
import FeatureBadge from './FeatureBadge.jsx';

export default function SettingsOverlay({ isAdmin, onClose }) {
  const [childProfiles, setChildProfiles] = useState([]);
  const [childLoading, setChildLoading] = useState(true);
  const [showAddChild, setShowAddChild] = useState(false);
  const [newChildName, setNewChildName] = useState('');
  const [newChildAge, setNewChildAge] = useState('');
  const [newChildGrade, setNewChildGrade] = useState('');
  const [newChildAvatar, setNewChildAvatar] = useState('👧');
  const [addingChild, setAddingChild] = useState(false);
  const [persona, setPersona] = useState(null);
  const [personaLoading, setPersonaLoading] = useState(false);
  const [families, setFamilies] = useState([]);
  const [familiesState, setFamiliesState] = useState('idle');
  const [systemLogs, setSystemLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [adminExpanded, setAdminExpanded] = useState(false);

  // Sleep schedule state
  const [sleepStart, setSleepStart] = useState('21:00');
  const [sleepEnd, setSleepEnd] = useState('06:30');
  const [sleepSaving, setSleepSaving] = useState(false);
  // Time limit state
  const [dailyLimit, setDailyLimit] = useState(60);
  const [limitSaving, setLimitSaving] = useState(false);
  // Age filter state
  const [ageFilter, setAgeFilter] = useState('6-9');
  const [ageFilterSaving, setAgeFilterSaving] = useState(false);
  // Notification state
  const [notifEnabled, setNotifEnabled] = useState(true);
  const [notifTaskReminder, setNotifTaskReminder] = useState(true);
  const [notifSaving, setNotifSaving] = useState(false);
  // Device connection URL
  const [deviceUrl, setDeviceUrl] = useState(null);
  const [deviceUrlLoading, setDeviceUrlLoading] = useState(false);

  useEffect(() => {
    loadChildProfiles();
    loadSettingsFromBackend();
    loadNotificationSettings();
  }, []);

  async function loadChildProfiles() {
    setChildLoading(true);
    const data = await getChildProfiles();
    setChildProfiles(data || []);
    setChildLoading(false);
  }

  async function handleAddChild(e) {
    e.preventDefault();
    const name = newChildName.trim();
    if (!name) return;
    setAddingChild(true);
    const result = await addChildProfile({
      name,
      age: newChildAge ? parseInt(newChildAge, 10) : undefined,
      grade: newChildGrade || undefined,
      avatar: newChildAvatar || '👧',
    });
    setAddingChild(false);
    if (result?.child_id || result?.ok) {
      showToast(`✅ Đã thêm hồ sơ: ${name}`);
      setNewChildName(''); setNewChildAge(''); setNewChildGrade(''); setNewChildAvatar('👧');
      setShowAddChild(false);
      loadChildProfiles();
    } else {
      showToast('❌ Thêm hồ sơ thất bại, thử lại sau');
    }
  }

  async function handleDeleteChild(child) {
    if (!window.confirm(`Xoá hồ sơ "${child.name}"?`)) return;
    const result = await deleteChildProfile(child.id);
    if (result?.ok) {
      showToast(`🗑 Đã xoá: ${child.name}`);
      loadChildProfiles();
    } else {
      showToast('❌ Xoá thất bại');
    }
  }

  async function loadSettingsFromBackend() {
    try {
      const [sleepData, limitData, ageData] = await Promise.all([
        getSleepSchedule(),
        getTimeLimits(),
        getAgeFilter(),
      ]);
      if (sleepData?.settings) {
        const s = sleepData.settings;
        if (s.start_time) setSleepStart(s.start_time);
        if (s.end_time) setSleepEnd(s.end_time);
      }
      if (limitData?.settings) {
        const lm = limitData.settings;
        if (lm.daily_limit_minutes) setDailyLimit(lm.daily_limit_minutes);
      }
      if (ageData?.settings) {
        const af = ageData.settings;
        if (af.min_age != null && af.max_age != null) {
          setAgeFilter(`${af.min_age}-${af.max_age}`);
        }
      }
    } catch (_) {}
  }

  async function loadNotificationSettings() {
    try {
      const data = await getNotificationSettings();
      if (data?.settings) {
        setNotifEnabled(data.settings.enabled !== false);
        setNotifTaskReminder(data.settings.event_types?.chat !== false);
      }
    } catch (_) {}
  }

  async function handleSaveNotifications() {
    setNotifSaving(true);
    try {
      const result = await savePushSettings({
        enabled: notifEnabled,
        event_types: { chat: notifTaskReminder, cry: notifEnabled, homework: notifTaskReminder },
        channels: { in_app: true, web_push: false },
      });
      if (result?.ok) {
        showToast('✅ Đã lưu cài đặt thông báo');
      } else {
        showToast('❌ Lưu thất bại, thử lại sau');
      }
    } catch (_) {
      showToast('❌ Lỗi kết nối');
    } finally {
      setNotifSaving(false);
    }
  }

  async function handleLoadDeviceUrl() {
    setDeviceUrlLoading(true);
    try {
      const qr = await getDeviceConnectionUrl('parent_app');
      if (qr?.payload_url) {
        setDeviceUrl(qr.payload_url);
      } else {
        showToast('❌ Không tạo được mã kết nối');
      }
    } catch (_) {
      showToast('❌ Lỗi kết nối');
    } finally {
      setDeviceUrlLoading(false);
    }
  }

  async function handleSaveSleep() {
    setSleepSaving(true);
    try {
      const result = await saveSleepSchedule({
        enabled: true,
        start_time: sleepStart,
        end_time: sleepEnd,
        days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
        timezone: 'Asia/Ho_Chi_Minh',
      });
      if (result?.ok) {
        showToast('✅ Đã lưu lịch hoạt động robot');
      } else {
        showToast('❌ Lưu thất bại, thử lại sau');
      }
    } catch (_) {
      showToast('❌ Lỗi kết nối');
    } finally {
      setSleepSaving(false);
    }
  }

  async function handleSaveTimeLimits() {
    setLimitSaving(true);
    try {
      const result = await saveTimeLimits({
        enabled: true,
        daily_limit_minutes: dailyLimit,
        warning_minutes: Math.min(10, dailyLimit),
        reset_time: '00:00',
      });
      if (result?.ok) {
        showToast('✅ Đã lưu giới hạn thời gian');
      } else {
        showToast('❌ Lưu thất bại, thử lại sau');
      }
    } catch (_) {
      showToast('❌ Lỗi kết nối');
    } finally {
      setLimitSaving(false);
    }
  }

  async function handleSaveAgeFilter() {
    setAgeFilterSaving(true);
    try {
      const [minStr, maxStr] = ageFilter.split('-');
      const minAge = parseInt(minStr, 10);
      const maxAge = parseInt(maxStr, 10);
      const result = await saveAgeFilter({
        enabled: true,
        min_age: minAge,
        max_age: maxAge,
        blocked_topics: [],
        allowed_topics: [],
        strict_mode: true,
      });
      if (result?.ok) {
        showToast('✅ Đã lưu bộ lọc độ tuổi');
      } else {
        showToast('❌ Lưu thất bại, thử lại sau');
      }
    } catch (_) {
      showToast('❌ Lỗi kết nối');
    } finally {
      setAgeFilterSaving(false);
    }
  }

  async function loadPersona() {
    setPersonaLoading(true);
    const data = await apiFetch('/api/persona');
    setPersona(data?.persona || data);
    setPersonaLoading(false);
  }

  async function loadFamilies() {
    setFamiliesState('loading');
    const data = await apiFetch('/api/admin/families');
    if (data) {
      setFamilies(Array.isArray(data) ? data : data.families || []);
      setFamiliesState('data');
    } else {
      setFamiliesState('error');
    }
  }

  async function loadSystemLogs() {
    setLogsLoading(true);
    const data = await getSystemLogs();
    setSystemLogs(data || []);
    setLogsLoading(false);
  }

  function handleExpandAdmin() {
    if (!adminExpanded) {
      setAdminExpanded(true);
      loadPersona();
      loadFamilies();
      loadSystemLogs();
    } else {
      setAdminExpanded(false);
    }
  }

  return (
    <div className="settings-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="settings-panel">
        {/* Header */}
        <div className="settings-header">
          <span className="settings-title">⚙️ Cài đặt</span>
          <button className="settings-close" onClick={onClose} title="Đóng">✕</button>
        </div>

        {/* Section 1: Hồ sơ trẻ */}
        <div className="settings-section">
          <div className="settings-section-title">
            👧 Hồ sơ trẻ
          </div>
          {childLoading ? (
            <SectionState state="loading" loadingText="Đang tải hồ sơ..." />
          ) : childProfiles.length === 0 ? (
            <SectionState state="empty" emptyText="Chưa có hồ sơ trẻ." emptyIcon="👧" />
          ) : (
            childProfiles.map(child => (
              <div key={child.id} className="profile-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div className="profile-avatar">{child.avatar}</div>
                  <div>
                    <div className="profile-name">{child.name}</div>
                    <div className="profile-info">
                      {child.age ? `${child.age} tuổi` : ''}{child.grade ? ` · ${child.grade}` : ''}
                    </div>
                  </div>
                </div>
                <button
                  className="btn-sm"
                  style={{ background: 'none', color: 'var(--danger, #e53e3e)', border: '1px solid var(--danger, #e53e3e)', minWidth: 32 }}
                  onClick={() => handleDeleteChild(child)}
                  title="Xoá hồ sơ"
                >
                  🗑
                </button>
              </div>
            ))
          )}
          <button
            className="btn-outline"
            style={{ marginTop: 10, width: '100%' }}
            onClick={() => setShowAddChild(v => !v)}
          >
            {showAddChild ? '✖ Đóng' : '➕ Thêm hồ sơ'}
          </button>
          {showAddChild && (
            <form onSubmit={handleAddChild} style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <input
                className="form-input"
                placeholder="Tên bé *"
                value={newChildName}
                onChange={e => setNewChildName(e.target.value)}
                maxLength={80}
                required
              />
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  className="form-input"
                  placeholder="Tuổi"
                  type="number"
                  min="1" max="18"
                  value={newChildAge}
                  onChange={e => setNewChildAge(e.target.value)}
                  style={{ flex: 1 }}
                />
                <input
                  className="form-input"
                  placeholder="Lớp (vd: 1)"
                  value={newChildGrade}
                  onChange={e => setNewChildGrade(e.target.value)}
                  maxLength={40}
                  style={{ flex: 1 }}
                />
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{ fontSize: 13, color: 'var(--muted)' }}>Avatar:</span>
                {['👧', '👦', '🧒', '👶', '🐱', '🐶'].map(emoji => (
                  <button
                    key={emoji}
                    type="button"
                    onClick={() => setNewChildAvatar(emoji)}
                    style={{
                      fontSize: 22, background: 'none', border: newChildAvatar === emoji ? '2px solid var(--primary)' : '2px solid transparent',
                      borderRadius: 8, cursor: 'pointer', padding: 2,
                    }}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
              <button type="submit" className="btn-sm primary" disabled={addingChild || !newChildName.trim()}>
                {addingChild ? '⏳ Đang thêm...' : '✅ Lưu hồ sơ'}
              </button>
            </form>
          )}
        </div>

        {/* Section 2: Thông báo & Nhắc nhở */}
        <div className="settings-section">
          <div className="settings-section-title">
            🔔 Thông báo & Nhắc nhở
          </div>
          <div className="settings-row">
            <div>
              <div className="settings-row-label">Thông báo hoạt động bất thường</div>
              <div className="settings-row-sub">Nhận cảnh báo khi bé khóc hoặc có sự kiện bất thường</div>
            </div>
            <button
              className={`btn-sm ${notifEnabled ? 'primary' : 'secondary'}`}
              onClick={() => setNotifEnabled(v => !v)}
            >
              {notifEnabled ? '✅ Bật' : 'Tắt'}
            </button>
          </div>
          <div className="settings-row">
            <div>
              <div className="settings-row-label">Nhắc nhở nhiệm vụ</div>
              <div className="settings-row-sub">Thông báo khi Bi nhắc bé làm nhiệm vụ</div>
            </div>
            <button
              className={`btn-sm ${notifTaskReminder ? 'primary' : 'secondary'}`}
              onClick={() => setNotifTaskReminder(v => !v)}
            >
              {notifTaskReminder ? '✅ Bật' : 'Tắt'}
            </button>
          </div>
          <button
            className="btn-outline"
            style={{ marginTop: 10 }}
            onClick={handleSaveNotifications}
            disabled={notifSaving}
          >
            {notifSaving ? '⏳ Đang lưu...' : '💾 Lưu thông báo'}
          </button>
        </div>

        {/* Section 3: Giờ hoạt động robot */}
        <div className="settings-section">
          <div className="settings-section-title">
            ⏰ Giờ hoạt động robot
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
            <div>
              <div className="form-label">Giờ tắt (ngủ)</div>
              <input
                type="time"
                className="form-input"
                style={{ width: 'auto' }}
                value={sleepStart}
                onChange={e => setSleepStart(e.target.value)}
              />
            </div>
            <div>
              <div className="form-label">Giờ bật (thức)</div>
              <input
                type="time"
                className="form-input"
                style={{ width: 'auto' }}
                value={sleepEnd}
                onChange={e => setSleepEnd(e.target.value)}
              />
            </div>
          </div>
          <button
            className="btn-outline"
            onClick={handleSaveSleep}
            disabled={sleepSaving}
          >
            {sleepSaving ? '⏳ Đang lưu...' : '💾 Lưu lịch'}
          </button>
        </div>

        {/* Section 4: Nội dung & An toàn */}
        <div className="settings-section">
          <div className="settings-section-title">
            🛡️ Nội dung & An toàn
          </div>
          <div style={{ marginBottom: 12 }}>
            <div className="form-label">Giới hạn thời gian mỗi ngày: {dailyLimit} phút</div>
            <input
              type="range"
              min={15}
              max={180}
              step={15}
              value={dailyLimit}
              onChange={e => setDailyLimit(Number(e.target.value))}
              style={{ width: '100%', marginTop: 8 }}
            />
            <button
              className="btn-sm secondary"
              style={{ marginTop: 8 }}
              onClick={handleSaveTimeLimits}
              disabled={limitSaving}
            >
              {limitSaving ? '⏳ Đang lưu...' : '💾 Lưu giới hạn'}
            </button>
          </div>
          <div style={{ marginBottom: 12 }}>
            <div className="form-label">Bộ lọc chủ đề theo tuổi</div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
              {['3-5', '5-7', '6-9', '8-12'].map(range => (
                <button
                  key={range}
                  className={`btn-sm ${ageFilter === range ? 'primary' : 'secondary'}`}
                  onClick={() => setAgeFilter(range)}
                >
                  {range} tuổi
                </button>
              ))}
            </div>
          </div>
          <button
            className="btn-outline"
            onClick={handleSaveAgeFilter}
            disabled={ageFilterSaving}
          >
            {ageFilterSaving ? '⏳ Đang lưu...' : '💾 Lưu cài đặt'}
          </button>
        </div>

        {/* Section 5: Kết nối thiết bị / QR */}
        <div className="settings-section">
          <div className="settings-section-title">
            📡 Kết nối thiết bị
          </div>
          {deviceUrl ? (
            <div style={{ background: 'var(--bg)', border: '1.5px solid var(--border)', borderRadius: 10, padding: 12, marginBottom: 10, wordBreak: 'break-all' }}>
              <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 6, color: 'var(--primary)' }}>🔗 URL kết nối:</div>
              <div style={{ fontSize: 12, color: 'var(--text)', lineHeight: 1.5 }}>{deviceUrl}</div>
              <button
                className="btn-sm primary"
                style={{ marginTop: 8 }}
                onClick={() => { navigator.clipboard?.writeText(deviceUrl); showToast('✅ Đã sao chép URL'); }}
              >
                📋 Sao chép
              </button>
            </div>
          ) : (
            <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 10 }}>
              Nhấn để tạo mã kết nối thiết bị
            </p>
          )}
          <button
            className="btn-outline"
            onClick={handleLoadDeviceUrl}
            disabled={deviceUrlLoading}
          >
            {deviceUrlLoading ? '⏳ Đang tạo...' : deviceUrl ? '🔄 Làm mới mã' : '🔗 Tạo mã kết nối'}
          </button>
        </div>

        {/* Section 6: Chế độ kỹ thuật — admin only */}
        {isAdmin && (
          <div className="settings-section">
            <button
              className="settings-section-title"
              style={{ background: 'none', border: 'none', cursor: 'pointer', width: '100%', textAlign: 'left', padding: 0 }}
              onClick={handleExpandAdmin}
            >
              🔧 Chế độ kỹ thuật / Quản trị
              <span style={{ marginLeft: 8, color: 'var(--muted)', fontSize: 14 }}>
                {adminExpanded ? '▲' : '▼'}
              </span>
            </button>

            {adminExpanded && (
              <div style={{ marginTop: 14 }}>
                {/* System logs */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                    📋 Nhật ký hệ thống
                  </div>
                  {logsLoading ? (
                    <SectionState state="loading" loadingText="Đang tải nhật ký..." />
                  ) : systemLogs.length === 0 ? (
                    <SectionState state="empty" emptyText="Không có nhật ký." emptyIcon="📋" />
                  ) : (
                    <div style={{ background: '#0f172a', borderRadius: 12, padding: 12, overflow: 'auto', maxHeight: 240 }}>
                      {systemLogs.map(log => (
                        <div key={log.id} className="log-item">
                          <span className={`log-level ${log.level}`}>[{log.level}]</span>
                          <span className="log-msg">{log.message}</span>
                          <span className="log-time" style={{ color: '#64748b' }}>
                            {log.source}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Persona settings (real API) */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>🤖 Cài đặt Persona</div>
                  {personaLoading ? (
                    <SectionState state="loading" loadingText="Đang tải persona..." />
                  ) : persona ? (
                    <div className="profile-card">
                      <div className="profile-avatar">🤖</div>
                      <div>
                        <div className="profile-name">{persona.name || 'Bi'}</div>
                        <div className="profile-info">Giọng: {persona.voice || '—'}</div>
                      </div>
                    </div>
                  ) : (
                    <SectionState state="error" errorText="Không tải được persona." onRetry={loadPersona} />
                  )}
                </div>

                {/* Admin families (real API) */}
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>👨‍👩‍👧‍👦 Quản lý gia đình</div>
                  {familiesState === 'idle' && null}
                  {familiesState === 'loading' && <SectionState state="loading" loadingText="Đang tải danh sách gia đình..." />}
                  {familiesState === 'error' && <SectionState state="error" errorText="Không tải được danh sách gia đình." onRetry={loadFamilies} />}
                  {familiesState === 'data' && (
                    families.length === 0 ? (
                      <SectionState state="empty" emptyText="Chưa có gia đình nào." emptyIcon="👨‍👩‍👧" />
                    ) : (
                      families.map((f, i) => (
                        <div key={f.family_id || i} className="profile-card">
                          <div className="profile-avatar">👨‍👩‍👧</div>
                          <div>
                            <div className="profile-name">{f.display_name || f.family_id}</div>
                            <div className="profile-info">ID: {f.family_id}</div>
                          </div>
                        </div>
                      ))
                    )
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
