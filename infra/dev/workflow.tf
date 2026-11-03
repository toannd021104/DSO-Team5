resource "aws_s3_bucket" "incident_evidence" {
  bucket_prefix = "${local.name}-incident-evidence-"
  force_destroy = true
  tags          = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "incident_evidence" {
  bucket                  = aws_s3_bucket.incident_evidence.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "incident_evidence" {
  bucket = aws_s3_bucket.incident_evidence.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "incident_evidence" {
  bucket = aws_s3_bucket.incident_evidence.id
  rule {
    id     = "expire-incident-evidence"
    status = "Enabled"
    expiration { days = 90 }
  }
}

resource "aws_dynamodb_table" "incidents" {
  name         = "${local.name}-incidents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "finding_id"
  attribute {
    name = "finding_id"
    type = "S"
  }
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
  tags = local.common_tags
}

resource "aws_sqs_queue" "workflow_dlq" {
  name                      = "${local.name}-workflow-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
  tags                      = local.common_tags
}

resource "aws_cloudwatch_log_group" "workflow" {
  name              = "/aws/states/${local.name}-incident-workflow"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_sns_topic" "incident_alerts" {
  name              = "${local.name}-incident-alerts"
  kms_master_key_id = "alias/aws/sns"
  tags              = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "workflow_failures" {
  alarm_name          = "${local.name}-workflow-failures"
  alarm_description   = "Incident workflow executions failed; review execution history and logs."
  namespace           = "AWS/States"
  metric_name         = "ExecutionsFailed"
  dimensions          = { StateMachineArn = aws_sfn_state_machine.incident.arn }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.incident_alerts.arn]
  ok_actions          = [aws_sns_topic.incident_alerts.arn]
  tags                = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "workflow_dlq" {
  alarm_name          = "${local.name}-workflow-dlq-not-empty"
  alarm_description   = "GuardDuty events could not start the incident workflow; inspect the EventBridge dead-letter queue."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = aws_sqs_queue.workflow_dlq.name }
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.incident_alerts.arn]
  ok_actions          = [aws_sns_topic.incident_alerts.arn]
  tags                = local.common_tags
}

resource "aws_iam_role" "eventbridge_stepfunctions" {
  name = "${local.name}-eventbridge-sfn"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "events.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "eventbridge_stepfunctions" {
  name = "start-incident-workflow"
  role = aws_iam_role.eventbridge_stepfunctions.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "states:StartExecution", Resource = aws_sfn_state_machine.incident.arn }]
  })
}

resource "aws_iam_role" "workflow" {
  name = "${local.name}-workflow"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "states.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
  tags = local.common_tags
}

resource "aws_iam_role_policy" "workflow" {
  name = "invoke-incident-functions-and-write-logs"
  role = aws_iam_role.workflow.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["lambda:InvokeFunction"], Resource = [aws_lambda_function.analyzer.arn, aws_lambda_function.remediator.arn] },
      { Effect = "Allow", Action = ["logs:CreateLogDelivery", "logs:GetLogDelivery", "logs:UpdateLogDelivery", "logs:DeleteLogDelivery", "logs:ListLogDeliveries", "logs:PutResourcePolicy", "logs:DescribeResourcePolicies", "logs:DescribeLogGroups"], Resource = "*" }
    ]
  })
}

