"""
Custom data transformation functions.
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def replace_values(df: pd.DataFrame, column: str, replace_dict: Dict[str, str]) -> pd.DataFrame:
    """
    Replaces values in a specified column based on a dictionary mapping.
    """
    logger.info(f"Replacing values in column '{column}' using dictionary: {replace_dict}")
    if column not in df.columns:
        logger.warning(f"Column '{column}' not found in DataFrame. Skipping replacement.")
        return df
    df[column] = df[column].replace(replace_dict)
    return df

def fill_missing_with_value(df: pd.DataFrame, column: str, value: Any) -> pd.DataFrame:
    """Fills missing values in a specified column with a given value."""
    logger.info(f"Filling missing values in column '{column}' with value: {value}")
    if column not in df.columns:
        logger.warning(f"Column '{column}' not found in DataFrame. Skipping missing value fill.")
        return df
    df[column] = df[column].fillna(value)
    return df

if __name__ == '__main__':
    # Example usage (for testing)
    try:
        data = {'col1': [1, 2, 3], 'col2': ['a', 'b', None]}
        df = pd.DataFrame(data)

        df = replace_values(df.copy(), "col2", {"a": "A", "b": "B"})
        print(df)
        df = fill_missing_with_value(df.copy(), "col2", "UNKNOWN")
        print(df)
    except Exception as e:
        logger.error(f"Test error: {e}")