# Đóng góp

Cảm ơn bạn đã giúp cải thiện Guarduty. Giữ thay đổi tập trung, nêu rõ ảnh hưởng vận hành và cập nhật tài liệu cùng với thay đổi hành vi.

## Quy ước repository

- README gốc giúp người mới nắm dự án; để hướng dẫn deploy trong `infra/dev/README.md`.
- Giải thích cho người mới và nội dung thuyết trình thuộc `docs/` và `presentation/`; chỉnh mã nguồn `presentation/build_deck.py` rồi build lại PPTX.
- Slide phải phân biệt rõ finding thật, sample/synthetic fixture và nội dung roadmap. Không gọi analyzer rule-based là AI analyst.
- Giữ stack deploy hiện tại trong `infra/dev`. Chỉ tách Terraform module dùng lại khi có consumer thứ hai thực tế.
- Tách bạch trách nhiệm AWS operation, remediation policy và analysis. Output AI/model không được cấp quyền Kubernetes mutation.
- Cập nhật `docs/architecture.md`, `docs/response-playbooks.md` và `docs/roadmap.md` khi luồng hoặc trạng thái thay đổi.
- Khi đổi incident flow, cập nhật đồng bộ sơ đồ SVG, project guide và slide source/deck.
- Dùng event fixture tổng hợp đã loại dữ liệu nhạy cảm. Không commit finding hoặc incident evidence thật.

## Thay đổi Terraform

Chạy trong `infra/dev`:

```bash
terraform fmt -recursive
terraform init
terraform validate
terraform plan -var-file=terraform.tfvars
```

Đọc kỹ account, region, thay đổi tài nguyên và chi phí trước khi apply. Không apply vào project account từ checkout mới; state của account đó được lưu local và không có trong repo. Xác định người quản lý state trước khi thay đổi stack live.

## Bảo mật và file sinh tự động

Không commit:

- `terraform.tfvars`, Terraform state, plan, credentials hoặc private key.
- GuardDuty event thô, CloudTrail record, S3 evidence hoặc secret gắn với account.
- Lambda ZIP sinh tự động, Python bytecode hoặc cache directory.

Commit `.terraform.lock.hcl` để giữ lựa chọn provider nhất quán.

PPTX là artifact có thể sinh lại và được commit để tiện thuyết trình; `build_deck.py` là nguồn nội dung chuẩn. Không đưa AWS credentials, account evidence hoặc tài nguyên cloud thật vào slide.

## Pull request

Mô tả hành vi thay đổi, Terraform resource bị ảnh hưởng, thao tác validation đã chạy, tác động chi phí/quyền truy cập và tài liệu đã cập nhật. Cập nhật sơ đồ khi incident flow thay đổi.
