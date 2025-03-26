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

## Security Testing

Security testing is a critical part of the MLOps platform deployment process. This section outlines penetration tests that should be performed after deployment to verify security controls.

### Penetration Testing Framework

The platform should undergo regular penetration testing across all components:

#### Authentication & Authorization Testing

```bash
# Test 1: JWT Token Manipulation
# 1. Get a valid token
TOKEN=$(curl -s -X POST https://api.mlops-platform.com/api/v1/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test_user&password=test_password" | jq -r '.access_token')

# 2. Decode and modify claims (using jwt-cli tool)
# Install: npm install -g jwt-cli
jwt decode $TOKEN
# Manually modify payload in a text editor and save as modified_payload.json

# 3. Forge token with modified payload (test with invalid signature)
FORGED_TOKEN=$(jwt encode --secret "invalid_secret" --alg HS256 modified_payload.json)

# 4. Test with forged token (should be rejected)
curl -s -X GET https://api.mlops-platform.com/api/v1/models \
  -H "Authorization: Bearer $FORGED_TOKEN"



# Test 2: Authorization Bypass
# Try accessing admin resources with regular user token
curl -s -X GET https://api.mlops-platform.com/api/v1/admin/users \
  -H "Authorization: Bearer $USER_TOKEN"

# Expected: 403 Forbidden


# Test 3: SQL Injection Testing
# Test model search endpoint with SQL injection payload
curl -s -X GET "https://api.mlops-platform.com/api/v1/models?name=test'%20OR%201=1%20--" \
  -H "Authorization: Bearer $TOKEN"

# Test user input fields with various injection payloads
curl -s -X POST https://api.mlops-platform.com/api/v1/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "model_id": "1; DROP TABLE models; --",
    "features": [1.0, 2.0, 3.0]
  }'
```

```bash
# Test 4: Rate Limiting Bypass Attempts
# Create script to send multiple requests
for i in {1..100}; do
  curl -s -X GET https://api.mlops-platform.com/api/v1/models \
    -H "Authorization: Bearer $TOKEN" \
    -w "%{http_code}\n" -o /dev/null
  sleep 0.1
done

# Try with different headers to bypass rate limiting
curl -s -X GET https://api.mlops-platform.com/api/v1/models \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Forwarded-For: 1.2.3.4" \
  -H "X-Real-IP: 5.6.7.8"

# Expected: Rate limiting should be enforced regardless of headers


# Test 5: Model Poisoning Attempt
# Attempt to upload a malicious model
curl -s -X POST https://api.mlops-platform.com/api/v1/models \
  -H "Content-Type: multipart/form-data" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "name=malicious_model" \
  -F "model_file=@malicious_model.pkl" \
  -F "description=This is a test model"

# Test 6: Adversarial Input Testing
# Create malicious inputs designed to exploit model vulnerabilities
curl -s -X POST https://api.mlops-platform.com/api/v1/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "model_id": "valid_model_id",
    "features": [1e9, -1e9, null, "string_instead_of_number"]
  }'

# Expected: Input validation should reject invalid types and ranges
```

```bash
# Test 7: Kubernetes Security Assessment
# Use kube-bench to check against CIS benchmarks
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml
kubectl logs -f job.kube-bench

# Test 8: Network Policy Verification
# Try to access internal services from unauthorized pods
kubectl run test-pod --image=busybox -n default -- sleep 3600
kubectl exec -it test-pod -n default -- wget -T 5 http://redis.mlops.svc.cluster.local:6379
# Expected: Connection timeout or refused

# Test 9: Secrets Management
# Check for hardcoded secrets in ConfigMaps
kubectl get configmaps -A -o yaml | grep -i "password\|secret\|key\|token"
# Expected: No secrets in plaintext


# Test 10: Unauthorized Access to Monitoring
# Try accessing Prometheus without authentication
curl -s http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query?query=up

# Test 11: Check for sensitive data in logs
kubectl logs deployment/mlops-api -n mlops | grep -i "password\|secret\|key\|token"
# Expected: No sensitive data in logs
```
