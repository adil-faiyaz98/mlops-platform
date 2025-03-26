import os
import secrets
import logging
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED
from pydantic import BaseModel, validator, SecretStr

from api.exceptions import AuthenticationError, AuthorizationError
from api.utils.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Load settings
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

# API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# JWT settings from environment variables with secure defaults
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    if os.environ.get("ENVIRONMENT") == "development":
        JWT_SECRET_KEY = "dev-secret-do-not-use-in-production"
        logger.warning("Using insecure JWT secret key in development environment")
    else:
        raise ValueError("JWT_SECRET_KEY environment variable is not set")

JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Data models
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    scopes: List[str] = []

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: SecretStr
    full_name: Optional[str] = None
    
    @validator('password')
    def password_strength(cls, v):
        """Validate password strength"""
        password = v.get_secret_value()
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one number")
        if not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/`~" for c in password):
            raise ValueError("Password must contain at least one special character")
        return v

# API key storage (in a real app, this would be in a database)
# This is just for demonstration - in production, use a proper database
api_keys = {
    # "actual-api-key-hash": {"client_id": "client1", "scopes": ["predict"]}
}

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT token
    
    Args:
        data: Data to encode in token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to create access token: {e}", exc_info=True)
        raise AuthenticationError(f"Token creation failed")

def verify_api_key(api_key: str = Security(api_key_header)) -> Dict:
    """
    Verify an API key
    
    Args:
        api_key: The API key to verify
        
    Returns:
        API key metadata
        
    Raises:
        AuthenticationError: If API key is invalid
    """
    if not api_key:
        raise AuthenticationError("API key required")
    
    # Hash the API key
    hashed_key = get_password_hash(api_key)
    
    # In production, you would look up the hash in a database
    if hashed_key not in api_keys:
        # Use constant-time comparison to prevent timing attacks
        # and add a small delay to prevent brute force
        secrets.compare_digest(hashed_key, "dummy-hash")
        time.sleep(0.1)
        
        logger.warning(f"Invalid API key attempt")
        raise AuthenticationError("Invalid API key")
    
    return api_keys[hashed_key]

def verify_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Verify a JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Token data
        
    Raises:
        AuthenticationError: If token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise AuthenticationError("Invalid token")
        
        scopes = payload.get("scopes", [])
        return TokenData(username=username, scopes=scopes)
    
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")

def validate_scopes(required_scopes: List[str], token_data: TokenData = Depends(verify_token)) -> TokenData:
    """
    Validate that token has required scopes
    
    Args:
        required_scopes: List of required scopes
        token_data: Token data from verify_token
        
    Returns:
        Token data if validation passes
        
    Raises:
        AuthorizationError: If token doesn't have required scopes
    """
    for scope in required_scopes:
        if scope not in token_data.scopes:
            logger.warning(f"User {token_data.username} missing required scope: {scope}")
            raise AuthorizationError(f"Missing required scope: {scope}")
    
    return token_data

def get_current_user(token_data: TokenData = Depends(verify_token)) -> User:
    """
    Get current user from token
    
    Args:
        token_data: Token data from verify_token
        
    Returns:
        User object
        
    Raises:
        AuthenticationError: If user not found or disabled
    """
    # In production, load the user from a database
    # This is just for demonstration
    if token_data.username == "testuser":
        return User(
            username=token_data.username,
            email="test@example.com",
            full_name="Test User",
            disabled=False,
            scopes=token_data.scopes
        )
    
    raise AuthenticationError("User not found")