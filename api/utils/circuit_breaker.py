import time
import logging
import functools
from enum import Enum
from typing import Callable, Any, Dict, Optional

# Configure logger
logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"     # Circuit is closed, requests flow through
    OPEN = "open"         # Circuit is open, requests are rejected
    HALF_OPEN = "half_open"  # Circuit is half-open, testing if service is back

class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to prevent cascading failures
    when calling external services.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        exception_whitelist: tuple = None,
    ):
        """
        Initialize the circuit breaker
        
        Args:
            name: Name for the circuit breaker
            failure_threshold: Number of consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            exception_whitelist: Exception types that don't count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.exception_whitelist = exception_whitelist or ()
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.metrics = {
            "success_count": 0,
            "failure_count": 0,
            "rejected_count": 0,
            "last_failure_time": 0,
            "last_state_change_time": time.time(),
            "current_state": CircuitState.CLOSED.value
        }
    
    def __call__(self, func):
        """
        Decorator to wrap a function with circuit breaker
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call the function with circuit breaker logic
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self._transition_to_half_open()
            else:
                self._increment_rejected()
                raise CircuitBreakerOpenException(
                    f"Circuit '{self.name}' is OPEN - request rejected"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            if isinstance(e, self.exception_whitelist):
                # Don't count whitelisted exceptions as failures
                raise e
            
            self._on_failure(e)
            raise e
    
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery"""
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit to half-open state"""
        prev_state = self.state
        self.state = CircuitState.HALF_OPEN
        
        if prev_state != CircuitState.HALF_OPEN:
            logger.info(f"Circuit '{self.name}' state: {prev_state.value} -> {self.state.value}")
            self.metrics["last_state_change_time"] = time.time()
            self.metrics["current_state"] = self.state.value
    
    def _transition_to_open(self) -> None:
        """Transition circuit to open state"""
        prev_state = self.state
        self.state = CircuitState.OPEN
        
        if prev_state != CircuitState.OPEN:
            logger.warning(f"Circuit '{self.name}' state: {prev_state.value} -> {self.state.value}")
            self.metrics["last_state_change_time"] = time.time()
            self.metrics["current_state"] = self.state.value
    
    def _transition_to_closed(self) -> None:
        """Transition circuit to closed state"""
        prev_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        
        if prev_state != CircuitState.CLOSED:
            logger.info(f"Circuit '{self.name}' state: {prev_state.value} -> {self.state.value}")
            self.metrics["last_state_change_time"] = time.time()
            self.metrics["current_state"] = self.state.value
    
    def _on_success(self) -> None:
        """Handle successful call"""
        self.metrics["success_count"] += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_closed()
    
    def _on_failure(self, exception: Exception) -> None:
        """Handle failed call"""
        self.last_failure_time = time.time()
        self.failure_count += 1
        self.metrics["failure_count"] += 1
        self.metrics["last_failure_time"] = self.last_failure_time
        
        logger.warning(
            f"Circuit '{self.name}' registered failure ({self.failure_count}/{self.failure_threshold}): {str(exception)}"
        )
        
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self._transition_to_open()
    
    def _increment_rejected(self) -> None:
        """Increment rejected request count"""
        self.metrics["rejected_count"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        return self.metrics
    
    def reset(self) -> None:
        """Reset circuit breaker to closed state"""
        prev_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        
        if prev_state != CircuitState.CLOSED:
            logger.info(f"Circuit '{self.name}' manually reset: {prev_state.value} -> {self.state.value}")
            self.metrics["last_state_change_time"] = time.time()
            self.metrics["current_state"] = self.state.value

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit is open"""
    pass