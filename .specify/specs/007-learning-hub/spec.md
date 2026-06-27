# Feature Specification: Learning Hub Redesign (tab Học tập)

> Created: 2026-06-28 · Feature dir: `.specify/specs/007-learning-hub/`
> Nguồn: phiên thiết kế 2026-06-27/28 — nghiên cứu Duolingo/Khan/IXL/Anki/SplashLearn + quyết định của user + ui-ux-pro-max + phần dùng-được của taste-skill.
> Module lớn nhất dự án (ngang phần robot) → làm tỉ mỉ cả giao diện lẫn nội dung/sư phạm.

## Summary

Thiết kế lại tab "Học tập" (LearningHubPage) theo hướng **subject-first**: mở tab thấy lưới **tất cả môn** (nhóm theo danh mục + tìm kiếm), bấm 1 môn vào **trang chi tiết môn** với nhiều **chế độ học/luyện** (Lộ trình kiểu Duolingo · Luyện theo bài · Luyện theo đề · HSG/Chuyển cấp hoặc Nâng cao), mỗi chế độ có **timer tùy chọn**. Bổ sung lớp **"gia sư thông minh"** biến app từ ngân hàng đề thành gia sư: **Sổ lỗi**, **Mastery theo chủ đề** (kiểu IXL SmartScore), **"Hỏi Bi vì sao sai"** (AI Socratic), **Robot đọc đề/trả lời bằng giọng** (TTS/STT). Toàn bộ phải **responsive hoàn hảo** từ điện thoại nhỏ tới PC màn rộng, **an toàn cho trẻ** (không social toàn cầu), giữ **bản sắc vui-nhiều-màu** Robot Bi.

Triển khai 2 lớp: **Lớp 1** dùng dữ liệu/engine đã có (làm đợt này, từng màn có review); **Lớp 2** cần backend mới (đợt sau).

## Clarifications

### Session 2026-06-27/28

- Q: Hiển thị "nhiều môn" thế nào? → A: **Subject-first** — màn đầu là lưới tất cả môn (nhóm danh mục + search); vào 1 môn mới chọn chế độ.
- Q: Trong 1 môn có gì? → A: **Lộ trình** (Duolingo) + **Luyện tập** (theo bài / theo đề / HSG-Chuyển cấp / Nâng cao) + **Thi**, mỗi chế độ chọn được **có/không giờ**.
- Q: HSG/Chuyển cấp cho môn nào? → A: chỉ môn Bộ GD đưa vào kỳ thi; môn ngoài → "Luyện tập nâng cao".
- Q: "Học" cho mọi môn nhưng backend chỉ có 3 môn? → A: dựng **FE-shell trước cho mọi môn** (3 môn nội dung thật, còn lại "Sắp có"), backend nội dung thêm sau.
- Q: Cấp 1 dùng thẻ hay dropdown? → A: **thẻ chế độ ở cấp 1**, dropdown chỉ cho cấp 2 (chọn đề/cấp/vòng HSG).
- Q: Bố cục desktop? → A: **rộng khi duyệt, hẹp (~640px) khi làm bài**; container duyệt căn giữa ≤1280px (không kéo căng ultra-wide, không co 480px).
- Q: Danh mục môn? → A: dùng sơ đồ đề xuất (Ngôn ngữ / Toán & KHTN / Xã hội / Năng khiếu / Kỹ năng & khác); user chỉnh map sau.
- Q: taste-skill áp tới đâu? → A: tab này là product UI cho trẻ → **không** áp luật minimalist/đơn-sắc/cấm-emoji; **giữ** emoji + màu vui; chỉ lấy nguyên tắc UI phổ quát (chống slop, shape lock, trạng thái đầy đủ, responsive, a11y).

### Session 2026-06-28 (clarify)

- Q: Map môn ↔ danh mục? → A: **Dùng sơ đồ đề xuất** (xem "Resolved Decisions" → Category map). 5 nhóm: Ngôn ngữ · Toán & KHTN · Xã hội · Năng khiếu · Kỹ năng & khác.
- Q: Môn nào có HSG/Chuyển cấp (còn lại Nâng cao)? → A: **Toán/Lý/Hóa/Sinh/Văn/Sử/Địa/GDCD/Anh/Tin** (Bộ GD). NGOẠI LỆ: **IELTS và TOEIC phải có chế độ "Thi thử mô phỏng đề thật"** (full-length, đúng cấu trúc + thời gian như đề thật, giống các web luyện thi online) để bé dễ làm quen.
- Q: Tên chế độ học kiểu Duolingo? → A: **"Lộ trình"**.

