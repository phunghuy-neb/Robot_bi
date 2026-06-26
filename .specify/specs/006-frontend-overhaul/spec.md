# Feature Specification: Frontend Overhaul — Parent App + Admin

> Created: 2026-06-27 · Feature dir: `.specify/specs/006-frontend-overhaul/`
> Scope source: audit session 2026-06-26/27 (21 issues A1–E4) + user decisions Q1–Q5 + 3 new features (WiFi, family accounts, role-based access).

## Summary

Đại tu giao diện Parent App và Admin của Robot Bi: dọn nợ kỹ thuật FE (bug hiển thị, vi phạm design system / accessibility), tổ chức lại cấu trúc tab cho rõ vai trò, thống nhất giao diện Admin theo design token, và bổ sung 3 năng lực mới — khai báo WiFi cho robot, quản lý tài khoản thành viên gia đình, và phân quyền truy cập theo vai trò (chủ gia đình / bố mẹ ông bà / con). Nguyên tắc xuyên suốt: **desktop và mobile đủ chức năng như nhau, không cắt bớt**; không được làm hồi quy bất kỳ Protected Fix nào trong PROJECT.md.

Đây là feature lớn, nhiều workstream, triển khai nhiều phiên theo thứ tự rủi ro tăng dần.

## Clarifications

### Session 2026-06-27

- Q: Con đăng nhập bằng cách nào? → A: Màn đăng nhập hiện danh sách hồ sơ trẻ của gia đình → bấm chọn → nhập PIN (luồng login riêng cho con, không nhập username).
- Q: Ai trở thành owner và tạo thành viên ra sao? → A: Ai cũng tự đăng ký được; sau đó tự tạo gia đình mới (thành owner) HOẶC được owner của một gia đình thêm vào; owner chọn vai trò cho người được thêm. Tài khoản con do owner tạo (con không tự đăng ký).
- Q: Quan hệ tài khoản con ↔ hồ sơ trẻ? → A: Chọn từ hồ sơ trẻ đã có; 1 hồ sơ ↔ 1 tài khoản con.
- Q: Con thấy gì ở khu Cài đặt? → A: Con luôn vào được Cài đặt để đổi avatar/tên của mình và cấu hình WiFi; các mục còn lại (thông báo, giờ ngủ, nội dung & an toàn, kết nối thiết bị, thành viên) ẩn/mở tùy owner cấu hình.

## User Scenarios

- **Phụ huynh (chủ gia đình)** mở Parent App trên điện thoại, thấy số liệu trang chủ đúng nhãn, bấm được mọi thẻ, chuyển tab rõ ràng giữa "Theo dõi học tập" (giám sát) và "Học tập" (nội dung học của bé).
- **Phụ huynh** vào Cài đặt khai báo WiFi để robot kết nối mạng nhà, và tạo tài khoản cho ông bà (xem toàn bộ) lẫn cho con (giới hạn).
- **Con** đăng nhập bằng mã PIN, thấy giao diện rút gọn — vào được các tab học/giải trí nhưng không thấy mục Cài đặt & An toàn.
- **Quản trị viên hệ thống** (is_admin) dùng khu Admin có giao diện nhất quán, dễ đọc trên cả desktop và mobile.

## User Stories (prioritized)

### US1 — Sửa bug hiển thị FE (P1) · Priority: HIGH
Là phụ huynh, tôi muốn các con số và nút trên app phản ánh đúng thực tế và bấm được, để tin tưởng dữ liệu app đưa ra.
- Nhãn metric trang chủ đúng với số liệu thật (không còn chữ cứng sai).
- Mọi thẻ trông-bấm-được đều thực sự hành động.
- Khu vực dữ liệu rỗng hiện trạng thái "trống" rõ ràng, không quay vòng "đang tải" mãi.
- Ô chọn ngày hiển thị theo định dạng Việt Nam.

