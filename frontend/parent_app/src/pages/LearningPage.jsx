import { useState, useEffect } from 'react';
import { apiFetch, showToast } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import FeatureBadge from '../components/FeatureBadge.jsx';

export default function LearningPage({ activeChild }) {
  const [vocabState, setVocabState] = useState('loading');
  const [vocab, setVocab] = useState([]);
  const [vocabSearch, setVocabSearch] = useState('');
  const [tasksState, setTasksState] = useState('loading');
  const [tasks, setTasks] = useState([]);
  const [storiesState, setStoriesState] = useState('loading');
  const [stories, setStories] = useState([]);

  useEffect(() => {
    loadVocab();
    loadTasks();
    loadStories();
  }, []);

  async function loadVocab() {
    setVocabState('loading');
    const data = await apiFetch('/api/education/vocabulary');
    const words = data?.words || [];
    if (words.length > 0) { setVocab(words); setVocabState('data'); }
    else if (data) setVocabState('empty');
    else setVocabState('error');
  }

  async function loadTasks() {
    setTasksState('loading');
    const data = await apiFetch('/api/tasks');
    if (Array.isArray(data) && data.length > 0) { setTasks(data); setTasksState('data'); }
    else if (Array.isArray(data)) setTasksState('empty');
    else setTasksState('error');
  }

  async function loadStories() {
    setStoriesState('loading');
    const data = await apiFetch('/api/story/list');
    const list = data?.stories || data || [];
    if (Array.isArray(list) && list.length > 0) { setStories(list); setStoriesState('data'); }
    else if (data) setStoriesState('empty');
    else setStoriesState('error');
  }

  async function completeTask(id) {
    const r = await apiFetch(`/api/tasks/${id}/complete`, { method: 'POST' });
    if (r?.ok) {
      showToast('✅ Hoàn thành! +1 ⭐');
      loadTasks();
    } else {
      showToast('Nhiệm vụ đã hoàn thành rồi!');
    }
  }

  async function startGame(type) {
    const path = type === 'flashcard'
      ? '/api/education/flashcard/start'
      : `/api/game/${type}/start`;
    const r = await apiFetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    });
    if (r) showToast('🎮 Trò chơi bắt đầu!');
    else showToast('⚠️ Chức năng này sẽ được kết nối sau.');
  }

  function speakWord(word) {
    apiFetch('/api/puppet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: word }),
    });
    showToast(`🔊 Bi đọc: ${word}`);
  }

  const filteredVocab = vocab.filter(w =>
    w.word?.toLowerCase().includes(vocabSearch.toLowerCase()) ||
    w.meaning?.toLowerCase().includes(vocabSearch.toLowerCase())
  );

  return (
    <div>
      <div className="page-header">
        <div className="page-title">📚 Học tập</div>
        <div className="page-subtitle">Từ vựng · Nhiệm vụ · Luyện tập · Truyện</div>
      </div>

      <div className="page-body">
        {/* Quick action shortcuts */}
        <div className="quick-actions-grid">
          <button className="quick-action-btn" onClick={() => document.querySelector('.vocab-grid')?.scrollIntoView({ behavior: 'smooth' })}>
            <span>📖</span>
            <span>Từ vựng</span>
          </button>
          <button className="quick-action-btn" onClick={() => startGame('flashcard')}>
            <span>🃏</span>
            <span>Flashcard</span>
          </button>
          <button className="quick-action-btn" onClick={() => showToast('Video: Chuyển sang tab Thêm')}>
            <span>🎬</span>
            <span>Video</span>
          </button>
          <button className="quick-action-btn" onClick={() => startGame('word-quiz')}>
            <span>🎮</span>
            <span>Trò chơi</span>
          </button>
        </div>

        {/* Progress ring + featured lesson */}
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div className="progress-ring-wrap">
            <svg className="progress-ring" viewBox="0 0 120 120" width="100" height="100">
              <circle cx="60" cy="60" r="50" fill="none" stroke="var(--primary-soft)" strokeWidth="12" />
              <circle cx="60" cy="60" r="50" fill="none" stroke="var(--primary)" strokeWidth="12"
                strokeDasharray="314" strokeDashoffset="78.5"
                strokeLinecap="round"
                style={{ transform: 'rotate(-90deg)', transformOrigin: '60px 60px' }}
              />
            </svg>
            <div className="progress-ring-label">75%</div>
          </div>
          <div className="lesson-card" style={{ flex: 1 }}>
            <div className="lesson-thumb">🔤</div>
            <div className="lesson-body">
              <div className="lesson-title">Từ vựng chủ đề Gia đình</div>
              <div className="lesson-meta">10 từ · 5–7 tuổi</div>
            </div>
            <button className="btn-start" onClick={() => startGame('vocabulary')}>Bắt đầu</button>
          </div>
        </div>

        {/* Vocabulary section */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🔤 Từ vựng</span>
            <button className="btn-sm secondary" onClick={loadVocab} style={{ minHeight: 36 }}>↻</button>
          </div>

          {vocabState === 'data' && (
            <input
              type="text"
              className="form-input"
              style={{ marginBottom: 12 }}
              placeholder="🔍 Tìm từ vựng..."
              value={vocabSearch}
              onChange={e => setVocabSearch(e.target.value)}
            />
          )}

          {vocabState === 'loading' && <SectionState state="loading" loadingText="Đang tải từ vựng..." />}
          {vocabState === 'error' && <SectionState state="error" errorText="Không tải được từ vựng." onRetry={loadVocab} />}
          {vocabState === 'empty' && <SectionState state="empty" emptyText="Chưa có từ vựng nào." emptyIcon="📚" />}
          {vocabState === 'data' && (
            filteredVocab.length === 0 ? (
              <SectionState state="empty" emptyText="Không tìm thấy từ phù hợp." emptyIcon="🔍" />
            ) : (
              <div className="vocab-grid">
                {filteredVocab.map((w, i) => (
                  <div key={i} className="vocab-card" onClick={() => speakWord(w.word)}>
                    <span className="vocab-emoji">{w.emoji || '📖'}</span>
                    <div className="vocab-word">{w.word}</div>
                    <div className="vocab-meaning">{w.meaning}</div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>

        {/* Quiz / Luyện tập */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🎮 Luyện tập</span>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button className="btn-action primary" onClick={() => startGame('word-quiz')}>
              📝 Bắt đầu Word Quiz
            </button>
            <button className="btn-action primary" onClick={() => startGame('voice-quiz')}>
              🎤 Bắt đầu Voice Quiz
            </button>
          </div>
        </div>

        {/* Tasks */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">✅ Nhiệm vụ hôm nay</span>
            <button className="btn-sm secondary" onClick={loadTasks} style={{ minHeight: 36 }}>↻</button>
          </div>
          {tasksState === 'loading' && <SectionState state="loading" loadingText="Đang tải nhiệm vụ..." />}
          {tasksState === 'error' && <SectionState state="error" errorText="Không tải được nhiệm vụ." onRetry={loadTasks} />}
          {tasksState === 'empty' && <SectionState state="empty" emptyText="Chưa có nhiệm vụ nào hôm nay." emptyIcon="📋" />}
          {tasksState === 'data' && (
            tasks.map(task => (
              <div key={task.task_id} className={`task-item${task.completed_today ? ' done' : ''}`}>
                <button
                  className={`task-check${task.completed_today ? ' done' : ''}`}
                  onClick={() => !task.completed_today && completeTask(task.task_id)}
                  title={task.completed_today ? 'Đã hoàn thành' : 'Đánh dấu hoàn thành'}
                >
                  {task.completed_today ? '✓' : ''}
                </button>
                <span className="task-name">{task.name}</span>
                <span className="task-stars">{'⭐'.repeat(task.stars || 0)}</span>
              </div>
            ))
          )}
        </div>

        {/* Stories */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📖 Truyện kể</span>
            <button className="btn-sm secondary" onClick={loadStories} style={{ minHeight: 36 }}>↻</button>
          </div>
          {storiesState === 'loading' && <SectionState state="loading" loadingText="Đang tải truyện..." />}
          {storiesState === 'error' && <SectionState state="error" errorText="Không tải được truyện." onRetry={loadStories} />}
          {storiesState === 'empty' && <SectionState state="empty" emptyText="Chưa có truyện nào." emptyIcon="📚" />}
          {storiesState === 'data' && (
            stories.slice(0, 6).map((s, i) => (
              <div key={i} className="media-card">
                <div className="media-thumb">{s.emoji || '📖'}</div>
                <div className="media-body">
                  <div className="media-title">{s.title}</div>
                  <div className="media-meta">{s.duration || ''} {s.age ? `· ${s.age}` : ''}</div>
                </div>
                <button
                  className="btn-sm primary media-action"
                  onClick={() => {
                    apiFetch('/api/story/tell', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ story_id: s.id || null }),
                    });
                    showToast(`📖 Bi đang kể: "${s.title}"`);
                  }}
                >
                  ▶ Kể
                </button>
              </div>
            ))
          )}
        </div>

        {/* Chat với Bi — coming soon */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">💬 Chat với Bi</span>
            <FeatureBadge type="coming-soon" />
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 14 }}>
            Lịch sử chat phụ huynh ↔ Bi — Sắp hỗ trợ.
          </p>
        </div>
      </div>
    </div>
  );
}
