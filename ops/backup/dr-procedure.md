# Disaster Recovery Procedure for MLOps Platform

Complete Environment Recovery
In the event of a complete environment failure:

## 1. Recreate Infrastructure

```bash
cd infrastructure/terraform
terraform init
terraform apply -auto-approve
```

## 2. Restore Kubernetes Resources

```bash
velero restore create --from-backup latest-mlops-daily-backup
```

### 3. Verify Database Connectivity

```bash
kubectl exec -it deployment/mlops-api -- curl -s http://localhost:8080/api/v1/health | jq
```

### 4. Update DNS

```bash
export LOAD_BALANCER_DNS=$(kubectl get svc mlops-api-lb -n mlops -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
export LOAD_BALANCER_HOSTED_ZONE_ID=$(aws elb describe-load-balancers --query 'LoadBalancerDescriptions[?DNSName==`'$LOAD_BALANCER_DNS'`].CanonicalHostedZoneNameID' --output text)
export HOSTED_ZONE_ID=$(aws route53 list-hosted-zones --query 'HostedZones[?Name==`example.com.`].Id' --output text | cut -d'/' -f3)

# Update DNS record
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "api.mlops.example.com",
          "Type": "A",
          "AliasTarget": {
            "HostedZoneId": "'$LOAD_BALANCER_HOSTED_ZONE_ID'",
            "DNSName": "'$LOAD_BALANCER_DNS'",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'
```

# Recovery Testing

## 6.Test Scenarios

```python
import pytest
import requests
import time
from fastapi.testclient import TestClient
import json
from unittest.mock import patch, Mock

from api.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def redis_mock():
    with patch("api.cache.enhanced_redis_cache.redis.Redis") as mock:
        # Configure the mock to fail after a few calls
        real_ping = Mock()
        real_get = Mock()

        # First calls succeed
        def side_effect_ping(*args, **kwargs):
            if real_ping.call_count < 3:  # First 3 calls succeed
                return True
            else:
                raise ConnectionError("Redis connection failed")
        real_ping.side_effect = side_effect_ping

        # Get also fails after a few calls
        def side_effect_get(*args, **kwargs):
            if real_get.call_count < 3:  # First 3 calls succeed
                return None
            else:
                raise ConnectionError("Redis connection failed")
        real_get.side_effect = side_effect_get

        instance = mock.return_value
        instance.ping = real_ping
        instance.get = real_get
        yield mock

def test_circuit_breaker_opens_after_failures(client, redis_mock):
    """Test that circuit breaker opens after multiple failures"""

    # Cache should be available initially
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["dependencies"]["cache"]["status"] == "ok"

    # Make multiple requests to trigger circuit breaker
    for _ in range(5):
        response = client.post("/api/v1/predict",
                              json={"features": [1.0, 2.0, 3.0, 4.0]})

    # Check health again - cache should now be in degraded or unavailable state
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["dependencies"]["cache"]["status"] in ["degraded", "unavailable"]

    # API should still work without cache
    response = client.post("/api/v1/predict",
                          json={"features": [1.0, 2.0, 3.0, 4.0]})
    assert response.status_code == 200

@pytest.mark.slow
def test_circuit_breaker_resets_after_timeout(client, redis_mock):
    """Test that circuit breaker resets after timeout period"""

    # Configure Redis mock to fail initially, then recover
    instance = redis_mock.return_value
    real_ping = Mock()

    def side_effect_ping(*args, **kwargs):
        # Fail for the first 5 calls, then succeed
        if real_ping.call_count < 5:
            raise ConnectionError("Redis connection failed")
        return True

    real_ping.side_effect = side_effect_ping
    instance.ping = real_ping

    # Make requests to trigger circuit breaker
    for _ in range(5):
        client.post("/api/v1/predict", json={"features": [1.0, 2.0, 3.0, 4.0]})

    # Verify circuit is open
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["dependencies"]["cache"]["status"] in ["degraded", "unavailable"]

    # Wait for circuit breaker timeout (adjust based on your config)
    # In a real test, you would mock time.time() instead of actually waiting
    time.sleep(10)

    # Make another request, circuit should attempt to reset
    client.post("/api/v1/predict", json={"features": [1.0, 2.0, 3.0, 4.0]})

    # Verify circuit is closed
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["dependencies"]["cache"]["status"] == "ok"
```
