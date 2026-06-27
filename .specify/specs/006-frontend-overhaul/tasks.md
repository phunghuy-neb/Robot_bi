# Tasks: Frontend Overhaul — Parent App + Admin

> Spec: [spec.md](./spec.md) · Plan: [plan.md](./plan.md) · Created 2026-06-27
> Thứ tự thực thi: P1→P2→P3→(P4∥P5∥P6)→P7; P8 (parity) kiểm xen kẽ + Phase Polish.
> Mỗi phase = 1 increment độc lập: commit riêng + `python tests/run_tests.py` PASS + cập nhật `.claude/handoff.md`.

## Quyết định chốt tại bước tasks (OQ-2 + PIN)

- **OQ-2 — định danh family ở màn login con**: dùng **mã gia đình** = `family_id` (chuỗi `family_name` hiện có). Màn "Đăng nhập cho bé" nhập mã gia đình một lần rồi ghi nhớ trên thiết bị (localStorage); sau đó hiện lưới hồ sơ trẻ của family đó. KHÔNG liệt kê hồ sơ toàn cục.
- **PIN con**: 4–6 chữ số, bắt buộc toàn số; hash Argon2id trong `users.password_hash` (tái dùng `hash_password`/`verify_password`); rate-limit tái dùng `login_attempts` (khóa theo `child:{family}:{child_profile_id}` hoặc IP như luồng hiện có).
- **Tests**: dùng cùng `tests/run_tests.py` (thêm Group mới cho P7); không tạo framework test khác.

---

## Phase 1: Setup
- [ ] T001 Đọc spec.md + plan.md + các file nguồn liên quan; ghi lại baseline `python tests/run_tests.py` (số PASS hiện tại) — file: `.specify/specs/006-frontend-overhaul/`, `frontend/parent_app/src/`, `src/infrastructure/`
- [ ] T002 Tạo nhánh `006-frontend-overhaul` từ `main` để gom đợt đại tu — file: (git branch)

## Phase 2: Foundational (blocking nhẹ)
- [ ] T003 Xác nhận token `--tap-min:48px` + radius (`--radius-sm/md/lg/modal`) trong `:root` đủ dùng cho mọi phase; bổ sung token còn thiếu nếu cần — file: `frontend/parent_app/src/styles.css`

---

## Phase 3: US1 (P1) — Sửa bug hiển thị · Test độc lập: nhãn/số khớp dữ liệu thật, mọi thẻ bấm-được hành động, khu rỗng hiện empty
- [x] T004 [P] [US1] Sửa 3 `metric-label` cứng ("8 hoạt động"→"Phút học", "Vui vẻ"→"Cảm xúc", "3/5 hoàn thành"→"Nhiệm vụ"), giữ `metric-num` lấy dữ liệu thật — file: `frontend/parent_app/src/pages/HomePage.jsx`
- [x] T005 [P] [US1] Đổi 5 thẻ shortcut `<div>` thành `<button>` + `scrollIntoView` tới section (refs: radio/music/knowledge/games/video). LƯU Ý: "Truyện kể" không có section trên trang → đổi thành "🔎 Tri thức" trỏ Khám phá tri thức — file: `frontend/parent_app/src/pages/MorePage.jsx`
- [x] T006 [P] [US1] Thêm `emotionState` (loading/data/empty/error); nhánh rỗng → empty state thay vì loading mãi — file: `frontend/parent_app/src/pages/JournalPage.jsx`
- [x] T007 [P] [US1] Locale ngày: `index.html` ĐÃ SẴN `<html lang="vi">` → không cần sửa — file: `frontend/parent_app/index.html`
- [x] T008 [US1] `npm run build` OK (61 modules, 712ms) — file: `frontend/parent_app/`

