import pytest
import json
import time
from fastapi.testclient import TestClient
import os
import boto3
from moto import mock_dynamodb, mock_s3
from unittest.mock import patch

from api.app.main import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture
def mock_aws_services(aws_credentials):
    with mock_dynamodb(), mock_s3():
        # Set up DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.create_table(
            TableName='mlops-model-metadata',
            KeySchema=[{'AttributeName': 'model_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'model_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table.put_item(Item={
            'model_id': 'test-model',
            'version': '1',
            'created_at': '2023-01-01T00:00:00Z',
            'framework': 'sklearn',
            's3_path': 's3://bucket/models/test-model/model.pkl'
        })
        
        # Set up S3
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket='bucket')
        s3.put_object(
            Bucket='bucket',
            Key='models/test-model/model.pkl',
            Body=b'mock model data'
        )
        
        yield

@patch('api.services.model_loader.ModelLoader.load_model_from_s3')
def test_prediction_api_flow(mock_load_model, client, mock_aws_services):
    """Test the complete prediction API flow"""
    # Mock the model to return a simple prediction
    def mock_predict(features):
        return {"prediction": 1, "probability": 0.95}
    
    mock_load_model.return_value = mock_predict
    
    # Test prediction endpoint
    response = client.post(
        "/api/v1/predict",
        json={"model_id": "test-model", "features": [1.0, 2.0, 3.0, 4.0]}
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "probability" in data
    assert data["prediction"] == 1
    assert data["probability"] == 0.95

@patch('api.services.model_loader.ModelLoader.load_model_from_s3')
def test_batch_prediction_api_flow(mock_load_model, client, mock_aws_services):
    """Test the batch prediction API flow"""
    # Mock the model to return different predictions based on the first feature
    def mock_predict(features):
        if features[0] < 5.0:
            return {"prediction": 0, "probability": 0.8}
        else:
            return {"prediction": 1, "probability": 0.9}
    
    mock_load_model.return_value = mock_predict
    
    # Test batch prediction endpoint
    response = client.post(
        "/api/v1/batch-predict",
        json={
            "model_id": "test-model", 
            "inputs": [
                [1.0, 2.0, 3.0, 4.0],
                [5.0, 6.0, 7.0, 8.0],
                [9.0, 10.0, 11.0, 12.0]
            ]
        }
    )
    
    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["prediction"] == 0
    assert data[0]["probability"] == 0.8
    assert data[1]["prediction"] == 1
    assert data[1]["probability"] == 0.9
    assert data[2]["prediction"] == 1
    assert data[2]["probability"] == 0.9

def test_health_endpoint(client):
    """Test the health check endpoint"""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "uptime" in data

def test_model_not_found(client, mock_aws_services):
    """Test error handling for non-existent model"""
    response = client.post(
        "/api/v1/predict",
        json={"model_id": "non-existent-model", "features": [1.0, 2.0, 3.0, 4.0]}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

def test_invalid_input(client):
    """Test validation for invalid input"""
    # Missing required field
    response = client.post(
        "/api/v1/predict",
        json={"features": [1.0, 2.0, 3.0, 4.0]}  # Missing model_id
    )
    
    assert response.status_code == 422
    
    # Invalid feature type
    response = client.post(
        "/api/v1/predict",
        json={"model_id": "test-model", "features": ["invalid", "features"]}
    )
    
    assert response.status_code == 422