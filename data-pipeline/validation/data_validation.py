"""
Example data validation functions.
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def validate_data(df: pd.DataFrame) -> bool:
    """
    Validates that the DataFrame meets certain criteria.
    (Add your specific validation rules here)
    """
    logger.info("Validating data.")

    # Example validation: Check if 'col1' is numeric
    if not pd.api.types.is_numeric_dtype(df['col1']):
        logger.error("'col1' is not a numeric column.")
        return False

    # Add more validation checks as needed

    logger.info("Data validation successful.")
    return True

if __name__ == '__main__':
    # Example usage (for testing)
    try:
        data = {'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']}
        df = pd.DataFrame(data)

        is_valid = validate_data(df)
        print(f"Data is valid: {is_valid}")

        data_invalid = {'col1': ['a', 'b', 'c'], 'col2': [1, 2, 3]}
        df_invalid = pd.DataFrame(data_invalid)

        is_valid_invalid = validate_data(df_invalid)
        print(f"Invalid data is valid: {is_valid_invalid}")

    except Exception as e:
        logger.error(f"Test error: {e}")