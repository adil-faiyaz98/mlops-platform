terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"  # Specify a specific version
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"  # Specify a specific version
    }
  }
}

# Configure the Google Cloud provider
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Configure the AWS provider
provider "aws" {
  region = var.aws_region
}