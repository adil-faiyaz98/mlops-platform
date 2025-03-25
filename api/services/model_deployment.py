"""
Model deployment script using Vertex AI.
"""

import logging
import os
import mlflow
from google.cloud import aiplatform
from google.cloud.aiplatform.models import Model
from google.cloud.aiplatform.models import Endpoint
from google.cloud.aiplatform import helpers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelDeployer:
    """
    Deploys a trained model to Vertex AI.
    """

    def __init__(self, project_id: str, region: str, model_name: str):
        """
        Initializes the ModelDeployer.
        """
        self.project_id = project_id
        self.region = region
        self.model_name = model_name
        aiplatform.init(project=project_id, location=region)

    def deploy(self, model_path: str, run_id: str, metrics: dict, environment: str) -> str:
        """
        Deploys the model to Vertex AI.
        """
        logger.info(f"Deploying model from {model_path} to {environment} environment.")

        try:
            # Upload the model to Vertex AI Model Registry
            model_upload = aiplatform.Model.upload(
                display_name=self.model_name,
                artifact_uri=model_path,
                serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-0:latest",
                #serving_container_predict_route="/predict",
                #serving_container_health_route="/health",
                #serving_container_ports=[8080],
            )
            logger.info(f"Model uploaded to Vertex AI Model Registry. Model ID: {model_upload.resource_name}")

            # Create an endpoint
            endpoint = aiplatform.Endpoint.create(
                display_name=f"{self.model_name}-endpoint-{environment}",
            )
            logger.info(f"Endpoint created. Endpoint ID: {endpoint.resource_name}")

            # Deploy the model to the endpoint
            model_deploy = endpoint.deploy(
                model=model_upload,
                deployed_model_display_name=f"{self.model_name}-deployed-{environment}",
                machine_type="n1-standard-2",
                traffic_percentage=100,
                min_replica_count=1,
                max_replica_count=1,
            )
            logger.info(f"Model deployed to endpoint. Deployed model ID: {model_deploy.id}")

            # Return the endpoint URL
            endpoint_url = f"https://{self.region}-aiplatform.googleapis.com/v1/{endpoint.resource_name}"
            return endpoint_url

        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            raise e