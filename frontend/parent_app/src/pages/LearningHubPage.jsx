import { useState, useEffect, useRef } from 'react';
import {
  getLearningModules, getLearningLesson, submitLearningLesson, showToast,
  getExamTracks, getExams, getExam, submitExam, submitToeicSW, submitToeicSpeakingAudio,
  getExamSessions, deleteExam,
} from '../services/api.js';
import ExamBuilder from '../components/ExamBuilder.jsx';
import SubjectGrid from '../components/learning/SubjectGrid.jsx';

// TOEIC S&W task type -> Vietnamese label (drives the free-text prompt header).
const SW_TASK_LABELS = {
  read_aloud:           'Đọc to',
  describe_picture:     'Miêu tả tranh',
  respond_to_questions: 'Trả lời câu hỏi',
  email:                'Viết email',
  express_opinion:      'Nêu quan điểm',
  opinion_essay:        'Bài luận quan điểm',
};

// Kind -> badge color for track cards.
const TRACK_KIND_COLORS = {
  practice:    '#2196f3',
  competition: '#e91e63',
  exam:        '#7c3aed',
  roadmap:     '#2e7d32',
};

function fmtTime(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

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

  // ── Exam mode state ──────────────────────────────────────────────────────
  const [mode, setMode] = useState('learn'); // 'learn' | 'exam'
  // spec 007: cửa trước subject-first. 'subjects' = lưới môn; 'detail' = vào 1 môn (UI cũ, US2 sẽ thay).
  const [hubView, setHubView] = useState('subjects');
  const [examView, setExamView] = useState('tracks'); // 'tracks' | 'list' | 'playing' | 'result'
  const [tracks, setTracks] = useState([]);
  const [examLoading, setExamLoading] = useState(false);
  const [selectedTrack, setSelectedTrack] = useState(null);
  const [examList, setExamList] = useState([]);
  const [examData, setExamData] = useState(null); // { paper, questions }
  const [examAnswers, setExamAnswers] = useState({});
  const [examQIndex, setExamQIndex] = useState(0);
  const [examTimeLeft, setExamTimeLeft] = useState(0);
  const [examResult, setExamResult] = useState(null);
  const [examSubmitting, setExamSubmitting] = useState(false);
  const examStartRef = useRef(0);
  const examTimerRef = useRef(null);
  // TOEIC S&W speaking: browser-native speech-to-text (no extra deps).
  const [recording, setRecording] = useState(false);
  const recognitionRef = useRef(null);
  // Audio THẬT cho Speaking: ghi clip mỗi câu, gửi server STT khi nộp.
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioBlobsRef = useRef({});  // { [questionId]: Blob }

  useEffect(() => { loadModules(); }, []);

  // Exam countdown timer.
  useEffect(() => {
    if (examView !== 'playing') return undefined;
    examTimerRef.current = setInterval(() => {
      setExamTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(examTimerRef.current);
          finishExam(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(examTimerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [examView]);

  async function loadTracks() {
    setExamLoading(true);
    const data = await getExamTracks();
    if (data?.tracks) setTracks(data.tracks);
    setExamLoading(false);
  }

  async function openTrack(track) {
    setSelectedTrack(track);
    setExamLoading(true);
    const data = await getExams({ track: track.track });
    setExamList(data?.exams || []);
    setExamLoading(false);
    setExamView('list');
  }

  async function startExam(paper) {
    const data = await getExam(paper.paper_id);
    if (!data?.questions?.length) { showToast('Không tải được đề thi'); return; }
    setExamData(data);
    setExamAnswers({});
    audioBlobsRef.current = {};
    setExamQIndex(0);
    setExamResult(null);
    setExamTimeLeft((data.paper.duration_minutes || 30) * 60);
    examStartRef.current = (data.paper.duration_minutes || 30) * 60;
    setExamView('playing');
  }

  function pickAnswer(questionId, option) {
    setExamAnswers(prev => ({ ...prev, [questionId]: option }));
  }

  function stopRecording() {
    try { recognitionRef.current?.stop(); } catch { /* noop */ }
    try { mediaRecorderRef.current?.state === 'recording' && mediaRecorderRef.current.stop(); } catch { /* noop */ }
    setRecording(false);
  }

  // Ghi âm THẬT clip của câu `questionId` qua MediaRecorder (gửi server STT khi nộp).
  // Song song chạy Web Speech API để hiện transcript xem trước (nếu trình duyệt hỗ trợ).
  async function startAudioCapture(questionId) {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') return false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];
      const mr = new MediaRecorder(stream);
      mr.ondataavailable = (e) => { if (e.data && e.data.size) audioChunksRef.current.push(e.data); };
      mr.onstop = () => {
        if (audioChunksRef.current.length) {
          audioBlobsRef.current[questionId] = new Blob(audioChunksRef.current, { type: mr.mimeType || 'audio/webm' });
        }
        try { mediaStreamRef.current?.getTracks().forEach(t => t.stop()); } catch { /* noop */ }
        mediaStreamRef.current = null;
      };
      mediaRecorderRef.current = mr;
      mr.start();
      return true;
    } catch {
      return false;
    }
  }

  // Speaking: ghi âm thật (server STT) + Web Speech API (transcript xem trước).
  async function toggleRecord(questionId) {
    if (recording) { stopRecording(); return; }
    const gotAudio = await startAudioCapture(questionId);
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR && !gotAudio) { showToast('Trình duyệt không hỗ trợ ghi âm — hãy gõ nội dung bạn nói.'); return; }
    if (SR) {
      const rec = new SR();
      rec.lang = 'en-US';
      rec.interimResults = true;
      rec.continuous = true;
      let finalText = examAnswers[questionId] ? `${examAnswers[questionId]} ` : '';
      rec.onresult = (e) => {
        let interim = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const t = e.results[i][0].transcript;
          if (e.results[i].isFinal) finalText += `${t} `; else interim += t;
        }
        setExamAnswers(prev => ({ ...prev, [questionId]: (finalText + interim).trim() }));
      };
      rec.onerror = () => {};
      recognitionRef.current = rec;
      rec.start();
    }
    setRecording(true);
  }

  async function finishExam(auto = false) {
    if (examSubmitting || !examData) return;
    clearInterval(examTimerRef.current);
    stopRecording();
    setExamSubmitting(true);
    const timeSpent = Math.max(0, examStartRef.current - examTimeLeft);
    let res;
    if (examData.paper.subject === 'toeic_sw') {
      const skill = (examData.paper.skill || 'writing').toLowerCase();
      const blobMap = audioBlobsRef.current || {};
      const recordedQids = Object.keys(blobMap);
      if (skill === 'speaking' && recordedQids.length) {
        // Ưu tiên audio THẬT: server transcribe (Whisper) rồi chấm.
        res = await submitToeicSpeakingAudio(examData.paper.paper_id, {
          questionIds: recordedQids,
          blobs: recordedQids.map(q => blobMap[q]),
          timeSpentSeconds: timeSpent,
          language: 'en',
        });
        // Fallback sang transcript trình duyệt nếu server STT lỗi.
        if (!res && Object.keys(examAnswers).length) {
          res = await submitToeicSW(examData.paper.paper_id, { transcripts: examAnswers, timeSpentSeconds: timeSpent });
        }
      } else {
        res = await submitToeicSW(examData.paper.paper_id, {
          responses: skill === 'speaking' ? {} : examAnswers,
          transcripts: skill === 'speaking' ? examAnswers : {},
          timeSpentSeconds: timeSpent,
        });
      }
    } else {
      res = await submitExam(examData.paper.paper_id, examAnswers, timeSpent);
    }
    setExamSubmitting(false);
    if (res) {
      setExamResult({ ...res, auto });
      setExamView('result');
    } else {
      showToast('Nộp bài thất bại, thử lại');
    }
  }

  function switchMode(next) {
    setMode(next);
    if (next === 'exam' && tracks.length === 0) loadTracks();
    if (next === 'exam') setExamView('tracks');
  }

  // spec 007 US1: chọn 1 môn từ lưới → vào trang môn. Môn có Lộ trình (en/math/science)
  // mở chế độ Học; còn lại mở chế độ Làm đề (mọi môn đều có đề).
  function pickSubject(s) {
    const key = s.subject;
    setActiveSubject(key);
    switchMode(['en', 'math', 'science'].includes(key) ? 'learn' : 'exam');
    setHubView('detail');
  }

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

  // spec 007 US1: lưới môn là màn đầu (cửa trước). Vào 1 môn mới hiện UI học/đề.
  if (hubView === 'subjects') {
    return (
      <div>
        <div className="page-header">
          <div className="page-title">📚 Học tập</div>
          <div className="page-subtitle">Chọn môn để học và luyện tập</div>
        </div>
        <div className="page-body">
          <SubjectGrid onPick={pickSubject} />
        </div>
      </div>
    );
  }

  const ModeToggle = () => (
    <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
      <button
        onClick={() => setHubView('subjects')}
        title="Tất cả môn"
        style={{
          padding: '10px 12px', borderRadius: 12, fontWeight: 700, fontSize: 14,
          border: '2px solid var(--border)', background: 'var(--card)',
          color: 'var(--text)', cursor: 'pointer',
        }}
      >← Môn</button>
      {[['learn', '📚 Học theo chủ đề'], ['exam', '📝 Làm đề & Thi thử']].map(([key, label]) => (
        <button
          key={key}
          onClick={() => switchMode(key)}
          style={{
            flex: 1, padding: '10px 8px', borderRadius: 12, fontWeight: 700, fontSize: 14,
            border: `2px solid var(--primary, #2196f3)`,
            background: mode === key ? 'var(--primary, #2196f3)' : 'transparent',
            color: mode === key ? '#fff' : 'var(--primary, #2196f3)', cursor: 'pointer',
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );

  // ── EXAM MODE ──────────────────────────────────────────────────────────────
  if (mode === 'exam') {
    const isSW = examData?.paper?.subject === 'toeic_sw';

    // TOEIC S&W result — estimated 200-scale band + per-task feedback/tips.
    if (examView === 'result' && examResult && isSW) {
      const r = examResult;
      const byOrder = [...(r.review || [])].sort((a, b) => a.order_index - b.order_index);
      return (
        <div style={{ padding: '16px', maxWidth: 560, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 18 }}>
            <div style={{ fontSize: 56 }}>{r.passed ? '🏆' : '🗣️'}</div>
            <div style={{ fontSize: 34, fontWeight: 800 }}>~{r.estimated_200}<span style={{ fontSize: 18, fontWeight: 600, color: 'var(--muted)' }}>/200</span></div>
            <div style={{ fontSize: 14, color: 'var(--muted)', marginTop: 2 }}>
              {Number(r.score).toFixed(1)}/{Number(r.max_score).toFixed(1)} điểm · {r.percent}%
              {r.auto ? ' · hết giờ tự nộp ⏱️' : ''}
            </div>
            <div style={{
              display: 'inline-block', marginTop: 8, padding: '6px 16px', borderRadius: 99,
              fontWeight: 700, color: '#fff', background: r.passed ? '#2e7d32' : '#ef5350',
            }}>
              {r.passed ? '✅ Đạt' : `❌ Chưa đạt (cần ${r.pass_percent}%)`}
            </div>
            {r.disclaimer && (
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 10, fontStyle: 'italic' }}>
                ⚠️ {r.disclaimer}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
            {byOrder.map((q, i) => (
              <div key={q.question_id} style={{
                background: 'var(--card)', borderRadius: 12, padding: 14,
                borderLeft: '4px solid #7c3aed',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ fontWeight: 700 }}>Câu {i + 1}</div>
                  <div style={{ fontWeight: 800, color: '#7c3aed' }}>
                    {Number(q.score).toFixed(1)}/{Number(q.max_score).toFixed(1)}
                  </div>
                </div>
                <div style={{ fontSize: 13, color: 'var(--muted)', whiteSpace: 'pre-wrap', marginBottom: 6 }}>
                  Bài làm: <i>{q.given || '— (bỏ trống)'}</i>
                </div>
                {q.feedback && <div style={{ fontSize: 13, color: 'var(--text)' }}>📝 {q.feedback}</div>}
                {Array.isArray(q.tips) && q.tips.length > 0 && (
                  <ul style={{ fontSize: 13, color: 'var(--text)', margin: '6px 0 0', paddingLeft: 18 }}>
                    {q.tips.map((t, k) => <li key={k}>{t}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn-sm secondary" style={{ flex: 1, minHeight: 48 }}
              onClick={() => setExamView('list')}>📋 Đề khác</button>
            <button className="btn-sm primary" style={{ flex: 1, minHeight: 48 }}
              onClick={() => startExam(examData.paper)}>🔄 Làm lại</button>
          </div>
        </div>
      );
    }

    // Result
    if (examView === 'result' && examResult) {
      const r = examResult;
      const byOrder = [...(r.review || [])].sort((a, b) => a.order_index - b.order_index);
      return (
        <div style={{ padding: '16px', maxWidth: 560, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 20 }}>
            <div style={{ fontSize: 64 }}>{r.passed ? '🏆' : '📚'}</div>
            <div style={{ fontSize: 30, fontWeight: 800 }}>{r.percent}%</div>
            <div style={{ fontSize: 16, color: 'var(--muted)' }}>
              {r.correct_count}/{r.total_questions} câu đúng
              {r.auto ? ' · hết giờ tự nộp ⏱️' : ''}
            </div>
            <div style={{
              display: 'inline-block', marginTop: 8, padding: '6px 16px', borderRadius: 99,
              fontWeight: 700, color: '#fff',
              background: r.passed ? '#2e7d32' : '#ef5350',
            }}>
              {r.passed ? '✅ Đạt' : `❌ Chưa đạt (cần ${r.pass_percent}%)`}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
            {byOrder.map((q, i) => (
              <div key={q.question_id} style={{
                background: 'var(--card)', borderRadius: 12, padding: 14,
                borderLeft: `4px solid ${q.correct === false ? '#ef5350' : q.correct ? '#4caf50' : '#ff9800'}`,
              }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {q.correct === false ? '✗' : q.correct ? '✓' : '✎'} Câu {i + 1}
                </div>
                <div style={{ fontSize: 13, color: 'var(--muted)' }}>
                  Bạn chọn: <b>{q.given || '—'}</b>
                  {q.correct === false && <> · Đáp án: <b style={{ color: '#2e7d32' }}>{q.expected}</b></>}
                  {q.correct === null && <> · Đáp án mẫu: <b>{q.expected}</b></>}
                </div>
                {q.explanation && (
                  <div style={{ fontSize: 13, marginTop: 6, color: 'var(--text)' }}>💡 {q.explanation}</div>
                )}
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn-sm secondary" style={{ flex: 1, minHeight: 48 }}
              onClick={() => setExamView('list')}>📋 Đề khác</button>
            <button className="btn-sm primary" style={{ flex: 1, minHeight: 48 }}
              onClick={() => startExam(examData.paper)}>🔄 Làm lại</button>
          </div>
        </div>
      );
    }

    // TOEIC S&W playing — free-text writing / spoken transcript per task.
    if (examView === 'playing' && examData && isSW) {
      const skill = (examData.paper.skill || 'writing').toLowerCase();
      const isSpeaking = skill === 'speaking';
      const q = examData.questions[examQIndex];
      const total = examData.questions.length;
      const text = examAnswers[q.question_id] || '';
      const words = text.trim() ? text.trim().split(/\s+/).length : 0;
      const answered = Object.values(examAnswers).filter(v => (v || '').trim()).length;
      const low = examTimeLeft <= 60;
      const taskLabel = SW_TASK_LABELS[q.topic] || (isSpeaking ? 'Nói' : 'Viết');
      return (
        <div style={{ padding: '16px', maxWidth: 560, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
            <div style={{ flex: 1, fontWeight: 700, fontSize: 15 }}>{examData.paper.title}</div>
            <div style={{
              fontWeight: 800, fontSize: 18, padding: '4px 12px', borderRadius: 10,
              background: low ? '#ffebee' : '#ede7f6', color: low ? '#c62828' : '#5e35b1',
            }}>⏱️ {fmtTime(examTimeLeft)}</div>
          </div>

          {/* Task nav dots */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
            {examData.questions.map((qq, i) => {
              const done = (examAnswers[qq.question_id] || '').trim().length > 0;
              return (
                <button key={qq.question_id} onClick={() => { stopRecording(); setExamQIndex(i); }}
                  style={{
                    width: 32, height: 32, borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: 'pointer',
                    border: `2px solid ${i === examQIndex ? '#7c3aed' : '#ccc'}`,
                    background: done ? '#d1c4e9' : 'var(--card)', color: 'var(--text)',
                  }}>{i + 1}</button>
              );
            })}
          </div>

          <div style={{ background: 'var(--card)', borderRadius: 16, padding: '18px 16px', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{
                fontSize: 12, fontWeight: 700, color: '#fff', background: '#7c3aed',
                padding: '3px 10px', borderRadius: 99,
              }}>{isSpeaking ? '🗣️ Nói' : '✍️ Viết'} · {taskLabel}</span>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>Câu {examQIndex + 1}/{total} {q.emoji}</span>
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4, whiteSpace: 'pre-wrap' }}>{q.question}</div>
            {q.question_vi && <div style={{ fontSize: 14, color: 'var(--muted)' }}>{q.question_vi}</div>}
          </div>

          {isSpeaking && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <button onClick={() => toggleRecord(q.question_id)}
                style={{
                  minHeight: 44, padding: '0 16px', borderRadius: 12, fontWeight: 700, cursor: 'pointer',
                  border: `2px solid ${recording ? '#c62828' : '#7c3aed'}`,
                  background: recording ? '#ffebee' : 'var(--card)',
                  color: recording ? '#c62828' : '#7c3aed',
                }}>
                {recording ? '⏹️ Dừng ghi' : '🎤 Ghi âm để nói'}
              </button>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                {recording ? 'Đang nghe…' : 'Hoặc gõ lời bạn nói bên dưới'}
              </span>
            </div>
          )}

          <textarea
            value={text}
            onChange={e => setExamAnswers(prev => ({ ...prev, [q.question_id]: e.target.value }))}
            placeholder={isSpeaking ? 'Lời nói của bạn (transcript) sẽ hiện ở đây…' : 'Viết bài của bạn ở đây…'}
            rows={isSpeaking ? 5 : 8}
            style={{
              width: '100%', boxSizing: 'border-box', borderRadius: 12, padding: 12, fontSize: 15,
              border: '2px solid var(--border, #e0e0e0)', background: 'var(--card)', color: 'var(--text)',
              resize: 'vertical', marginBottom: 6, fontFamily: 'inherit',
            }}
          />
          <div style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'right', marginBottom: 14 }}>
            {words} từ
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn-sm secondary" style={{ flex: 1, minHeight: 48 }}
              disabled={examQIndex === 0}
              onClick={() => { stopRecording(); setExamQIndex(i => Math.max(0, i - 1)); }}>← Trước</button>
            {examQIndex < total - 1 ? (
              <button className="btn-sm primary" style={{ flex: 1, minHeight: 48 }}
                onClick={() => { stopRecording(); setExamQIndex(i => Math.min(total - 1, i + 1)); }}>Sau →</button>
            ) : (
              <button className="btn-sm primary" style={{ flex: 1, minHeight: 48 }}
                disabled={examSubmitting}
                onClick={() => finishExam(false)}>
                {examSubmitting ? 'Bi đang chấm…' : `📨 Nộp bài (${answered}/${total})`}
              </button>
            )}
          </div>
        </div>
      );
    }

    // Playing
    if (examView === 'playing' && examData) {
      const q = examData.questions[examQIndex];
      const total = examData.questions.length;
      const answered = Object.keys(examAnswers).length;
      const low = examTimeLeft <= 60;
      return (
        <div style={{ padding: '16px', maxWidth: 560, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
            <div style={{ flex: 1, fontWeight: 700, fontSize: 15 }}>{examData.paper.title}</div>
            <div style={{
              fontWeight: 800, fontSize: 18, padding: '4px 12px', borderRadius: 10,
              background: low ? '#ffebee' : '#e3f2fd', color: low ? '#c62828' : '#1565c0',
            }}>⏱️ {fmtTime(examTimeLeft)}</div>
          </div>

          {/* Question nav dots */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
            {examData.questions.map((qq, i) => {
              const done = examAnswers[qq.question_id] != null;
              return (
                <button key={qq.question_id} onClick={() => setExamQIndex(i)}
                  style={{
                    width: 32, height: 32, borderRadius: 8, fontWeight: 700, fontSize: 13,
                    cursor: 'pointer',
                    border: `2px solid ${i === examQIndex ? 'var(--primary, #2196f3)' : '#ccc'}`,
                    background: done ? '#c8e6c9' : 'var(--card)',
                    color: 'var(--text)',
                  }}>{i + 1}</button>
              );
            })}
          </div>

          <div style={{ background: 'var(--card)', borderRadius: 16, padding: '20px 16px', marginBottom: 16 }}>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 6 }}>
              Câu {examQIndex + 1}/{total} {q.emoji}
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{q.question}</div>
            {q.question_vi && <div style={{ fontSize: 14, color: 'var(--muted)' }}>{q.question_vi}</div>}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
            {q.options.map(option => {
              const chosen = examAnswers[q.question_id] === option;
              return (
                <button key={option} onClick={() => pickAnswer(q.question_id, option)}
                  style={{
                    minHeight: 52, fontSize: 16, fontWeight: 600, borderRadius: 12, textAlign: 'left',
                    padding: '0 16px', cursor: 'pointer',
                    border: `2px solid ${chosen ? 'var(--primary, #2196f3)' : 'var(--border, #e0e0e0)'}`,
                    background: chosen ? '#e3f2fd' : 'var(--card)', color: 'var(--text)',
                  }}>{option}</button>
              );
            })}
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn-sm secondary" style={{ flex: 1, minHeight: 48 }}
              disabled={examQIndex === 0}
              onClick={() => setExamQIndex(i => Math.max(0, i - 1))}>← Trước</button>
            {examQIndex < total - 1 ? (
              <button className="btn-sm primary" style={{ flex: 1, minHeight: 48 }}
                onClick={() => setExamQIndex(i => Math.min(total - 1, i + 1))}>Sau →</button>
            ) : (
              <button className="btn-sm primary" style={{ flex: 1, minHeight: 48 }}
                disabled={examSubmitting}
                onClick={() => finishExam(false)}>
                {examSubmitting ? 'Đang nộp…' : `📨 Nộp bài (${answered}/${total})`}
              </button>
            )}
          </div>
        </div>
      );
    }

    // Exam list for a track
    // Parent tự tạo đề (chỉ gia đình mình thấy).
    if (examView === 'builder') {
      return (
        <div style={{ padding: '16px', maxWidth: 560, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <button className="btn-sm secondary" style={{ minWidth: 40 }}
              onClick={() => setExamView('tracks')}>←</button>
            <div style={{ fontWeight: 700, fontSize: 18 }}>Tạo đề của tôi</div>
          </div>
          <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 12 }}>
            Đề bạn tạo chỉ tài khoản của bạn nhìn thấy (xuất hiện ở mục "Luyện tập").
          </div>
          <ExamBuilder
            onCreated={() => { setExamView('tracks'); loadTracks(); }}
            onCancel={() => setExamView('tracks')} />
        </div>
      );
    }

    if (examView === 'list' && selectedTrack) {
      return (
        <div style={{ padding: '16px', maxWidth: 560, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <button className="btn-sm secondary" style={{ minWidth: 40 }}
              onClick={() => setExamView('tracks')}>←</button>
            <div style={{ fontWeight: 700, fontSize: 18 }}>{selectedTrack.label}</div>
          </div>
          {examLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}><div className="spinner" /></div>
          ) : examList.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
              Chưa có đề thi cho mục này. Nội dung sẽ được bổ sung dần.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {examList.map(ex => {
                const own = ex.source === 'custom' && ex.family_id;
                return (
                  <div key={ex.paper_id} style={{ display: 'flex', alignItems: 'stretch', gap: 8 }}>
                    <button onClick={() => startExam(ex)}
                      style={{
                        flex: 1, display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
                        borderRadius: 12, background: 'var(--card)', cursor: 'pointer', textAlign: 'left',
                        border: '2px solid var(--border, #e0e0e0)',
                      }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700 }}>
                          {ex.title}{own && <span style={{ fontSize: 11, color: '#2563eb' }}> · đề của tôi</span>}
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                          {ex.total_questions} câu · {ex.duration_minutes} phút · đạt ≥{ex.pass_percent}%
                          {ex.attempts > 0 && ` · đã làm ${ex.attempts} lần`}
                        </div>
                      </div>
                      {ex.best_percent != null && (
                        <div style={{
                          fontWeight: 800, fontSize: 15,
                          color: ex.best_percent >= ex.pass_percent ? '#2e7d32' : '#ef5350',
                        }}>{ex.best_percent}%</div>
                      )}
                      <span style={{ fontSize: 18, color: 'var(--muted)' }}>▶</span>
                    </button>
                    {own && (
                      <button title="Xóa đề của tôi"
                        onClick={async () => {
                          if (!window.confirm(`Xóa đề "${ex.title}"?`)) return;
                          const r = await deleteExam(ex.paper_id);
                          if (r) { showToast('Đã xóa đề'); openTrack(selectedTrack); }
                          else showToast('Xóa thất bại');
                        }}
                        style={{
                          width: 44, borderRadius: 12, border: '2px solid #ef5350',
                          background: 'transparent', color: '#ef5350', cursor: 'pointer', fontSize: 16,
                        }}>🗑️</button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      );
    }

    // Tracks catalog (default exam view)
    const grouped = {};
    tracks.forEach(t => { (grouped[t.kind] = grouped[t.kind] || []).push(t); });
    const KIND_LABELS = {
      practice: 'Luyện tập', competition: '🏆 Đội tuyển HSG',
      exam: '🎓 Thi chuyển cấp', roadmap: '🌐 Lộ trình ngoại ngữ',
    };
    return (
      <div style={{ padding: '16px', maxWidth: 560, margin: '0 auto' }}>
        <ModeToggle />
        <button onClick={() => setExamView('builder')}
          style={{
            width: '100%', marginBottom: 16, padding: '12px', borderRadius: 12,
            border: '2px dashed var(--primary, #2196f3)', background: 'transparent',
            color: 'var(--primary, #2196f3)', fontWeight: 700, fontSize: 14, cursor: 'pointer',
          }}>➕ Tạo đề của tôi</button>
        {examLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><div className="spinner" /></div>
        ) : (
          Object.entries(grouped).map(([kind, items]) => (
            <div key={kind} style={{ marginBottom: 20 }}>
              <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>
                {KIND_LABELS[kind] || kind}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {items.map(t => (
                  <button key={t.track} onClick={() => openTrack(t)}
                    style={{
                      background: 'var(--card)', borderRadius: 14, padding: '16px 12px',
                      border: `2px solid ${TRACK_KIND_COLORS[t.kind] || '#999'}33`,
                      cursor: 'pointer', textAlign: 'left',
                    }}>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{t.label}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                      {t.paper_count} đề{t.levels?.length ? ` · ${t.levels.length} cấp độ` : ''}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    );
  }

  // ── LEARN MODE (default) ─────────────────────────────────────────────────
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
      <ModeToggle />
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
