# Runbook demo trên AWS sandbox

Runbook dùng AWS profile `guru`, region `us-east-1` và cluster `guarduty-dev`. Chỉ chạy trong sandbox. AWS canary domain được dùng để tạo một detection finding có chủ đích; chỉ gửi DNS lookup, không kết nối tới domain.

## 1. Xác nhận account và stack

```bash
aws sts get-caller-identity --profile guru
aws eks describe-cluster --profile guru --region us-east-1 --name guarduty-dev \
  --query 'cluster.{status:status,version:version}'
kubectl get nodes
kubectl get pods -n guarduty-demo
```

Tiếp tục khi cluster `ACTIVE`, node `Ready`, pod demo `Running`.

## 2. Kiểm tra GuardDuty coverage

```bash
detector_id=$(aws guardduty list-detectors --profile guru --region us-east-1 \
  --query 'DetectorIds[0]' --output text)
aws guardduty list-coverage --profile guru --region us-east-1 \
  --detector-id "$detector_id" --output table
```

Coverage EKS và EC2 agents cần là `HEALTHY` trước khi chạy runtime canary.

## 3. Chạy mô phỏng hành vi giới hạn

```bash
kubectl apply -f examples/safe-eks-runtime-simulation/manifest.yaml
kubectl rollout status deployment/workshop-victim -n guarduty-workshop --timeout=180s
kubectl wait --for=condition=complete job/scoped-recon -n guarduty-workshop --timeout=300s
kubectl logs job/scoped-recon -n guarduty-workshop
```

Kỳ vọng: HTTP 200, TCP port 80 mở và API list có quyền giới hạn. Hoạt động này có thể không tạo GuardDuty finding.

## 4. Chạy DNS canary

```bash
kubectl exec -n guarduty-demo deployment/guarduty-demo-victim -- \
  nslookup guarddutyc2activityb.com
```

GuardDuty có thể tạo finding `Backdoor:Runtime/C&CActivity.B!DNS`. Detection xuất hiện bất đồng bộ. Lấy detector ID và finding gần nhất:

```bash
aws guardduty list-findings --profile guru --region us-east-1 \
  --detector-id "$detector_id" \
  --finding-criteria '{"Criterion":{"type":{"Equals":["Backdoor:Runtime/C&CActivity.B!DNS"]}}}' \
  --sort-criteria '{"AttributeName":"updatedAt","OrderBy":"DESC"}' \
  --max-results 10
```

Runtime finding đơn lẻ phải đi `NOTIFY_ONLY`; đây không phải attack sequence và không được tự quarantine.

## 5. Kiểm tra workflow, evidence và thông báo

```bash
state_machine_arn=$(aws stepfunctions list-state-machines --profile guru --region us-east-1 \
  --query "stateMachines[?name=='guarduty-dev-incident-workflow'].stateMachineArn | [0]" \
  --output text)
aws stepfunctions list-executions --profile guru --region us-east-1 \
  --state-machine-arn "$state_machine_arn" --max-results 10
```

Hoặc lấy tên state machine từ `terraform -chdir=infra/dev output incident_workflow_name`, rồi xem execution trong AWS Console. Kiểm tra S3/DynamoDB evidence, execution output và SNS publish. SNS topic cần subscriber để có người nhận.

Ở lần chạy sandbox gần nhất, DNS canary tạo finding `Backdoor:Runtime/C&CActivity.B!DNS`; EventBridge tự khởi chạy workflow và execution hoàn tất với quyết định `NOTIFY_ONLY`. Finding/evidence có object trong S3, incident state có record trong DynamoDB, SNS publish thành công nhưng topic chưa có subscriber. Đây là runtime finding đơn lẻ, không phải attack sequence.

## 6. Cleanup

```bash
kubectl delete namespace guarduty-workshop --wait=true
kubectl get networkpolicy -A
kubectl get pods -n guarduty-demo
```

Namespace mô phỏng phải bị xoá, không còn NetworkPolicy canary, và pod demo vẫn `Running`. Hạ tầng Terraform được giữ lại để tiếp tục thuyết trình; xem [hướng dẫn teardown](../infra/dev/README.md) khi kết thúc toàn bộ lab.
