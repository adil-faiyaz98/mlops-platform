import time
import random  # Simulate metrics, replace with real calculations
from monitoring.logging import logger  # Import the logger from logging.py


class MetricsCollector:
    """
    Collects and reports metrics related to model performance, data quality,
    and system health.
    """

    def __init__(self, model_name="MyModel"):
        self.model_name = model_name
        self.start_time = time.time()

    def calculate_accuracy(self, predictions, ground_truth):
        """Calculates the accuracy of the model."""
        try:
            # Replace with your actual accuracy calculation
            correct_predictions = sum(p == g for p, g in zip(predictions, ground_truth))
            accuracy = correct_predictions / len(ground_truth)
            logger.info(f"Model {self.model_name} - Accuracy: {accuracy:.4f}")
            return accuracy
        except Exception as e:
            logger.error(f"Error calculating accuracy: {e}")
            return None

    def check_data_completeness(self, data):
        """Checks for missing values in the data."""
        try:
            missing_values = sum(1 for row in data if None in row)  # Simplified check
            completeness = 1 - (missing_values / len(data))
            logger.info(f"Data completeness: {completeness:.4f}")
            return completeness
        except Exception as e:
            logger.error(f"Error checking data completeness: {e}")
            return None

    def collect_system_metrics(self):
        """Collects CPU and Memory usage (simulated here)."""
        try:
            # Replace with actual system metrics collection using psutil or similar library
            cpu_usage = random.uniform(10, 90)  # Simulate CPU usage
            memory_usage = random.uniform(20, 80) # Simulate memory usage
            logger.info(f"CPU Usage: {cpu_usage:.2f}%")
            logger.info(f"Memory Usage: {memory_usage:.2f}%")
            return cpu_usage, memory_usage
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return None, None

    def report_latency(self, inference_time):
        """Reports the latency of the model's inference."""
        logger.info(f"Model {self.model_name} - Inference latency: {inference_time:.4f} seconds")

    def uptime(self):
        """Calculates the uptime of the monitoring process."""
        uptime_seconds = time.time() - self.start_time
        logger.info(f"Monitoring system uptime: {uptime_seconds:.2f} seconds")

    def custom_metric(self, metric_name, value):
         """Logs a custom metric with a given name and value."""
         logger.info(f"Custom metric '{metric_name}': {value}")

if __name__ == '__main__':
    # Example usage
    metrics_collector = MetricsCollector(model_name="FraudDetectionModel")

    # Simulate some data
    predictions = [0, 1, 0, 1, 0]
    ground_truth = [0, 1, 1, 1, 0]
    data = [[1, 2, 3], [4, None, 6], [7, 8, 9]]  # Simulate missing value

    metrics_collector.calculate_accuracy(predictions, ground_truth)
    metrics_collector.check_data_completeness(data)
    metrics_collector.collect_system_metrics()
    metrics_collector.report_latency(0.015)  # Simulate 15ms latency
    metrics_collector.uptime()
    metrics_collector.custom_metric("number_of_requests", 120)