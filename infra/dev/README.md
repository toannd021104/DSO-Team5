# AWS lab: EKS + GuardDuty

Stack này dựng một VPC riêng, EKS với worker nodes trong private subnet, GuardDuty EKS Protection, Runtime Monitoring và luồng EventBridge → Lambda.

> Lambda hiện ở chế độ **observe-only**: kiểm tra một số trường của finding rồi ghi summary vào CloudWatch Logs. Lambda không có quyền gọi Kubernetes API và không tự khắc phục sự cố.

## Trạng thái triển khai hiện tại

Stack đã deploy ở `us-east-1`: VPC, EKS 1.34, hai EC2 workers, GuardDuty EKS Protection/Runtime Monitoring, EventBridge rule và Lambda observe-only. GuardDuty agent được quản lý tự động; coverage hiện healthy cho cluster và hai worker. Sample finding `AttackSequence:EKS/CompromisedCluster` đã kích hoạt Lambda và được ghi vào CloudWatch Logs.

Terraform state đang lưu local tại workspace triển khai; không xoá hoặc thay máy làm việc trước khi chuyển state sang backend dùng chung. Region `ap-southeast-1` bị AWS Organizations policy chặn một số API discovery/create; lab hiện chạy tại `us-east-1`.

Stack **chưa** có Step Functions, Detective integration, root-cause analysis workflow hay auto-remediation. Lambda hiện chỉ validate finding và log summary.

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

Theo dõi finding đã được Lambda nhận:

```bash
aws logs tail "$(terraform output -raw incident_handler_log_group)" \
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
