// Robot Bi Parent App â€” API Service Layer
// Tier 1: Real backend (preserved behavior from legacy index.html)
// Tier 2: Mock adapters â€” marked TODO for future backend integration

import {
  mockChildProfiles,
  mockRadioChannels,
  mockVideoLessons,
  mockMonthlyEmotions,
  mockInteractiveGames,
  mockSystemLogs,
} from '../data/mockData.js';

// â”€â”€ Auth Storage â”€â”€
let _token = localStorage.getItem('bi_token') || '';
let _refreshToken = localStorage.getItem('bi_refresh') || '';
let _refreshPromise = null;

function authHeader() {
  return _token ? { Authorization: 'Bearer ' + _token } : {};
}

// â”€â”€ Toast â”€â”€
export let toastFn = null;
export function registerToast(fn) { toastFn = fn; }
export function showToast(msg) { toastFn && toastFn(msg); }

// â”€â”€ Utilities â”€â”€
export function getBaseUrl() { return window.location.origin; }
export function getToken() { return _token; }

// â”€â”€ Auth: login â”€â”€
export async function login(username, password) {
  const r = await fetch('/auth/login/v2', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || 'Sai tÃªn Ä‘Äƒng nháº­p hoáº·c máº­t kháº©u.');
  }
  const data = await r.json();
  _token = data.access_token;
  _refreshToken = data.refresh_token;
  localStorage.setItem('bi_token', _token);
  localStorage.setItem('bi_refresh', _refreshToken);
  return { username: data.username || username, isAdmin: data.is_admin || false };
}

// â”€â”€ Auth: logout â”€â”€
export async function logout() {
  try {
    if (_token && _refreshToken) {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader() },
        body: JSON.stringify({ refresh_token: _refreshToken }),
      });
    }
  } catch (_) {}
  _token = '';
  _refreshToken = '';
  localStorage.removeItem('bi_token');
  localStorage.removeItem('bi_refresh');
}

// â”€â”€ Auth: refresh token â”€â”€
export async function refreshToken() {
  if (_refreshPromise) return _refreshPromise;
  _refreshPromise = (async () => {
    try {
      if (!_refreshToken) return false;
      const rr = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: _refreshToken }),
      });
      if (!rr.ok) return false;
      const data = await rr.json();
      _token = data.access_token;
      _refreshToken = data.refresh_token;
      localStorage.setItem('bi_token', _token);
      localStorage.setItem('bi_refresh', _refreshToken);
      return true;
    } catch (_) {
      return false;
    } finally {
      _refreshPromise = null;
    }
  })();
  return _refreshPromise;
}

// â”€â”€ Check existing session on app load â”€â”€
export async function checkExistingSession() {
  if (!_token) return null;
  try {
    const r = await fetch('/api/auth/me', { headers: authHeader() });
    if (r.ok) {
      const data = await r.json();
      return { username: data.username, isAdmin: data.is_admin || false };
    }
    const ok = await refreshToken();
    if (ok) {
      const r2 = await fetch('/api/auth/me', { headers: authHeader() });
      if (r2.ok) {
        const data = await r2.json();
        return { username: data.username, isAdmin: data.is_admin || false };
      }
    }
    _token = '';
    localStorage.removeItem('bi_token');
    return null;
  } catch (_) {
    return null;
  }
}

// â”€â”€ apiFetch with 401 â†’ refresh â†’ retry â†’ logout â”€â”€
export async function apiFetch(path, opts = {}) {
  try {
    const h1 = { ...authHeader(), ...(opts.headers || {}) };
    const r = await fetch(path, { ...opts, headers: h1 });
    if (r.status === 401) {
      if (_refreshToken) {
        const ok = await refreshToken();
        if (!ok) { await logout(); return null; }
        const h2 = { ...authHeader(), ...(opts.headers || {}) };
        const retry = await fetch(path, { ...opts, headers: h2 });
        if (retry.ok) return await retry.json();
      }
      await logout();
      return null;
    }
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch (_) {
    return null;
  }
}

// â”€â”€ WebSocket: robot status â”€â”€
let _ws = null;
let _wsDelay = 1000;
let _wsLoggedOut = false;
let _wsReconnectTimer = null;
let _wsOnEvent = null;
let _wsOnStatusChange = null;

export function connectWebSocket(onEvent, onStatusChange) {
  _wsOnEvent = onEvent;
  _wsOnStatusChange = onStatusChange;
  _wsLoggedOut = false;
  _doConnect();
}

function _doConnect() {
  if (_wsLoggedOut || !_token) return;
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  _ws = new WebSocket(`${proto}//${location.host}/ws?token=${encodeURIComponent(_token)}`);
  _ws.onopen = () => {
    _wsDelay = 1000;
    _wsOnStatusChange && _wsOnStatusChange('online');
  };
  _ws.onmessage = e => {
    try { _wsOnEvent && _wsOnEvent(JSON.parse(e.data)); } catch (_) {}
  };
  _ws.onclose = () => {
    _wsOnStatusChange && _wsOnStatusChange('offline');
    if (_wsLoggedOut) return;
    _wsReconnectTimer = setTimeout(_doConnect, Math.min(_wsDelay, 12000));
    _wsDelay = Math.min(_wsDelay * 1.5, 12000);
  };
  _ws.onerror = () => _ws && _ws.close();
}

export function disconnectWebSocket() {
  _wsLoggedOut = true;
  if (_wsReconnectTimer) { clearTimeout(_wsReconnectTimer); _wsReconnectTimer = null; }
  if (_ws) { _ws.close(); _ws = null; }
}

// â”€â”€ Mom-talk audio (protected behavior) â”€â”€
let _momMicActive = false;
let _momMediaStream = null;
let _momAudioWs = null;
let _momScriptProcessor = null;
let _momAudioCtx = null;

export async function startMomMic() {
  if (!_token) throw new Error('Vui lÃ²ng Ä‘Äƒng nháº­p trÆ°á»›c');
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('TrÃ¬nh duyá»‡t khÃ´ng há»— trá»£ mic. DÃ¹ng Chrome/Firefox vÃ  truy cáº­p qua HTTPS.');
  }
  try {
    _momMediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    const sr = await apiFetch('/api/mom/start', { method: 'POST' });
    if (!sr) throw new Error('KhÃ´ng thá»ƒ bÃ¡o server');
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    _momAudioWs = new WebSocket(`${proto}//${location.host}/api/mom/audio?token=${encodeURIComponent(_token)}`);
    _momAudioWs.binaryType = 'arraybuffer';
    await new Promise((res, rej) => {
      _momAudioWs.onopen = res;
      _momAudioWs.onerror = () => rej(new Error('WebSocket lá»—i'));
      setTimeout(() => rej(new Error('Timeout')), 5000);
    });
    _momAudioCtx = new AudioContext({ sampleRate: 16000 });
    const source = _momAudioCtx.createMediaStreamSource(_momMediaStream);
    _momScriptProcessor = _momAudioCtx.createScriptProcessor(512, 1, 1);
    _momScriptProcessor.onaudioprocess = event => {
      if (!_momMicActive || !_momAudioWs || _momAudioWs.readyState !== WebSocket.OPEN) return;
      _momAudioWs.send(event.inputBuffer.getChannelData(0).buffer.slice(0));
    };
    const sg = _momAudioCtx.createGain();
    sg.gain.value = 0;
    source.connect(_momScriptProcessor);
    _momScriptProcessor.connect(sg);
    sg.connect(_momAudioCtx.destination);
    _momMicActive = true;
    return true;
  } catch (err) {
    stopMomMic();
    throw err;
  }
}

