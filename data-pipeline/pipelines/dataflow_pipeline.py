import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import argparse
import logging
import pandas as pd #Added to validate file.

def run(argv=None):
    """Main entry point; defines and executes the pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input',
        dest='input',
        default='gs://your-input-bucket/input.txt',
        help='Input file to process.')
    parser.add_argument(
        '--output',
        dest='output',
        default='gs://your-output-bucket/output',
        help='Output file to write results to.')
    known_args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(pipeline_args)

    with beam.Pipeline(options=pipeline_options) as pipeline:
        # Read the text file into a PCollection.
        lines = pipeline | 'Read' >> beam.io.ReadFromText(known_args.input)

        # Transform: Count words in each line
        word_counts = lines | 'Split' >> beam.FlatMap(lambda line: line.split()) \
                          | 'PairWithOne' >> beam.Map(lambda word: (word, 1)) \
                          | 'GroupAndSum' >> beam.CombinePerKey(sum)

        # Format the word counts
        formatted_results = word_counts | 'Format' >> beam.Map(lambda word_count: '%s: %s' % word_count)

        # Write the formatted results to the output file.
        formatted_results | 'Write' >> beam.io.WriteToText(known_args.output, num_shards=1)

def test_pipeline(input_file:str, output_file:str):
    """Test the code and verify."""
    try:
        data = {'text': ['hello world', 'beam pipeline', 'apache beam']}
        df = pd.DataFrame(data)
        df.to_csv(input_file, index=False)
        print("Successfully wrote") #Load here - to avoid loading into GCS.

        #Local Variable.
        dataflowCodeTest = dataflowCode(input=input_file, output=output_file).test()

        #Check output test
        print(dataflowCodeTest)

        is_data = False #Boolean variable to check before it loads up and if something is wrong.
        # Add the load in to show to load a file from gs
        try:
           if (dataflowCodeTest == "Test completed"):
             print ("Test Completed")
             dfCheck = pd.read_csv(output_file)
             print(dfCheck) # Load csv and to check.

             print(os.remove(output_file)) #Delete Output File to show as valid.
             print(os.remove(input_file)) #Deletes if load as good.
             is_data = True

           else:
              is_data = False

        except Exception as e:
            # Output has failed.
            print (f"Model deployment errors found.")
            is_data = False
            raise Exception("Test_pipeline function has failed to pass and has output errors")

    except Exception as e:
      # Input loading of the data test failure
      is_data = False
      print(f"The first test of loading the file has failed")
      print (e) #Error and code will still follow through
      raise Exception("Check what are your inputs")

class dataflowCode(object):
  """Added code with parameter value"""
  def __init__(self, input, output):
    self.input = input #Setting up Input.
    self.output = output # Setting up outputs.

  def setCodeRunner(self, input1, out1):
      """Testing the codes locally first."""
      with beam.Pipeline() as pipeline:
          # Load the text file[pattern] into a PCollection.
          lines = pipeline | 'ReadMyFile' >> beam.io.ReadFromText(input1) # Replace with your input
          # Write the output to a file.
          lines | 'WriteMyFile' >> beam.io.WriteToText(out1, num_shards=1) # Replace with your output

  def test(self):
    """Set this output for this part for the check list - to ensure output is correctly used."""
    try: #Load the code
      print("Loading Dataflow runner codes: ") # Check DataFlow codes are in
      self.setCodeRunner(self.input, self.output) # Calling the codes
    except:
      return "The codes failed to run or DataFlow packages are missing - Update." # Return this code for check

    return "Test completed" # After it loads and pass through the file.

if __name__ == '__main__':
    import logging
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Loading Main Function")

    try:
        logging.info("Running TestFunction Before Deploying") # Run this to test all function and codes.
        test_pipeline("input.txt", "output.txt") # All this to load, and test.
        run() # For testing purpose - All this will validate everything
    except Exception as e: # Catch if something goes
        logging.error(f"The entire test code has failed: {e}") # Error codes - Load all error code function.