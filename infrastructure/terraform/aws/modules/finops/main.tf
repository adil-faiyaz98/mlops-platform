# FinOps module for cost optimization and monitoring

resource "aws_budgets_budget" "mlops_monthly_budget" {
  name              = "mlops-monthly-budget-${var.environment}"
  budget_type       = "COST"
  time_unit         = "MONTHLY"
  time_period_start = "2023-01-01_00:00"
  
  # Set budget limit based on environment
  limit_amount      = var.environment == "production" ? "1000" : "300"
  limit_unit        = "USD"

  # Filter to only include resources with the mlops-platform tag
  cost_filter {
    name = "TagKeyValue"
    values = [
      "user:Project$mlops-platform"
    ]
  }

  # Alert at 80% of the budget
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.alert_emails
  }

  # Alert at 100% of the budget
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.alert_emails
  }
}

# CloudWatch dashboard for cost monitoring
resource "aws_cloudwatch_dashboard" "mlops_cost_dashboard" {
  dashboard_name = "mlops-cost-dashboard-${var.environment}"
  
  dashboard_body = <<EOF
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "view": "timeSeries",
        "stacked": false,
        "metrics": [
          [ "AWS/Billing", "EstimatedCharges", "ServiceName", "AmazonEKS" ],
          [ "...", "AmazonS3" ],
          [ "...", "AmazonEC2" ],
          [ "...", "AmazonSageMaker" ],
          [ "...", "AmazonDynamoDB" ],
          [ "...", "AWSSupportBusiness" ]
        ],
        "region": "us-east-1",
        "title": "Estimated Charges by Service"
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "view": "timeSeries",
        "stacked": false,
        "metrics": [
          [ "AWS/Billing", "EstimatedCharges", "Currency", "USD" ]
        ],
        "region": "us-east-1",
        "title": "Total Estimated Charges"
      }
    }
  ]
}
EOF
}

# AWS Cost Anomaly Detection
resource "aws_ce_anomaly_monitor" "mlops_anomaly_monitor" {
  name              = "mlops-anomaly-monitor-${var.environment}"
  monitor_type      = "DIMENSIONAL"
  
  dimensional_value_count = 1
  
  dimension_value {
    dimension = "SERVICE"
    values    = ["Amazon Elastic Kubernetes Service", "Amazon SageMaker", "Amazon EC2", "Amazon S3"]
  }
}

resource "aws_ce_anomaly_subscription" "mlops_anomaly_subscription" {
  name              = "mlops-anomaly-subscription-${var.environment}"
  threshold         = 10.0
  frequency         = "DAILY"
  monitor_arn_list  = [aws_ce_anomaly_monitor.mlops_anomaly_monitor.arn]
  
  subscriber {
    type      = "EMAIL"
    address   = var.alert_emails[0]
  }
}

# Auto Scaling for EKS workloads based on cost efficiency
resource "aws_autoscaling_policy" "eks_node_cost_optimization" {
  name                   = "mlops-eks-node-cost-optimization-${var.environment}"
  adjustment_type        = "ChangeInCapacity"
  autoscaling_group_name = var.eks_asg_name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# S3 Lifecycle rules for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "model_lifecycle" {
  bucket = var.model_bucket_name

  rule {
    id     = "archive-old-models"
    status = "Enabled"

    filter {
      prefix = "models/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    filter {
      prefix = "logs/"
    }

    expiration {
      days = 90
    }
  }
}

# IAM policies for cost optimization
resource "aws_iam_policy" "cost_optimization_policy" {
  name        = "mlops-cost-optimization-policy-${var.environment}"
  description = "Policy for cost optimization automation"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetDimensionValues",
          "ce:GetTags",
          "ce:GetReservationUtilization",
          "ce:GetSavingsPlansUtilization"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sagemaker:StopTrainingJob",
          "sagemaker:StopNotebookInstance"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:ResourceTag/Environment": var.environment
            "aws:ResourceTag/Project": "mlops-platform"
          }
        }
      }
    ]
  })
}