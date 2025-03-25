import pytest
# Test file name
import pytest
import pandas as pd
from airflow.models import DagBag
import os #added the file path.

# from airflow.providers.apache.beam.operators.beam import BeamRunPythonPipelineOperator
# from airflow.providers.google.cloud.transfers.local_to_gcs import LocalToGCSOperator
# From data and models (not used)
# from data_pipeline.connectors import csv_connector
# from data_pipeline.transformations import data_transformations
# from data_pipeline.validation import data_validation

DAG_FOLDER = "data_pipeline/pipelines"

# Create test file path, local and all
data = {'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']} # Creating simple data set for validation purposes.
local_path = "raw_data.csv" # Creating the simple test file.
df = pd.DataFrame(data) #Create as data frame
df.to_csv(local_path, index=False) #Local testing file - Check this file out

def test_dag_loading(): #Test load and it is success.
    """Test whether the DAG loads without errors"""
    dag_bag = DagBag(dag_folder=DAG_FOLDER, include_examples=False)
    dag = dag_bag.get_dag(dag_id="data_pipeline_dag") #Load your model
    assert dag is not None # If None and can not access then error the code.
    assert len(dag_bag.dags) == 1 #Check all models loaded - Make it 1.

    try:
        os.remove("raw_data.csv") # After the test, delete it.
        print("Success for Remove.")

    except FileNotFoundError: #Code to capture if wrong for the loading codes - error.
        print("Please make sure there is nothing and you are starting this file - load.")
        print("Error, the raw file load.")
    except Exception as e: #All exceptions with name
        print("Something else went wrong") #Output function
        print(f"{e}") # For debug.