### US2 — Tuân thủ design system & accessibility (P2) · Priority: HIGH
Là người dùng (đặc biệt trên điện thoại), tôi muốn nút đủ lớn để chạm và bố cục không vỡ trên màn lớn.
- Mọi vùng chạm đạt tối thiểu kích thước chạm chuẩn (token `--tap-min` = 48px; ngoại lệ phải ≥44px và có lý do ghi rõ).
- Khu camera không chiếm chiều cao quá mức trên desktop.
- Lưới thẻ ở trang "Thêm" không tạo thẻ khổng lồ trên desktop.
- `docs/DESIGN_SYSTEM.md` mô tả khớp với CSS thực tế.

### US3 — Cấu trúc tab & theo dõi học tập (P3) · Priority: HIGH
Là phụ huynh, tôi muốn phân biệt rõ "nơi bé học" và "nơi tôi theo dõi việc học".
- Tab học đa môn (kiểu Duolingo) mang nhãn "Học tập".
- Tab giám sát học tập mang nhãn "Theo dõi học tập" và hiển thị tổng quan tiến độ 3 môn (Tiếng Anh / Toán / Khoa học).
- Sidebar (desktop) và bottom-nav (mobile) đồng bộ nhãn, vẫn 6 tab.

### US4 — Monitor page gọn gàng (P4) · Priority: MEDIUM
Là phụ huynh, tôi muốn trang giám sát dễ đọc, không lặp nội dung.
- Các khối trong trang giám sát có thể gập/mở.
- Không lặp lại "báo cáo tuần" đã có ở trang chủ.
- Khu camera cao hợp lý.

### US5 — Giao diện Admin nhất quán (P5) · Priority: MEDIUM
Là quản trị viên, tôi muốn 9 trang admin trông đồng nhất và đọc tốt trên mọi kích thước màn hình.
- Bo góc, màu, khoảng cách theo design token chung.
- Một kiểu công tắc bật/tắt thống nhất (không lẫn checkbox và emoji).
- Admin vẫn là giao diện riêng, tách khỏi Parent App.

### US6 — Khai báo WiFi cho robot (P6) · Priority: MEDIUM
Là phụ huynh, tôi muốn nhập WiFi nhà để robot kết nối mà không cần thao tác kỹ thuật.
- Trong Cài đặt có ô nhập tên WiFi + mật khẩu và nút gửi xuống robot.
- Hiển thị trạng thái kết nối hiện tại của robot.

### US7 — Tài khoản gia đình & phân quyền (P7) · Priority: HIGH (làm cuối, lớn nhất)
Là chủ gia đình, tôi muốn tạo tài khoản cho người thân và cho con, kiểm soát con được xem gì.
- Chủ gia đình tạo/xóa tài khoản cho bố mẹ ông bà (quyền xem đầy đủ) và cho con (quyền giới hạn).
- Con đăng nhập bằng PIN, mỗi con gắn với một hồ sơ trẻ.
- Mặc định con bị ẩn mục "Cài đặt & An toàn"; các phần khác vẫn xem được; chủ gia đình tinh chỉnh thêm.
- Giới hạn được thực thi ở phía máy chủ (không chỉ ẩn trên giao diện).

### Cross-cutting — Parity desktop/mobile (P8) · áp dụng cho mọi US
Mọi màn sau khi sửa phải đủ chức năng và nội dung như nhau trên desktop và mobile.

## Functional Requirements

### Nhóm P1 — Bug hiển thị
- **FR-P1-1**: Trang chủ phải hiển thị nhãn metric đúng ngữ nghĩa số liệu (ví dụ "Phút học", "Nhiệm vụ"), không dùng chuỗi cứng sai.
- **FR-P1-2**: Mọi phần tử giao diện mang dáng vẻ bấm-được phải có hành động thật; thẻ shortcut trang "Thêm" phải cuộn tới đúng khu vực tương ứng.
- **FR-P1-3**: Khi không có dữ liệu cảm xúc, khu biểu đồ phải hiển thị trạng thái "trống", không kẹt ở "đang tải".
- **FR-P1-4**: Ô chọn ngày hiển thị theo locale Việt Nam.

