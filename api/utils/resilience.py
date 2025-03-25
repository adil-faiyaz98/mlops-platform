"""
Resilience utilities for handling failures gracefully.
Implements retries, circuit breakers, and timeouts.
"""
import time
import random
import logging
import functools
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

from src.utils.logging import logger
from src.utils.metrics import get_metrics

# Get metrics instance
metrics = get_metrics()

# Define circuit breaker states
class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation, requests flow through
    OPEN = "open"          # Failed state, requests immediately rejected
    HALF_OPEN = "half_open"  # Testing if service is healthy again

class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    
    Tracks failures and stops sending requests to a failing service
    after a threshold is reached.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exceptions: tuple = (Exception,)
    ):
        """
        Initialize circuit breaker
        
        Args:
            name: Circuit breaker name for metrics/logging
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again (half-open state)
            expected_exceptions: Exception types that trigger the circuit breaker
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        # Internal state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_allowed = False
    
    def __call__(self, func):
        """
        Decorator to apply circuit breaker to a function
        
        Args:
            func: Function to wrap
            
        Returns:
            Wrapped function with circuit breaker
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func, *args, **kwargs):
        """
        Call function with circuit breaker logic
        
        Args:
            func: Function to call
            *args: Arguments to pass
            **kwargs: Keyword arguments to pass
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
            Original exception: If function fails and circuit is still closed
        """
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info(
                    "Circuit half-open, allowing test request", 
                    circuit_name=self.name
                )
                self.state = CircuitState.HALF_OPEN
            else:
                # Track rejected requests
                metrics.incr("circuit_breaker.rejected", tags={
                    "circuit_name": self.name, 
                    "state": self.state.value
                })
                
                raise CircuitBreakerError(
                    f"Circuit {self.name} is open - service unavailable"
                )
        
        try:
            # Call the function
            start_time = time.time()
            result = func(*args, **kwargs)
            
            # Track success
            elapsed = (time.time() - start_time) * 1000
            metrics.timing("circuit_breaker.execution_time", elapsed, tags={
                "circuit_name": self.name, 
                "state": self.state.value,
                "outcome": "success"
            })
            
            # Reset after success
            self._handle_success()
            
            return result
            
        except self.expected_exceptions as e:
            # Track failure
            metrics.incr("circuit_breaker.failure", tags={
                "circuit_name": self.name, 
                "state": self.state.value,
                "exception": e.__class__.__name__
            })
            
            # Update state based on failure
            self._handle_failure()
            
            # Re-raise the exception
            raise
    
    def _handle_success(self):
        """Handle successful function execution"""
        if self.state == CircuitState.HALF_OPEN:
            # Reset circuit after successful test request
            logger.info(
                "Circuit reset after successful test request", 
                circuit_name=self.name
            )
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            
            # Track circuit state change
            metrics.incr("circuit_breaker.state_change", tags={
                "circuit_name": self.name, 
                "from_state": CircuitState.HALF_OPEN.value,
                "to_state": CircuitState.CLOSED.value
            })
    
    def _handle_failure(self):
        """Handle function execution failure"""
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            
            if self.failure_count >= self.failure_threshold:
                # Open the circuit after too many failures
                logger.warning(
                    "Circuit opened after too many failures", 
                    circuit_name=self.name,
                    failure_count=self.failure_count
                )
                self.state = CircuitState.OPEN
                
                # Track circuit state change
                metrics.incr("circuit_breaker.state_change", tags={
                    "circuit_name": self.name, 
                    "from_state": CircuitState.CLOSED.value,
                    "to_state": CircuitState.OPEN.value
                })
                
        elif self.state == CircuitState.HALF_OPEN:
            # Failed in half-open state, go back to open
            logger.warning(
                "Circuit re-opened after failed test request", 
                circuit_name=self.name
            )
            self.state = CircuitState.OPEN
            
            # Track circuit state change
            metrics.incr("circuit_breaker.state_change", tags={
                "circuit_name": self.name, 
                "from_state": CircuitState.HALF_OPEN.value,
                "to_state": CircuitState.OPEN.value
            })

class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass

def with_retry(
    retry_count: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: tuple = (Exception,),
    on_retry=None
):
    """
    Decorator for retrying a function on failure
    
    Args:
        retry_count: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Exception types to retry on
        on_retry: Callback function to execute on retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(retry_count),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            reraise=True,
            before_sleep=on_retry
        )
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped
    return decorator

# Example usage for ML prediction
def predict_with_resilience(model_fn, data, model_name="default"):
    """
    Make a prediction with retry and circuit breaker
    
    Args:
        model_fn: Model prediction function
        data: Input data
        model_name: Model name for metrics
        
    Returns:
        Model prediction
    """
    @with_retry(retry_count=3, min_wait=1.0, max_wait=5.0)
    @CircuitBreaker(name=f"model_{model_name}", failure_threshold=5, recovery_timeout=30)
    def _predict(data):
        # Time the prediction
        with metrics.timed(
            "model_predict", 
            tags={"model": model_name}
        ):
            try:
                prediction = model_fn(data)
                metrics.incr(
                    "model_predict_success", 
                    tags={"model": model_name}
                )
                return prediction
            except Exception as e:
                metrics.incr(
                    "model_predict_error", 
                    tags={"model": model_name, "error": str(e)}
                )
                logger.error(
                    "Model prediction error", 
                    model=model_name, 
                    error=str(e),
                    exc_info=True
                )
                raise
    
    # Make prediction with resilience
    return _predict(data)