# Apply infrastructure manifests
kubectl apply -f infrastructure/base/
kubectl apply -f infrastructure/overlays/production/

# Verify all pods are running
kubectl get pods -n mlops