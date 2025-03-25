import pandas as pd
from data_pipeline.ingestion import load_data_from_gcs

def test_load_data_from_gcs():
    # Requires setting up a test GCS bucket and a test CSV file.
    test_bucket = "your-test-bucket"
    test_blob = "test_data.csv"

    # Implement upload file and test bucket.
    test_data = """col1,col2\n1,a\n2,b"""
    #Load from GCS
    df = load_data_from_gcs(test_bucket, test_blob)

    #Verify the columns and count.
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2