# Roadmap

## 0. Thiết kế (đã hoàn thành)

- [x] Chọn AWS region `ap-southeast-1` và profile `guru`.
- [x] Nghiên cứu GuardDuty, Detective, AWS incident response guidance và các repo playbook mẫu.
- [x] Vẽ luồng detect → analyze → policy → contain → recover/verify bằng SVG.
- [x] Dựng Terraform nền tảng EKS + GuardDuty + EventBridge → Lambda observe-only.
- [ ] Triển khai lên account sandbox. Hiện AWS Organization SCP explicit-deny API cần để lập Terraform plan.

## 1. Detection trên sandbox

- Bật EKS Protection và Runtime Monitoring; xác nhận GuardDuty agent coverage healthy.
- Chạy Container Security Workshop module 5.3.2 trong cluster riêng.
- Lưu event mẫu đã khử thông tin nhạy cảm, kiểm tra finding và các nguồn signal.
- Ghi lại prerequisites, chi phí thực tế và bước teardown.

**Tiêu chí đạt:** attack-sequence finding được tạo và nhận qua EventBridge; coverage được xác nhận; có thể xoá lab sạch.

## 2. Workflow phân tích (observe-only)

- EventBridge → Step Functions; retry có giới hạn, DLQ và alarm.
- Validate account/region/schema, idempotency, raw event retention và incident record.
- Enrich từ GuardDuty, EKS metadata, CloudTrail/audit và Detective context.
- Xuất root-cause hypothesis có evidence, confidence, blast radius và evidence gaps.
- Replay finding fixtures để kiểm tra các nhánh policy.

**Tiêu chí đạt:** duplicate không nhân đôi incident; thiếu context hoặc API lỗi chỉ notify; mọi kết luận có provenance.

## 3. Sandbox auto-containment

- Enable EKS VPC CNI NetworkPolicy support và xác thực giới hạn theo CNI/OS/IP family.
- Chỉ auto xử lý exact attack-sequence finding trên cluster/workload allowlist.
- Dùng role riêng, Kubernetes RBAC hẹp, action ID, TTL, verification, rollback và kill switch.
- Kiểm thử positive, false-positive, replay, timeout, partial action và recovery.

**Tiêu chí đạt:** containment chỉ tác động đúng workload đã định; policy rollback đúng resource do action tạo; lỗi không gây mutation lặp.

## 4. AI-assisted analysis

- Thêm read-only summarizer trên evidence bundle đã giảm dữ liệu nhạy cảm.
- Yêu cầu trích dẫn evidence fields và thể hiện uncertainty.
- So sánh chất lượng với incident đã được người review; policy engine vẫn là nơi duy nhất cho phép action.

## 5. Hardening

- Retention, KMS, CloudWatch metrics/alarms, ownership, runbooks, budget controls và game-day.
- Mở rộng multi-account hoặc production chỉ sau khi sandbox playbook đạt tiêu chí và quyền đã được rà soát.
