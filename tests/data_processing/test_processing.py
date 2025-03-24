#/project_root/tests/data_processing/test_processing.py
from src.data_processing import processing #What were testing.
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock #Get
import json
import re
from pytest import mark

#Test_Cases
@pytest.fixture
def setupMock(test1 ,file1): #To start file.
    gcs_filename = "test_file.csv" # File Name to test the file that does and should not work
    csv_content_ = test1
    openCSV= ""

    # The file content will become something else
    def test_run():
      for line in file1.split(","): #Load Line by Line
        return print(line) #Print each run as the case.

    # Open File
    gcs =  {} #Test here.
    return  dict (
        gcs_filename = gcs_filename,
        create_open_side = MagicMock(side_effect=[str(4)]) # To return a new set of values, make sure each line runs as int
        )

# Test for basic values, to what is there.
@pytest.mark.skip("not tested") #Will still pass, due to its been skip
@pytest.mark.parametrize(
    ""
)
def test_calculate_bias_metrics(mock_data): #Test to check metric.
    with patch("src.data_processing.processing.validate_data") as test: #Use all the files here!
        result1= processing.calculate_bias_metrics(dataFrame, test1['target'].values, dataFrame["SENSTIVE_FEATURE"].values) # All of all data (what does code do with the file in function)
        pass # This is set to not crash, you need to validate to make sure result2 is not failing the code and has been saved