"""
Connector for reading data from CSV files.
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)

def read_csv(file_path: str) -> pd.DataFrame:
    """
    Reads data from a CSV file into a Pandas DataFrame.
    """
    logger.info(f"Reading data from CSV file: {file_path}")
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Successfully read CSV file. Shape: {df.shape}")
        return df
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        raise

if __name__ == '__main__':
    # Example usage (for testing)
    try:
        data = {'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']}
        df = pd.DataFrame(data)
        df.to_csv("sample.csv", index=False)  # Create a sample CSV

        data = read_csv("sample.csv")
        print(data)
        os.remove("sample.csv")  # Delete the file
    except Exception as e:
        logger.error(f"Test error: {e}")