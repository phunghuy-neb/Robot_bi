import { useState, useEffect } from 'react';
import { getLearningSubjects } from '../../services/api.js';
import { CATEGORIES, OTHER_CATEGORY } from './constants.js';
import SubjectCard from './SubjectCard.jsx';
import SectionState from '../SectionState.jsx';

// Lưới môn subject-first: nhóm theo danh mục + tìm kiếm. Full-width (.learn-browse).
export default function SubjectGrid({ onPick }) {
  const [state, setState] = useState('loading');
  const [subjects, setSubjects] = useState([]);
  const [q, setQ] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    setState('loading');
    try {
      const list = await getLearningSubjects();
      setSubjects(list || []);
      setState(list && list.length ? 'data' : 'empty');
    } catch (_) {
      setState('error');
    }
  }

  const query = q.trim().toLowerCase();
  const match = s => !query || (s.label || s.subject || '').toLowerCase().includes(query);

  // Nhóm theo CATEGORIES (giữ thứ tự); môn không khớp → "Khác".
  const groups = CATEGORIES
    .map(cat => ({ ...cat, items: subjects.filter(s => cat.keys.includes(s.subject) && match(s)) }))
    .filter(g => g.items.length);
  const others = subjects.filter(s => !CATEGORIES.some(c => c.keys.includes(s.subject)) && match(s));
  if (others.length) groups.push({ ...OTHER_CATEGORY, items: others });

  return (
    <div className="learn-browse">
      <input
        className="form-input learn-search"
        placeholder="🔍 Tìm môn học..."
        value={q}
        onChange={e => setQ(e.target.value)}
      />
      {state === 'loading' && <SectionState state="loading" loadingText="Đang tải môn học..." />}
      {state === 'error' && <SectionState state="error" errorText="Không tải được danh sách môn." onRetry={load} />}
      {state === 'empty' && <SectionState state="empty" emptyText="Chưa có môn học nào." emptyIcon="📚" />}
      {state === 'data' && (
        groups.length === 0 ? (
          <SectionState state="empty" emptyText="Không tìm thấy môn phù hợp." emptyIcon="🔍" />
        ) : (
          groups.map(g => (
            <div key={g.name}>
              <div className="subject-cat-title">{g.icon} {g.name}</div>
              <div className="subject-grid">
                {g.items.map(s => <SubjectCard key={s.subject} subject={s} onPick={onPick} />)}
              </div>
            </div>
          ))
        )
      )}
    </div>
  );
}