## User Scenarios

- **Trẻ** mở tab Học tập, thấy mọi môn theo nhóm, gõ tìm "Toán", bấm vào → chọn "Luyện theo bài", không tính giờ, làm từng câu, sai thì bấm "Hỏi Bi vì sao", nghe Bi đọc đề.
- **Trẻ** vào môn Tiếng Anh, thấy "Câu hay sai (12)", luyện lại đúng những câu mình từng sai.
- **Trẻ luyện thi** chọn môn Toán → "Luyện HSG" → chọn vòng tỉnh, đặt giờ 60 phút, làm như thi thật.
- **Phụ huynh** mở "Theo dõi học tập" thấy con yếu chủ đề "Thì quá khứ" (mã màu đỏ + chữ "Cần cố gắng").
- Trên **điện thoại nhỏ, tablet, laptop, PC màn rộng** — mọi màn đều vừa vặn, không cuộn ngang, không co cụm giữa, không kéo căng.

## User Stories (prioritized)

> **Lớp 1 (đợt này)** = US1–US10 · **Lớp 2 (đợt sau, cần BE)** = US11–US14.

### US1 — Lưới môn subject-first (P1) · HIGH
Trẻ/phụ huynh mở tab thấy **tất cả môn có nội dung** (từ danh sách môn backend), **nhóm theo danh mục**, có **ô tìm kiếm** lọc nhanh; lưới dùng hết chiều ngang (full-width, căn giữa ≤1280px). Môn rỗng tự ẩn.

### US2 — Trang chi tiết môn (P1) · HIGH
Bấm 1 môn → trang môn: header môn + tiến độ; **dải thẻ chế độ** (cấp 1); 2 thẻ nổi bật **"📕 Câu hay sai (n)"** + **"🎯 Chủ đề cần ôn"**; **mastery theo chủ đề** dạng accordion (gập mặc định). Desktop ≥1024 chia 2 cột; ≤1023 một cột.

### US3 — Luyện theo đề + cấu hình timer (P1) · HIGH
Làm full đề (tái dùng luồng exam hiện có), có **màn cấu hình**: chọn đề/cấp (dropdown cấp 2) + thời gian (Không giờ/15/30/45/60) → Bắt đầu. Chấm cuối, lưu phiên.

### US4 — Luyện theo bài (P1) · HIGH
Làm **câu hỏi đơn lẻ** từ ngân hàng câu hỏi của môn; **phản hồi + giải thích NGAY sau mỗi câu**; timer tùy chọn. Áp dụng mọi môn.

### US5 — Sổ lỗi (ôn câu sai) (P1) · HIGH
Gom câu trẻ từng trả lời sai (từ phiên làm đã lưu) → cho **luyện lại riêng**, nhóm theo môn/chủ đề. Đếm số câu sai hiển thị ở thẻ "Câu hay sai".

### US6 — Mastery theo chủ đề (P1) · HIGH
Mỗi chủ đề có **điểm thành thạo 0-100** + **mã màu kèm chữ** (<60 Cần cố gắng · 60-79 Khá · 80-89 Thạo · ≥90 Làm chủ). Bề mặt cho cả trẻ (trang môn) và phụ huynh.

### US7 — Hỏi Bi vì sao sai + Robot đọc/nghe (P1) · HIGH
Sau câu sai có nút **"🤖 Hỏi Bi vì sao"** → AI giải thích kiểu **Socratic** (gợi mở, không đưa đáp án thẳng), ngôn ngữ trẻ, **lọc SafetyFilter** trước khi tới trẻ. Có nút **🔊 Bi đọc đề** (TTS) và tùy chọn **trả lời bằng giọng** (STT) — tái dùng cơ chế TOEIC.

### US8 — HSG / Chuyển cấp / Nâng cao (P1) · MEDIUM
Môn **Bộ GD** (Toán/Lý/Hóa/Sinh/Văn/Sử/Địa/GDCD/Anh/Tin): có chế độ **Luyện HSG** + **Thi chuyển cấp** (dropdown chọn vòng/cấp). Môn ngoài danh mục: thay bằng **Luyện tập nâng cao**. **NGOẠI LỆ — IELTS và TOEIC**: có thêm chế độ **"Thi thử mô phỏng đề thật"** (full-length, đúng cấu trúc + thời gian như đề thật, giống web luyện thi online) để bé làm quen định dạng thi thật.

