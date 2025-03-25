from fastapi.testclient import TestClient
from api.app.main import app # Make sure you know it's there!

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}