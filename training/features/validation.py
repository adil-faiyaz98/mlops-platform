"""
Data validation script using pandera.
"""

import pandas as pd
import pandera as pa
from pandera import Column, Check
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InputDataSchema(pa.SchemaModel):
    """
    Schema for input data validation.
    """
    # Example columns (customize as needed)
    numerical_column_example: Column(pa.Float, Check.greater_than_or_equal_to(0))
    numerical_column_example2: Column(pa.Float, Check.greater_than_or_equal_to(0))
    categorical_column_example: Column(pa.String, Check.isin(["category1", "category2"]))
    target: Column(pa.Int, Check.isin([0, 1]))

    class Config:
        strict = True
        coerce = True

def validate_data(input_path: str) -> bool:
    """
    Validates the input data against the defined schema.
    """
    logger.info(f"Validating data from {input_path}")
    try:
        df = pd.read_csv(input_path)
        InputDataSchema.validate(df, lazy=True)
        logger.info("Data validation successful.")
        return True
    except pa.errors.SchemaErrors as e:
        logger.error(f"Data validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during data validation: {e}")
        return False