### US9 — Khung "Lộ trình" (shell) (P1) · MEDIUM
Mọi môn hiện chế độ **Lộ trình** (kiểu Duolingo). Nội dung thật cho en/math/science; môn khác hiển thị **"Sắp có"** (chờ backend nội dung lớp 2).

### US10 — Responsive hoàn hảo mọi màn (P1, xuyên suốt) · HIGH
Mọi màn của tab phải hiển thị tốt từ **phone nhỏ (≤360) → phone → tablet → laptop → PC màn rộng (≥1536)**: không cuộn ngang, không co cụm giữa, không kéo căng mép-tới-mép; nút ≥48px; chữ co giãn; làm bài cột hẹp ~640px.

### US11 — Gamification an toàn trẻ (P2)
Streak + **đóng băng/ngày nghỉ**; **mục tiêu hằng ngày** tùy chỉnh; **huy hiệu** cột mốc; XP. **Leaderboard CHỈ trong gia đình** (không toàn cầu/xã hội). Phần thưởng do phụ huynh kiểm soát.

### US12 — Ôn tập giãn cách + adaptive (P2)
Lịch **ôn tập giãn cách** (nhắc ôn câu cũ/yếu); **adaptive** ưu tiên ra câu thuộc chủ đề đang yếu.

### US13 — Báo cáo phụ huynh nâng cao (P2)
Tab "Theo dõi học tập" hiện **chủ đề mạnh/yếu mã màu + thời gian học + xu hướng**; **"Bi tóm tắt ngày học"** gửi phụ huynh.

### US14 — Nội dung Lộ trình Duolingo cho mọi môn (P2, cần soạn BE)
Bổ sung module bài học kiểu Duolingo cho các môn ngoài 3 môn hiện có.

## Functional Requirements

### Lớp 1 — Duyệt & điều hướng
- **FR-1**: Tab hiển thị lưới tất cả môn **có nội dung** (môn không có gì → ẩn), nhóm theo danh mục, kèm ô tìm kiếm lọc theo tên môn.
- **FR-2**: Mỗi thẻ môn hiển thị tên + biểu tượng + chỉ báo tiến độ/mastery của môn; bấm vào mở trang chi tiết môn.
- **FR-3**: Trang chi tiết môn hiển thị các thẻ chế độ phù hợp với môn (Lộ trình, Luyện theo bài, Luyện theo đề, HSG/Chuyển cấp **hoặc** Nâng cao) + thẻ "Câu hay sai" + "Chủ đề cần ôn" + mastery theo chủ đề (gập được).

### Lớp 1 — Học/Luyện/Thi
- **FR-4**: Mỗi chế độ luyện/thi có bước cấu hình: chọn nội dung (đề/cấp/vòng qua dropdown khi cần) + chọn **có/không giờ** (Không/15/30/45/60 phút) trước khi bắt đầu.
- **FR-5**: "Luyện theo đề" làm trọn đề, chấm khi nộp, lưu phiên (tái dùng luồng hiện có); tôn trọng logic chấm đề/TOEIC hiện tại.
- **FR-6**: "Luyện theo bài" làm từng câu, **chấm + giải thích ngay sau mỗi câu**; timer tùy chọn.
- **FR-7**: "Luyện HSG"/"Thi chuyển cấp" chỉ xuất hiện ở môn thuộc danh mục Bộ GD; môn ngoài hiển thị "Luyện tập nâng cao". **IELTS và TOEIC** có thêm chế độ **"Thi thử mô phỏng đề thật"** (đề full-length đúng cấu trúc + thời gian thật, có hẹn giờ mặc định theo định dạng thi).
- **FR-8**: "Lộ trình" hiển thị cho mọi môn; môn chưa có nội dung backend hiển thị trạng thái "Sắp có" rõ ràng (không màn trống mơ hồ).

### Lớp 1 — Gia sư thông minh
- **FR-9**: Sổ lỗi gom các câu trẻ từng trả lời sai, cho luyện lại, nhóm theo môn/chủ đề; số lượng hiển thị trên thẻ.
- **FR-10**: Mastery theo chủ đề hiển thị điểm 0-100 + nhãn chữ + mã màu; **màu không phải tín hiệu duy nhất** (luôn kèm chữ).
- **FR-11**: Sau câu sai, trẻ có thể yêu cầu giải thích từ AI; lời giải mang tính gợi mở, đúng ngôn ngữ trẻ, **đi qua bộ lọc an toàn** trước khi hiển thị.
- **FR-12**: Có thể cho robot **đọc đề bằng giọng**; tùy chọn **trả lời bằng giọng** (nơi phù hợp).

