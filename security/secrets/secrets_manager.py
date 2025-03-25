# Modified secrets_manager.py
"""
Unified Secrets Manager for AWS and GCP.
"""
import json
import logging
from typing import Dict, Optional, Any, Union
import boto3
from botocore.exceptions import ClientError
from google.cloud import secretmanager
from mlops_project.utils.config import Config  # Assuming Config is used for settings

logger = logging.getLogger(__name__)

class SecretsManager:
    """
    Unified interface for accessing secrets from AWS and GCP Secret Manager.
    """

    def __init__(
        self,
        provider: str = None,
        config: Config = None,
        aws_prefix: str = "mlops-platform/",
        aws_region: str = "us-east-1",  # Added aws_region
        gcp_project: str = None
    ):
        """Initialize SecretsManager."""
        self.config = config or Config()
        self.provider = provider or self.config.get("cloud", {}).get("provider", "gcp")
        self._cache = {}

        # AWS Attributes
        self.aws_region = aws_region or self.config.get("cloud", {}).get("aws", {}).get("region", "us-east-1")
        self.aws_client = None
        self.aws_prefix = aws_prefix

        # GCP Attributes
        self.gcp_project = gcp_project or self.config.get("cloud", {}).get("project_id")  # Explicitly retrieve project ID
        self.gcp_client = None

        # Initialize client based on the provider
        if self.provider.lower() == "aws":
            self._init_aws_client()
        else:
            self._init_gcp_client()

    def _init_aws_client(self):
        """Initialize AWS Secrets Manager client."""
        try:
            self.aws_client = boto3.client(
                "secretsmanager",
                region_name=self.aws_region
            )
        except Exception as e:
            logger.error(f"Error initializing AWS client: {e}")
            self.aws_client = None  # Set to None in case of initialization failure


    def _init_gcp_client(self):
        """Initialize Google Cloud Secret Manager client."""
        try:
            self.gcp_client = secretmanager.SecretManagerServiceClient()
        except Exception as e:
            logger.error(f"Error initializing GCP client: {e}")
            self.gcp_client = None  # Set to None in case of initialization failure



    def get_secret(
        self,
        secret_name: str,
        version: str = "latest",
        use_cache: bool = True
    ) -> Optional[Union[str, Dict]]:
        """Get a secret value from the Secrets Manager."""
        cache_key = f"{secret_name}:{version}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        if self.provider.lower() == "aws":
            secret_value = self._get_aws_secret(secret_name, version)
        elif self.provider.lower() == "gcp":
            secret_value = self._get_gcp_secret(secret_name, version)
        else:
            logger.error(f"Unsupported provider: {self.provider}")
            return None

        if use_cache and secret_value is not None:
            self._cache[cache_key] = secret_value

        return secret_value

    def _get_aws_secret(self, secret_name: str, version: str) -> Optional[Union[str, Dict]]:
        """Get secret from AWS Secrets Manager."""
        if not self.aws_client:
            logger.error("AWS client is not initialized.")
            return None

        secret_name = self._get_full_secret_name(secret_name)

        try:
            version_param = {}
            if version != "latest":
                version_param["VersionId"] = version

            response = self.aws_client.get_secret_value(
                SecretId=secret_name,
                **version_param
            )

            if "SecretString" in response:
                secret_value = response["SecretString"]
                try:
                    return json.loads(secret_value)  # Attempt to parse JSON
                except json.JSONDecodeError:
                    return secret_value
            else:
                return response["SecretBinary"]

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning(f"AWS Secret {secret_name} not found.")
            elif e.response["Error"]["Code"] == "AccessDeniedException":
                logger.error(f"AWS Access denied to secret {secret_name}.")
            else:
                logger.error(f"AWS Error retrieving secret {secret_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching AWS secret {secret_name}: {e}")
            return None


    def _get_gcp_secret(self, secret_name: str, version: str) -> Optional[Union[str, Dict]]:
        """Get secret from Google Cloud Secret Manager."""
        if not self.gcp_client or not self.gcp_project:
            logger.error("GCP client is not initialized or project not configured.")
            return None

        try:
            # Construct the secret path.
            secret_path = f"projects/{self.gcp_project}/secrets/{secret_name}/versions/{version}"
            response = self.gcp_client.access_secret_version(name=secret_path)
            secret_value = response.payload.data.decode("UTF-8")

            try:
                return json.loads(secret_value)  # Attempt to parse JSON
            except json.JSONDecodeError:
                return secret_value

        except Exception as e:
            logger.error(f"GCP Error accessing secret {secret_name}: {e}")
            return None


    def create_or_update_secret(
        self,
        secret_name: str,
        secret_value: Union[str, Dict, bytes],
        description: str = None,
        tags: Dict = None
    ) -> bool:
        """Create or update a secret based on the configured cloud provider."""
        if isinstance(secret_value, dict):
            secret_value = json.dumps(secret_value)

        if self.provider.lower() == "aws":
            return self._create_or_update_aws_secret(secret_name, secret_value, description, tags)
        elif self.provider.lower() == "gcp":
            return self._create_or_update_gcp_secret(secret_name, secret_value, description, tags)
        else:
            logger.error(f"Unsupported cloud provider: {self.provider}")
            return False

    def _create_or_update_aws_secret(
        self,
        secret_name: str,
        secret_value: Union[str, bytes],
        description: str,
        tags: Dict
    ) -> bool:
        """Create or update secret in AWS Secrets Manager."""
        if not self.aws_client:
            logger.error("AWS client is not initialized.")
            return False

        secret_name = self._get_full_secret_name(secret_name)

        try:
            try:
                self.aws_client.describe_secret(SecretId=secret_name)
                # Update secret if it exists
                update_params = {"SecretId": secret_name}
                if isinstance(secret_value, bytes):
                    update_params["SecretBinary"] = secret_value
                else:
                    update_params["SecretString"] = secret_value

                self.aws_client.update_secret(**update_params)
                logger.info(f"AWS Secret updated: {secret_name}")
            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    # Create secret if it doesn't exist
                    create_params = {
                        "Name": secret_name,
                        "Description": description or f"Secret for {secret_name}"
                    }
                    if isinstance(secret_value, bytes):
                        create_params["SecretBinary"] = secret_value
                    else:
                        create_params["SecretString"] = secret_value

                    if tags:
                        create_params["Tags"] = [{"Key": k, "Value": v} for k, v in tags.items()]

                    self.aws_client.create_secret(**create_params)
                    logger.info(f"AWS Secret created: {secret_name}")
                else:
                    raise  # Re-raise other client errors

            # Clear cache for the secret
            self._clear_secret_cache(secret_name)
            return True

        except Exception as e:
            logger.error(f"AWS Error creating/updating secret {secret_name}: {e}")
            return False


    def _create_or_update_gcp_secret(
        self,
        secret_name: str,
        secret_value: Union[str, bytes],
        description: str,
        tags: Dict
    ) -> bool:
        """Create or update secret in Google Cloud Secret Manager."""
        if not self.gcp_client or not self.gcp_project:
            logger.error("GCP client is not initialized or project not configured.")
            return False

        try:
            parent = f"projects/{self.gcp_project}"
            secret_path = f"{parent}/secrets/{secret_name}"

            # Ensure secret_value is bytes
            if isinstance(secret_value, str):
                secret_bytes = secret_value.encode("UTF-8")
            elif not isinstance(secret_value, bytes):
                secret_bytes = str(secret_value).encode("UTF-8")
            else:
                secret_bytes = secret_value

            try:
                # Check if secret exists
                self.gcp_client.get_secret(name=secret_path)
                # Add new version if it does
                self.gcp_client.add_secret_version(
                    parent=secret_path,
                    payload={"data": secret_bytes}
                )
                logger.info(f"GCP New version added to secret: {secret_name}")
            except Exception:
                # Create secret if it doesn't exist
                labels = {k.replace("-", "_"): v.replace("-", "_") for k, v in tags.items()} if tags else None
                create_secret_request = secretmanager.CreateSecretRequest(
                    parent=parent,
                    secret_id=secret_name,
                    secret={
                        "replication": {"automatic": {}},
                        "labels": labels
                    }
                )
                secret_obj = self.gcp_client.create_secret(request=create_secret_request)
                secret_path = secret_obj.name

                # Add initial version
                version_path = f"{parent}/secrets/{secret_name}" # Ensure correct path
                self.gcp_client.add_secret_version(
                    parent=version_path,
                    payload={"data": secret_bytes}
                )
                logger.info(f"GCP Secret created: {secret_name}")

            # Clear the cache for the secret
            self._clear_secret_cache(secret_name)
            return True

        except Exception as e:
            logger.error(f"GCP Error creating/updating secret {secret_name}: {e}")
            return False


    def delete_secret(
        self,
        secret_name: str,
        recovery_window_days: int = None
    ) -> bool:
        """Delete a secret."""
        if self.provider.lower() == "aws":
            return self._delete_aws_secret(secret_name, recovery_window_days)
        elif self.provider.lower() == "gcp":
            return self._delete_gcp_secret(secret_name)
        else:
            logger.error(f"Unsupported provider: {self.provider}")
            return False

    def _delete_aws_secret(self, secret_name: str, recovery_window_days: int) -> bool:
        """Delete secret from AWS Secrets Manager."""
        if not self.aws_client:
            logger.error("AWS client is not initialized.")
            return False

        secret_name = self._get_full_secret_name(secret_name)

        try:
            delete_params = {"SecretId": secret_name}
            if recovery_window_days is not None:
                delete_params["RecoveryWindowInDays"] = recovery_window_days
            else:
                delete_params["ForceDeleteWithoutRecovery"] = True  # Force delete if no recovery window
            self.aws_client.delete_secret(**delete_params)
            logger.info(f"AWS Secret deleted: {secret_name}")

            # Clear cache for the secret
            self._clear_secret_cache(secret_name)
            return True

        except ClientError as e:
            logger.error(f"AWS Error deleting secret {secret_name}: {e}")
            return False

    def _delete_gcp_secret(self, secret_name: str) -> bool:
        """Delete secret from Google Cloud Secret Manager."""
        if not self.gcp_client or not self.gcp_project:
            logger.error("GCP client is not initialized or project not configured.")
            return False

        try:
            parent = f"projects/{self.gcp_project}"
            secret_path = f"{parent}/secrets/{secret_name}"
            self.gcp_client.delete_secret(name=secret_path)
            logger.info(f"GCP Secret deleted: {secret_name}")

            # Clear cache for the secret
            self._clear_secret_cache(secret_name)
            return True

        except Exception as e:
            logger.error(f"GCP Error deleting secret {secret_name}: {e}")
            return False

    def list_secrets(self, name_filter: Optional[str] = None) -> Dict[str, Dict]:
        """List secrets with an optional name filter."""
        if self.provider.lower() == "aws":
            return self._list_aws_secrets(name_filter)
        elif self.provider.lower() == "gcp":
            return self._list_gcp_secrets(name_filter)
        else:
            logger.error(f"Unsupported provider: {self.provider}")
            return {}

    def _list_aws_secrets(self, name_filter: Optional[str] = None) -> Dict[str, Dict]:
        """List secrets from AWS Secrets Manager with optional filtering."""
        if not self.aws_client:
            logger.error("AWS client is not initialized.")
            return {}

        results = {}
        try:
            paginator = self.aws_client.get_paginator('list_secrets')
            page_iterator = paginator.paginate(
                Filters=[{'Key': 'name', 'Values': [self._get_full_secret_name("") + "*"]}]
            )

            for page in page_iterator:
                for secret in page.get("SecretList", []):
                    secret_name = secret.get("Name")
                    # remove the prefix
                    cleaned_secret_name = self._remove_prefix(secret_name)

                    if name_filter and name_filter not in cleaned_secret_name:
                        continue
                    results[cleaned_secret_name] = {
                        "arn": secret.get("ARN"),
                        "created_date": secret.get("CreatedDate"),
                    }  # Basic info
            return results
        except Exception as e:
            logger.error(f"AWS Error listing secrets: {e}")
            return {}

    def _list_gcp_secrets(self, name_filter: Optional[str] = None) -> Dict[str, Dict]:
        """List secrets from Google Cloud Secret Manager with optional filtering."""
        if not self.gcp_client or not self.gcp_project:
            logger.error("GCP client is not initialized or project not configured.")
            return {}

        results = {}
        try:
            parent = f"projects/{self.gcp_project}"
            for secret in self.gcp_client.list_secrets(request={"parent": parent}):
                secret_name = secret.name.split("/")[-1]  # Just the name
                if name_filter and name_filter not in secret_name:
                    continue
                results[secret_name] = {"create_time": secret.create_time}  # Basic info
            return results
        except Exception as e:
            logger.error(f"GCP Error listing secrets: {e}")
            return {}

    def enable_rotation(
        self,
        secret_name: str,
        rotation_lambda_arn: str,
        rotation_days: int = 30
    ) -> bool:
        """Enable secret rotation (AWS only)."""
        if self.provider.lower() != "aws":
            logger.warning("Secret rotation is only supported for AWS.")
            return False

        if not self.aws_client:
            logger.error("AWS client is not initialized.")
            return False
        try:
            secret_name = self._get_full_secret_name(secret_name)

            self.aws_client.rotate_secret(
                SecretId=secret_name,
                RotationLambdaARN=rotation_lambda_arn,
                RotationRules={'AutomaticallyAfterDays': rotation_days}
            )

            logger.info(f"Rotation enabled for AWS secret {secret_name}")
            return True
        except Exception as e:
            logger.error(f"AWS Error enabling rotation for secret {secret_name}: {e}")
            return False

    def _get_full_secret_name(self, secret_name: str) -> str:
        """Adds the prefix to the given secret name."""
        return f"{self.aws_prefix}{secret_name}" if not secret_name.startswith(self.aws_prefix) else secret_name

    def _remove_prefix(self, secret_name: str) -> str:
        """Removes the prefix from the given secret name."""
        return secret_name[len(self.aws_prefix):] if secret_name.startswith(self.aws_prefix) else secret_name

    def _clear_secret_cache(self, secret_name):
         """Clears cache entries for a specific secret."""
         keys_to_delete = [key for key in self._cache if key.startswith(f"{secret_name}:")]
         for key in keys_to_delete:
             del self._cache[key]

############################################################################################################
# Example Usage
############################################################################################################
your_config = Config()
if __name__ == "__main__":
    # Initialize SecretsManager
    try:
        secrets_manager = SecretsManager(config=your_config, provider="aws")
        # Access a secret
        secret_value = secrets_manager.get_secret("your_secret_name")

        if secret_value:
            # Use the secret
            print("The secret value is:", secret_value)
        else:
            # Handle the case where the secret was not found
            print("The secret was not found")
    except Exception as e:
        # Handle the exception
        print("The secret was not found")