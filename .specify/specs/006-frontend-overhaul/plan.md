# Implementation Plan: Frontend Overhaul — Parent App + Admin

> Spec: [spec.md](./spec.md) · Created 2026-06-27 · Feature dir `.specify/specs/006-frontend-overhaul/`
> Convention theo 004/005 (plan gọn, không tách research.md/contracts riêng).

## Technical Context

- **Frontend**: React 18 + Vite 5 SPA, không React Router (tab routing qua object map trong `App.jsx`). CSS thuần trong 1 file `frontend/parent_app/src/styles.css` với design token ở `:root`. Breakpoint mobile 768px.
- **Backend**: FastAPI, SQLite (`runtime/robot_bi.db`), auth Argon2id + JWT (`src/infrastructure/auth/auth.py`).
- **Schema migration pattern (đã có)**: `db.init_db()` dùng `CREATE TABLE IF NOT EXISTS` + `PRAGMA table_info(<t>)` để dò cột thiếu + `ALTER TABLE ADD COLUMN` (idempotent). P7 BÁM ĐÚNG mẫu này.
- **JWT hiện tại** (`create_access_token`): payload `sub, family, type, tv(token_version), iat, exp`. `verify_access_token` kiểm `type`, `token_version`, `is_active`. `get_current_user` trả `{user_id, family_name}` (chưa có role/is_admin) — **thêm field là additive, 21 callers không vỡ**.
- **Phân quyền admin hiện có**: `require_admin`/`is_user_admin` trong `admin_router.py` — dùng làm KHUÔN cho `require_role`.
- **Tiến độ môn học**: `education_router.education_summary` (:89) → `progress_tracker.get_subject_progress` (:73) đã trả tiến độ theo môn → dùng cho P3.
- **WiFi**: `wifi_router.py` đã có `GET /api/wifi/status`, `POST /api/wifi/add`, `POST /api/motor/register` — P6 chỉ thêm FE.
- **Tab arrays**: `components/Sidebar.jsx` + `components/BottomNav.jsx` (mỗi file 1 mảng TABS) — P3 sửa nhãn ở cả hai.

## Constitution / Protected-Fixes Check

Không có `.specify/memory/constitution.md`; nguồn ràng buộc là **Protected Fixes trong PROJECT.md**. Đối chiếu:

| Protected Fix | Ảnh hưởng đợt này | Cách giữ |
|---|---|---|
| JWT access/refresh + rotation, `verify_access_token` | P7 thêm claim `role` | CHỈ thêm field vào payload; không đổi logic verify token_version/is_active/type. Token cũ thiếu `role` → mặc định an toàn (coi như parent/đọc) |
| Rate-limit login (5→15p), `login_attempts` | Con login bằng PIN | Tái dùng đúng luồng `authenticate_user` + rate-limit hiện có, không tạo path mới |
| Cô lập đa gia đình (`family_id` scope) | P7 endpoint family | Mọi query members/permissions BẮT BUỘC scope `family_name`; require_role(owner) |
| DB path/schema tasks/conversations/turns | P7 thêm cột users + bảng mới | KHÔNG đụng schema tasks/conversations/turns; chỉ ADD COLUMN users + bảng `family_permissions` mới |
| Argon2id auth | PIN của con | Hash PIN bằng `hash_password` sẵn có (Argon2id); verify qua `verify_password` |
| RAG / audio / safety filter / 5-provider chain | Không đụng | Đợt này thuần FE + auth/family; không chạm các vùng này |

→ **Không có vi phạm**. P7 là phần rủi ro nhất, đã có chiến lược giữ nguyên hành vi protected.

## Architecture & Affected Files

### P1 — Bug hiển thị (FE-only)
- `pages/HomePage.jsx`: sửa 2 `metric-label` cứng (dòng ~130,140) → "Phút học" / "Nhiệm vụ".
- `pages/MorePage.jsx`: 5 thẻ shortcut `<div>` → `<button>` + onClick cuộn tới section (dùng `ref`/`scrollIntoView`).
- `pages/JournalPage.jsx`: nhánh `emotionData` rỗng → `SectionState state="empty"` thay vì `"loading"` (dòng ~433).
- `pages/JournalPage.jsx` (+ `index.html` root): `<input type="date">` thêm `lang="vi"` (hoặc set trên `<html lang="vi">`).