## Phase 4: US2 (P2) — Design system / accessibility · Test độc lập: mọi vùng chạm ≥48px, camera không quá cao, more-card không khổng lồ trên desktop
- [x] T009 [US2] `.btn-sm` 36px→`var(--tap-min)`; `.pill-tab` 40px→`var(--tap-min)`; `.btn-back` `auto`→`var(--tap-min)`; `.settings-close` 40→44px (ngoại lệ icon). NGOÀI RA gỡ 11 inline `minHeight:36` + 1 `minHeight:40` ở HomePage/MonitorPage/LearningPage/JournalPage (override CSS) — file: `frontend/parent_app/src/styles.css` + 4 page
- [x] T010 [US2] `.camera-section` thêm `max-height: min(56vh,460px)` giữ `aspect-ratio` — file: `frontend/parent_app/src/styles.css`
- [x] T011 [US2] `.more-grid` → `repeat(auto-fit, minmax(150px, 1fr))` (desktop nhiều cột, không phình) — file: `frontend/parent_app/src/styles.css`
- [x] T012 [P] [US2] DESIGN_SYSTEM.md: sửa mâu thuẫn btn-sm 36→48, thêm ngoại lệ settings-close 44 + camera max-height + more-grid responsive — file: `docs/DESIGN_SYSTEM.md`
- [x] T013 [US2] `npm run build` OK (61 modules, 654ms) — file: `frontend/parent_app/`

## Phase 5: US3 (P3) — Cấu trúc tab + theo dõi học tập · Test độc lập: nhãn tab phân biệt rõ, tiến độ 3 môn hiển thị (rỗng nếu chưa có dữ liệu)
- [x] T014 [P] [US3] Sidebar: `learninghub` "Học Anh văn"→"Học tập" (icon 🔤→📚); `learning` "Học tập"→"Theo dõi học tập" (icon 📚→📊) — file: `frontend/parent_app/src/components/Sidebar.jsx`
- [x] T015 [P] [US3] BottomNav: `learninghub` "Anh văn"→"Học" (📚); `learning` "Học"→"Theo dõi" (📊) — file: `frontend/parent_app/src/components/BottomNav.jsx`
- [x] T016 [US3] Dùng `apiFetch('/api/education/summary')` trực tiếp theo pattern LearningPage (không thêm helper riêng) — file: `frontend/parent_app/src/pages/LearningPage.jsx`
- [x] T017 [US3] LearningPage: tiêu đề "📊 Theo dõi học tập"; thêm card "Tiến độ theo môn" (en/math/science từ `subject_progress` + streak, empty state); wire progress ring về dữ liệu THẬT (trước hardcode 75%) — file: `frontend/parent_app/src/pages/LearningPage.jsx` + `styles.css` (.subject-progress-*)
- [x] T018 [P] [US3] DESIGN_SYSTEM.md: nhãn tab learning→"Theo dõi học tập", learninghub→"Học tập" — file: `docs/DESIGN_SYSTEM.md`
- [x] T019 [US3] `npm run build` OK (61 modules, 757ms) — file: `frontend/parent_app/`

## Phase 6: US4 (P4) — Monitor UX · Test độc lập: section gập/mở được, không lặp báo cáo tuần, camera cao hợp lý
- [x] T020 [P] [US4] Tạo `components/CollapsibleSection.jsx` dùng chung (state expanded, a11y) — file: `frontend/parent_app/src/components/CollapsibleSection.jsx`
- [x] T021 [US4] MonitorPage: bọc các section bằng CollapsibleSection; BỎ khối "báo cáo tuần" trùng HomePage; dùng class camera đã sửa P2 — file: `frontend/parent_app/src/pages/MonitorPage.jsx`
- [x] T022 [US4] `npm run build` OK (62 modules, 661ms) + kiểm desktop/mobile qua responsive source/build — file: `frontend/parent_app/`

## Phase 7: US5 (P5) — Admin UI polish · Test độc lập: 9 trang admin dùng token nhất quán, 1 kiểu toggle, đọc tốt trên mobile
- [x] T023 [US5] Thêm nhóm class `.admin-*` (card/table/input/btn/toggle) dùng design token — file: `frontend/parent_app/src/styles.css`
- [x] T024 [P] [US5] Tạo `components/admin/Toggle.jsx` (1 kiểu công tắc thống nhất) — file: `frontend/parent_app/src/components/admin/Toggle.jsx`
- [x] T025 [US5] AdminApp: màu active + bo góc dùng token thay `#334155`/`10` — file: `frontend/parent_app/src/pages/admin/AdminApp.jsx`
- [x] T026 [P] [US5] Chuyển inline style → class design-system: Users/ApiKeys/Exams/YouTube — file: `frontend/parent_app/src/pages/admin/UsersAdminPage.jsx`, `ApiKeysPage.jsx`, `ExamsAdminPage.jsx`, `YouTubeAdminPage.jsx`
- [x] T027 [P] [US5] Chuyển inline style → class + Toggle: Safety/Persona/Content/Logs/Stats — file: `frontend/parent_app/src/pages/admin/SafetyAdminPage.jsx`, `PersonaAdminPage.jsx`, `ContentAdminPage.jsx`, `LogsAdminPage.jsx`, `StatsAdminPage.jsx`
- [x] T028 [US5] `npm run build` OK (63 modules, 660ms) + kiểm 9 trang admin bằng responsive class/source sweep — file: `frontend/parent_app/`

