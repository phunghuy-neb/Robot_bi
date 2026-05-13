import { useState, useEffect } from 'react';
import { apiFetch } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import FeatureBadge from '../components/FeatureBadge.jsx';

function fmtTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch (_) { return ts; }
}

const EVENT_ICONS = {
  chat: '💬', homework: '📚', game: '🎮', safety_filter: '⚠️',
  cry: '😢', offline: '📴', battery_low: '🔋', default: '📌',
};

export default function HomePage({ user, lastWsEvent }) {
  const [weeklyState, setWeeklyState] = useState('loading');
  const [weekly, setWeekly] = useState(null);
  const [eventsState, setEventsState] = useState('loading');
  const [events, setEvents] = useState([]);
  const [todaySummary, setTodaySummary] = useState(null);
  const [alert, setAlert] = useState(null);

  const today = new Date().toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!lastWsEvent) return;
    if (lastWsEvent.type === 'safety_filter' || lastWsEvent.type === 'cry') {
      setAlert(lastWsEvent);
    }
    // Refresh events on any realtime event
    loadEvents();
  }, [lastWsEvent]);

  async function loadData() {
    loadWeekly();
    loadEvents();
    loadTodaySummary();
  }

  async function loadWeekly() {
    setWeeklyState('loading');
    const data = await apiFetch('/api/analytics/weekly');
    if (data) {
      setWeekly(data);
      setWeeklyState('data');
    } else {
      setWeeklyState('error');
    }
  }

  async function loadTodaySummary() {
    const [statusData, taskData, emotionData] = await Promise.all([
      apiFetch('/api/status'),
      apiFetch('/api/tasks'),
      apiFetch('/api/emotion/today'),
    ]);
    setTodaySummary({
      sessions: statusData?.sessions_today ?? 0,
      learningMinutes: statusData?.learning_minutes ?? 0,
      emotion: emotionData?.today?.dominant_emotion || emotionData?.dominant_emotion || '😊',
      tasksCompleted: taskData ? taskData.filter(t => t.completed_today).length : 0,
      totalTasks: taskData?.length ?? 0,
    });
  }

  async function loadEvents() {
    setEventsState('loading');
    const data = await apiFetch('/api/events?limit=5');
    const list = data?.events || [];
    if (list.length > 0) {
      setEvents(list);
      setEventsState('data');
    } else if (data) {
      setEventsState('empty');
    } else {
      setEventsState('error');
    }
  }

  return (
    <div>
      {/* Hero header */}
      <div className="home-hero">
        <div className="home-greeting">Xin chào, Mẹ yêu! 💖</div>
        <div className="home-date">{today}</div>
      </div>

      <div className="page-body">
        {/* Alert card — only visible on safety/cry events */}
        {alert && (
          <div className="alert-card">
            <div className="alert-icon">⚠️</div>
            <div>
              <div className="alert-text">Cảnh báo: {alert.type === 'cry' ? 'Bé đang khóc!' : 'Nội dung bị lọc'}</div>
              <div className="alert-sub">{alert.message || ''}</div>
            </div>
          </div>
        )}

        {/* Today summary grid */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 'var(--font-section)', fontWeight: 700, marginBottom: 10, color: 'var(--text)' }}>
            📊 Tóm tắt hôm nay
          </div>
          <div className="today-grid">
            <div className="metric-card grad-blue">
              <div className="metric-num">
                {todaySummary?.sessions ?? '—'}
                <span className="metric-online-dot" />
              </div>
              <div className="metric-label">Lượt trò chuyện</div>
            </div>
            <div className="metric-card grad-orange-pink">
              <div className="metric-num">{todaySummary?.learningMinutes ?? '—'}</div>
              <div className="metric-label">8 hoạt động</div>
            </div>
            <div className="metric-card grad-mint">
              <div className="metric-num" style={{ fontSize: 22 }}>{todaySummary?.emotion ?? '😊'}</div>
              <div className="metric-label">Vui vẻ</div>
            </div>
            <div className="metric-card grad-purple-soft">
              <div className="metric-num">
                {todaySummary ? `${todaySummary.tasksCompleted}/${todaySummary.totalTasks}` : '—'}
              </div>
              <div className="metric-label">3/5 hoàn thành</div>
            </div>
          </div>
        </div>

        {/* Weekly report */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📈 Báo cáo tuần</span>
            <button className="btn-sm secondary" onClick={loadWeekly} style={{ minHeight: 36 }}>↻</button>
          </div>
          {weeklyState === 'loading' && <SectionState state="loading" loadingText="Đang tải báo cáo tuần..." />}
          {weeklyState === 'error' && <SectionState state="error" errorText="Không tải được báo cáo tuần." onRetry={loadWeekly} />}
          {weeklyState === 'data' && weekly && (
            <div className="weekly-stat-row">
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.total_sessions ?? weekly.sessions ?? 0}</div>
                <div className="weekly-stat-label">Lượt hội thoại</div>
              </div>
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.total_minutes ?? weekly.minutes ?? 0}</div>
                <div className="weekly-stat-label">Phút học</div>
              </div>
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.homework_count ?? 0}</div>
                <div className="weekly-stat-label">Bài tập</div>
              </div>
              <div className="weekly-stat">
                <div className="weekly-stat-num">{weekly.task_completion ?? 0}%</div>
                <div className="weekly-stat-label">Hoàn thành</div>
              </div>
            </div>
          )}
        </div>

        {/* Room location — coming soon */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📍 Vị trí phòng robot</span>
            <FeatureBadge type="coming-soon" />
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>
            Tính năng định vị phòng đang được phát triển.
          </p>
        </div>

        {/* Recent events */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🔔 Hoạt động gần nhất</span>
            <button className="btn-sm secondary" onClick={loadEvents} style={{ minHeight: 36 }}>↻</button>
          </div>
          {eventsState === 'loading' && <SectionState state="loading" loadingText="Đang tải sự kiện..." />}
          {eventsState === 'error' && <SectionState state="error" errorText="Không tải được sự kiện." onRetry={loadEvents} />}
          {eventsState === 'empty' && <SectionState state="empty" emptyText="Bi đang chờ bé ra chơi! 🤖" emptyIcon="🤖" />}
          {eventsState === 'data' && (
            <div className="event-list">
              {events.map((evt, i) => (
                <div key={evt.id || i} className="event-row">
                  <div className="event-icon">
                    {EVENT_ICONS[evt.type] || EVENT_ICONS.default}
                  </div>
                  <div className="event-body">
                    <div className="event-title">{evt.message || evt.type || 'Sự kiện'}</div>
                    <div className="event-time">{fmtTime(evt.timestamp || evt.created_at)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
