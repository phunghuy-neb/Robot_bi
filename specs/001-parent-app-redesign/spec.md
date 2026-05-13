# Feature Specification: Redesign Giao Diện Parent App Robot Bi

**Feature Branch**: `001-parent-app-redesign`

**Created**: 2026-05-13

**Status**: Active

**Input**: Redesign toàn bộ Web Parent App của Robot Bi theo hướng frontend-first. Backend cho các chức năng mới sẽ làm sau, vòng này chỉ làm UI/UX và frontend placeholder/mock integration.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phụ huynh kiểm tra trạng thái nhanh (Priority: P1)

Một phụ huynh mở Parent App và trong vòng 3 giây biết ngay: robot có đang hoạt động không, con hôm nay thế nào, có cảnh báo gì không, và hoạt động gần nhất là gì. Phụ huynh không cần click sâu để có bức tranh tổng quan.

**Why this priority**: Dashboard tổng quan là lý do chính phụ huynh mở app mỗi ngày. Nếu app không cung cấp thông tin này ngay lập tức, giá trị cốt lõi bị mất.

**Independent Test**: Mở app → Trang chủ hiển thị trạng thái robot, tóm tắt ngày hôm nay, cảnh báo nếu có, hoạt động gần nhất — tất cả trên màn hình mà không cần scroll.

**Acceptance Scenarios**:

1. **Given** robot đang kết nối, **When** phụ huynh mở Trang chủ, **Then** badge "Đang hoạt động" màu xanh lá hiển thị rõ; tóm tắt hoạt động hôm nay hiện trên card; cảnh báo nếu có xuất hiện nổi bật.
2. **Given** robot mất kết nối, **When** phụ huynh mở Trang chủ, **Then** badge "Mất kết nối" màu đỏ hiển thị; card hiện dữ liệu lần cuối cập nhật với timestamp; app không crash.
3. **Given** phụ huynh lớn tuổi, **When** mở Trang chủ, **Then** chữ ≥16px, nền contrast ≥4.5:1 WCAG AA, không có icon-only button cho action quan trọng.

---

### User Story 2 - Phụ huynh xem nhật ký và lịch sử hoạt động (Priority: P2)

Phụ huynh vào tab Nhật ký để xem lại cuộc trò chuyện giữa robot và con, sự kiện đã xảy ra, và lọc theo loại sự kiện hoặc ngày. Phụ huynh muốn có thể xuất báo cáo để lưu hoặc chia sẻ.

**Why this priority**: Nhật ký là tính năng giám sát quan trọng thứ hai sau dashboard. Phụ huynh cần kiểm tra con đã học gì, nói gì, cảm xúc thế nào.

**Independent Test**: Tab Nhật ký → danh sách sự kiện hiện ra; bộ lọc hoạt động; nút xuất PDF/CSV hiện với badge "Sắp hỗ trợ" (không gọi API chưa tồn tại).

**Acceptance Scenarios**:

1. **Given** có sự kiện trong DB, **When** phụ huynh mở Nhật ký, **Then** danh sách hiện theo thứ tự mới nhất trước; mỗi mục có icon loại, tiêu đề, thời gian, tóm tắt.
2. **Given** phụ huynh muốn lọc, **When** chọn bộ lọc loại/ngày, **Then** danh sách lọc lại client-side ngay; bộ lọc nâng cao theo thiết bị có badge "Sắp hỗ trợ".
3. **Given** phụ huynh nhấn nút xuất PDF/CSV, **When** backend chưa sẵn, **Then** hiện thông báo "Tính năng đang được phát triển" — không gây lỗi 404/500 trong console.
4. **Given** không có sự kiện, **When** phụ huynh mở Nhật ký, **Then** hiện empty state thân thiện "Chưa có hoạt động nào" — không hiện blank/broken UI.

---

### User Story 3 - Phụ huynh cài đặt và quản lý hồ sơ (Priority: P2)

Phụ huynh vào Cài đặt để thiết lập thông số cho robot: chế độ ngủ tự động, giới hạn thời gian, bộ lọc nội dung theo tuổi. Phụ huynh có thể quản lý hồ sơ của nhiều trẻ.

**Why this priority**: Cài đặt là tính năng nền tảng để cá nhân hóa robot theo nhu cầu từng gia đình.

**Independent Test**: Mở Cài đặt → các section hiện rõ; form có label tiếng Việt; nút Lưu đủ lớn; tính năng mock có badge; Chế độ kỹ thuật chỉ hiện với admin.

**Acceptance Scenarios**:

