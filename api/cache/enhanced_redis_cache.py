import redis
import time
import logging
import os
from typing import List, Any, Dict, Optional

from api.utils.config import Config
from api.utils.metrics import get_metrics

logger = logging.getLogger(__name__)
metrics = get_metrics()

class EnhancedRedisCache:
    """
    Enhanced Redis cache with features such as:
    - Automatic (de)serialization
    - Circuit breaker for fault tolerance
    - Configurable expiration time
    - Metrics for monitoring
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize Redis cache
        
        Args:
            redis_url: Redis connection URL
            config: Configuration object
        """
        self.config = config or Config()
        cache_config = self.config.get("cache", {})
        
        self.redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.enabled = cache_config.get("enabled", True)
        self.default_ttl = cache_config.get("default_ttl", 60)  # seconds
        self.serialization_format = cache_config.get("serialization_format", "json")  # or pickle
        
        # Circuit breaker settings
        self.failure_threshold = cache_config.get("failure_threshold", 5)
        self.circuit_reset_time = cache_config.get("circuit_reset_time", 30)  # seconds
        
        self.client = None
        self.circuit_open = False
        self.last_circuit_open_time = 0
        self.failure_count = 0
        
        # Initialize Redis client
        if self.enabled:
            self._init_client()

    def _init_client(self):
        """Initialize Redis client"""
        try:
            start_time = time.time()
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping() #Check if everything is all right
            metrics.timing("redis.init_latency", time.time() - start_time)
            
        except Exception as e:
            self.client = None
            logger.error(f"Error initializing Redis client: {e}")
            self._handle_failure("init")

    def _serialize(self, value: Any) -> str:
        """Serialize value for caching"""
        if self.serialization_format == "pickle":
            import pickle
            return pickle.dumps(value)
        else: # json (default)
            import json
            return json.dumps(value)
            
    def _deserialize(self, value: str) -> Any:
        """Deserialize value from cache"""
        if value is None:
            return None
            
        if self.serialization_format == "pickle":
            import pickle
            return pickle.loads(value)
        else: # json (default)
            import json
            return json.loads(value)

    def _handle_failure(self, operation: str):
        """
        Handle Redis failure using circuit breaker
        Opens the circuit if failure threshold is reached.
        """
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold and not self.circuit_open:
            # Open the circuit
            self.circuit_open = True
            self.last_circuit_open_time = time.time()
            
            logger.warning(
                f"Circuit breaker open due to Redis failures (operation: {operation})"
            )
            
            metrics.incr("redis.circuit_open")

    def is_available(self) -> bool:
        """
        Check if Redis is available
        
        Returns:
            True if Redis is available, False otherwise
        """
        # Check circuit breaker status
        if self.circuit_open:
            # Check if circuit breaker has been open for longer than reset time
            if time.time() - self.last_circuit_open_time > self.circuit_reset_time:
                # Reset circuit breaker
                self.circuit_open = False
                self.failure_count = 0
                logger.info("Circuit breaker reset: Redis is available again")
            else:
                # Circuit is still open
                return False
        
        # Perform a ping check
        try:
            if self.client is None:
                self._init_client()
            if self.client is not None:
                self.client.ping()
            return True
            
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            self._handle_failure("ping")
            return False
            
    def generate_key(self, *args) -> str:
        """Generate a cache key from arguments"""
        return ":".join([str(arg) for arg in args])

    # Add these methods to the EnhancedRedisCache class after the generate_key method

    def mget(self, keys: List[str]) -> List[Any]:
        """
        Get multiple values from cache
        
        Args:
            keys: List of cache keys
            
        Returns:
            List of cached values (None for keys not found)
        """
        if not self.enabled or self.circuit_open or self.client is None:
            return [None] * len(keys)
            
        try:
            start_time = time.time()
            results = self.client.mget(keys)
            
            # Deserialize results
            values = [self._deserialize(result) for result in results]
            
            # Track metrics
            metrics.timing("redis.mget_latency", time.time() - start_time)
            metrics.incr("redis.mget", value=len(keys))
            
            return values
            
        except Exception as e:
            logger.error(f"Redis mget error: {e}")
            self._handle_failure("mget")
            return [None] * len(keys)
            
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.enabled or self.circuit_open or self.client is None:
            return False
            
        try:
            return bool(self.client.exists(key))
            
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            self._handle_failure("exists")
            return False
            
    def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time on key
        
        Args:
            key: Cache key
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or self.circuit_open or self.client is None:
            return False
            
        try:
            return bool(self.client.expire(key, ttl))
            
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            self._handle_failure("expire")
            return False
            
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment value in cache
        
        Args:
            key: Cache key
            amount: Amount to increment
            
        Returns:
            New value or None if operation failed
        """
        if not self.enabled or self.circuit_open or self.client is None:
            return None
            
        try:
            return self.client.incrby(key, amount)
            
        except Exception as e:
            logger.error(f"Redis increment error: {e}")
            self._handle_failure("increment")
            return None
            
    def health_check(self) -> Dict[str, Any]:
        """
        Check Redis health
        
        Returns:
            Health check result
        """
        status = "healthy"
        message = None
        latency = 0
        
        if not self.enabled:
            return {
                "status": "disabled",
                "latency_ms": 0,
                "message": "Redis cache is disabled"
            }
            
        if self.circuit_open:
            return {
                "status": "unhealthy",
                "latency_ms": 0,
                "message": f"Circuit breaker open, will reset in {self.circuit_reset_time - (time.time() - self.last_circuit_open_time):.1f}s"
            }
            
        if self.client is None:
            return {
                "status": "unhealthy",
                "latency_ms": 0,
                "message": "Redis client not initialized"
            }
            
        try:
            # Measure latency
            start_time = time.time()
            self.client.ping()
            latency = (time.time() - start_time) * 1000  # ms
            
            # Check if latency is acceptable
            if latency > 100:  # 100ms threshold
                status = "degraded"
                message = f"High Redis latency: {latency:.2f}ms"
                
        except Exception as e:
            status = "unhealthy"
            message = f"Redis health check failed: {str(e)}"
            
        return {
            "status": status,
            "latency_ms": round(latency, 2),
            "message": message
        }