### P2 — Design system / CSS (`styles.css` + docs)
- `.btn-sm` (dòng 845) `min-height:36px` → `var(--tap-min)` (hoặc ≥44px nếu cần mật độ, ghi chú).
- `.settings-close` (497) + `.pill-tab` (589) `40px` → ≥44px.
- `.btn-back` (890) `min-height:auto` → bỏ override (tap-min) nhưng giữ layout (dùng padding).
- `.camera-section` (532) `aspect-ratio:16/9` → thêm `max-height` (vd `min(60vh, 480px)`).
- `.more-grid` (774) + `.more-card` (777) `aspect-ratio:1` → responsive: desktop bỏ aspect-ratio vuông / giới hạn `max-width`, dùng `repeat(auto-fit, minmax(...))`.
- `docs/DESIGN_SYSTEM.md`: cập nhật mô tả tap target + camera + more-grid cho khớp.

### P3 — Cấu trúc tab (FE-only)
- `components/Sidebar.jsx`: `learninghub` label "Học Anh văn"→"Học tập"; `learning` "Học tập"→"Theo dõi học tập"; cân nhắc đổi icon cho hợp.
- `components/BottomNav.jsx`: `learninghub` "Anh văn"→"Học"; `learning` "Học"→"Theo dõi".
- `pages/LearningPage.jsx`: đổi tiêu đề trang + thêm khối "Tổng quan tiến độ 3 môn" gọi `/api/education/summary` (subject_progress en/math/science).
- `services/api.js`: thêm `getEducationSummary()` nếu chưa có.
- Cập nhật `docs/DESIGN_SYSTEM.md` (nhãn tab) — đã đổi số tab ở doc-sync trước, chỉnh nhãn.

### P4 — Monitor UX (FE-only)
- `pages/MonitorPage.jsx`: bọc mỗi section bằng component gập/mở (state `expanded`); BỎ khối "báo cáo tuần" trùng HomePage; section camera dùng class đã sửa ở P2.
- (Tùy chọn) tạo `components/CollapsibleSection.jsx` dùng chung.

### P5 — Admin polish (FE-only)
- `pages/admin/*.jsx` (9 file): thay inline style rời rạc bằng class design-system / token; thống nhất 1 kiểu toggle (tạo `components/admin/Toggle.jsx` hoặc class CSS chung).
- `styles.css`: thêm nhóm class admin (`.admin-*`) dùng token bo góc/màu/spacing; responsive cho màn hẹp.
- `AdminApp.jsx`: màu active dùng token thay `#334155`.

### P6 — WiFi UI (FE-only, BE sẵn)
- `components/SettingsOverlay.jsx`: thêm section "📶 WiFi cho robot" (input SSID + password + nút gửi + hiển thị status).
- `services/api.js`: thêm `getWifiStatus()` → `GET /api/wifi/status`, `addWifi({ssid,password})` → `POST /api/wifi/add`.

### P7 — Gia đình & phân quyền (BE trước, rồi FE) — 3 lát cắt
**Lát C1 — nền tảng (BE)**
- `db.py init_db()`: ADD COLUMN `users.role TEXT DEFAULT 'parent'`, `users.child_profile_id TEXT` (mẫu PRAGMA+ALTER); CREATE TABLE `family_permissions` (granular — xem Data/Schema); migration set user hiện có (user đầu mỗi family hoặc is_admin → `owner`, còn lại `parent`).
- `auth.py`: `create_access_token` thêm claim `role` (đọc từ users); `get_current_user` trả thêm `role` (+ `family_name`); thêm `require_role(*allowed)` (mirror `require_admin`).
- Helper `db.py`: `get_user_role`, `create_family`, `list_family_members`, `add_existing_user_to_family`, `set_member_role`, `create_child_account`, `remove_family_member`, `get_family_permissions`, `set_family_permissions`, `list_family_child_profiles_public`, `verify_child_pin`.

**Lát C2 — quản lý thành viên + đăng nhập con (BE)**
- `src/api/routers/family_router.py` (MỚI) + đăng ký trong `server.py`:
  - `POST /api/family/create` (user chưa có family) — tạo family → owner.
  - `GET /api/family/members` (owner) — list thành viên.
  - `POST /api/family/members/add` (owner) — thêm tài khoản người lớn ĐÃ đăng ký bằng username + chọn role; chặn user đang ở family khác.
  - `POST /api/family/members/child` (owner) — tạo con từ `child_profile_id` có sẵn + PIN→Argon2 (1↔1).
  - `PUT /api/family/members/{user_id}/role` (owner) — đổi role; `DELETE /api/family/members/{user_id}` (owner) — chặn tự xóa / owner cuối.
  - `GET/PUT /api/family/permissions` (owner) — đọc/ghi quyền con (granular).
- `auth_router.py` (mở rộng): `GET /api/auth/child-profiles?family=` (công khai, chỉ id+tên+avatar theo family) + `POST /api/auth/child-login` (`{family, child_profile_id, pin}` → JWT role=child), tái dùng rate-limit hiện có.
- Gắn `require_role` cho route nhạy cảm; route theo từng quyền `child_can_*` (vd safety/sleep/notifications/device/members) phải kiểm `family_permissions` cho child.

**Lát C3 — FE**
- `App.jsx`: đọc `role` từ user; lọc TABS + ẩn/hiện mục Settings theo `role` + `family_permissions` (con: luôn có avatar/tên + WiFi; còn lại theo toggle owner).
- `pages/LoginPage.jsx`: thêm chế độ "Đăng nhập cho bé" — nhập/ghi nhớ mã gia đình → hiện lưới hồ sơ trẻ (`/api/auth/child-profiles`) → chọn → nhập PIN (`/api/auth/child-login`). Người lớn vẫn login username/password như cũ.
- `components/SettingsOverlay.jsx`: (owner) section "👨‍👩‍👧 Thành viên gia đình" — tạo family nếu chưa có, thêm người lớn theo username + role, tạo con từ hồ sơ + PIN, bảng toggle quyền con; (child) chỉ render mục avatar/tên + WiFi + mục được owner bật.
- `services/api.js`: helpers `createFamily/getFamilyMembers/addFamilyMember/setMemberRole/createChildAccount/removeFamilyMember/getFamilyPermissions/setFamilyPermissions/getChildProfilesPublic/childLogin`.

### P8 — Parity (xuyên suốt)
- Sau mỗi P động giao diện: kiểm desktop ≥768px và mobile <768px đủ chức năng; không cắt nội dung. Không file riêng — là tiêu chí review.

## Data / Schema changes

```sql
-- users: thêm cột (ALTER TABLE ADD COLUMN, idempotent qua PRAGMA check)
ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'parent';        -- 'owner'|'parent'|'child'
ALTER TABLE users ADD COLUMN child_profile_id TEXT;             -- chỉ set khi role='child' (1↔1 hồ sơ)

-- family_permissions (MỚI, per family) — granular theo clarify 2026-06-27.
-- LUÔN cho phép con: đổi avatar/tên + WiFi (không cần cột). Owner bật/tắt các mục dưới (mặc định 0 = ẩn với con):
CREATE TABLE IF NOT EXISTS family_permissions (
  family_name           TEXT PRIMARY KEY REFERENCES families(family_id) ON DELETE CASCADE,
  child_can_monitor     INTEGER NOT NULL DEFAULT 0,
  child_can_journal     INTEGER NOT NULL DEFAULT 0,
  child_can_notifications INTEGER NOT NULL DEFAULT 0,
  child_can_sleep       INTEGER NOT NULL DEFAULT 0,
  child_can_safety      INTEGER NOT NULL DEFAULT 0,
  child_can_device      INTEGER NOT NULL DEFAULT 0,
  child_can_members     INTEGER NOT NULL DEFAULT 0,
  updated_at            TEXT NOT NULL
);
```
- **Migration vai trò**: với mỗi family, gán `role='owner'` cho user `is_admin` hoặc user tạo sớm nhất; còn lại `role='parent'`. `is_admin` GIỮ NGUYÊN, độc lập với role.
- **Đăng ký & family** (clarify): tự đăng ký tạo user role mặc định; user tạo family mới → `owner`; owner thêm user-đã-đăng-ký vào family mình bằng cách set `users.family_name` + chọn role. Cần chặn 1 user ở 2 family (xem Risks).
- **PIN con**: lưu trong `users.password_hash` (Argon2id), KHÔNG cột mới. Con tạo bởi owner từ một `child_profiles` có sẵn.
- KHÔNG đụng `tasks`, `conversations`, `turns`, `auth_tokens` (Protected Fix).

## API / Contracts