1. **Given** phụ huynh mở Cài đặt, **When** cuộn qua các section, **Then** mỗi section có tiêu đề rõ, control có nhãn tiếng Việt; tính năng mock có badge "Sắp hỗ trợ" màu xám.
2. **Given** nhiều hồ sơ trẻ, **When** phụ huynh chọn hồ sơ khác từ sidebar user card, **Then** Trang chủ và Học tập cập nhật nội dung theo hồ sơ đã chọn.
3. **Given** user là admin, **When** vào Cài đặt, **Then** section "Chế độ kỹ thuật / Quản trị" hiển thị; phụ huynh thường không thấy section này.

---

### User Story 4 - Phụ huynh khám phá giải trí và nội dung (Priority: P3)

Phụ huynh vào tab Thêm để xem thêm tính năng giải trí: nhạc (đã có), radio, video bài học, trò chơi. Phụ huynh có thể bật nhạc qua robot từ xa.

**Why this priority**: Nội dung giải trí bổ sung giá trị thực tế nhưng không phải tính năng cốt lõi hàng ngày.

**Independent Test**: Tab Thêm → Music player hoạt động (API hiện có); Radio/Video/Trò chơi mới hiển thị badge "Sắp hỗ trợ"; không gọi API chưa tồn tại.

**Acceptance Scenarios**:

1. **Given** phụ huynh mở tab Thêm, **When** nhìn vào danh sách, **Then** Music player hoạt động bình thường; Radio/Video/Trò chơi mới hiển thị badge "Sắp hỗ trợ" — không có lỗi 404 trong console.
2. **Given** phụ huynh nhấn "Xem kênh Radio", **When** backend chưa sẵn, **Then** hiện danh sách kênh mẫu với badge "Dữ liệu mẫu - Sắp hỗ trợ".

---

### User Story 5 - Admin/phụ huynh kỹ thuật dùng chế độ quản trị (Priority: P4)

Admin cần xem nhật ký hệ thống, cấu hình kết nối thiết bị, và quản lý nhiều gia đình. Những tính năng này nằm trong khu riêng, không làm rối giao diện phụ huynh thông thường.

**Why this priority**: Admin là minority use case. Không ảnh hưởng UX của phụ huynh thông thường.

**Independent Test**: Đăng nhập admin → Cài đặt → Chế độ kỹ thuật hiển thị; phụ huynh thường không thấy section này.

**Acceptance Scenarios**:

1. **Given** user có role admin, **When** mở Cài đặt, **Then** section "Chế độ kỹ thuật / Quản trị" hiện ra với các control kỹ thuật.
2. **Given** admin xem Nhật ký hệ thống, **When** backend chưa implement, **Then** hiện placeholder log viewer với badge "Chưa kết nối backend" — không gây lỗi console.

---

### Edge Cases

- Khi JWT hết hạn trong lúc dùng app: hiện "Phiên đăng nhập đã hết hạn" và chuyển về trang đăng nhập — không crash app.
- Khi WebSocket mất kết nối: robot status card tự hiện "Đang kết nối lại..." và thử reconnect — không cần phụ huynh reload.
- Khi không có dữ liệu (trẻ chưa dùng robot hôm nay): Trang chủ hiện empty state thân thiện ("Bi đang chờ bé ra chơi!").
- Khi màn hình <768px: sidebar thu gọn thành bottom navigation bar với 5 tab icon + nhãn ngắn.
- Khi không có microphone: không hiện lỗi lặp lại trong UI; CryDetector log một lần duy nhất.
- Khi API trả về lỗi: hiện thông báo lỗi rõ ràng + nút "Thử lại" — không hiện raw error stack.

## Requirements *(mandatory)*

### Functional Requirements

**Navigation & Layout**

- **FR-001**: Sidebar chính phải có đúng 5 tab: Trang chủ, Giám sát, Học tập, Nhật ký, Thêm.
- **FR-002**: Cuối sidebar phải hiện đúng thứ tự: (1) Robot status card, (2) Signed-in user card, (3) Nút Cài đặt, (4) Nút Đăng xuất.
- **FR-003**: Robot status card hiển thị: trạng thái Đang hoạt động / Mất kết nối (từ WebSocket `/ws/events`), Wi-Fi/device health khi có.
- **FR-004**: Signed-in user card hiển thị: tên người dùng, role (Phụ huynh / Admin), hồ sơ trẻ đang chọn nếu có; nhấn vào user card để chuyển hồ sơ trẻ.
- **FR-005**: Màn hình <768px: sidebar chuyển thành bottom tab bar (5 tab, icon + nhãn tiếng Việt ngắn).
- **FR-006**: Không có tab Admin riêng; admin controls chỉ nằm trong Cài đặt > Chế độ kỹ thuật.
- **FR-007**: Cài đặt và Đăng xuất mở như modal/panel overlay hoặc route riêng — không chiếm vị trí tab chính.