resource "aws_sfn_state_machine" "incident" {
  name     = "${local.name}-incident-workflow"
  role_arn = aws_iam_role.workflow.arn
  type     = "STANDARD"
  definition = jsonencode({
    StartAt = "AnalyzeFinding"
    States = {
      AnalyzeFinding = {
        Type           = "Task"
        Resource       = "arn:aws:states:::lambda:invoke"
        Parameters     = { FunctionName = aws_lambda_function.analyzer.arn, "Payload.$" = "$" }
        ResultSelector = { "analysis.$" = "$.Payload" }
        ResultPath     = "$.workflow"
        Retry          = [{ ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException", "Lambda.TooManyRequestsException"], IntervalSeconds = 2, BackoffRate = 2, MaxAttempts = 3 }]
        Catch          = [{ ErrorEquals = ["States.ALL"], ResultPath = "$.error", Next = "AnalysisFailed" }]
        Next           = "CheckPolicy"
      }
      CheckPolicy = {
        Type = "Choice"
        Choices = [
          { Variable = "$.workflow.analysis.duplicate", BooleanEquals = true, Next = "Duplicate" },
          { Variable = "$.workflow.analysis.auto_remediate", BooleanEquals = true, Next = "QuarantineTarget" }
        ]
        Default = "NotifyOnly"
      }
      QuarantineTarget = {
        Type           = "Task"
        Resource       = "arn:aws:states:::lambda:invoke"
        Parameters     = { FunctionName = aws_lambda_function.remediator.arn, "Payload.$" = "$.workflow.analysis" }
        ResultSelector = { "response.$" = "$.Payload" }
        ResultPath     = "$.workflow.remediation"
        Retry          = [{ ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException", "Lambda.TooManyRequestsException"], IntervalSeconds = 2, BackoffRate = 2, MaxAttempts = 2 }]
        Catch          = [{ ErrorEquals = ["States.ALL"], ResultPath = "$.error", Next = "RemediationFailed" }]
        Next           = "ContainmentWindow"
      }
      ContainmentWindow = { Type = "Wait", Seconds = 900, Next = "ReleaseQuarantine" }
      ReleaseQuarantine = {
        Type           = "Task"
        Resource       = "arn:aws:states:::lambda:invoke"
        Parameters     = { FunctionName = aws_lambda_function.remediator.arn, Payload = { action = "release", "finding_id.$" = "$.workflow.analysis.finding_id" } }
        ResultSelector = { "response.$" = "$.Payload" }
        ResultPath     = "$.workflow.release"
        Retry          = [{ ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException", "Lambda.TooManyRequestsException"], IntervalSeconds = 2, BackoffRate = 2, MaxAttempts = 3 }]
        Catch          = [{ ErrorEquals = ["States.ALL"], ResultPath = "$.error", Next = "ReleaseFailed" }]
        Next           = "Complete"
      }
      NotifyOnly        = { Type = "Succeed" }
      Duplicate         = { Type = "Succeed" }
      AnalysisFailed    = { Type = "Fail", Error = "AnalysisFailed", Cause = "Finding analysis failed; see workflow logs and incident record." }
      RemediationFailed = { Type = "Fail", Error = "RemediationFailed", Cause = "Containment failed; see workflow logs and incident record." }
      ReleaseFailed     = { Type = "Fail", Error = "ReleaseFailed", Cause = "Scheduled containment expiry failed; manually remove the action-specific policy." }
      Complete          = { Type = "Succeed" }
    }
  })
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.workflow.arn}:*"
    include_execution_data = false
    level                  = "ALL"
  }
  depends_on = [aws_iam_role_policy.workflow]
  tags       = local.common_tags
}

resource "aws_sqs_queue_policy" "workflow_dlq" {
  queue_url = aws_sqs_queue.workflow_dlq.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow", Principal = { Service = "events.amazonaws.com" }, Action = "sqs:SendMessage",
      Resource = aws_sqs_queue.workflow_dlq.arn, Condition = { ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.attack_sequence[0].arn } }
    }]
  })
}

resource "aws_cloudwatch_event_target" "workflow" {
  count     = var.enable_attack_sequence_event ? 1 : 0
  rule      = aws_cloudwatch_event_rule.attack_sequence[0].name
  target_id = "incident-workflow"
  arn       = aws_sfn_state_machine.incident.arn
  role_arn  = aws_iam_role.eventbridge_stepfunctions.arn
  dead_letter_config {
    arn = aws_sqs_queue.workflow_dlq.arn
  }
  retry_policy {
    maximum_event_age_in_seconds = 3600
    maximum_retry_attempts       = 12
  }
}

resource "aws_security_group" "remediator" {
  name_prefix = "${local.name}-remediator-"
  description = "Egress from response Lambda to EKS Kubernetes API only."
  vpc_id      = module.vpc.vpc_id
  egress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [module.eks.cluster_security_group_id]
  }
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.common_tags
}

resource "aws_vpc_security_group_ingress_rule" "remediator_to_cluster" {
  security_group_id            = module.eks.cluster_security_group_id
  referenced_security_group_id = aws_security_group.remediator.id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
  description                  = "Guarduty response Lambda to EKS API"
}

resource "aws_iam_role" "analyzer" {
  name               = "${local.name}-analyzer"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "analyzer" {
  name = "read-findings-and-store-evidence"
  role = aws_iam_role.analyzer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["guardduty:GetFindings"], Resource = "arn:aws:guardduty:${var.aws_region}:${data.aws_caller_identity.current.account_id}:detector/${aws_guardduty_detector.this.id}/findings/get" },
      { Effect = "Allow", Action = ["cloudtrail:LookupEvents"], Resource = "*" },
      { Effect = "Allow", Action = ["dynamodb:PutItem", "dynamodb:UpdateItem"], Resource = aws_dynamodb_table.incidents.arn },
      { Effect = "Allow", Action = ["s3:PutObject"], Resource = "${aws_s3_bucket.incident_evidence.arn}/*" },
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.analyzer.arn}:*" }
    ]
  })
}

resource "aws_cloudwatch_log_group" "analyzer" {
  name              = "/aws/lambda/${local.name}-analyzer"
  retention_in_days = 30
  tags              = local.common_tags
}

data "archive_file" "analyzer" {
  type        = "zip"
  source_file = "${path.module}/lambda/analyzer.py"
  output_path = "${path.module}/analyzer.zip"
}

