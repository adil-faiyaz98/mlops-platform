"""
Centralized configuration management for ML pipeline.
Handles environment-specific settings, secrets, and cloud provider settings.
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from google.cloud import secretmanager
from google.auth.exceptions import DefaultCredentialsError
import boto3
from botocore.exceptions import NoCredentialsError

logger = logging.getLogger(__name__)

class CloudProvider(Enum):
    """Supported cloud providers"""
    GCP = "gcp"
    AWS = "aws"
    HYBRID = "hybrid"
    LOCAL = "local"

@dataclass
class CloudConfig:
    """Cloud provider specific configuration"""
    provider: CloudProvider
    project_id: str
    region: str
    credentials_path: Optional[str] = None

    # GCP specific
    gcp_artifact_registry: Optional[str] = None
    gcp_repository: Optional[str] = None

    # AWS specific
    aws_account_id: Optional[str] = None
    aws_role_name: Optional[str] = None
    aws_ecr_repository: Optional[str] = None

@dataclass
class MLConfig:
    """ML pipeline configuration"""
    experiment_name: str
    model_name: str
    deploy_threshold: float
    batch_size: int
    epochs: int
    learning_rate: float
    model_type: str
    target_column: str
    sensitive_feature: str
    mlflow_tracking_uri: str

@dataclass
class AppConfig:
    """Application configuration"""
    service_name: str
    service_port: int
    service_timeout: int
    service_memory: str
    environment: str
    log_level: str
    raw_data_path: str
    train_data_path: str
    test_data_path: str
    processing_script_path: str
    training_script_path: str
    model_dir: str
    validation_script_path: str
    deployer_script_path: str

@dataclass
class DeployConfig:
    """Deployment configuration"""
    serving_container_image_uri: str
    machine_type: str
    min_replica_count: int
    max_replica_count: int

@dataclass
class SecretDefinition:
    """Defines the secrets to retrieve and their corresponding environment variables."""
    secret_name: str
    environment_variable: str

class Config:
    """Centralized configuration management"""

    DEFAULT_ENVIRONMENT = "development"
    CONFIG_DIR_NAME = "config"
    BASE_CONFIG_FILE = "config.json"
    ENVIRONMENT_CONFIG_FILE = "config.{}.json"

    # Define the secrets to be loaded
    SECRETS = [
        SecretDefinition(secret_name="jwt-secret", environment_variable="JWT_SECRET"),
        SecretDefinition(secret_name="db-password", environment_variable="DB_PASSWORD"),
        SecretDefinition(secret_name="api-key", environment_variable="API_KEY")
    ]


    def __init__(self, env: str = None):
        """Initialize configuration for the specified environment"""
        self.env = env or os.environ.get("ENVIRONMENT", self.DEFAULT_ENVIRONMENT)
        self.project_id = os.environ.get("PROJECT_ID", "")
        self.config = {} # Initialize config
        self._load_config()

    def _load_config(self):
        """Load configuration from files and environment variables"""
        # Base configuration path
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.CONFIG_DIR_NAME)

        # Load base config
        base_config_path = os.path.join(config_dir, self.BASE_CONFIG_FILE)
        self.config = self._load_json_config(base_config_path)

        # Load environment-specific config
        env_config_path = os.path.join(config_dir, self.ENVIRONMENT_CONFIG_FILE.format(self.env))
        env_config = self._load_json_config(env_config_path)

        # Merge configs, with environment config taking precedence
        if env_config:
            self._deep_merge(self.config, env_config)

        # Override with environment variables
        self._override_from_env()

        # Initialize specific config objects
        self._init_cloud_config()
        self._init_ml_config()
        self._init_app_config()
        self._init_deploy_config()

        # Load secrets if in non-local environment
        if self.cloud.provider != CloudProvider.LOCAL:
            self._load_secrets()

    def _load_json_config(self, path: str) -> Dict[str, Any]:
        """Load JSON configuration from file"""
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
            else:
                logger.info(f"Config file not found: {path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {path}: {e}")
            raise  # Re-raise to prevent the app from starting with corrupted configuration
        except FileNotFoundError:
             logger.warning(f"Config file not found: {path}")
             return {}

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Deep merge override dict into base dict.  Modifies base in place."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _override_from_env(self) -> None:
        """Override config with environment variables"""
        # Use a more robust approach to traverse the config dictionary

        def set_config_value(config_dict: Dict[str, Any], key_path: list[str], value: str) -> None:
            """Recursively set a value in the config dictionary based on the key path."""
            if len(key_path) == 1:
                if key_path[0] in config_dict:
                    config_dict[key_path[0]] = self._convert_type(value, config_dict[key_path[0]])
                else:
                    logger.warning(f"Invalid key path: {key_path}.  Key '{key_path[0]}' not found.")
                return

            if key_path[0] in config_dict and isinstance(config_dict[key_path[0]], dict):
                set_config_value(config_dict[key_path[0]], key_path[1:], value)
            else:
                logger.warning(f"Invalid key path: {key_path}.  '{key_path[0]}' is not a dictionary or does not exist.")


        for env_var, env_value in os.environ.items():
            if not env_var.isupper(): #Only process uppercase env vars to prevent unexpected behavior.
                continue

            # Map env var prefixes to config sections.
            prefix_map = {
                "ML_": "ml",
                "CLOUD_": "cloud",
                "APP_": "app",
                "DEPLOY_": "deploy",
            }

            for prefix, section in prefix_map.items():
                if env_var.startswith(prefix):
                    key_path = env_var[len(prefix):].lower().split("_")
                    if section in self.config:
                        set_config_value(self.config[section], key_path, env_value)
                    else:
                        logger.warning(f"Section '{section}' not found in config.")


    def _convert_type(self, value: str, reference: Any) -> Any:
        """Convert string value to appropriate type based on reference"""
        try:
            if isinstance(reference, bool):
                return value.lower() in ("true", "yes", "1", "t")
            elif isinstance(reference, int):
                return int(value)
            elif isinstance(reference, float):
                return float(value)
            else:
                return value
        except ValueError as e:
            logger.error(f"Could not convert value '{value}' to type of '{reference}'. Error: {e}")
            return value # Return the original string to avoid crashing, but log the error.


    def _init_cloud_config(self) -> None:
        """Initialize cloud configuration"""
        cloud_cfg = self.config.get("cloud", {})
        provider_str = cloud_cfg.get("provider", "gcp").lower()

        # Determine cloud provider
        try:
            provider = CloudProvider(provider_str)  # Use Enum constructor directly for validation.
        except ValueError:
            logger.warning(f"Invalid cloud provider '{provider_str}'. Defaulting to LOCAL.")
            provider = CloudProvider.LOCAL  # Default to local if invalid.

        # Create cloud config object
        self.cloud = CloudConfig(
            provider=provider,
            project_id=cloud_cfg.get("project_id", self.project_id),
            region=cloud_cfg.get("region", "us-central1"),
            credentials_path=cloud_cfg.get("credentials_path"),
            gcp_artifact_registry=cloud_cfg.get("gcp", {}).get("artifact_registry"),
            gcp_repository=cloud_cfg.get("gcp", {}).get("repository"),
            aws_account_id=cloud_cfg.get("aws", {}).get("account_id"),
            aws_role_name=cloud_cfg.get("aws", {}).get("role_name"),
            aws_ecr_repository=cloud_cfg.get("aws", {}).get("ecr_repository")
        )

    def _init_ml_config(self) -> None:
        """Initialize ML configuration"""
        ml_cfg = self.config.get("ml", {})
        self.ml = MLConfig(
            experiment_name=ml_cfg.get("experiment_name", "ml-experiment"),
            model_name=ml_cfg.get("model_name", "ml-model"),
            deploy_threshold=ml_cfg.get("deploy_threshold", 0.7),
            batch_size=ml_cfg.get("batch_size", 32),
            epochs=ml_cfg.get("epochs", 10),
            learning_rate=ml_cfg.get("learning_rate", 0.001),
            model_type=ml_cfg.get("model_type", "LogisticRegression"),
            target_column=ml_cfg.get("target_column", "target"),
            sensitive_feature=ml_cfg.get("sensitive_feature", "feature1"),
            mlflow_tracking_uri=ml_cfg.get("mlflow_tracking_uri", "file:///app/mlruns")
        )

    def _init_app_config(self) -> None:
        """Initialize application configuration"""
        app_cfg = self.config.get("app", {})
        self.app = AppConfig(
            service_name=app_cfg.get("service_name", "ml-service"),
            service_port=app_cfg.get("service_port", 8080),
            service_timeout=app_cfg.get("service_timeout", 3600),
            service_memory=app_cfg.get("service_memory", "2048M"),
            environment=self.env,
            log_level=app_cfg.get("log_level", "INFO"),
            raw_data_path=app_cfg.get("raw_data_path", "raw.csv"),
            train_data_path=app_cfg.get("train_data_path", "train.csv"),
            test_data_path=app_cfg.get("test_data_path", "test.csv"),
            processing_script_path=app_cfg.get("processing_script_path", "src/data_processing/processing.py"),
            training_script_path=app_cfg.get("training_script_path", "src/model_training/train.py"),
            model_dir=app_cfg.get("model_dir", "src/model_training/"),
            validation_script_path=app_cfg.get("validation_script_path", "src/data_processing/validation.py"),
            deployer_script_path=app_cfg.get("deployer_script_path", "src/deployment/deployer.py")
        )

    def _init_deploy_config(self) -> None:
        """Initialize deployment configuration"""
        deploy_cfg = self.config.get("deploy", {})
        self.deploy = DeployConfig(
            serving_container_image_uri=deploy_cfg.get("serving_container_image_uri", "us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-0:latest"),
            machine_type=deploy_cfg.get("machine_type", "n1-standard-2"),
            min_replica_count=deploy_cfg.get("min_replica_count", 1),
            max_replica_count=deploy_cfg.get("max_replica_count", 1)
        )

    def _load_secrets(self) -> None:
        """Load secrets from Google Secret Manager or AWS Secrets Manager"""
        try:
            if self.cloud.provider in (CloudProvider.GCP, CloudProvider.HYBRID):
                self._load_gcp_secrets()
            elif self.cloud.provider == CloudProvider.AWS:
                self._load_aws_secrets()
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}", exc_info=True)  # Log with traceback for better debugging


    def _load_gcp_secrets(self) -> None:
        """Load secrets from Google Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            parent = f"projects/{self.cloud.project_id}"

            for secret_def in self.SECRETS:
                try:
                    secret_path = f"{parent}/secrets/{secret_def.secret_name}/versions/latest"
                    response = client.access_secret_version(request={"name": secret_path})
                    os.environ[secret_def.environment_variable] = response.payload.data.decode("UTF-8")
                    logger.debug(f"Loaded secret {secret_def.secret_name} from GCP Secret Manager")

                except Exception as e:
                    logger.warning(f"Could not load secret: {secret_def.secret_name} - {e}")

        except DefaultCredentialsError:
            logger.warning("GCP credentials not available, skipping secret loading")
        except Exception as e:
            logger.error(f"Error loading GCP secrets: {e}", exc_info=True)

    def _load_aws_secrets(self) -> None:
        """Load secrets from AWS Secrets Manager"""
        try:
            session = boto3.session.Session()
            client = session.client(service_name="secretsmanager", region_name=self.cloud.region)

            for secret_def in self.SECRETS:
                try:
                    response = client.get_secret_value(SecretId=secret_def.secret_name)
                    if "SecretString" in response:
                        secret_value = response["SecretString"]
                    else:
                        secret_value = response["SecretBinary"].decode("utf-8")
                    os.environ[secret_def.environment_variable] = secret_value
                    logger.debug(f"Loaded secret {secret_def.secret_name} from AWS Secrets Manager")


                except Exception as e:
                    logger.warning(f"Could not load secret: {secret_def.secret_name} - {e}")

        except NoCredentialsError:
            logger.warning("AWS credentials not available, skipping secret loading")
        except Exception as e:
            logger.error(f"Error loading AWS secrets: {e}", exc_info=True)