### Lớp 1 — Giao diện & Responsive (bắt buộc)
- **FR-13**: Màn duyệt dùng lưới co giãn, container căn giữa giới hạn ~1280px; màn đang làm bài dùng cột hẹp ~640px căn giữa.
- **FR-14**: Bố cục đúng theo dải breakpoint chuẩn (≤360 / phone / tablet 768-1023 / laptop 1024-1279 / ≥1280 / ≥1536); tablet trang môn 1 cột, ≥1024 chia 2 cột.
- **FR-15**: Mọi vùng chạm ≥48px; tương phản đạt WCAG AA; có focus ring; chữ co giãn (mobile body ≥16px); không cuộn ngang ở mọi màn.
- **FR-16**: Giữ emoji + bảng màu vui (bản sắc trẻ); một thang bo góc nhất quán; có đủ trạng thái loading (skeleton)/empty/error; chuyển động có lý do + tôn trọng `prefers-reduced-motion`.

### Ràng buộc chung
- **FR-C1**: Không hồi quy Protected Fixes (cô lập đa gia đình, chấm đề/TOEIC, SafetyFilter post-LLM/pre-TTS, chuỗi 5 LLM, đường dẫn/lược đồ DB).
- **FR-C2**: Mọi truy vấn nội dung học scope theo gia đình hiện hành.
- **FR-C3**: Sau thay đổi code chạy `python tests/run_tests.py`; thêm test cho năng lực mới (sổ lỗi, mastery, gating chế độ, responsive sanity).
- **FR-C4**: Child-safety: không có bảng xếp hạng/social toàn cầu cho trẻ; mọi văn bản AI tới trẻ qua SafetyFilter.

### Lớp 2 (cần BE — ngoài phạm vi build đợt 1, ghi để theo dõi)
- **FR-L2-1**: Ôn tập giãn cách + adaptive theo điểm yếu.
- **FR-L2-2**: Nội dung Lộ trình Duolingo cho mọi môn.
- **FR-L2-3**: Gamification đầy đủ (đóng băng streak, huy hiệu, family leaderboard) + phần thưởng phụ huynh kiểm soát.
- **FR-L2-4**: Báo cáo phụ huynh nâng cao + "Bi tóm tắt ngày học".

## Key Entities / Data

- **Subject (môn)**: từ danh sách môn backend — khóa, nhãn, biểu tượng, số đề; gắn **Category (danh mục)** (suy ra ở FE, có thể chuyển BE sau).
- **Mode (chế độ)**: Lộ trình / Luyện theo bài / Luyện theo đề / HSG / Chuyển cấp / Nâng cao — khả dụng tùy môn (theo track có nội dung + danh mục Bộ GD).
- **TopicMastery (mastery theo chủ đề)**: điểm 0-100 + nhãn + màu, suy từ lịch sử trả lời.
- **ErrorItem (mục sổ lỗi)**: câu từng sai (từ phiên làm đã lưu) gắn môn/chủ đề.
- **SessionConfig (cấu hình phiên)**: chế độ + nội dung + có/không giờ + thời lượng.
- (Lớp 2) **ReviewSchedule (lịch ôn giãn cách)**, **DailyGoal/Badge/Streak**, **FamilyLeaderboard**.

## Success Criteria

- **SC-1**: Tab mở ra hiển thị **toàn bộ môn có nội dung** theo nhóm; tìm kiếm lọc đúng trong <1 giây cảm nhận.
- **SC-2**: 100% màn không cuộn ngang và không co cụm giữa khi đo ở **320/360/390/414/600/768/1024/1280/1440/1920**.
- **SC-3**: Trẻ vào 1 môn chọn được chế độ + đặt giờ và bắt đầu trong ≤3 thao tác.
- **SC-4**: Mastery theo chủ đề luôn hiển thị **màu + chữ** (không màu đơn lẻ); phụ huynh nhận ra chủ đề yếu mà không cần hướng dẫn.
- **SC-5**: Trẻ ôn lại được câu từng sai từ Sổ lỗi; số đếm khớp lịch sử.
- **SC-6**: Lời giải "Hỏi Bi" tới trẻ đều đã qua SafetyFilter; không có bảng xếp hạng toàn cầu nào lộ ra cho trẻ.
- **SC-7**: `python tests/run_tests.py` PASS sau mỗi màn; không hồi quy Protected Fixes.
- **SC-8**: Mọi chức năng truy cập được trên desktop đều truy cập được trên mobile (parity).

## Edge Cases & Safety

