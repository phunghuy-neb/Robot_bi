import { useState } from 'react';
import { createCustomExam, showToast } from '../services/api.js';

// Form tạo đề MCQ dùng chung cho Admin (isGlobal) và Parent (đề cá nhân).
// onCreated(paperId) được gọi khi tạo thành công.
function emptyQ() {
  return { question: '', options: ['', '', '', ''], answer: '', explanation: '' };
}

export default function ExamBuilder({ isGlobal = false, onCreated, onCancel }) {
  const [title, setTitle] = useState('');
  const [subject, setSubject] = useState('custom');
  const [questions, setQuestions] = useState([emptyQ()]);
  const [busy, setBusy] = useState(false);

  function setQ(i, patch) {
    setQuestions(qs => qs.map((q, idx) => idx === i ? { ...q, ...patch } : q));
  }
  function setOpt(i, j, val) {
    setQuestions(qs => qs.map((q, idx) => idx === i
      ? { ...q, options: q.options.map((o, k) => k === j ? val : o) } : q));
  }

  async function submit() {
    if (!title.trim()) { showToast('Nhập tên đề'); return; }
    const clean = questions
      .map(q => ({
        question: q.question.trim(),
        options: q.options.map(o => o.trim()).filter(Boolean),
        answer: q.answer.trim(),
        explanation: q.explanation.trim(),
      }))
      .filter(q => q.question && q.options.length >= 2 && q.options.includes(q.answer));
    if (!clean.length) {
      showToast('Cần ≥1 câu hợp lệ: có câu hỏi, ≥2 lựa chọn, và đáp án nằm trong lựa chọn');
      return;
    }
    setBusy(true);
    const res = await createCustomExam({ title: title.trim(), subject: subject.trim() || 'custom', is_global: isGlobal, questions: clean });
    setBusy(false);
    if (res?.ok) { showToast(`Đã tạo đề (${res.total_questions} câu)`); onCreated?.(res.paper_id); }
    else showToast('Tạo đề thất bại');
  }

  const inp = { width: '100%', boxSizing: 'border-box', padding: '8px 10px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', fontSize: 14 };
  const card = { background: 'var(--card,#fff)', borderRadius: 12, padding: 14, marginBottom: 12 };

  return (
    <div>
      <div style={{ ...card, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <input style={{ ...inp, flex: 2, minWidth: 200 }} placeholder="Tên đề thi"
          value={title} onChange={e => setTitle(e.target.value)} />
        <input style={{ ...inp, flex: 1, minWidth: 120 }} placeholder="Môn (vd: math)"
          value={subject} onChange={e => setSubject(e.target.value)} />
      </div>

      {questions.map((q, i) => (
        <div key={i} style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <b>Câu {i + 1}</b>
            {questions.length > 1 && (
              <button onClick={() => setQuestions(qs => qs.filter((_, k) => k !== i))}
                style={{ border: 'none', background: 'none', color: '#dc2626', cursor: 'pointer', fontWeight: 700 }}>Xóa câu</button>
            )}
          </div>
          <input style={{ ...inp, marginBottom: 8 }} placeholder="Câu hỏi"
            value={q.question} onChange={e => setQ(i, { question: e.target.value })} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
            {q.options.map((o, j) => (
              <input key={j} style={inp} placeholder={`Lựa chọn ${j + 1}`}
                value={o} onChange={e => setOpt(i, j, e.target.value)} />
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input style={{ ...inp, flex: 1, minWidth: 140 }} placeholder="Đáp án đúng (chép đúng 1 lựa chọn)"
              value={q.answer} onChange={e => setQ(i, { answer: e.target.value })} />
            <input style={{ ...inp, flex: 1, minWidth: 140 }} placeholder="Giải thích (tùy chọn)"
              value={q.explanation} onChange={e => setQ(i, { explanation: e.target.value })} />
          </div>
        </div>
      ))}

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button onClick={() => setQuestions(qs => [...qs, emptyQ()])}
          style={{ padding: '9px 14px', borderRadius: 8, border: '1px dashed #94a3b8', background: 'transparent', cursor: 'pointer', fontWeight: 700 }}>+ Thêm câu</button>
        <div style={{ flex: 1 }} />
        {onCancel && <button onClick={onCancel} style={{ padding: '9px 14px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', background: 'transparent', cursor: 'pointer' }}>Hủy</button>}
        <button disabled={busy} onClick={submit}
          style={{ padding: '9px 16px', borderRadius: 8, border: 'none', background: '#16a34a', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>
          {busy ? 'Đang tạo…' : (isGlobal ? '✅ Tạo đề chung' : '✅ Tạo đề của tôi')}
        </button>
      </div>
    </div>
  );
}
