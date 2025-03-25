import pytest
from api.models.prediction import PredictionRequest

def test_prediction_request_valid():
    request = PredictionRequest(feature1=1.0, feature2=2.0, feature3=3.0)
    assert request.feature1 == 1.0
    assert request.feature2 == 2.0
    assert request.feature3 == 3.0

def test_prediction_request_invalid_feature_type():
    with pytest.raises(ValueError):
        PredictionRequest(feature1="abc", feature2=2.0, feature3=3.0)