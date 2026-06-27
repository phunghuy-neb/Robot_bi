import { useState } from 'react';
import { getPracticeQuestions, gradePractice, showToast } from '../../services/api.js';
import SectionState from '../SectionState.jsx';

// Luyện theo bài (spec 007 US4): làm câu đơn lẻ, server chấm + giải thích NGAY sau mỗi câu.
// (US7 sẽ thêm 🔊 Bi đọc đề + "Hỏi Bi vì sao".)
export default function QuestionRunner({ subject, subjectLabel, topic, onExit }) {
  const [step, setStep] = useState('config'); // config | loading | playing | done
  const [count, setCount] = useState(10);
  const [questions, setQuestions] = useState([]);
  const [idx, setIdx] = useState(0);
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState(null); // {correct, correct_answer, explanation}
  const [score, setScore] = useState(0);
  const [busy, setBusy] = useState(false);

  async function start() {
    setStep('loading');
    const data = await getPracticeQuestions(subject, topic, count);
    const qs = data?.questions || [];
    if (!qs.length) { setStep('config'); showToast('Môn này chưa có câu luyện tập'); return; }
    setQuestions(qs); setIdx(0); setScore(0); setAnswer(''); setFeedback(null); setStep('playing');
  }

  async function submit(opt) {
    if (busy || feedback) return;
    setAnswer(opt); setBusy(true);
    const res = await gradePractice(questions[idx].question_id, opt);
    setBusy(false);
    if (res) { setFeedback(res); if (res.correct) setScore(s => s + 1); }
    else { setAnswer(''); showToast('Lỗi chấm bài, thử lại'); }
  }

  function next() {
    if (idx + 1 < questions.length) { setIdx(i => i + 1); setAnswer(''); setFeedback(null); }
    else setStep('done');
  }

  const q = questions[idx];

  return (
    <div>
      <div className="page-header">
        <button className="btn-back" onClick={onExit}>← {subjectLabel || 'Môn'}</button>
        <div className="page-title">📝 Luyện theo bài</div>
      </div>
      <div className="page-body learn-quiz">
        {step === 'config' && (
          <div className="card">
            <div className="form-label">Số câu luyện</div>
            <div style={{ display: 'flex', gap: 8, margin: '8px 0 16px', flexWrap: 'wrap' }}>
              {[5, 10, 20].map(n => (
                <button key={n} className={`pill-tab${count === n ? ' active' : ''}`} onClick={() => setCount(n)}>{n} câu</button>
              ))}
            </div>
            <button className="btn-action primary" onClick={start}>🚀 Bắt đầu</button>
          </div>
        )}
        {step === 'loading' && <SectionState state="loading" loadingText="Đang tải câu hỏi..." />}
        {step === 'playing' && q && (
          <div className="card">
            <div style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 8 }}>Câu {idx + 1}/{questions.length} · Đúng {score}</div>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 12 }}>{q.emoji ? `${q.emoji} ` : ''}{q.question}</div>
            {q.question_vi && q.question_vi !== q.question && (
              <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 12 }}>{q.question_vi}</div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {(q.options || []).map(opt => (
                <button
                  key={opt}
                  className={`game-option${feedback && opt === feedback.correct_answer ? ' selected' : ''}`}
                  disabled={busy || !!feedback}
                  onClick={() => submit(opt)}
                  style={feedback && opt === answer && !feedback.correct ? { borderColor: '#dc2626' } : undefined}
                >
                  {opt}
                </button>
              ))}
            </div>
            {feedback && (
              <>
                <div className={`game-feedback ${feedback.correct ? 'correct' : 'wrong'}`} style={{ marginTop: 12 }}>
                  <b>{feedback.correct ? '✅ Đúng rồi!' : '❌ Chưa đúng'}</b>
                  {!feedback.correct && <span>Đáp án đúng: {feedback.correct_answer}</span>}
                  {feedback.explanation && <span>{feedback.explanation}</span>}
                </div>
                <button className="btn-action primary" style={{ marginTop: 12 }} onClick={next}>
                  {idx + 1 < questions.length ? 'Câu tiếp →' : 'Kết thúc'}
                </button>
              </>
            )}
          </div>
        )}
        {step === 'done' && (
          <div className="card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48 }}>{score === questions.length ? '🏆' : score >= questions.length * 0.6 ? '🎉' : '💪'}</div>
            <div style={{ fontSize: 24, fontWeight: 800, margin: '8px 0' }}>{score}/{questions.length} câu đúng</div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 12 }}>
              <button className="btn-sm primary" onClick={() => setStep('config')}>Làm lại</button>
              <button className="btn-sm secondary" onClick={onExit}>Xong</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
