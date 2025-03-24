# /project_root/src/monitoring/metrics.py
from prometheus_client import Counter, Histogram

# Define Prometheus metrics
PREDICTION_REQUESTS = Counter(
    'ml_api_prediction_requests_total',
    'Total number of prediction requests'
)

PREDICTION_ERRORS = Counter(
    'ml_api_prediction_errors_total',
    'Total number of prediction errors'
)

PREDICTION_LATENCY = Histogram(
    'ml_api_prediction_latency_seconds',
    'Prediction latency in seconds',
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10)  # Customize buckets
)