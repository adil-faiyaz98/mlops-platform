"""
Example data transformation functions.
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def convert_to_uppercase(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Converts a specified column in a DataFrame to uppercase.
    """
    logger.info(f"Converting column '{column}' to uppercase.")
    if column not in df.columns:
        logger.warning(f"Column '{column}' not found in DataFrame. Skipping.")
        return df
    df[column] = df[column].str.upper()
    return df

def add_new_column(df: pd.DataFrame, column: str, value: Any) -> pd.DataFrame:
    """Adds a new column to the DataFrame with the specified value."""
    logger.info(f"Adding new column '{column}' with value '{value}'.")
    df[column] = value
    return df

if __name__ == '__main__':
    # Example usage (for testing)
    try:
        data = {'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']}
        df = pd.DataFrame(data)

        df = convert_to_uppercase(df.copy(), "col2")
        print(df)
        df = add_new_column(df.copy(), "col3", "d")
        print(df)
    except Exception as e:
        logger.error(f"Test error: {e}")