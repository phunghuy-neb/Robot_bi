import { useState, useEffect } from 'react';
import { getLearningModules, getLearningLesson, submitLearningLesson, showToast } from '../services/api.js';

const MODULE_COLORS = {
  // English
  colors:       { bg: '#fff3e0', accent: '#ff9800', icon: '🎨' },
  animals:      { bg: '#e8f5e9', accent: '#4caf50', icon: '🐾' },
  numbers:      { bg: '#e3f2fd', accent: '#2196f3', icon: '🔢' },
  family:       { bg: '#fce4ec', accent: '#e91e63', icon: '👨‍👩‍👧' },
  // Math
  math_shapes:  { bg: '#ede7f6', accent: '#7c3aed', icon: '🔺' },
  math_add:     { bg: '#e8eaf6', accent: '#3f51b5', icon: '➕' },
  math_count:   { bg: '#e3f2fd', accent: '#0288d1', icon: '🔢' },
  // Science
  sci_weather:  { bg: '#fff8e1', accent: '#f59e0b', icon: '☀️' },
  sci_body:     { bg: '#fbe9e7', accent: '#ef5350', icon: '🧠' },
  sci_plant:    { bg: '#e8f5e9', accent: '#2e7d32', icon: '🌱' },
};

const SUBJECTS = [
  { key: 'en',      label: '🔤 Tiếng Anh', color: '#2196f3' },
  { key: 'math',    label: '🔢 Toán',      color: '#7c3aed' },
  { key: 'science', label: '🔬 Khoa học',  color: '#2e7d32' },
];

