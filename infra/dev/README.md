# AWS lab: EKS + GuardDuty

Stack dựng VPC/EKS, GuardDuty EKS Protection + Runtime Monitoring và workflow EventBridge → Step Functions → analyzer. Analyzer lưu GuardDuty evidence vào S3/DynamoDB; response adapter riêng có Kubernetes RBAC giới hạn trong namespace demo và tạo NetworkPolicy quarantine có TTL.

## Trạng thái triển khai hiện tại

Stack deploy tại `us-east-1`: VPC, EKS 1.34, hai EC2 workers, GuardDuty plans, EventBridge/Step Functions, analyzer, encrypted S3 evidence (90 ngày), DynamoDB (PITR + TTL), DLQ/alarms và VPC-connected response Lambda. Analyzer tạo evidence-based root-cause hypothesis; không gọi AI. AWS Organizations SCP chặn Detective/Bedrock. Quarantine 15 phút cho pod demo opted-in đã được positive-test; sample finding fixture ngoài account/cluster nhận `NOTIFY_ONLY`. SNS topic chưa có subscriber.

Terraform state lưu local; chuyển sang backend dùng chung trước khi nhiều người cùng apply. Region lab là `us-east-1`; các thao tác Terraform phải dùng đúng workspace/state hiện có để tránh tạo stack trùng.

## Điều kiện cần

- Terraform `1.13.x`
- AWS CLI đã cấu hình profile `guru`
- `kubectl`
- Quyền tạo VPC, EKS, EC2, IAM, GuardDuty, EventBridge, Lambda và CloudWatch Logs
- Region có hỗ trợ EKS version và instance type đã chọn

Terraform lấy credentials từ AWS CLI profile tại máy bạn; không ghi access key vào file `.tf` hoặc `terraform.tfvars`.

## 1. Cấu hình lab

```bash
cp terraform.tfvars.example terraform.tfvars
```

Sửa `terraform.tfvars`:

- Giữ `aws_profile = "guru"` và `aws_region = "us-east-1"` cho lab hiện tại.
- Chọn Kubernetes version còn được AWS hỗ trợ tại region này.
- Đổi `allowed_cidr_blocks` thành IP public hiện tại của bạn dạng `/32`, ví dụ `198.51.100.25/32` chỉ là địa chỉ minh hoạ, cần thay bằng IP thật.

CIDR mở `0.0.0.0/0` bị từ chối để không public EKS API cho mọi nơi.

## 2. Xem và triển khai Terraform

Chạy từ thư mục `infra/dev`:

```bash
terraform init
terraform fmt -recursive
terraform validate
terraform plan -var-file=terraform.tfvars -out=dev.tfplan
```

Đọc plan, đặc biệt kiểm tra AWS account, region, public CIDR, số worker và tài nguyên GuardDuty. Sau khi xác nhận mới triển khai:

```bash
terraform apply dev.tfplan
```

## 3. Kết nối tới cluster

```bash
aws eks update-kubeconfig \
  --profile guru \
  --region us-east-1 \
  --name "$(terraform output -raw eks_cluster_name)"
```

Theo dõi log của analyzer Lambda trong workflow:

```bash
aws logs tail "/aws/lambda/guarduty-dev-analyzer" \
  --profile guru \
  --region us-east-1 \
  --follow
```

## GuardDuty Runtime Monitoring

Stack bật feature `RUNTIME_MONITORING` với `EKS_ADDON_MANAGEMENT`; EKS cluster được gắn tag `GuardDutyManaged=true`. Kiểm tra coverage của cluster trong GuardDuty trước khi đánh giá kết quả. Coverage `Unhealthy` nghĩa là runtime telemetry có thể không tới GuardDuty.

EKS Protection dùng audit log của Kubernetes và được bật riêng với Runtime Monitoring. Nếu account từng cấu hình EKS Runtime Monitoring kiểu cũ, hãy xem xét migration trước khi đưa Terraform quản lý detector.

## Chi phí và giới hạn

EKS control plane, EC2, NAT Gateway, GuardDuty, CloudWatch Logs và data transfer có thể tính phí. Stack dùng một NAT Gateway để tiết kiệm, nên không có tính sẵn sàng cao. Đây là cấu hình lab, không phải production.

GuardDuty detector tồn tại ở cấp account và region. Nếu account đã có detector hoặc được quản lý tập trung, hãy xác nhận quyền sở hữu trước khi đưa detector vào Terraform state.

## Xoá lab

Gỡ workload workshop trước, sau đó chạy:

```bash
terraform destroy -var-file=terraform.tfvars
```

Kiểm tra lại AWS Console để chắc chắn tài nguyên lab đã được xoá. Không xoá detector đang được hệ thống khác sử dụng.
