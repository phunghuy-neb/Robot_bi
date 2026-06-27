export default function SubjectCard({ subject, onPick }) {
  return (
    <button type="button" className="subject-card" onClick={() => onPick(subject)}>
      <span className="subject-card-emoji">{subject.emoji || '📚'}</span>
      <span className="subject-card-name">{subject.label || subject.subject}</span>
      <span className="subject-card-meta">{subject.paper_count || 0} đề</span>
    </button>
  );
}
