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
    
@dataclass
class AppConfig:
    """Application configuration"""
    service_name: str
    service_port: int
    service_timeout: int
    service_memory: str
    environment: str
    log_level: str

class Config:
    """Centralized configuration management"""
    
    def __init__(self, env: str = None):
        """Initialize configuration for the specified environment"""
        self.env = env or os.environ.get("ENVIRONMENT", "development")
        self.project_id = os.environ.get("PROJECT_ID", "")
        self._load_config()
        
    def _load_config(self):
        """Load configuration from files and environment variables"""
        # Base configuration path
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        
        # Load base config
        base_config_path = os.path.join(config_dir, "config.json")
        self.config = self._load_json_config(base_config_path)
        
        # Load environment-specific config
        env_config_path = os.path.join(config_dir, f"config.{self.env}.json")
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
        
        # Load secrets if in non-local environment
        if self.cloud.provider != CloudProvider.LOCAL:
            self._load_secrets()
            
    def _load_json_config(self, path: str) -> Dict[str, Any]:
        """Load JSON configuration from file"""
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"Error loading config from {path}: {e}")
            return {}
            
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Deep merge override dict into base dict"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
                
    def _override_from_env(self) -> None:
        """Override config with environment variables"""
        # Example: ML_MODEL_NAME environment variable will override config["ml"]["model_name"]
        for env_var, env_value in os.environ.items():
            # Handle ML_ prefixed environment variables
            if env_var.startswith("ML_"):
                parts = env_var[3:].lower().split("_")
                if len(parts) == 2 and parts[0] in self.config and parts[1] in self.config[parts[0]]:
                    self.config[parts[0]][parts[1]] = self._convert_type(env_value, self.config[parts[0]][parts[1]])
                    
            # Handle CLOUD_ prefixed environment variables
            elif env_var.startswith("CLOUD_"):
                parts = env_var[6:].lower().split("_")
                if len(parts) == 2 and parts[0] in self.config["cloud"] and parts[1] in self.config["cloud"][parts[0]]:
                    self.config["cloud"][parts[0]][parts[1]] = self._convert_type(env_value, self.config["cloud"][parts[0]][parts[1]])
                    
            # Handle APP_ prefixed environment variables
            elif env_var.startswith("APP_"):
                parts = env_var[4:].lower().split("_")
                if len(parts) == 2 and parts[0] in self.config["app"] and parts[1] in self.config["app"][parts[0]]:
                    self.config["app"][parts[0]][parts[1]] = self._convert_type(env_value, self.config["app"][parts[0]][parts[1]])
    
    def _convert_type(self, value: str, reference: Any) -> Any:
        """Convert string value to appropriate type based on reference"""
        if isinstance(reference, bool):
            return value.lower() in ("true", "yes", "1", "t")
        elif isinstance(reference, int):
            return int(value)
        elif isinstance(reference, float):
            return float(value)
        else:
            return value
            
    def _init_cloud_config(self) -> None:
        """Initialize cloud configuration"""
        cloud_cfg = self.config.get("cloud", {})
        provider_str = cloud_cfg.get("provider", "gcp").lower()
        
        # Determine cloud provider
        if provider_str == "aws":
            provider = CloudProvider.AWS
        elif provider_str == "gcp":
            provider = CloudProvider.GCP
        elif provider_str == "hybrid":
            provider = CloudProvider.HYBRID
        else:
            provider = CloudProvider.LOCAL
            
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
            learning_rate=ml_cfg.get("learning_rate", 0.001)
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
            log_level=app_cfg.get("log_level", "INFO")
        )
        
    def _load_secrets(self) -> None:
        """Load secrets from Google Secret Manager"""
        try:
            if self.cloud.provider in (CloudProvider.GCP, CloudProvider.HYBRID):
                self._load_gcp_secrets()
            elif self.cloud.provider == CloudProvider.AWS:
                self._load_aws_secrets()
        except Exception as e:
            logger.warning(f"Failed to load secrets: {e}")
            
    def _load_gcp_secrets(self) -> None:
        """Load secrets from Google Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            parent = f"projects/{self.cloud.project_id}"
            
            # Define secrets to fetch
            secrets_to_load = {
                "JWT_SECRET": "jwt-secret",
                "DB_PASSWORD": "db-password",
                "API_KEY": "api-key"
            }
            
            for env_var, secret_name in secrets_to_load.items():
                try:
                    secret_path = f"{parent}/secrets/{secret_name}/versions/latest"
                    response = client.access_secret_version(name=secret_path)
                    os.environ[env_var] = response.payload.data.decode("UTF-8")
                except Exception:
                    logger.warning(f"Could not load secret: {secret_name}")
                    
        except DefaultCredentialsError:
            logger.warning("GCP credentials not available, skipping secret loading")
            
    def _load_aws_secrets(self) -> None:
        """Load secrets from AWS Secrets Manager"""
        # Implement AWS Secrets Manager integration here
        pass