### Nhóm P2 — Design system / accessibility
- **FR-P2-1**: Tất cả vùng chạm tương tác đạt tối thiểu kích thước chạm chuẩn của hệ thống (48px), trừ ngoại lệ ≥44px có ghi chú lý do.
- **FR-P2-2**: Khu camera bị giới hạn chiều cao tối đa hợp lý trên màn hình lớn.
- **FR-P2-3**: Lưới thẻ trang "Thêm" responsive, không sinh thẻ quá khổ trên desktop.
- **FR-P2-4**: `docs/DESIGN_SYSTEM.md` được cập nhật để khớp giá trị CSS thực tế.

### Nhóm P3 — Cấu trúc tab
- **FR-P3-1**: Tab học đa môn mang nhãn "Học tập".
- **FR-P3-2**: Tab giám sát học tập mang nhãn "Theo dõi học tập".
- **FR-P3-3**: Tab "Theo dõi học tập" hiển thị tổng quan tiến độ 3 môn (Tiếng Anh / Toán / Khoa học) từ dữ liệu học tập sẵn có.
- **FR-P3-4**: Nhãn tab đồng bộ giữa điều hướng desktop và mobile; tổng số tab giữ nguyên 6.

### Nhóm P4 — Monitor UX
- **FR-P4-1**: Mỗi khối nội dung trong trang giám sát có thể gập/mở.
- **FR-P4-2**: Trang giám sát không lặp lại nội dung "báo cáo tuần" đã có ở trang chủ.
- **FR-P4-3**: Khu camera trong trang giám sát có chiều cao hợp lý trên mọi màn hình.

### Nhóm P5 — Admin polish
- **FR-P5-1**: 9 trang admin dùng chung design token (bo góc, màu, khoảng cách) thay vì giá trị rời rạc.
- **FR-P5-2**: Công tắc bật/tắt trong admin theo một kiểu thống nhất.
- **FR-P5-3**: Admin giữ là giao diện riêng, không trộn vào Parent App.
- **FR-P5-4**: Các trang admin đọc và thao tác được trên màn hình hẹp (mobile).

### Nhóm P6 — WiFi robot
- **FR-P6-1**: Trong Cài đặt có biểu mẫu nhập tên WiFi và mật khẩu để gửi cấu hình xuống robot.
- **FR-P6-2**: Giao diện hiển thị trạng thái kết nối hiện tại của robot.
- **FR-P6-3**: Tận dụng dịch vụ WiFi backend hiện có; không thay đổi hợp đồng backend.

### Nhóm P7 — Gia đình & phân quyền
- **FR-P7-1**: Hệ thống phân biệt 3 vai trò trong một gia đình: chủ gia đình (owner), thành viên người lớn (parent), và con (child); tách biệt với vai trò quản trị hệ thống (is_admin) hiện có.
- **FR-P7-2**: Người dùng tự đăng ký được tài khoản. Một tài khoản có thể (a) tạo gia đình mới và trở thành owner, hoặc (b) được owner của một gia đình hiện có thêm vào.
- **FR-P7-2b**: Owner thêm một tài khoản người lớn (đã đăng ký) vào gia đình mình bằng định danh và **chọn vai trò** cho người được thêm (parent); owner cũng có thể đổi vai trò hoặc gỡ thành viên.
- **FR-P7-2c**: Tài khoản con do owner tạo từ một hồ sơ trẻ có sẵn + đặt PIN; con KHÔNG tự đăng ký. Quan hệ 1 hồ sơ trẻ ↔ 1 tài khoản con.
- **FR-P7-3**: Con đăng nhập bằng cách chọn hồ sơ trẻ của gia đình trên màn đăng nhập rồi nhập PIN (không nhập username). Danh sách hồ sơ ở màn login phải được giới hạn theo gia đình (không liệt kê toàn cục).
- **FR-P7-4**: Vai trò owner và parent xem được toàn bộ chức năng dành cho phụ huynh.
- **FR-P7-5**: Vai trò con luôn truy cập được mục Cài đặt ở mức tối thiểu: đổi avatar/tên của chính mình và cấu hình WiFi. Các mục Cài đặt còn lại (thông báo, giờ ngủ, nội dung & an toàn, kết nối thiết bị, quản lý thành viên) mặc định ẩn với con và do owner bật/tắt.
- **FR-P7-6**: Chủ gia đình có thể bật/tắt từng nhóm quyền của con (giám sát, nhật ký, và các mục Cài đặt ở FR-P7-5) ngoài mặc định.
- **FR-P7-7**: Giới hạn quyền phải được thực thi ở phía máy chủ; gọi trực tiếp API mà không đủ quyền phải bị từ chối.
- **FR-P7-8**: Mọi dữ liệu thành viên/quyền được giới hạn theo gia đình; tài khoản gia đình này không thấy/sửa được gia đình khác. Chỉ owner mới quản lý thành viên và quyền của gia đình mình.
- **FR-P7-9**: Tài khoản hiện có được gán vai trò mặc định mà không làm gián đoạn đăng nhập đang dùng.

