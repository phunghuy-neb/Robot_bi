// Hằng số cấu hình tab Học tập (spec 007). Dễ chỉnh — không hardcode rải rác.

// Nhóm danh mục môn (theo Resolved Decisions 007). key = subject key của backend.
export const CATEGORIES = [
  { name: 'Ngôn ngữ',        icon: '🗣', keys: ['en', 'chinese', 'japanese', 'korean', 'ielts', 'toeic_lr', 'toeic_sw'] },
  { name: 'Toán & KHTN',     icon: '🔢', keys: ['math', 'physics', 'chemistry', 'biology', 'science', 'informatics', 'programming'] },
  { name: 'Xã hội',          icon: '🏛', keys: ['literature', 'vietnamese', 'history', 'geography', 'civics'] },
  { name: 'Năng khiếu',      icon: '🎨', keys: ['music', 'art'] },
  { name: 'Kỹ năng & khác',  icon: '🧩', keys: ['economics', 'health', 'life_skills', 'logic'] },
];

export const OTHER_CATEGORY = { name: 'Khác', icon: '📚' };

// Môn được Bộ GD đưa vào kỳ thi → có chế độ Luyện HSG + Thi chuyển cấp.
// Môn ngoài danh sách này → "Luyện tập nâng cao".
export const BO_GD_SUBJECTS = [
  'math', 'physics', 'chemistry', 'biology',
  'literature', 'history', 'geography', 'civics',
  'en', 'informatics',
];

// Môn có chế độ "Thi thử mô phỏng đề thật" (full-length, đúng cấu trúc + thời gian).
export const MOCK_EXAM_SUBJECTS = ['ielts', 'toeic_lr', 'toeic_sw'];

// Tùy chọn thời gian khi cấu hình phiên (phút; 0 = không tính giờ).
export const TIMER_OPTIONS = [0, 15, 30, 45, 60];

// Trả tên danh mục cho 1 subject key (mặc định "Khác").
export function categoryOf(subjectKey) {
  const cat = CATEGORIES.find(c => c.keys.includes(subjectKey));
  return cat ? cat.name : OTHER_CATEGORY.name;
}

// Mastery band theo điểm 0-100 (kiểu IXL SmartScore) — luôn kèm chữ + class màu.
export function masteryBand(score) {
  const s = Number(score) || 0;
  if (s >= 90) return { label: 'Làm chủ', cls: 'mastery-master' };
  if (s >= 80) return { label: 'Thạo', cls: 'mastery-good' };
  if (s >= 60) return { label: 'Khá', cls: 'mastery-mid' };
  return { label: 'Cần cố gắng', cls: 'mastery-low' };
}
