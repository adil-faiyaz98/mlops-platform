# jWT vulnerability test
# Update JWT secret with higher entropy
kubectl create secret generic mlops-secrets --from-literal=JWT_SECRET_KEY=$(openssl rand -hex 32) --dry-run=client -o yaml | kubectl apply -f -

# Rotate keys and restart services
kubectl rollout restart deployment/mlops-api -n mlops-production


# Container Security
# Update base image and rebuild
docker build --no-cache -t mlops-api:latest .

# Push and deploy updated image
docker tag mlops-api:latest $ECR_REPOSITORY:latest
docker push $ECR_REPOSITORY:latest
kubectl set image deployment/mlops-api -n mlops-production api=$ECR_REPOSITORY:latest


# Excessive Permissions
# Update IAM roles with least privilege
aws iam put-role-policy --role-name mlops-platform-role --policy-name restricted-policy --policy-document file://updated-policy.json

# Update Kubernetes RBAC
kubectl apply -f infrastructure/kubernetes/rbac/least-privilege-roles.yaml


