# Mlops Framework

An MLOps framework that simplifies the deployment and management of machine learning models on AWS SageMaker, providing a seamless integration between model development and production serving.

## 1. Deploying Models

```python
from sagemaker_deployer import ModelDeployer

deployer = ModelDeployer()
deployer.deploy_model("model-v1", "s3://bucket/model.tar.gz")
```

## 2. Performance Monitoring

```bash
kubectl top pods -n mlops
```

## 3. Model Rollback

```bash
kubectl rollout undo deployment/mlops-api -n mlops
```

## Configuration

- AWS Region
- SageMaker Instance Types
- Scaling Parameters
- Authentication Settings
- Monitoring Thresholds

## Troubleshooting

- Common scenarios and solutions are documented in ops/troubleshooting.md:
- API performance issues
- Model serving errors
- Database query optimization
- Network diagnostics

## Best Practices

- Version all model artifacts

- Use staging environments

- Implement gradual rollouts

- Monitoring

- Set up alerts for key metrics

- Monitor resource utilization

- Track model performance

- Security

- Rotate credentials regularly

- Implement rate limiting

- Use proper IAM roles

## Key Features

- **API Serving:**
  - `/api/v1/predict`: For single-instance predictions.
  - `/api/v1/batch-predict`: For batch predictions.
- **Comprehensive Monitoring and Observability:**
  - OpenTelemetry integration for traces, metrics, and logs.
  - Prometheus metrics scraping.
  - Jaeger and Zipkin support for distributed tracing.
  - Elasticsearch for log aggregation.
  - Kubernetes and host metrics collection.
  - Application metrics instrumentation.
- **Security:**
  - Rate limiting (IP-based and API key-based) with a token bucket algorithm.
  - Web Application Firewall (WAF) integration (GCP Cloud Armor and AWS WAF).
  - Protection against common web application attacks (SQLi, XSS, LFI, RFI).
  - IP whitelisting.
  - API Key Hashing.
- **Resilience and Fault Tolerance:**
  - Circuit breaker pattern to prevent cascading failures.
  - Retry mechanism with exponential backoff.
  - Redis availability checks.
- **Health Checks:**
  - `/api/v1/health`: Detailed health check.
  - `/api/v1/health/liveness`: Kubernetes liveness check.
  - `/api/v1/health/readiness`: Kubernetes readiness check.
- **Performance Testing:**
  - Locust load testing support.
- **Infrastructure as Code:**
  - Terraform for WAF configuration.
- **Kubernetes Ready:**
  - Designed to be deployed in a Kubernetes environment.

## Architecture

!Architecture Diagram

_(Replace this with a diagram of your architecture)_

This component is designed to be deployed as part of a larger MLOps pipeline. It sits at the end of the pipeline, serving pre-trained models.

## Getting Started

### Prerequisites

- Python 3.9+
- Docker (for local development)
- Kubernetes cluster (for production deployment)
- Redis instance
- Elasticsearch instance
- Jaeger or Zipkin instance (for tracing)
- GCP and/or AWS account (if using WAF)

### Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd your-repo
    ```

2.  Create a virtual environment (recommended):

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Environment Variables:**

    The following environment variables are required:

    - `ELASTICSEARCH_USERNAME`: Username for Elasticsearch.
    - `ELASTICSEARCH_PASSWORD`: Password for Elasticsearch.
    - `SAMPLING_PERCENTAGE`: Percentage of traces to sample (e.g., `10` for 10%).
    - `APP_VERSION`: The version of the application.
    - `ENV`: The environment (e.g., `development`, `production`).
    - `REDIS_HOST`: The host of the redis instance.
    - `REDIS_PORT`: The port of the redis instance.
    - `REDIS_DB`: The database of the redis instance.
    - `REDIS_PASSWORD`: The password of the redis instance.
    - `DATABASE_HOST`: The host of the database.
    - `DATABASE_PORT`: The port of the database.
    - `ML_SERVICE_HOST`: The host of the ML service.
    - `ML_SERVICE_PORT`: The port of the ML service.

2.  **Configuration File (`config.py`):**

    Create a `config.py` file in the `api/utils` directory. Here's a sample:

    ```python
    # api/utils/config.py
    class Config:
        def __init__(self):
            self.config = {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                },
                "ml_service": {
                    "host": "localhost",
                    "port": 8501,
                },
                "cache": {
                    "host": "localhost",
                    "port": 6379,
                },
                "security": {
                    "rate_limits": {
                        "authenticated": 100,
                        "auth_window": 60,
                        "anonymous": 20,
                        "anon_window": 60,
                        "sensitive_endpoints": 10,
                        "sensitive_window": 60
                    }
                }
            }


        def get(self, section, key=None):
            if key:
                return self.config.get(section, {}).get(key)
            return self.config.get(section)


    ```

### Running the API

```bash
uvicorn api.main:app --reload

