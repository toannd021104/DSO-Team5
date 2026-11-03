# Development lab

This stack creates a dedicated VPC, a private-node EKS cluster, GuardDuty EKS Protection, optional EKS Runtime Monitoring, and an EventBridge → Lambda finding path. The Lambda is intentionally **observe-only**: it validates the event and writes a compact summary to CloudWatch. It has no EKS access and cannot remediate workloads.

## Prerequisites

- Terraform 1.13.x
- AWS CLI credentials for profile `guru`
- kubectl
- An AWS region where the selected EKS version and instance type are available
- Permissions to create VPC, EKS, EC2, IAM, GuardDuty, EventBridge, Lambda, and CloudWatch resources

The AWS provider uses the local profile; no credentials are stored in Terraform variables or source control.

## Configure

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `allowed_cidr_blocks` to your current public IPv4 address in `/32` form. The example address is documentation-only and will not allow access. Keep the EKS public endpoint restricted to your own IP.

Check the supported EKS version in the chosen region and update `kubernetes_version` if necessary. Runtime Monitoring uses the current `RUNTIME_MONITORING` feature and GuardDuty-managed EKS add-on setting. The cluster is tagged `GuardDutyManaged=true` for agent management. Existing clusters or accounts with legacy EKS Runtime Monitoring configuration may require migration review.

## Plan and deploy

From this directory:

```bash
terraform init
terraform fmt -recursive
terraform validate
terraform plan -var-file=terraform.tfvars -out=dev.tfplan
terraform apply dev.tfplan
```

Review the plan carefully. EKS, NAT Gateway, EC2 nodes, GuardDuty protection, log storage, and data transfer can incur charges. This example uses one NAT Gateway to lower cost and is not highly available.

Configure kubectl after apply:

```bash
aws eks update-kubeconfig \
  --profile guru \
  --region ap-southeast-1 \
  --name "$(terraform output -raw eks_cluster_name)"
```

Inspect the observe-only Lambda log group:

```bash
aws logs tail "$(terraform output -raw incident_handler_log_group)" \
  --profile guru \
  --region ap-southeast-1 \
  --follow
```

## Runtime Monitoring behavior

GuardDuty Runtime Monitoring coverage depends on agent deployment and healthy connectivity. Verify coverage in GuardDuty before interpreting missing runtime findings as a clean result. EKS Protection is enabled independently and uses EKS audit log signals.

## Destroy the lab

Remove any workshop workloads first, then destroy resources from this directory:

```bash
terraform destroy -var-file=terraform.tfvars
```

Confirm that the detector features and all lab resources are removed in the AWS console. GuardDuty can be account-level and may already be managed elsewhere; do not adopt an existing detector into this disposable state without reviewing ownership and impact.