export function stopMomMic() {
  _momMicActive = false;
  if (_momScriptProcessor) { _momScriptProcessor.disconnect(); _momScriptProcessor = null; }
  if (_momAudioCtx) { _momAudioCtx.close(); _momAudioCtx = null; }
  if (_momMediaStream) { _momMediaStream.getTracks().forEach(t => t.stop()); _momMediaStream = null; }
  if (_momAudioWs) { _momAudioWs.close(); _momAudioWs = null; }
  if (_token) fetch('/api/mom/stop', { method: 'POST', headers: authHeader() }).catch(() => {});
}

export function isMomMicActive() { return _momMicActive; }

// â”€â”€ Conversations (Tier 1) â”€â”€
export async function getConversations(limit = 20) {
  return apiFetch(`/api/conversations?limit=${limit}`);
}

export async function getConversation(id) {
  return apiFetch(`/api/conversations/${id}`);
}

// â”€â”€ Tier 2: Mock adapters â”€â”€

export async function getChildProfiles() {
  // TODO: backend integration â€” GET /api/children
  console.info('[MOCK] child-profiles: using mock data');
  return mockChildProfiles();
}

export async function exportReport(fmt) {
  // TODO: backend integration â€” POST /api/reports/export
  console.info('[MOCK] export-report: coming soon');
  return null;
}

export async function getMonthlyEmotions(month) {
  // TODO: backend integration â€” GET /api/emotions/monthly
  console.info('[MOCK] monthly-emotions: using mock data');
  return mockMonthlyEmotions(month);
}

export async function getRoomLocation() {
  // TODO: backend integration â€” GET /api/robot/location
  console.info('[MOCK] room-location: coming soon');
  return null;
}

export async function getRadioChannels() {
  // TODO: backend integration â€” GET /api/entertainment/radio
  console.info('[MOCK] radio-channels: using mock data');
  return mockRadioChannels();
}

export async function getVideoLessons() {
  // TODO: backend integration â€” GET /api/entertainment/videos
  console.info('[MOCK] video-lessons: using mock data');
  return mockVideoLessons();
}

export async function getInteractiveGames() {
  // TODO: backend integration â€” GET /api/games/interactive
  console.info('[MOCK] interactive-games: using mock data');
  return mockInteractiveGames();
}

export async function getSystemLogs() {
  // TODO: backend integration â€” GET /api/admin/logs
  console.info('[MOCK] system-logs: using mock data');
  return mockSystemLogs();
}

export async function savePushSettings(settings) {
  // TODO: backend integration â€” POST /api/settings/notifications
  console.info('[MOCK] push-settings: coming soon');
  return null;
}

export async function saveSleepSchedule(schedule) {
  // TODO: backend integration â€” POST /api/settings/sleep
  console.info('[MOCK] sleep-schedule: coming soon');
  return null;
}

export async function saveTimeLimits(limits) {
  // TODO: backend integration â€” POST /api/settings/time-limits
  console.info('[MOCK] time-limits: coming soon');
  return null;
}

export async function saveAgeFilter(filter) {
  // TODO: backend integration â€” POST /api/settings/age-filter
  console.info('[MOCK] age-filter: coming soon');
  return null;
}

export async function getParentChatHistory() {
  // TODO: backend integration â€” GET /api/conversations/parent
  console.info('[MOCK] parent-chat: coming soon');
  return null;
}
