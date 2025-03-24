import os
import logging
from datetime import datetime, timedelta
from typing import Union, Dict, Any

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, validator
import joblib
import pandas as pd
import numpy as np
from starlette.responses import JSONResponse

from src.utils.config import config
from opentelemetry import trace
from opentelemetry.exporter.prometheus import PrometheusExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from prometheus_client import make_asgi_app
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
import uvicorn  # For local dev server
import logging
import time  # Import the time module

from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Telemetry setup
# Prometheus exporter
exporter = PrometheusExporter(prefix="ml_api")
reader = PeriodicExportingMetricReader(exporter)
resource = Resource.create({"service.name": "ml-api"})  # Add additional configurations
meter_provider = MeterProvider(resource=resource, metric_readers=[reader])

# OTLP exporter (for Jaeger, etc.)
otlp_exporter = OTLPSpanExporter(endpoint="grpc://localhost:4317", insecure=True)  # Replace with your collector endpoint

# Console exporter (for local debugging)
console_exporter = ConsoleSpanExporter()  # Print in the console

trace_provider = TracerProvider(resource=resource)
trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace_provider.add_span_processor(BatchSpanProcessor(console_exporter))

trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

# JWT Security Configuration: Retrieve from Secret Manager (PLACEHOLDER)
# TODO: Replace with retrieval from a secret manager!
JWT_SECRET = os.environ.get("JWT_SECRET", "your-insecure-jwt-secret")  #  **NEVER STORE IN CODE OR ENVIRONMENT, USE A SECRET MANAGER**
JWT_ALGORITHM = "HS256"

# Simulate User database (Replace with a proper DB)
users = {
    "testuser": {"password": "testpassword", "scopes": []}
}

# Add the middleware for authentication.
middleware = [
    Middleware(HTTPSRedirectMiddleware) #Force users to come in using security.
]
app = FastAPI(middleware=middleware)

# FastAPI Instrumentor
FastAPIInstrumentor.instrument_app(app, tracer=tracer)

# Expose Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Load the model
model_path = os.path.join("models", "model.joblib")  # Change to right paths
try:
    model = joblib.load(model_path)
    logging.info(f"Loaded model from {model_path}")
except FileNotFoundError as e:
    logging.critical(f"Model not found: {e}")
    raise HTTPException(status_code=500, detail="Model not found")
except Exception as e:
    logging.error(f"Error loading the model: {e}")
    raise HTTPException(status_code=500, detail="Failed to load model") #Can not process file.

# JWT Security: Configure OAuth2 Password Bearer - **DO NOT USE IN PRODUCTION - SEE BELOW**
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# For the username and password - Create Token for the Session
@app.post("/token") #To connect to the API with authen.
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint to get a JWT token for authentication."""
    user = users.get(form_data.username) # if the User exist, if there's no users.
    if not user or user["password"] != form_data.password: # check password
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30) #Token time.
    access_token = create_access_token(data={"sub": form_data.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    """This function is for if data needs to be added in token or something extra (Like role or number code)"""
    to_encode = data.copy() #copying
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire}) # adding keys for exp
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM) # add signature
    return encoded_jwt #Create Key
# from datetime import timezone

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
    user = users.get(username) # If all the keys doesn't work or no accounts then (send it)

    if user is None: # For User or Account
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": username} # All is validate and the the accounts is correct - Allow with the username.

class PredictionRequest(BaseModel): #All parameters to be working
    feature1: float
    feature2: float
    feature3: float

    @validator('*') # for each feature column
    def check_is_number(cls,value):
      if not isinstance(value, (int,float)):
        raise ValueError('Features must be numbers')
      return value

    class Config: # Sample data
        schema_extra = {
            "example": {
                "feature1": 1.0,
                "feature2": 2.0,
                "feature3": 3.0,
            }
        }

class PredictionResponse(BaseModel): #Output information
    prediction: float
    model_version: str #Version
    username: str #username
@app.post("/predict", response_model=PredictionResponse) # Requires a JWT bearer to connect to it.
async def predict(request: PredictionRequest, current_user: dict = Depends(get_current_user)): # what is called inside the function /API
    """
    Make a prediction based on input features. Authenticates with a valid JWT Bearer token.
    """
    from src.monitoring.metrics import PREDICTION_REQUESTS, PREDICTION_ERRORS, PREDICTION_LATENCY

    PREDICTION_REQUESTS.inc()  # Increment requests by one to monitor
    start_time = time.time()  # Grab the current time.

    with tracer.start_as_current_span("predict_endpoint"): # Get traceability (See Telemetry information, how long what happened?
        try:
            # Validate input
            input_data = pd.DataFrame([request.dict()])
            logging.info(f"Received prediction request: {input_data}") # Log what request

            # Make the prediction
            prediction = model.predict(input_data[config.feature_names])[0] # Test that key, code, numbers

            #Log The Code that was Predicied
            logging.info(f"Prediction: {prediction}")
            latency = time.time() - start_time #Check Time

            #Metric Data
            PREDICTION_LATENCY.observe(latency)

            # what that function does it.
            return PredictionResponse(prediction=float(prediction), model_version=config.model_name, username = current_user["username"]) # what output what code does

        except ValueError as ve:
            logging.error(f"Data Validation error: {ve}")
            PREDICTION_ERRORS.inc()
            raise HTTPException(status_code=400, detail=f"Invalid input: {ve}")
        except KeyError as ke:
            logging.error(f"Missing feature: {ke}")
            PREDICTION_ERRORS.inc()
            raise HTTPException(status_code=400, detail=f"Missing feature: {ke}")
        except Exception as e: #Catches all errors
            PREDICTION_ERRORS.inc() # What happened to prevent the code from coming
            logging.exception("Error during prediction:")  # Logs with traceback
            raise HTTPException(status_code=500, detail=str(e))

#Setup the function that will allow to be seen and check it's status.
@app.get("/health") #Test it
async def health_check(): # Test to be valid
    """
    Health check endpoint.
    """
    return {"status": "healthy"}

#See The Config, we are working on it. (For debugging) - Not for production mode or for internal, (code may be able to do more damage)
@app.get("/config")
async def get_config(): # Test - get the config.
  """Get config values"""
  return config.__dict__

# Uvicorn server setup for local development
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)