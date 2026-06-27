import { masteryBand } from './constants.js';
import CollapsibleSection from '../CollapsibleSection.jsx';
import SectionState from '../SectionState.jsx';

// Màu thanh theo accuracy (band SmartScore) — đồng bộ masteryBand().
function barColor(acc) {
  if (acc >= 90) return '#2563eb';
  if (acc >= 80) return '#16a34a';
  if (acc >= 60) return '#f59e0b';
  return '#dc2626';
}

// Mastery theo chủ đề (spec 007 US6): thanh % + band (màu KÈM chữ), yếu xếp trước.
export default function MasteryByTopic({ topics, loading }) {
  return (
    <CollapsibleSection title="🎯 Mức thành thạo theo chủ đề" defaultExpanded={false}>
      {loading ? (
        <SectionState state="loading" loadingText="Đang tính mức thành thạo..." />
      ) : !topics || topics.length === 0 ? (
        <SectionState state="empty" emptyText="Làm vài đề để xem mức thành thạo từng chủ đề." emptyIcon="📊" />
      ) : (
        topics.map(t => {
          const band = masteryBand(t.accuracy);
          return (
            <div key={t.topic} className="subject-progress-row">
              <div className="subject-progress-head">
                <span>{t.topic}</span>
                <span className={band.cls}>{t.accuracy}% · {band.label}</span>
              </div>
              <div className="subject-progress-bar">
                <div className="subject-progress-fill" style={{ width: `${t.accuracy}%`, background: barColor(t.accuracy) }} />
              </div>
            </div>
          );
        })
      )}
    </CollapsibleSection>
  );
}
