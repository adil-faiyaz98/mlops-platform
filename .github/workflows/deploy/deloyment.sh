#!/bin/bash
# Local deployment script for testing deployment flow

set -e

# Environment selection with default
ENVIRONMENT=${1:-development}
echo "Deploying to $ENVIRONMENT environment"

# Define variables based on environment
if [ "$ENVIRONMENT" == "production" ]; then
    echo "Warning: You are deploying to PRODUCTION!"
    echo "Press Ctrl+C to cancel, or Enter to continue..."
    read
    REPLICAS=3
    MIN_REPLICAS=2
    MAX_REPLICAS=10
    CPU_LIMIT="1000m"
    MEMORY_LIMIT="1024Mi"
    NAMESPACE="mlops-prod"
elif [ "$ENVIRONMENT" == "staging" ]; then
    REPLICAS=2
    MIN_REPLICAS=1
    MAX_REPLICAS=5
    CPU_LIMIT="500m"
    MEMORY_LIMIT="512Mi"
    NAMESPACE="mlops-staging"
else
    REPLICAS=1
    MIN_REPLICAS=1
    MAX_REPLICAS=3
    CPU_LIMIT="200m"
    MEMORY_LIMIT="256Mi"
    NAMESPACE="mlops-dev"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build Docker image
echo "Building Docker image..."
docker build -t mlops-api:latest .

# Check if kind is installed
if ! command -v kind &> /dev/null; then
    echo "kind is not installed. Please install it first: https://kind.sigs.k8s.io/docs/user/quick-start/"
    exit 1
fi

# Check if cluster exists, create if not
if ! kind get clusters | grep -q "mlops"; then
    echo "Creating kind cluster..."
    kind create cluster --name mlops --config infrastructure/kind/kind-config.yaml
fi

# Switch context to kind cluster
kubectl config use-context kind-mlops

# Load Docker image into kind
echo "Loading Docker image into kind cluster..."
kind load docker-image mlops-api:latest --name mlops

# Create namespace if it doesn't exist
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo "Creating namespace $NAMESPACE..."
    kubectl create namespace "$NAMESPACE"
fi

# Deploy ConfigMap and Secrets
echo "Deploying ConfigMap and Secrets..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: mlops-config
  namespace: $NAMESPACE
data:
  ENVIRONMENT: "$ENVIRONMENT"
  LOG_LEVEL: "INFO"
EOF

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: mlops-secrets
  namespace: $NAMESPACE
type: Opaque
stringData:
  JWT_SECRET_KEY: "dev-secret-not-for-production"
  REDIS_PASSWORD: "dev-password"
EOF

# Deploy Redis
echo "Deploying Redis..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: $NAMESPACE
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: $NAMESPACE
spec:
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:6
        ports:
        - containerPort: 6379
EOF

# Deploy the API
echo "Deploying MLOps API..."
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlops-api
  namespace: $NAMESPACE
spec:
  replicas: $REPLICAS
  selector:
    matchLabels:
      app: mlops-api
  template:
    metadata:
      labels:
        app: mlops-api
    spec:
      containers:
      - name: api
        image: mlops-api:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "redis"
        - name: ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: mlops-config
              key: ENVIRONMENT
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: mlops-config
              key: LOG_LEVEL
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: mlops-secrets
              key: JWT_SECRET_KEY
        resources:
          requests:
            cpu: "100m"
            memory: "128Mi"
          limits:
            cpu: "$CPU_LIMIT"
            memory: "$MEMORY_LIMIT"
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 20
EOF

# Deploy the API Service
echo "Deploying API Service..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: mlops-api
  namespace: $NAMESPACE
spec:
  selector:
    app: mlops-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
EOF

# Deploy Ingress
echo "Deploying Ingress..."
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mlops-ingress
  namespace: $NAMESPACE
spec:
  rules:
  - host: mlops.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mlops-api
            port:
              number: 80
EOF

# Install Nginx Ingress Controller if not already installed
if ! kubectl get deployment -n ingress-nginx ingress-nginx-controller &> /dev/null; then
    echo "Installing NGINX Ingress Controller..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/kind/deploy.yaml
    
    echo "Waiting for Ingress controller to be ready..."
    kubectl wait --namespace ingress-nginx \
      --for=condition=ready pod \
      --selector=app.kubernetes.io/component=controller \
      --timeout=90s
fi

# Wait for deployment to be ready
echo "Waiting for deployment to be ready..."
kubectl rollout status deployment/mlops-api -n $NAMESPACE --timeout=60s

# Port-forward the service for easy access
echo "Setting up port-forward to the service..."
kubectl port-forward -n $NAMESPACE svc/mlops-api 8000:80 &
PORT_FORWARD_PID=$!

echo ""
echo "======================================================"
echo "MLOps Platform deployed successfully to $ENVIRONMENT!"
echo "Access the API at: http://localhost:8000/api/v1/"
echo "Access the docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop port-forwarding and exit"
echo "======================================================"

# Wait for Ctrl+C
trap "kill $PORT_FORWARD_PID; echo 'Port-forwarding stopped'" INT
wait