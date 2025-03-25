"""
Structured logging configuration for production environments.
Provides consistent log formatting with contextual information.
"""
import os
import sys
import time
import json
import logging
from typing import Any, Dict, Optional

import structlog
from structlog.processors import (
    TimeStamper, JSONRenderer, format_exc_info, 
    UnicodeDecoder, StackInfoRenderer
)
from structlog.stdlib import filter_by_level, add_log_level
from structlog.threadlocal import wrap_dict

from fastapi import Response

# Configure environment-aware log level
def get_log_level() -> int:
    """Get log level based on environment"""
    env = os.environ.get("ENV", "development").lower()
    if env == "production":
        return logging.INFO
    return logging.DEBUG

def setup_structured_logging():
    """Configure structured logging for the application"""
    log_level = get_log_level()
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            filter_by_level,
            add_log_level,
            TimeStamper(fmt="iso"),
            format_exc_info,
            StackInfoRenderer(),
            UnicodeDecoder(),
            JSONRenderer(sort_keys=True)
        ],
        context_class=wrap_dict(dict),
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Return the configured logger
    return structlog.get_logger()

# Create a global logger instance
logger = setup_structured_logging()

# Add request context middleware
def add_request_context_middleware(app):
    """Add request context to each log entry in a FastAPI app"""
    @app.middleware("http")
    async def add_request_id_to_logger(request, call_next):
        # Generate request ID if not provided
        request_id = request.headers.get("X-Request-ID", f"req-{time.time()}")
        
        # Add request context to all logs in this request
        with structlog.contextvars.bound_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else None,
        ):
            try:
              response = await call_next(request)
            except Exception as e:
                logger.error(f"Error handling request: {e}", request_id=request_id, path=request.url.path)
                response = Response(content="Internal Server Error", status_code=500)  # Or custom error handling

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
    
    return app