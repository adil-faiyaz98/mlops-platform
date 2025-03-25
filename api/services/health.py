"""
Health check service for API and dependencies
"""
import os
import time
import socket
import logging
import platform
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import Depends

from api.models.health import HealthCheckResponse, HealthStatus, DependencyHealth
from api.cache.enhanced_redis_cache import EnhancedRedisCache
from api.utils.config import Config

logger = logging.getLogger(__name__)

# Track start time for uptime reporting
START_TIME = time.time()

class HealthService:
    """Service for health checks and system status"""
    
    def __init__(
        self,
        config: Optional[Config] = None,
        redis_cache: Optional[EnhancedRedisCache] = None
    ):
        """
        Initialize health service
        
        Args:
            config: Configuration object
            redis_cache: Redis cache instance
        """
        self.config = config or Config()
        self.redis_cache = redis_cache
        self.version = os.environ.get("APP_VERSION", "0.1.0")
        self.environment = self.config.get("environment", "development")
        self.hostname = socket.gethostname()
        
    async def check_health(self) -> HealthCheckResponse:
        """
        Perform comprehensive health check
        
        Returns:
            Health check response
        """
        # Track dependencies health
        dependencies = {}
        overall_status = HealthStatus.HEALTHY
        
        # Check Redis health if available
        if self.redis_cache:
            redis_health = self.redis_cache.health_check()
            redis_status = HealthStatus.HEALTHY
            
            if redis_health["status"] == "degraded":
                redis_status = HealthStatus.DEGRADED
                overall_status = HealthStatus.DEGRADED
            elif redis_health["status"] == "unhealthy":
                redis_status = HealthStatus.UNHEALTHY
                overall_status = HealthStatus.UNHEALTHY
                
            dependencies["redis"] = DependencyHealth(
                status=redis_status,
                latency_ms=redis_health["latency_ms"],
                message=redis_health["message"],
                last_check=datetime.now(timezone.utc).isoformat()
            )
            
        # Check model service
        model_status, model_latency, model_message = self._check_model_service()
        if model_status != HealthStatus.HEALTHY and overall_status == HealthStatus.HEALTHY:
            overall_status = model_status
            
        dependencies["model"] = DependencyHealth(
            status=model_status,
            latency_ms=model_latency,
            message=model_message,
            last_check=datetime.now(timezone.utc).isoformat()
        )
        
        # Database health check (if applicable)
        # TODO: Add database health check if needed
        
        # Return health check response
        return HealthCheckResponse(
            status=overall_status,
            version=self.version,
            environment=self.environment,
            dependencies=dependencies,
            uptime_seconds=time.time() - START_TIME
        )
        
    def _check_model_service(self):
        """
        Check model service health
        
        Returns:
            Tuple of (status, latency, message)
        """
        try:
            model_path = self.config.get("model", {}).get("path")
            
            # Simple check if model path exists
            if not model_path or not os.path.exists(model_path):
                return HealthStatus.UNHEALTHY, 0, "Model path not found"
                
            # TODO: Add more sophisticated model health check
            # For example, run a simple prediction on a test input
            
            return HealthStatus.HEALTHY, 0, None
            
        except Exception as e:
            logger.error(f"Model health check failed: {e}")
            return HealthStatus.UNHEALTHY, 0, str(e)