locals {
  name = "${var.project_name}-${var.environment}"

  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
  })
}

data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = "${local.name}-vpc"
  cidr = "10.40.0.0/16"

  azs             = slice(data.aws_availability_zones.available.names, 0, 2)
  private_subnets = ["10.40.1.0/24", "10.40.2.0/24"]
  public_subnets  = ["10.40.101.0/24", "10.40.102.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = var.single_nat_gateway
  one_nat_gateway_per_az = !var.single_nat_gateway

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = local.common_tags
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  name               = local.name
  kubernetes_version = var.kubernetes_version

  endpoint_public_access                   = true
  endpoint_public_access_cidrs             = var.allowed_cidr_blocks
  endpoint_private_access                  = true
  enable_cluster_creator_admin_permissions = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  addons = {
    coredns                = {}
    eks-pod-identity-agent = { before_compute = true }
    kube-proxy             = {}
    vpc-cni                = { before_compute = true }
  }

  eks_managed_node_groups = {
    default = {
      name           = "${local.name}-workers"
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size
    }
  }

  tags = merge(local.common_tags, {
    GuardDutyManaged = "true"
  })
}

resource "aws_guardduty_detector" "this" {
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"

  tags = local.common_tags
}

resource "aws_guardduty_detector_feature" "eks_protection" {
  detector_id = aws_guardduty_detector.this.id
  name        = "EKS_AUDIT_LOGS"
  status      = "ENABLED"
}

resource "aws_guardduty_detector_feature" "runtime_monitoring" {
  count = var.enable_runtime_monitoring ? 1 : 0

  detector_id = aws_guardduty_detector.this.id
  name        = "RUNTIME_MONITORING"
  status      = "ENABLED"

  additional_configuration {
    name   = "EKS_ADDON_MANAGEMENT"
    status = "ENABLED"
  }
}

resource "aws_cloudwatch_log_group" "incident_handler" {
  name              = "/aws/lambda/${local.name}-incident-handler"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_iam_role" "incident_handler" {
  name = "${local.name}-incident-handler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "incident_handler_logs" {
  name = "write-own-log-group"
  role = aws_iam_role.incident_handler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "${aws_cloudwatch_log_group.incident_handler.arn}:*"
    }]
  })
}

data "archive_file" "incident_handler" {
  type        = "zip"
  source_file = "${path.module}/lambda/incident_handler.py"
  output_path = "${path.module}/incident_handler.zip"
}

resource "aws_lambda_function" "incident_handler" {
  function_name = "${local.name}-incident-handler"
  description   = "Validates and records GuardDuty findings; observe-only, no remediation."
  role          = aws_iam_role.incident_handler.arn
  runtime       = "python3.13"
  handler       = "incident_handler.handler"
  timeout       = 30
  memory_size   = 128

  filename         = data.archive_file.incident_handler.output_path
  source_code_hash = data.archive_file.incident_handler.output_base64sha256

  environment {
    variables = {
      PROJECT_NAME  = local.name
      RESPONSE_MODE = "observe-only"
    }
  }

  depends_on = [aws_iam_role_policy.incident_handler_logs]

  tags = local.common_tags
}

resource "aws_cloudwatch_event_rule" "attack_sequence" {
  count = var.enable_attack_sequence_event ? 1 : 0

  name        = "${local.name}-eks-attack-sequence"
  description = "Route critical EKS attack sequence findings to the observe-only incident handler."

  event_pattern = jsonencode({
    source        = ["aws.guardduty"]
    "detail-type" = ["GuardDuty Finding"]
    detail = {
      type = ["AttackSequence:EKS/CompromisedCluster"]
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "incident_handler" {
  count = var.enable_attack_sequence_event ? 1 : 0

  rule      = aws_cloudwatch_event_rule.attack_sequence[0].name
  target_id = "${local.name}-incident-handler"
  arn       = aws_lambda_function.incident_handler.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  count = var.enable_attack_sequence_event ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.incident_handler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.attack_sequence[0].arn
}
