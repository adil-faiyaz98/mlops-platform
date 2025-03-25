#!/usr/bin/env python3
import time
import requests
import concurrent.futures
import statistics
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_ENDPOINT = "https://api-dev.mlops.example.com/api/v1/health"
NUM_REQUESTS = 100
CONCURRENT_REQUESTS = 10
MAX_ALLOWED_FAILURES = 5
MAX_ALLOWED_P95_MS = 1000  # 1 second max allowed P95

def make_request():
    try:
        start_time = time.time()
        response = requests.get(API_ENDPOINT, timeout=5)
        elapsed_ms = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            return {"success": True, "latency_ms": elapsed_ms, "status_code": response.status_code}
        else:
            logger.warning(f"Request failed with status code {response.status_code}")
            return {"success": False, "latency_ms": elapsed_ms, "status_code": response.status_code}
    except Exception as e:
        logger.error(f"Request error: {e}")
        return {"success": False, "latency_ms": None, "status_code": None, "error": str(e)}

def main():
    logger.info(f"Starting resilience test with {NUM_REQUESTS} requests, {CONCURRENT_REQUESTS} concurrent")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [executor.submit(make_request) for _ in range(NUM_REQUESTS)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    # Analyze results
    success_count = sum(1 for r in results if r["success"])
    failure_count = NUM_REQUESTS - success_count
    success_rate = (success_count / NUM_REQUESTS) * 100
    
    # Calculate latency statistics (only for successful requests)
    latencies = [r["latency_ms"] for r in results if r["success"] and r["latency_ms"] is not None]
    if latencies:
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
    else:
        avg_latency = p95_latency = p99_latency = float('inf')
    
    # Log results
    logger.info(f"Success rate: {success_rate:.2f}% ({success_count}/{NUM_REQUESTS})")
    logger.info(f"Average latency: {avg_latency:.2f}ms")
    logger.info(f"P95 latency: {p95_latency:.2f}ms")
    logger.info(f"P99 latency: {p99_latency:.2f}ms")
    
    # Verify against SLAs
    passed = True
    if failure_count > MAX_ALLOWED_FAILURES:
        logger.error(f"Too many failures: {failure_count} > {MAX_ALLOWED_FAILURES}")
        passed = False
    
    if p95_latency > MAX_ALLOWED_P95_MS:
        logger.error(f"P95 latency too high: {p95_latency:.2f}ms > {MAX_ALLOWED_P95_MS}ms")
        passed = False
    
    if passed:
        logger.info("✅ Resilience test PASSED")
        return 0
    else:
        logger.error("❌ Resilience test FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())