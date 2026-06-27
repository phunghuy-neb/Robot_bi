import { useState } from 'react';
import { askBiExplain } from '../../services/api.js';

// "Hỏi Bi vì sao sai" (spec 007 US7): LLM gợi mở (Socratic), đã qua SafetyFilter ở server.
export default function AskBi({ question, childAnswer, correctAnswer }) {
  const [state, setState] = useState('idle'); // idle | loading | done
  const [text, setText] = useState('');

  async function ask() {
    setState('loading');
    try {
      const r = await askBiExplain({ question, childAnswer, correctAnswer });
      setText(r?.explanation || 'Con thử đọc kỹ lại câu hỏi nhé!');
    } catch (_) {
      setText('Con thử đọc kỹ lại câu hỏi nhé!');
    }
    setState('done');
  }

  if (state === 'done') {
    return <div className="ask-bi-answer">🤖 {text}</div>;
  }
  return (
    <button type="button" className="btn-sm secondary" style={{ marginTop: 10 }} onClick={ask} disabled={state === 'loading'}>
      {state === 'loading' ? '🤖 Bi đang nghĩ...' : '🤖 Hỏi Bi vì sao'}
    </button>
  );
}
