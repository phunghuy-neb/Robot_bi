import { useState, useEffect, useCallback } from 'react';
import { adminGetLogs } from '../../services/api.js';

const LEVELS = ['', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

export default function LogsAdminPage() {
  const [level, setLevel] = useState('');
  const [component, setComponent] = useState('');
  const [data, setData] = useState({ logs: [], total: 0 });
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setData(await adminGetLogs({ level, component, limit: 200 }));
    setLoading(false);
  }, [level, component]);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="admin-toolbar">
        <div className="admin-toolbar-left">
          <select className="admin-select compact" value={level} onChange={e => setLevel(e.target.value)}>
            {LEVELS.map(l => <option key={l} value={l}>{l || 'Mọi mức'}</option>)}
          </select>
          <input className="admin-input compact" value={component} placeholder="Lọc theo component…" onChange={e => setComponent(e.target.value)} />
          <button onClick={load} className="admin-btn ghost small">↻ Làm mới</button>
        </div>
        <span className="admin-count">{data.total} dòng (đã ẩn thông tin nhạy cảm)</span>
      </div>

      {loading ? <div className="spinner admin-loading" /> : (
        <div className="admin-card compact admin-table-scroll">
          {(data.logs || []).length === 0 ? <div className="admin-empty">Không có nhật ký.</div> : (
            <table className="admin-table compact">
              <thead><tr>
                <th className="admin-th">Thời điểm</th><th className="admin-th">Mức</th><th className="admin-th">Component</th><th className="admin-th">Thông điệp</th>
              </tr></thead>
              <tbody>
                {data.logs.map((l, i) => (
                  <tr key={i}>
                    <td className="admin-td small nowrap">{(l.timestamp || '').replace('T', ' ').slice(0, 19)}</td>
                    <td className={`admin-td admin-log-level ${String(l.level || '').toLowerCase()}`}>{l.level}</td>
                    <td className="admin-td small">{l.component}</td>
                    <td className="admin-td small admin-mono">{l.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
