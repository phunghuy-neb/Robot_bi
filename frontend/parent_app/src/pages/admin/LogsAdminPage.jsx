import { useState, useEffect, useCallback } from 'react';
import { adminGetLogs } from '../../services/api.js';

const LEVELS = ['', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
const LEVEL_COLOR = { DEBUG: '#64748b', INFO: '#2563eb', WARNING: '#b45309', ERROR: '#dc2626', CRITICAL: '#991b1b' };
const card = { background: 'var(--card,#fff)', borderRadius: 14, padding: 12 };
const inp = { padding: '7px 10px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', fontSize: 14 };

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
      <div style={{ display: 'flex', gap: 10, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <select style={inp} value={level} onChange={e => setLevel(e.target.value)}>
          {LEVELS.map(l => <option key={l} value={l}>{l || 'Mọi mức'}</option>)}
        </select>
        <input style={inp} value={component} placeholder="Lọc theo component…" onChange={e => setComponent(e.target.value)} />
        <button onClick={load} style={{ padding: '7px 14px', borderRadius: 8, border: '1px solid var(--border,#cbd5e1)', background: 'transparent', cursor: 'pointer' }}>↻ Làm mới</button>
        <span style={{ fontSize: 13, color: 'var(--muted,#64748b)', marginLeft: 'auto' }}>{data.total} dòng (đã ẩn thông tin nhạy cảm)</span>
      </div>

      {loading ? <div className="spinner" style={{ margin: 40 }} /> : (
        <div style={{ ...card, overflowX: 'auto' }}>
          {(data.logs || []).length === 0 ? <div style={{ padding: 24, textAlign: 'center', color: 'var(--muted,#64748b)' }}>Không có nhật ký.</div> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 640 }}>
              <thead><tr>
                <th style={th}>Thời điểm</th><th style={th}>Mức</th><th style={th}>Component</th><th style={th}>Thông điệp</th>
              </tr></thead>
              <tbody>
                {data.logs.map((l, i) => (
                  <tr key={i}>
                    <td style={{ ...td, whiteSpace: 'nowrap', fontSize: 12 }}>{(l.timestamp || '').replace('T', ' ').slice(0, 19)}</td>
                    <td style={{ ...td, fontWeight: 700, color: LEVEL_COLOR[l.level] || 'inherit' }}>{l.level}</td>
                    <td style={{ ...td, fontSize: 12 }}>{l.component}</td>
                    <td style={{ ...td, fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-word' }}>{l.message}</td>
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

const th = { textAlign: 'left', padding: '8px 10px', fontSize: 12, color: 'var(--muted,#64748b)', borderBottom: '2px solid var(--border,#e2e8f0)' };
const td = { padding: '8px 10px', borderBottom: '1px solid var(--border,#eef1f6)', fontSize: 13 };
