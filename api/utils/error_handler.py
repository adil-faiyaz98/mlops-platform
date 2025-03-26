import logging
import traceback
from typing import Dict, Any, Optional, Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

# Configure logger
logger = logging.getLogger(__name__)

class APIErrorBase(Exception):
    """Base exception for all API errors"""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    
    def __init__(
        self, 
        message: str = "An unexpected error occurred",
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        log_exception: bool = True
    ):
        self.message = message
        self.details = details or {}
        self.headers = headers or {}
        
        if log_exception:
            logger.error(
                f"{self.__class__.__name__}: {message}",
                extra={
                    "error_code": self.error_code,
                    "details": self.details
                },
                exc_info=True
            )
        
        super().__init__(message)


class ValidationError(APIErrorBase):
    """Raised for request validation errors"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"


class NotFoundError(APIErrorBase):
    """Raised when a resource is not found"""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class AuthenticationError(APIErrorBase):
    """Raised for authentication failures"""
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, **kwargs)
        # Always include WWW-Authenticate header
        self.headers["WWW-Authenticate"] = "Bearer"


class AuthorizationError(APIErrorBase):
    """Raised for authorization failures"""
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "authorization_error"


class RateLimitExceededError(APIErrorBase):
    """Raised when rate limit is exceeded"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limit_exceeded"
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded", 
        retry_after_seconds: int = 60,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        # Include retry information in headers
        self.headers["Retry-After"] = str(retry_after_seconds)


class ServiceUnavailableError(APIErrorBase):
    """Raised when a required service is unavailable"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "service_unavailable"


class BadGatewayError(APIErrorBase):
    """Raised when an upstream service returns an error"""
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "bad_gateway"


# Define error handling functions for FastAPI
async def api_error_handler(request: Request, exc: APIErrorBase) -> JSONResponse:
    """Handle custom API exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "request_id": getattr(request.state, "request_id", None)
            }
        },
        headers=exc.headers
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors from FastAPI"""
    errors = []
    
    for error in exc.errors():
        error_location = " -> ".join([str(loc) for loc in error["loc"] if loc != "body"])
        errors.append({
            "field": error_location,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation error for {request.url.path}",
        extra={
            "errors": errors,
            "client_ip": request.client.host if request.client else None,
            "request_id": getattr(request.state, "request_id", None)
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": {
                    "errors": errors
                },
                "request_id": getattr(request.state, "request_id", None)
            }
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions"""
    request_id = getattr(request.state, "request_id", None)
    
    # Log the full exception with traceback for internal debugging
    logger.error(
        f"Unhandled exception in {request.url.path}: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        },
        exc_info=True
    )
    
    # Return a generic error to the client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "request_id": request_id
            }
        }
    )


# Register these handlers in main.py
# app.add_exception_handler(APIErrorBase, api_error_handler)
# app.add_exception_handler(RequestValidationError, validation_exception_handler)
# app.add_exception_handler(Exception, unhandled_exception_handler)