```

### Running Tests

```bash
pytest api/tests
```

### Load Tests

```bash
locust -f api/tests/performance/locustfile.py --host=http://localhost:8000

```

### Deployment

This component is designed to be deployed in a Kubernetes environment. You'll need to:

Build a Docker image of the API.
Push the image to a container registry.
Create Kubernetes manifests (Deployment, Service, etc.).
Deploy the manifests to your Kubernetes cluster.
Configure the OpenTelemetry collector to scrape metrics and collect logs.
Configure the WAF (GCP Cloud Armor or AWS WAF) using the provided Terraform files.
WAF Configuration
The infrastructure/web_application_firewall directory contains Terraform files for configuring the WAF.

### GCP Cloud Armor:

Set the project_id variable.
Set the ip_whitelist variable (if needed).
Set the rate_limit_threshold variable.
Set the rate_limit_paths variable.
Set the rate_limit_enforce_key variable.
Run terraform init, terraform plan, and terraform apply.
AWS WAF:

Set the aws_region variable.
Set the ip_whitelist variable (if needed).
Set the rate_limit_threshold variable.
Set the rate_limit_paths variable.
Set the rate_limit_enforce_key variable.
Run terraform init, terraform plan, and terraform apply.
Monitoring
The OpenTelemetry collector is configured to collect traces, metrics, and logs. You can use:

### Monitoring / Observability

Prometheus: For metrics monitoring and alerting.

### License

This project is licensed under the MIT License - see the LICENSE file for details.

<<<<<<< HEAD

```bash
python pipeline.py --input-data-uri gs://your-bucket/processed-data/ --output-dir ./models --deploy-env staging
```

## API Deployment

Deploy the model API to Cloud Run:

```bash
./scripts/deploy.sh --environment production
```

## Monitoring

Access monitoring dashboards:

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Security

The platform implements several security features:

- JWT authentication for API access
- Least-privilege RBAC via service accounts
- Secret management for sensitive configuration
- Input validation to prevent injection attacks

## Configuration

Configuration is managed through:

1. JSON config files in `config/`
2. Environment variables for sensitive or deployment-specific values
3. Command-line arguments for one-time settings

## Testing

Run tests with pytest:

```bash
pytest tests/
```

Run load tests with Locust:

```bash
locust -f locustfile.py --host https://your-api-endpoint
```

## CI/CD Pipeline

The CI/CD pipeline automates:

1. Code quality checks and testing
2. Docker image building
3. Infrastructure deployment
4. Model validation and deployment
5. API deployment with traffic management

6. Fork the repository
7. Create your feature branch (`git checkout -b feature/amazing-feature`)
8. Commit your changes (`git commit -m 'Add some amazing feature'`)
9. Push to the branch (`git push origin feature/amazing-feature`)
10. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [MLflow](https://mlflow.org) for experiment tracking
- [FastAPI](https://fastapi.tiangolo.com) for API development
- [Prometheus](https://prometheus.io) for metrics collection
- [OpenTelemetry](https://opentelemetry.io) for distributed tracing
- [Google Cloud](https://cloud.google.com) and [AWS](https://aws.amazon.com) for cloud infrastructure