**Design System**

- **FR-008**: Áp dụng đúng design token: primary #2563eb, dark #1d4ed8, accent #7c3aed, success #22c55e, warning #f59e0b, danger #ef4444, info #0ea5e9, bg #f3f7ff, card #fff, border #e5eefb, text-primary #0f172a, text-secondary #475569, text-muted #94a3b8.
- **FR-009**: Card radius 22px, button radius 12px, shadow: 0 16px 40px rgba(15,23,42,0.06).
- **FR-010**: Font: Be Vietnam Pro hoặc Plus Jakarta Sans, fallback system sans-serif. Load từ Google Fonts CDN.
- **FR-011**: Font size: body tối thiểu 16px; button label quan trọng ≥18px; tiêu đề section ≥20px; heading trang ≥24px.
- **FR-012**: Tap target tối thiểu 48px × 48px cho tất cả button và link quan trọng.
- **FR-013**: Contrast ratio ≥4.5:1 (WCAG AA) cho text đọc được trên nền.
- **FR-014**: Không dùng icon-only button cho bất kỳ action quan trọng nào — luôn có text label đi kèm.
- **FR-015**: Tone thiết kế: "Công nghệ ấm áp" — professional blue-based palette với warm accents; không dùng toy colors hay childish fonts; thân thiện nhưng không trẻ con.

**Trang chủ**

- **FR-016**: Trang chủ hiển thị trên desktop không cần scroll: robot status, tóm tắt hoạt động hôm nay, cảnh báo (nếu có), hoạt động gần nhất.
- **FR-017**: Card "Báo cáo tuần" hiển thị summary từ `/api/analytics/weekly` (API hiện có); nếu lỗi hiện empty state rõ.
- **FR-018**: Card "Vị trí phòng robot" hiển thị UI placeholder với badge "Sắp hỗ trợ" — không gọi API chưa tồn tại.

**Giám sát**

- **FR-019**: Tab Giám sát hiển thị: camera stream (MJPEG `/cam` hoặc WebRTC `/api/webrtc`), emotion summary từ `/api/emotions`, conversation list từ `/api/conversations`.
- **FR-020**: Nếu camera không khả dụng: hiện placeholder "Camera không khả dụng" — không hiện broken stream.
- **FR-021**: Card "Báo cáo tuần chi tiết" hiển thị breakdown đầy đủ từ `/api/analytics/weekly` trong tab Giám sát.

**Học tập**

- **FR-022**: Tab Học tập hiển thị: tiến độ flashcard từ `/api/education`, lịch học từ `/api/education/schedule`, vocabulary từ `/api/education/vocabulary`, stories từ `/api/stories`.
- **FR-023**: Quiz games (word quiz, voice quiz từ `game_router.py`) hiển thị trong tab Học tập như một sub-section "Luyện tập".
- **FR-024**: Sub-section "Chat với Bi" (lịch sử phụ huynh ↔ Bi tách riêng khỏi lịch sử bé) nằm trong tab Học tập với badge "Sắp hỗ trợ" — không gọi endpoint chưa tồn tại.

**Nhật ký**

- **FR-025**: Tab Nhật ký hiển thị sự kiện từ `/api/events` và conversations từ `/api/conversations`.
- **FR-026**: Bộ lọc cơ bản (loại sự kiện, khoảng ngày) chạy client-side trên dữ liệu đã tải từ API.
- **FR-027**: Bộ lọc nâng cao theo thiết bị: UI hiện với badge "Sắp hỗ trợ".
- **FR-028**: Ghi chú phụ huynh vào sự kiện: UI input hiện với badge "Sắp hỗ trợ" — không POST đến endpoint chưa tồn tại.
- **FR-029**: Phát lại file ghi âm: icon play ở trạng thái disabled với tooltip "Sắp hỗ trợ".
- **FR-030**: Nút xuất PDF/CSV: khi click hiện thông báo "Tính năng đang phát triển" — không gọi endpoint chưa tồn tại.
- **FR-031**: Biểu đồ thống kê cảm xúc theo tháng: hiện với "Dữ liệu mẫu" badge — dữ liệu mock hardcode.

**Tab Thêm**

