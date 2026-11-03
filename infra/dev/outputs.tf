output "aws_region" {
  description = "Region containing the lab infrastructure."
  value       = var.aws_region
}

output "eks_cluster_name" {
  description = "Name of the EKS lab cluster."
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Kubernetes API endpoint for the EKS lab cluster."
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "guardduty_detector_id" {
  description = "GuardDuty detector ID configured by this stack."
  value       = aws_guardduty_detector.this.id
}

output "incident_handler_name" {
  description = "Observe-only Lambda function receiving attack sequence events."
  value       = aws_lambda_function.incident_handler.function_name
}

output "incident_handler_log_group" {
  description = "CloudWatch log group for incident handler summaries."
  value       = aws_cloudwatch_log_group.incident_handler.name
}
