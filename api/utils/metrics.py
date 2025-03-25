"""
Metrics collection for monitoring application performancelection for monitoring application performance
Supports StatsD, Prometheus, and CloudWatchD, Prometheus, and CloudWatch
"""
import os
import time
import loggingimport logging
import socket
import threadingimport threading
from typing import Dict, List, Optional, Union, Anyl, Union, Any

logger = logging.getLogger(__name__)logger = logging.getLogger(__name__)

class Metrics:
    """
    Metrics collection with multiple backend supportMetrics collection with multiple backend support
    - StatsD
    - Prometheus
    - CloudWatch
    """
    
    def __init__(self):
        """Initialize metrics collection"""lection"""
        self.metric_backends = []self.metric_backends = []
        
        # Load backends based on environmentironment
        self._setup_backends()
        
    def _setup_backends(self):
        """Set up metrics backends"""
        # Check environment variablesbles
        use_statsd = os.environ.get("ENABLE_STATSD", "false").lower() == "true"        use_statsd = os.environ.get("ENABLE_STATSD", "false").lower() == "true"
        use_prometheus = os.environ.get("ENABLE_PROMETHEUS", "true").lower() == "true"        use_prometheus = os.environ.get("ENABLE_PROMETHEUS", "true").lower() == "true"
        use_cloudwatch = os.environ.get("ENABLE_CLOUDWATCH", "false").lower() == "true"get("ENABLE_CLOUDWATCH", "false").lower() == "true"
        
        # Set up StatsD if enabled    # Set up StatsD if enabled
        if use_statsd:
            try:
                from statsd import StatsClientmport StatsClient
                statsd_host = os.environ.get("STATSD_HOST", "localhost")        statsd_host = os.environ.get("STATSD_HOST", "localhost")
                statsd_port = int(os.environ.get("STATSD_PORT", "8125"))= int(os.environ.get("STATSD_PORT", "8125"))
                statsd_prefix = os.environ.get("STATSD_PREFIX", "mlops")tsd_prefix = os.environ.get("STATSD_PREFIX", "mlops")
                
                statsd = StatsClient(host=statsd_host, port=statsd_port, prefix=statsd_prefix)host, port=statsd_port, prefix=statsd_prefix)
                self.metric_backends.append(StatsDBackend(statsd))end(statsd))
                logger.info(f"Initialized StatsD metrics backend: {statsd_host}:{statsd_port}")       logger.info(f"Initialized StatsD metrics backend: {statsd_host}:{statsd_port}")
            except ImportError:    except ImportError:
                logger.warning("StatsD client not installed, skipping StatsD metrics")d, skipping StatsD metrics")
            except Exception as e:    except Exception as e:
                logger.error(f"Failed to initialize StatsD metrics: {e}")
                
        # Set up Prometheus if enabled
        if use_prometheus:
            try:    try:
                import prometheus_client as prom
                
                # Initialize Prometheus registrygistry
                registry = prom.CollectorRegistry(auto_describe=True)escribe=True)
                        
                # Export default metrics
                prom.ProcessCollector(registry=registry)try)
                prom.PlatformCollector(registry=registry)istry=registry)
                prom.GCCollector(registry=registry)
                        
                self.metric_backends.append(PrometheusBackend(registry))
                logger.info("Initialized Prometheus metrics backend")d Prometheus metrics backend")
            except ImportError:
                logger.warning("Prometheus client not installed, skipping Prometheus metrics")led, skipping Prometheus metrics")
            except Exception as e:    except Exception as e:
                logger.error(f"Failed to initialize Prometheus metrics: {e}")
                
        # Set up CloudWatch if enabledoudWatch if enabled
        if use_cloudwatch:if use_cloudwatch:
            try:
                import boto3
                        
                region = os.environ.get("AWS_REGION", "us-east-1")os.environ.get("AWS_REGION", "us-east-1")
                namespace = os.environ.get("CLOUDWATCH_NAMESPACE", "MLOps/API")namespace = os.environ.get("CLOUDWATCH_NAMESPACE", "MLOps/API")
                
                cloudwatch = boto3.client("cloudwatch", region_name=region)    cloudwatch = boto3.client("cloudwatch", region_name=region)
                self.metric_backends.append(CloudWatchBackend(cloudwatch, namespace))_backends.append(CloudWatchBackend(cloudwatch, namespace))
                logger.info(f"Initialized CloudWatch metrics backend: {namespace}")loudWatch metrics backend: {namespace}")
            except ImportError:
                logger.warning("Boto3 not installed, skipping CloudWatch metrics")    logger.warning("Boto3 not installed, skipping CloudWatch metrics")
            except Exception as e:ception as e:
                logger.error(f"Failed to initialize CloudWatch metrics: {e}")                logger.error(f"Failed to initialize CloudWatch metrics: {e}")
                                
        # If no backends initialized, use no-op backendse no-op backend
        if not self.metric_backends:
            self.metric_backends.append(NoopBackend())        self.metric_backends.append(NoopBackend())
            logger.warning("No metrics backends configured, using no-op backend")g no-op backend")
            
    def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None): value: int = 1, tags: Optional[Dict[str, str]] = None):
        """
        Increment counterIncrement counter
        
        Args:
            name: Metric name name
            value: Value to increment byincrement by
            tags: Metric tagsgs
        """"""
        for backend in self.metric_backends:etric_backends:
            try:
                backend.incr(name, value, tags)        backend.incr(name, value, tags)
            except Exception as e:
                logger.error(f"Failed to increment metric {name}: {e}") increment metric {name}: {e}")
                
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):at, tags: Optional[Dict[str, str]] = None):
        """"""
        Set gauge valuevalue
        
        Args:
            name: Metric name
            value: Gauge valuevalue: Gauge value
            tags: Metric tags
        """
        for backend in self.metric_backends:ends:
            try:
                backend.gauge(name, value, tags)        backend.gauge(name, value, tags)
            except Exception as e: Exception as e:
                logger.error(f"Failed to set gauge {name}: {e}")gauge {name}: {e}")
                   
    def timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):tr, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Record timing
        
        Args:
            name: Metric name
            value: Timing value in millisecondseconds
            tags: Metric tags    tags: Metric tags
        """
        for backend in self.metric_backends:
            try:ry:
                backend.timing(name, value, tags)e, value, tags)
            except Exception as e:except Exception as e:
                logger.error(f"Failed to record timing {name}: {e}")
                
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):float, tags: Optional[Dict[str, str]] = None):
        """
        Record histogram valueRecord histogram value
        
        Args:
            name: Metric nameame: Metric name
            value: Value to recordord
            tags: Metric tagstags: Metric tags
        """
        for backend in self.metric_backends:ckends:
            try:
                backend.histogram(name, value, tags)
            except Exception as e:
                logger.error(f"Failed to record histogram {name}: {e}")
                

