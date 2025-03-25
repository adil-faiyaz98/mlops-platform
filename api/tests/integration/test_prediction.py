from fastapi.testclient import TestClient
import pytest
from api.app.main import app # Your FastAPI App

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client

def test_prediction_endpoint(test_client):
    # Assuming you have authentication setup, get a token here
    headers = {"Authorization": "Bearer YOUR_TEST_TOKEN"}  # Replace with a valid token

    # Make request
    response = test_client.post(
        "/api/v1/predict",
        headers=headers,
        json={"feature1": 1.0, "feature2": 2.0, "feature3": 3.0}
    )
    assert response.status_code == 200
    data = response.json()

    # Verify data
    assert "prediction" in data
    # Test values.
    assert type(data["prediction"]) is float