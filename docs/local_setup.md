# Local Setup Instructions

````markdown
# MLOps Platform Local Setup Guide

This guide provides instructions for setting up the MLOps Platform locally for development and testing.

## Prerequisites

- Python 3.8+ installed
- Docker and Docker Compose installed
- Git installed
- AWS CLI configured (optional, for S3/SageMaker features)

## Option 1: Setup with Docker

The easiest way to run the platform locally is with Docker and Docker Compose.

### Step 1: Clone the repository

```bash
1. Clone the repository:
git clone https://github.com/adil-faiyaz98/mlops-platform.git
cd mlops-platform


2. Configure environment variables
# Copy the example .env file
cp .env.example .env

# Edit the .env file with your specific configuration
# For local development, you can use the defaults


3. Startup the services
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f api


# API will be accessible at http://localhost:8000/api/v1/


4. Run tests
# Run tests within the container
docker-compose exec api pytest
```

## Option 2: Setup with Python Virtual Environment

### Step 1: Clone the repository

```bash
git clone https://github.com/adil-faiyaz98/mlops-platform.git
cd mlops-platform
```

### Step 2: Create and activate a virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools
```

### Step 4: Configure environment variables

```bash
# On Windows
copy .env.example .env
notepad .env

# On macOS/Linux
cp .env.example .env
nano .env
```

### Step 5: Run Redis Locally

```bash
# Using Docker
docker run -d -p 6379:6379 --name redis redis:6
```

### Step 6: Run the API

```bash
# Run the FastAPI application
uvicorn api.app.main:app --reload --port 8000

# API HOSTED
The API will be accessible at http://localhost:8000/api/v1/
```
````

### Step 7: Run Tests

```bash
# Run tests
pytest
```

# -----------------------

## Development workflow

### To run the components separately

```bash
# Run only the API
docker-compose up api

# Run only Redis
docker-compose up redis
```

### Making Code Changes

```bash
# Rebuild the image after making changes
docker-compose build api

# Restart with new image
docker-compose up -d api

```

### Test API endpoints

```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test prediction endpoint (requires authentication)
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"features": [1.0, 2.0, 3.0, 4.0]}'
```

## Debugging

### For debugging in VS Code, create a launch configuration (.vscode/launch.json):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["api.app.main:app", "--reload", "--port", "8000"],
      "jinja": true,
      "justMyCode": true
    }
  ]
}
```

### Common Issues and Tips

#### Redis Connection

```bash
# Check if Redis container is running
docker ps | grep redis

# Verify Redis connectivity
docker exec -it redis redis-cli ping  # Should return PONG
```

#### Authentication Issues

```bash
Ensure JWT_SECRET_KEY is set in .env file
Check token expiration (default is 60 minutes)
Verify you're using the Bearer format: Authorization: Bearer YOUR_TOKEN

```

#### Model Loading Issues

```bash
Verify model files exist in the expected location
Check S3 permissions if loading from S3
Look for errors in logs: docker-compose logs api

```
