import { useState } from 'react';
import { knowledgeQuery } from '../services/api.js';

// Mỗi danh mục: cách gọi endpoint + cách render kết quả.
// input=null → không cần nhập (bấm là tra luôn). render trả JSX hoặc null nếu rỗng.
const CATS = [
  {
    key: 'dictionary', label: '📖 Từ điển', icon: '📖', endpoint: 'dictionary',
    input: { name: 'word', placeholder: 'Nhập từ tiếng Anh…' },
    params: v => ({ word: v, lang: 'en' }),
    render: d => (!d?.word ? null : (
      <div>
        <h4 style={H}>{d.word} {d.phonetic && <span style={{ color: 'var(--muted,#64748b)', fontWeight: 400 }}>{d.phonetic}</span>}</h4>
        {(d.meanings || []).slice(0, 4).map((m, i) => (
          <div key={i} style={{ marginBottom: 6 }}>
            <i style={{ color: 'var(--accent,#2563eb)' }}>{m.partOfSpeech}</i>: {(m.definitions || m.defs || [])[0]?.definition || m.definition || ''}
          </div>
        ))}
      </div>
    )),
  },
  {
    key: 'wiki', label: '🌐 Wikipedia', icon: '🌐', endpoint: 'wiki',
    input: { name: 'q', placeholder: 'Chủ đề muốn tra…' },
    params: v => ({ q: v, lang: 'vi' }),
    render: d => (!d?.title ? null : (
      <div style={{ display: 'flex', gap: 12 }}>
        {d.thumbnail && <img src={d.thumbnail} alt="" style={IMG} />}
        <div>
          <h4 style={H}>{d.title}</h4>
          <p style={{ margin: '4px 0' }}>{d.extract}</p>
          {d.url && <a href={d.url} target="_blank" rel="noreferrer">Đọc thêm →</a>}
        </div>
      </div>
    )),
  },
  {
    key: 'weather', label: '⛅ Thời tiết', icon: '⛅', endpoint: 'weather',
    input: { name: 'city', placeholder: 'Tên thành phố…' },
    params: v => ({ city: v }),
    render: d => (d?.temperature_c == null ? null : (
      <div>
        <h4 style={H}>{d.city}{d.country ? `, ${d.country}` : ''}</h4>
        <div style={{ fontSize: 32, fontWeight: 800 }}>{d.temperature_c}°C</div>
        <div style={{ color: 'var(--muted,#64748b)' }}>Gió {d.windspeed_kmh} km/h</div>
      </div>
    )),
  },
  {
    key: 'pokemon', label: '🔴 Pokémon', icon: '🔴', endpoint: 'pokemon',
    input: { name: 'name', placeholder: 'Tên Pokémon (pikachu…)' },
    params: v => ({ name: v.toLowerCase() }),
    render: d => (!d?.name ? null : (
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        {d.sprite && <img src={d.sprite} alt={d.name} style={{ width: 96, height: 96 }} />}
        <div>
          <h4 style={{ ...H, textTransform: 'capitalize' }}>{d.name} <span style={{ color: 'var(--muted,#64748b)' }}>#{d.id}</span></h4>
          <div>Hệ: {(d.types || []).join(', ')}</div>
        </div>
      </div>
    )),
  },
  {
    key: 'number-fact', label: '🔢 Sự thật về số', icon: '🔢', endpoint: 'number-fact',
    input: { name: 'number', placeholder: 'Một con số (để trống = ngẫu nhiên)', required: false },
    params: v => ({ number: v }),
    render: d => (!d?.fact ? null : <p style={{ margin: 0 }}><b>{d.number}</b>: {d.fact}</p>),
  },
  {
    key: 'math', label: '🧮 Máy tính', icon: '🧮', endpoint: 'math',
    input: { name: 'expr', placeholder: 'VD: 12 * (3 + 4)' },
    params: v => ({ expr: v }),
    render: d => (d?.result == null ? null : <p style={{ margin: 0, fontSize: 18 }}><code>{d.expr}</code> = <b>{d.result}</b></p>),
  },
  {
    key: 'animal-fact', label: '🐱 Động vật', icon: '🐱', endpoint: 'animal-fact',
    input: { name: 'kind', placeholder: 'cat hoặc dog', required: false },
    params: v => ({ kind: (v || 'cat').toLowerCase() }),
    render: d => (!d?.fact ? null : (
      <div style={{ display: 'flex', gap: 12 }}>
        {d.image && <img src={d.image} alt={d.animal} style={IMG} />}
        <p style={{ margin: 0 }}>{d.fact}</p>
      </div>
    )),
  },
  { key: 'fun-fact', label: '💡 Điều thú vị', icon: '💡', endpoint: 'fun-fact', input: null, params: () => ({}), render: d => (!d?.fact ? null : <p style={{ margin: 0 }}>{d.fact}</p>) },
  { key: 'jokes', label: '😄 Truyện cười', icon: '😄', endpoint: 'jokes', input: null, params: () => ({ type: 'single' }), render: d => (!d?.joke ? null : <p style={{ margin: 0 }}>{d.joke}</p>) },
  {
    key: 'iss', label: '🛰️ Trạm ISS', icon: '🛰️', endpoint: 'iss', input: null, params: () => ({}),
    render: d => (d?.latitude == null ? null : (
      <div>
        <p style={{ margin: 0 }}>Vị trí: {Number(d.latitude).toFixed(2)}, {Number(d.longitude).toFixed(2)}</p>
        <p style={{ margin: '4px 0 0' }}>Số người đang ở ngoài không gian: <b>{d.people_in_space}</b></p>
      </div>
    )),
  },
  {
    key: 'apod', label: '🌌 Ảnh NASA', icon: '🌌', endpoint: 'apod', input: null, params: () => ({}),
    render: d => (!d?.title ? null : (
      <div>
        <h4 style={H}>{d.title} <span style={{ color: 'var(--muted,#64748b)', fontWeight: 400 }}>{d.date}</span></h4>
        {d.media_type === 'image' && d.url && <img src={d.url} alt={d.title} style={{ maxWidth: '100%', borderRadius: 10, margin: '6px 0' }} />}
        <p style={{ margin: 0 }}>{d.explanation}</p>
      </div>
    )),
  },
];

