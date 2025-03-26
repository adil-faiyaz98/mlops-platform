import re
import os
import time
import logging
import secrets
from typing import List, Optional, Dict, Any, Callable
from fastapi import Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
import bleach

# Configure logger
logger = logging.getLogger(__name__)

class SecurityConfig:
    """Configuration for security middleware"""
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    
    # If no secret key provided in prod, generate one and warn
    if not JWT_SECRET_KEY:
        if os.getenv("ENVIRONMENT", "development") == "production":
            logger.warning("No JWT_SECRET_KEY set in production! Generating temporary key.")
        JWT_SECRET_KEY = secrets.token_hex(32)
    
    # CORS settings
    CORS_ALLOW_ORIGINS: List[str] = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # Content Security Policy
    CSP_DIRECTIVES: Dict[str, str] = {
        "default-src": "'self'",
        "img-src": "'self' data:",
        "script-src": "'self'",
        "style-src": "'self' 'unsafe-inline'",
        "connect-src": "'self'",
        "frame-ancestors": "'none'",
        "form-action": "'self'"
    }
    
    # Security headers
    SECURITY_HEADERS: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses"""
    
    def __init__(self, app, config: SecurityConfig = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in self.config.SECURITY_HEADERS.items():
            response.headers[header_name] = header_value
        
        # Add Content-Security-Policy header
        csp_value = "; ".join(f"{k} {v}" for k, v in self.config.CSP_DIRECTIVES.items())
        response.headers["Content-Security-Policy"] = csp_value
        
        return response


class XSSProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware to sanitize request inputs to prevent XSS"""
    
    def __init__(self, app, paths_to_sanitize: List[str] = None):
        super().__init__(app)
        self.paths_to_sanitize = paths_to_sanitize or ["/api/"]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Only sanitize paths that match our criteria
        should_sanitize = any(request.url.path.startswith(path) for path in self.paths_to_sanitize)
        
        if should_sanitize and request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Get the request body
                body = await request.json()
                
                # Sanitize the body - recursively clean strings
                sanitized_body = self._sanitize_data(body)
                
                # Override the request's receive method to return our sanitized body
                original_receive = request.receive
                
                async def receive():
                    data = await original_receive()
                    if data["type"] == "http.request":
                        data["body"] = sanitized_body.encode()
                    return data
                
                request._receive = receive
            
            except Exception as e:
                logger.warning(f"Failed to sanitize request body: {str(e)}")
        
        return await call_next(request)
    
    def _sanitize_data(self, data: Any) -> Any:
        """Recursively sanitize data to prevent XSS"""
        if isinstance(data, str):
            return bleach.clean(data)
        elif isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        return data


class JWTBearerAuth(HTTPBearer):
    """JWT Bearer authentication class"""
    
    def __init__(
        self, 
        auto_error: bool = True,
        config: SecurityConfig = None,
        required_scopes: List[str] = None
    ):
        super().__init__(auto_error=auto_error)
        self.config = config or SecurityConfig()
        self.required_scopes = required_scopes or []
    
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            return None
        
        # Validate JWT token
        try:
            payload = jwt.decode(
                credentials.credentials,
                self.config.JWT_SECRET_KEY,
                algorithms=[self.config.JWT_ALGORITHM]
            )
            
            # Check token expiration
            if "exp" in payload and payload["exp"] < time.time():
                from api.utils.error_handler import AuthenticationError
                raise AuthenticationError("Token has expired")
            
            # Check required scopes if specified
            if self.required_scopes:
                token_scopes = payload.get("scope", "").split()
                if not all(scope in token_scopes for scope in self.required_scopes):
                    from api.utils.error_handler import AuthorizationError
                    raise AuthorizationError("Insufficient permissions")
            
            # Add the payload to request state for handlers to access
            request.state.user = payload
            return payload
            
        except JWTError:
            from api.utils.error_handler import AuthenticationError
            raise AuthenticationError("Invalid authentication token")


class SQLInjectionProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware to detect and block potential SQL injection attacks"""
    
    def __init__(self, app):
        super().__init__(app)
        # Common SQL injection patterns
        self.sql_patterns = [
            r"(?i)(select\s+.*\s+from)",
            r"(?i)(insert\s+into)",
            r"(?i)(update\s+.*\s+set)",
            r"(?i)(delete\s+from)",
            r"(?i)(drop\s+table)",
            r"(?i)(union\s+select)",
            r"(?i)(exec\s*\()",
            r"(?i)(--\s*$)",
            r"(?i)(\/\*.*\*\/)"
        ]
        self.sql_pattern_compiled = [re.compile(pattern) for pattern in self.sql_patterns]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Check query parameters
        for param, values in request.query_params.items():
            if self._is_sql_injection(values):
                logger.warning(
                    f"Potential SQL injection detected in query param: {param}={values}",
                    extra={"client_ip": request.client.host, "path": request.url.path}
                )
                from api.utils.error_handler import ValidationError
                raise ValidationError("Invalid input detected", details={"reason": "security_violation"})
        
        # Check path parameters
        for value in request.path_params.values():
            if isinstance(value, str) and self._is_sql_injection(value):
                logger.warning(
                    f"Potential SQL injection detected in path param: {value}",
                    extra={"client_ip": request.client.host, "path": request.url.path}
                )
                from api.utils.error_handler import ValidationError
                raise ValidationError("Invalid input detected", details={"reason": "security_violation"})
        
        # For POST/PUT/PATCH requests, check the body
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_copy = await request.body()
                body_str = body_copy.decode()
                
                if self._is_sql_injection(body_str):
                    logger.warning(
                        f"Potential SQL injection detected in request body",
                        extra={"client_ip": request.client.host, "path": request.url.path}
                    )
                    from api.utils.error_handler import ValidationError
                    raise ValidationError("Invalid input detected", details={"reason": "security_violation"})
                
                # Reset the request body
                async def receive():
                    return {"type": "http.request", "body": body_copy}
                
                request._receive = receive
                
            except UnicodeDecodeError:
                # Not a text body, continue
                pass
        
        return await call_next(request)
    
    def _is_sql_injection(self, value: str) -> bool:
        """Check if a string matches known SQL injection patterns"""
        if not isinstance(value, str):
            return False
            
        return any(pattern.search(value) for pattern in self.sql_pattern_compiled)