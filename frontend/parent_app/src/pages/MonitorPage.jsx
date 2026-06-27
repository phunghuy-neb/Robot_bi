import { useState, useEffect } from 'react';
import { apiFetch, startMomMic, stopMomMic, showToast, getToken } from '../services/api.js';
import CollapsibleSection from '../components/CollapsibleSection.jsx';
import SectionState from '../components/SectionState.jsx';

export default function MonitorPage() {
  const [camOn, setCamOn] = useState(false);
  const [camError, setCamError] = useState(false);
  const [momMicOn, setMomMicOn] = useState(false);
  const [eventsState, setEventsState] = useState('loading');
  const [events, setEvents] = useState([]);

  useEffect(() => {
    loadEvents();
  }, []);

  // Listen for external camera-stop signal (tab switch, logout, beforeunload)
  useEffect(() => {
    function handleCameraStop() { setCamOn(false); }
    window.addEventListener('bi:stopcamera', handleCameraStop);
    return () => window.removeEventListener('bi:stopcamera', handleCameraStop);
  }, []);

  async function loadEvents() {
    setEventsState('loading');
    const data = await apiFetch('/api/events?limit=20');
    const list = data?.events || [];
    if (list.length > 0) { setEvents(list); setEventsState('data'); }
    else if (data) setEventsState('empty');
    else setEventsState('error');
  }

  async function handleStartMomMic() {
    try {
      await startMomMic();
      setMomMicOn(true);
      showToast('🎤 Mẹ đang nói — Bi đang tạm dừng');
    } catch (err) {
      showToast('Không thể bật mic: ' + err.message);
    }
  }

  function handleStopMomMic() {
    stopMomMic();
    setMomMicOn(false);
    showToast('Bi đang hoạt động bình thường');
  }

  function handleToggleCam() {
    setCamOn(prev => !prev);
    setCamError(false);
  }

  async function sendMotor(vx, vy) {
    const speed = 70;
    const forward = -vy * speed;
    const turn = vx * speed;
    const left = Math.round(forward + turn);
    const right = Math.round(forward - turn);
    await apiFetch('/api/motor/joystick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ left, right }),
    });
  }

  const token = getToken();

  return (
    <div>
      <div className="page-header">
        <div className="page-title">📹 Giám sát</div>
        <div className="page-subtitle">Camera · Điều khiển · Sự kiện</div>
      </div>

      <div className="page-body">
        <CollapsibleSection
          title="📷 Camera"
          actions={
            <button className="btn-sm primary" onClick={handleToggleCam}>
              {camOn ? '⏹ Tắt Camera' : '▶ Bật Camera'}
            </button>
          }
        >
          <div className="camera-section">
            {camOn && !camError ? (
              <img
                className="camera-feed"
                src={`/api/camera?auth=${encodeURIComponent(token)}`}
                alt="Camera feed"
                onError={() => { setCamError(true); }}
              />
            ) : (
              <div className="camera-placeholder">
                <span className="cam-icon">{camError ? '❌' : '📷'}</span>
                <p>{camError ? 'Camera không khả dụng' : 'Nhấn "Bật Camera" để xem'}</p>
              </div>
            )}
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="🎤 Nói chuyện với Bi">
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 14 }}>
            Nhấn để bật micro và nói chuyện trực tiếp với robot.
          </p>
          <div className="mom-mic-controls">
            {!momMicOn ? (
              <button className="btn-action primary" onClick={handleStartMomMic}>
                🎤 Nói chuyện với Bi
              </button>
            ) : (
              <button className="btn-action danger" onClick={handleStopMomMic}>
                ⏹ Dừng — Trả lại cho Bi
              </button>
            )}
          </div>
          {momMicOn && (
            <p style={{ color: 'var(--danger)', fontSize: 14, marginTop: 10, fontWeight: 600 }}>
              🟠 Mẹ đang nói — Bi đang tạm dừng
            </p>
          )}
        </CollapsibleSection>

        <CollapsibleSection title="🕹️ Điều khiển robot">
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 14 }}>
            Điều khiển hướng di chuyển của Robot Bi.
          </p>
          <div className="motor-grid">
            <div />
            <button className="motor-btn" onClick={() => sendMotor(0, -1)} title="Tiến">⬆️</button>
            <div />
            <button className="motor-btn" onClick={() => sendMotor(-1, 0)} title="Trái">⬅️</button>
            <button className="motor-btn stop" onClick={() => sendMotor(0, 0)} title="Dừng">⏹</button>
            <button className="motor-btn" onClick={() => sendMotor(1, 0)} title="Phải">➡️</button>
            <div />
            <button className="motor-btn" onClick={() => sendMotor(0, 1)} title="Lùi">⬇️</button>
            <div />
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          title="🔔 Sự kiện gần đây"
          actions={
            <button className="btn-sm secondary" onClick={loadEvents}>↻</button>
          }
        >
          {eventsState === 'loading' && <SectionState state="loading" loadingText="Đang tải sự kiện..." />}
          {eventsState === 'error' && <SectionState state="error" errorText="Không tải được sự kiện." onRetry={loadEvents} />}
          {eventsState === 'empty' && <SectionState state="empty" emptyText="Chưa có sự kiện nào." emptyIcon="📭" />}
          {eventsState === 'data' && (
            <div className="event-list">
              {events.map((evt, i) => (
                <div key={evt.id || i} className="event-row">
                  <div className="event-icon">📌</div>
                  <div className="event-body">
                    <div className="event-title">{evt.message || evt.type || 'Sự kiện'}</div>
                    <div className="event-time">
                      {evt.timestamp ? new Date(evt.timestamp).toLocaleString('vi-VN') : ''}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CollapsibleSection>
      </div>
    </div>
  );
}
