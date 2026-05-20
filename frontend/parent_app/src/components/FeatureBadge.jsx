const LABELS = {
  'coming-soon': 'Sắp hỗ trợ',
  'mock-data': 'Dữ liệu mẫu',
  'no-backend': 'Chưa kết nối backend',
};

export default function FeatureBadge({ type }) {
  return (
    <span className={`feature-badge ${type}`}>
      {LABELS[type] || type}
    </span>
  );
}
