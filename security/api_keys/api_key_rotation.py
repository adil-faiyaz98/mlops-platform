"""
API Key management for secure API access with automatic rotation capability.
"""
import os
import time
import uuid
import hmac
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.utils.config import Config
from src.utils.secrets import SecretManager

import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class APIKeyManager:
    """
    Manages API keys with rotation capabilities
    - Creates API keys with expiration
    - Validates keys
    - Rotates keys automatically
    - Handles key revocation
    """
    
    def __init__(
        self, 
        config: Optional[Config] = None,
        secret_manager: Optional[SecretManager] = None,
        signing_secret_rotation_interval_days: int = 30  # Added parameter for rotation interval
    ):
        """
        Initialize API Key Manager
        
        Args:
            config: Configuration object
            secret_manager: Secret manager for storing keys
        """
        self.config = config or Config()
        self.secret_manager = secret_manager or SecretManager(self.config)
        
        # API key settings
        key_config = self.config.get("security", {}).get("api_keys", {})
        self.key_length = key_config.get("length", 32)
        self.default_expiry_days = key_config.get("expiry_days", 90)
        self.rotation_warning_days = key_config.get("rotation_warning_days", 15)
        
        self.signing_secret_rotation_interval_days = signing_secret_rotation_interval_days

        self.signing_secret = self._get_signing_secret()
        self.last_signing_secret_rotation = self._get_last_signing_secret_rotation()

    def _get_last_signing_secret_rotation(self) -> int:
        """Get the timestamp of the last signing secret rotation"""
        secret_name = "api-key-signing-secret-rotation"
        try:
            rotation_timestamp = self.secret_manager.get_secret(secret_name)
            if rotation_timestamp:
                return int(rotation_timestamp)
        except Exception as e:
            logger.warning(f"Could not retrieve last signing secret rotation: {e}")
        return 0 # Return 0 if not set

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type(Exception))  # Retry decorator with exponential backoff
    def _set_secret_with_retry(self, secret_name: str, secret_value: any):
        """Helper function for setting secrets with retry logic"""
        self.secret_manager.set_secret(secret_name, secret_value)

    def _get_signing_secret(self) -> str:
        """Get or generate signing secret for API keys and rotate if necessary"""
        secret_name = "api-key-signing-secret"
        
        # Check if signing secret needs rotation
        if self._should_rotate_signing_secret():
            return self._rotate_signing_secret()
            
        # Try to get from secret manager
        try:
            secret = self.secret_manager.get_secret(secret_name)
            if secret:
                return secret
        except Exception as e:
            logger.warning(f"Could not retrieve signing secret: {e}")
            
        # Generate new secret
        new_secret = secrets.token_hex(32)
        
        # Try to store in secret manager
        try:
            self._set_secret_with_retry(secret_name, new_secret)
        except Exception as e:
            logger.warning(f"Could not store signing secret: {e}")
            
        return new_secret

    def _should_rotate_signing_secret(self) -> bool:
        """Check if the signing secret should be rotated based on time interval"""
        now = int(time.time())
        time_since_rotation = now - self.last_signing_secret_rotation
        days_since_rotation = time_since_rotation / (60 * 60 * 24)
        return days_since_rotation >= self.signing_secret_rotation_interval_days

    def _rotate_signing_secret(self) -> str:
        """Rotate the signing secret"""
        secret_name = "api-key-signing-secret"
        rotation_secret_name = "api-key-signing-secret-rotation"

        logger.info("Rotating signing secret for API keys...")
        new_secret = secrets.token_hex(32)

        try:
            # Store the new signing secret
            self._set_secret_with_retry(secret_name, new_secret)

            # Update the rotation timestamp
            now = int(time.time())
            self._set_secret_with_retry(rotation_secret_name, now)
            self.last_signing_secret_rotation = now
            self.signing_secret = new_secret # Update current secret

            logger.info("Successfully rotated signing secret.")
            return new_secret # Return new secret

        except Exception as e:
            logger.error(f"Error rotating signing secret: {e}")
            return self.signing_secret # Revert to the old secret
            

    def generate_key(self, client_id: str, expiry_days: Optional[int] = None, include_jti: bool = False) -> Dict[str, str]:
        """
        Generate a new API key for a client
        
        Args:
            client_id: Client identifier
            expiry_days: Days until key expires (default from config)
            include_jti: Whether to include a JTI (JWT ID) claim for more granular control

        Returns:
            Dict with key info: api_key, prefix, expires_at
        """
        # Set expiry
        expiry_days = expiry_days or self.default_expiry_days
        expires_at = datetime.utcnow() + timedelta(days=expiry_days)
        expires_timestamp = int(expires_at.timestamp())
        
        # Generate unique components
        key_id = str(uuid.uuid4())
        random_part = secrets.token_hex(self.key_length)

        jti = None
        if include_jti:
            jti = str(uuid.uuid4()) # Generate a UUID for JTI claim
        
        # Create key signature
        signature = self._sign_key(client_id, key_id, expires_timestamp, random_part, jti=jti)
        
        # Format as API key (first 8 chars are key prefix for identification)
        prefix = key_id[:8]
        api_key = f"{prefix}.{key_id}.{expires_timestamp}.{random_part}.{signature}"

        if include_jti:
            api_key = f"{api_key}.{jti}" # Append the JTI
        
        # Store key metadata (not the key itself)
        key_metadata = {
            "client_id": client_id,
            "key_id": key_id,
            "prefix": prefix,
            "expires_at": expires_timestamp,
            "created_at": int(datetime.utcnow().timestamp()),
            "revoked": False,
            "jti": jti,
        }
        
        # Store in secret manager
        secret_name = f"api-key-{prefix}"
        try:
            self._set_secret_with_retry(secret_name, key_metadata)
        except Exception as e:
            logger.error(f"Failed to store API key metadata: {e}")
            raise # Re-raise the exception to indicate key generation failure

        return {
            "api_key": api_key,
            "prefix": prefix,
            "expires_at": expires_at.isoformat()
        }
    
    def _sign_key(self, client_id: str, key_id: str, expires_at: int, random_part: str, jti: Optional[str] = None) -> str:
        """
        Create HMAC signature for API key
        
        Args:
            client_id: Client identifier
            key_id: Key UUID
            expires_at: Expiration timestamp
            random_part: Random component of key
            jti: Optional JTI (JWT ID)

        Returns:
            Signature string
        """
        message = f"{client_id}:{key_id}:{expires_at}:{random_part}"
        if jti:
            message = f"{message}:{jti}" # Include jti in signature

        signature = hmac.new(
            self.signing_secret.encode(),
            message.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def validate_key(self, api_key: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Validate an API key
        
        Args:
            api_key: API key to validate
            
        Returns:
            Tuple of (is_valid, client_id, error_message, jti)
        """
        # Parse key components
        try:
            parts = api_key.split(".")
            if len(parts) == 5:
                prefix, key_id, expires_at_str, random_part, signature = parts
                jti = None
            elif len(parts) == 6:
                prefix, key_id, expires_at_str, random_part, signature, jti = parts
            else:
                return False, None, "Invalid API key format", None # Wrong number of parts
            expires_at = int(expires_at_str)
        except (ValueError, AttributeError):
            return False, None, "Invalid API key format", None # Incorrect format

        # Check expiration
        now = int(datetime.utcnow().timestamp())
        if expires_at < now:
            return False, None, "API key expired", None
        
        # Get key metadata from secret manager
        try:
            secret_name = f"api-key-{prefix}"
            key_metadata = self.secret_manager.get_secret(secret_name)
            
            if not key_metadata:
                return False, None, "Unknown API key", None
                
            # Check if key was revoked
            if key_metadata.get("revoked", False):
                return False, None, "API key revoked", None
                
            # Extract client_id from metadata
            client_id = key_metadata.get("client_id")
            stored_key_id = key_metadata.get("key_id")
            stored_jti = key_metadata.get("jti")
            
            # Verify key components match
            if stored_key_id != key_id:
                return False, None, "Invalid API key", None
            
            if jti and stored_jti != jti:
                 return False, None, "Invalid JTI", None # JTI doesn't match

            # Verify signature
            expected_signature = self._sign_key(
                client_id, key_id, expires_at, random_part, jti=jti
            )
            
            if signature != expected_signature:
                return False, None, "Invalid API key signature", None
                
            # Key is valid
            return True, client_id, None, jti
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False, None, "Error validating API key", None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type(Exception))
    def revoke_key(self, prefix: str, jti: Optional[str] = None) -> bool:
        """
        Revoke an API key or a specific JTI
        
        Args:
            prefix: Key prefix
            jti: Optional JTI (JWT ID) to revoke

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get key metadata
            secret_name = f"api-key-{prefix}"
            key_metadata = self.secret_manager.get_secret(secret_name)
            
            if not key_metadata:
                logger.warning(f"Attempted to revoke unknown API key: {prefix}")
                return False

            client_id = key_metadata.get("client_id")
                
            if jti:
                # Revoke specific JTI (requires more complex logic)
                if not key_metadata.get("jti") == jti:
                    logger.warning(f"Attempted to revoke unknown JTI: {jti} for key {prefix}")
                    return False

                key_metadata["revoked"] = True # Simplest JTI revocation - treat whole key as revoked
                key_metadata["revoked_jti"] = jti

            else:
                # Mark as revoked (whole key)
                key_metadata["revoked"] = True
                key_metadata["revoked_at"] = int(datetime.utcnow().timestamp())
            
            # Update metadata
            self._set_secret_with_retry(secret_name, key_metadata)

            log_message = f"Revoked API key {prefix} for client {client_id}"
            if jti:
                log_message = f"Revoked JTI {jti} of API key {prefix} for client {client_id}"
            logger.info(log_message)

            return True
            
        except Exception as e:
            logger.error(f"Error revoking API key {prefix}: {e}")
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
           retry=retry_if_exception_type(Exception))
    def rotate_key(self, prefix: str) -> Optional[Dict[str, str]]:
        """
        Rotate an API key (generate new key and revoke old)
        
        Args:
            prefix: Key prefix to rotate
            
        Returns:
            Dict with new key info or None if rotation failed
        """
        try:
            # Get key metadata
            secret_name = f"api-key-{prefix}"
            key_metadata = self.secret_manager.get_secret(secret_name)
            
            if not key_metadata:
                logger.warning(f"Attempted to rotate unknown API key: {prefix}")
                return None
                
            client_id = key_metadata.get("client_id")
            
            # Generate new key with same expiry and JTI setting
            current_expiry = datetime.fromtimestamp(key_metadata.get("expires_at", 0))
            now = datetime.utcnow()
            days_remaining = (current_expiry - now).days
            expiry_days = max(days_remaining, self.default_expiry_days)
            
            include_jti = key_metadata.get("jti") is not None # Preserve JTI setting

            # Generate new key
            new_key = self.generate_key(client_id, expiry_days, include_jti=include_jti)
            
            # Mark old key as to be revoked (grace period)
            key_metadata["pending_revocation"] = True
            key_metadata["pending_revocation_time"] = int((now + timedelta(days=7)).timestamp())
            self._set_secret_with_retry(secret_name, key_metadata) # Use retry

            logger.info(f"Rotated API key {prefix} for client {client_id}")
            return new_key
            
        except Exception as e:
            logger.error(f"Error rotating API key {prefix}: {e}")
            return None

    def list_keys_for_client(self, client_id: str) -> List[Dict[str, any]]:
        """
        List all API keys for a client
        
        Args:
            client_id: Client identifier
            
        Returns:
            List of key metadata
        """
        keys = []
        
        # List secrets with api-key prefix
        try:
            secrets = self.secret_manager.list_secrets("api-key-")
            
            for secret_name, metadata in secrets.items():
                if metadata.get("client_id") == client_id:
                    # Add key info without sensitive data
                    key_info = {
                        "prefix": metadata.get("prefix"),
                        "created_at": datetime.fromtimestamp(metadata.get("created_at", 0)).isoformat(),
                        "expires_at": datetime.fromtimestamp(metadata.get("expires_at", 0)).isoformat(),
                        "revoked": metadata.get("revoked", False),
                        "status": self._get_key_status(metadata),
                        "jti": metadata.get("jti") # Include JTI
                    }
                    keys.append(key_info)
                    
            return keys
            
        except Exception as e:
            logger.error(f"Error listing API keys for client {client_id}: {e}")
            raise  # Re-raise the exception
    
    def _get_key_status(self, key_metadata: Dict[str, any]) -> str:
        """Determine key status for reporting"""
        if key_metadata.get("revoked", False):
            return "revoked"
            
        expires_at = key_metadata.get("expires_at", 0)
        now = int(datetime.utcnow().timestamp())
        
        if expires_at < now:
            return "expired"
            
        # Check if expiring soon
        warning_threshold = now + (self.rotation_warning_days * 86400)
        if expires_at < warning_threshold:
            return "expiring_soon"
            
        if key_metadata.get("pending_revocation", False):
            return "pending_revocation"
            
        return "active"