# Troubleshooting Scenarios

## 1. API Performance Degradation

```bash
- Check resource utilization
kubectl top pods -n mlops
```

## 2. Check request latency metrics

```bash
curl -s http://<prometheus-url>/api/v1/query?query=histogram_quantile(0.95%2Csum(rate(http_request_duration_seconds_bucket%7Bjob%3D%22mlops-api%22%7D%5B5m%5D))by(le%2Croute))
```

## 3. Check database query performance

```bash
# Get slow query logs
kubectl exec -it $(kubectl get pod -l app=postgres -n mlops -o jsonpath='{.items[0].metadata.name}') -n mlops -- psql -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10"
```

## 4. Check network issues

```bash
# Test network latency between components
kubectl exec -it deployment/mlops-api -n mlops -- ping -c 5 redis.mlops.svc.cluster.local
```

## 5. Remediation Options

### Scale Horizontally

```bash
kubectl scale deployment/mlops-api -n mlops --replicas=5
```

### Enable/Optimize Caching

```bash
# Update configmap with caching settings
kubectl edit configmap mlops-api-config -n mlops
```

### Restart Problematic pods

```bash
kubectl delete pod <pod-name> -n mlops
kubectl rollout restart deployment/mlops-api -n mlops
```

## Model Serving Errors

### 1. Check Model loading logs

```bash
kubectl logs -l app=mlops-api -n mlops | grep "model.*load"
```

### 2. Verify model files in S3

```bash
aws s3 ls s3://mlops-models/models/<model-id>/
```

### 3. Check Model metadata

```bash
aws dynamodb get-item --table-name mlops-model-metadata --key '{"model_id": {"S": "<model-id>"}}'
```

### 4. Remediation options

```bash
# Rollback to previous model version
kubectl rollout undo deployment/mlops-api -n mlops


# Update model version in configmap
kubectl edit configmap mlops-api-config -n mlops
# Restart pods to pick up new config
kubectl rollout restart deployment/mlops-api -n mlops
```