function shuffleArray(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export default function LearningHubPage() {
  const [view, setView] = useState('modules'); // 'modules' | 'lessons' | 'playing' | 'result'
  const [modules, setModules] = useState([]);
  const [streak, setStreak] = useState({ current: 0, total_xp: 0 });
  const [loading, setLoading] = useState(true);
  const [activeSubject, setActiveSubject] = useState('en');

  const [selectedModule, setSelectedModule] = useState(null);
  const [selectedLesson, setSelectedLesson] = useState(null);
  const [lessonData, setLessonData] = useState(null);

  // Quiz state
  const [qIndex, setQIndex] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [shuffledOptions, setShuffledOptions] = useState([]);
  const [feedback, setFeedback] = useState(null); // null | 'correct' | 'wrong'
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { loadModules(); }, []);

  async function loadModules() {
    setLoading(true);
    const data = await getLearningModules();
    if (data?.modules) {
      setModules(data.modules);
      setStreak(data.streak || { current: 0, total_xp: 0 });
    }
    setLoading(false);
  }

  function openModule(mod) {
    setSelectedModule(mod);
    setView('lessons');
  }

  async function openLesson(lesson) {
    const data = await getLearningLesson(lesson.lesson_id);
    if (!data?.items?.length) { showToast('Không tải được bài học'); return; }
    setLessonData(data);
    setSelectedLesson(lesson);
    setQIndex(0);
    setAnswers([]);
    setFeedback(null);
    setResult(null);
    setShuffledOptions(shuffleArray(data.items[0].options));
    setView('playing');
  }

  function handleAnswer(option) {
    if (feedback) return;
    const item = lessonData.items[qIndex];
    const isCorrect = option.toLowerCase() === item.question.toLowerCase();
    setFeedback(isCorrect ? 'correct' : 'wrong');

    const newAnswers = [...answers, option];
    setAnswers(newAnswers);

    setTimeout(async () => {
      setFeedback(null);
      if (qIndex + 1 < lessonData.items.length) {
        const next = qIndex + 1;
        setQIndex(next);
        setShuffledOptions(shuffleArray(lessonData.items[next].options));
      } else {
        // Submit
        setSubmitting(true);
        const res = await submitLearningLesson(lessonData.lesson.lesson_id, newAnswers);
        setSubmitting(false);
        if (res) {
          setResult(res);
          setStreak({ current: res.streak?.current || 0, total_xp: res.streak?.total_xp || 0 });
          loadModules();
        }
        setView('result');
      }
    }, 900);
  }

  // ── Views ────────────────────────────────────────────────────────────────

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
      <div className="spinner" />
    </div>
  );

  if (view === 'result' && result) {
    const pct = Math.round((result.score / result.total) * 100);
    const stars = result.score >= 5 ? 3 : result.score >= 4 ? 2 : result.score >= 3 ? 1 : 0;
    return (
      <div style={{ padding: '24px 16px', maxWidth: 480, margin: '0 auto', textAlign: 'center' }}>
        <div style={{ fontSize: 72, marginBottom: 8 }}>
          {stars === 3 ? '🏆' : stars === 2 ? '🥈' : stars === 1 ? '🥉' : '😅'}
        </div>
        <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 4 }}>
          {result.score}/{result.total} câu đúng
        </div>
        <div style={{ fontSize: 18, color: 'var(--muted)', marginBottom: 16 }}>
          {'⭐'.repeat(stars)}{'☆'.repeat(3 - stars)}
        </div>
        {result.completed && (
          <div style={{ background: '#e8f5e9', border: '1px solid #4caf50', borderRadius: 12, padding: '12px 16px', marginBottom: 16, color: '#2e7d32', fontWeight: 600 }}>
            ✅ Hoàn thành bài học! +{result.xp_earned} XP
          </div>
        )}
        <div style={{ background: 'var(--card)', borderRadius: 12, padding: 16, marginBottom: 20 }}>
          <div style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 4 }}>Chuỗi ngày học</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>🔥 {streak.current} ngày</div>
          <div style={{ fontSize: 13, color: 'var(--muted)' }}>Tổng {streak.total_xp} XP</div>
        </div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
          <button className="btn-sm secondary" style={{ flex: 1, minHeight: 48 }}
            onClick={() => openLesson(selectedLesson)}>
            🔄 Làm lại
          </button>
          <button className="btn-sm primary" style={{ flex: 1, minHeight: 48 }}
            onClick={() => setView('lessons')}>
            📋 Các bài khác
          </button>
        </div>
      </div>
    );
  }

  if (view === 'playing' && lessonData) {
    const item = lessonData.items[qIndex];
    const total = lessonData.items.length;
    const pct = Math.round(((qIndex) / total) * 100);
    return (
      <div style={{ padding: '16px', maxWidth: 480, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <button className="btn-sm secondary" style={{ minWidth: 40 }}
            onClick={() => setView('lessons')}>←</button>
          <div style={{ flex: 1, background: '#e0e0e0', borderRadius: 99, height: 10 }}>
            <div style={{ width: `${pct}%`, background: 'var(--primary)', height: 10, borderRadius: 99, transition: 'width 0.3s' }} />
          </div>
          <span style={{ fontSize: 13, color: 'var(--muted)', minWidth: 40, textAlign: 'right' }}>
            {qIndex + 1}/{total}
          </span>
        </div>

        {/* Question */}
        <div style={{
          textAlign: 'center', padding: '24px 16px', marginBottom: 20,
          background: feedback === 'correct' ? '#e8f5e9' : feedback === 'wrong' ? '#ffebee' : 'var(--card)',
          borderRadius: 16, transition: 'background 0.3s',
          border: `2px solid ${feedback === 'correct' ? '#4caf50' : feedback === 'wrong' ? '#f44336' : 'transparent'}`,
        }}>
          <div style={{ fontSize: 72, marginBottom: 8 }}>{item.emoji}</div>
          <div style={{ fontSize: 32, fontWeight: 700, marginBottom: 6 }}>{item.question}</div>
          <div style={{ fontSize: 16, color: 'var(--muted)' }}>{item.question_vi}</div>
          {feedback === 'correct' && <div style={{ marginTop: 8, fontSize: 20, color: '#4caf50', fontWeight: 700 }}>✓ Đúng rồi! 🎉</div>}
          {feedback === 'wrong' && <div style={{ marginTop: 8, fontSize: 16, color: '#f44336' }}>✗ Sai — đáp án đúng: <b>{item.question}</b></div>}
        </div>

        {/* Options */}
        {submitting ? (
          <div style={{ textAlign: 'center', padding: 20 }}><div className="spinner" /></div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {shuffledOptions.map(option => (
              <button
                key={option}
                onClick={() => handleAnswer(option)}
                disabled={!!feedback}
                style={{
                  minHeight: 64, fontSize: 18, fontWeight: 600, borderRadius: 12,
                  border: '2px solid var(--border, #e0e0e0)',
                  background: feedback && option.toLowerCase() === item.question.toLowerCase()
                    ? '#e8f5e9'
                    : feedback ? '#fafafa' : 'var(--card)',
                  color: feedback && option.toLowerCase() === item.question.toLowerCase()
                    ? '#2e7d32' : 'var(--text)',
                  cursor: feedback ? 'default' : 'pointer',
                  opacity: feedback && option.toLowerCase() !== item.question.toLowerCase() ? 0.5 : 1,
                  transition: 'all 0.2s',
                }}
              >
                {option}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (view === 'lessons' && selectedModule) {
    const colors = MODULE_COLORS[selectedModule.module] || { bg: '#f5f5f5', accent: '#666', icon: '📚' };
    return (
      <div style={{ padding: '16px', maxWidth: 480, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <button className="btn-sm secondary" style={{ minWidth: 40 }}
            onClick={() => setView('modules')}>←</button>
          <span style={{ fontSize: 24 }}>{colors.icon}</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{selectedModule.label}</div>
            <div style={{ fontSize: 13, color: 'var(--muted)' }}>{selectedModule.label_vi}</div>
          </div>
        </div>

        <div style={{ background: 'var(--card)', borderRadius: 12, padding: 12, marginBottom: 20, display: 'flex', gap: 20, justifyContent: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: colors.accent }}>{selectedModule.completed_lessons}/{selectedModule.total_lessons}</div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>Bài hoàn thành</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: colors.accent }}>{selectedModule.module_xp}</div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>XP</div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {selectedModule.lessons.map((lesson, i) => (
            <button
              key={lesson.lesson_id}
              onClick={() => openLesson(lesson)}
              style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '14px 16px', borderRadius: 12,
                background: lesson.completed ? '#e8f5e9' : 'var(--card)',
                border: `2px solid ${lesson.completed ? '#4caf50' : 'var(--border, #e0e0e0)'}`,
                cursor: 'pointer', textAlign: 'left',
              }}
            >
              <span style={{ fontSize: 28 }}>{lesson.completed ? '✅' : `${i + 1}️⃣`}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>Bài {i + 1}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>{lesson.completed ? 'Hoàn thành' : '5 câu hỏi · 10 XP'}</div>
              </div>
              <span style={{ fontSize: 18, color: 'var(--muted)' }}>▶</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // Modules view (default)
  const subjectInfo = SUBJECTS.find(s => s.key === activeSubject) || SUBJECTS[0];
  const filteredModules = modules.filter(m => (m.subject || 'en') === activeSubject);

  return (
    <div style={{ padding: '16px', maxWidth: 480, margin: '0 auto' }}>
      {/* Subject tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, overflowX: 'auto', paddingBottom: 4 }}>
        {SUBJECTS.map(subj => (
          <button
            key={subj.key}
            onClick={() => setActiveSubject(subj.key)}
            style={{
              whiteSpace: 'nowrap', padding: '8px 16px', borderRadius: 99,
              border: `2px solid ${subj.color}`,
              background: activeSubject === subj.key ? subj.color : 'transparent',
              color: activeSubject === subj.key ? '#fff' : subj.color,
              fontWeight: 600, fontSize: 14, cursor: 'pointer',
            }}
          >
            {subj.label}
          </button>
        ))}
      </div>

      {/* Streak bar */}
      <div style={{
        background: 'linear-gradient(135deg, #ff9800, #f44336)',
        borderRadius: 14, padding: '14px 20px', marginBottom: 20,
        display: 'flex', justifyContent: 'space-around', color: '#fff',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>🔥 {streak.current}</div>
          <div style={{ fontSize: 12, opacity: 0.9 }}>Chuỗi ngày</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 28, fontWeight: 700 }}>⭐ {streak.total_xp}</div>
          <div style={{ fontSize: 12, opacity: 0.9 }}>Tổng XP</div>
        </div>
      </div>

      {/* Module grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}><div className="spinner" /></div>
      ) : filteredModules.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
          Chưa có bài học nào
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {filteredModules.map(mod => {
            const colors = MODULE_COLORS[mod.module] || { bg: '#f5f5f5', accent: '#666', icon: '📚' };
            const pct = mod.total_lessons ? Math.round((mod.completed_lessons / mod.total_lessons) * 100) : 0;
            return (
              <button
                key={mod.module}
                onClick={() => openModule(mod)}
                style={{
                  background: colors.bg, borderRadius: 16, padding: '18px 14px',
                  border: `2px solid ${colors.accent}22`, cursor: 'pointer',
                  textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 6,
                }}
              >
                <div style={{ fontSize: 44 }}>{colors.icon}</div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>{mod.label}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{mod.label_vi}</div>
                <div style={{ background: '#ddd', borderRadius: 99, height: 6, margin: '4px 0' }}>
                  <div style={{ width: `${pct}%`, background: colors.accent, height: 6, borderRadius: 99 }} />
                </div>
                <div style={{ fontSize: 11, color: '#888' }}>
                  {mod.completed_lessons}/{mod.total_lessons} bài · {mod.module_xp} XP
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
