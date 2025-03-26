# Install dependencies
pip install -r security/requirements.txt

# Run the tests
python security/tests/penetration_tests.py \
  --url https://api.mlops-platform.com \
  --token YOUR_AUTH_TOKEN \
  --output security-report.json

# Generate HTML report
python -c "import json, markdown; html=markdown.markdown(open('security-report.md').read()); open('security-report.html', 'w').write(f'<html><body>{html}</body></html>')"



# To manually check for critical vulnerabilities
CRITICAL_VULNS=$(jq '[.vulnerabilities[] | select(.severity == "critical")] | length' security-report.json)
if [ $CRITICAL_VULNS -gt 0 ]; then
  echo "Critical vulnerabilities found! Blocking deployment."
  exit 1
fi


# Update JWT secret with higher entropy
kubectl create secret generic mlops-secrets \
  --from-literal=JWT_SECRET_KEY=$(openssl rand -hex 32) \
  --dry-run=client -o yaml | kubectl apply -f -

# Rotate keys and restart services
kubectl rollout restart deployment/mlops-api -n mlops-production


# Update base image and rebuild
docker build --no-cache -t mlops-api:latest .

# Push and deploy updated image
docker tag mlops-api:latest $ECR_REPOSITORY:latest
docker push $ECR_REPOSITORY:latest
kubectl set image deployment/mlops-api -n mlops-production api=$ECR_REPOSITORY:latest


# Update IAM roles with least privilege
aws iam put-role-policy \
  --role-name mlops-platform-role \
  --policy-name restricted-policy \
  --policy-document file://updated-policy.json

# Update Kubernetes RBAC
kubectl apply -f infrastructure/kubernetes/rbac/least-privilege-roles.yaml

# Force unlock
terraform force-unlock LOCK_ID

# Check IAM permissions
aws ecr get-login-password --region us-east-1

# Ensure AWS credentials are valid
aws sts get-caller-identity


# Update kubeconfig
aws eks update-kubeconfig --name mlops-platform-staging --region us-east-1

# Check AWS auth config
kubectl describe configmap -n kube-system aws-auth