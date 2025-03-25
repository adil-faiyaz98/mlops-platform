import { check, sleep } from 'k6';
import http from 'k6/http';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('error_rate');
const predictLatency = new Trend('predict_latency');
const batchPredictLatency = new Trend('batch_predict_latency');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up to 10 users
    { duration: '1m', target: 50 },    // Ramp up to 50 users
    { duration: '2m', target: 50 },    // Stay at 50 users for 2 minutes
    { duration: '30s', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests must complete below 500ms
    error_rate: ['rate<0.01'],         // Error rate must be less than 1%
    predict_latency: ['p(95)<300'],    // 95% of predict requests must complete below 300ms
    batch_predict_latency: ['p(95)<1000'], // 95% of batch predict requests must complete below 1s
  },
};

// Base URL for the API
const baseUrl = __ENV.API_URL || 'https://api-dev.mlops.example.com';

// Sample data for predictions
const predictPayload = JSON.stringify({
  features: [1.0, 2.0, 3.0, 4.0]
});

const batchPredictPayload = JSON.stringify({
  inputs: [
    [1.0, 2.0, 3.0, 4.0],
    [5.0, 6.0, 7.0, 8.0],
    [9.0, 10.0, 11.0, 12.0]
  ]
});

// Helper function for checking responses
function checkResponse(response, expectedStatus = 200) {
  const success = response.status === expectedStatus;
  errorRate.add(!success);
  return success;
}

// Main test function
export default function () {
  // Test health endpoint
  const healthRes = http.get(`${baseUrl}/api/v1/health`);
  check(healthRes, {
    'health status is 200': (r) => r.status === 200,
    'health response has status field': (r) => r.json('status') !== undefined,
  });
  
  // Test predict endpoint
  const predictStart = new Date();
  const predictRes = http.post(`${baseUrl}/api/v1/predict`, predictPayload, {
    headers: { 'Content-Type': 'application/json' }
  });
  predictLatency.add(new Date() - predictStart);
  
  check(predictRes, {
    'predict status is 200': (r) => checkResponse(r),
    'predict has predictions': (r) => r.json('prediction') !== undefined,
  });
  
  // Test batch predict endpoint (less frequently)
  if (Math.random() < 0.2) {  // 20% of the time
    const batchStart = new Date();
    const batchRes = http.post(`${baseUrl}/api/v1/batch-predict`, batchPredictPayload, {
      headers: { 'Content-Type': 'application/json' }
    });
    batchPredictLatency.add(new Date() - batchStart);
    
    check(batchRes, {
      'batch predict status is 200': (r) => checkResponse(r),
      'batch predict has predictions array': (r) => Array.isArray(r.json('predictions')),
    });
  }
  
  // Wait between requests to simulate user behavior
  sleep(Math.random() * 3);
}