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

output "incident_workflow_name" {
  description = "Step Functions state machine that analyzes and applies guarded response decisions."
  value       = aws_sfn_state_machine.incident.name
}

output "incident_evidence_bucket" {
  description = "Private S3 bucket retaining raw findings and normalized evidence for 90 days."
  value       = aws_s3_bucket.incident_evidence.id
}

output "remediation_namespace" {
  description = "Dedicated namespace whose opted-in demo workload can be quarantined."
  value       = kubernetes_namespace_v1.remediation.metadata[0].name
}

output "incident_alert_topic_arn" {
  description = "SNS topic for workflow failure and dead-letter alarms; subscribe an operator endpoint to receive alerts."
  value       = aws_sns_topic.incident_alerts.arn
}
