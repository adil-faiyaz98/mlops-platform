"""
Data preprocessing and feature engineering script.
"""

import pandas as pd
import numpy as np
import argparse
import logging
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Removes duplicate rows from the DataFrame."""
    logger.info("Removing duplicate rows.")
    df_no_duplicates = df.drop_duplicates()
    logger.info(f"Removed {len(df) - len(df_no_duplicates)} duplicate rows.")
    return df_no_duplicates

def remove_outliers(df: pd.DataFrame, column: str, threshold: float = 3.0) -> pd.DataFrame:
    """Removes outliers from a specified column using the Z-score method."""
    logger.info(f"Removing outliers from column '{column}'.")
    if column not in df.columns:
        logger.warning(f"Column '{column}' not found in DataFrame. Skipping outlier removal.")
        return df
    z_scores = np.abs((df[column] - df[column].mean()) / df[column].std())
    df_no_outliers = df[z_scores < threshold]
    logger.info(f"Removed {len(df) - len(df_no_outliers)} outliers from column '{column}'.")
    return df_no_outliers

def handle_missing_values(df: pd.DataFrame, columns: List[str], strategy: str = 'mean') -> pd.DataFrame:
    """Handles missing values in the specified columns using the specified strategy."""
    logger.info(f"Handling missing values in columns {columns} using strategy '{strategy}'.")
    for column in columns:
        if column not in df.columns:
            logger.warning(f"Column '{column}' not found in DataFrame. Skipping missing value handling for this column.")
            continue
        imputer = SimpleImputer(strategy=strategy)
        df[column] = imputer.fit_transform(df[[column]])
    return df

def correct_skewness(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Corrects skewness in a specified column using log transformation."""
    logger.info(f"Correcting skewness in column '{column}'.")
    if column not in df.columns:
        logger.warning(f"Column '{column}' not found in DataFrame. Skipping skewness correction.")
        return df
    df[column] = np.log1p(df[column])
    return df

def create_interaction_term(df: pd.DataFrame, col1: str, col2: str, new_col: str) -> pd.DataFrame:
    """Creates an interaction term between two columns."""
    logger.info(f"Creating interaction term '{new_col}' between '{col1}' and '{col2}'.")
    if col1 not in df.columns or col2 not in df.columns:
        logger.warning(f"One or both of columns '{col1}' and '{col2}' not found in DataFrame. Skipping interaction term creation.")
        return df
    df[new_col] = df[col1] * df[col2]
    return df

def create_polynomial_features(df: pd.DataFrame, column: str, degree: int = 2) -> pd.DataFrame:
    """Creates polynomial features for a specified column."""
    logger.info(f"Creating polynomial features for column '{column}' with degree {degree}.")
    if column not in df.columns:
        logger.warning(f"Column '{column}' not found in DataFrame. Skipping polynomial feature creation.")
        return df
    for i in range(2, degree + 1):
        df[f"{column}_{i}"] = df[column] ** i
    return df

def process_data(df: pd.DataFrame, sensitive_feature: str, numerical_columns: List[str], categorical_columns: List[str]) -> pd.DataFrame:
    """
    Applies a series of preprocessing steps to the DataFrame.
    """
    logger.info("Starting data processing.")

    # Example preprocessing steps (customize as needed)
    df = remove_duplicates(df)
    for column in numerical_columns:
        df = remove_outliers(df, column)
    df = handle_missing_values(df, numerical_columns + categorical_columns, 'mean')
    for column in numerical_columns:
        df = correct_skewness(df, column)
    df = create_interaction_term(df, numerical_columns[0], numerical_columns[1], 'interaction_term')
    df = create_polynomial_features(df, numerical_columns[0], degree=3)

    # Separate sensitive feature if needed
    if sensitive_feature in df.columns:
        sensitive_data = df[sensitive_feature]
        df = df.drop(columns=[sensitive_feature])
        logger.info(f"Sensitive feature '{sensitive_feature}' separated.")
    else:
        sensitive_data = None
        logger.warning(f"Sensitive feature '{sensitive_feature}' not found in DataFrame.")

    logger.info("Data processing completed.")
    return df, sensitive_data

def split_data(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> tuple:
    """Splits the data into training and testing sets."""
    logger.info(f"Splitting data into training and testing sets with test size {test_size}.")
    train_df, test_df = train_test_split(df, test_size=test_size, random_state=random_state)
    return train_df, test_df

def main(input_data: str, output_train_data: str, output_test_data: str, sensitive_feature: str, numerical_columns: List[str], categorical_columns: List[str]):
    """Main function to execute data processing and feature engineering."""
    logger.info("Starting data processing pipeline.")

    try:
        # Load data
        df = pd.read_csv(input_data)
        logger.info(f"Data loaded successfully from {input_data}. Shape: {df.shape}")

        # Process data
        processed_df, sensitive_data = process_data(df.copy(), sensitive_feature, numerical_columns, categorical_columns)

        # Split data
        train_df, test_df = split_data(processed_df)

        # Save processed data
        train_df.to_csv(output_train_data, index=False)
        test_df.to_csv(output_test_data, index=False)
        logger.info(f"Processed training data saved to {output_train_data}")
        logger.info(f"Processed testing data saved to {output_test_data}")

    except Exception as e:
        logger.error(f"An error occurred during data processing: {e}")
        raise

    logger.info("Data processing pipeline completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data processing and feature engineering script.")
    parser.add_argument("--input_data", required=True, help="Path to the input data CSV file.")
    parser.add_argument("--output_train_data", required=True, help="Path to save the processed training data CSV file.")
    parser.add_argument("--output_test_data", required=True, help="Path to save the processed testing data CSV file.")
    parser.add_argument("--sensitive_feature", required=True, help="Name of the sensitive feature column.")
    parser.add_argument("--numerical_columns", nargs='+', required=True, help="List of numerical columns.")
    parser.add_argument("--categorical_columns", nargs='+', required=True, help="List of categorical columns.")
    args = parser.parse_args()

    main(args.input_data, args.output_train_data, args.output_test_data, args.sensitive_feature, args.numerical_columns, args.categorical_columns)