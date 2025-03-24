# /infrastructure/variables.tf

variable "aws_region" {
  type = string
  default = "us-east-1"
  description = "The AWS region to deploy to."
}

variable "s3_bucket_name" {
  type = string
  description = "The name of the S3 bucket to create for model artifacts and data."
}

variable "sagemaker_role_name" {
  type = string
  default = "SageMakerRole"
  description = "The name of the IAM role for SageMaker."
}

variable "training_image" {
  type = string
  description = "ECR value for Sagemaker to use the right location."
}

variable "inference_instance_type" {
  type = string
  description = "ML Type instance Sagemaker"
}