- Môn chưa có nội dung chế độ nào → ẩn khỏi lưới (FR-1).
- Môn có đề nhưng chưa có Lộ trình → "Học" hiện "Sắp có", các chế độ luyện đề vẫn dùng được.
- Sổ lỗi rỗng → empty state khích lệ ("Chưa có câu sai nào — giỏi quá!").
- Trẻ chưa đăng nhập đủ quyền / tài khoản con bị giới hạn → tôn trọng phân quyền 006 (tab học vẫn thuộc nhóm con thấy).
- AI lỗi/timeout khi "Hỏi Bi" → thông báo nhẹ, fallback hiển thị giải thích tĩnh của câu (nếu có).
- Robot/loa không sẵn → nút 🔊 ẩn hoặc báo nhẹ, không chặn làm bài.
- Mất mạng giữa phiên → giữ tiến độ tạm, không mất sạch.
- TUYỆT ĐỐI không social/leaderboard toàn cầu cho trẻ; không nới SafetyFilter.

## Out of Scope (đợt 1)

- Engine **ôn tập giãn cách / adaptive** đầy đủ (lớp 2).
- **Soạn nội dung Lộ trình Duolingo** cho 22 môn ở backend (lớp 2).
- Gamification đầy đủ (đóng băng streak, huy hiệu, family leaderboard) (lớp 2).
- Báo cáo phụ huynh nâng cao + "Bi tóm tắt ngày học" (lớp 2).
- Thay đổi luồng chấm đề/TOEIC hiện có (chỉ tái dùng).

## Resolved Decisions (2026-06-28)

- Subject-first; lưới môn nhóm danh mục + search; trang môn dùng thẻ chế độ (cấp 1) + dropdown (cấp 2).
- Mỗi môn: Lộ trình + Luyện theo bài + Luyện theo đề + HSG/Chuyển cấp (Bộ GD) hoặc Nâng cao; timer tùy chọn.
- Lớp gia sư (Sổ lỗi, Mastery theo chủ đề kiểu SmartScore, Hỏi Bi Socratic, Robot đọc/nghe) đưa vào ngay vì dữ liệu/engine có sẵn.
- Gamification + spaced/adaptive + parent report nâng cao = lớp 2.
- Responsive: duyệt rộng (≤1280 căn giữa) / làm bài hẹp (640); breakpoints sm/md/lg/xl/2xl; tablet 1 cột, ≥1024 2 cột.
- Giữ emoji + màu vui (bản sắc trẻ); taste-skill chỉ áp nguyên tắc phổ quát.
- Leaderboard chỉ trong gia đình; không social toàn cầu.
- Tên chế độ Duolingo = **"Lộ trình"**.
- **Category map (đã chốt)**: Ngôn ngữ (Anh/Trung/Nhật/Hàn/IELTS/TOEIC L&R/TOEIC S&W) · Toán & KHTN (Toán/Lý/Hóa/Sinh/Khoa học/Tin/Lập trình) · Xã hội (Văn/Tiếng Việt/Sử/Địa/GDCD) · Năng khiếu (Nhạc/Mỹ thuật) · Kỹ năng & khác (Kinh tế/Sức khỏe/Kỹ năng sống/Logic).
- **Môn có HSG + Chuyển cấp (đã chốt)**: Toán/Lý/Hóa/Sinh/Văn/Sử/Địa/GDCD/Anh/Tin; còn lại "Nâng cao".
- **IELTS & TOEIC**: thêm chế độ "Thi thử mô phỏng đề thật" (full-length, đúng cấu trúc + thời gian).

## Assumptions

- Danh mục môn map ở FE theo sơ đồ ĐÃ CHỐT (xem Resolved Decisions → Category map); vẫn dễ sửa sau.
- Danh sách môn "có nội dung" lấy từ danh sách môn backend hiện có (môn có đề mới hiện).
- IELTS/TOEIC "đề thật": dùng cấu trúc + thời gian chuẩn của định dạng thi (cấu hình ở FE, dựa nội dung đề có sẵn); TOEIC S&W tái dùng luồng chấm STT hiện có.
- "Luyện theo bài" và "Luyện theo đề" dùng chung ngân hàng câu hỏi hiện có; khác nhau ở cách trình bày (từng câu vs trọn đề) + thời điểm chấm.
- Danh sách môn Bộ GD (có HSG/chuyển cấp) là một danh sách cấu hình ở FE, mặc định theo đề xuất, chỉnh được.
- Tái dùng TTS/STT của luồng TOEIC cho "đọc đề / trả lời giọng".
