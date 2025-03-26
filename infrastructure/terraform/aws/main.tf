terraform {
  required_version = ">= 1.0.0"
  
  backend "s3" {
    # Will be parameterized via CLI
    # bucket         = "mlops-terraform-state"
    # key            = "platform/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "mlops-terraform-locks"
    # encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.10"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.5"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "mlops-platform"
      ManagedBy   = "terraform"
    }
  }
}

# VPC for our cluster
module "vpc" {
  source = "./modules/vpc"

  environment           = var.environment
  vpc_name              = "mlops-platform-vpc"
  vpc_cidr              = var.vpc_cidr
  availability_zones    = var.availability_zones
  private_subnets_cidr  = var.private_subnets_cidr
  public_subnets_cidr   = var.public_subnets_cidr
}

# EKS Cluster
module "eks" {
  source = "./modules/eks"

  environment           = var.environment
  cluster_name          = "mlops-platform-${var.environment}"
  cluster_version       = var.eks_cluster_version
  vpc_id                = module.vpc.vpc_id
  private_subnets_ids   = module.vpc.private_subnets
  public_subnets_ids    = module.vpc.public_subnets
  node_groups           = var.eks_node_groups
  fargate_profiles      = var.eks_fargate_profiles
  eks_managed_node_groups = var.eks_managed_node_groups
}

# S3 buckets for model artifacts and data
module "s3" {
  source = "./modules/s3"

  environment           = var.environment
  model_bucket_name     = "mlops-models-${var.environment}-${var.aws_account_id}"
  data_bucket_name      = "mlops-data-${var.environment}-${var.aws_account_id}"
  log_bucket_name       = "mlops-logs-${var.environment}-${var.aws_account_id}"
}

# DynamoDB for model metadata
module "dynamodb" {
  source = "./modules/dynamodb"

  environment           = var.environment
  model_metadata_table  = "mlops-model-metadata-${var.environment}"
  model_registry_table  = "mlops-model-registry-${var.environment}"
}

# SageMaker resources
module "sagemaker" {
  source = "./modules/sagemaker"

  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  private_subnets_ids   = module.vpc.private_subnets
  model_bucket_name     = module.s3.model_bucket_name
  model_execution_role  = "mlops-sagemaker-execution-${var.environment}"
}

# ECR repositories
module "ecr" {
  source = "./modules/ecr"

  environment           = var.environment
  repository_names      = ["mlops-api", "mlops-training", "mlops-inference"]
}

# Outputs for CI/CD pipeline
output "eks_cluster_name" {
  description = "The name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "ecr_repository_urls" {
  description = "The URLs of the ECR repositories"
  value       = module.ecr.repository_urls
}

output "model_bucket_name" {
  description = "The name of the S3 bucket for models"
  value       = module.s3.model_bucket_name
}

output "kubeconfig_command" {
  description = "Command to get kubeconfig"
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}"
}