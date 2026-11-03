# Dev lab: EKS + GuardDuty

Terraform root module này dựng sandbox Guarduty tại `us-east-1`.

## Tài nguyên được tạo

- VPC riêng, private subnet cho EKS worker, một NAT Gateway và EKS cluster.
- Managed node group và VPC CNI bật Kubernetes NetworkPolicy.
- GuardDuty EKS Protection và Runtime Monitoring.
- EventBridge chuyển finding vào Step Functions Standard workflow.
- Analyzer Lambda, S3 evidence bucket mã hoá, DynamoDB incident table, SQS DLQ, CloudWatch logs/alarms và SNS topic.
- Response Lambda riêng với EKS access entry và Kubernetes RBAC giới hạn trong namespace.
- Workload NGINX demo trong `guarduty-demo`, đã opt-in vào playbook quarantine.

Analyzer ghi giả thuyết dựa trên GuardDuty evidence và truy vấn CloudTrail best-effort. Analyzer chưa gọi AI model. AWS Organizations SCP của account hiện tại chặn Detective và Bedrock. SNS topic chưa có subscription; cần cấu hình destination để nhận alarm.

Response policy có thể áp dụng NetworkPolicy cho đúng pod trong 15 phút. Adapter và rollback đã được kiểm tra riêng bằng probe mạng. Bài mô phỏng runtime giới hạn đã chạy trong namespace riêng và xác nhận HTTP/API activity, nhưng chưa tạo được GuardDuty finding mới trong cửa sổ theo dõi ban đầu. Chưa chạy attack-sequence workshop end-to-end qua auto-containment.

## Yêu cầu

- Terraform `1.13.x` (xem `versions.tf`).
- AWS CLI có profile được cấp quyền quản lý các tài nguyên nêu trên.
- `kubectl` để kiểm tra cluster.
- AWS account sandbox riêng; không dùng production.
- Public IPv4 CIDR giới hạn cho EKS API endpoint, thường là IP hiện tại dạng `/32`.

File `terraform.tfvars.example` dùng profile `guru`, region `us-east-1` và CIDR chỉ dành cho tài liệu. Hãy thay CIDR trước khi apply.

## State và an toàn account

Terraform state của deployment hiện tại được lưu local và không có trong Git. Stack live đã tồn tại trong AWS account của dự án. Clone repo mới không có state đó. Không chạy `apply` từ clone mới vào account hiện hữu: Terraform có thể tạo trùng tài nguyên hoặc xung đột với cấu hình GuardDuty cấp account.

Trước khi nhiều người cùng vận hành, hãy thiết lập remote backend an toàn có locking và migrate state theo quy trình đã review. Hiện tại một operator nên quản lý local state hiện hữu và giữ bản sao lưu được bảo vệ bên ngoài repo.

## Cấu hình và deploy

Chạy trong thư mục này:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Sửa `terraform.tfvars`: đặt `allowed_cidr_blocks` thành public IP `/32` hiện tại; xác nhận profile, region, phiên bản Kubernetes, cấu hình node và remediation. Sau đó:

```bash
aws sts get-caller-identity --profile guru
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan -var-file=terraform.tfvars -out=dev.tfplan
```

Đọc `dev.tfplan`. Xác nhận account, region, CIDR EKS API, quyền sở hữu GuardDuty detector, tài nguyên bị tạo/thay đổi/xoá và chi phí dự kiến. Sau khi plan đúng:

```bash
terraform apply dev.tfplan
```

Git bỏ qua `.tfplan`, local state và `terraform.tfvars`. Giữ các file này riêng tư.

## Kết nối cluster

Chạy các lệnh trong `infra/dev`:

```bash
aws eks update-kubeconfig \
  --profile guru \
  --region us-east-1 \
  --name "$(terraform output -raw eks_cluster_name)"

kubectl get nodes
kubectl get pods -n guarduty-demo
```

## Kiểm tra dịch vụ đã deploy

Kiểm tra GuardDuty runtime coverage:

```bash
aws guardduty get-coverage-statistics \
  --profile guru \
  --region us-east-1 \
  --detector-id "$(terraform output -raw guardduty_detector_id)" \
  --statistics-type COUNT_BY_COVERAGE_STATUS COUNT_BY_RESOURCE_TYPE
```

Kiểm tra alarms và workflow:

```bash
aws cloudwatch describe-alarms \
  --profile guru \
  --region us-east-1 \
  --alarm-name-prefix guarduty-dev-

aws stepfunctions list-executions \
  --profile guru \
  --region us-east-1 \
  --state-machine-arn "arn:aws:states:us-east-1:$(aws sts get-caller-identity --profile guru --query Account --output text):stateMachine/$(terraform output -raw incident_workflow_name)" \
  --max-results 10
```

Theo dõi log của analyzer Lambda:

```bash
aws logs tail /aws/lambda/guarduty-dev-analyzer \
  --profile guru \
  --region us-east-1 \
  --follow
```

Chi tiết kiến trúc và giới hạn hiện tại nằm trong [`docs/architecture.md`](../../docs/architecture.md) và [`docs/response-playbooks.md`](../../docs/response-playbooks.md).

## Chi phí

Lab có thể phát sinh phí EKS control plane, EC2 worker, NAT Gateway, GuardDuty, CloudWatch, S3, DynamoDB, Lambda, Step Functions và data transfer. Stack dùng một NAT Gateway để tiết kiệm, không phải topology HA cho production. EKS API endpoint đang public nhưng giới hạn theo CIDR đã cấu hình.

## Huỷ lab

Trước tiên gỡ tài nguyên do workshop tạo và xác nhận đúng account/state. Sau đó tạo và đọc destroy plan:

```bash
terraform plan -destroy -var-file=terraform.tfvars -out=destroy.tfplan
terraform show destroy.tfplan
```

Evidence bucket bật `force_destroy`; destroy stack sẽ xoá incident evidence đang lưu. GuardDuty detector có scope account/region; hãy xác nhận detector chỉ thuộc lab trước khi xoá. Nếu plan đúng:

```bash
terraform apply destroy.tfplan
```

Sau khi destroy, kiểm tra AWS Console và Kubernetes để xác nhận tài nguyên đã được gỡ. Lưu lại evidence cần cho điều tra trước khi huỷ.
