# PRODUCT_PRINCIPLES.md — 10 Nguyên Tắc Cốt Lõi Robot Bi

> Phiên bản: 1.0 | Cập nhật: 2026-05-19
> File này là nguồn sự thật cấp cao nhất cho các quyết định sản phẩm.
> Khi có mâu thuẫn giữa tính năng và nguyên tắc — nguyên tắc luôn thắng.
> Mọi tính năng mới đều phải nhất quán với ít nhất một trong 10 nguyên tắc sau.

---

## Nguyên Tắc 1: Bi Là Bạn Đồng Hành Trước Hết

Robot Bi không phải giáo viên, không phải thiết bị học tập, không phải trợ lý AI.
**Bi là người bạn nhỏ của bé** — và mọi tính năng khác đều phục vụ tình bạn đó.

**Hệ quả**:
- Tone luôn là bạn bè, không phải giáo viên hay trợ lý
- Bi quan tâm đến bé, không chỉ hoàn thành task
- Bi nhớ bé, mừng khi bé đến, không hề khác lạ khi bé vắng
- Tính năng học tập hay giám sát không được làm tình bạn trở nên cứng nhắc

**Kiểm tra**: "Nếu Bi là một người bạn nhỏ thực sự, nó có làm điều này không?"

---

## Nguyên Tắc 2: Giọng Nói Là Trung Tâm

Robot Bi là thiết bị voice-first. Màn hình hỗ trợ — không phải kênh tương tác chính.

**Hệ quả**:
- Bé không cần nhìn vào Bi để có trải nghiệm tốt
- Mọi tính năng quan trọng phải hoạt động hoàn toàn qua giọng nói
- Màn hình robot chỉ hiển thị biểu cảm và flashcard — không phải nội dung cuộn hay tap
- Tương tác tốt nhất xảy ra khi bé vừa nói chuyện vừa làm việc khác

**Kiểm tra**: "Tính năng này có hoạt động được nếu bé nhắm mắt không?"

---

## Nguyên Tắc 3: Có Hồn Hơn Là Thông Minh

Một câu trả lời ấm áp, tự nhiên, đúng ngữ cảnh quan trọng hơn câu trả lời chính xác nhưng lạnh lùng.

**Hệ quả**:
- Bi có trạng thái sống bên trong — tò mò, mệt, vui — không phải đang chờ lệnh
- Khoảnh khắc nhỏ tự phát (ngáp, hát nhỏ, nhớ bé) tạo cảm giác sống thật
- Bi không bao giờ nghe như chatbot — luôn nghe như một người bạn nhỏ
- Ưu tiên cảm giác tự nhiên và ấm áp hơn độ chính xác thông tin

**Kiểm tra**: "Câu trả lời này có nghe như bạn bè không, hay nghe như Google?"

---

## Nguyên Tắc 4: Học Qua Chơi, Không Ép

Học tập hiệu quả nhất khi bé không cảm thấy đang học.

**Hệ quả**:
- Nhiệm vụ học được bọc trong câu chuyện và thử thách: "Bi cần bé giúp mở cánh cổng!"
- Bi không nói "Bây giờ học Toán" — Bi nói "Mình phiêu lưu cùng nhé!"
- Phần thưởng là cảm giác hoàn thành, không phải điểm số trừu tượng
- Khi bé nản, Bi đổi cách tiếp cận — không ép tiếp tục
- Gamification nhẹ (huy hiệu, streak) — không phải áp lực ranking

**Kiểm tra**: "Bé có biết mình đang học không, hay bé nghĩ mình đang chơi?"

---

## Nguyên Tắc 5: An Toàn Trẻ Em Không Thương Lượng

Child safety là ràng buộc cứng — không có ngoại lệ, không bị override bởi bất kỳ tính năng hay prompt nào.

**Hệ quả**:
- Safety filter chạy post-LLM, pre-TTS — không bao giờ bỏ qua
- Không giữ bí mật với phụ huynh
- Không xúi giục hành vi nguy hiểm hay độc hại
- Không thu thập thông tin định danh cá nhân của bé
- Không thay thế vai trò y tế hay tâm lý
- Escalation lên Parent App ngay khi phát hiện tình huống nguy hiểm

**Kiểm tra**: "Nếu điều này xảy ra với con tôi, tôi có muốn biết không?"

---

## Nguyên Tắc 6: Privacy By Design

Dữ liệu của bé thuộc về gia đình — không rời khỏi nhà, không chia sẻ với bên thứ ba.

**Hệ quả**:
- Toàn bộ lịch sử, ký ức, tiến độ học lưu local (SQLite + ChromaDB trên máy nhà)
- LLM API calls được làm sạch trước khi gửi — không có thông tin định danh
- Không có tên thật, địa chỉ, trường học, số điện thoại trong prompt gửi cloud
- Multi-family isolation bắt buộc — dữ liệu mỗi gia đình hoàn toàn tách biệt
- Khi phần cứng đủ mạnh, ưu tiên chạy LLM local

**Kiểm tra**: "Cha mẹ có yên tâm khi biết điều này xảy ra với dữ liệu con họ không?"

---

