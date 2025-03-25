import pytest
import json
import time
import numpy as np
from fastapi.testclient import TestClient
import os
import boto3
from moto import mock_aws
from unittest.mock import patch

from api.app.main import app
from api.utils.config import Config

# Create test client
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for Moto"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@mock_aws
def test_prediction_flow_end_to_end(client, mock_aws_credentials):
    """Test the complete prediction flow from request to response"""
    
    # Create S3 bucket and upload mock model
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="mlops-models")
    
    # Upload a simple "model" file (just for testing)
    s3.put_object(
        Bucket="mlops-models",
        Key="models/model-1/model.pkl",
        Body=b"mock model data"
    )
    
    # Create DynamoDB table for model metadata
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.create_table(
        TableName="mlops-model-metadata",
        KeySchema=[
            {"AttributeName": "model_id", "KeyType": "HASH"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "model_id", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    
    # Add model metadata
    table.put_item(
        Item={
            "model_id": "model-1",
            "version": "1",
            "created_at": "2023-01-01T00:00:00Z",
            "framework": "sklearn",
            "path": "s3://mlops-models/models/model-1/model.pkl",
            "input_schema": {
                "type": "array",
                "items": {"type": "number"}
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "prediction": {"type": "number"},
                    "probability": {"type": "number"}
                }
            }
        }
    )
    
    # Mock the model loading and prediction
    with patch("api.services.model_registry.ModelRegistry.load_model") as mock_load:
        # Create a mock model that always predicts 1 with 0.9 probability
        mock_model = lambda x: {"prediction": 1, "probability": 0.9}
        mock_load.return_value = mock_model
        
        # Make prediction request
        response = client.post(
            "/api/v1/predict",
            json={
                "features": [1.0, 2.0, 3.0, 4.0],
                "model_id": "model-1"
            }
        )
        
        # Check response
        assert response.status_code == 200
        result = response.json()
        assert "prediction" in result
        assert "probability" in result
        assert result["prediction"] == 1
        assert result["probability"] == 0.9
        
        # Check proper AWS calls were made
        calls = mock_load.call_args_list
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert args[0] == "model-1"

@mock_aws
def test_batch_prediction_flow(client, mock_aws_credentials):
    """Test the batch prediction flow"""
    
    # Set up AWS resources (same as previous test)
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="mlops-models")
    s3.put_object(
        Bucket="mlops-models",
        Key="models/model-1/model.pkl",
        Body=b"mock model data"
    )
    
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.create_table(
        TableName="mlops-model-metadata",
        KeySchema=[
            {"AttributeName": "model_id", "KeyType": "HASH"}
        ],
        AttributeDefinitions=[
            {"AttributeName": "model_id", "AttributeType": "S"}
        ],
        BillingMode="PAY_PER_REQUEST"
    )
    
    table.put_item(
        Item={
            "model_id": "model-1",
            "version": "1",
            "created_at": "2023-01-01T00:00:00Z",
            "framework": "sklearn",
            "path": "s3://mlops-models/models/model-1/model.pkl",
            "input_schema": {
                "type": "array",
                "items": {"type": "number"}
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "prediction": {"type": "number"},
                    "probability": {"type": "number"}
                }
            }
        }
    )
    
    # Create test data with multiple inputs
    test_inputs = [
        [1.0, 2.0, 3.0, 4.0],
        [5.0, 6.0, 7.0, 8.0],
        [9.0, 10.0, 11.0, 12.0]
    ]
    
    # Mock model loading and batch prediction
    with patch("api.services.model_registry.ModelRegistry.load_model") as mock_load:
        # Create mock model that returns different values based on input
        def mock_model(features):
            if features[0] == 1.0:
                return {"prediction": 0, "probability": 0.8}
            elif features[0] == 5.0:
                return {"prediction": 1, "probability": 0.9}
            else:
                return {"prediction": 1, "probability": 0.7}
                
        mock_load.return_value = mock_model
        
        # Make batch prediction request
        response = client.post(
            "/api/v1/batch-predict",
            json={
                "inputs": test_inputs,
                "model_id": "model-1",
                "batch_size": 2  # Process in batches of 2
            }
        )
        
        # Check response
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 3
        
        # Check results match expected values
        assert results[0]["prediction"] == 0
        assert results[0]["probability"] == 0.8
        assert results[1]["prediction"] == 1
        assert results[1]["probability"] == 0.9
        assert results[2]["prediction"] == 1
        assert results[2]["probability"] == 0.7