class MetricsBackend:
    """Base class for metrics backends"""nds"""
    
    def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):[str, str]] = None):
        """Increment counter"""
        pass
        
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set gauge value"""
        pass
        
    def timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):[str, str]] = None):
        """Record timing"""
        pass
        
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record histogram value"""
        pass


class NoopBackend(MetricsBackend):
    """No-op metrics backend"""
    pass


class StatsDBackend(MetricsBackend):
    """StatsD metrics backend"""
    
    def __init__(self, client):(self, client):
        """Initialize StatsD backend"""ckend"""
        self.client = client.client = client
        
    def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):    def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment counter"""        """Increment counter"""
        self.client.incr(self._format_name(name, tags), value)rmat_name(name, tags), value)
        
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set gauge value"""
        self.client.gauge(self._format_name(name, tags), value), tags), value)
        
    def timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record timing"""
        self.client.timing(self._format_name(name, tags), value)name(name, tags), value)
        
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record histogram value (maps to timing in StatsD)"""
        self.client.timing(self._format_name(name, tags), value)(name, tags), value)
        
    def _format_name(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:_format_name(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Format metric name with tags"""
        if not tags:
            return namereturn name
                        
        # Format tags as StatsD tags        # Format tags as StatsD tags
        tag_str = ",".join(f"{k}={v}" for k, v in tags.items())}" for k, v in tags.items())
        return f"{name}:{tag_str}" return f"{name}:{tag_str}"


class PrometheusBackend(MetricsBackend):heusBackend(MetricsBackend):
    """Prometheus metrics backend"""
    
    def __init__(self, registry):istry):
        """Initialize Prometheus backend"""    """Initialize Prometheus backend"""
        self.registry = registryy
        self.metrics = {}
        self.metrics_lock = threading.Lock()self.metrics_lock = threading.Lock()
        
    def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):tags: Optional[Dict[str, str]] = None):
        """Increment counter"""
        counter = self._get_counter(name, tags)
        if tags:
            counter.labels(**tags).inc(value)).inc(value)
        else:
            counter.inc(value)
            
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set gauge value"""
        gauge = self._get_gauge(name, tags)
        if tags:
            gauge.labels(**tags).set(value)t(value)
        else:
            gauge.set(value)
            
    def timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record timing"""cord timing"""
        # Use histogram for timing in Prometheustheus
        histogram = self._get_histogram(name, tags)ogram = self._get_histogram(name, tags)
        if tags:





























































































































































    return _metrics_instance        _metrics_instance = Metrics()    if _metrics_instance is None:    global _metrics_instance    """        Metrics instance    Returns:        Get metrics instance    """def get_metrics() -> Metrics:_metrics_instance = None# Singleton instance            self._flush()            time.sleep(self.flush_interval)        while True:        """Background thread for flushing metrics"""    def _flush_thread(self):                        logger.error(f"Failed to flush metrics to CloudWatch: {e}")        except Exception as e:            )                MetricData=metrics_to_flush                Namespace=self.namespace,            self.client.put_metric_data(        try:                        self.metrics_buffer = self.metrics_buffer[self.buffer_size:]            metrics_to_flush = self.metrics_buffer[:self.buffer_size]        with self.buffer_lock:                        return        if not self.metrics_buffer:        """Flush metrics to CloudWatch"""    def _flush(self):                                self._flush()            if len(self.metrics_buffer) >= self.buffer_size:            # Flush if buffer is full                        self.metrics_buffer.append(metric_data)        with self.buffer_lock:                }            "Dimensions": [{"Name": k, "Value": v} for k, v in (tags or {}).items()]            "Unit": unit,            "Value": value,            "MetricName": name,        metric_data = {        """Add metric to buffer"""    def _add_metric(self, name: str, value: float, unit: str, tags: Optional[Dict[str, str]] = None):                self._add_metric(name, value, "None", tags)        # CloudWatch doesn't have histograms, use multiple metrics instead        """Record histogram value"""    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):                self._add_metric(name, value, "Milliseconds", tags)        """Record timing"""    def timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):                self._add_metric(name, value, "None", tags)        """Set gauge value"""    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):                self._add_metric(name, value, "Count", tags)        """Increment counter"""    def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):                self.flush_thread.start()        self.flush_thread = threading.Thread(target=self._flush_thread, daemon=True)        self.flush_interval = 60  # seconds        # Start background thread for flushing metrics                self.buffer_size = 20  # Max metrics per CloudWatch API call        self.buffer_lock = threading.Lock()        self.metrics_buffer = []        self.namespace = namespace        self.client = client        """Initialize CloudWatch backend"""    def __init__(self, client, namespace: str):        """CloudWatch metrics backend"""class CloudWatchBackend(MetricsBackend):            return prom.Histogram.DEFAULT_BUCKETS            # Default Prometheus buckets        else:            return [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60]            # Latency buckets in seconds: 1ms to 60s        if "latency" in name or "duration" in name:                import prometheus_client as prom        """Choose appropriate histogram buckets based on metric name"""    def _choose_buckets(self, name: str):                        return self.metrics[metric_key]                )                    buckets=self._choose_buckets(name)                    registry=self.registry,                    list(tags.keys()) if tags else [],                    name.replace(".", " "),                    name.replace(".", "_"),                self.metrics[metric_key] = prom.Histogram(            if metric_key not in self.metrics:            metric_key = f"histogram:{name}"        with self.metrics_lock:                import prometheus_client as prom        """Get or create histogram"""    def _get_histogram(self, name: str, tags: Optional[Dict[str, str]] = None):                        return self.metrics[metric_key]                )                    registry=self.registry                    list(tags.keys()) if tags else [],                    name.replace(".", " "),                    name.replace(".", "_"),                self.metrics[metric_key] = prom.Gauge(            if metric_key not in self.metrics:            metric_key = f"gauge:{name}"        with self.metrics_lock:                import prometheus_client as prom        """Get or create gauge"""    def _get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None):                        return self.metrics[metric_key]                )                    registry=self.registry                    list(tags.keys()) if tags else [],                    name.replace(".", " "),                    name.replace(".", "_"),                self.metrics[metric_key] = prom.Counter(            if metric_key not in self.metrics:            metric_key = f"counter:{name}"        with self.metrics_lock:                import prometheus_client as prom        """Get or create counter"""    def _get_counter(self, name: str, tags: Optional[Dict[str, str]] = None):                        histogram.observe(value)        else:            histogram.labels(**tags).observe(value)        if tags:        histogram = self._get_histogram(name, tags)        """Record histogram value"""    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):                        histogram.observe(value / 1000)        else:            histogram.labels(**tags).observe(value / 1000)  # Convert ms to seconds            histogram.labels(**tags).observe(value / 1000)  # Convert ms to seconds

















    return _metrics_instance        _metrics_instance = Metrics()    if _metrics_instance is None:


    global _metrics_instance    """        Metrics instance    Returns:        Get metrics instance    """



def get_metrics() -> Metrics:_metrics_instance = None# Singleton instance            self._flush()            time.sleep(self.flush_interval)



        while True:        """Background thread for flushing metrics"""    def _flush_thread(self):


                        logger.error(f"Failed to flush metrics to CloudWatch: {e}")        except Exception as e:            )




                MetricData=metrics_to_flush                Namespace=self.namespace,            self.client.put_metric_data(        try:



                        self.metrics_buffer = self.metrics_buffer[self.buffer_size:]            metrics_to_flush = self.metrics_buffer[:self.buffer_size]



        with self.buffer_lock:                        return        if not self.metrics_buffer:        """Flush metrics to CloudWatch"""


    def _flush(self):                                self._flush()            if len(self.metrics_buffer) >= self.buffer_size:


            # Flush if buffer is full                        self.metrics_buffer.append(metric_data)        with self.buffer_lock:


                }            "Dimensions": [{"Name": k, "Value": v} for k, v in (tags or {}).items()]

            "Unit": unit,            "Value": value,            "MetricName": name,
        metric_data = {        """Add metric to buffer"""    def _add_metric(self, name: str, value: float, unit: str, tags: Optional[Dict[str, str]] = None):

                self._add_metric(name, value, "None", tags)

        # CloudWatch doesn't have histograms, use multiple metrics instead

        """Record histogram value"""    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):


                self._add_metric(name, value, "Milliseconds", tags)
        """Record timing"""    def timing(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):


                self._add_metric(name, value, "None", tags)        """Set gauge value"""
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):


                self._add_metric(name, value, "Count", tags)        """Increment counter"""



    def incr(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
                self.flush_thread.start()        self.flush_thread = threading.Thread(target=self._flush_thread, daemon=True)



        self.flush_interval = 60  # seconds        # Start background thread for flushing metrics                self.buffer_size = 20  # Max metrics per CloudWatch API call




        self.buffer_lock = threading.Lock()


        self.metrics_buffer = []        self.namespace = namespace        self.client = client        """Initialize CloudWatch backend"""

    def __init__(self, client, namespace: str):        """CloudWatch metrics backend"""class CloudWatchBackend(MetricsBackend):            return prom.Histogram.DEFAULT_BUCKETS            # Default Prometheus buckets
        else:            return [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60]        else:
            histogram.observe(value / 1000)
            
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):

            # Latency buckets in seconds: 1ms to 60s



        if "latency" in name or "duration" in name:        
        import prometheus_client as prom


        """Choose appropriate histogram buckets based on metric name"""    def _choose_buckets(self, name: str):

                        return self.metrics[metric_key]                )                    buckets=self._choose_buckets(name)



                    registry=self.registry,                    list(tags.keys()) if tags else [],                    name.replace(".", " "),                    name.replace(".", "_"),

                self.metrics[metric_key] = prom.Histogram(            if metric_key not in self.metrics:



            metric_key = f"histogram:{name}"        with self.metrics_lock:                import prometheus_client as prom


        """Get or create histogram"""    def _get_histogram(self, name: str, tags: Optional[Dict[str, str]] = None):


                        return self.metrics[metric_key]                )                    registry=self.registry



                    list(tags.keys()) if tags else [],                    name.replace(".", " "),                    name.replace(".", "_"),
                self.metrics[metric_key] = prom.Gauge(            if metric_key not in self.metrics:            metric_key = f"gauge:{name}"




        with self.metrics_lock:                import prometheus_client as prom        """Get or create gauge"""


    def _get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None):

                        return self.metrics[metric_key]                )                    registry=self.registry                    list(tags.keys()) if tags else [],




                    name.replace(".", " "),                    name.replace(".", "_"),                self.metrics[metric_key] = prom.Counter(

            if metric_key not in self.metrics:            metric_key = f"counter:{name}"



        with self.metrics_lock:                import prometheus_client as prom        """Get or create counter"""    def _get_counter(self, name: str, tags: Optional[Dict[str, str]] = None):
            
            histogram.observe(value)        else:
            histogram.labels(**tags).observe(value)
        if tags:
        histogram = self._get_histogram(name, tags)        """Record histogram value"""