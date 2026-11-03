variable "aws_region" {
  description = "AWS region for this disposable EKS and GuardDuty lab."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile used by Terraform."
  type        = string
  default     = "guru"
}

variable "project_name" {
  description = "Short project prefix used in AWS resource names."
  type        = string
  default     = "guarduty"
}

variable "environment" {
  description = "Environment name used in resource names and tags."
  type        = string
  default     = "dev"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes minor version supported in the selected region."
  type        = string
  default     = "1.34"
}

variable "enable_runtime_monitoring" {
  description = "Enable GuardDuty EKS Runtime Monitoring and automated agent management."
  type        = bool
  default     = true
}

variable "enable_attack_sequence_event" {
  description = "Route critical EKS attack sequence findings into the incident workflow."
  type        = bool
  default     = true
}

variable "auto_remediation_enabled" {
  description = "Allow the deterministic policy to quarantine only opted-in pods in the dedicated sandbox namespace."
  type        = bool
  default     = true
}

variable "remediation_namespace" {
  description = "Dedicated namespace containing only workloads explicitly opted into sandbox quarantine."
  type        = string
  default     = "guarduty-demo"

  validation {
    condition     = can(regex("^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", var.remediation_namespace)) && var.remediation_namespace != "kube-system"
    error_message = "Use a valid, dedicated non-system Kubernetes namespace."
  }
}

variable "node_instance_types" {
  description = "EC2 instance types for the EKS managed node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Desired number of EKS worker nodes."
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum number of EKS worker nodes."
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of EKS worker nodes."
  type        = number
  default     = 3
}

variable "single_nat_gateway" {
  description = "Use one NAT Gateway to reduce lab cost. This is not a highly available production design."
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "IPv4 CIDRs allowed to reach the EKS public API endpoint. Replace the default with your current public IP /32 before applying."
  type        = list(string)
  default     = []

  validation {
    condition     = length(var.allowed_cidr_blocks) > 0 && !contains(var.allowed_cidr_blocks, "0.0.0.0/0")
    error_message = "Set one or more restricted CIDRs; do not expose the EKS API to 0.0.0.0/0."
  }
}

variable "tags" {
  description = "Additional tags applied to supported resources."
  type        = map(string)
  default     = {}
}
