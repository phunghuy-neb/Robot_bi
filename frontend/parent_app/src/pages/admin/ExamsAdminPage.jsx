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

  if (loading) return <div className="spinner" style={{ margin: 40 }} />;

  const th = { textAlign: 'left', padding: '10px 12px', fontSize: 13, color: 'var(--muted,#64748b)', borderBottom: '2px solid var(--border,#e2e8f0)' };
  const td = { padding: '10px 12px', borderBottom: '1px solid var(--border,#eef1f6)', fontSize: 14 };

  if (creating) {
    return (
      <div>
        <button onClick={() => setCreating(false)} style={{ marginBottom: 14, padding: '8px 14px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', background: 'transparent', cursor: 'pointer' }}>← Quay lại danh sách</button>
        <h3 style={{ margin: '0 0 12px' }}>Tạo đề chung (mọi tài khoản sẽ thấy)</h3>
        <ExamBuilder isGlobal onCreated={() => { setCreating(false); load(); }} onCancel={() => setCreating(false)} />
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontSize: 13, color: 'var(--muted,#64748b)' }}>{papers.length} đề thi (mọi gia đình)</span>
        <button onClick={() => setCreating(true)} style={{ padding: '8px 14px', borderRadius: 8, border: 'none', background: '#16a34a', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>+ Tạo đề chung</button>
      </div>
      <div style={{ background: 'var(--card,#fff)', borderRadius: 14, padding: 12, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
          <thead>
            <tr>
              <th style={th}>Tên đề</th><th style={th}>Môn</th><th style={th}>Câu</th>
              <th style={th}>Phạm vi</th><th style={th}>Nguồn</th><th style={th}>Trạng thái</th><th style={th}></th>
            </tr>
          </thead>
          <tbody>
            {papers.map(p => (
              <tr key={p.paper_id} style={{ opacity: busy === p.paper_id ? 0.5 : 1 }}>
                <td style={td}><b>{p.title}</b></td>
                <td style={td}>{p.subject}</td>
                <td style={td}>{p.total_questions}</td>
                <td style={td}>{p.family_id
                  ? <span style={{ color: '#7c3aed' }}>👪 {p.family_id}</span>
                  : <span style={{ color: '#2563eb' }}>🌐 Chung</span>}</td>
                <td style={{ ...td, fontSize: 12, color: 'var(--muted,#64748b)' }}>{p.source}</td>
                <td style={td}>{p.status}</td>
                <td style={td}>
                  <button disabled={busy === p.paper_id} onClick={() => del(p)}
                    style={{ padding: '5px 10px', borderRadius: 8, border: 'none', background: '#dc2626', color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: 12 }}>Xóa</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
