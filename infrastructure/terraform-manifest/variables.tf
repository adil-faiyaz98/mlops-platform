variable "gcp_project_id" {
  type        = string
  description = "The GCP project ID"
}

variable "gcp_region" {
  type        = string
  description = "The GCP region to deploy resources to"
}

variable "aws_region" {
  type        = string
  description = "The AWS region to deploy resources to"
  default = "us-east-1" #Default aws region
}