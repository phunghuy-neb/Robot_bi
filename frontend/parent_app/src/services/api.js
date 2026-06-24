// Robot Bi Parent App — API Service Layer
// Tier 1: Real backend (preserved behavior from legacy index.html)
// Tier 2: Wired to backend with mock fallback when backend returns no data

import {
  mockRadioChannels,
  mockVideoLessons,
  mockMonthlyEmotions,
  mockInteractiveGames,
  mockSystemLogs,
} from '../data/mockData.js';

// —— Auth Storage ——
let _token = localStorage.getItem('bi_token') || '';
let _refreshToken = localStorage.getItem('bi_refresh') || '';
let _refreshPromise = null;

function authHeader() {
  return _token ? { Authorization: 'Bearer ' + _token } : {};
}

// —— Toast ——
export let toastFn = null;
export function registerToast(fn) { toastFn = fn; }
export function showToast(msg) { toastFn && toastFn(msg); }

// —— Utilities ——
export function getBaseUrl() { return window.location.origin; }
export function getToken() { return _token; }

// —— Auth: login ——
export async function login(username, password) {
  const r = await fetch('/auth/login/v2', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || 'Sai tên đăng nhập hoặc mật khẩu.');
  }
  const data = await r.json();
  _token = data.access_token;
  _refreshToken = data.refresh_token;
  localStorage.setItem('bi_token', _token);
  localStorage.setItem('bi_refresh', _refreshToken);
  return { username: data.username || username, isAdmin: data.is_admin || false };
}

