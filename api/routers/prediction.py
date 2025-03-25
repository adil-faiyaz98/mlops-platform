"""
Prediction API endpoints
"""
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request

from api.models.prediction import (
    PredictionRequest, 
    PredictionResponse,
    BatchPredictionRequest, 
    BatchPredictionResponse
)
from api.services.inference import InferenceService
from api.utils.metrics import get_metrics

logger = logging.getLogger(__name__)
metrics = get_metrics()

router = APIRouter(prefix="/api/v1", tags=["predictions"])

@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Make prediction",
    response_description="Model prediction results"
)
async def predict(
    request: Request,
    prediction_request: PredictionRequest,
    background_tasks: BackgroundTasks,
    inference_service: InferenceService = Depends()
):
    """
    Make predictions using the deployed model
    
    - **inputs**: Input data for prediction
    - **parameters**: Optional parameters for prediction
    """
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    try:
        # Log request metadata
        logger.info(f"Prediction request received: {request_id}")
        metrics.incr("api.prediction_requests")
        
        # Make prediction
        result = await inference_service.predict(
            inputs=prediction_request.inputs,
            parameters=prediction_request.parameters
        )
        
        # Track latency
        latency = time.time() - start_time
        metrics.timing("api.prediction_latency", latency * 1000)
        logger.info(f"Prediction completed in {latency:.3f}s: {request_id}")
        
        # Track prediction in background
        background_tasks.add_task(
            track_prediction,
            request_id=request_id,
            inputs_count=len(prediction_request.inputs),
            latency=latency
        )
        
        return result
        
    except ValueError as e:
        # Invalid input
        metrics.incr("api.prediction_input_errors")
        logger.warning(f"Invalid prediction input: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Server error
        metrics.incr("api.prediction_errors")
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail="Prediction failed")


@router.post(
    "/batch-predict",
    response_model=BatchPredictionResponse,
    summary="Make batch prediction",
    response_description="Batch prediction results"
)
async def batch_predict(
    request: Request,
    prediction_request: BatchPredictionRequest,
    background_tasks: BackgroundTasks,
    max_batch_size: Optional[int] = Query(None, description="Maximum batch size"),
    inference_service: InferenceService = Depends()
):
    """
    Make batch predictions using the deployed model
    
    - **inputs**: List of input data for prediction
    - **parameters**: Optional parameters for prediction
    - **max_batch_size**: Maximum batch size (optional)
    """
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    try:
        # Log request metadata
        logger.info(f"Batch prediction request received: {request_id}, batch size: {len(prediction_request.inputs)}")
        metrics.incr("api.batch_prediction_requests")
        metrics.gauge("api.batch_size", len(prediction_request.inputs))
        
        # Enforce maximum batch size if specified
        inputs = prediction_request.inputs
        if max_batch_size and len(inputs) > max_batch_size:
            raise ValueError(f"Batch size ({len(inputs)}) exceeds maximum allowed ({max_batch_size})")
            
        # Make prediction
        result = await inference_service.predict(
            inputs=prediction_request.inputs,
            parameters=prediction_request.parameters
        )
        
        # Track latency
        latency = time.time() - start_time
        metrics.timing("api.batch_prediction_latency", latency * 1000)
        logger.info(f"Batch prediction completed in {latency:.3f}s: {request_id}")
        
        # Track prediction in background
        background_tasks.add_task(
            track_prediction,
            request_id=request_id,
            inputs_count=len(prediction_request.inputs),
            latency=latency,
            is_batch=True
        )
        
        return result
        
    except ValueError as e:
        # Invalid input
        metrics.incr("api.batch_prediction_input_errors")
        logger.warning(f"Invalid batch prediction input: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        # Server error
        metrics.incr("api.batch_prediction_errors")
        logger.error(f"Batch prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail="Batch prediction failed")