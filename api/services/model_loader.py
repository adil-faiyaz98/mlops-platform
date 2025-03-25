import os
import time
import logging
from typing import Any, Dict, Optional, Union, Callable
import boto3
import botocore
import pickle
import json
import tempfile
from pathlib import Path

from api.utils.circuit_breaker import CircuitBreaker
from api.utils.backoff import exponential_backoff
from api.exceptions.model_exceptions import ModelNotFoundError, ModelLoadingError, InvalidModelError

# Configure logger
logger = logging.getLogger(__name__)

class ModelLoader:
    """
    Handles loading models from S3 with comprehensive error handling,
    retry logic, and circuit breaker pattern.
    """
    
    def __init__(self, default_region: str = None):
        """
        Initialize model loader
        
        Args:
            default_region: Default AWS region for S3
        """
        self.default_region = default_region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self._s3_client = None
        self._init_time = time.time()
        self._model_cache = {}  # Simple in-memory cache for loaded models
    
    @property
    def s3_client(self):
        """Lazy initialization of S3 client with circuit breaker"""
        if self._s3_client is None:
            self._s3_client = boto3.client("s3", region_name=self.default_region)
        return self._s3_client
    
    @CircuitBreaker(name="s3", failure_threshold=3, recovery_timeout=60)
    def download_model_file(self, bucket: str, key: str, local_path: Path) -> Path:
        """
        Download model file from S3 with circuit breaker
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            local_path: Local path to save file
            
        Returns:
            Path to downloaded file
        """
        try:
            # Use exponential backoff for transient errors
            @exponential_backoff(max_retries=3, initial_delay=1, max_delay=5)
            def download_with_retry():
                self.s3_client.download_file(bucket, key, str(local_path))
            
            # Execute download with retry
            download_with_retry()
            return local_path
            
        except botocore.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                raise ModelNotFoundError(f"Model file not found: s3://{bucket}/{key}")
            elif error_code == 'AccessDenied':
                raise ModelLoadingError(f"Access denied to model file: s3://{bucket}/{key}")
            else:
                logger.error(f"S3 error downloading model: {error_code} - {str(e)}")
                raise ModelLoadingError(f"Failed to download model: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error downloading model: {str(e)}", exc_info=True)
            raise ModelLoadingError(f"Failed to download model: {str(e)}")
    
    def load_pickle_model(self, local_path: Path) -> Any:
        """
        Load model from pickle file
        
        Args:
            local_path: Path to pickle file
            
        Returns:
            Loaded model
        """
        try:
            with open(local_path, 'rb') as f:
                return pickle.load(f)
        except (pickle.PickleError, EOFError) as e:
            raise InvalidModelError(f"Invalid pickle file: {str(e)}")
        except Exception as e:
            raise ModelLoadingError(f"Error loading pickle model: {str(e)}")
    
    def load_model_from_s3(
        self, 
        s3_uri: str, 
        model_format: str = "pickle",
        model_id: str = None,
        force_reload: bool = False
    ) -> Any:
        """
        Load model from S3
        
        Args:
            s3_uri: S3 URI in format s3://bucket/key
            model_format: Format of the model file (pickle, json, etc.)
            model_id: Optional model ID for caching
            force_reload: Force reload from S3 even if cached
            
        Returns:
            Loaded model
        """
        # Check cache first if model_id provided and not forcing reload
        cache_key = model_id or s3_uri
        if not force_reload and cache_key in self._model_cache:
            logger.info(f"Loading model from cache: {cache_key}")
            return self._model_cache[cache_key]['model']
        
        # Parse S3 URI
        try:
            if not s3_uri.startswith("s3://"):
                raise ValueError(f"Invalid S3 URI format: {s3_uri}")
                
            parts = s3_uri.replace("s3://", "").split("/", 1)
            if len(parts) < 2:
                raise ValueError(f"Invalid S3 URI format: {s3_uri}")
                
            bucket = parts[0]
            key = parts[1]
            
        except ValueError as e:
            logger.error(f"Error parsing S3 URI: {str(e)}")
            raise ModelLoadingError(f"Invalid S3 URI: {str(e)}")
        
        # Create temp file for download
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / Path(key).name
            
            # Download model file
            self.download_model_file(bucket, key, local_path)
            
            # Load based on format
            try:
                if model_format.lower() == "pickle":
                    model = self.load_pickle_model(local_path)
                elif model_format.lower() == "json":
                    with open(local_path, 'r') as f:
                        model = json.load(f)
                else:
                    raise ModelLoadingError(f"Unsupported model format: {model_format}")
                
                # Cache the model if model_id provided
                if model_id:
                    self._model_cache[cache_key] = {
                        'model': model,
                        'loaded_at': time.time()
                    }
                
                return model
                
            except (InvalidModelError, ModelLoadingError) as e:
                # Re-raise these specific exceptions
                raise
            except Exception as e:
                logger.error(f"Unexpected error loading model: {str(e)}", exc_info=True)
                raise ModelLoadingError(f"Failed to load model: {str(e)}")
    
    def clear_cache(self, model_id: Optional[str] = None) -> None:
        """
        Clear model cache
        
        Args:
            model_id: Specific model ID to clear, or all if None
        """
        if model_id:
            if model_id in self._model_cache:
                del self._model_cache[model_id]
                logger.info(f"Cleared cache for model: {model_id}")
        else:
            self._model_cache.clear()
            logger.info("Cleared entire model cache")
    
    def get_cache_info(self) -> Dict:
        """
        Get information about cached models
        
        Returns:
            Dict with cache information
        """
        return {
            "cache_size": len(self._model_cache),
            "models": [
                {
                    "model_id": model_id,
                    "loaded_at": info['loaded_at'],
                    "age_seconds": time.time() - info['loaded_at']
                }
                for model_id, info in self._model_cache.items()
            ]
        }