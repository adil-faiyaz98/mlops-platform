import time
import logging
from typing import Optional, List, Dict, Callable
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
import jwt

from api.utils.config import Config

logger = logging.getLogger(__name__)

# Set up security scheme
security = HTTPBearer()


class AuthManager:
    """Handles authentication and authorization"""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize auth manager"""
        self.config = config or Config()
        self.auth_config = self.config.get("security", {}).get("auth", {})
        
        # JWT settings
        self.jwt_secret = self.auth_config.get("jwt_secret", "your-secret-key")
        self.jwt_algorithm = self.auth_config.get("jwt_algorithm", "HS256")
        self.jwt_expiration = self.auth_config.get("jwt_expiration_minutes", 60)
        
    def verify_token(
        self, 
        token: str
    ) -> Dict:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            # Check if token is expired
            if payload.get('exp', 0) < time.time():
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
                
            return payload
            
        except jwt.DecodeError:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
            
    async def get_current_user(
        self, 
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict:
        """
        Get current user from token
        
        Args:
            credentials: HTTP Authorization credentials
            
        Returns:
            User information from token
            
        Raises:
            HTTPException: If authentication fails
        """
        token = credentials.credentials
        payload = self.verify_token(token)
        
        # Return user information from token
        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "scopes": payload.get("scopes", []),
            "exp": payload.get("exp")
        }


# Create auth dependency
auth_manager = AuthManager()


def require_scope(required_scope: str):
    """
    Dependency to require specific scope
    
    Args:
        required_scope: Required scope
        
    Returns:
        Dependency function
    """
    async def scope_validator(
        request: Request,
        user: Dict = Depends(auth_manager.get_current_user)
    ):
        scopes = user.get("scopes", [])
        
        if required_scope not in scopes:
            logger.warning(
                f"Access denied: User {user.get('username')} missing required scope {required_scope}"
            )
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required scope: {required_scope}"
            )
            
        # Add user to request state
        request.state.user = user
        return user
        
    return scope_validator