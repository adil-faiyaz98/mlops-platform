"""
Rate limiting implementation to protect API endpoints from abuse.
Implements token bucket algorithm with Redis backend for distributed rate limiting.
"""
import time
import logging
import hashlib
from typing import Optional, Tuple, List

from fastapi import Request, HTTPException, Depends
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from api.cache.enhanced_redis_cache import EnhancedRedisCache
from api.utils.config import Config
from api.utils.metrics import get_metrics

logger = logging.getLogger(__name__)
metrics = get_metrics()

class RateLimiter:
    """
    Token bucket rate limiter with Redis backend for distributed rate limiting.
    Implements both IP-based and API key-based rate limiting.
    """
    
    def __init__(
        self,
        redis_cache: EnhancedRedisCache,
        config: Optional[Config] = None,
        anon_limit: int = int(os.getenv("RATE_LIMIT_ANON", "20")),
        anon_window: int = int(os.getenv("RATE_LIMIT_ANON_WINDOW", "60")),
        auth_limit: int = int(os.getenv("RATE_LIMIT_AUTH", "100")),
        auth_window: int = int(os.getenv("RATE_LIMIT_AUTH_WINDOW", "60")),
        sensitive_limit: int = int(os.getenv("RATE_LIMIT_SENSITIVE", "10")),
        sensitive_window: int = int(os.getenv("RATE_LIMIT_SENSITIVE_WINDOW", "60")),
        protected_paths: List[str] = None
    ):
        """
        Initialize rate limiter
        
        Args:
            redis_cache: Redis cache instance
            config: Configuration object
            anon_limit: Number of requests allowed for anonymous users in the window
            anon_window: Time window for anonymous users in seconds
            auth_limit: Number of requests allowed for authenticated users in the window
            auth_window: Time window for authenticated users in seconds
            sensitive_limit: Number of requests allowed for sensitive endpoints in the window
            sensitive_window: Time window for sensitive endpoints in seconds
            protected_paths: List of API paths that should have rate limiting applied
        """
        self.redis = redis_cache
        self.config = config or Config()
        
        # Default rate limits
        rate_limit_config = self.config.get("security", {}).get("rate_limits", {})
        
        # Default: 100 requests per minute for authenticated users
        self.auth_rate_limit = rate_limit_config.get("authenticated", 100)
        self.auth_window = rate_limit_config.get("auth_window", 60)  # 60 seconds
        
        # Default: 20 requests per minute for unauthenticated users
        self.anon_rate_limit = rate_limit_config.get("anonymous", 20)
        self.anon_window = rate_limit_config.get("anon_window", 60)  # 60 seconds
        
        # Stricter limits for sensitive endpoints
        self.sensitive_rate_limit = rate_limit_config.get("sensitive_endpoints", 10)
        self.sensitive_window = rate_limit_config.get("sensitive_window", 60)

        # Cooldown duration for redis availability checks
        self.redis_check_cooldown = 5  # seconds
        self.last_redis_check = 0

        # Set rate limit parameters
        self.anon_limit = anon_limit
        self.anon_window = anon_window
        self.auth_limit = auth_limit
        self.auth_window = auth_window
        self.sensitive_limit = sensitive_limit
        self.sensitive_window = sensitive_window
        
        # Set default protected paths if none provided
        self.protected_paths = protected_paths or [
            "/api/v1/predict",
            "/api/v1/batch-predict"
        ]
        
        logger.info(f"Rate limiter initialized: anon={anon_limit}/{anon_window}s, "
                   f"auth={auth_limit}/{auth_window}s, "
                   f"sensitive={sensitive_limit}/{sensitive_window}s")
        logger.info(f"Protected paths: {self.protected_paths}")

    def _generate_key(self, request: Request, is_sensitive: bool = False) -> str:
        """Generate Redis key for rate limiting"""
        # Get client identifier (API key or IP)
        client_id = self._get_client_id(request)
        
        # Generate key based on endpoint type
        endpoint_type = "sensitive" if is_sensitive else "standard"
        return f"ratelimit:{endpoint_type}:{client_id}"
        
    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting
        First try API key, then fall back to IP address
        """
        # Try to get API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization") or request.headers.get("X-Auth-Token")
        if api_key:
            if api_key.startswith("Bearer "):
                api_key = api_key[7:]  # Remove 'Bearer ' prefix
            
            # Hash the API key to avoid storing it directly
            try:
                return hashlib.sha256(api_key.encode()).hexdigest()
            except Exception as e:
                logger.error(f"Error hashing API key: {e}")
                return "unknown_api_key" # Or handle the error appropriately
        
        # Fall back to client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        
        if forwarded_for:
            # Get the original client IP from X-Forwarded-For
            client_ip = forwarded_for.split(",")[0].strip()
            
        return f"ip:{client_ip}"
    
    def check_rate_limit(
        self, 
        request: Request, 
        is_authenticated: bool = False,
        is_sensitive: bool = False
    ) -> Tuple[bool, int]:
        """
        Check if request is within rate limit
        Implements token bucket refill.

        Args:
            request: FastAPI request
            is_authenticated: Whether request is authenticated
            is_sensitive: Whether endpoint is sensitive
            
        Returns:
            Tuple of (is_allowed, remaining)
        """
        # Get appropriate limits
        if is_sensitive:
            limit = self.sensitive_rate_limit
            window = self.sensitive_window
        elif is_authenticated:
            limit = self.auth_rate_limit
            window = self.auth_window
        else:
            limit = self.anon_rate_limit
            window = self.anon_window
            
        # Generate Redis key
        key = self._generate_key(request, is_sensitive)
        
        # Track metrics
        client_id = self._get_client_id(request)
        is_api_key = not client_id.startswith("ip:")
        metric_tags = {
            "endpoint": request.url.path,
            "method": request.method,
            "auth_type": "api_key" if is_api_key else "ip",
            "is_sensitive": str(is_sensitive).lower()
        }
        
        # Implement token bucket algorithm with Redis
        now = int(time.time())

        if self._is_redis_available():
            try:
                # Use Redis pipeline for atomic operations
                with self.redis.client.pipeline() as pipe:
                    # Get current number of tokens and last refill time
                    pipe.hmget(key, "tokens", "last_refill")
                    # Set expiry in case of a new key
                    pipe.expire(key, window * 2) # Double the window

                    results = pipe.execute()
                    current_tokens, last_refill_str = results[0]

                    # Initialize if key doesn't exist
                    current_tokens = int(float(current_tokens)) if current_tokens else limit
                    last_refill = int(last_refill_str) if last_refill_str else now

                    # Refill tokens
                    elapsed_time = now - last_refill
                    refill_rate = limit / window  # tokens per second
                    new_tokens = min(limit, current_tokens + (elapsed_time * refill_rate))

                    # Check if under limit
                    is_allowed = new_tokens >= 1
                    remaining = int(new_tokens - 1 if is_allowed else 0)

                    if is_allowed:
                        # Update tokens and last refill time
                        pipe.multi() # Start a new transaction block for atomic updates
                        pipe.hmset(key, {"tokens": remaining, "last_refill": now})
                        pipe.expire(key, window * 2) # Reset expiration
                        pipe.execute()  # Execute transaction

                    # Report metrics
                    metrics.incr(
                        "api.rate_limit.requests", 
                        tags=metric_tags
                    )
                    if not is_allowed:
                        metrics.incr(
                            "api.rate_limit.exceeded", 
                            tags=metric_tags
                        )
                        logger.warning(f"Rate limit exceeded for {client_id} at {request.url.path}")

                    return is_allowed, remaining

            except Exception as e:
                logger.error(f"Error checking rate limit: {str(e)}")
                # Fail open to avoid blocking legitimate traffic
                return True, limit
        else:
            # If Redis is unavailable, fail open but log
            logger.warning("Redis unavailable for rate limiting - allowing request")
            return True, limit

    def _is_redis_available(self) -> bool:
        """Check redis availability with a cooldown to prevent spamming redis with ping requests."""
        now = time.time()
        if now - self.last_redis_check > self.redis_check_cooldown:
            self.last_redis_check = now
            return self.redis.is_available()
        return True # Return true if within cooldown period. Assume redis is still available.

    def get_limit_headers(self, remaining: int, window: Optional[int] = None) -> dict:
        """Get HTTP headers for rate limiting information"""
        if window is None:
            window = self.anon_window
            
        return {
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time()) + window)
        }
            
    async def rate_limit_dependency(
        self,
        request: Request,
        is_authenticated: bool = False,
        is_sensitive: bool = False
    ) -> None:
        """
        FastAPI dependency for rate limiting
        
        Args:
            request: FastAPI request
            is_authenticated: Whether request is authenticated
            is_sensitive: Whether endpoint is sensitive
            
        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Skip rate limiting for paths that aren't protected
        path = request.url.path
        if not any(path.startswith(p) for p in self.protected_paths):
            return

        is_allowed, remaining = self.check_rate_limit(
            request, 
            is_authenticated=is_authenticated,
            is_sensitive=is_sensitive
        )
        
        # Set rate limit headers
        limit_headers = self.get_limit_headers(
            remaining, 
            self.sensitive_window if is_sensitive else (
                self.auth_window if is_authenticated else self.anon_window
            )
        )
        
        for name, value in limit_headers.items():
            request.state.rate_limit_headers = {**getattr(request.state, "rate_limit_headers", {}), name: value}
        
        if not is_allowed:
            # Determine when rate limit resets
            if hasattr(request, "state"):
                reset_time = getattr(request.state, "rate_limit_reset", 0)
            else:
                reset_time = 0
                
            # Calculate seconds until reset
            retry_after = max(1, int(reset_time - time.time()))
            
            # Return 429 with appropriate headers
            headers = {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(remaining),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time)
            }
            
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers=headers
            )
            
# Create rate limiter middleware
async def add_rate_limit_headers(request: Request, call_next):
    """Middleware to add rate limit headers to responses"""
    response = await call_next(request)
    
    # Add rate limit headers from request state
    if hasattr(request.state, "rate_limit_headers"):
        for name, value in request.state.rate_limit_headers.items():
            response.headers[name] = value
            
    return response