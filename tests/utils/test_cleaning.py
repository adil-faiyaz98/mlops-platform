# /project_root/tests/data_processing/test_cleaning.py

import pytest
import pandas as pd
import numpy as np
from src.data_processing import cleaning

def create_sample_dataframe():
    data = {'feature1': [1, 2, 2, 3, 4, 5, 100],
            'feature2': [6, 7, 7, 8, 9, 10, 200],
            'target': [11, 12, 12, 13, 14, 15, 300]}
    df = pd.DataFrame(data)
    return df

def test_remove_duplicates():
    df = create_sample_dataframe()
    cleaned_df = cleaning.remove_duplicates(df)
    assert cleaned_df.shape == (6, 3)

def test_remove_duplicates_subset():
    df = create_sample_dataframe()
    cleaned_df = cleaning.remove_duplicates(df, subset=['feature1', 'feature2'])
    assert cleaned_df.shape == (6, 3)

def test_remove_outliers_iqr():
    df = create_sample_dataframe()
    cleaned_df = cleaning.remove_outliers(df, 'feature1', method='iqr')
    assert cleaned_df.shape == (6, 3)

def test_remove_outliers_zscore():
    df = create_sample_dataframe()
    cleaned_df = cleaning.remove_outliers(df, 'feature1', method='zscore')
    assert cleaned_df.shape == (6, 3)

def test_remove_outliers_clipping():
    df = create_sample_dataframe()
    cleaned_df = cleaning.remove_outliers(df, 'feature1', method='clipping')
    assert cleaned_df['feature1'].max() <= 9.75 #Check the values to ensure it is being tested.

def test_handle_missing_values_impute_mean():
    df = create_sample_dataframe()
    df.iloc[0, 0] = np.nan
    cleaned_df = cleaning.handle_missing_values(df, method='impute', strategy='mean')
    assert not cleaned_df['feature1'].isnull().any()
    assert cleaned_df['feature1'][0] == 14 #Verify it can pass that.

def test_handle_missing_values_drop():
    df = create_sample_dataframe()
    df.iloc[0, 0] = np.nan
    cleaned_df = cleaning.handle_missing_values(df, method='drop')
    assert cleaned_df.shape == (6, 3) # Make sure only one exist.

def test_correct_skewness():
    df = create_sample_dataframe()
    cleaned_df = cleaning.correct_skewness(df, ['feature1'])
    assert cleaned_df['feature1'].skew() < 0.5 # Make sure its less than