## Phase 8: US6 (P6) — WiFi UI cho robot · Test độc lập: nhập SSID/pass gửi xuống robot, hiện trạng thái
- [x] T029 [US6] `services/api.js`: `getWifiStatus()`→`GET /api/wifi/status`, `addWifi({ssid,password})`→`POST /api/wifi/add` — file: `frontend/parent_app/src/services/api.js`
- [x] T030 [US6] SettingsOverlay: section "📶 WiFi cho robot" (status + SSID/password + nút gửi), load status on mount — file: `frontend/parent_app/src/components/SettingsOverlay.jsx`
- [x] T031 [US6] `npm run build` OK (646ms) — file: `frontend/parent_app/`

## Phase 9: US7 (P7) — Gia đình & phân quyền (BE trước → FE) · Test độc lập: con bị chặn route nhạy cảm cả khi gọi thẳng API; owner tạo con→con login PIN; cô lập family

### Lát C1 — Nền tảng (BE)
- [ ] T032 [US7] `db.py init_db()`: ALTER `users` ADD `role TEXT DEFAULT 'parent'` + `child_profile_id TEXT` (PRAGMA+ALTER idempotent); CREATE TABLE `family_permissions` (granular `child_can_*`); migration gán role owner/parent cho user hiện có — file: `src/infrastructure/database/db.py`
- [ ] T033 [US7] `db.py` helpers: `get_user_role`, `create_family`, `list_family_members`, `add_existing_user_to_family`, `set_member_role`, `create_child_account`, `remove_family_member`, `get_family_permissions`, `set_family_permissions`, `list_family_child_profiles_public`, `verify_child_pin` — file: `src/infrastructure/database/db.py`
- [ ] T034 [US7] `auth.py`: `create_access_token` thêm claim `role`; `get_current_user` trả thêm `role`; thêm `require_role(*allowed)` (mirror `require_admin`), token cũ thiếu `role` → mặc định `parent` — file: `src/infrastructure/auth/auth.py`
- [ ] T035 [US7] Test C1 (Group mới): JWT mang `role`; `require_role` chặn child; migration không vỡ login user cũ; family_permissions mặc định an toàn — file: `tests/run_tests.py`

### Lát C2 — Endpoint quản lý thành viên + đăng nhập con (BE)
- [ ] T036 [US7] `family_router.py` (MỚI): `POST /api/family/create`, `GET /api/family/members`, `POST /api/family/members/add` (username+role, chặn user ở family khác), `POST /api/family/members/child` (child_profile_id+PIN, 1↔1), `PUT /api/family/members/{id}/role`, `DELETE /api/family/members/{id}` (chặn self/owner-cuối), `GET/PUT /api/family/permissions` — đều `require_role('owner')` + scope family — file: `src/api/routers/family_router.py`
- [ ] T037 [US7] Đăng ký `family_router` trong app — file: `src/api/server.py`
- [ ] T038 [US7] `auth_router.py`: `GET /api/auth/child-profiles?family=` (công khai, chỉ id+tên+avatar, rate-limit) + `POST /api/auth/child-login` (`{family,child_profile_id,pin}`→JWT role=child) — file: `src/api/routers/auth_router.py`
- [ ] T039 [US7] Gắn `require_role`/kiểm `family_permissions` cho route nhạy cảm (settings safety/sleep/notifications/device, members) — chặn child khi quyền tắt — file: `src/api/routers/control_router.py`, `src/api/routers/admin_router.py`, `src/api/routers/family_router.py`
- [ ] T040 [US7] Test C2 (Group mới): owner tạo con→con login PIN OK; cô lập family (A không thấy/sửa B); chặn self-delete + owner-cuối; chặn add user đã thuộc family khác; child gọi thẳng API nhạy cảm bị 403 (SC-6) — file: `tests/run_tests.py`