### Ràng buộc chung (bắt buộc)
- **FR-C1**: Không làm hồi quy bất kỳ Protected Fix nào trong PROJECT.md (JWT access/refresh + rotation, rate-limit đăng nhập, cô lập đa gia đình, RAG threshold/scope, audio mom-talk/streaming, safety filter post-LLM/pre-TTS, chuỗi 5 nhà cung cấp LLM, đường dẫn/lược đồ DB của tasks/conversations/turns).
- **FR-C2**: Sau khi thay đổi code phải chạy `python tests/run_tests.py`; bổ sung test cho năng lực mới (đặc biệt phân quyền và cô lập gia đình).
- **FR-C3**: Mọi màn được sửa phải giữ tương đương chức năng giữa desktop và mobile.

## Key Entities / Data

- **User (tài khoản)**: mở rộng thêm *vai trò gia đình* (owner / parent / child) và *liên kết tới hồ sơ trẻ* (chỉ cho tài khoản con). Vai trò được owner gán khi thêm thành viên người lớn; con luôn role=child. Vai trò quản trị hệ thống (is_admin) vẫn tách biệt.
- **FamilyPermissions (quyền theo gia đình)**: cấu hình per-gia-đình quy định con được truy cập phần nào. Luôn cho phép: đổi avatar/tên của con + cấu hình WiFi. Owner bật/tắt: giám sát, nhật ký, và từng mục Cài đặt còn lại (thông báo, giờ ngủ, nội dung & an toàn, kết nối thiết bị, thành viên). Mặc định các mục này tắt với con.
- **ChildProfile (hồ sơ trẻ)**: thực thể danh tính học tập sẵn có; mỗi tài khoản con tham chiếu đúng một hồ sơ trẻ (1↔1).
- **WiFiCredential (thông tin WiFi)**: dữ liệu tạm (tên mạng + mật khẩu) người dùng nhập để chuyển xuống robot; không lưu trữ lâu dài trên giao diện.

## Success Criteria

- **SC-1**: 100% nhãn/số liệu hiển thị ở trang chủ và nhật ký khớp dữ liệu thật khi kiểm thử với dữ liệu mẫu.
- **SC-2**: 100% phần tử tương tác trên màn cảm ứng đạt kích thước chạm chuẩn (kiểm bằng đo trên giao diện).
- **SC-3**: Người dùng phân biệt được hai tab học/giám sát qua nhãn mà không cần hướng dẫn.
- **SC-4**: Mọi chức năng truy cập được trên desktop đều truy cập được trên mobile (không màn nào bị cắt nội dung).
- **SC-5**: Chủ gia đình tạo được tài khoản con và đăng nhập thử thành công bằng PIN trong dưới 2 phút.
- **SC-6**: Tài khoản con không thể truy cập mục Cài đặt & An toàn, kể cả khi gọi thẳng API (kiểm bằng test phía máy chủ).
- **SC-7**: Toàn bộ bộ kiểm thử `python tests/run_tests.py` đạt PASS sau mỗi nhóm thay đổi, bao gồm test mới cho phân quyền và cô lập gia đình.
- **SC-8**: Không có Protected Fix nào bị hồi quy (đối chiếu danh sách PROJECT.md).

