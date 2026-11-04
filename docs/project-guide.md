# Guarduty AI Ops — hướng dẫn dễ hiểu

## Dự án này giải quyết việc gì?

Guarduty là phòng lab về vận hành an ninh cho ứng dụng chạy trên Amazon EKS. GuardDuty phát hiện hành vi đáng ngờ; một workflow kiểm tra bằng chứng; policy quyết định chỉ thông báo hay cách ly workload trong phạm vi sandbox.

Luồng chính:

**Detect → Analyze → Decide → Contain → Verify / Release**

Mục tiêu không phải để AI tự có quyền sửa hệ thống. Phần phân tích tạo giả thuyết có bằng chứng; policy xác định sẵn mới có quyền cho phép hành động. Trong bản lab, tự động cách ly chỉ dành cho attack sequence Critical có cluster và pod khớp chính xác, nằm trong namespace được cho phép.

## Các thành phần giống một đội ứng cứu

| Thành phần AWS | Vai trò dễ hiểu |
|---|---|
| Amazon EKS | Cụm Kubernetes chạy ứng dụng demo. |
| GuardDuty EKS Protection | Theo dõi hoạt động Kubernetes audit log. |
| GuardDuty Runtime Monitoring | Theo dõi hành vi runtime như process và kết nối mạng trên node/container. |
| Amazon EventBridge | Bộ định tuyến: chuyển đúng finding vào đúng workflow. |
| AWS Step Functions | Điều phối các bước phân tích, policy và phản hồi; có thể chờ rồi tự gỡ cách ly. |
| AWS Lambda analyzer | Lấy finding gốc, gom thông tin cluster/workload/process và ghi giả thuyết điều tra. |
| Amazon S3 | Lưu finding và evidence để xem lại. |
| Amazon DynamoDB | Theo dõi trạng thái incident, chống xử lý trùng và ghi quyết định. |
| AWS Lambda remediator + Kubernetes NetworkPolicy | Cô lập pod được cho phép mà không xoá pod hoặc node. |
| Amazon SQS DLQ / CloudWatch / SNS | Giữ event lỗi, theo dõi workflow và gửi thông báo. SNS cần subscriber để chuyển thông báo tới người vận hành. |

## Một finding đi qua hệ thống thế nào?

1. **Detect:** GuardDuty tạo finding khi thấy một hoạt động khớp dấu hiệu rủi ro.
2. **Ingest:** EventBridge lọc finding EKS attack sequence hoặc EKS Runtime Monitoring rồi khởi chạy workflow.
3. **Analyze:** Analyzer lấy lại finding chuẩn từ GuardDuty, bổ sung thông tin workload/process và lưu evidence.
4. **Decide:** Policy kiểm tra loại finding, độ nghiêm trọng, account/region/cluster, workload và cấu hình cho phép.
5. **Contain:** Nếu mọi điều kiện tự động đều đạt, remediator tạo NetworkPolicy chỉ áp dụng lên pod đã chọn.
6. **Verify / Release:** Workflow giữ cách ly tối đa 15 phút rồi gỡ đúng policy. Nếu điều kiện không đạt, gửi nhánh `NOTIFY_ONLY`.

## Vì sao cần cả GuardDuty và policy?

GuardDuty trả lời: **“Có dấu hiệu nào đáng điều tra?”** Finding không tự chứng minh nguyên nhân cuối cùng và không nên tự quyết định thay đổi môi trường. Policy trả lời: **“Có đủ điều kiện an toàn để tự hành động không?”** Phân tách hai việc này giúp demo được tự động hoá mà vẫn giới hạn blast radius.

## AI trong đề tài

AI có thể được bổ sung để tóm tắt incident, sắp xếp timeline, đưa ra giả thuyết và chỉ ra evidence còn thiếu. AI không được cấp quyền gọi API thay đổi cluster. Trong account lab hiện tại, Detective và Bedrock bị AWS Organizations SCP chặn; vì vậy bản đang chạy dùng analyzer xác định và giả thuyết theo luật, không phải AI analyst.

## Cách đọc repo

| Đường dẫn | Nội dung |
|---|---|
| [`README.md`](../README.md) | Bắt đầu nhanh, trạng thái lab và cấu trúc repo. |
| [`docs/architecture.md`](architecture.md) | Thành phần AWS và ranh giới quyền. |
| [`docs/incident-response-flow.md`](incident-response-flow.md) | Luồng xử lý chi tiết và sơ đồ SVG. |
| [`docs/research.md`](research.md) | Tài liệu AWS và kết quả nghiên cứu/lab. |
| [`docs/response-playbooks.md`](response-playbooks.md) | Điều kiện cách ly, rollback và các giới hạn. |
| [`docs/roadmap.md`](roadmap.md) | Việc đã làm và phần còn lại. |
| [`infra/dev/`](../infra/dev/README.md) | Terraform root module cho sandbox. |
| [`examples/safe-eks-runtime-simulation/`](../examples/safe-eks-runtime-simulation/README.md) | Mô phỏng runtime giới hạn và DNS canary. |
| [`presentation/`](../presentation/README.md) | Slide, mã nguồn tạo slide và cách build lại. |

## Thuật ngữ

- **Finding:** cảnh báo có cấu trúc do GuardDuty tạo.
- **Attack sequence:** finding tổng hợp nhiều dấu hiệu liên quan theo thời gian; bản lab nhắm tới `AttackSequence:EKS/CompromisedCluster`.
- **Evidence:** dữ liệu cụ thể hỗ trợ quá trình điều tra, ví dụ process, pod, cluster và thời điểm.
- **Root-cause hypothesis:** giả thuyết nguyên nhân gốc; cần ghi rõ bằng chứng và phần chưa biết, không phải kết luận pháp chứng.
- **Quarantine:** chặn lưu lượng mạng của một workload trong thời gian giới hạn để thu hẹp ảnh hưởng.
- **DLQ:** hàng đợi giữ event không xử lý được để điều tra và chạy lại.
