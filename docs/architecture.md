# Kiến trúc Guarduty

## Trạng thái triển khai

Terraform hiện có tạo VPC/EKS, cấu hình GuardDuty, một EventBridge rule cho attack-sequence finding và Lambda observe-only ghi summary. Lambda chưa có quyền vào Kubernetes API và không chạy remediation.

## Luồng mục tiêu

Sơ đồ đầy đủ, bao gồm phân tích nguyên nhân, policy gate, sandbox auto-containment và phục hồi, nằm ở [incident-response-flow.md](incident-response-flow.md). Sơ đồ vector là [incident-response-flow.svg](incident-response-flow.svg).

### Các thành phần mục tiêu

| Thành phần | Vai trò |
|---|---|
| GuardDuty EKS Protection + Runtime Monitoring | Quan sát EKS audit logs và runtime; Extended Threat Detection tương quan tín hiệu thành attack sequence. |
| EventBridge | Lọc finding/coverage event và mở workflow; không nhét remediation logic vào event pattern. |
| Step Functions Standard | Điều phối validate → deduplicate → enrich → policy → action → verify; thể hiện retry, timeout và nhánh lỗi. |
| DynamoDB | Incident/action key để chống xử lý lặp và ghi trạng thái workflow. |
| S3 mã hoá | Lưu event/evidence theo retention đã định, giới hạn quyền đọc. Không lưu kubeconfig hay secrets. |
| Lambda read-only | Chuẩn hoá finding, lấy context được cho phép và tạo evidence bundle/root-cause hypothesis. |
| Amazon Detective | Điều tra finding groups, entities và Kubernetes/AWS activity. Đây là nguồn hỗ trợ điều tra, không phải điều kiện để phản ứng khẩn cấp. |
| Policy evaluator | Quyết định notify/approval/auto theo finding type, environment, target, confidence, coverage và action allowlist. |
| Response adapter | Thực thi một playbook giới hạn; role và Kubernetes RBAC tách khỏi quyền enrich. |
| CloudWatch / notification | Log, metrics, alarm cho coverage, workflow/DLQ và action failure. |

## Luồng xử lý

1. GuardDuty phát finding. Coverage-health event được theo dõi riêng để phát hiện khoảng trống telemetry.
2. EventBridge gửi finding phù hợp vào Step Functions và cấu hình retry/DLQ cho lỗi giao nhận.
3. Workflow xác thực account/region/schema; ghi finding gốc; tạo idempotency key từ finding và phiên bản playbook.
4. Enrichment lấy các field có nguồn rõ ràng: attack signals, cluster, namespace, pod/container/process, principal/IRSA, CloudTrail/EKS audit và owner metadata.
5. Điều tra tạo timeline, affected scope, root-cause hypothesis, confidence và evidence gaps. Detective finding groups là một nguồn tương quan bổ sung.
6. Policy gate duyệt action. Thiếu target/context hoặc lỗi service đều rơi về notify-only.
7. Sandbox policy có thể tự chạy containment reversible cho exact finding và resource allowlist. Production/high-impact có approval hoặc notify theo policy.
8. Workflow verify action; sau đó remediate nguyên nhân, recover workload, kiểm tra tái phát và lưu action/rollback.

## Quyền và ranh giới tin cậy

- EventBridge event là input không tin cậy. Kiểm tra `source`, `detail-type`, account, region, finding ID/type và resource trước mọi action.
- GuardDuty finding là bằng chứng tiềm năng; không xem description hoặc severity riêng lẻ là kết luận forensic.
- AI chỉ đọc evidence bundle đã giảm dữ liệu nhạy cảm. Kết quả phải trỏ field/evidence ID và nêu uncertainty. AI không có quyền mutation.
- IAM role cho enrichment chỉ đọc; role cho response là riêng, ngắn quyền và giới hạn theo cluster/namespace/verb.
- Kubeconfig dài hạn không được lưu trong Lambda. EKS IAM access entry và Kubernetes RBAC phải chỉ cấp quyền cho playbook đã duyệt.
- Action có action ID, idempotency, audit record, kill switch, TTL/rollback và xác minh kết quả.

## Điều kiện cho NetworkPolicy quarantine

Amazon VPC CNI phải được cấu hình hỗ trợ network policy trước khi tự động dùng playbook này. Policy chỉ kiểm soát các traffic paths mà CNI hỗ trợ; cần xác thực phiên bản CNI, OS node, IP family và NIC/traffic path. Policy adapter phải đọc pod/workload label và xác định blast radius trước khi ghi policy. Nếu selector không target được đúng workload, workflow không được tạo policy.

## Xử lý lỗi

- Event sai schema, enrichment timeout, Detective chưa có dữ liệu, target mơ hồ, coverage unhealthy, hoặc policy lỗi: ghi incident và notify; không mutation.
- Retry chỉ áp dụng cho lỗi tạm thời, có backoff và giới hạn. Lỗi vượt giới hạn đi vào DLQ, phát alarm.
- Nếu containment apply thành công nhưng verify thất bại, ghi trạng thái partial, thông báo ngay và theo runbook rollback/containment; không lặp mutation mù.
- Rollback chỉ gỡ resource do action ID hiện tại tạo, không xoá NetworkPolicy có sẵn.

## Phân kỳ xây dựng

1. Detection + EventBridge observe-only (Terraform hiện tại).
2. Orchestration, event archive, idempotency, enrichment và policy replay.
3. Sandbox NetworkPolicy quarantine với verify, TTL và rollback.
4. AI analyst read-only, đo chất lượng và evidence citation.
5. Nâng cấp account/production theo ownership, approval, retention và game-day.