## Edge Cases & Safety

- Gia đình chưa cấu hình quyền con → áp mặc định an toàn (ẩn Cài đặt & An toàn).
- Con bị xóa hồ sơ/tài khoản trong khi đang đăng nhập → phiên con phải mất hiệu lực hợp lý.
- Chủ gia đình tự hạ quyền/tự xóa chính mình → phải bị chặn (tránh gia đình không còn owner).
- Owner thêm một tài khoản đã thuộc gia đình khác → phải xử lý rõ (chặn hoặc yêu cầu rời gia đình cũ), không để một tài khoản ở hai gia đình.
- Màn login con liệt kê hồ sơ → phải giới hạn theo gia đình (qua mã/định danh gia đình trên thiết bị), không phơi hồ sơ trẻ toàn cục.
- PIN của con yếu/trùng → phải có ràng buộc tối thiểu; không lưu PIN dạng thô.
- Mất kết nối khi gửi WiFi xuống robot → thông báo lỗi rõ, không treo giao diện.
- Dữ liệu rỗng ở mọi khu vực → hiện trạng thái "trống", không kẹt "đang tải".
- An toàn trẻ: không nới lỏng safety filter, không lộ chức năng giám sát/điều khiển cho tài khoản con khi chưa được cấp quyền.

## Out of Scope

- Dashboard tùy chỉnh (bật/tắt thẻ), mục tiêu học tập do phụ huynh đặt, push notification PWA, báo cáo tuần qua email — vẫn nằm ở backlog, không thuộc đợt này.
- Hoàn thiện toàn bộ các nút "save" stub còn lại ngoài phạm vi WiFi/role (chỉ xử lý khi đụng tới).
- Video call SDP thật, firmware robot, phần cứng.
- Thay đổi chuỗi nhà cung cấp LLM, RAG, audio, safety logic.

## Resolved Decisions (2026-06-27)

- **Mô hình tài khoản con**: con là tài khoản đăng nhập riêng theo vai trò child, dùng PIN, liên kết 1↔1 tới một hồ sơ trẻ; do owner tạo. **Đăng nhập con = chọn hồ sơ trên màn login + nhập PIN** (clarify 2026-06-27).
- **Đăng ký & gia đình**: tự đăng ký mở; tài khoản tự tạo family mới (→ owner) hoặc được owner thêm vào và owner gán vai trò (clarify 2026-06-27).
- **Giới hạn mặc định của con**: con luôn vào Cài đặt để đổi avatar/tên + cấu hình WiFi; các mục Cài đặt khác + giám sát + nhật ký do owner bật/tắt (clarify 2026-06-27).
- **Admin tách riêng**: giữ là giao diện riêng (đã chốt).
- **Parity**: desktop = mobile, không cắt nội dung (user nhấn mạnh).
- **Thứ tự triển khai**: P1 → P2 → P3 → (P4 ∥ P5 ∥ P6) → P7; P8 kiểm xen kẽ; P7 cần BE trước rồi FE.

## Assumptions

- Tài khoản con vẫn lưu/băm PIN và áp rate-limit như tài khoản thường (tái dùng cơ chế hash + rate-limit hiện có); khác biệt chỉ ở giao diện đăng nhập (chọn hồ sơ thay vì gõ username).
- Màn login con xác định gia đình qua một mã/định danh gia đình nhập hoặc ghi nhớ trên thiết bị (chi tiết chốt ở `/speckit-tasks`/plan), không liệt kê hồ sơ trẻ toàn cục.
- Tổng quan tiến độ 3 môn lấy từ dữ liệu học tập đã có; nếu môn nào chưa có dữ liệu thì hiển thị trạng thái trống.
- "Theo dõi học tập" là đổi tên + bổ sung trên trang giám sát học tập hiện có, không tạo tab thứ 7.
- Kích thước chạm mục tiêu là 48px theo token hiện có; ngoại lệ chỉ khi có lý do thiết kế và ≥44px.
