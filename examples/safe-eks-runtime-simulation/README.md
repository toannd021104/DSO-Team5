# Mô phỏng runtime EKS trong phạm vi giới hạn

Bài tập rút gọn này tạo hoạt động Kubernetes API giới hạn và một lần TCP connect scan vào HTTP demo service trong namespace riêng. Bài được thiết kế để kiểm tra runtime telemetry mà không áp dụng ClusterRoleBinding quyền rộng, host mount đặc quyền, quét subnet lớn, truy vấn metadata, Tor traffic, sửa log trên host hoặc gây cạn tài nguyên.

Bài mô phỏng có thể tạo GuardDuty runtime finding. GuardDuty không đảm bảo sẽ tương quan lượng tín hiệu giới hạn này thành `AttackSequence:EKS/CompromisedCluster`. Bài workshop đầy đủ dùng hành vi có chủ đích rủi ro cao. Namespace này không nằm trong allowlist remediation, nên finding (nếu có) phải đi nhánh notify-only.

## Chạy

Từ thư mục gốc repo, sau khi `kubectl` đã kết nối sandbox cluster:

```bash
kubectl apply -f examples/safe-eks-runtime-simulation/manifest.yaml
kubectl rollout status deployment/workshop-victim -n guarduty-workshop --timeout=180s
kubectl wait --for=condition=complete job/scoped-recon -n guarduty-workshop --timeout=300s
kubectl logs job/scoped-recon -n guarduty-workshop
```

Kiểm tra GuardDuty findings và Runtime Monitoring coverage. Việc phát hiện diễn ra bất đồng bộ; bài rút gọn không đảm bảo sinh finding.

## Dọn dẹp

Chỉ xoá namespace của bài tập này:

```bash
kubectl delete namespace guarduty-workshop --wait=true
```

Xác nhận namespace đã được xoá trước khi chạy lại.
