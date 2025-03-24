#!/usr/bin/env python3

import os
import boto3
import argparse
import logging
import time
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set Global Variables
DEFAULT_MODEL_PATH = "s3://your-s3-bucket-name/sagemaker/models/model.joblib"
DEFAULT_IMAGE_URI = "your-ecr-image-uri"

# Function to create a SageMaker client
def get_sagemaker_client(region):
    return boto3.client('sagemaker', region_name=region)

# Function to check if a resource exists
def resource_exists(sagemaker, resource_type, resource_name):
    try:
        if resource_type == "endpoint":
            sagemaker.describe_endpoint(EndpointName=resource_name)
        elif resource_type == "endpoint_config":
            sagemaker.describe_endpoint_config(EndpointConfigName=resource_name)
        elif resource_type == "model":
            sagemaker.describe_model(ModelName=resource_name)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
        return True
    except sagemaker.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ValidationException' or e.response['Error']['Code'] == 'NotFoundException':
            return False
        else:
            logger.error(f"Error checking if resource exists: {e}")
            raise

# Function to create a SageMaker model
def create_sagemaker_model(sagemaker, model_name, image_uri, execution_role_arn, model_data_url):
    try:
        sagemaker.create_model(
            ModelName=model_name,
            ExecutionRoleArn=execution_role_arn,
            PrimaryContainer={
                'Image': image_uri,
                'ModelDataUrl': model_data_url
            }
        )
        logger.info(f"SageMaker model created successfully: {model_name}")
    except Exception as e:
        logger.error(f"Error creating SageMaker model: {e}")
        raise

# Function to create a SageMaker endpoint configuration
def create_endpoint_config(sagemaker, endpoint_config_name, model_name, initial_instance_count, instance_type, initial_variant_weight):
    try:
        production_variants = [
            {
                'VariantName': 'variant1',
                'ModelName': model_name,
                'InitialInstanceCount': int(initial_instance_count),
                'InstanceType': instance_type,
                'InitialVariantWeight': float(initial_variant_weight)
            }
        ]
        sagemaker.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=production_variants
        )
        logger.info(f"SageMaker endpoint configuration created successfully: {endpoint_config_name}")
    except Exception as e:
        logger.error(f"Error creating SageMaker endpoint configuration: {e}")
        raise

# Function to create a SageMaker endpoint or update it
def create_or_update_endpoint(sagemaker, endpoint_name, endpoint_config_name):
    try:
        if resource_exists(sagemaker, "endpoint", endpoint_name):
            sagemaker.update_endpoint(EndpointName=endpoint_name, EndpointConfigName=endpoint_config_name)
            logger.info(f"SageMaker endpoint update started: {endpoint_name}")
        else:
            sagemaker.create_endpoint(EndpointName=endpoint_name, EndpointConfigName=endpoint_config_name)
            logger.info(f"SageMaker endpoint creation started: {endpoint_name}")
    except Exception as e:
        logger.error(f"Error creating/updating SageMaker endpoint: {e}")
        raise

# Function to wait for the endpoint to be in service
def wait_for_endpoint_update(sagemaker, endpoint_name, timeout=600):
    start_time = time.time()
    while True:
        try:
            response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
            status = response['EndpointStatus']
            if status == 'InService':
                logger.info(f"Endpoint {endpoint_name} is now InService.")
                return
            elif status in ('Creating', 'Updating'):
                logger.info(f"Endpoint {endpoint_name} is {status}. Waiting...")
            elif status in ('Failed', 'Deleting'):
                raise ValueError(f"Endpoint {endpoint_name} is in {status} state.")
            else:
                logger.warning(f"Unexpected endpoint status: {status}. Waiting...")
        except Exception as e:
            logger.error(f"Error describing endpoint: {e}")
            raise

        time.sleep(60)  # Check every 60 seconds
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Timeout waiting for endpoint {endpoint_name} to become InService.")

# Function for Canary Deployment
def canary_deployment(sagemaker, endpoint_config_name, production_variants):
    try:
        sagemaker.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=production_variants
        )
        logger.info(f"SageMaker endpoint configuration created successfully: {endpoint_config_name}")
    except Exception as e:
        logger.error(f"Error creating SageMaker endpoint configuration: {e}")
        raise

# Function for Blue/Green Deployment
def blue_green_deployment(sagemaker, endpoint_name, endpoint_config_name):
    try:
        if resource_exists(sagemaker, "endpoint", endpoint_name):
            sagemaker.update_endpoint(EndpointName=endpoint_name, EndpointConfigName=endpoint_config_name)
            logger.info(f"SageMaker endpoint update started: {endpoint_name}")
        else:
            sagemaker.create_endpoint(EndpointName=endpoint_name, EndpointConfigName=endpoint_config_name)
            logger.info(f"SageMaker endpoint creation started: {endpoint_name}")
    except Exception as e:
        logger.error(f"Error creating/updating SageMaker endpoint: {e}")
        raise

