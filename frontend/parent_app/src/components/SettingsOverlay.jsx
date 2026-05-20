import { useState, useEffect } from 'react';
import {
  apiFetch,
  getChildProfiles,
  getSystemLogs,
  showToast,
} from '../services/api.js';
import SectionState from './SectionState.jsx';
import FeatureBadge from './FeatureBadge.jsx';

export default function SettingsOverlay({ isAdmin, onClose }) {
  const [childProfiles, setChildProfiles] = useState([]);
  const [childLoading, setChildLoading] = useState(true);
  const [persona, setPersona] = useState(null);
  const [personaLoading, setPersonaLoading] = useState(false);
  const [families, setFamilies] = useState([]);
  const [familiesState, setFamiliesState] = useState('idle');
  const [systemLogs, setSystemLogs] = useState([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [adminExpanded, setAdminExpanded] = useState(false);

  // Sleep schedule state (UI only, coming-soon)
  const [sleepStart, setSleepStart] = useState('21:00');
  const [sleepEnd, setSleepEnd] = useState('06:30');
  // Time limit state
  const [dailyLimit, setDailyLimit] = useState(60);
  // Age filter state
  const [ageFilter, setAgeFilter] = useState('6-9');

  useEffect(() => {
    loadChildProfiles();
  }, []);

  async function loadChildProfiles() {
    setChildLoading(true);
    const data = await getChildProfiles();
    setChildProfiles(data || []);
    setChildLoading(false);
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
            <FeatureBadge type="mock-data" />
          </div>
          {childLoading ? (
            <SectionState state="loading" loadingText="Đang tải hồ sơ..." />
          ) : childProfiles.length === 0 ? (
            <SectionState state="empty" emptyText="Chưa có hồ sơ trẻ." emptyIcon="👧" />
          ) : (
            childProfiles.map(child => (
              <div key={child.id} className="profile-card">
                <div className="profile-avatar">{child.avatar}</div>
                <div>
                  <div className="profile-name">{child.name}</div>
                  <div className="profile-info">
                    {child.age} tuổi · {child.grade} · Giới hạn {child.dailyLimit} phút/ngày
                  </div>
                </div>
              </div>
            ))
          )}
          <button
            className="btn-outline"
            style={{ marginTop: 10, width: '100%' }}
            onClick={() => showToast('Quản lý hồ sơ: Sắp hỗ trợ')}
          >
            ➕ Thêm hồ sơ
          </button>
        </div>

        {/* Section 2: Thông báo & Nhắc nhở */}
        <div className="settings-section">
          <div className="settings-section-title">
            🔔 Thông báo & Nhắc nhở
            <FeatureBadge type="coming-soon" />
          </div>
          <div className="settings-row">
            <div>
              <div className="settings-row-label">Thông báo hoạt động bất thường</div>
              <div className="settings-row-sub">Nhận cảnh báo khi bé khóc hoặc có sự kiện bất thường</div>
            </div>
            <button className="btn-sm secondary" onClick={() => showToast('Thông báo: Sắp hỗ trợ')}>
              Bật/Tắt
            </button>
          </div>
          <div className="settings-row">
            <div>
              <div className="settings-row-label">Nhắc nhở nhiệm vụ</div>
              <div className="settings-row-sub">Thông báo khi Bi nhắc bé làm nhiệm vụ</div>
            </div>
            <button className="btn-sm secondary" onClick={() => showToast('Nhắc nhở: Sắp hỗ trợ')}>
              Bật/Tắt
            </button>
          </div>
        </div>

        {/* Section 3: Giờ hoạt động robot */}
        <div className="settings-section">
          <div className="settings-section-title">
            ⏰ Giờ hoạt động robot
            <FeatureBadge type="coming-soon" />
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
            onClick={() => showToast('Giờ hoạt động: Sắp hỗ trợ')}
          >
            💾 Lưu lịch
          </button>
        </div>

        {/* Section 4: Nội dung & An toàn */}
        <div className="settings-section">
          <div className="settings-section-title">
            🛡️ Nội dung & An toàn
            <FeatureBadge type="coming-soon" />
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
            onClick={() => showToast('Nội dung & An toàn: Sắp hỗ trợ')}
          >
            💾 Lưu cài đặt
          </button>
        </div>

        {/* Section 5: Kết nối thiết bị / QR */}
        <div className="settings-section">
          <div className="settings-section-title">
            📡 Kết nối thiết bị
            <FeatureBadge type="coming-soon" />
          </div>
          <div
            style={{
              width: 120, height: 120, background: 'var(--bg)', border: '2px dashed var(--border)',
              borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 40, marginBottom: 10,
            }}
          >
            📱
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>
            Mã QR kết nối thiết bị — Sắp hỗ trợ
          </p>
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
                    <FeatureBadge type="no-backend" />
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
