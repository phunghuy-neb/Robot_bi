import { useState, useEffect } from 'react';
import { apiFetch, getRadioChannels, getVideoLessons, getInteractiveGames, showToast,
  getMyYoutubeChannels, addMyYoutubeChannel, removeMyYoutubeChannel } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import FeatureBadge from '../components/FeatureBadge.jsx';
import YouTubeChannelManager from '../components/YouTubeChannelManager.jsx';

const DEMO_SONGS = {
  kids_vn: [{ title: 'Cá vàng bơi', artist: 'Nhạc thiếu nhi VN', icon: '🐠' }, { title: 'Đàn vịt con', artist: 'Nhạc thiếu nhi VN', icon: '🦆' }],
  kids_en: [{ title: 'Twinkle Twinkle', artist: 'Nursery Rhyme', icon: '⭐' }, { title: 'ABC Song', artist: 'Learning Songs', icon: '📚' }],
  lullaby: [{ title: 'Ru con', artist: 'Nhạc dân ca', icon: '🌙' }, { title: 'Con cò bay lả', artist: 'Dân ca', icon: '🐦' }],
};

const PLAYLIST_CATS = { kids_vn: 'vietnamese', kids_en: 'english', lullaby: 'lullabies' };

export default function MorePage() {
  const [musicPlaying, setMusicPlaying] = useState(false);
  const [currentPlaylist, setCurrentPlaylist] = useState('kids_vn');
  const [songs, setSongs] = useState(DEMO_SONGS['kids_vn']);
  const [currentTrack, setCurrentTrack] = useState(null);
  const [radioChannels, setRadioChannels] = useState([]);
  const [videoLessons, setVideoLessons] = useState([]);
  const [games, setGames] = useState([]);
  const [showYtManager, setShowYtManager] = useState(false);

  useEffect(() => {
    loadRadio();
    loadVideos();
    loadGames();
  }, []);

  async function loadPlaylist(type) {
    setCurrentPlaylist(type);
    const cat = PLAYLIST_CATS[type] || 'vietnamese';
    const data = await apiFetch(`/api/music/playlist?category=${cat}`);
    setSongs(data?.tracks || DEMO_SONGS[type] || []);
  }

  async function loadRadio() {
    const data = await getRadioChannels();
    if (data) setRadioChannels(data);
  }

  async function loadVideos() {
    const data = await getVideoLessons();
    if (data) setVideoLessons(data);
  }

  async function loadGames() {
    const data = await getInteractiveGames();
    if (data) setGames(data);
  }

  function toggleMusicPlay() {
    const newState = !musicPlaying;
    setMusicPlaying(newState);
    apiFetch(`/api/music/${newState ? 'play' : 'stop'}`, { method: 'POST' }).catch(() => {});
  }

  function musicCmd(cmd) {
    apiFetch(`/api/music/${cmd === 'prev' ? 'previous' : cmd}`, { method: 'POST' }).catch(() => {});
    showToast(`🎵 ${cmd}`);
  }

  function setVolume(v) {
    apiFetch('/api/music/volume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ level: parseInt(v) }),
    }).catch(() => {});
  }

  function playTrack(song, type) {
    setCurrentTrack(song);
    setMusicPlaying(true);
    apiFetch('/api/music/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ track_id: song.id, category: PLAYLIST_CATS[type] }),
    });
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">➕ Thêm</div>
        <div className="page-subtitle">Nhạc · Radio · Video học · Trò chơi</div>
      </div>

      <div className="page-body">
        {/* Feature shortcut cards */}
        <div className="more-grid">
          <div className="more-card" style={{ background: 'linear-gradient(135deg, #FFE4E6 0%, #FECDD3 100%)' }}>
            <span>📻</span>
            <div>Radio</div>
          </div>
          <div className="more-card" style={{ background: 'var(--grad-mint)' }}>
            <span>🎵</span>
            <div>Âm nhạc</div>
          </div>
          <div className="more-card" style={{ background: 'var(--grad-purple-soft)' }}>
            <span>📖</span>
            <div>Truyện kể</div>
          </div>
          <div className="more-card" style={{ background: 'var(--grad-hot)', color: '#fff', position: 'relative' }}>
            <span className="hot-badge">HOT</span>
            <span>🎮</span>
            <div>Trò chơi</div>
          </div>
          <div className="more-card" style={{ background: 'var(--grad-blue)' }}>
            <span>🎬</span>
            <div>Video học</div>
          </div>
        </div>

        {/* Music player (real API) */}
        <div className="music-player-card">
          <div className="music-track-label">🎵 Đang phát</div>
          <div className="music-track-title">{currentTrack?.title || 'Chọn bài hát...'}</div>
          <div className="music-track-artist">{currentTrack?.artist || '—'}</div>
          <div className="music-controls">
            <button className="music-btn" onClick={() => musicCmd('prev')} title="Bài trước">⏮</button>
            <button className="music-btn play" onClick={toggleMusicPlay} title={musicPlaying ? 'Dừng' : 'Phát'}>
              {musicPlaying ? '⏸' : '▶'}
            </button>
            <button className="music-btn" onClick={() => musicCmd('next')} title="Bài tiếp">⏭</button>
            <button className="music-btn" onClick={() => musicCmd('shuffle')} title="Ngẫu nhiên">🔀</button>
          </div>
          <div className="music-volume-row">
            <span title="Âm lượng">🔊</span>
            <input type="range" min="0" max="100" defaultValue="50" onChange={e => setVolume(e.target.value)} title="Âm lượng" style={{ flex: 1 }} />
          </div>
        </div>

        {/* Playlist tabs */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📋 Danh sách phát</span>
          </div>
          <div className="filter-bar" style={{ marginBottom: 12 }}>
            {[['kids_vn', '🇻🇳 VN'], ['kids_en', '🇬🇧 Anh'], ['lullaby', '🌙 Ru ngủ']].map(([type, label]) => (
              <button
                key={type}
                className={`btn-sm ${currentPlaylist === type ? 'primary' : 'secondary'}`}
                onClick={() => loadPlaylist(type)}
              >
                {label}
              </button>
            ))}
          </div>
          {songs.length === 0 ? (
            <SectionState state="empty" emptyText="Chưa có bài hát." emptyIcon="🎵" />
          ) : (
            songs.map((s, i) => (
              <div key={i} className="media-card">
                <div className="media-thumb">{s.icon || '🎵'}</div>
                <div className="media-body">
                  <div className="media-title">{s.title}</div>
                  <div className="media-meta">{s.artist}</div>
                </div>
                <button className="btn-sm primary media-action" onClick={() => playTrack(s, currentPlaylist)}>
                  ▶
                </button>
              </div>
            ))
          )}
        </div>

        {/* Radio */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📻 Radio</span>
          </div>
          {radioChannels.length === 0 ? (
            <SectionState state="loading" loadingText="Đang tải kênh radio..." />
          ) : (
            radioChannels.map(ch => (
              <div key={ch.id} className="media-card">
                <div className="media-thumb">{ch.icon}</div>
                <div className="media-body">
                  <div className="media-title">{ch.name}</div>
                  <div className="media-meta">{ch.genre}{ch.frequency ? ` · ${ch.frequency}` : ''}</div>
                </div>
                <button
                  className="btn-sm primary media-action"
                  onClick={() => ch.url ? window.open(ch.url, '_blank', 'noopener') : showToast('Kênh này chưa có URL')}
                >
                  ▶ Nghe
                </button>
              </div>
            ))
          )}
        </div>

        {/* Video học */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🎬 Video học</span>
          </div>
          {videoLessons.length === 0 ? (
            <SectionState state="loading" loadingText="Đang tải video..." />
          ) : (
            videoLessons.map(v => (
              <div key={v.id} className="media-card">
                <div className="media-thumb">{typeof v.thumbnail === 'string' && v.thumbnail.startsWith('http')
                  ? <img src={v.thumbnail} alt={v.title} style={{ width: 48, height: 36, objectFit: 'cover', borderRadius: 6 }} />
                  : v.thumbnail}
                </div>
                <div className="media-body">
                  <div className="media-title">{v.title}</div>
                  <div className="media-meta">{[v.subject, v.age ? `${v.age} tuổi` : ''].filter(Boolean).join(' · ')}</div>
                </div>
                <button
                  className="btn-sm primary media-action"
                  onClick={() => v.url ? window.open(v.url, '_blank', 'noopener') : showToast('Video này chưa có URL')}
                >
                  ▶ Xem
                </button>
              </div>
            ))
          )}
        </div>

        {/* Kênh YouTube của gia đình — phụ huynh tự thêm */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="card-title">📺 Kênh YouTube của gia đình</span>
            <button className="btn-sm secondary" onClick={() => setShowYtManager(v => !v)}>
              {showYtManager ? 'Thu gọn' : 'Quản lý'}
            </button>
          </div>
          <div style={{ fontSize: 13, color: 'var(--muted,#64748b)', padding: '0 4px 8px' }}>
            Thêm kênh giáo dục bạn tin tưởng — chỉ <b>gia đình bạn</b> thấy video từ các kênh này.
            Lấy Channel ID (UC…): mở kênh → <b>Share channel</b> → <b>Copy channel ID</b>.
          </div>
          {showYtManager && (
            <YouTubeChannelManager
              loadFn={getMyYoutubeChannels}
              addFn={addMyYoutubeChannel}
              removeFn={removeMyYoutubeChannel}
              accent="#7c3aed"
            />
          )}
        </div>

        {/* Interactive games — coming soon */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🎮 Trò chơi tương tác</span>
            <FeatureBadge type="coming-soon" />
          </div>
          {games.length === 0 ? (
            <SectionState state="loading" loadingText="Đang tải trò chơi..." />
          ) : (
            games.map(g => (
              <div key={g.id} className="media-card">
                <div className="media-thumb">{g.icon}</div>
                <div className="media-body">
                  <div className="media-title">{g.name}</div>
                  <div className="media-meta">{g.description} · {g.difficulty} · {g.age}</div>
                </div>
                <button
                  className="btn-sm secondary media-action"
                  disabled
                  title="Sắp hỗ trợ"
                >
                  Sắp ra
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
