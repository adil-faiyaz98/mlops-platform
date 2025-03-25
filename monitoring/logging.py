import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Configure logging
logger = logging.getLogger('monitoring')
logger.setLevel(logging.DEBUG)  # Set default log level.  Consider using INFO for production.

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create a stream handler to log to the console
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Create a rotating file handler to log to a file
log_file = 'monitoring.log' # or 'logs/monitoring.log' if you want a 'logs' subdirectory
rotating_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)  # 1MB, 5 backups
rotating_handler.setFormatter(formatter)
logger.addHandler(rotating_handler)


log_level_str = os.environ.get('MONITORING_LOG_LEVEL', 'INFO').upper()  # Default to INFO
try:
    log_level = getattr(logging, log_level_str)
    logger.setLevel(log_level)
except AttributeError:
    logger.warning(f"Invalid log level: {log_level_str}. Using INFO.")
    logger.setLevel(logging.INFO)


# Helper functions (Optional, for specific logging tasks)
def log_model_drift(model_name, feature, drift_score):
    logger.warning(f"Model {model_name} - Feature {feature} - Drift Score: {drift_score}")


def log_data_quality_issue(description):
    logger.error(f"Data quality issue: {description}")


def log_performance_metric(metric_name, value, model_name=None):
    if model_name:
        logger.info(f"Model {model_name} - {metric_name}: {value}")
    else:
        logger.info(f"{metric_name}: {value}")



if __name__ == '__main__':
    # Example Usage (when running this file directly)
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")

    log_model_drift("MyModel", "feature_1", 0.7)
    log_data_quality_issue("Missing values in customer ID column.")
    log_performance_metric("Accuracy", 0.85, model_name="MyModel")
    log_performance_metric("CPU Usage", 75.2)  # System-level metric