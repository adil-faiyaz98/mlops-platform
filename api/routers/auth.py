from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta, datetime, timezone
import jwt
from api.utils.security import create_access_token, get_current_user
from api.utils.security import fake_users_db, authenticate_user

router = APIRouter()

# JWT Security: Configure OAuth2 Password Bearer - **DO NOT USE IN PRODUCTION - SEE BELOW**
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") #Look into database for User

# For the username and password - Create Token for the Session
@router.post("/token") #To connect to the API with authen.
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint to get a JWT token for authentication."""
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user: # check password
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30) #Token time.
    access_token = create_access_token(data={"sub": form_data.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}