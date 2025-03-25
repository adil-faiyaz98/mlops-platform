# training/features/feature_engineering.py

import pandas as pd

def create_dummy_variables(df, column_name):
    """
    Creates dummy variables for a categorical column in a Pandas DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame.
        column_name (str): The name of the categorical column.

    Returns:
        pd.DataFrame: The DataFrame with dummy variables added.
    """
    try:
        dummies = pd.get_dummies(df[column_name], prefix=column_name)
        df = pd.concat([df, dummies], axis=1)
        df = df.drop(column_name, axis=1)  # Remove the original column
        return df
    except Exception as e:
        print(f"Error creating dummy variables: {e}")
        raise


def apply_feature_engineering(df):
    """
    Applies feature engineering steps to a DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: The feature-engineered DataFrame.
    """
    try:
        # Example: Create dummy variables for 'category' column
        if 'category' in df.columns:
            df = create_dummy_variables(df, 'category')

        # Example: Create a new feature 'interaction_feature'
        if 'feature1' in df.columns and 'feature2' in df.columns:
            df['interaction_feature'] = df['feature1'] * df['feature2']

        # Add more feature engineering steps here as needed

        return df

    except Exception as e:
        print(f"Error applying feature engineering: {e}")
        raise


if __name__ == '__main__':
    # Example Usage
    data = {'id': [1, 2, 3], 'category': ['A', 'B', 'A'], 'feature1': [10, 20, 30], 'feature2': [5, 10, 15]}
    df = pd.DataFrame(data)

    engineered_df = apply_feature_engineering(df)
    print(engineered_df)