| Method | Path | Quyền | Mô tả |
|---|---|---|---|
| GET | `/api/wifi/status` | user | (đã có) trạng thái WiFi robot |
| POST | `/api/wifi/add` | user | (đã có) gửi SSID/pass xuống robot — con cũng được (FR-P7-5) |
| POST | `/api/family/create` | user chưa có family | tạo gia đình mới → người tạo thành owner |
| GET | `/api/family/members` | owner | danh sách thành viên family |
| POST | `/api/family/members/add` | owner | thêm tài khoản người lớn ĐÃ đăng ký vào family bằng username + chọn role |
| POST | `/api/family/members/child` | owner | tạo tài khoản con từ child_profile_id có sẵn + PIN (1↔1) |
| PUT | `/api/family/members/{user_id}/role` | owner | đổi vai trò thành viên |
| DELETE | `/api/family/members/{user_id}` | owner | gỡ/xóa thành viên (chặn self / owner cuối) |
| GET | `/api/family/permissions` | owner | quyền con hiện tại |
| PUT | `/api/family/permissions` | owner | cập nhật quyền con (granular) |
| GET | `/api/auth/child-profiles?family=<id>` | công khai (theo family) | liệt kê hồ sơ trẻ của 1 family cho màn login con (chỉ id+tên+avatar, không dữ liệu nhạy cảm) |
| POST | `/api/auth/child-login` | công khai | đăng nhập con bằng `{family, child_profile_id, pin}` → JWT role=child |

- JWT access token: thêm claim `role` (không phá token cũ — thiếu `role` ⇒ coi là `parent`).
- `get_current_user` trả thêm `role`.
- Màn login con cần định danh family trên thiết bị (mã family hoặc ghi nhớ) trước khi gọi `child-profiles` — không phơi toàn cục.

## Phases

1. **P1** Bug hiển thị — FE, không test Python (chạy `run_tests.py` để chắc không vỡ), `npm run build`.
2. **P2** Design system/CSS + cập nhật DESIGN_SYSTEM.md.
3. **P3** Cấu trúc tab + tiến độ 3 môn.
4. **P4 ∥ P5 ∥ P6** (độc lập nhau): Monitor UX · Admin polish · WiFi UI.
5. **P7** Gia đình+role theo 3 lát C1→C2→C3, mỗi lát có test:
   - C1: test JWT mang role + `require_role` chặn child + migration không vỡ login.
   - C2: test owner tạo con→con login PIN; cô lập family; chặn self/owner-cuối.
   - C3: test tay 3 loại tài khoản thấy đúng giao diện.
6. **P8** Parity review xen kẽ mỗi phase.

Mỗi phase: commit riêng + `python tests/run_tests.py` PASS + cập nhật `.claude/handoff.md` (Rule 9).

## Risks & Open Questions

- **OQ-1 — ✅ ĐÃ CHỐT (clarify 2026-06-27)**: con đăng nhập = chọn hồ sơ trên màn login + nhập PIN (không nhập username). Cần endpoint công khai liệt kê hồ sơ theo family + endpoint child-login.
- **OQ-2 — định danh family ở màn login con**: con cần biết thuộc family nào để hiện đúng lưới hồ sơ. Đề xuất: nhập/ghi nhớ "mã gia đình" trên thiết bị (owner cung cấp) — KHÔNG liệt kê hồ sơ toàn cục. Chốt chi tiết ở `/speckit-tasks`.
- **Risk — user ở 2 gia đình**: đăng ký mở + owner add bằng username → phải chặn add user đã thuộc family khác (hoặc yêu cầu rời family cũ). Cần test.
- **Risk — endpoint child-profiles công khai**: chỉ trả id+tên+avatar, scope theo family, không lộ dữ liệu nhạy cảm; cân nhắc rate-limit để tránh dò.
- **Risk — JWT role với token cũ**: token phát trước khi có `role` sẽ thiếu claim → phải mặc định `parent` an toàn, không crash. (Đã tính trong verify.)
- **Risk — migration owner**: family nhiều user mà không ai is_admin → chọn user `created_at` sớm nhất làm owner; cần test.
- **Risk — child tự gọi API**: phải chặn ở server (require_role), không chỉ ẩn tab. Test bắt buộc SC-6.
- **Risk — P5 admin polish chạm 9 file**: dễ vỡ layout; làm từng trang, build kiểm sau mỗi trang.
- **Out of scope nhắc lại**: dashboard tùy chỉnh, goals, push PWA, email report, video call SDP — không làm đợt này.
