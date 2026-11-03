# Roadmap

## 0. Thiết kế và nền tảng (hoàn thành)

- [x] Chọn region `us-east-1`, profile `guru`; nghiên cứu AWS docs/workshops và dự án tham khảo.
- [x] SVG luồng detect → analyze → policy → contain → verify/release.
- [x] Dựng VPC, EKS 1.34, hai worker, GuardDuty EKS Protection + Runtime Monitoring.
- [x] EventBridge → Step Functions, retry, SQS DLQ, alarms, DynamoDB incident state, S3 evidence (90 ngày).

## 1. Detection (đã deploy; workshop còn lại)

- [x] GuardDuty plans và managed agent; coverage hiện healthy (1 EKS + 2 EC2).
- [x] Sample finding qua workflow; sample tổng hợp ngoài account/cluster lab được `NOTIFY_ONLY`.
- [ ] Chạy Container Security Workshop 5.3.2 để tạo attack sequence thật trong cluster lab và ghi kết quả/cleanup.

## 2. Evidence analysis (đã deploy; giới hạn rõ)

- [x] Lấy finding canonical bằng GuardDuty `GetFindings`; lưu event/finding/analysis vào S3 và trạng thái vào DynamoDB.
- [x] Trích actor, resource, workload, signals, MITRE indicators; CloudTrail lookup best-effort; lưu root-cause hypothesis và evidence gaps.
- [x] Deterministic gates theo account, region, type, severity, cluster, namespace và pod exact.
- [ ] Detective enrichment: SCP hiện từ chối `detective:ListGraphs`.
- [ ] AI summary: SCP hiện từ chối Bedrock `ListFoundationModels`/`InvokeModel`.

**Giới hạn:** đây là evidence-based triage, không phải forensic root-cause kết luận hay AI analyst.

## 3. Sandbox containment (đã deploy và positive-test)

- [x] Bật VPC CNI NetworkPolicy và dùng namespace `guarduty-demo`; chỉ pod có opt-in label mới đủ điều kiện.
- [x] Response role riêng, EKS access entry và Kubernetes RBAC chỉ trong namespace.
- [x] Tạo policy theo selector pod, xác minh object; Step Functions chờ 15 phút rồi release đúng policy có finding label.
- [x] Positive test: policy chặn probe vào demo web pod; release gỡ policy; kiểm tra lại trạng thái sạch.
- [ ] Chạy attack-sequence end-to-end để xác minh GuardDuty finding thật dẫn đến quarantine tự động.
- [ ] Test false positive, duplicate, timeout, partial failure và rollback trong replay/game-day.

## 4. Operations và AI (còn lại)

- [ ] Subscribe SNS alarm topic để người vận hành nhận lỗi workflow/DLQ.
- [ ] Bổ sung coverage-health alarm và dashboard/SLO cho detection, analysis, containment.
- [ ] Khi policy account cho phép, bật Detective enrichment và AI summarizer read-only có citation.
- [ ] Chuyển Terraform state sang backend dùng chung có locking trước khi làm nhóm.
- [ ] Thiết lập budget alert, runbook và teardown; chỉ cân nhắc production sau review quyền/blast radius.
