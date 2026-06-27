import { useState, useEffect } from 'react';
import { getMistakes } from '../../services/api.js';
import SectionState from '../SectionState.jsx';
import QuestionRunner from './QuestionRunner.jsx';

// Sổ lỗi (spec 007 US5): câu trẻ hay sai → ôn lại riêng, nhóm theo chủ đề.
export default function ErrorBook({ subject, subjectLabel, onExit }) {
  const [state, setState] = useState('loading');
  const [mistakes, setMistakes] = useState([]);
  const [practicing, setPracticing] = useState(false);

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  async function load() {
    setState('loading');
    const d = await getMistakes(subject);
    if (!d) { setState('error'); return; }
    setMistakes(d.mistakes || []);
    setState((d.mistakes || []).length ? 'data' : 'empty');
  }

  if (practicing) {
    return (
      <QuestionRunner
        subject={subject}
        subjectLabel={subjectLabel}
        providedQuestions={mistakes}
        onExit={() => { setPracticing(false); load(); }}
      />
    );
  }

  const groups = {};
  mistakes.forEach(m => { (groups[m.topic || 'Khác'] = groups[m.topic || 'Khác'] || []).push(m); });

  return (
    <div>
      <div className="page-header">
        <button className="btn-back" onClick={onExit}>← {subjectLabel || 'Môn'}</button>
        <div className="page-title">📕 Câu hay sai</div>
      </div>
      <div className="page-body learn-browse">
        {state === 'loading' && <SectionState state="loading" loadingText="Đang tải sổ lỗi..." />}
        {state === 'error' && <SectionState state="error" errorText="Không tải được sổ lỗi." onRetry={load} />}
        {state === 'empty' && <SectionState state="empty" emptyText="Chưa có câu sai nào — giỏi quá!" emptyIcon="🎉" />}
        {state === 'data' && (
          <>
            <button className="btn-action primary" style={{ marginBottom: 14 }} onClick={() => setPracticing(true)}>
              🔁 Luyện lại {mistakes.length} câu
            </button>
            {Object.entries(groups).map(([topic, items]) => (
              <div key={topic} className="card">
                <div className="card-header"><span className="card-title">{topic} ({items.length})</span></div>
                {items.map(m => (
                  <div key={m.question_id} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 14 }}>
                    {m.emoji ? `${m.emoji} ` : ''}{m.question}
                  </div>
                ))}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
