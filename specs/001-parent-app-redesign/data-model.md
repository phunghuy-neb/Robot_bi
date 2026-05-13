# Data Model: Parent App UI Redesign

**Feature**: 001-parent-app-redesign | **Date**: 2026-05-13

> Note: This is a frontend-only redesign. No backend schema changes. All entities below are either (a) read from existing APIs, or (b) frontend-local mock state.

---

## Entities từ Existing Backend API

### Conversation
Source: `GET /api/conversations`, `GET /api/conversations/{id}`
```
session_id:          string   (PK)
family_id:           string   (scoped)
title:               string
started_at:          datetime
ended_at:            datetime | null
turn_count:          number
is_homework:         boolean
homework_marked_at:  datetime | null
```
UI usage: Nhật ký tab (thread list, detail modal), Giám sát tab.

### Event
Source: `GET /api/events`
```
event_id:    string   (PK)
family_id:   string   (scoped)
type:        string   (e.g. 'cry', 'wake_word', 'safety_filter', 'task_complete')
data:        object   (varies by type)
created_at:  datetime
```
UI usage: Nhật ký tab (event list with client-side filter), Trang chu (recent events).

### WeeklyReport
Source: `GET /api/analytics/weekly`
```
week_start:       date
total_sessions:   number
total_minutes:    number
avg_session_min:  number
emotion_summary:  { happy: n, sad: n, neutral: n, ... }
homework_count:   number
task_completion:  number  (0.0–1.0)
```
UI usage: Trang chu (summary card), Giam sat (detail breakdown).

### EmotionSummary
Source: `GET /api/emotions`
```
date:     date
emotions: Array<{ type: string, count: number, pct: number }>
```
UI usage: Giam sat tab.

### Task
Source: `GET /api/tasks`
```
task_id:          string
family_id:        string
name:             string
remind_time:      string | null
completed_today:  boolean
stars:            number
created_at:       datetime
last_reminded:    datetime | null
import_key:       string | null
```
UI usage: Hoc tap tab (task list).

### VocabWord
Source: `GET /api/education/vocabulary`
```
emoji:    string
word:     string
meaning:  string
```
UI usage: Hoc tap tab (vocab grid).

### Story
Source: `GET /api/stories`
```
id:       string
title:    string
emoji:    string
type:     string  ('fable' | 'fairy_tale' | 'bedtime')
duration: string
```
UI usage: Hoc tap tab, Them tab.

### MusicTrack
Source: `GET /api/music/status`, playlist endpoints
```
title:    string
artist:   string
playing:  boolean
progress: number  (0.0–1.0)
```
UI usage: Them tab (music player).

### RobotWifiStatus
Source: `GET /api/wifi/status`
```
connected:   boolean
ssid:        string | null
rssi:        number | null
ip:          string | null
```
UI usage: Sidebar robot status card (WiFi sub-label).

### AdminFamily
Source: `GET /api/admin/families` (admin only)
```
family_id:    string
display_name: string
created_at:   datetime
```
UI usage: Cai dat > Che do ky thuat (admin families list).

---

## Frontend-Local State (React — không sync backend)

### App.jsx top-level state (React useState)
```javascript
// Authentication
const [isLoggedIn, setIsLoggedIn] = useState(false);
const [user, setUser] = useState({ username: '', isAdmin: false });

// Navigation
const [activeTab, setActiveTab] = useState('home');  // 'home'|'monitor'|'learning'|'journal'|'more'

// Settings overlay
const [settingsOpen, setSettingsOpen] = useState(false);

// Robot status (driven by WebSocket onEvent)
const [robotStatus, setRobotStatus] = useState('connecting');  // 'online'|'offline'|'connecting'
const [wifiInfo, setWifiInfo] = useState({ ssid: null, rssi: null });

// Active child profile
const [activeChild, setActiveChild] = useState(null);  // ChildProfile | null

// Toast
const [toastMsg, setToastMsg] = useState(null);
```

State is passed to child components via props; no global store needed at this scale.

### Token Storage (localStorage — same keys as legacy)
```javascript
localStorage.setItem('bi_token', accessToken);    // JWT access token
localStorage.setItem('bi_refresh', refreshToken); // JWT refresh token
// Cleared on logout
```

### ChildProfile (mock, stored in localStorage 'bi_active_child')
```javascript
{
  id:     string,   // 'mock-1', 'mock-2', etc.
  name:   string,   // 'Bé Minh'
  age:    number,   // 8
  avatar: string    // emoji '👦'
}
```
Note: Persisted child profiles via backend is a future feature. Current is session-local.

### UIBadge Prop Values (FeatureBadge component)
```javascript
// <FeatureBadge type="coming-soon" />  → "Sắp hỗ trợ"
// <FeatureBadge type="mock-data" />    → "Dữ liệu mẫu"
// <FeatureBadge type="no-backend" />   → "Chưa kết nối backend"
const BADGE_TYPES = ['coming-soon', 'mock-data', 'no-backend'];
```

### RobotStatus (React state in App.jsx, driven by WebSocket)
```javascript
// robotStatus: 'online' | 'offline' | 'connecting'
// Transitions driven by connectWebSocket() onEvent callbacks in src/services/api.js
```

---

## Mock Data Shapes (for UI placeholder rendering)

### mockRadioChannel
```javascript
{ id: number, name: string, genre: string, icon: string }
```

### mockVideoLesson
```javascript
{ id: number, title: string, subject: string, duration: string, thumbnail: string }
```

### mockMonthlyEmotionData
```javascript
{
  month: string,  // 'Thang 5/2026'
  data: Array<{ week: string, happy: number, neutral: number, sad: number }>
}
```

### mockInteractiveGame
```javascript
{ id: number, name: string, icon: string, description: string, ageMin: number, ageMax: number }
```

### mockSystemLog
```javascript
{ timestamp: datetime, level: 'INFO'|'WARN'|'ERROR', message: string }
```

---

## State Transitions

### Robot Status Card
```
CONNECTING -> ONLINE  (WebSocket open + server confirms)
CONNECTING -> OFFLINE (connection timeout/error)
ONLINE -> OFFLINE     (WebSocket close event)
OFFLINE -> CONNECTING (manual reconnect / page focus)
```

### Settings Overlay
```
CLOSED -> OPEN   (setSettingsOpen(true) — Cài đặt button in Sidebar)
OPEN -> CLOSED   (setSettingsOpen(false) — close button or backdrop click)
```

### Child Profile Switcher
```
NO_CHILD  -> CHILD_SELECTED  (setActiveChild(profile))
CHILD_SELECTED -> NO_CHILD   (setActiveChild(null))
CHILD_SELECTED -> CHILD_SELECTED (setActiveChild(differentProfile))
```

### Auth Flow
```
LOGGED_OUT -> LOGGED_IN  (login() success → setIsLoggedIn(true) + setUser())
LOGGED_IN  -> LOGGED_OUT (logout() → setIsLoggedIn(false) + clear localStorage)
LOGGED_IN  -> LOGGED_OUT (401 + refresh fails → auto logout)
```

---

*Data model complete. No backend schema changes. All Tier 1 entities read from existing APIs.*
