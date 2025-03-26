import json
import random
import time
import uuid
from typing import Dict, List
from locust import HttpUser, task, between

class MLApiUser(HttpUser):
    """
    Locust user for testing the ML API under load
    """
    # Wait 1-5 seconds between tasks
    wait_time = between(1, 5)
    
    def on_start(self):
        """Initialize user session"""
        # Get auth token for authenticated endpoints
        # In a real test, include proper authentication
        self.headers = {
            "Content-Type": "application/json",
            "X-Request-ID": str(uuid.uuid4())
        }
        
        # Pre-generate some realistic feature vectors
        self.feature_vectors = [
            [random.uniform(-10, 10) for _ in range(10)]
            for _ in range(50)
        ]
    
    @task(10)
    def predict_endpoint(self):
        """Test the main prediction endpoint"""
        # Select a random feature vector
        features = random.choice(self.feature_vectors)
        
        # Add small variations to simulate real-world usage
        features = [f + random.uniform(-0.1, 0.1) for f in features]
        
        # Create request payload
        payload = {
            "features": features,
            "model_id": "test-model"
        }
        
        # Make request with timing
        start_time = time.time()
        with self.client.post(
            "/api/v1/predict",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            duration = time.time() - start_time
            
            # Validate response
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "prediction" in data and "probability" in data:
                        response.success()
                    else:
                        response.failure(f"Invalid response format: {data}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 429:
                # Rate limit - mark as success but log it
                response.success()
                self.environment.events.request_success.fire(
                    request_type="POST",
                    name="/api/v1/predict (rate-limited)",
                    response_time=duration,
                    response_length=len(response.text)
                )
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(3)
    def batch_predict_endpoint(self):
        """Test the batch prediction endpoint"""
        # Select 5-20 random feature vectors
        batch_size = random.randint(5, 20)
        inputs = random.sample(self.feature_vectors, batch_size)
        
        # Create request payload
        payload = {
            "inputs": inputs,
            "model_id": "test-model",
            "batch_size": 5  # Process in batches of 5
        }
        
        # Make request with timing
        start_time = time.time()
        with self.client.post(
            "/api/v1/batch-predict",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            duration = time.time() - start_time
            
            # Validate response
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, list) and len(data) == batch_size:
                        response.success()
                    else:
                        response.failure(f"Invalid response format or length: {data}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Test the health check endpoint"""
        with self.client.get(
            "/api/v1/health",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "status" in data:
                        response.success()
                    else:
                        response.failure("Invalid health check response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Health check failed: {response.status_code}")

# Run with: locust -f locustfile.py --host http://your-api-host