import os
import logging
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import UploadFile

from api.models.model_metadata import ModelMetadata, ModelDeployResponse
from api.utils.config import Config

logger = logging.getLogger(__name__)


class ModelManagerService:
    """Service for managing ML models"""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the model manager service"""
        self.config = config or Config()
        self.models_dir = self.config.get("models", {}).get("storage_path", "./models")
        
        # Ensure models directory exists
        os.makedirs(self.models_dir, exist_ok=True)
        
        # In production, this would interface with a model registry database
        # For simplicity, using a dictionary as storage
        self.models = {}
        
        # Load existing models
        self._load_existing_models()
        
    def _load_existing_models(self):
        """Load existing model metadata from storage"""
        try:
            metadata_path = os.path.join(self.models_dir, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    self.models = json.load(f)
            else:
                self.models = {}
        except Exception as e:
            logger.error(f"Error loading model metadata: {str(e)}")
            self.models = {}
    
    def _save_models_metadata(self):
        """Save model metadata to storage"""
        try:
            metadata_path = os.path.join(self.models_dir, "metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(self.models, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving model metadata: {str(e)}")
            
    async def list_models(
        self,
        limit: int = 10,
        offset: int = 0,
        deployed_only: bool = False
    ) -> List[ModelMetadata]:
        """
        List registered models
        
        Args:
            limit: Maximum number of models to return
            offset: Offset for pagination
            deployed_only: If True, only return deployed models
            
        Returns:
            List of model metadata
        """
        # Filter and convert to ModelMetadata objects
        result = []
        
        for model_id, model_data in list(self.models.items())[offset:offset+limit]:
            # Filter deployed only if specified
            if deployed_only and not model_data.get("deployed", False):
                continue
                
            # Convert to Pydantic model
            model = ModelMetadata(**model_data)
            result.append(model)
            
        return result
        
    async def get_model(
        self,
        model_id: str,
        version: Optional[str] = None
    ) -> ModelMetadata:
        """
        Get details for a specific model
        
        Args:
            model_id: Model ID or name
            version: Optional specific version
            
        Returns:
            Model metadata
            
        Raises:
            ValueError: If model not found
        """
        # Check if model exists
        if model_id not in self.models:
            # Try to find by name
            for mid, model in self.models.items():
                if model.get("model_name") == model_id:
                    model_id = mid
                    break
            else:
                raise ValueError(f"Model {model_id} not found")
        
        model_data = self.models[model_id]
        
        # If version specified and it's a specific version
        if version and model_data.get("version") != version:
            raise ValueError(f"Model {model_id} with version {version} not found")
            
        return ModelMetadata(**model_data)
        
    async def deploy_model(
        self,
        model_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ModelDeployResponse:
        """
        Deploy a model to the serving environment
        
        Args:
            model_id: Model ID to deploy
            config: Deployment configuration
            
        Returns:
            Deployment response
            
        Raises:
            ValueError: If model not found
        """
        # Check if model exists
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
            
        # In a real implementation, this would trigger actual deployment
        # For this example, just update the status
        self.models[model_id]["deployed"] = True
        self.models[model_id]["serving_endpoint"] = f"/api/v1/models/{model_id}/predict"
        self._save_models_metadata()
        
        deployment_id = f"deployment-{uuid.uuid4()}"
        
        return ModelDeployResponse(
            model_id=model_id,
            deployment_id=deployment_id,
            status="DEPLOYED",
            endpoint=f"/api/v1/models/{model_id}/predict",
            message="Model deployed successfully"
        )
        
    async def upload_model(
        self,
        name: str,
        version: str,
        framework: str,
        description: Optional[str] = None,
        model_file: UploadFile = None
    ) -> ModelMetadata:
        """
        Upload and register a new model
        
        Args:
            name: Model name
            version: Model version
            framework: ML framework
            description: Optional model description
            model_file: Model file to upload
            
        Returns:
            Metadata for the registered model
        """
        # Generate model ID
        model_id = f"{name.lower().replace(' ', '-')}-{version.replace('.', '-')}"
        
        # Check if model already exists
        if model_id in self.models:
            raise ValueError(f"Model {name} version {version} already exists")
            
        # Create model directory
        model_dir = os.path.join(self.models_dir, model_id)
        os.makedirs(model_dir, exist_ok=True)
        
        # Save model file if provided
        model_path = None
        if model_file:
            model_path = os.path.join(model_dir, model_file.filename)
            with open(model_path, "wb") as buffer:
                buffer.write(await model_file.read())
                
        # Create model metadata
        model_metadata = {
            "model_id": model_id,
            "model_name": name,
            "version": version,
            "framework": framework,
            "created_at": datetime.now().isoformat(),
            "performance_metrics": {},  # Would be populated from model evaluation
            "input_schema": {},  # Would be extracted from model
            "output_schema": {},  # Would be extracted from model
            "description": description,
            "tags": [],
            "deployed": False,
            "serving_endpoint": None,
            "model_path": model_path
        }
        
        # Save to registry
        self.models[model_id] = model_metadata
        self._save_models_metadata()
        
        return ModelMetadata(**model_metadata)