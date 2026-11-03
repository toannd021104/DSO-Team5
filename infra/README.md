# Terraform infrastructure

- `dev/` is the first disposable AWS lab stack.
- Keep environment values in an untracked `terraform.tfvars` file copied from the example.
- Never commit state files, plans, credentials, or live event data.
- Review the plan and account/region before every apply.
- The current Lambda path is observe-only. Workload mutation is intentionally a separate future milestone.
