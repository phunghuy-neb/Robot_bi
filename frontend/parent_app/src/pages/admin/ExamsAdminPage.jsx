import { useState, useEffect, useCallback } from 'react';
import { adminListPapers, deleteExam, showToast } from '../../services/api.js';
import ExamBuilder from '../../components/ExamBuilder.jsx';

export default function ExamsAdminPage() {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setPapers(await adminListPapers());
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  async function del(p) {
    if (!window.confirm(`Xóa đề "${p.title}"?`)) return;
    setBusy(p.paper_id);
    const res = await deleteExam(p.paper_id);
    setBusy(null);
    if (res) { showToast('Đã xóa đề'); load(); } else showToast('Xóa thất bại');
  }

  if (loading) return <div className="spinner admin-loading" />;

  if (creating) {
    return (
      <div>
        <button className="admin-btn ghost" onClick={() => setCreating(false)}>← Quay lại danh sách</button>
        <h3 className="admin-section-title">Tạo đề chung (mọi tài khoản sẽ thấy)</h3>
        <ExamBuilder isGlobal onCreated={() => { setCreating(false); load(); }} onCancel={() => setCreating(false)} />
      </div>
    );
  }

  return (
    <div>
      <div className="admin-toolbar">
        <span className="admin-page-note">{papers.length} đề thi (mọi gia đình)</span>
        <button className="admin-btn success" onClick={() => setCreating(true)}>+ Tạo đề chung</button>
      </div>
      <div className="admin-card compact admin-table-scroll">
        <table className="admin-table">
          <thead>
            <tr>
              <th className="admin-th">Tên đề</th><th className="admin-th">Môn</th><th className="admin-th">Câu</th>
              <th className="admin-th">Phạm vi</th><th className="admin-th">Nguồn</th><th className="admin-th">Trạng thái</th><th className="admin-th"></th>
            </tr>
          </thead>
          <tbody>
            {papers.map(p => (
              <tr key={p.paper_id} className={busy === p.paper_id ? 'admin-row-busy' : ''}>
                <td className="admin-td"><b>{p.title}</b></td>
                <td className="admin-td">{p.subject}</td>
                <td className="admin-td">{p.total_questions}</td>
                <td className="admin-td">{p.family_id
                  ? <span className="admin-status purple">👪 {p.family_id}</span>
                  : <span className="admin-status info">🌐 Chung</span>}</td>
                <td className="admin-td small admin-muted">{p.source}</td>
                <td className="admin-td">{p.status}</td>
                <td className="admin-td">
                  <button disabled={busy === p.paper_id} onClick={() => del(p)}
                    className="admin-btn small danger">Xóa</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
