# Web Application Firewall Configuration
# This module configures WAF for both GCP (Cloud Armor) and AWS (AWS WAF)
# and provide a unified management.

# --- Variables ---

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "Region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "enable_gcp_waf" {
  description = "Whether to enable GCP Cloud Armor"
  type        = bool
  default     = true
}

variable "enable_aws_waf" {
  description = "Whether to enable AWS WAF"
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "us-east-1"
}

variable "ip_whitelist" {
  description = "List of IP addresses/ranges to whitelist"
  type        = list(string)
  default     = []
}

variable "rate_limit_threshold" {
  description = "Rate limiting threshold (requests per minute)"
  type        = number
  default     = 100
}

variable "rate_limit_paths" {
  description = "Comma-separated list of request paths to apply rate limiting"
  type        = string
  default     = "/api/v1/predict,/api/v1/batch-predict"
}

variable "rate_limit_enforce_key" {
  description = "Key to enforce rate limiting on (IP, HTTP_HEADER, etc.)"
  type        = string
  default     = "IP"
  validation {
    condition     = contains(["IP", "HTTP_HEADER"], var.rate_limit_enforce_key)
    error_message = "Value must be either IP or HTTP_HEADER"
  }
}

variable "waf_expression_version" {
  description = "Version of WAF preconfigured expressions to use (GCP Cloud Armor)"
  type        = string
  default     = "v33-stable"
  # Recommended to update this value periodically to incorporate new security features
}

# --- Google Cloud Armor Security Policy ---
resource "google_compute_security_policy" "cloud_armor" {
  count       = var.enable_gcp_waf ? 1 : 0
  name        = "mlops-platform-security-policy"
  description = "WAF policy for MLOps Platform API"
  project     = var.project_id
  # Enable logging
  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
    }
  }
  # Default rule (deny all)
  rule {
    action   = "deny(403)"
    priority = "2147483647" # Max Int32 value
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default deny rule"
  }

  # Allow traffic from specific IPs if whitelist is provided
  dynamic "rule" {
    for_each = length(var.ip_whitelist) > 0 ? [1] : []
    content {
      action   = "allow"
      priority = "1000"
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = var.ip_whitelist
        }
      }
      description = "Allow whitelisted IPs"
    }
  }

  # Common web application attack protection (SQLi, XSS, LFI, RFI)
  rule {
    action   = "deny(403)"
    priority = 1100
    match {
      expr {
        expression = join(" || ", [
          "evaluatePreconfiguredExpr('sqli-${var.waf_expression_version}')",
          "evaluatePreconfiguredExpr('xss-${var.waf_expression_version}')",
          "evaluatePreconfiguredExpr('rfi-${var.waf_expression_version}')",
          "evaluatePreconfiguredExpr('lfi-${var.waf_expression_version}')"
        ])
      }
    }
    description = "Common web application attack protection"
  }

  # Rate limiting for specific paths or all paths
  rule {
    action   = "rate_based_ban"
    priority = 1500
    match {
      expr {
        expression = var.rate_limit_paths != "" ? "request.path.matches(\"" + join("\") || request.path.matches(\"", split(",", var.rate_limit_paths)) + "\")" : "true"
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = var.rate_limit_enforce_key
      rate_limit_threshold {
        count        = var.rate_limit_threshold
        interval_sec = 60
      }
    }
    description = "Rate limiting for specified endpoints"
  }
  tags = {
    "managed-by" = "terraform",
    "environment" = "production"
  }
}

# --- AWS WAF Web ACL ---
resource "aws_wafv2_web_acl" "waf" {
  count       = var.enable_aws_waf ? 1 : 0
  name        = "mlops-platform-waf"
  description = "WAF for MLOps Platform API"
  scope       = "REGIONAL" # Ensure this matches your use case, use CLOUDFRONT if using CloudFront

  default_action {
    allow {}
  }
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "mlops-platform-waf"
    sampled_requests_enabled   = true
  }
  # AWS Managed Rules - Core rule set
  rule {
    name     = "AWS-AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesCommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # AWS Managed Rules - Known bad inputs
  rule {
    name     = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWS-AWSManagedRulesKnownBadInputsRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # IP-based rate limiting
  rule {
    name     = "RateLimitRule"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = var.rate_limit_threshold
        aggregate_key_type = "IP" #  Can be changed to custom header
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  # IP whitelist if provided
  dynamic "rule" {
    for_each = length(var.ip_whitelist) > 0 ? [1] : []
    content {
      name     = "IPWhitelistRule"
      priority = 0  # Highest priority

      action {
        allow {}
      }

      statement {
        ip_set_reference_statement {
          arn = aws_wafv2_ip_set.whitelist[0].arn
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "IPWhitelistRule"
        sampled_requests_enabled   = true
      }
    }
  }

  tags = {
    "managed-by" = "terraform",
    "environment" = "production"
  }
}

# IP whitelist set for AWS WAF
resource "aws_wafv2_ip_set" "whitelist" {
  count              = var.enable_aws_waf && length(var.ip_whitelist) > 0 ? 1 : 0
  name               = "ip-whitelist"
  description        = "Whitelisted IP addresses"
  scope              = "REGIONAL"
  ip_address_version = "IPV4"
  addresses          = var.ip_whitelist

  tags = {
    "managed-by" = "terraform",
    "environment" = "production"
  }
}

# --- Outputs ---
output "gcp_security_policy_id" {
  description = "The ID of the created GCP Security Policy (Cloud Armor)"
  value       = var.enable_gcp_waf ? google_compute_security_policy.cloud_armor[0].id : null
}

output "aws_waf_acl_id" {
  description = "The ID of the created AWS WAF Web ACL"
  value       = var.enable_aws_waf ? aws_wafv2_web_acl.waf[0].id : null
}

output "aws_waf_acl_arn" {
  description = "The ARN of the created AWS WAF Web ACL"
  value       = var.enable_aws_waf ? aws_wafv2_web_acl.waf[0].arn : null
}