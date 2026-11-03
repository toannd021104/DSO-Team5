# Hạ tầng

Code hạ tầng được nhóm theo từng Terraform root module có thể deploy độc lập. Hiện repo có một AWS lab:

| Đường dẫn | Mục đích | State |
|---|---|---|
| [`dev/`](dev/README.md) | VPC, EKS, GuardDuty, incident workflow và sandbox response adapter | Terraform state local; triển khai tại `us-east-1` |

Giữ cấu hình riêng của môi trường trong `terraform.tfvars` không theo dõi bởi Git. Commit `.terraform.lock.hcl`; không commit state, plan, credentials, finding thô hoặc evidence.

Trước mọi lệnh `terraform apply` hoặc `destroy`:

1. Xác nhận AWS account và region.
2. Khởi tạo đúng root module và state.
3. Đọc toàn bộ plan, bao gồm dữ liệu sẽ bị xoá và tài nguyên GuardDuty cấp account.
4. Chỉ apply vào sandbox dự kiến.

Dự án chưa có remote backend dùng chung. Không để nhiều người apply từ các local state khác nhau vào cùng một account.