// —— Auth: logout ——
export async function logout() {
  try {
    if (_token && _refreshToken) {
      await fetch('/auth/logout', {
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

// —— Auth: refresh token ——
export async function refreshToken() {
  if (_refreshPromise) return _refreshPromise;
  _refreshPromise = (async () => {
    try {
      if (!_refreshToken) return false;
      const rr = await fetch('/auth/refresh', {
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

// —— Check existing session on app load ——
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

// —— apiFetch with 401 → refresh → retry → logout ——
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

// —— WebSocket: robot status ——
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

// —— Mom-talk audio (protected behavior) ——
let _momMicActive = false;
let _momMediaStream = null;
let _momAudioWs = null;
let _momScriptProcessor = null;
let _momAudioCtx = null;

export async function startMomMic() {
  if (!_token) throw new Error('Vui lòng đăng nhập trước');
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('Trình duyệt không hỗ trợ mic. Dùng Chrome/Firefox và truy cập qua HTTPS.');
  }
  try {
    _momMediaStream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    const sr = await apiFetch('/api/mom/start', { method: 'POST' });
    if (!sr) throw new Error('Không thể báo server');
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    _momAudioWs = new WebSocket(`${proto}//${location.host}/api/mom/audio?token=${encodeURIComponent(_token)}`);
    _momAudioWs.binaryType = 'arraybuffer';
    await new Promise((res, rej) => {
      _momAudioWs.onopen = res;
      _momAudioWs.onerror = () => rej(new Error('WebSocket lỗi'));
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

// —— Conversations (Tier 1) ——
export async function getConversations(limit = 20) {
  return apiFetch(`/api/conversations?limit=${limit}`);
}

export async function getConversation(id) {
  return apiFetch(`/api/conversations/${id}`);
}

// —— Tier 2: Backend-wired adapters with mock fallback ——

export async function getChildProfiles() {
  const data = await apiFetch('/api/children');
  if (data?.children?.length) {
    return data.children.map(c => ({
      id: c.child_id,
      name: c.name,
      age: c.age ?? 0,
      grade: c.grade || '',
      avatar: c.avatar || '👤',
      dailyLimit: 0,
    }));
  }
  return [];
}

export async function exportReport(fmt = 'csv', options = {}) {
  const today = new Date().toISOString().slice(0, 10);
  const thirtyDaysAgo = new Date(Date.now() - 30 * 86400_000).toISOString().slice(0, 10);
  const format = (fmt === 'pdf') ? 'pdf' : 'csv';
  const r = await fetch('/api/reports/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({
      format,
      start_date: options.start_date || thirtyDaysAgo,
      end_date: options.end_date || today,
      sections: options.sections || ['events', 'conversations', 'emotions', 'education', 'tasks'],
      child_id: options.child_id || null,
    }),
  });
  if (!r.ok) return null;
  const blob = await r.blob();
  const start = options.start_date || thirtyDaysAgo;
  const end = options.end_date || today;
  return { blob, filename: `robot-bi-${start}--${end}.${format}` };
}

export async function getMonthlyEmotions(month) {
  const query = month ? `?month=${encodeURIComponent(month)}` : '';
  const data = await apiFetch(`/api/emotions/monthly${query}`);
  const weeks = data?.weeks;
  if (weeks?.length) {
    return weeks.map((w, i) => {
      const total = w.count || (w.happy + w.neutral + w.sad + w.stressed) || 1;
      const pct = v => Math.round((v / total) * 100);
      return {
        week: `Tuần ${i + 1}`,
        happy: pct(w.happy || 0),
        neutral: pct(w.neutral || 0),
        sad: pct(w.sad || 0),
        stressed: pct(w.stressed || 0),
      };
    });
  }
  return mockMonthlyEmotions(month);
}

export async function getRoomLocation() {
  // BLOCKED: no component renders this data yet
  return null;
}

export async function getRadioChannels() {
  const data = await apiFetch('/api/entertainment/radio');
  const items = data?.channels || data?.items || [];
  if (items.length) {
    return items.map(ch => ({
      id: ch.content_id,
      name: ch.title,
      icon: '📻',
      genre: ch.tags?.[0] || ch.description || '',
      frequency: '',
      url: ch.source_url || '',
    }));
  }
  return mockRadioChannels();
}

export async function getVideoLessons() {
  const data = await apiFetch('/api/entertainment/videos');
  const items = data?.videos || data?.items || [];
  if (items.length) {
    return items.map(v => ({
      id: v.content_id,
      title: v.title,
      thumbnail: v.thumbnail_url || '🎬',
      subject: v.tags?.[0] || '',
      duration: v.duration || '',
      age: (v.age_min != null && v.age_max != null) ? `${v.age_min}-${v.age_max}` : '',
      url: v.source_url || '',
    }));
  }
  return mockVideoLessons();
}

export async function getInteractiveGames() {
  const data = await apiFetch('/api/games/interactive');
  const items = data?.games || data?.items || [];
  if (items.length) {
    return items.map(g => ({
      id: g.content_id,
      name: g.title,
      icon: '🎮',
      description: g.description || '',
      difficulty: 'Trung bình',
      age: (g.age_min != null && g.age_max != null) ? `${g.age_min}-${g.age_max}` : '',
    }));
  }
  return mockInteractiveGames();
}

export async function getSystemLogs() {
  const data = await apiFetch('/api/admin/logs');
  if (data?.logs) {
    return data.logs.map((entry, i) => ({
      id: i + 1,
      level: entry.level,
      message: entry.message,
      timestamp: entry.timestamp,
      source: entry.component || entry.source || '',
    }));
  }
  return [];
}

export async function addChildProfile(profileData) {
  return apiFetch('/api/children', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profileData),
  });
}

export async function deleteChildProfile(childId) {
  return apiFetch(`/api/children/${childId}`, { method: 'DELETE' });
}

export async function getLearningModules() {
  return apiFetch('/api/learning/modules');
}

export async function getLearningLesson(lessonId) {
  return apiFetch(`/api/learning/lessons/${lessonId}`);
}

export async function submitLearningLesson(lessonId, answers) {
  return apiFetch(`/api/learning/lessons/${lessonId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  });
}

export async function getLearningProgress() {
  return apiFetch('/api/learning/progress');
}

// —— Exam system (Phase 1): question bank, exam papers, attempts ——
export async function getExamSubjects() {
  return apiFetch('/api/learning/subjects');
}

export async function getExamTracks() {
  return apiFetch('/api/learning/tracks');
}

export async function getExams(filters = {}) {
  const qs = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v != null && v !== '')
  ).toString();
  return apiFetch(`/api/learning/exams${qs ? `?${qs}` : ''}`);
}

export async function getExam(paperId) {
  return apiFetch(`/api/learning/exams/${paperId}`);
}

export async function submitExam(paperId, answers, timeSpentSeconds = 0) {
  return apiFetch(`/api/learning/exams/${paperId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers, time_spent_seconds: timeSpentSeconds }),
  });
}

// TOEIC Speaking & Writing: free-text grading (rubric + LLM, offline fallback).
// `responses` = written answers (writing skill); `transcripts` = spoken text
// (speaking skill). The backend reads the relevant map based on the paper skill.
export async function submitToeicSW(paperId, { responses = {}, transcripts = {}, timeSpentSeconds = 0 } = {}) {
  return apiFetch(`/api/learning/exams/${paperId}/submit-toeic-sw`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ responses, transcripts, time_spent_seconds: timeSpentSeconds }),
  });
}

// Custom exams: parent tạo đề riêng (gia đình); admin is_global=true → đề chung.
export async function createCustomExam(payload) {
  return apiFetch('/api/learning/exams/custom', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function deleteExam(paperId) {
  return apiFetch(`/api/learning/exams/${paperId}`, { method: 'DELETE' });
}

export async function adminListPapers() {
  const data = await apiFetch('/api/learning/admin/papers');
  return data?.papers || [];
}

export async function getExamSessions(limit = 50) {
  return apiFetch(`/api/learning/exams/sessions?limit=${limit}`);
}

export async function getExamSession(sessionId) {
  return apiFetch(`/api/learning/exams/sessions/${sessionId}`);
}

// —— Admin content pipeline (is_admin only) ——
export async function adminGenerateQuestions(payload) {
  return apiFetch('/api/learning/admin/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function adminReviewQueue(params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v != null && v !== '')
  ).toString();
  return apiFetch(`/api/learning/admin/review${qs ? `?${qs}` : ''}`);
}

export async function adminReviewQuestion(questionId, action, edits = {}) {
  return apiFetch(`/api/learning/admin/review/${questionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, ...edits }),
  });
}

export async function adminAssembleExam(payload) {
  return apiFetch('/api/learning/admin/exams', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function getSleepSchedule() {
  return apiFetch('/api/settings/sleep');
}

export async function saveSleepSchedule(schedule) {
  return apiFetch('/api/settings/sleep', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      enabled: schedule.enabled !== false,
      start_time: schedule.start_time || '21:00',
      end_time: schedule.end_time || '06:30',
      days: schedule.days || ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
      timezone: schedule.timezone || 'Asia/Ho_Chi_Minh',
    }),
  });
}

export async function getTimeLimits(child_id = null) {
  const q = child_id ? `?child_id=${encodeURIComponent(child_id)}` : '';
  return apiFetch(`/api/settings/time-limits${q}`);
}

export async function saveTimeLimits(limits) {
  return apiFetch('/api/settings/time-limits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      child_id: limits.child_id || null,
      enabled: limits.enabled !== false,
      daily_limit_minutes: limits.daily_limit_minutes || 60,
      warning_minutes: limits.warning_minutes || 10,
      reset_time: limits.reset_time || '00:00',
    }),
  });
}

export async function getAgeFilter(child_id = null) {
  const q = child_id ? `?child_id=${encodeURIComponent(child_id)}` : '';
  return apiFetch(`/api/settings/age-filter${q}`);
}

export async function saveAgeFilter(filter) {
  return apiFetch('/api/settings/age-filter', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      child_id: filter.child_id || null,
      enabled: filter.enabled !== false,
      min_age: filter.min_age || 5,
      max_age: filter.max_age || 12,
      blocked_topics: filter.blocked_topics || [],
      allowed_topics: filter.allowed_topics || [],
      strict_mode: filter.strict_mode !== false,
    }),
  });
}

export async function getNotificationSettings() {
  return apiFetch('/api/settings/notifications');
}

export async function savePushSettings(settings) {
  return apiFetch('/api/settings/notifications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      enabled: settings.enabled !== false,
      event_types: settings.event_types || {},
      quiet_hours: settings.quiet_hours || {},
      channels: settings.channels || { in_app: true, web_push: false },
      push_subscription: settings.push_subscription || null,
    }),
  });
}

export async function getDeviceConnectionUrl(purpose = 'parent_app') {
  const data = await apiFetch(`/api/device/connection-qr?purpose=${encodeURIComponent(purpose)}&ttl_seconds=300`);
  return data?.qr || null;
}

export async function getRobotLocation() {
  return apiFetch('/api/robot/location');
}

export async function getParentChatHistory(limit = 20) {
  return apiFetch(`/api/parent-chat?limit=${limit}`);
}

export async function sendParentChat(message) {
  return apiFetch('/api/parent-chat/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
}

// Camera stop signal — dispatches event so MonitorPage can set camOn=false
export function stopCamera() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('bi:stopcamera'));
  }
}

// Audio monitor cleanup alias
export function stopAudioMonitor() { stopMomMic(); }

// —— Admin: user account management (is_admin only) ——
export async function adminListUsers() {
  const data = await apiFetch('/api/admin/users');
  return data?.users || [];
}

export async function adminSetUserActive(userId, active) {
  return apiFetch(`/api/admin/users/${userId}/active`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active }),
  });
}

export async function adminSetUserAdmin(userId, isAdmin) {
  return apiFetch(`/api/admin/users/${userId}/admin`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_admin: isAdmin }),
  });
}

export async function adminResetPassword(userId, newPassword) {
  return apiFetch(`/api/admin/users/${userId}/reset-password`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_password: newPassword }),
  });
}

export async function adminDeleteUser(userId) {
  return apiFetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
}

// —— Admin: public API keys + feature toggles (is_admin only) ——
export async function adminGetKeys() {
  const data = await apiFetch('/api/admin/config/keys');
  return data?.keys || [];
}

export async function adminSetKey(name, value) {
  return apiFetch(`/api/admin/config/keys/${name}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  });
}

export async function adminClearKey(name) {
  return apiFetch(`/api/admin/config/keys/${name}`, { method: 'DELETE' });
}

export async function adminTestKey(name) {
  return apiFetch(`/api/admin/config/keys/${name}/test`, { method: 'POST' });
}

export async function adminGetToggles() {
  const data = await apiFetch('/api/admin/config/toggles');
  return data?.toggles || [];
}

export async function adminSetToggle(name, enabled) {
  return apiFetch(`/api/admin/config/toggles/${name}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
}

// —— YouTube: allowlist GLOBAL (admin — mọi gia đình thấy) ——
export async function adminGetYoutubeChannels() {
  const data = await apiFetch('/api/admin/youtube/channels');
  return data || { channels: [], available: false, enabled: false, has_key: false };
}

export async function adminAddYoutubeChannel(channel) {
  return apiFetch('/api/admin/youtube/channels', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(channel),
  });
}

export async function adminRemoveYoutubeChannel(channelId) {
  return apiFetch(`/api/admin/youtube/channels/${channelId}`, { method: 'DELETE' });
}

// —— YouTube: kênh của GIA ĐÌNH (parent tự thêm) ——
export async function getMyYoutubeChannels() {
  const data = await apiFetch('/api/entertainment/youtube/channels');
  return data || { channels: [], global_count: 0, available: false };
}

export async function addMyYoutubeChannel(channel) {
  return apiFetch('/api/entertainment/youtube/channels', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(channel),
  });
}

export async function removeMyYoutubeChannel(channelId) {
  return apiFetch(`/api/entertainment/youtube/channels/${channelId}`, { method: 'DELETE' });
}

// —— An toàn trẻ (admin — GLOBAL) ——
export async function adminGetSafetyConfig() {
  const data = await apiFetch('/api/admin/safety/config');
  return data || { blocklist_words: [], blocked_topics: [], policy: {} };
}

export async function adminSetSafetyBlocklist(words) {
  return apiFetch('/api/admin/safety/blocklist', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ words }),
  });
}

export async function adminSetSafetyTopics(topics) {
  return apiFetch('/api/admin/safety/topics', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topics }),
  });
}

export async function adminSetSafetyPolicy(policy) {
  return apiFetch('/api/admin/safety/policy', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(policy),
  });
}

export async function adminGetSafetyStats(limit = 50) {
  const data = await apiFetch(`/api/admin/safety/stats?limit=${limit}`);
  return data || { counts: {}, recent: [] };
}

export async function adminResetSafetyStats() {
  return apiFetch('/api/admin/safety/stats/reset', { method: 'POST' });
}