const H = { margin: '0 0 6px', fontSize: 16, fontWeight: 700 };
const IMG = { width: 72, height: 72, objectFit: 'cover', borderRadius: 8, flexShrink: 0 };
const inp = { padding: '9px 12px', borderRadius: 10, border: '1px solid var(--border,#cbd5e1)', fontSize: 14, flex: 1, minWidth: 140 };

export default function KnowledgeExplorer() {
  const [catKey, setCatKey] = useState('dictionary');
  const [val, setVal] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const cat = CATS.find(c => c.key === catKey);

  async function run(e) {
    e?.preventDefault?.();
    if (cat.input?.required !== false && cat.input && !val.trim()) { setError('Hãy nhập nội dung cần tra.'); return; }
    setLoading(true); setError(''); setResult(null);
    const data = await knowledgeQuery(cat.endpoint, cat.params(val.trim()));
    setLoading(false);
    if (!data || data.ok === false) { setError('Không tìm thấy / nguồn tạm lỗi. Thử lại nhé.'); return; }
    const node = cat.render(data);
    if (!node) { setError('Không có dữ liệu phù hợp.'); return; }
    setResult(node);
  }

  function pick(k) {
    setCatKey(k); setVal(''); setResult(null); setError('');
  }

  return (
    <div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        {CATS.map(c => (
          <button key={c.key} onClick={() => pick(c.key)} style={{
            padding: '6px 12px', borderRadius: 999, cursor: 'pointer', fontSize: 13, fontWeight: 600,
            border: catKey === c.key ? 'none' : '1px solid var(--border,#cbd5e1)',
            background: catKey === c.key ? '#2563eb' : 'transparent',
            color: catKey === c.key ? '#fff' : 'var(--text,#0f172a)',
          }}>{c.icon} {c.label.replace(/^[^ ]+ /, '')}</button>
        ))}
      </div>

      <form onSubmit={run} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {cat.input && (
          <input style={inp} value={val} placeholder={cat.input.placeholder}
            onChange={e => setVal(e.target.value)} />
        )}
        <button type="submit" disabled={loading} style={{
          padding: '9px 18px', borderRadius: 10, border: 'none', background: '#16a34a',
          color: '#fff', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap',
        }}>{loading ? 'Đang tra…' : '🔍 Tra cứu'}</button>
      </form>

      {error && <div style={{ padding: '10px 14px', borderRadius: 10, background: '#fef3c7', color: '#92400e', fontSize: 14 }}>{error}</div>}
      {result && <div style={{ padding: 14, borderRadius: 12, background: 'var(--bg,#f5f6fa)', fontSize: 14, lineHeight: 1.5 }}>{result}</div>}
    </div>
  );
}
