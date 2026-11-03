# Kiến trúc Guarduty

## Trạng thái triển khai

Stack deploy ở `us-east-1`: VPC/EKS, GuardDuty EKS Protection/Runtime Monitoring, EventBridge → Step Functions, analyzer, S3/DynamoDB evidence store, DLQ/alarms và response Lambda trong VPC. Sample AttackSequence fixture ngoài account/cluster lab được xử lý `NOTIFY_ONLY`. Quarantine NetworkPolicy trên pod opted-in đã được test bằng probe mạng và release.

Detective API và Bedrock bị từ chối bởi AWS Organizations SCP; vì vậy không có Detective enrichment hay AI summary hoạt động. SNS alarm topic chưa có subscription.

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
| Amazon Detective | Nguồn enrichment thiết kế; chưa hoạt động trong account hiện tại do Organizations SCP chặn `detective:ListGraphs`. |
| Policy evaluator | Analyzer xét finding type/severity, account/region/cluster, namespace và một pod exact; adapter kiểm tra opt-in label, owner controller và hostNetwork. Coverage/confidence chưa là gate. |
| Response adapter | Thực thi một playbook giới hạn; role và Kubernetes RBAC tách khỏi quyền enrich. |
| CloudWatch / notification | Workflow failure và DLQ alarms; SNS topic chưa có subscription. Coverage alarm và per-finding notification chưa triển khai. |

## Luồng xử lý

1. GuardDuty phát finding. Coverage hiện kiểm tra qua GuardDuty; chưa có alarm tự động cho khoảng trống telemetry.
2. EventBridge gửi finding phù hợp vào Step Functions và cấu hình retry/DLQ cho lỗi giao nhận.
3. Workflow xác thực account/region/schema; ghi finding gốc; tạo idempotency key từ finding và phiên bản playbook.
4. Analyzer trích GuardDuty sequence signals/actors/resources/MITRE và workload; CloudTrail lookup theo actor là best-effort. Pod labels và owner controller chỉ được xác minh ngay trước action; EKS audit/Detective enrichment chưa được nối.
5. Analyzer lưu GuardDuty signals/resources/MITRE, CloudTrail lookup best-effort, affected scope, root-cause hypothesis và evidence gaps. Detective chưa được gọi do SCP.
6. Policy gate xét finding type/severity, account, region, cluster, namespace và target pod; response adapter kiểm tra opt-in label, owner controller và loại hostNetwork. Coverage-health chưa nối vào policy; cần triển khai alarm trước khi dùng như điều kiện tự động.
7. Sandbox policy có thể tự chạy NetworkPolicy containment reversible cho exact Critical finding và pod allowlist. Production/high-impact chưa có playbook.
8. Adapter xác minh object/selector, Step Functions chờ 15 phút rồi gỡ policy; data-plane verification đã chạy thủ công trong lab. Eradication/rebuild/credential rotation chưa tự động hoá.

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

- Event sai schema, enrichment timeout, target mơ hồ hoặc policy lỗi: workflow fail/notify-only, không mutation. Coverage-health alarm chưa được triển khai; đây là hạng mục roadmap.
- Retry chỉ áp dụng cho lỗi tạm thời, có backoff và giới hạn. Lỗi vượt giới hạn đi vào DLQ, phát alarm.
- Nếu containment apply thành công nhưng verify thất bại, ghi trạng thái partial, thông báo ngay và theo runbook rollback/containment; không lặp mutation mù.
- Rollback chỉ gỡ resource do action ID hiện tại tạo, không xoá NetworkPolicy có sẵn.

## Phân kỳ xây dựng

1. Detection, EventBridge/Step Functions, evidence store, analyzer và guarded sandbox quarantine/release (đã deploy; sample finding đã đi notify-only, adapter đã positive-test).
2. Workshop attack sequence end-to-end và replay các nhánh failure.
3. Thêm per-finding notification và subscribe SNS alarm topic.
4. Bật Detective/AI analyst read-only sau khi SCP/quyền account cho phép; đo chất lượng và evidence citation.
5. Hardening, game-day và review blast radius trước khi cân nhắc production.