### Lát C3 — FE
- [ ] T041 [US7] `services/api.js` helpers: `createFamily/getFamilyMembers/addFamilyMember/setMemberRole/createChildAccount/removeFamilyMember/getFamilyPermissions/setFamilyPermissions/getChildProfilesPublic/childLogin` — file: `frontend/parent_app/src/services/api.js`
- [ ] T042 [US7] `App.jsx`: đọc `role`; lọc TABS + ẩn/hiện mục Settings theo `role` + `family_permissions` (con: luôn avatar/tên+WiFi, còn lại theo toggle) — file: `frontend/parent_app/src/App.jsx`
- [ ] T043 [US7] `LoginPage.jsx`: thêm chế độ "Đăng nhập cho bé" (nhập/ghi nhớ mã gia đình → lưới hồ sơ → chọn → nhập PIN); người lớn giữ login username/password — file: `frontend/parent_app/src/pages/LoginPage.jsx`
- [ ] T044 [US7] `SettingsOverlay.jsx`: (owner) section "👨‍👩‍👧 Thành viên gia đình" — tạo family nếu chưa có, thêm người lớn theo username+role, tạo con từ hồ sơ+PIN, bảng toggle quyền con; (child) chỉ render avatar/tên + WiFi + mục owner bật — file: `frontend/parent_app/src/components/SettingsOverlay.jsx`
- [ ] T045 [US7] `npm run build` OK + kiểm tay 3 loại tài khoản (owner/parent/child) thấy đúng giao diện trên desktop+mobile — file: `frontend/parent_app/`

## Phase 10: Polish & Cross-Cutting (P8 parity + docs + final)
- [ ] T046 [P] Parity sweep: rà mọi màn đã đổi đảm bảo desktop=mobile, không cắt nội dung (SC-4) — file: `frontend/parent_app/src/`
- [ ] T047 [P] Cập nhật `SYSTEM_MAP.md` + `docs/STATUS_MAP.md`: vai trò gia đình, WiFi UI, family_permissions, login con — file: `SYSTEM_MAP.md`, `docs/STATUS_MAP.md`
- [ ] T048 `python tests/run_tests.py` toàn bộ PASS (bao gồm Group P7 mới) + đối chiếu Protected Fixes không hồi quy (SC-7, SC-8) — file: `tests/run_tests.py`
- [ ] T049 Cập nhật `.claude/handoff.md` (Rule 9) + đánh dấu các phase đã commit — file: `.claude/handoff.md`

---

## Dependencies & thứ tự
- Phase 1 → 2 → 3. Sau đó P2(US2) nên xong trước P3/P4/P5 (nền design).
- **US1, US2** độc lập nhau (có thể đảo) nhưng làm sớm (rủi ro thấp).
- **US4, US5, US6** độc lập nhau — chạy song song được sau US2/US3.
- **US7** làm cuối; trong US7 BẮT BUỘC C1→C2→C3 (FE phụ thuộc endpoint).
- Phase 10 sau cùng.

## Parallel opportunities
- Trong US1: T004–T007 song song (khác file).
- Trong US5: T026 ∥ T027 (nhóm trang khác nhau); T024 độc lập.
- Across stories: sau khi US2 xong, một người làm US4, người khác US5, người khác US6.

## MVP scope
- **MVP tối thiểu = US1 + US2** (app sạch bug + đạt accessibility) — giao được ngay, rủi ro thấp.
- Gia tăng: US3 (cấu trúc tab) → US6 (WiFi, nhanh) → US4/US5 → US7 (lớn nhất, làm cuối).

## Independent test criteria (tóm tắt)
- US1: nhãn/số khớp dữ liệu thật; mọi thẻ hành động; khu rỗng hiện empty.
- US2: vùng chạm ≥48px; camera/more-card không vỡ desktop.
- US3: nhãn tab phân biệt; tiến độ 3 môn hiển thị/empty.
- US4: section gập/mở; không lặp báo cáo tuần.
- US5: 9 trang admin nhất quán token + mobile-readable.
- US6: gửi WiFi + hiện status.
- US7: con bị chặn route nhạy cảm cả khi gọi thẳng API; owner tạo con→login PIN; cô lập family.
