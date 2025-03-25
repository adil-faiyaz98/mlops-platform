import pytest
import time
from unittest.mock import Mock, patch

from api.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, CircuitState

def test_circuit_breaker_initialization():
    """Test circuit breaker initialization with default values"""
    cb = CircuitBreaker("test-circuit")
    
    assert cb.name == "test-circuit"
    assert cb.failure_threshold == 5
    assert cb.recovery_timeout == 30
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.last_failure_time == 0

def test_circuit_breaker_successful_execution():
    """Test successful execution doesn't change circuit state"""
    cb = CircuitBreaker("test-circuit")
    
    # Define test function
    test_func = Mock(return_value="success")
    
    # Wrap and call
    wrapped = cb(test_func)
    result = wrapped()
    
    # Assertions
    assert result == "success"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.metrics["success_count"] == 1
    assert cb.metrics["failure_count"] == 0
    test_func.assert_called_once()

def test_circuit_breaker_failure_below_threshold():
    """Test failures below threshold don't open circuit"""
    cb = CircuitBreaker("test-circuit", failure_threshold=3)
    
    # Define test function that raises exception
    test_func = Mock(side_effect=ValueError("test error"))
    wrapped = cb(test_func)
    
    # Execute function twice (below threshold of 3)
    for _ in range(2):
        with pytest.raises(ValueError):
            wrapped()
    
    # Circuit should still be closed
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 2
    assert cb.metrics["failure_count"] == 2
    assert cb.metrics["success_count"] == 0

def test_circuit_breaker_opens_after_threshold():
    """Test circuit opens after failure threshold is reached"""
    cb = CircuitBreaker("test-circuit", failure_threshold=3)
    
    # Define test function that raises exception
    test_func = Mock(side_effect=ValueError("test error"))
    wrapped = cb(test_func)
    
    # Execute function three times (meets threshold)
    for _ in range(3):
        with pytest.raises(ValueError):
            wrapped()
    
    # Circuit should now be open
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 3
    assert cb.metrics["failure_count"] == 3
    
    # Further calls should be rejected without calling the function
    with pytest.raises(CircuitBreakerOpenException):
        wrapped()
    
    # Function shouldn't have been called a 4th time
    assert test_func.call_count == 3
    assert cb.metrics["rejected_count"] == 1

def test_circuit_breaker_half_open_after_timeout():
    """Test circuit transitions to half-open after timeout"""
    cb = CircuitBreaker("test-circuit", failure_threshold=2, recovery_timeout=0.1)
    
    # Define test function that raises exception
    test_func = Mock(side_effect=ValueError("test error"))
    wrapped = cb(test_func)
    
    # Trigger circuit open
    for _ in range(2):
        with pytest.raises(ValueError):
            wrapped()
    
    assert cb.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(0.2)
    
    # Next call should attempt to close circuit and execute function
    # But function still fails
    with pytest.raises(ValueError):
        wrapped()
    
    # Circuit should go back to open
    assert cb.state == CircuitState.OPEN
    assert test_func.call_count == 3  # Called one more time during recovery attempt

def test_circuit_breaker_closes_after_successful_recovery():
    """Test circuit closes after successful execution in half-open state"""
    cb = CircuitBreaker("test-circuit", failure_threshold=2, recovery_timeout=0.1)
    
    # Mock function that fails initially, then succeeds
    test_func = Mock()
    test_func.side_effect = [ValueError("error1"), ValueError("error2"), "success"]
    wrapped = cb(test_func)
    
    # First two calls fail and open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            wrapped()
    
    assert cb.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(0.2)
    
    # Next call should succeed and close circuit
    result = wrapped()
    assert result == "success"
    assert cb.state == CircuitState.CLOSED
    assert test_func.call_count == 3

def test_circuit_breaker_whitelisted_exceptions():
    """Test that whitelisted exceptions don't count as failures"""
    cb = CircuitBreaker(
        "test-circuit", 
        failure_threshold=2, 
        exception_whitelist=(ValueError,)
    )
    
    # Define test function that raises whitelisted exception
    value_error_func = Mock(side_effect=ValueError("whitelisted error"))
    wrapped_value = cb(value_error_func)
    
    # ValueErrors shouldn't count toward failure threshold
    for _ in range(3):
        with pytest.raises(ValueError):
            wrapped_value()
    
    # Circuit should still be closed
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    
    # Non-whitelisted exception should count
    type_error_func = Mock(side_effect=TypeError("non-whitelisted error"))
    wrapped_type = cb(type_error_func)
    
    for _ in range(2):
        with pytest.raises(TypeError):
            wrapped_type()
    
    # Now circuit should be open
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2

def test_circuit_breaker_manual_reset():
    """Test manual reset of circuit breaker"""
    cb = CircuitBreaker("test-circuit", failure_threshold=2)
    
    # Define test function that raises exception
    test_func = Mock(side_effect=ValueError("test error"))
    wrapped = cb(test_func)
    
    # Open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            wrapped()
    
    assert cb.state == CircuitState.OPEN
    
    # Reset circuit manually
    cb.reset()
    
    # Circuit should be closed
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    
    # Should be able to call function again
    with pytest.raises(ValueError):
        wrapped()
    
    assert cb.failure_count == 1