import os
import time
import jwt
import json
import statistics
from datetime import datetime, timedelta
from locust import HttpUser, task, between

# Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "test_secret_for_load_tests")

def create_token():
    """Create a JWT token for authentication"""
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    payload = {
        "sub": "load-test-user",
        "exp": expires
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token
# from datetime import timezone

class MLApiUser(HttpUser):
    wait_time = between(1, 5)  # Wait between 1-5 seconds between tasks
    
    def on_start(self):
        self.token = create_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    @task(1)
    def health_check(self):
        self.client.get("/health")
        
    @task(3)
    def predict_small_payload(self):
        payload = {
            "features": [1.2, 3.4, 2.5, 1.8, 5.6]
        }
        self.client.post("/predict", 
                         json=payload,
                         headers=self.headers)
    
    @task(1)
    def predict_large_payload(self):
        # Create a larger payload to test performance with more data
        features = [float(i) * 0.1 for i in range(100)]
        payload = {
            "features": features
        }
        self.client.post("/predict", 
                         json=payload,
                         headers=self.headers)