"""
Model Management API endpoints
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request

from api.models.model_management import ModelInfo, ModelList, ModelFramework, ModelMetrics, ModelStatusEnum
from api.services.model_management import ModelManagementService
from api.security.auth import auth_manager, require_scope

# Create logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/models", tags=["models"], dependencies=[Depends(auth_manager.get_current_user)])

# Constants
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10

# Helper function to validate and sanitize input parameters
def validate_input(page: int, page_size: int) -> None:
    """Validates input parameters for pagination"""
    if page <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page must be greater than 0")
    if page_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page size must be greater than 0")
    if page_size > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page size cannot exceed 100")


@router.get(
    "/",
    response_model=ModelList,
    summary="List models",
    description="Retrieve a paginated list of registered models",
    dependencies=[Depends(require_scope("models:read"))]
)
async def list_models(
    request: Request,
    page: int = Query(DEFAULT_PAGE, description="Page number"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, description="Page size"),
    framework: Optional[ModelFramework] = Query(None, description="Filter by ML framework"),
    status: Optional[ModelStatusEnum] = Query(None, description="Filter by model status"),
    owner: Optional[str] = Query(None, description="Filter by owner")
):
    """
    List registered ML models, including metadata and metrics
    """
    try:
        # Validate input parameters
        validate_input(page, page_size)

        # Construct filters based on query parameters
        filters = {}
        if framework:
            filters["framework"] = framework
        if status:
            filters["status"] = status
        if owner:
            filters["owner"] = owner

        # Call ModelManagementService to fetch models
        model_management_service = ModelManagementService(request=request)  # Initialize with request
        models, total = await model_management_service.list_models(page, page_size, filters)

        # Return paginated model list
        return ModelList(models=models, model_count=total)

    except HTTPException as http_exception:
        # Re-raise HTTPExceptions, so that they will be handled by FastAPI
        raise http_exception

    except Exception as e:
        # Catch all other exceptions and return as a 500 Internal Server Error
        logger.exception("Error listing models")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{model_id}",
    response_model=ModelInfo,
    summary="Get model",
    description="Retrieve detailed information for a specific model",
    dependencies=[Depends(require_scope("models:read"))]
)
async def get_model(
    request: Request,
    model_id: str
):
    """
    Retrieve details of a single model, including metrics and metadata
    """
    try:
        # Call ModelManagementService to fetch model
        model_management_service = ModelManagementService(request=request)  # Initialize with request
        model = await model_management_service.get_model(model_id)

        # Check if model exists
        if not model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

        # Return model information
        return model

    except HTTPException as http_exception:
        # Re-raise HTTPExceptions, so that they will be handled by FastAPI
        raise http_exception

    except Exception as e:
        # Catch all other exceptions and return as a 500 Internal Server Error
        logger.exception(f"Error getting model with id: {model_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/",
    response_model=ModelInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Register model",
    description="Register a new ML model with its metadata",
    dependencies=[Depends(require_scope("models:write"))]
)
async def register_model(
    request: Request,
    model_info: ModelInfo
):
    """
    Register a new ML model with its metadata and initial status
    """
    try:
        # Call ModelManagementService to create model
        model_management_service = ModelManagementService(request=request)  # Initialize with request
        model = await model_management_service.create_model(model_info)

        # Check if model was successfully created
        if not model:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create model")

        # Return created model information
        return model

    except HTTPException as http_exception:
        # Re-raise HTTPExceptions, so that they will be handled by FastAPI
        raise http_exception

    except Exception as e:
        # Catch all other exceptions and return as a 500 Internal Server Error
        logger.exception("Error registering model")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put(
    "/{model_id}",
    response_model=ModelInfo,
    summary="Update model",
    description="Update the metadata for a specific model",
    dependencies=[Depends(require_scope("models:write"))]
)
async def update_model(
    request: Request,
    model_id: str,
    model_info: ModelInfo
):
    """
    Update the details of an existing model, including metrics
    """
    try:
        # Call ModelManagementService to update model
        model_management_service = ModelManagementService(request=request)  # Initialize with request
        model = await model_management_service.update_model(model_id, model_info)

        # Check if model exists
        if not model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

        # Return updated model information
        return model

    except HTTPException as http_exception:
        # Re-raise HTTPExceptions, so that they will be handled by FastAPI
        raise http_exception

    except Exception as e:
        # Catch all other exceptions and return as a 500 Internal Server Error
        logger.exception(f"Error updating model with id: {model_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete model",
    description="Delete a specific model",
    dependencies=[Depends(require_scope("models:delete"))]
)
async def delete_model(
    request: Request,
    model_id: str
):
    """
    Delete a registered ML model
    """
    try:
        # Call ModelManagementService to delete model
        model_management_service = ModelManagementService(request=request)  # Initialize with request
        deleted = await model_management_service.delete_model(model_id)

        # Check if model was successfully deleted
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

        # Return a 204 No Content response to indicate successful deletion
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException as http_exception:
        # Re-raise HTTPExceptions, so that they will be handled by FastAPI
        raise http_exception

    except Exception as e:
        # Catch all other exceptions and return as a 500 Internal Server Error
        logger.exception(f"Error deleting model with id: {model_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))