import { useState, useEffect } from 'react';
import { BO_GD_SUBJECTS, MOCK_EXAM_SUBJECTS } from './constants.js';
import { showToast, getMistakes, getTopicMastery } from '../../services/api.js';
import ModeCard from './ModeCard.jsx';
import MasteryByTopic from './MasteryByTopic.jsx';

// Trang chi tiết 1 môn: thẻ chế độ (cấp 1) + gating + 2 thẻ nổi bật.
// Lát US2: route các chế độ vào luồng học/đề hiện có. US3-US7 sẽ tinh chỉnh từng chế độ
// (cấu hình timer, luyện theo bài, sổ lỗi, mastery, hỏi Bi).
export default function SubjectDetail({ subject, onBack, onEnterLearn, onEnterExam, onEnterPractice, onOpenErrorBook }) {
  const key = subject?.subject;
  const [mistakeCount, setMistakeCount] = useState(null);
  const [masteryTopics, setMasteryTopics] = useState(null);
  const [masteryLoading, setMasteryLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getMistakes(key).then(d => { if (alive) setMistakeCount(d?.count ?? 0); }).catch(() => {});
    setMasteryLoading(true);
    getTopicMastery(key)
      .then(d => { if (alive) { setMasteryTopics(d?.topics || []); setMasteryLoading(false); } })
      .catch(() => { if (alive) setMasteryLoading(false); });
    return () => { alive = false; };
  }, [key]);
  const hasLotrinh = ['en', 'math', 'science'].includes(key);
  const isBoGD = BO_GD_SUBJECTS.includes(key);
  const isMock = MOCK_EXAM_SUBJECTS.includes(key);

  const modes = [
    {
      icon: '🧭', label: 'Lộ trình', sub: hasLotrinh ? 'Học từng bước' : 'Sắp có',
      onClick: () => (hasLotrinh ? onEnterLearn() : showToast('Lộ trình môn này sắp có')),
    },
    {
      icon: '📝', label: 'Luyện theo bài', sub: 'Từng câu, chấm ngay',
      onClick: onEnterPractice,
    },
    {
      icon: '📄', label: 'Luyện theo đề', sub: 'Làm trọn đề', onClick: onEnterExam,
    },
  ];
  if (isBoGD) {
    modes.push({ icon: '🏆', label: 'Luyện HSG', sub: 'Đội tuyển học sinh giỏi', onClick: onEnterExam });
    modes.push({ icon: '🎓', label: 'Thi chuyển cấp', sub: 'Vào lớp 6 / 10 / THPT', onClick: onEnterExam });
  } else if (isMock) {
    modes.push({ icon: '🎯', label: 'Thi thử như thật', sub: 'Mô phỏng đề thật', onClick: onEnterExam });
  } else {
    modes.push({ icon: '⭐', label: 'Luyện tập nâng cao', sub: 'Thử thách thêm', onClick: onEnterExam });
  }

  return (
    <div>
      <div className="page-header">
        <button className="btn-back" onClick={onBack}>← Tất cả môn</button>
        <div className="page-title">{subject?.emoji || '📚'} {subject?.label || key}</div>
        <div className="page-subtitle">{subject?.paper_count || 0} đề · chọn cách học bên dưới</div>
      </div>

      <div className="page-body learn-browse">
        <div className="subject-detail-grid">
          <section>
            <div className="mode-card-grid">
              {modes.map((m, i) => <ModeCard key={i} {...m} />)}
            </div>
          </section>
          <aside>
            {/* Số liệu thật ở US5 (sổ lỗi) + US6 (chủ đề yếu) */}
            <button type="button" className="card highlight-card" onClick={onOpenErrorBook}>
              📕 Câu hay sai <span className="muted">({mistakeCount == null ? '…' : `${mistakeCount} câu`})</span>
            </button>
            <MasteryByTopic topics={masteryTopics} loading={masteryLoading} />
          </aside>
        </div>
      </div>
    </div>
  );
}
