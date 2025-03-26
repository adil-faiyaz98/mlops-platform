from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from typing import Union, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Base exception class
class MLOpsError(Exception):
    """Base class for all MLOps platform exceptions"""
    def __init__(
        self, 
        status_code: int, 
        detail: Union[str, Dict[str, Any]], 
        headers: Dict[str, str] = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

# Specific exception types
class ModelNotFoundError(MLOpsError):
    """Raised when a model is not found in the registry"""
    def __init__(self, model_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with ID '{model_id}' not found"
        )

class InvalidModelError(MLOpsError):
    """Raised when model data is invalid"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid model data: {detail}"
        )

class ModelLoadingError(MLOpsError):
    """Raised when a model fails to load"""
    def __init__(self, model_id: str, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load model '{model_id}': {detail}"
        )

class PredictionError(MLOpsError):
    """Raised when model prediction fails"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {detail}"
        )

class RateLimitExceededError(MLOpsError):
    """Raised when rate limit is exceeded"""
    def __init__(self, wait_time_seconds: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please try again in {wait_time_seconds} seconds",
            headers={"Retry-After": str(wait_time_seconds)}
        )

class AuthenticationError(MLOpsError):
    """Raised when authentication fails"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class AuthorizationError(MLOpsError):
    """Raised when user is not authorized to access a resource"""
    def __init__(self, detail: str = "Not authorized to access this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

# Exception handlers for FastAPI
async def mlops_exception_handler(request: Request, exc: MLOpsError):
    """Handler for MLOps custom exceptions"""
    logger.error(f"MLOps error: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers or {}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors"""
    errors: List[Dict[str, Any]] = exc.errors()
    error_messages = []
    
    # Format error messages to be more user-friendly
    for error in errors:
        loc = " → ".join([str(x) for x in error["loc"] if x != "body"])
        msg = f"{loc}: {error['msg']}"
        error_messages.append(msg)
    
    logger.warning(f"Validation error: {error_messages}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request validation failed",
            "errors": error_messages
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler for HTTP exceptions"""
    logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None) or {}
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )