"""
End-to-end ML Pipeline implementation that orchestrates:
- Data ingestion
- Data validation
- Feature engineering
- Model training
- Model evaluation
- Model deployment

Consolidated version for single file deployment.
"""

import os
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

import pandas as pd
import mlflow
from mlflow.tracking import MlflowClient
from google.cloud import storage
from sklearn.model_selection import train_test_split
from sklearn.exceptions import NotFittedError
import pandera as pa
from pandera import Column, Check
import optuna
import numpy as np
import subprocess
import time

# Ensure components are importable
try:
    from src.utils.config import config #Config will be passed.
    from src.data_processing.cleaning import remove_duplicates, remove_outliers, handle_missing_values, correct_skewness
    from src.data_processing.feature_engineering import create_interaction_term, create_polynomial_features
    from src.data_processing.ingestion import load_data_from_gcs, ingest_from_api
    from src.data_processing.processing import process_data
    from src.data_processing.validation import validate_data, InputDataSchema
    #from src.training.model import MLModel # Removed due to deprecation
    #from src.deployment.deployer import ModelDeployer #Deploy model.
except ImportError as e:
    raise ImportError(f"Failed to import components. Ensure 'src' is in your PYTHONPATH: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MLPipeline:
    """End-to-end ML pipeline for training and deploying models"""

    def __init__(
        self,
        project_id: str,
        region: str,
        input_data_uri: str,
        output_dir: str,
        model_name: str,
        experiment_name: str = "ml-model-training",
        deploy_env: str = "staging"
    ):
        """Initializes the MLPipeline."""
        self.project_id = project_id
        self.region = region
        self.input_data_uri = input_data_uri
        self.output_dir = output_dir
        self.model_name = model_name
        self.experiment_name = experiment_name
        self.deploy_env = deploy_env
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{model_name}_{self.timestamp}"
        self.deploy_threshold = 0.7 #Can be parametrized

        # Initialize MLflow
        try:
            mlflow.set_tracking_uri("file:///app/mlruns") #Where the metrics will save (important)
            mlflow.set_experiment(experiment_name) #Also important
            self.client = MlflowClient()
            logger.info("MLflow initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MLflow: {e}")
            raise  #Re-raise
        
        # Initialize deployer (GCP-specific for now)
        try:
            #self.deployer = ModelDeployer( #Check if working
            #    project_id=project_id,
            #    region=region,
            #    model_name=model_name
            #)
            #logger.info("ModelDeployer initialized successfully.")
            logger.info("Model deployer needs further adjustment.")
        except Exception as e:
            logger.error(f"Failed to initialize ModelDeployer: {e}")
            raise  #Re-raise

    def load_data(self) -> pd.DataFrame:
        """Load data from GCS or local filesystem"""
        logger.info(f"Loading data from {self.input_data_uri}")
        
        try:
            if self.input_data_uri.startswith("gs://"):
                # Extract bucket and blob path
                bucket_name = self.input_data_uri.split("gs://")[1].split("/")[0]
                blob_path = "/".join(self.input_data_uri.split("gs://")[1].split("/")[1:])
                
                # Download from GCS
                storage_client = storage.Client(project=self.project_id)
                bucket = storage_client.get_bucket(bucket_name)
                blob = bucket.blob(blob_path)
                
                temp_file = "/tmp/temp_dataset.csv"
                blob.download_to_filename(temp_file)
                df = pd.read_csv(temp_file)
                os.remove(temp_file)  # Clean up
            else:
                # Load from local path
                df = pd.read_csv(self.input_data_uri)
            
            logger.info(f"Loaded data with shape: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise #Re-raise

    def validate_data_step(self, input_path: str) -> bool: #Added validate path.
      """Validates data from Great expectation. """
      logger.info(f"Start data validation with expectation at: {input_path}")
      try:
        is_valid = validate_data(input_path) #Check if valiate is success
        return is_valid
      except Exception as e: #Catches Error
          logger.error(f"Error validating: {e}")
          raise

    def preprocess_data(self, input_path : str, output_train_path: str, output_test_path:str, sensitive_feature : str) -> str:
        """Preprocess data and generating features"""
        # The code will be called with preprocessing.
        logger.info("Preprocessing data and generating features")

        #Call processing py and perform all the data and feature engineering.
        try:
            command = [
                "python",
                "src/data_processing/processing.py",
                "--input_data",
                input_path,
                "--output_train_data",
                output_train_path,
                "--output_test_data",
                output_test_path,
                "--sensitive_feature",
                sensitive_feature,
            ]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) #Run code.
            stdout, stderr = process.communicate() #Get the command.

            if stderr: #If there is any error
                logger.error(f"Subprocess Error : {stderr.decode()}") # Decode to see.
                raise RuntimeError("Error during data processing")

            else: #Load results.
                logger.info(f"Subprocess output : {stdout.decode()}")

        except Exception as e:
            logger.error(f"Failed to run the processing.py. {e}")
            raise
        return "ALL good in proprocess"

    def train_model(self,trainPath,testPath):
        """Train the model and log metrics with MLflow, using hyperparameter tuning."""
        logger.info("Now training the model") # Training
        os.environ['TF_CONFIG'] = json.dumps({ #Json to pass parameters.
            'cluster': {
                'worker': ["localhost:2222"]
            },
               'task': {'type': 'worker', 'index': 0}
            })
        try:

          command = [
                "python",
                "src/model_training/train.py", #From original
                "--model_dir",
                "src/model_training/", # Where model is going to be saved
                "--train_dir", # Where training data file in
                trainPath,
                "--test_dir", # Where to load test from
                testPath #Set the path value in configuration
                ] # Command I passed.
          process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) #Command to run, save errors or outputs
          stdout, stderr = process.communicate() #Run the command,

          if stderr: #If any errors
                logger.error(f"Subprocess Error : {stderr.decode()}") #Print any
                raise RuntimeError("Check errors with the model.")

          else: #Load results and make sure that code doesn't crash
                logger.info(f"Subprocess outputs : {stdout.decode()}")


        except Exception as e:
            logger.error(f"Failed to Run code. {e}")
            raise # Error
        return "Succesful call all trainers"

    def deploy_model(
        self, 
        model_path: str,
        metrics: Dict[str, float],
        run_id: str
    ) -> str:
        """Deploy the model if metrics meet threshold"""
        # Check if model meets deployment criteria
        logger.info ("Model to deply needs further adjustment") #Remove and work on this.
        return "None since it needs to be worked on."

        if metrics.get("accuracy", 0) < self.deploy_threshold:
            logger.warning(
                f"Model accuracy {metrics.get('accuracy')} below threshold {self.deploy_threshold}. "
                "Skipping deployment."
            )
            return None
            
        logger.info(f"Deploying model {self.model_name} to {self.deploy_env}")
        
        # Deploy model - use Vertex AI for all deployments
        try:
            #endpoint_url = self.deployer.deploy( #The lines to connect, if available.
            #    model_path=model_path,
            #    run_id=run_id,
            #    metrics=metrics,
            #    environment=self.deploy_env
            #)
            #logger.info(f"Model deployed successfully to: {endpoint_url}")
            #return endpoint_url
            logger.info ("Please re-run, since we can call this for a error") #Remove
        except Exception as e:
            logger.error(f"Failed to deploy model: {e}")
            raise  # Re-raise

    def run(self) -> Dict[str, Any]:
        """Run the full ML pipeline"""
        logger.info(f"Starting ML pipeline for {self.model_name}")

        # Track pipeline start time
        start_time = datetime.now()

        #Local Path
        data_path = os.path.join(self.output_dir, "raw.csv")
        train_path = os.path.join(self.output_dir, "train.csv")
        test_path = os.path.join(self.output_dir, "test.csv")

        try:
            # Load data
            df = self.load_data()

            if os.path.exists(data_path):  #Check if this path exists.
              os.remove(data_path)  #Remove File
            df.to_csv(data_path, index=False)  #Save the file.
            logger.info(f"Saving this file to {data_path}")

            # Validate data
            if not self.validate_data_step(data_path):  # Using the function to ensure that the result is correct
                raise ValueError("Data validation failed based on schema.")

            # Preprocess data
            process_test = self.preprocess_data(data_path, train_path, test_path, "feature1") # Can set as arguments
            logger.info(f"{process_test} Check the model") # Run all the code, without model or any outputs.

            # Run new Model
            allTrained = self.train_model (train_path,test_path) # Calling this new model

            # The next set of tasks need to re-evaluated.
            #X_train, X_test, y_train, y_test, feature_columns = (None, None, None, None, None)

            #if os.path.exists(train_path): #If Train exists
            #with open(train_path, 'r') as file:
            #  trainDF = pd.read_csv(file) #Load csv
            #  logger.info(f"Here are the train file columsn {trainDF.columns}") #Show the training results

            #if os.path.exists(test_path): #If Test exists
            #with open(test_path, 'r') as file:
            #  testDF = pd.read_csv(file) #Load csv
            #  logger.info(f"Here are the testing file columsn {testDF.columns}") #Show the testing results

            # This steps aren't used because the code still needs it.
            #trainDF = trainDF #Load file
            #testDF = testDF #Load file

            #X_train = trainDF #Load file
            #X_test = testDF #Load file
            training_result = {"model": None}

            # This part is needs to be adjusted or deprecate it
            # Train and evaluate model
            #training_result = self.train_model(data_path, X_train, y_train, X_test, y_test, feature_columns)
            
            # Deploy model (if appropriate)
            endpoint_url = self.deploy_model(
                model_path=training_result["model_path"],
                metrics=training_result["metrics"],
                run_id=training_result["run_id"]
            )

            # Calculate pipeline duration
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Pipeline completed successfully in {duration:.2f} seconds")

            return {
                "run_id": training_result["run_id"],
                "metrics": training_result["metrics"],
                "model_path": training_result["model_path"],
                "endpoint_url": endpoint_url,
                "duration": duration,
                "status": "success",
                "best_params": training_result.get("best_params", {}), #Include hyperparameters
            }

        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}", exc_info=True)

            # Calculate pipeline duration despite failure
            duration = (datetime.now() - start_time).total_seconds()

            return {
                "status": "failed",
                "error": str(e),
                "duration": duration
            }


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="ML Pipeline")
    parser.add_argument("--project-id", required=True, help="GCP Project ID")
    parser.add_argument("--region", default="us-central1", help="GCP Region")
    parser.add_argument("--input-data-uri", required=True, help="URI to input data")
    parser.add_argument("--output-dir", required=True, help="Output directory for model artifacts")
    parser.add_argument("--model-name", required=True, help="Name of the model")
    parser.add_argument(
        "--experiment-name", default="ml-model-training", help="MLflow experiment name"
    )
    parser.add_argument(
        "--deploy-env",
        default="staging",
        choices=["staging", "production"],
        help="Deployment environment",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Initialize and run pipeline
    pipeline = MLPipeline(
        project_id=args.project_id,
        region=args.region,
        input_data_uri=args.input_data_uri,
        output_dir=args.output_dir,
        model_name=args.model_name,
        experiment_name=args.experiment_name,
        deploy_env=args.deploy_env,
    )

    result = pipeline.run()

    if result["status"] == "success":
        logger.info(f"Pipeline completed successfully. Model metrics: {result['metrics']}")
        exit(0)
    else:
        logger.error(f"Pipeline failed: {result['error']}")
        exit(1)