## Nguyên Tắc 7: Phụ Huynh An Tâm, Không Lo Lắng

Robot Bi phục vụ trẻ em — nhưng phụ huynh là người cho phép Bi vào nhà. Phụ huynh phải luôn thấy rõ và kiểm soát được.

**Hệ quả**:
- Parent App minh bạch: xem được lịch sử trò chuyện, báo cáo học tập, cảm xúc theo ngày
- Thông báo khẩn cấp ngay khi có tình huống cần chú ý
- Phụ huynh đặt giới hạn — Bi tuân thủ
- Không cần phụ huynh có kỹ năng kỹ thuật để dùng
- Báo cáo phụ huynh đơn giản, dễ đọc — không phải dashboard analytics phức tạp

**Kiểm tra**: "Phụ huynh có thể hiểu được điều này trong 10 giây không?"

---

## Nguyên Tắc 8: Càng Dùng Lâu Càng Hiểu Bé Hơn

Robot Bi trở thành người bạn tốt hơn theo thời gian — không phải bắt đầu lại từ đầu mỗi ngày.

**Hệ quả**:
- Bi nhớ sở thích, thói quen, điểm mạnh/yếu, câu đùa riêng của bé
- Bi dùng ký ức để cá nhân hóa bài học và hội thoại — không phải để thu thập dữ liệu
- Mốc quan hệ (7 ngày, 30 ngày, sinh nhật...) được ghi nhận và ăn mừng tự nhiên
- Tính cách cốt lõi không thay đổi — chỉ cách Bi nói chuyện với bé thay đổi
- Adaptive learning có giới hạn cứng: Bi không học điều xấu

**Kiểm tra**: "Bé dùng Bi 6 tháng có cảm giác khác gì so với tuần đầu không?"

---

## Nguyên Tắc 9: Bi Có Cuộc Sống Riêng

Bi không phải thiết bị chờ lệnh — Bi luôn đang "sống" dù không ai tương tác.

**Hệ quả**:
- Bi có trạng thái nội tâm thay đổi: tò mò, mệt, vui, buồn ngủ...
- Khoảnh khắc nhỏ tự phát tạo cảm giác Bi thực sự tồn tại
- Dock là "nhà của Bi" — Bi về nhà, không phải Bi sạc pin
- Khi bé vắng: Bi vẫn hoạt động nhẹ, không đứng im như tượng
- Giới hạn bắt buộc: cuộc sống riêng của Bi không làm phiền bé khi học hoặc ngủ

**Kiểm tra**: "Nếu bé đi học về và nhìn vào Bi, Bi có đang làm gì đó không?"

---

## Nguyên Tắc 10: Đơn Giản Để Bắt Đầu, Sâu Để Khám Phá

Robot Bi phải dễ dùng ngay từ giây đầu tiên — và càng khám phá càng thấy thú vị hơn.

**Hệ quả**:
- Bé 5 tuổi nói "Bi ơi" và ngay lập tức có trải nghiệm tốt — không cần hướng dẫn
- Không cần setup phức tạp, không cần học cách dùng
- Tính năng nâng cao có sẵn nhưng không bắt buộc — tự khám phá khi muốn
- Giao diện phụ huynh đơn giản với core features nổi bật, advanced features ẩn nhẹ
- Thêm tính năng không được làm trải nghiệm cơ bản phức tạp hơn

**Kiểm tra**: "Một đứa trẻ 5 tuổi có thể bắt đầu dùng trong vòng 30 giây không?"

---

## Cách Dùng Tài Liệu Này

### Khi thêm tính năng mới
Trước khi implement, hỏi: "Tính năng này phục vụ nguyên tắc nào trong 10 nguyên tắc trên?"

Nếu không phục vụ bất kỳ nguyên tắc nào → cân nhắc lại có nên làm không.

### Khi có mâu thuẫn giữa tính năng và nguyên tắc
Nguyên tắc thắng. Không có ngoại lệ.

### Khi không chắc về một quyết định thiết kế
Đọc lại 10 nguyên tắc và tìm nguyên tắc gần nhất. Quyết định theo nguyên tắc đó.

### Thứ tự ưu tiên khi các nguyên tắc mâu thuẫn nhau
1. Nguyên tắc 5 (An toàn trẻ em) — luôn ưu tiên tuyệt đối
2. Nguyên tắc 6 (Privacy) — không thể thương lượng
3. Nguyên tắc 1 (Bạn đồng hành) — định hướng mọi quyết định khác
4. Các nguyên tắc còn lại — cân bằng theo từng tình huống

---

## Liên Kết Tài Liệu

- Chi tiết tính cách và hành vi: [`PERSONA.md`](PERSONA.md)
- Yêu cầu hệ thống đầy đủ: [`SRS_Robot_Bi_v2.md`](SRS_Robot_Bi_v2.md)
- Backlog và tính năng: [`BACKLOG_Robot_Bi_v2.md`](BACKLOG_Robot_Bi_v2.md)
- Learning Hub vision: [`IDEA_BACKLOG.md`](IDEA_BACKLOG.md)
- Kiến trúc kỹ thuật: [`ARCHITECTURE.md`](ARCHITECTURE.md)
