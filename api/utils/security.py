import os
from datetime import timedelta, datetime, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Union

JWT_SECRET = os.environ.get("JWT_SECRET")  #  **NEVER STORE IN CODE OR ENVIRONMENT, USE A SECRET MANAGER**
JWT_ALGORITHM = "HS256"
# JWT Security Configuration: Retrieve from Secret Manager (PLACEHOLDER)

# Simulate User database (Replace with a proper DB)
fake_users_db = {
    "testuser": {"password": "testpassword", "scopes": []}
}

def authenticate_user(db, username, password): #To check in User or the API
    user = db.get(username)
    if not user:
        return False
    if user["password"] == password:
        return user
    return False

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None): #To create the code with time expired
    """This function is for if data needs to be added in token or something extra (Like role or number code)"""
    to_encode = data.copy() #copying
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire}) # adding keys for exp
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM) # add signature
    return encoded_jwt #Create Key

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") #Check Key (For DB user)

async def get_current_user(token: str = Depends(oauth2_scheme)): # For Token to access the code,
    """Dependency to validate the access token."""
    try: # Check for the key, and that payload to see key
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM]) # decode from the code
        username: str = payload.get("sub") #Get the payload info on what their user and information is
        if username is None: # Check user and all that in the payload
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, #Error
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.exceptions.JWTError as ex: #Catch Exception for error log.
        print(ex) # To load traceback info (for debugging reasons).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = fake_users_db.get(username) # If all the keys doesn't work or no accounts then (send it)

    if user is None: # For User or Account
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": username} # All is validate and the the accounts is correct - Allow with the username.

# Example using Google Cloud Secrets Manager
from google.cloud import secretmanager

PROJECT_ID = os.environ.get("PROJECT_ID")
def get_secret(secret_id, version_id="latest"):
    """Access the payload for the given secret version if one exists."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}" #Set project
    response = client.access_secret_version(request={"name": name})
    payload = response.payload.data.decode("UTF-8") #Load Data.
    return payload