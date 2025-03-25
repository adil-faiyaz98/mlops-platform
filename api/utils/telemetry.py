"""
OpenTelemetry setup and configuration for the API.
This module provides a unified approach to tracing, metrics, and logging.
"""
import os
from typing import Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from api.utils.config import Config
from api.utils.logging import logger

def setup_telemetry(app=None, service_name: str = "mlops-api", config: Optional[Config] = None) -> None:
    """
    Set up OpenTelemetry tracing, metrics, and logging
    
    Args:
        app: FastAPI application to instrument
        service_name: Name of the service
        config: Configuration object
    """
    config = config or Config()
    telemetry_config = config.get("telemetry", {})
    
    # Get configuration from environment or config file
    otlp_endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", 
        telemetry_config.get("otlp_endpoint", "http://localhost:4317")
    )
    
    # Determine sampling ratio (100% in dev, configurable in prod)
    environment = os.environ.get("ENVIRONMENT", "development")
    if environment == "production":
        sampling_ratio = float(os.environ.get(
            "OTEL_SAMPLING_RATIO", 
            telemetry_config.get("sampling_ratio", "0.1")
        ))
    else:
        sampling_ratio = 1.0
    
    # Set up resources with service information
    version = os.environ.get("APP_VERSION", "unknown")
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": version,
        "service.environment": environment,
        "telemetry.sdk.language": "python",
        "deployment.environment": environment
    })
    
    # Configure trace provider with appropriate sampling strategy
    sampler = TraceIdRatioBased(sampling_ratio)
    trace_provider = TracerProvider(
        resource=resource,
        sampler=sampler
    )
    
    # Set up OTLP exporter for sending traces to collector
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace_provider.add_span_processor(span_processor)
    
    # Set global trace provider
    trace.set_tracer_provider(trace_provider)
    
    # Set up propagator for distributed tracing
    propagator = TraceContextTextMapPropagator()
    
    # Get tracer
    tracer = trace.get_tracer(service_name, version)
    
    # Instrument libraries
    RequestsInstrumentor().instrument()
    RedisInstrumentor().instrument()
    
    # Instrument FastAPI if app is provided
    if app:
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=trace_provider,
            excluded_urls="/health,/metrics",
        )
    
    logger.info(
        "OpenTelemetry initialized", 
        service=service_name, 
        version=version,
        environment=environment,
        sampling_ratio=sampling_ratio,
        otlp_endpoint=otlp_endpoint
    )
    
    return tracer

def create_span(name: str, context: Optional[Dict] = None) -> trace.Span:
    """
    Create a new span for tracing
    
    Args:
        name: Name of the span
        context: Optional parent context
        
    Returns:
        OpenTelemetry span
    """
    tracer = trace.get_tracer(__name__)
    return tracer.start_as_current_span(name)