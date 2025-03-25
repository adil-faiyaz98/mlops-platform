"""
Main API application with security and documentation enhancements.
"""
import os
from typing import Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import JSONResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from api.utils.config import Config
from api.utils.logging import logger, add_request_context_middleware
from api.utils.metrics import get_metrics
from api.cache.enhanced_redis_cache import EnhancedRedisCache
from api.middleware.rate_limiter import setup_rate_limiting
from api.middleware.cache_middleware import setup_cache_middleware
from api.routers import health, prediction, model, auth

# Initialize metrics
metrics = get_metrics()

def create_application() -> FastAPI:
    """
    Create and configure FastAPI application
    
    Returns:
        Configured FastAPI application
    """
    # Load configuration
    config = Config()
    
    # Create FastAPI app
    app = FastAPI(
        title="MLOps Platform API",
        description="Production-ready ML model serving API",
        version=os.environ.get("APP_VERSION", "0.1.0"),
        docs_url=None,  # Disable default docs for custom secured docs
        redoc_url=None,  # Disable default redoc for custom secured docs
    )

    # Add the middleware for authentication.
    middleware = [
        Middleware(HTTPSRedirectMiddleware) #Force users to come in using security.
    ]
    app = FastAPI(middleware=middleware)
    
    # Configure CORS
    cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",") #added get and check
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Create Redis client
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis_cache = EnhancedRedisCache(redis_url=redis_url, config=config)
    
    # Set up middleware
    try:
        setup_rate_limiting(app, redis_cache, config)
    except Exception as e:
        logger.error(f"Error setting up rate limiting middleware: {e}", exc_info=True)
        # Option 1: Exit if rate limiting is critical
        # sys.exit(1)
        # Option 2: Continue without rate limiting (less secure)
        pass  
    
    try:
        cache_manager = setup_cache_middleware(app, redis_cache, config)
    except Exception as e:
        logger.error(f"Error setting up cache middleware: {e}", exc_info=True)
        cache_manager = None # Disable middleware

    app = add_request_context_middleware(app)
    
    try:
        app = metrics.setup_http_metrics_middleware(app)
    except Exception as e:
        logger.error(f"Error setting up metrics middleware: {e}", exc_info=True)

    
    # Register API routes
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(prediction.router, prefix="/api/v1")
    app.include_router(model.router, prefix="/api/v1")
    app.include_router(auth.router)
    #app.include_router(monitoring.router, prefix="/api/v1") Removed for this
    
    # Add metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint():
        """Prometheus metrics endpoint"""
        from prometheus_client import generate_latest
        content = generate_latest()
        return Response(content=content, media_type="text/plain")
    
    # Custom API docs endpoints (with optional auth)
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Custom Swagger UI endpoint"""
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url="/static/swagger-ui-bundle.js",
            swagger_css_url="/static/swagger-ui.css",
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html():
        """Custom ReDoc endpoint"""
        return get_redoc_html(
            openapi_url="/openapi.json",
            title=f"{app.title} - ReDoc",
            redoc_js_url="/static/redoc.standalone.js",
        )
    
    # Enhanced OpenAPI schema
    def custom_openapi():
        """Generate custom OpenAPI schema with enhanced documentation"""
        if app.openapi_schema:
            return app.openapi_schema
            
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        
        # Add servers section for different environments
        openapi_schema["servers"] = [
            {"url": "https://api.mlops-platform.com", "description": "Production"},
            {"url": "https://staging.mlops-platform.com", "description": "Staging"},
            {"url": "http://localhost:8000", "description": "Local Development"}
        ]
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            }
        }
        
        # Add security requirement to all operations
        for path in openapi_schema["paths"].values():
            for operation in path.values():
                operation["security"] = [
                    {"BearerAuth": []},
                    {"ApiKeyAuth": []}
                ]
                
                # Add rate limit documentation
                if "parameters" not in operation:
                    operation["parameters"] = []
                    
                # Add standard response codes
                if "responses" not in operation:
                    operation["responses"] = {}
                
                if "400" not in operation["responses"]:
                    operation["responses"]["400"] = {
                        "description": "Bad Request - Invalid input data"
                    }
                if "401" not in operation["responses"]:
                    operation["responses"]["401"] = {
                        "description": "Unauthorized - Missing or invalid authentication"
                    }
                if "429" not in operation["responses"]:
                    operation["responses"]["429"] = {
                        "description": "Too Many Requests - Rate limit exceeded"
                    }
        
        # Store and return schema
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    # Set custom OpenAPI schema
    app.openapi = custom_openapi
    
    return app

# Create FastAPI instance
app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app.main:app", 
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", 8000)),
        reload=os.environ.get("ENV") != "production"
    )