def main(args):
    try:
        # 1. Setting Variables
        region = args.region
        s3_bucket = args.s3_bucket
        sagemaker_role_name = args.sagemaker_role_name
        model_name = args.model_name
        image_uri = args.image_uri
        endpoint_name = f"{model_name}-endpoint"
        instance_type = args.instance_type
        initial_instance_count = args.initial_instance_count
        initial_variant_weight = args.initial_variant_weight

        # 2. Initialize SageMaker Client
        sagemaker = get_sagemaker_client(region)
        execution_role_arn = f"arn:aws:iam::{args.aws_account_id}:role/{sagemaker_role_name}"
        model_data_url = f"s3://{s3_bucket}/sagemaker/models/model.joblib"

        # 3. Deployment
        if args.deployment_strategy == "create": # New Model
            # a. Create model
            if resource_exists(sagemaker, "model", model_name):
                logger.warning(f"Model with name '{model_name}' exists. Skipping creation.")
            else:
                create_sagemaker_model(sagemaker, model_name, image_uri, execution_role_arn, model_data_url)

            # b. Create endpoint config
            endpoint_config_name = f"{endpoint_name}-config" # The name
            if resource_exists(sagemaker, "endpoint_config", endpoint_config_name):
                logger.warning(f"Endpoint config with name '{endpoint_config_name}' exists. Skipping creation.")
            else:
                create_endpoint_config(sagemaker, endpoint_config_name, model_name, initial_instance_count, instance_type, initial_variant_weight)

            # c. Create a SageMaker endpoint
            create_or_update_endpoint(sagemaker, endpoint_name, endpoint_config_name)
            wait_for_endpoint_update(sagemaker, endpoint_name)

        elif args.deployment_strategy == "canary":
            # Configure production variants for canary deployment
            endpoint_config_name = f"{endpoint_name}-canary-config"
            production_variants = [
                {
                    'VariantName': 'prod',
                    'ModelName': model_name,
                    'InitialInstanceCount': int(initial_instance_count),
                    'InstanceType': instance_type,
                    'InitialVariantWeight': 0.9  # 90% traffic
                },
                {
                    'VariantName': 'canary',
                    'ModelName': model_name,
                    'InitialInstanceCount': 1,
                    'InstanceType': instance_type,
                    'InitialVariantWeight': 0.1  # 10% traffic
                }
            ]

            canary_deployment(sagemaker, endpoint_config_name, production_variants)
            create_or_update_endpoint(sagemaker, endpoint_name, endpoint_config_name)
            wait_for_endpoint_update(sagemaker, endpoint_name) #Run Code

        elif args.deployment_strategy == "blue_green":
            # Configure production variants for blue/green deployment
            endpoint_config_name = f"{endpoint_name}-blue-green-config"
            initial_instance_count = int(initial_instance_count)
            initial_variant_weight = float(initial_variant_weight)
            production_variants = [
                {
                    'VariantName': 'variant1',
                    'ModelName': model_name,
                    'InitialInstanceCount': initial_instance_count,
                    'InstanceType': instance_type,
                    'InitialVariantWeight': initial_variant_weight
                }
            ]

            create_endpoint_config(sagemaker, endpoint_config_name, model_name, initial_instance_count, instance_type, initial_variant_weight)
            blue_green_deployment(sagemaker, endpoint_name, endpoint_config_name)
            wait_for_endpoint_update(sagemaker, endpoint_name)

        else:
            raise ValueError(f"Unsupported deployment strategy: {args.deployment_strategy}")

        logger.info("Deployment completed successfully.") #Done
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy a SageMaker endpoint with various deployment strategies.")
    #Required
    parser.add_argument("--aws-account-id", required=True, help="AWS account ID") #Account access
    parser.add_argument("--region", required=True, help="AWS region") #Region Access.
    parser.add_argument("--s3-bucket", required=True, help="S3 bucket name") # Data Files
    parser.add_argument("--sagemaker-role-name", required=True, help="SageMaker role name") #Access

    #Config Settings
    parser.add_argument("--model-name", default="your-model", help="Model name") # Test Models.
    parser.add_argument("--image-uri", default=DEFAULT_IMAGE_URI, help="ECR image URI") #The access to code.
    #Settings what test or model and that tests.
    parser.add_argument("--initial-instance-count", default=1, help="Instance count", type=int) # Model or Instances
    parser.add_argument("--instance-type", default="ml.m5.large", help="Instance type") # Small to Large
    parser.add_argument("--initial-variant-weight", default=1.0, help="Initial variant weight", type=float) # Model weight

    #Type of models
    parser.add_argument(
        "--deployment-strategy",
        choices=["create", "canary", "blue_green"],
        default="create",
        help="Deployment strategy (create, canary, blue_green)",
    )
    args = parser.parse_args()

    main(args) #All to the training.