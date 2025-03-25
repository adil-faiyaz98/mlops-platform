"""
Apache Airflow DAG definition for the data pipeline.
"""
import logging
import os
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.transfers.local_to_gcs import LocalToGCSOperator #If using gcloud
from airflow.providers.apache.beam.operators.beam import BeamRunPythonPipelineOperator #If on premise

from data_pipeline.connectors import csv_connector
from data_pipeline.transformations import data_transformations
from data_pipeline.validation import data_validation

# Configure logging
logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
with DAG(
    dag_id='data_pipeline_dag',
    default_args=default_args,
    schedule_interval=None, #Can change.  ex) '@daily' for daily runs
    catchup=False,
    tags=['mlops', 'data_pipeline']
) as dag:

    # Function to execute data processing (replace with your actual logic)
    def process_data(input_path, output_path):
        try:
            # 1. Read Data
            df = csv_connector.read_csv(input_path)

            # 2. Apply Transformations
            df = data_transformations.convert_to_uppercase(df, "col2")
            df = data_transformations.add_new_column(df, "new_col", 10)

            # 3. Validate Data
            is_valid = data_validation.validate_data(df)
            if not is_valid:
                raise ValueError("Data validation failed.")

            # 4. Save Data
            df.to_csv(output_path, index=False)
            logger.info(f"Successfully wrote data to {output_path}. Shape: {df.shape}")
        except Exception as e:
            logger.error(f"Pipeline Failed with codes.",exc_info = True)
            raise

    # Define tasks
    load_data_gcs = LocalToGCSOperator( #Use gcloud
        task_id="load_data_gcs",
        src="data/raw_data.csv",
        dst="data/raw_data.csv", #Location within bucket and file path, change it.
        bucket="example_bucket", #What Bucket
        gcp_conn_id="gcp_cloud"
    )

    process_data_task = PythonOperator(
        task_id='process_data',
        python_callable=process_data,
        op_kwargs={
            'input_path': '{{ ti.xcom_pull(task_ids="load_data_gcs", key="return_value") }}',  # XCom from load_data_gcs, if you change this.
            'output_path': '/tmp/processed_data.csv'  # Example local path

            #'input_path': 'gs://your-gcs-bucket/data/raw_data.csv',  # Real Data or example load files
            #'output_path': 'gs://your-gcs-bucket/data/processed_data.csv' #Gcloud set this.
        },
    )
    process_data_task.set_upstream(load_data_gcs)

    # Define task dependencies
    #process_data_task #Make it in order for the processing to run correctly.
#Adjust the import statement per the data type that was listed.
# from airflow.providers.apache.beam.operators.beam import BeamRunPythonPipelineOperator
# from airflow.providers.google.cloud.transfers.local_to_gcs import LocalToGCSOperator