resource "aws_lambda_function" "analyzer" {
  function_name    = "${local.name}-analyzer"
  role             = aws_iam_role.analyzer.arn
  runtime          = "python3.13"
  handler          = "analyzer.handler"
  timeout          = 60
  memory_size      = 256
  filename         = data.archive_file.analyzer.output_path
  source_code_hash = data.archive_file.analyzer.output_base64sha256
  environment {
    variables = {
      TABLE_NAME  = aws_dynamodb_table.incidents.name
      BUCKET      = aws_s3_bucket.incident_evidence.id
      CLUSTER     = module.eks.cluster_name
      DETECTOR_ID = aws_guardduty_detector.this.id
      NAMESPACE   = var.remediation_namespace
      MODE        = var.auto_remediation_enabled ? "auto" : "observe-only"
    }
  }
  depends_on = [aws_iam_role_policy.analyzer]
  tags       = local.common_tags
}

resource "aws_iam_role" "remediator" {
  name               = "${local.name}-remediator"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "remediator_vpc" {
  role       = aws_iam_role.remediator.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "remediator_describe_cluster" {
  name = "describe-lab-cluster"
  role = aws_iam_role.remediator.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [
      { Effect = "Allow", Action = ["eks:DescribeCluster"], Resource = module.eks.cluster_arn },
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:UpdateItem"], Resource = aws_dynamodb_table.incidents.arn }
    ]
  })
}

resource "aws_cloudwatch_log_group" "remediator" {
  name              = "/aws/lambda/${local.name}-remediator"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_eks_access_entry" "remediator" {
  cluster_name      = module.eks.cluster_name
  principal_arn     = aws_iam_role.remediator.arn
  type              = "STANDARD"
  kubernetes_groups = ["guarduty-remediator"]
}

resource "kubernetes_namespace_v1" "remediation" {
  metadata {
    name   = var.remediation_namespace
    labels = { "guarduty.io/environment" = "sandbox" }
  }
}

resource "kubernetes_role_v1" "remediator" {
  metadata {
    name      = "guarduty-remediator"
    namespace = kubernetes_namespace_v1.remediation.metadata[0].name
  }
  rule {
    api_groups = [""]
    resources  = ["pods"]
    verbs      = ["get", "list"]
  }
  rule {
    api_groups = ["networking.k8s.io"]
    resources  = ["networkpolicies"]
    verbs      = ["get", "create", "delete"]
  }
}

resource "kubernetes_role_binding_v1" "remediator" {
  metadata {
    name      = "guarduty-remediator"
    namespace = kubernetes_namespace_v1.remediation.metadata[0].name
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.remediator.metadata[0].name
  }
  subject {
    kind      = "Group"
    name      = "guarduty-remediator"
    api_group = "rbac.authorization.k8s.io"
  }
}

data "archive_file" "remediator" {
  type        = "zip"
  source_file = "${path.module}/lambda/remediator.py"
  output_path = "${path.module}/remediator.zip"
}

resource "kubernetes_deployment_v1" "demo_victim" {
  metadata {
    name      = "guarduty-demo-victim"
    namespace = kubernetes_namespace_v1.remediation.metadata[0].name
    labels    = { app = "guarduty-demo-victim" }
  }
  spec {
    replicas = 1
    selector {
      match_labels = { app = "guarduty-demo-victim" }
    }
    template {
      metadata {
        labels = {
          app                           = "guarduty-demo-victim"
          "guarduty.io/auto-quarantine" = "true"
        }
      }
      spec {
        container {
          name  = "web"
          image = "public.ecr.aws/nginx/nginx:1.27-alpine"
          port {
            container_port = 80
          }
          resources {
            requests = { cpu = "25m", memory = "32Mi" }
            limits   = { cpu = "100m", memory = "64Mi" }
          }
        }
      }
    }
  }
  wait_for_rollout = true
  depends_on       = [kubernetes_role_binding_v1.remediator]
}

resource "aws_lambda_function" "remediator" {
  function_name    = "${local.name}-remediator"
  description      = "Applies reversible, exact-scope network quarantine in the opt-in lab namespace."
  role             = aws_iam_role.remediator.arn
  runtime          = "python3.13"
  handler          = "remediator.handler"
  timeout          = 60
  memory_size      = 256
  filename         = data.archive_file.remediator.output_path
  source_code_hash = data.archive_file.remediator.output_base64sha256
  vpc_config {
    subnet_ids         = module.vpc.private_subnets
    security_group_ids = [aws_security_group.remediator.id]
  }
  environment {
    variables = {
      CLUSTER       = module.eks.cluster_name
      CLUSTER_URL   = module.eks.cluster_endpoint
      CLUSTER_CA    = module.eks.cluster_certificate_authority_data
      AWS_ACCOUNT   = data.aws_caller_identity.current.account_id
      NAMESPACE     = var.remediation_namespace
      POLICY_PREFIX = "guarduty-q-"
      TABLE_NAME    = aws_dynamodb_table.incidents.name
    }
  }
  depends_on = [aws_iam_role_policy.remediator_describe_cluster, kubernetes_role_binding_v1.remediator, aws_iam_role_policy_attachment.remediator_vpc]
  tags       = local.common_tags
}
