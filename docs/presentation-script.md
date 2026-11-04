# Kịch bản thuyết trình Guarduty AI Ops

Thời lượng gợi ý: 10–12 phút, sau đó demo 3–5 phút. Slide nằm ở [`presentation/guarduty-aiops.pptx`](../presentation/guarduty-aiops.pptx); file này là lời dẫn để người thuyết trình giải thích thuật ngữ và phân biệt phần đã kiểm chứng với phần còn là roadmap.

## Lời dẫn theo slide

### 1. Guarduty AI Ops

“Đề tài của nhóm là xây dựng một luồng ứng phó sự cố cho ứng dụng trên EKS: phát hiện, phân tích bằng chứng, quyết định theo policy, rồi tự cách ly workload khi đủ điều kiện.”

### 2. Vấn đề cần giải quyết

“Một finding đơn lẻ thường chưa đủ để biết phải làm gì. Nếu chỉ gửi cảnh báo thì người vận hành vẫn phải điều tra và thao tác thủ công. Nếu tự động sửa quá rộng thì có thể làm gián đoạn cả cluster. Nhóm cần cân bằng tốc độ ứng phó và giới hạn ảnh hưởng.”

### 3. Luồng xử lý

“GuardDuty nhận biết dấu hiệu. EventBridge định tuyến finding. Step Functions điều phối. Analyzer gom bằng chứng và tạo giả thuyết. Policy quyết định nhánh thông báo hay containment. Nếu cách ly, workflow có thời hạn và tự release.”

### 4. Kiến trúc AWS

“EKS là môi trường demo. EKS Protection thu audit activity, Runtime Monitoring bổ sung process và network context. Evidence được lưu ở S3 và DynamoDB. SQS DLQ, CloudWatch và SNS hỗ trợ vận hành khi workflow lỗi hoặc cần người xem xét.”

### 5. Detection

“EKS Protection và Runtime Monitoring giải quyết hai lớp telemetry khác nhau. Runtime Monitoring hiện được bật với GuardDuty-managed agent. Coverage cần theo dõi riêng vì thiếu telemetry sẽ làm giảm chất lượng phát hiện.”

### 6. Finding canary

“Để kiểm chứng runtime detection trong sandbox mới, nhóm gửi một DNS lookup tới test domain do AWS chỉ định. GuardDuty tạo finding C&C DNS severity 8 và ghi nhận process, node, pod, container và domain. Đây là canary được chủ động tạo, không phải một cuộc tấn công thật.”

### 7. Phân tích nguyên nhân

“Analyzer lấy lại finding chuẩn từ GuardDuty rồi chuẩn hoá resource và runtime process. Kết quả là một giả thuyết có confidence và evidence gaps. Đây chưa phải kết luận root cause hay AI-generated analysis. Detective và Bedrock chưa dùng được trong account này do SCP.”

### 8. Policy trước khi hành động

“Runtime finding thông thường đi nhánh notify-only. Tự quarantine chỉ dành cho attack sequence Critical, account/region/cluster đúng, workload xác định chính xác và pod opt-in. Remediator còn kiểm tra owner, hostNetwork và namespace trước khi tạo policy.”

### 9. Containment có thời hạn

“Thay vì xoá pod hoặc node, hệ thống tạo NetworkPolicy hẹp để cô lập pod mục tiêu. Step Functions giữ policy tối đa 15 phút rồi gỡ đúng policy đó. Cách làm này dễ kiểm tra và rollback hơn hành động phá huỷ.”

### 10. Reliability và evidence

“Workflow có retry giới hạn, DLQ, deduplication và trạng thái incident. Evidence được lưu để truy vết. Nhánh notify-only đã publish SNS thành công, nhưng SNS topic chưa có subscriber nên hiện chưa gửi đến một người nhận.”

### 11. Demo

“Demo gồm kiểm tra account/cluster và coverage; chạy mô phỏng hành vi giới hạn; tạo DNS canary; xem finding trong GuardDuty; rồi xem record phân tích, policy decision và trạng thái workflow.”

### 12. Kết quả kiểm chứng

“Lượt chạy mới đã kiểm chứng GuardDuty runtime detection và EventBridge tự chuyển finding vào Step Functions. Workflow hoàn tất, analyzer lưu evidence vào S3/DynamoDB, chọn `NOTIFY_ONLY` và publish SNS thành công. Mô phỏng giới hạn cũng chạy lại thành công nhưng không tạo finding. Attack sequence thật và tự quarantine từ attack sequence vẫn chưa được kiểm chứng.”

### 13. Giới hạn và bước tiếp theo

“Chưa chạy attack-sequence workshop đầy đủ và chưa kiểm chứng quarantine từ attack sequence thật. SNS chưa có subscriber. Bước tiếp theo là diễn tập attack sequence trong môi trường riêng, nối subscriber, bổ sung coverage alarm, rồi đánh giá Detective/AI khi account policy cho phép.”

### 14. Kết luận

“Điểm chính là AI Ops không đồng nghĩa trao toàn quyền cho AI. Hệ thống có thể tự xử lý phần đã có policy, evidence và rollback rõ; các trường hợp chưa đủ tin cậy sẽ được đưa cho người vận hành xem xét.”

## Câu hỏi thường gặp

**Đây đã là AI Ops chưa?**

Đây là nền tảng AI Ops: detection, evidence analysis, policy gate và corrective action có kiểm soát. AI analyst chưa bật trong account hiện tại.

**Vì sao runtime DNS finding không tự quarantine?**

Policy chỉ cho phép tự cách ly EKS attack sequence Critical có target chính xác. DNS canary là finding đơn lẻ nên chỉ đi nhánh notify-only.

**Đã chứng minh được attack sequence chưa?**

Chưa. Lượt chạy mới tạo runtime DNS finding đơn lẻ; sample finding tổng hợp chỉ kiểm tra fixture path, không chứng minh correlation thật của GuardDuty.

**Root cause đã được xác định chưa?**

Chưa. Analyzer tạo giả thuyết dựa trên evidence và nói rõ dữ liệu còn thiếu.
