# Automated Cloud Deployment Guide

This guide explains how to use the automated cloud deployment features of the MLOps platform.

## Overview

The MLOps platform includes a full CI/CD pipeline for automated deployment to AWS, with:

- Infrastructure as Code (Terraform)
- CI/CD pipeline (GitHub Actions)
- Multi-environment support
- Cost monitoring and optimization

## Prerequisites

Before you begin, you need:

1. **AWS Account** with appropriate permissions
2. **GitHub repository** configured with secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_ACCOUNT_ID`
3. **S3 bucket** for Terraform state
4. **DynamoDB table** for Terraform state locking

## Getting Started

### 1. Initialize Infrastructure

The first time you deploy, you need to create the Terraform state resources:

```bash
# Create S3 bucket for state
aws s3api create-bucket \
  --bucket mlops-terraform-state-${AWS_ACCOUNT_ID} \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket mlops-terraform-state-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for locks
aws dynamodb create-table \
  --table-name mlops-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1


# Get kubeconfig
aws eks update-kubeconfig --name mlops-platform-staging --region us-east-1

# Check resources
kubectl get pods -n mlops-staging
kubectl get services -n mlops-staging
kubectl get deployments -n mlops-staging
```

## 2. Tag Release Version

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 3. Rollback Procedure

```bash
# Immediate rollback via Kubernetes
kubectl rollout undo deployment/mlops-api -n mlops-production

# Revert to previous Terraform state version / Apply specific version
terraform workspace select production
terraform apply -target=module.eks -var-file=environments/production.tfvars
```

# Troubleshooting

## Terraform state lock issue

```bash
# Force unlock
terraform force-unlock LOCK_ID
```

## ECR push failure

```sh
Check IAM permissions
Ensure AWS credentials are valid
```

## EKS Connectivity Issues

```bash
# Update kubeconfig
aws eks update-kubeconfig --name mlops-platform-staging --region us-east-1

# Check AWS auth config
kubectl describe configmap -n kube-system aws-auth
```
