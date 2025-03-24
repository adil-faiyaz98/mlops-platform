# process-raw-csv.py
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import argparse

def csv_to_dict(line):
    """Converts a comma separated string to a dictionary."""
    fields = line.split(',')
    return {
        'feature1': float(fields[0]),
        'feature2': float(fields[1]),
        'feature3': float(fields[2]),
        'target': float(fields[3])
    }

def run(argv=None):
    """Main entry point; defines and executes the pipeline."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input',
        dest='input',
        required=True,
        help='Input file to process (GCS path).')
    parser.add_argument(
        '--output',
        dest='output',
        required=True,
        help='Output location (GCS path).')
    known_args, pipeline_args = parser.parse_known_args(argv)

    pipeline_options = PipelineOptions(pipeline_args, save_main_session=True)
    with beam.Pipeline(options=pipeline_options) as pipeline:
        # Read the text file[pattern] into a PCollection.
        lines = pipeline | 'Read' >> beam.io.ReadFromText(known_args.input)

        # Skip the header row.
        header = lines | "TakeHeader" >> beam.combiners.Sample.FixedSizeList(1)
        lines = (
            lines
            | "FilterHeader" >> beam.Filter(lambda row: row != header[0][0])
        )

        #Convert the rows to dictionaries
        records = lines | 'ParseCSV' >> beam.Map(csv_to_dict)

        # Write to GCS as JSON.
        records | 'Write' >> beam.io.WriteToText(
            known_args.output,
            num_shards=1,
            shard_name_template='',
            file_name_suffix='.json')

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run()