import { useState, useEffect, useMemo, useRef } from 'react';
import { getConversations, getConversation, getMonthlyEmotions, exportReport, showToast } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import SpecialMemories from '../components/SpecialMemories.jsx';

function fmtTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch (_) { return ts; }
}

export default function JournalPage() {
  const playbackRunRef = useRef(0);
  const [filterType, setFilterType] = useState('all');
  const [filterDate, setFilterDate] = useState('');
  const [advancedFilters, setAdvancedFilters] = useState({ q: '', minTurns: '0', sort: 'newest' });
  const [threadsState, setThreadsState] = useState('loading');
  const [threads, setThreads] = useState([]);
  const [selectedThread, setSelectedThread] = useState(null);
  const [threadDetail, setThreadDetail] = useState(null);
  const [threadLoading, setThreadLoading] = useState(false);
  const [emotionData, setEmotionData] = useState([]);
  const [emotionState, setEmotionState] = useState('loading');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [playbackState, setPlaybackState] = useState('idle');
  const [playbackIndex, setPlaybackIndex] = useState(-1);

  useEffect(() => {
    loadThreads();
    loadEmotions();
  }, []);

  useEffect(() => () => {
    playbackRunRef.current += 1;
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }, []);

  async function loadThreads() {
    setThreadsState('loading');
    stopPlayback();
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
    setEmotionState('loading');
    const data = await getMonthlyEmotions();
    if (Array.isArray(data) && data.length > 0) {
      setEmotionData(data);
      setEmotionState('data');
    } else if (data) {
      setEmotionData([]);
      setEmotionState('empty');
    } else {
      setEmotionState('error');
    }
  }

  async function openThread(id) {
    setThreadLoading(true);
    stopPlayback();
    setSelectedThread(id);
    const data = await getConversation(id);
    setThreadDetail(data);
    setThreadLoading(false);
  }

  function resetFilters() {
    setFilterType('all');
    setFilterDate('');
    setAdvancedFilters({ q: '', minTurns: '0', sort: 'newest' });
  }

  function setAdvancedFilter(name, value) {
    setAdvancedFilters(prev => ({ ...prev, [name]: value }));
  }

  function speechAvailable() {
    return (
      typeof window !== 'undefined'
      && window.speechSynthesis
      && typeof window.SpeechSynthesisUtterance !== 'undefined'
    );
  }

  function stopPlayback() {
    playbackRunRef.current += 1;
    if (speechAvailable()) window.speechSynthesis.cancel();
    setPlaybackState('idle');
    setPlaybackIndex(-1);
  }

  function playbackQueue() {
    return (threadDetail?.turns || [])
      .map((turn, index) => {
        const content = String(turn.content || '').trim();
        if (!content) return null;
        const speaker = turn.role === 'user' ? 'Bé nói' : 'Bi trả lời';
        return { index, text: `${speaker}: ${content}` };
      })
      .filter(Boolean);
  }

  function handleReplayThread() {
    if (!speechAvailable()) {
      showToast('Trình duyệt chưa hỗ trợ phát lại hội thoại');
      return;
    }
    const queue = playbackQueue();
    if (queue.length === 0) {
      showToast('Hội thoại này chưa có nội dung để phát lại');
      return;
    }

    const runId = playbackRunRef.current + 1;
    playbackRunRef.current = runId;
    window.speechSynthesis.cancel();

    const playAt = (queueIndex) => {
      if (playbackRunRef.current !== runId) return;
      const item = queue[queueIndex];
      if (!item) {
        setPlaybackState('idle');
        setPlaybackIndex(-1);
        return;
      }
      const utterance = new window.SpeechSynthesisUtterance(item.text);
      utterance.lang = 'vi-VN';
      utterance.rate = 0.95;
      utterance.onstart = () => {
        if (playbackRunRef.current !== runId) return;
        setPlaybackState('playing');
        setPlaybackIndex(item.index);
      };
      utterance.onend = () => {
        if (playbackRunRef.current !== runId) return;
        if (queueIndex + 1 < queue.length) playAt(queueIndex + 1);
        else {
          setPlaybackState('idle');
          setPlaybackIndex(-1);
        }
      };
      utterance.onerror = () => {
        if (playbackRunRef.current !== runId) return;
        setPlaybackState('idle');
        setPlaybackIndex(-1);
        showToast('Không phát lại được trong trình duyệt này');
      };
      window.speechSynthesis.speak(utterance);
    };

    playAt(0);
  }

  const filteredThreads = useMemo(() => {
    const query = advancedFilters.q.trim().toLowerCase();
    const minTurns = Number(advancedFilters.minTurns) || 0;
    const result = threads.filter(c => {
      if (filterDate) {
        const d = new Date(c.started_at);
        const fd = new Date(filterDate);
        if (d.toDateString() !== fd.toDateString()) return false;
      }
      if (filterType === 'homework' && !c.is_homework) return false;
      if (filterType === 'chat' && c.is_homework) return false;
      if ((c.turn_count || 0) < minTurns) return false;
      if (query) {
        const haystack = [
          c.title || '',
          c.session_id || '',
          c.started_at || '',
          String(c.turn_count || 0),
        ].join(' ').toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      return true;
    });

    return [...result].sort((a, b) => {
      if (advancedFilters.sort === 'oldest') {
        return new Date(a.started_at || 0) - new Date(b.started_at || 0);
      }
      if (advancedFilters.sort === 'turns') {
        return (b.turn_count || 0) - (a.turn_count || 0);
      }
      return new Date(b.started_at || 0) - new Date(a.started_at || 0);
    });
  }, [threads, filterDate, filterType, advancedFilters]);

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
            onClick={resetFilters}
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
          <div className="journal-advanced-panel">
            <label className="journal-filter-field">
              <span>Tìm hội thoại</span>
              <input
                className="filter-input"
                value={advancedFilters.q}
                onChange={e => setAdvancedFilter('q', e.target.value)}
                placeholder="Tiêu đề, mã phiên..."
              />
            </label>
            <label className="journal-filter-field">
              <span>Số lượt tối thiểu</span>
              <select
                className="filter-select"
                value={advancedFilters.minTurns}
                onChange={e => setAdvancedFilter('minTurns', e.target.value)}
              >
                <option value="0">Tất cả</option>
                <option value="2">Từ 2 lượt</option>
                <option value="5">Từ 5 lượt</option>
                <option value="10">Từ 10 lượt</option>
              </select>
            </label>
            <label className="journal-filter-field">
              <span>Sắp xếp</span>
              <select
                className="filter-select"
                value={advancedFilters.sort}
                onChange={e => setAdvancedFilter('sort', e.target.value)}
              >
                <option value="newest">Mới nhất</option>
                <option value="oldest">Cũ nhất</option>
                <option value="turns">Nhiều lượt nhất</option>
              </select>
            </label>
            <div className="journal-filter-count">
              {filteredThreads.length}/{threads.length} hội thoại
            </div>
          </div>
        )}

        {/* Conversations */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">💬 Hội thoại</span>
            <button className="btn-sm secondary" onClick={loadThreads}>↻</button>
          </div>

          {selectedThread ? (
            threadLoading ? (
              <SectionState state="loading" loadingText="Đang tải hội thoại..." />
            ) : threadDetail ? (
              <div>
                <button className="btn-back" onClick={() => { stopPlayback(); setSelectedThread(null); setThreadDetail(null); }}>
                  ← Quay lại
                </button>
                <div style={{ fontWeight: 700, fontSize: 'var(--font-section)', marginBottom: 14 }}>
                  {threadDetail.session?.title || 'Hội thoại'}
                </div>
                <div className="journal-playback-bar">
                  {playbackState === 'playing' ? (
                    <button className="btn-sm secondary" onClick={stopPlayback}>
                      Dừng phát
                    </button>
                  ) : (
                    <button className="btn-sm primary" onClick={handleReplayThread}>
                      Phát lại
                    </button>
                  )}
                  <span>
                    {playbackState === 'playing'
                      ? `Đang đọc lượt ${playbackIndex + 1}/${threadDetail.turns?.length || 0}`
                      : `${threadDetail.turns?.length || 0} lượt hội thoại`}
                  </span>
                </div>
                <div className="chat-bubble-wrap">
                  {(threadDetail.turns || []).map((turn, i) => (
                    <div key={i} className={`chat-entry${playbackIndex === i ? ' is-playing' : ''}`}>
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
            <SectionState
              state={emotionState === 'data' ? 'empty' : emotionState}
              loadingText="Đang tải dữ liệu cảm xúc..."
              emptyText="Chưa có dữ liệu cảm xúc tháng này"
              emptyIcon="📊"
              errorText="Không tải được dữ liệu cảm xúc."
              onRetry={emotionState === 'error' ? loadEmotions : undefined}
            />
          )}
        </div>
      </div>
    </div>
  );
}
