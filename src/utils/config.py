# /project_root/src/utils/config.py

import os
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Config:
    def __init__(self):
        """Loads configuration from environment variables and optional JSON file."""
        self.gcp_project = self._get_env("GCP_PROJECT", "your-gcp-project-id")
        self.gcs_bucket = self._get_env("GCS_BUCKET", "your-gcs-bucket-name")
        self.gcs_data_prefix = self._get_env("GCS_DATA_PREFIX", "vertex-ai/data")
        self.gcs_model_prefix = self._get_env("GCS_MODEL_PREFIX", "vertex-ai/models")
        self.model_name = self._get_env("MODEL_NAME", "my-model")
        self.feature_names = self._parse_list_env("FEATURE_NAMES", "feature1,feature2,feature3")
        self.target_variable = self._get_env("TARGET_VARIABLE", "target")
        self.model_type = self._get_env("MODEL_TYPE", "RandomForest")
        self.inference_machine_type = self._get_env("INFERENCE_MACHINE_TYPE", "n1-standard-4") # Vertex AI
        self.training_machine_type = self._get_env("TRAINING_MACHINE_TYPE", "n1-standard-8") # Vertex AI
        self.region = self._get_env("REGION", "us-central1")  # The current region

        # Load from JSON file (optional) - only load from JSON if it exists
        config_file_path = os.environ.get("CONFIG_FILE_PATH",None)
        if config_file_path and os.path.exists(config_file_path):
            try:
                with open(config_file_path, "r") as f:
                    config_data = json.load(f)
                    self._load_from_dict(config_data)
            except FileNotFoundError:
                logger.warning(f"Config file not found: {config_file_path}. Using environment variables.")
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding config file: {e}. Using environment variables.")

        logging.info(f"Configuration loaded: {self.__dict__}")

    def _get_env(self, key, default=None):
        """Gets an environment variable with optional default value."""
        value = os.environ.get(key, default)
        if value is None:
            logger.warning(f"Environment variable '{key}' not set, using default: {default}")
        return value

    def _parse_list_env(self, key, default=None):
        """Parses a comma-separated environment variable into a list."""
        value = self._get_env(key, default)
        if value:
            return [s.strip() for s in value.split(",")]
        return []
    def _parse_bool_env(self, key, default=False):
        """Parses a boolean environment variable."""
        value = self._get_env(key, str(default)).lower()
        if value in ['true', '1', 'yes']:
            return True
        elif value in ['false', '0', 'no']:
            return False
        else:
            logger.warning(f"Invalid boolean value for '{key}': {value}. Using default: {default}")
            return default

    def _load_from_dict(self, config_data):
        """Loads configuration from a dictionary."""
        for key, value in config_data.items():
            setattr(self, key, value)  # Override with file settings

# Singleton instance
config = Config()

if __name__ == '__main__':
    # Example usage for testing
    os.environ["GCS_BUCKET"] = "test-bucket"  # Simulate environment variables
    os.environ["FEATURE_NAMES"] = "a,b,c"
    cfg = Config()
    print(cfg.gcs_bucket)
    print(cfg.feature_names)