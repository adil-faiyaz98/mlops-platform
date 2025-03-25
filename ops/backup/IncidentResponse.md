# MLOps Platform Incident Response Runbook

## Overview

This runbook provides step-by-step procedures for responding to incidents in the MLOps platform.

## Incident Severity Levels

| Level | Description                                    | Response Time | Communication Frequency |
| ----- | ---------------------------------------------- | ------------- | ----------------------- |
| P1    | Service outage affecting all users             | Immediate     | Every 30 minutes        |
| P2    | Partial service outage or degraded performance | < 30 minutes  | Every hour              |
| P3    | Non-critical component failure                 | < 2 hours     | Daily                   |
| P4    | Minor issue not affecting users                | < 24 hours    | As needed               |

## Alert Response Procedures

### High API Error Rate Alert

**Triggered when**: Error rate exceeds 5% for 5 minutes

**Steps**:

1. **Assess the situation**

   ```bash
   # Check Pod status
   kubectl get pods -n mlops

   # Check container logs for errors
   kubectl logs -l app=mlops-api -n mlops --tail=100

   # Check API metrics
   curl -s http://<prometheus-url>/api/v1/query?query=sum(rate(http_request_errors_total%7Bjob%3D%22mlops-api%22%7D%5B5m%5D))%20by%20(route)
   ```

2. **Check recent deployments**

   ```bash
   kubectl rollout history deployment/mlops-api -n mlops
   ```

3. **Check downstream dependencies**

   ```bash
   # Health check API
    curl -s http://<api-endpoint>/api/v1/health | jq
   ```

4. **Remediation options**

   - Rollback recent deployment

   ```bash
   kubectl rollout undo deployment/mlops-api -n mlops
   ```

   - Scale up resources

   ```bash
   kubectl scale deployment/mlops-api -n mlops --replicas=5
   ```

   - Restarted affected pods

   ```bash
   kubectl rollout restart deployment/mlops-api -n mlops
   ```

# Circuit Breaker Open Alert

## Triggered when: Circuit breaker for any dependency remains open for > 1 minute

1. **Identify affected dependency**

```bash
# Check which dependency triggered the circuit breaker
curl -s http://<api-endpoint>/api/v1/health | jq '.dependencies'
```

2. **Check dependency health**

- Redis

```bash
kubectl exec -it $(kubectl get pod -l app=redis -n mlops -o jsonpath='{.items[0].metadata.name}') -n mlops -- redis-cli PING
```

- DB

```bash
# Check if database is reachable
kubectl run -it --rm db-check --image=postgres --restart=Never -- psql -h <db-host> -U <user> -c "SELECT 1"
```

3. **Restart dependencies**

```bash
kubectl rollout restart deployment/redis -n mlops

kubectl scale deployment/redis -n mlops --replicas=3

kubectl get networkpolicies -n mlops

# If manual reset is needed (depends on implementation)
curl -X POST http://<api-endpoint>/api/v1/admin/reset-circuits -H "Authorization: Bearer ${TOKEN}"
```
