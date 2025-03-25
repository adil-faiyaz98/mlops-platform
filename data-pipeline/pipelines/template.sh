#!/bin/bash
#
# This script generates a Dataflow template.
#

# Ensure the script exits immediately if any command fails
set -e

# Set environment variables (replace with your actual values or export them beforehand)
#export PROJECT_ID="your-gcp-project-id"
#export REGION="us-central1"
#export BUCKET_NAME="your-gcs-bucket"
#export TEMPLATE_NAME="your-dataflow-template"

# Check if required environment variables are set
if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ] || [ -z "$BUCKET_NAME" ] || [ -z "$TEMPLATE_NAME" ]; then
  echo "Error: Missing required environment variables. Please set PROJECT_ID, REGION, BUCKET_NAME, and TEMPLATE_NAME."
  exit 1
fi

# Function to check if a program is installed.  A good function to add if needed
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Step: Validation Check: Ensure all are load
echo "Validating Configurations"

if ! command_exists python3; then #Python
  echo "Error: python3 is not installed. Please install before continuing."
  exit 1
fi

if ! command_exists gcloud; then #GCloud Tool Kit
  echo "Error: gcloud is not installed. Please install the GCP before continuing."
  exit 1
fi
#Check if there is correct
if [ ! -d "pipelines" ]; then # If there is folder call Pipelines check.
  echo "Error: The folder does not exist pipelines . check folder"
  exit 1
fi

if [ ! -f "pipelines/dataflow_pipeline.py" ]; then
  echo "Error: The dataflow_pipeline.py is not the pipelines folder.  Check the folders before continuing."
  exit 1
fi
echo "All Settings Valid - Begin the Template Generation"

#Generate the Dataflow template.
echo "Generating Dataflow template..."
python3 pipelines/dataflow_pipeline.py \
  --runner=DataflowRunner \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --staging_location="gs://$BUCKET_NAME/staging" \
  --temp_location="gs://$BUCKET_NAME/temp" \
  --template_location="gs://$BUCKET_NAME/template/$TEMPLATE_NAME" \
  --save_main_session
  
if [ $? -eq 0 ]; then
  echo "Dataflow template generated successfully!"
else
  echo "Error: Dataflow template generation failed."
  exit 1
fi