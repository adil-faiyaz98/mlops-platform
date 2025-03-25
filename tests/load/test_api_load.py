# tests/load/test_api_load.py

import os
import json
from datetime import datetime, timedelta
import jwt
from locust import HttpUser, task, between

class MLApiUser(HttpUser):
    """
    Base class for load testing the ML API.  This contains common
    setup and task definitions.
    """

    wait_time = between(1, 5) # User wait time between tasks (1-5 seconds)
    host = os.getenv("API_HOST", "http://localhost:8080") # Set a default host
    headers = {"Content-Type": "application/json"} # Standard headers

    def on_start(self):
        """
        This method is called when a Locust user starts its run.
        You can use it to generate a JWT token and set it in the headers.
        """

        # Generate a simple payload for JWT - should match your requirements
        payload = {
            "user_id": "load_tester",
            "exp": datetime.utcnow() + timedelta(minutes=30) # expires in 30 mins
        }

        #  **SECURITY WARNING:  Replace 'secret' with a real secret key,
        #  ideally loaded from a secure secret store (e.g., environment variable)
        #  Do *not* hardcode secrets in production.**
        jwt_token = jwt.encode(payload, "secret", algorithm="HS256")
        self.headers["Authorization"] = f"Bearer {jwt_token}"


    @task(10) # Relatively frequent task
    def predict_with_synthetic_data(self):
        """Test the /predict endpoint with synthetic data"""
        features = [float(i) / 10 for i in range(20)]  # Example synthetic data
        payload = {"features": features}

        self.client.post("/predict",
                         json=payload,
                         headers=self.headers,
                         name="predict-synthetic")

    @task(3) # Less frequent task
    def get_health_check(self):
        """Check the /health endpoint"""
        self.client.get("/health", name="health_check")