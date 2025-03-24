import os
import pytest
import requests
import jwt
import time
from datetime import datetime, timedelta

# Configuration for tests
API_URL = os.environ.get("API_URL", "https://gcpfunctionapi-abcdefgh-uc.a.run.app")
JWT_SECRET = os.environ.get("JWT_SECRET", "test_secret_for_integration_tests")

def create_token():
    """Create a JWT token for authentication"""
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {
        "sub": "test-user",
        "exp": expires
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token
# from datetime import timezone

@pytest.fixture
def auth_headers():
    """Fixture to provide authentication headers"""
    token = create_token()
    return {"Authorization": f"Bearer {token}"}

def test_health_endpoint():
    """Test the health endpoint"""
    response = requests.get(f"{API_URL}/health")
    assert response.status_code == 200
    assert response.json().get("status") == "healthy"

def test_prediction_endpoint(auth_headers):
    """Test the prediction endpoint with authentication"""
    test_data = {
        "features": [1.2, 3.4, 2.5, 1.8, 5.6]
    }
    
    response = requests.post(
        f"{API_URL}/predict",
        json=test_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert "prediction" in response.json()

def test_invalid_auth():
    """Test that unauthorized requests are rejected"""
    test_data = {
        "features": [1.2, 3.4, 2.5, 1.8, 5.6]
    }
    
    # No auth header
    response = requests.post(
        f"{API_URL}/predict",
        json=test_data
    )
    assert response.status_code == 401

    # Invalid token
    response = requests.post(
        f"{API_URL}/predict",
        json=test_data,
        headers={"Authorization": "Bearer invalid-token"}
    )
    assert response.status_code == 401