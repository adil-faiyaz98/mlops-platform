"""
Main Locust configuration file for load testing the ML API.
Run with: locust -f locustfile.py --host=https://your-api-url
"""

import os
import json
from datetime import datetime, timedelta
import jwt
from locust import HttpUser, task, between

# Import the test user class from our load test module
# This allows us to keep our test logic in the tests directory
# but still use the standard locust command
from tests.load.test_api_load import MLApiUser

# Additional configurations that might be needed for specific environments
class ProductionLoadTest(MLApiUser):
    """Extended version of MLApiUser with production-specific configurations"""
    
    # Adjust the wait time for production testing
    wait_time = between(0.5, 3)  
    
    def on_start(self):
        # Call the parent on_start method
        super().on_start()
        
        # Add additional headers or configuration for production tests
        self.headers["X-Environment"] = "production"
        
    @task(5)
    def realistic_payload(self):
        """Test with realistic production-like data"""
        # Load realistic test data from file
        data_path = os.path.join(os.path.dirname(__file__), "tests/data/sample_payload.json")
        
        try:
            with open(data_path, "r") as f:
                sample_data = json.load(f)
                
            self.client.post("/predict", 
                            json=sample_data,
                            headers=self.headers,
                            name="predict-realistic")
        except FileNotFoundError:
            # Fallback to synthetic data if file not found
            features = [float(i) / 10 for i in range(20)]
            payload = {"features": features}
            
            self.client.post("/predict", 
                            json=payload,
                            headers=self.headers,
                            name="predict-synthetic")

# Export both user types so they can be selected when running locust
# Default is MLApiUser, but ProductionLoadTest can be selected with:
# locust -f locustfile.py --host=https://your-api-url ProductionLoadTest