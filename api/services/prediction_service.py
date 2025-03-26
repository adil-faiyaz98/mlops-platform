import logging
import time
from typing import Any, Dict, List, Union, Optional
import traceback

from api.exceptions import PredictionError, ModelNotFoundError
from api.services.model_registry import ModelRegistry
from api.utils.telemetry import trace_span, record_metrics

logger = logging.getLogger(__name__)

class PredictionService:
    """Service for handling model predictions"""
    
    def __init__(self, model_registry: ModelRegistry):
        """
        Initialize the prediction service
        
        Args:
            model_registry: Model registry service for loading models
        """
        self.model_registry = model_registry
    
    @trace_span("predict")
    def predict(
        self, 
        features: List[float], 
        model_id: str,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make a prediction using the specified model
        
        Args:
            features: Input features for the prediction
            model_id: ID of the model to use
            request_id: Optional request ID for tracing
            
        Returns:
            Dictionary with prediction results
            
        Raises:
            ModelNotFoundError: If the model is not found
            PredictionError: If prediction fails
        """
        start_time = time.time()
        
        try:
            # Log request information
            logger.info(
                f"Prediction request received",
                extra={
                    "model_id": model_id,
                    "feature_count": len(features),
                    "request_id": request_id or "unknown"
                }
            )
            
            # Load the model (may raise ModelNotFoundError)
            model = self.model_registry.load_model(model_id)
            
            # Make the prediction
            prediction = model(features)
            
            # Log successful prediction
            duration = time.time() - start_time
            logger.info(
                f"Prediction successful",
                extra={
                    "model_id": model_id,
                    "duration_ms": int(duration * 1000),
                    "request_id": request_id or "unknown"
                }
            )
            
            # Record metrics
            record_metrics(
                "prediction_latency_seconds",
                duration,
                {"model_id": model_id}
            )
            record_metrics(
                "prediction_count",
                1,
                {"model_id": model_id, "status": "success"}
            )
            
            return prediction
            
        except ModelNotFoundError:
            # Re-raise model not found errors
            record_metrics(
                "prediction_count",
                1,
                {"model_id": model_id, "status": "model_not_found"}
            )
            raise
            
        except Exception as e:
            # Log detailed error information
            logger.error(
                f"Prediction failed: {str(e)}",
                extra={
                    "model_id": model_id,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "request_id": request_id or "unknown"
                },
                exc_info=True
            )
            
            # Record failure metrics
            record_metrics(
                "prediction_count",
                1,
                {"model_id": model_id, "status": "error"}
            )
            
            # Wrap in PredictionError
            raise PredictionError(str(e))
    
    @trace_span("batch_predict")
    def batch_predict(
        self,
        inputs: List[List[float]],
        model_id: str,
        batch_size: int = 32,
        request_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Make predictions for multiple inputs using the specified model
        
        Args:
            inputs: List of feature vectors
            model_id: ID of the model to use
            batch_size: Batch size for processing
            request_id: Optional request ID for tracing
            
        Returns:
            List of prediction results
            
        Raises:
            ModelNotFoundError: If the model is not found
            PredictionError: If prediction fails
        """
        start_time = time.time()
        
        try:
            # Log request information
            logger.info(
                f"Batch prediction request received",
                extra={
                    "model_id": model_id,
                    "input_count": len(inputs),
                    "batch_size": batch_size,
                    "request_id": request_id or "unknown"
                }
            )
            
            # Load the model (may raise ModelNotFoundError)
            model = self.model_registry.load_model(model_id)
            
            results = []
            batches = 0
            
            # Process in batches
            for i in range(0, len(inputs), batch_size):
                batch = inputs[i:i+batch_size]
                batch_results = [model(features) for features in batch]
                results.extend(batch_results)
                batches += 1
            
            # Log successful batch prediction
            duration = time.time() - start_time
            logger.info(
                f"Batch prediction successful",
                extra={
                    "model_id": model_id,
                    "input_count": len(inputs),
                    "batches": batches,
                    "duration_ms": int(duration * 1000),
                    "request_id": request_id or "unknown"
                }
            )
            
            # Record metrics
            record_metrics(
                "batch_prediction_latency_seconds",
                duration,
                {"model_id": model_id}
            )
            record_metrics(
                "batch_prediction_count",
                1,
                {"model_id": model_id, "status": "success"}
            )
            record_metrics(
                "batch_prediction_items_processed",
                len(inputs),
                {"model_id": model_id}
            )
            
            return results
            
        except ModelNotFoundError:
            # Re-raise model not found errors
            record_metrics(
                "batch_prediction_count",
                1,
                {"model_id": model_id, "status": "model_not_found"}
            )
            raise
            
        except Exception as e:
            # Log detailed error information
            logger.error(
                f"Batch prediction failed: {str(e)}",
                extra={
                    "model_id": model_id,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "request_id": request_id or "unknown"
                },
                exc_info=True
            )
            
            # Record failure metrics
            record_metrics(
                "batch_prediction_count",
                1,
                {"model_id": model_id, "status": "error"}
            )
            
            # Wrap in PredictionError
            raise PredictionError(str(e))