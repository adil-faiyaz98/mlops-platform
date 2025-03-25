"""
Orchestration of a simple data pipeline.
"""
import logging
import pandas as pd

from data_pipeline.connectors import csv_connector
from data_pipeline.transformations import data_transformations
from data_pipeline.validation import data_validation

logger = logging.getLogger(__name__)

def run_pipeline(input_path: str, output_path: str):
    """
    Runs the data pipeline.
    """
    logger.info("Starting data pipeline.")

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
        logger.error(f"Error in data pipeline: {e}")
        raise

    logger.info("Data pipeline completed successfully.")

if __name__ == '__main__':
    # Example usage
    try:
        data = {'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']}
        df = pd.DataFrame(data)
        df.to_csv("input.csv", index=False)  # Create a sample CSV

        run_pipeline("input.csv", "output.csv")
        os.remove("input.csv")
        os.remove("output.csv")

    except Exception as e:
        logger.error(f"Test error: {e}")