# /project_root/tests/data_processing/test_ingestion.py
import pytest
import pandas as pd
from src.data_processing import ingestion
from unittest.mock import patch
from src.utils.config import config # Used config!
import io

# Create new test cases for local configuration for test file.
def getTestCasesDataProcessing (success, fileType, side_effect = "good"):
  cases = []
  def makeTest(mName = "TEST_NAME",mSuccess= True, mFile = 'sample.csv', isGCS = False, mSideEffect = None, mSideArgs={}):
    return {"mName" : mName, "mSuccess":mSuccess, "mFile" : mFile, "isGCS":isGCS, "mSideEffect":mSideEffect,"mSideArgs":mSideArgs} #Name, what we want with the name, and so on.

  class mockBufferData(): #Mock the buffer that connects to see what data to connect to.
    test:str = "default"
    def read(self): #Sample Return
      return self.test
  buffer = mockBufferData()

  def createSideEffect(file): #Return the file.
    with open(file, "r") as f:
      if (fileType == "csv"):
        buffer.test = f.read()
        return buffer
      else:
        raise ValueError("Type not implemented")
        return None #Type
  def createSuccessDF(testData = None): #Sample success result
    return pd.DataFrame(testData)


  #####################Set Local File####################################
  gcsPathTest = './sample.csv' # Sample. Replace with your sample
  cases.append(makeTest(mName="GOOD_FILE_Load", mSuccess = True, mFile=gcsPathTest, mSideEffect= lambda x: createSideEffect(gcsPathTest))) #Create a good data test if there's data to start from

  return cases
########################################Test- Cases#################################################

@pytest.mark.parametrize(
    "test_case",
    getTestCasesDataProcessing(True,"csv")
) #Run Tests
def test_csv(test_case,monkeypatch,test_config):
    from src.data_processing.ingestion import load_data_from_gcs

    def local_path(input_data): #To set the new file (Mock with it)
      from google.cloud import storage # What service google requires.

      #Create Mock here
      #Mock Bucket name and the load file.
      bucket = storage.Client().bucket
      bucket.get_blob = MagicMock(side_effect=test_case["mSideEffect"])
      return "CSV PASS" #Return CSV Pass to mock file, the result test is good.

    monkeypatch.setattr("src.data_processing.ingestion.load_data_from_gcs", local_path) # Mock it in Dataflow.

    #################Test here if valid result.###################
    try:
      local_path(test_case["mFile"])
      with open(test_case["mFile"], "r") as f: #Check and open up the csv
          print (f.read()) #Print everything
      #Check Assert to confirm results
      assert test_case["mName"] == "GOOD_FILE_Load"
    except Exception as e:
      pytest.fail(f"{e}") #If there's something Wrong.