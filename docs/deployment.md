# MLOps Platform Deployment Guide

This guide provides step-by-step instructions for deploying the MLOps Platform to different environments.

## Prerequisites

Before deployment, ensure you have:

1. AWS CLI configured with appropriate permissions
2. kubectl installed and configured
3. Terraform 1.0+ installed
4. Docker installed
5. Access to container registry (AWS ECR, DockerHub, etc.)

## Deployment Options

The MLOps Platform can be deployed in the following ways:

1. **AWS EKS Deployment** - Production ready, scalable deployment on AWS EKS
2. **Local Kubernetes** - Development/testing deployment on local K8s (kind, minikube)
3. **Docker Compose** - Simple deployment for development and testing

## Option 1: AWS EKS Deployment

### Step 1: Deploy Infrastructure with Terraform

```bash
# Navigate to terraform directory
cd infrastructure/terraform/aws

# Initialize Terraform
terraform init

# Review the plan
terraform plan -var-file=environments/prod.tfvars -out=tfplan

# Apply the plan
terraform apply tfplan

# Get kubeconfig
aws eks update-kubeconfig --name mlops-platform-cluster --region us-west-2
```

### Step 2: Build and Push Docker Images

```bash
# Set environment variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-west-2
export ECR_REPO=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mlops-api

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPO

# Build and tag image
docker build -t mlops-api:latest .
docker tag mlops-api:latest $ECR_REPO:latest

# Push image
docker push $ECR_REPO:latest
```

### Step 3: Deploy to Kubernetes

```yaml
# Create namespace if it doesn't exist
kubectl create namespace mlops

# Apply ConfigMaps and Secrets
kubectl apply -f infrastructure/kubernetes/configmaps/
kubectl apply -f infrastructure/kubernetes/secrets/

# Deploy Redis
kubectl apply -f infrastructure/kubernetes/redis/

# Deploy the API
kubectl apply -f infrastructure/kubernetes/api-deployment.yaml
kubectl apply -f infrastructure/kubernetes/api-service.yaml

# Check deployment status
kubectl get pods -n mlops
kubectl get svc -n mlops
```

### Step 4: Configure DNS and Ingress

```yaml
# Apply ingress resources
kubectl apply -f infrastructure/kubernetes/ingress.yaml

# Get the load balancer endpoint
export LB_ENDPOINT=$(kubectl get ingress mlops-ingress -n mlops -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "API is accessible at: https://$LB_ENDPOINT"
```

## Option 2: Local Kubernetes Deployment

### Step 1: Create a Kind cluster

```bash
# Create the kind cluster with ingress support
kind create cluster --name mlops --config infrastructure/kind/kind-config.yaml

# Build the Docker image locally
docker build -t mlops-api:local .

# Load the image into kind
kind load docker-image mlops-api:local --name mlops
```

### Step 2: Deploy to local cluster

```yaml
# Create namespace
kubectl create namespace mlops

# Apply configurations
kubectl apply -f infrastructure/kind/configmaps/
kubectl apply -f infrastructure/kind/secrets/
kubectl apply -f infrastructure/kind/redis.yaml
kubectl apply -f infrastructure/kind/api-deployment.yaml
kubectl apply -f infrastructure/kind/api-service.yaml
kubectl apply -f infrastructure/kind/ingress.yaml

# Install ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/kind/deploy.yaml

# Wait for ingress controller
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s

# Access the API
echo "API is accessible at: http://localhost/api/v1/"
```

## Option 3: Docker Compose Deployment

### Step 1: Create environment variables

```yaml
# Copy .env.example to .env
cp .env.example .env

# Edit .env file with appropriate values
nano .env
```

### Step 2: Start the services

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api

# API is accessible at http://localhost:8000/api/v1/



# Check health endpoint
curl http://<endpoint>/api/v1/health

# Expected response:
# {"status":"healthy","timestamp":"2023-03-25T12:34:56Z","environment":"production","version":"1.0.0"}
```
