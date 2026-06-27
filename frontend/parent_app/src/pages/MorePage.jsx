import { useState, useEffect, useRef } from 'react';
import { apiFetch, getRadioChannels, getVideoLessons, getInteractiveGames, showToast,
  getMyYoutubeChannels, addMyYoutubeChannel, removeMyYoutubeChannel,
  startWordQuiz, getWordQuizQuestion, answerWordQuiz, endWordQuiz,
  startVoiceQuiz, getVoiceQuizRiddle, answerVoiceQuiz, getGameScores } from '../services/api.js';
import SectionState from '../components/SectionState.jsx';
import YouTubeChannelManager from '../components/YouTubeChannelManager.jsx';
import KnowledgeExplorer from '../components/KnowledgeExplorer.jsx';

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
  const [loaded, setLoaded] = useState({ radio: false, video: false, games: false });
  const [showYtManager, setShowYtManager] = useState(false);
  const [showKnowledge, setShowKnowledge] = useState(false);
  const [gameModal, setGameModal] = useState(null);
  const [gameBusy, setGameBusy] = useState(false);
  const [gameDifficulty, setGameDifficulty] = useState('easy');
  const [gameQuestion, setGameQuestion] = useState(null);
  const [gameAnswer, setGameAnswer] = useState('');
  const [gameFeedback, setGameFeedback] = useState(null);
  const [gameSummary, setGameSummary] = useState(null);
  const [gameScores, setGameScores] = useState(null);

  // Refs cho shortcut card cuộn tới section tương ứng trên cùng trang
  const knowledgeRef = useRef(null);
  const musicRef = useRef(null);
  const radioRef = useRef(null);
  const videoRef = useRef(null);
  const gamesRef = useRef(null);
  const scrollToRef = (ref) => ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

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
    setLoaded(s => ({ ...s, radio: true }));
  }

  async function loadVideos() {
    const data = await getVideoLessons();
    if (data) setVideoLessons(data);
    setLoaded(s => ({ ...s, video: true }));
  }

  async function loadGames() {
    const data = await getInteractiveGames();
    if (data) setGames(data);
    setLoaded(s => ({ ...s, games: true }));
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

  function gameMode(game) {
    const haystack = [game?.url, game?.name, game?.description, ...(game?.tags || [])]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    if (haystack.includes('/api/game/voice-quiz') || haystack.includes('voice')) return 'voice';
    if (haystack.includes('/api/game/word-quiz') || haystack.includes('word') || haystack.includes('vocabulary')) return 'word';
    if (/^https?:\/\//i.test(game?.url || '')) return 'external';
    return 'unknown';
  }

  function gameActionLabel(game) {
    const mode = gameMode(game);
    if (mode === 'external') return 'Mở';
    if (mode === 'voice') return 'Chơi nhập đáp án';
    if (mode === 'word') return 'Chơi ngay';
    return 'Cấu hình';
  }

  function openGame(game) {
    const mode = gameMode(game);
    if (mode === 'external') {
      window.open(game.url, '_blank', 'noopener');
      return;
    }
    if (mode === 'unknown') {
      showToast('Game này cần URL /api/game/word-quiz/start hoặc /api/game/voice-quiz/start');
      return;
    }
    setGameModal({ game, mode });
    setGameQuestion(null);
    setGameAnswer('');
    setGameFeedback(null);
    setGameSummary(null);
    setGameScores(null);
    if (mode === 'word') {
      getGameScores().then(scores => setGameScores(scores?.word_quiz || [])).catch(() => {});
    }
  }

  async function loadNextGameQuestion(mode = gameModal?.mode) {
    setGameBusy(true);
    setGameFeedback(null);
    setGameAnswer('');
    const q = mode === 'voice' ? await getVoiceQuizRiddle() : await getWordQuizQuestion();
    setGameQuestion(q || null);
    setGameBusy(false);
  }

  async function startGameSession() {
    if (!gameModal) return;
    setGameSummary(null);
    setGameFeedback(null);
    setGameBusy(true);
    const started = gameModal.mode === 'voice'
      ? await startVoiceQuiz()
      : await startWordQuiz(gameDifficulty);
    setGameBusy(false);
    if (!started) {
      showToast('Không mở được trò chơi');
      return;
    }
    await loadNextGameQuestion(gameModal.mode);
    if (gameModal.mode === 'word') {
      const scores = await getGameScores();
      setGameScores(scores?.word_quiz || []);
    }
  }

  async function submitGameAnswer(answer = gameAnswer) {
    if (!gameModal || !answer || gameBusy || gameFeedback) return;
    setGameBusy(true);
    const result = gameModal.mode === 'voice'
      ? await answerVoiceQuiz(answer)
      : await answerWordQuiz(answer);
    setGameFeedback(result || { correct: false, score: 0 });
    setGameBusy(false);
  }

  async function finishGameSession() {
    if (!gameModal) return;
    setGameBusy(true);
    const summary = gameModal.mode === 'word' ? await endWordQuiz() : { done: true };
    setGameSummary(summary || { done: true });
    setGameQuestion(null);
    setGameFeedback(null);
    setGameBusy(false);
  }

  function closeGameModal() {
    setGameModal(null);
    setGameQuestion(null);
    setGameAnswer('');
    setGameFeedback(null);
    setGameSummary(null);
    setGameScores(null);
  }

  return (
    <div>
      <div className="page-header">
        <div className="page-title">➕ Thêm</div>
        <div className="page-subtitle">Nhạc · Radio · Video học · Trò chơi</div>
      </div>

      <div className="page-body">
        {/* Khám phá tri thức — tra cứu API ngoài an toàn cho trẻ */}
        <div className="card" ref={knowledgeRef}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="card-title">🔎 Khám phá tri thức</span>
            <button className="btn-sm secondary" onClick={() => setShowKnowledge(v => !v)}>
              {showKnowledge ? 'Thu gọn' : 'Mở'}
            </button>
          </div>
          <div style={{ fontSize: 13, color: 'var(--muted,#64748b)', padding: '0 4px 8px' }}>
            Tra từ điển, Wikipedia, thời tiết, Pokémon, sự thật thú vị, ảnh NASA… — nguồn an toàn cho trẻ.
          </div>
          {showKnowledge && <KnowledgeExplorer />}
        </div>

        {/* Feature shortcut cards — cuộn tới section tương ứng trên trang */}
        <div className="more-grid">
          <button type="button" className="more-card" style={{ background: 'linear-gradient(135deg, #FFE4E6 0%, #FECDD3 100%)' }} onClick={() => scrollToRef(radioRef)}>
            <span>📻</span>
            <div>Radio</div>
          </button>
          <button type="button" className="more-card" style={{ background: 'var(--grad-mint)' }} onClick={() => scrollToRef(musicRef)}>
            <span>🎵</span>
            <div>Âm nhạc</div>
          </button>
          <button type="button" className="more-card" style={{ background: 'var(--grad-purple-soft)' }} onClick={() => scrollToRef(knowledgeRef)}>
            <span>🔎</span>
            <div>Tri thức</div>
          </button>
          <button type="button" className="more-card" style={{ background: 'var(--grad-hot)', color: '#fff', position: 'relative' }} onClick={() => scrollToRef(gamesRef)}>
            <span className="hot-badge">HOT</span>
            <span>🎮</span>
            <div>Trò chơi</div>
          </button>
          <button type="button" className="more-card" style={{ background: 'var(--grad-blue)' }} onClick={() => scrollToRef(videoRef)}>
            <span>🎬</span>
            <div>Video học</div>
          </button>
        </div>

        {/* Music player (real API) */}
        <div className="music-player-card" ref={musicRef}>
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
        <div className="card" ref={radioRef}>
          <div className="card-header">
            <span className="card-title">📻 Radio</span>
          </div>
          {radioChannels.length === 0 ? (
            <SectionState state={loaded.radio ? 'empty' : 'loading'}
              loadingText="Đang tải kênh radio..." emptyText="Chưa có kênh radio." emptyIcon="📻" />
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
        <div className="card" ref={videoRef}>
          <div className="card-header">
            <span className="card-title">🎬 Video học</span>
          </div>
          {videoLessons.length === 0 ? (
            <SectionState state={loaded.video ? 'empty' : 'loading'}
              loadingText="Đang tải video..." emptyText="Chưa có video học." emptyIcon="🎬" />
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
              buttonTone="purple"
            />
          )}
        </div>

        {/* Interactive games */}
        <div className="card" ref={gamesRef}>
          <div className="card-header">
            <span className="card-title">🎮 Trò chơi tương tác</span>
          </div>
          {games.length === 0 ? (
            <SectionState state={loaded.games ? 'empty' : 'loading'}
              loadingText="Đang tải trò chơi..." emptyText="Chưa có trò chơi." emptyIcon="🎮" />
          ) : (
            games.map(g => (
              <div key={g.id} className="media-card">
                <div className="media-thumb">{g.icon}</div>
                <div className="media-body">
                  <div className="media-title">{g.name}</div>
                  <div className="media-meta">
                    {[g.description, g.difficulty, g.age ? `${g.age} tuổi` : ''].filter(Boolean).join(' · ')}
                  </div>
                </div>
                <button
                  className={`btn-sm ${gameMode(g) === 'unknown' ? 'secondary' : 'primary'} media-action`}
                  onClick={() => openGame(g)}
                  title={gameMode(g) === 'unknown' ? 'Admin cần cấu hình URL game' : 'Mở trò chơi'}
                >
                  {gameActionLabel(g)}
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {gameModal && (
        <div className="game-modal-backdrop" role="presentation" onClick={e => e.target === e.currentTarget && closeGameModal()}>
          <div className="game-modal" role="dialog" aria-modal="true" aria-label={gameModal.game.name}>
            <div className="game-modal-head">
              <div>
                <div className="game-kicker">{gameModal.mode === 'voice' ? 'Voice Quiz' : 'Word Quiz'}</div>
                <h2>{gameModal.game.name}</h2>
              </div>
              <button className="game-icon-btn" onClick={closeGameModal} aria-label="Đóng trò chơi">×</button>
            </div>

            {gameSummary ? (
              <div className="game-result-panel">
                <div className="game-score-big">{gameSummary.total_score ?? gameFeedback?.score ?? 0}</div>
                <div className="game-score-label">điểm</div>
                {gameSummary.questions_answered != null && (
                  <div className="game-meta-line">
                    Đúng {gameSummary.correct || 0} · Sai {gameSummary.incorrect || 0} · {gameSummary.questions_answered || 0} câu
                  </div>
                )}
                <div className="game-actions">
                  <button className="btn-sm primary" onClick={startGameSession} disabled={gameBusy}>
                    Chơi lại
                  </button>
                  <button className="btn-sm secondary" onClick={closeGameModal}>Đóng</button>
                </div>
              </div>
            ) : !gameQuestion ? (
              <div className="game-start-panel">
                <p>{gameModal.game.description || 'Mở một phiên chơi ngắn, trả lời ngay trong Parent App.'}</p>
                {gameModal.mode === 'word' && (
                  <div className="game-difficulty-row" role="group" aria-label="Độ khó">
                    {['easy', 'medium'].map(level => (
                      <button
                        key={level}
                        className={`pill-tab${gameDifficulty === level ? ' active' : ''}`}
                        onClick={() => setGameDifficulty(level)}
                      >
                        {level === 'easy' ? 'Dễ' : 'Vừa'}
                      </button>
                    ))}
                  </div>
                )}
                {gameScores?.length > 0 && (
                  <div className="game-meta-line">Điểm cao gần đây: {gameScores[0]?.score || 0}</div>
                )}
                <button className="btn-sm primary" onClick={startGameSession} disabled={gameBusy}>
                  {gameBusy ? 'Đang mở...' : 'Bắt đầu'}
                </button>
              </div>
            ) : (
              <div className="game-play-panel">
                <div className="game-question">
                  {gameModal.mode === 'voice'
                    ? (gameQuestion.riddle_text || 'Câu đố')
                    : (gameQuestion.question_text || gameQuestion.question || 'Câu hỏi')}
                </div>

                {gameModal.mode === 'voice' && gameQuestion.hint && (
                  <div className="game-hint">Gợi ý: {gameQuestion.hint}</div>
                )}

                {gameModal.mode === 'word' ? (
                  <div className="game-options">
                    {(gameQuestion.options || []).map(option => (
                      <button
                        key={option}
                        className={`game-option${gameAnswer === option ? ' selected' : ''}`}
                        onClick={() => {
                          setGameAnswer(option);
                          submitGameAnswer(option);
                        }}
                        disabled={gameBusy || !!gameFeedback}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : (
                  <form className="game-answer-row" onSubmit={e => { e.preventDefault(); submitGameAnswer(); }}>
                    <input
                      className="form-input"
                      value={gameAnswer}
                      onChange={e => setGameAnswer(e.target.value)}
                      placeholder="Nhập câu trả lời của bé..."
                      disabled={gameBusy || !!gameFeedback}
                    />
                    <button className="btn-sm primary" disabled={gameBusy || !gameAnswer.trim() || !!gameFeedback}>
                      Trả lời
                    </button>
                  </form>
                )}

                {gameFeedback && (
                  <div className={`game-feedback ${gameFeedback.correct ? 'correct' : 'wrong'}`}>
                    <b>{gameFeedback.correct ? 'Đúng rồi' : 'Chưa đúng'}</b>
                    <span>{gameFeedback.explanation || `Điểm: ${gameFeedback.score || 0}`}</span>
                  </div>
                )}

                <div className="game-actions">
                  <button className="btn-sm secondary" onClick={() => loadNextGameQuestion()} disabled={gameBusy || !gameFeedback}>
                    Câu tiếp
                  </button>
                  <button className="btn-sm primary" onClick={finishGameSession} disabled={gameBusy}>
                    Kết thúc
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
