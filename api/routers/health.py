"""
Health check endpoints
"""
from fastapi import APIRouter, Depends

from api.models.health import HealthCheckResponse
from api.services.health import HealthService

router = APIRouter(prefix="/api/v1", tags=["health"])

@router.get("/health", response_model=HealthCheckResponse, summary="Check API health")
async def health_check(health_service: HealthService = Depends()):
    """
    Check the health of the API and its dependencies
    
    Returns:
        Health check response
    """
    return await health_service.check_health()

@router.get("/readiness", summary="Readiness check")
async def readiness_check():
    """
    Simple readiness check endpoint for Kubernetes probes
    
    Returns:
        Simple OK response
    """
    return {"status": "ok"}

@router.get("/liveness", summary="Liveness check")
async def liveness_check():
    """
    Simple liveness check endpoint for Kubernetes probes
    
    Returns:
        Simple OK response
    """
    return {"status": "ok"}