- **FR-032**: Tab Thêm có các section: Nhạc (Music — API hiện có), Radio (badge "Sắp hỗ trợ"), Video học (badge "Sắp hỗ trợ"), Trò chơi tương tác mới (badge "Sắp hỗ trợ").
- **FR-033**: Music player kết nối với `/api/music/*` endpoints hiện có.
- **FR-034**: Radio section: danh sách kênh mock + badge "Dữ liệu mẫu - Sắp hỗ trợ".
- **FR-035**: Video học section: danh sách video mock + badge "Dữ liệu mẫu - Sắp hỗ trợ".

**Cài đặt**

- **FR-036**: Cài đặt có các section: Hồ sơ trẻ, Thông báo & Nhắc nhở, Giờ hoạt động robot, Nội dung & An toàn, Kết nối thiết bị.
- **FR-037**: Quản lý hồ sơ trẻ: UI cho phép xem/thêm/chỉnh sửa hồ sơ với badge "Dữ liệu mẫu"; persisted qua backend là tính năng sau.
- **FR-038**: Chế độ ngủ tự động (giờ bật/tắt): form time-picker UI với badge "Sắp hỗ trợ".
- **FR-039**: Giới hạn thời gian tương tác: slider/number input UI với badge "Sắp hỗ trợ".
- **FR-040**: Bộ lọc chủ đề theo tuổi: toggle group UI với badge "Sắp hỗ trợ".
- **FR-041**: Push notification settings: toggle UI với badge "Sắp hỗ trợ".
- **FR-042**: Mã QR kết nối thiết bị: QR code placeholder image với badge "Sắp hỗ trợ".

**Cài đặt > Chế độ kỹ thuật (Admin only)**

- **FR-043**: Section chỉ hiện với user có role admin (check từ JWT claims / user info response hiện có).
- **FR-044**: Nhật ký hệ thống: log viewer UI với badge "Chưa kết nối backend".
- **FR-045**: Quản lý gia đình: sử dụng `/api/admin/families` (API hiện có).

**Trạng thái UI bắt buộc**

- **FR-046**: Mọi màn hình/section phải có 3 trạng thái: loading (skeleton/spinner), error (thông báo + nút thử lại), empty (empty state thân thiện có icon và text).
- **FR-047**: Mọi tính năng chưa có backend phải dùng đúng 1 trong 3 badge: "Chưa kết nối backend" (UI disabled), "Dữ liệu mẫu" (mock data), "Sắp hỗ trợ" (coming soon placeholder).
- **FR-048**: Không gọi bất kỳ endpoint nào chưa tồn tại; mock functions/adapters chuẩn bị sẵn cho future backend integration.

**Auth & Security (Protected — không thay đổi)**

- **FR-049**: Luồng đăng nhập/đăng xuất không thay đổi: `/api/auth/login`, `/api/auth/logout`, `/api/auth/refresh`.
- **FR-050**: JWT access token, refresh token rotation, rate limiting 5 lần/15 phút giữ nguyên hoàn toàn.
- **FR-051**: Multi-family isolation: mọi API call giữ nguyên family_id scoping hiện có.

### Key Entities

- **RobotStatus**: trạng thái kết nối (từ WebSocket), uptime, WiFi health; room/location là mock.
- **ChildProfile**: hồ sơ trẻ active — tên, tuổi, avatar. Mock trong frontend session; backend là tính năng sau.
- **Event**: sự kiện từ `/api/events` — type, data, created_at, family_id.
- **Conversation**: từ `/api/conversations` — session_id, title, started_at, is_homework, turn_count.
- **WeeklyReport**: từ `/api/analytics/weekly` — session count, learning time, emotion summary.
- **UIBadge**: enum 3 loại: COMING_SOON ("Sắp hỗ trợ"), MOCK_DATA ("Dữ liệu mẫu"), NO_BACKEND ("Chưa kết nối backend").

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Phụ huynh thấy trạng thái robot và tóm tắt hôm nay trong vòng 3 giây sau khi mở Trang chủ — không cần scroll trên desktop.
- **SC-002**: Tất cả chức năng hiện có (auth, conversations, events, music, games quiz, flashcards, analytics, admin families) tiếp tục hoạt động đúng sau redesign.
- **SC-003**: Không có lỗi 404/500 nào trong console do gọi endpoint chưa tồn tại.
- **SC-004**: Tất cả text đọc được và nút nhấn được mà không cần zoom trên màn hình desktop — font ≥16px, contrast ≥4.5:1, tap target ≥48px.
- **SC-005**: Mọi màn hình có loading, error, empty state rõ ràng — không có blank/broken UI.
- **SC-006**: Layout đúng trên màn hình 375px (mobile) — sidebar thành bottom nav, không overflow.
- **SC-007**: Sidebar bottom order đúng: Robot status card → User card → Cài đặt → Đăng xuất.
- **SC-008**: SYSTEM_MAP.md được cập nhật sau khi implementation hoàn thành — phản ánh đúng màn hình và capability mới; không claim backend features chưa implement là "done".

