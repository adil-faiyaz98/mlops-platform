import pytest
from fastapi.testclient import TestClient
from src.api.app import app #Make sure app.py imports there.
import json
import os
from unittest.mock import patch, MagicMock
from fastapi import status
from fastapi.security import OAuth2PasswordBearer

client = TestClient(app)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
JWT_SECRET = os.environ.get("JWT_SECRET", "your-insecure-jwt-secret")
FAKE_TOKEN = "FakeToken"

# Mock the model loading
@pytest.fixture(autouse=True)
def mock_model():
    with patch('src.api.app.joblib.load') as mock_load:  # Adjust path
        mock_load.return_value = MockModel()
        yield

class MockModel:
    def predict(self, data): # For example it just get the top sum.
        if isinstance(data, pd.DataFrame):
          data = data.values
        return [sum(data[0])] # Just a dummy prediction,

# Make sure that the tests will return right results
@pytest.fixture()
def set_env():
    os.environ["S3_BUCKET"] = "test-bucket"  # Simulate environment variables
    os.environ["FEATURE_NAMES"] = "feature1,feature2,feature3"
    yield

@pytest.fixture
def test_config(set_env):
  # Config loading
  from src.utils.config import Config
  config = Config()
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_token_endpoint_valid_credentials():
    # Test username, and password, check token for access
    data = {"username": "testuser", "password": "testpassword"}
    response = client.post("/token", data=data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_token_endpoint_invalid_credentials():
    #Check If wrong password or username
    data = {"username": "testuser", "password": "wrongpassword"}
    response = client.post("/token", data=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED #Make sure it checks it to be auth.
    assert "detail" in response.json()

def test_prediction_endpoint_valid_request(test_config): # Check If Valid
    #Get Token from username.
    data = {"username": "testuser", "password": "testpassword"}
    token_response = client.post("/token", data=data)
    token_json = token_response.json()
    access_token = token_json["access_token"]

    #Set valid data and test, you want to see if valid or not.

    payload = {"feature1": 1.0, "feature2": 2.0, "feature3": 3.0}
    headers = {"Authorization": f"Bearer {access_token}"} #Load Key to use.
    response = client.post("/predict", json=payload, headers=headers) #Load up with test.
    assert response.status_code == 200
    assert "prediction" in response.json() #Load that value
    assert  response.json() == {'prediction': 6.0, 'model_version': "my-model"}

def test_prediction_endpoint_invalid_token(test_config): #Load it.
    # Use to make sure the code is tested to give a right error code.
    payload = {"feature1": 1.0, "feature2": 2.0, "feature3": 3.0} #Load with Fake

    #Bad key, error code expected.
    headers = {"Authorization": "Bearer invalidtoken"} #Bad KEY,
    response = client.post("/predict", json=payload, headers=headers)

    #Make sure Authentication, make sure right auth_code error.
    assert response.status_code == status.HTTP_401_UNAUTHORIZED #Make sure correct

def test_prediction_endpoint_no_token(test_config):
    # Test is to ensure that a key is placed in, if it can run or get a failure.

    # Test without Token.
    payload = {"feature1": 1.0, "feature2": 2.0, "feature3": 3.0} #Fake Data.
    response = client.post("/predict", json=payload) #Post Data (NO KEY)

    #No key will be a Authorization issue.
    assert response.status_code == status.HTTP_401_UNAUTHORIZED #Need that key!