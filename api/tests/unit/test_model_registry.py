import pytest
import boto3
import json
from unittest.mock import patch, MagicMock
from moto import mock_dynamodb, mock_s3

from api.services.model_registry import ModelRegistry
from api.exceptions.model_exceptions import ModelNotFoundError, InvalidModelError

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture
def dynamodb_table(aws_credentials):
    with mock_dynamodb():
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.create_table(
            TableName='mlops-model-metadata',
            KeySchema=[{'AttributeName': 'model_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'model_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test data
        table.put_item(Item={
            'model_id': 'test-model',
            'version': '1',
            'created_at': '2023-01-01T00:00:00Z',
            'framework': 'sklearn',
            's3_path': 's3://bucket/models/test-model/model.pkl'
        })
        
        yield table

@pytest.fixture
def s3_bucket(aws_credentials):
    with mock_s3():
        # Create mock S3 bucket and object
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket='bucket')
        s3.put_object(
            Bucket='bucket',
            Key='models/test-model/model.pkl',
            Body=b'mock model data'
        )
        yield s3

@pytest.fixture
def model_registry(dynamodb_table, s3_bucket):
    return ModelRegistry(table_name='mlops-model-metadata')

def test_get_model_metadata_success(model_registry):
    """Test successful retrieval of model metadata"""
    metadata = model_registry.get_model_metadata('test-model')
    
    assert metadata is not None
    assert metadata['model_id'] == 'test-model'
    assert metadata['version'] == '1'
    assert metadata['s3_path'] == 's3://bucket/models/test-model/model.pkl'

def test_get_model_metadata_not_found(model_registry):
    """Test handling of non-existent model"""
    with pytest.raises(ModelNotFoundError) as exc_info:
        model_registry.get_model_metadata('non-existent-model')
    
    assert 'not found' in str(exc_info.value)

def test_register_model_success(model_registry):
    """Test successful model registration"""
    new_model = {
        'model_id': 'new-model',
        'version': '1',
        'framework': 'pytorch',
        's3_path': 's3://bucket/models/new-model/model.pt'
    }
    
    result = model_registry.register_model(new_model)
    
    assert result is True
    # Verify model was added
    metadata = model_registry.get_model_metadata('new-model')
    assert metadata['model_id'] == 'new-model'
    assert metadata['framework'] == 'pytorch'

def test_register_model_invalid_data(model_registry):
    """Test registration with invalid model data"""
    invalid_model = {
        # Missing required fields
        'model_id': 'invalid-model'
    }
    
    with pytest.raises(InvalidModelError) as exc_info:
        model_registry.register_model(invalid_model)
    
    assert 'missing required fields' in str(exc_info.value).lower()

@patch('api.services.model_loader.ModelLoader.load_model_from_s3')
def test_load_model_success(mock_load, model_registry):
    """Test successful model loading"""
    mock_model = MagicMock()
    mock_load.return_value = mock_model
    
    model = model_registry.load_model('test-model')
    
    assert model is mock_model
    mock_load.assert_called_once()
    # Verify correct S3 path was used
    args = mock_load.call_args[0]
    assert 's3://bucket/models/test-model/model.pkl' in args

def test_load_model_not_found(model_registry):
    """Test loading non-existent model"""
    with pytest.raises(ModelNotFoundError) as exc_info:
        model_registry.load_model('non-existent-model')
    
    assert 'not found' in str(exc_info.value)