## Assumptions

- Stack: **React + Vite**. Legacy `frontend/parent_app/index.html` được thay bằng Vite mount shell sau audit. Không giữ legacy UI song song với React UI.
- Toàn bộ UI implementation nằm trong `frontend/parent_app/src/` (main.jsx, App.jsx, styles.css, components/, pages/, services/api.js, data/mockData.js).
- Files được phép sửa/tạo: `frontend/parent_app/` (toàn bộ — package.json, vite.config.js, index.html shell, src/). Không sửa src/, firmware/, frontend/robot_display/, tests/, runtime/, logs/, .env.
- API contracts hiện có không thay đổi: endpoint paths, request/response shape, auth headers giữ nguyên.
- Auth flow (đăng nhập/đăng xuất/refresh/rate-limit) giữ nguyên hoàn toàn trong `src/services/api.js` — đây là protected behavior. Tất cả behavior từ `doLogin`, `doLogout`, `apiFetch`, `connectWS`, `startMomMic`, `stopMomMic`, `loadThreads`, `showThreadDetail` phải được tái hiện đúng.
- Font Be Vietnam Pro được import trong src/styles.css qua Google Fonts CDN; fallback sang system sans-serif khi offline.
- Mock data và badge là cách accepted để signal "backend làm sau" — không fake tính năng đã hoàn thành.
- Admin role được detect từ field `is_admin` trong login response và lưu vào React state/context.
- Switching hồ sơ trẻ là local state trong frontend session (localStorage); persisted selection qua backend là tính năng sau.
- SYSTEM_MAP.md được cập nhật SAU KHI implementation hoàn thành — không trước, không trong khi coding.
- Implementation được chia thành phases nhỏ theo tab để dễ review và kiểm tra hồi quy.

## Clarifications

### Session 2026-05-13

- Q: Feature nào dùng API hiện có, UI mock, disabled, hoặc local state? → A: Chi tiết tại FR-016 đến FR-048. Existing API: robot status (WebSocket), auth, conversations, events, weekly analytics, emotion summary, music, quiz games, flashcards, stories, camera, admin families, WiFi. UI mock/placeholder (backend sau): export PDF/CSV, ghi chú phụ huynh, phát lại ghi âm, monthly emotion chart, room location, radio, video learning, new interactive games, QR code, system logs, push notifications, sleep schedule, time limits, age filter, child profiles persist, parent↔Bi chat. Local state only (frontend session): selected child profile.
- Q: Information architecture? → A: 5 sidebar tab chính (Trang chủ, Giám sát, Học tập, Nhật ký, Thêm) + Cài đặt (modal/overlay) + Cài đặt > Chế độ kỹ thuật (admin only sub-section). Xem FR-001 đến FR-007.
- Q: Sidebar bottom order? → A: (1) Robot status card, (2) Signed-in user card, (3) Nút Cài đặt, (4) Nút Đăng xuất. Trên mobile (<768px): bottom tab bar 5 tab. Xem FR-002, FR-005.
- Q: Elderly-friendly UX standards? → A: Font ≥16px body / ≥18px button / ≥20px section heading / ≥24px page heading; tap target ≥48px; contrast ≥4.5:1 WCAG AA; không icon-only button; tất cả state (loading/error/empty) có text mô tả. Xem FR-011 đến FR-014, FR-046.
- Q: Design balance (child-friendly vs parent-professional)? → A: "Công nghệ ấm áp" — professional blue-based palette (#2563eb), warm purple accent; không dùng toy colors hay childish fonts; tone thân thiện nhưng không trẻ con; phụ huynh lớn tuổi cảm thấy tin tưởng. Xem FR-015.
- Q: Hard boundaries? → A: Không sửa src/, firmware/, frontend/robot_display/, tests/, runtime/, logs/, .env. Không đổi API contract, không đổi auth/JWT, không đổi DB schema. Xem FR-049 đến FR-051 và Assumptions.
- Q: Chat với Bi placement? → A: Sub-section trong tab Học tập với badge "Sắp hỗ trợ". Xem FR-024.
- Q: SYSTEM_MAP.md update policy? → A: Cập nhật SAU KHI implementation hoàn thành. Mô tả "tab X hiển thị Y từ API Z (hiện có)" và "tab A có placeholder cho tính năng B (backend chưa implement)". Không claim incomplete backend features là done. Xem SC-008 và Assumptions.
