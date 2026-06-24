import { useState, useEffect } from 'react';
import { getConversations, getConversation, getMonthlyEmotions, exportReport, showToast } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import FeatureBadge from '../components/FeatureBadge.jsx';
import SpecialMemories from '../components/SpecialMemories.jsx';

function fmtTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch (_) { return ts; }
}

export default function JournalPage() {
  const [filterType, setFilterType] = useState('all');
  const [filterDate, setFilterDate] = useState('');
  const [threadsState, setThreadsState] = useState('loading');
  const [threads, setThreads] = useState([]);
  const [selectedThread, setSelectedThread] = useState(null);
  const [threadDetail, setThreadDetail] = useState(null);
  const [threadLoading, setThreadLoading] = useState(false);
  const [emotionData, setEmotionData] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadThreads();
    loadEmotions();
  }, []);

  async function loadThreads() {
    setThreadsState('loading');
    setSelectedThread(null);
    setThreadDetail(null);
    const data = await getConversations(20);
    const list = data?.conversations || [];
    if (list.length > 0) {
      setThreads(list);
      setThreadsState('data');
    } else if (data) {
      setThreadsState('empty');
    } else {
      setThreadsState('error');
    }
  }

  async function handleExport(format = 'csv') {
    setExporting(true);
    try {
      const result = await exportReport(format);
      if (!result?.blob) {
        showToast('❌ Xuất báo cáo thất bại');
        return;
      }
      const url = URL.createObjectURL(result.blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('✅ Đã tải báo cáo ' + format.toUpperCase());
    } catch (_) {
      showToast('❌ Lỗi kết nối');
    } finally {
      setExporting(false);
    }
  }

  async function loadEmotions() {
    const data = await getMonthlyEmotions();
    if (data) setEmotionData(data);
  }

  async function openThread(id) {
    setThreadLoading(true);
    setSelectedThread(id);
    const data = await getConversation(id);
    setThreadDetail(data);
    setThreadLoading(false);
  }

  // Client-side filter
  const filteredThreads = threads.filter(c => {
    if (filterDate) {
      const d = new Date(c.started_at);
      const fd = new Date(filterDate);
      if (d.toDateString() !== fd.toDateString()) return false;
    }
    if (filterType !== 'all') {
      if (filterType === 'homework' && !c.is_homework) return false;
    }
    return true;
  });

  return (
    <div>
      <div className="page-header">
        <div className="page-title">📔 Nhật ký</div>
        <div className="page-subtitle">Lịch sử hoạt động và hội thoại</div>
      </div>

      <div className="page-body">
        {/* Kỷ niệm đặc biệt (Stage 2) */}
        <SpecialMemories />

        {/* Filter bar */}
        <div className="filter-bar">
          <div className="pill-tabs">
            {[['all', 'Tất cả'], ['chat', 'Trò chuyện'], ['homework', 'Bài tập']].map(([val, label]) => (
              <button
                key={val}
                className={`pill-tab${filterType === val ? ' active' : ''}`}
                onClick={() => setFilterType(val)}
              >
                {label}
              </button>
            ))}
          </div>

          <input
            type="date"
            className="filter-date"
            value={filterDate}
            onChange={e => setFilterDate(e.target.value)}
          />

          <button
            className="btn-sm secondary"
            onClick={() => { setFilterType('all'); setFilterDate(''); }}
          >
            Xóa lọc
          </button>

          {/* Export button */}
          <button
            className="btn-sm primary"
            onClick={() => handleExport('csv')}
            disabled={exporting}
            title="Xuất báo cáo 30 ngày gần nhất"
          >
            {exporting ? '⏳ Đang xuất...' : '📤 Xuất CSV'}
          </button>
          <button
            className="btn-sm secondary"
            onClick={() => handleExport('pdf')}
            disabled={exporting}
            title="Xuất báo cáo PDF"
          >
            {exporting ? '⏳' : '📄 PDF'}
          </button>

          <button
            className="btn-sm secondary"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            🔍 Bộ lọc nâng cao
          </button>
        </div>

        {showAdvanced && (
          <div className="card" style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <FeatureBadge type="coming-soon" />
              <span style={{ color: 'var(--muted)', fontSize: 14 }}>Lọc theo thiết bị — Sắp hỗ trợ</span>
            </div>
          </div>
        )}

        {/* Conversations */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">💬 Hội thoại</span>
            <button className="btn-sm secondary" onClick={loadThreads} style={{ minHeight: 36 }}>↻</button>
          </div>

          {selectedThread ? (
            threadLoading ? (
              <SectionState state="loading" loadingText="Đang tải hội thoại..." />
            ) : threadDetail ? (
              <div>
                <button className="btn-back" onClick={() => { setSelectedThread(null); setThreadDetail(null); }}>
                  ← Quay lại
                </button>
                <div style={{ fontWeight: 700, fontSize: 'var(--font-section)', marginBottom: 14 }}>
                  {threadDetail.session?.title || 'Hội thoại'}
                </div>
                <div style={{ marginBottom: 8, color: 'var(--muted)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <button disabled title="Sắp hỗ trợ" style={{ opacity: 0.4, cursor: 'not-allowed', padding: '6px 12px', borderRadius: 8, border: '1.5px solid var(--border)', background: 'none', fontSize: 13 }}>
                    ▶ Phát lại
                  </button>
                  <FeatureBadge type="coming-soon" />
                </div>
                <div className="chat-bubble-wrap">
                  {(threadDetail.turns || []).map((turn, i) => (
                    <div key={i} className="chat-entry">
                      <div className="chat-who">{turn.role === 'user' ? '👦 Bé' : '🤖 Bi'}</div>
                      <div className={`bubble ${turn.role === 'user' ? 'user' : 'bi'}`}>
                        {turn.content}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <SectionState state="error" errorText="Không tải được hội thoại." onRetry={() => openThread(selectedThread)} />
            )
          ) : (
            <>
              {threadsState === 'loading' && <SectionState state="loading" loadingText="Đang tải hội thoại..." />}
              {threadsState === 'error' && <SectionState state="error" errorText="Không tải được hội thoại." onRetry={loadThreads} />}
              {threadsState === 'empty' && <SectionState state="empty" emptyText="Chưa có hội thoại nào" emptyIcon="💬" />}
              {threadsState === 'data' && (
                filteredThreads.length === 0 ? (
                  <SectionState state="empty" emptyText="Không có kết quả phù hợp với bộ lọc." emptyIcon="🔍" />
                ) : (
                  <div className="thread-timeline">
                    {filteredThreads.map(c => (
                      <div key={c.session_id} className="thread-item" onClick={() => openThread(c.session_id)}>
                        <span className="thread-icon">
                          {c.is_homework ? '📚' : '💬'}
                        </span>
                        <div className="thread-body">
                          <div className="thread-title">{c.title || 'Hội thoại không tiêu đề'}</div>
                          <div className="thread-meta">
                            {fmtTime(c.started_at)} · {c.turn_count || 0} lượt
                          </div>
                        </div>
                        <span className="thread-arrow">›</span>
                      </div>
                    ))}
                  </div>
                )
              )}
            </>
          )}
        </div>

        {/* Monthly emotion chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📊 Cảm xúc theo tháng</span>
          </div>
          {emotionData.length > 0 ? (
            <>
              <div className="emotion-chart">
                {emotionData.map((week, i) => (
                  <div key={i} className="emotion-week">
                    <span className="emotion-week-label">{week.week}</span>
                    <div className="bar-row">
                      <div className="bar-seg happy" style={{ width: `${week.happy}%` }} title={`Vui: ${week.happy}%`} />
                      <div className="bar-seg neutral" style={{ width: `${week.neutral}%` }} title={`Bình thường: ${week.neutral}%`} />
                      <div className="bar-seg sad" style={{ width: `${week.sad}%` }} title={`Buồn: ${week.sad}%`} />
                      <div className="bar-seg stressed" style={{ width: `${week.stressed}%` }} title={`Căng thẳng: ${week.stressed}%`} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="emotion-legend">
                <div className="legend-item"><div className="legend-dot" style={{ background: '#22c55e' }} />Vui vẻ</div>
                <div className="legend-item"><div className="legend-dot" style={{ background: '#94a3b8' }} />Bình thường</div>
                <div className="legend-item"><div className="legend-dot" style={{ background: '#f59e0b' }} />Buồn</div>
                <div className="legend-item"><div className="legend-dot" style={{ background: '#ef4444' }} />Căng thẳng</div>
              </div>
            </>
          ) : (
            <SectionState state="loading" loadingText="Đang tải dữ liệu cảm xúc..." />
          )}
        </div>
      </div>
    </div>
  );
}
