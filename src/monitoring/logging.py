# src/monitoring/logging.py
import logging
import sys

def setup_logging(level=logging.INFO):
    """Sets up logging configuration."""
    logger = logging.getLogger()
    logger.setLevel(level)

    # Create handlers
    stream_handler = logging.StreamHandler(sys.stdout) # Log to standard output

    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(stream_handler)

    return logger

# Example Usage (in other modules):
# logger = logging.getLogger(__name__)
# logger.info("This is an info message")