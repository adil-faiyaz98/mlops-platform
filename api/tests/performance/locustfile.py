from locust import HttpUser, task, between

class MLApiUser(HttpUser):
    """
    Locust test for simulating API load testing
    
    To run:
    locust -f locustfile.py --host=http://your-api-url
    """
    
    # Wait between 1 and 5 seconds between tasks
    wait_time = between(1, 5)
    
    def on_start(self):
        """Set up the user"""
        # Authentication if needed
        pass
        
    @task(3)
    def health_check(self):
        """Health check endpoint - high frequency"""
        self.client.get("/api/v1/health")
    
    @task(10)
    def predict(self):
        """Prediction endpoint - most common operation"""
        payload = {
            "inputs": [[1.0, 2.0, 3.0, 4.0]],
            "parameters": {
                "threshold": 0.5,
                "explain": False
            }
        }
        self.client.post(
            "/api/v1/predict",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
    
    @task(1)
    def batch_predict(self):
        """Batch prediction endpoint - less frequent"""
        payload = {
            "inputs": [
                [1.0, 2.0, 3.0, 4.0],
                [2.0, 3.0, 4.0, 5.0],
                [3.0, 4.0, 5.0, 6.0]
            ],
            "parameters": {
                "batch_size": 2
            }
        }
        self.client.post(
            "/api/v1/batch-predict",
            json=payload,
            headers={"Content-Type": "application/json"}
        )