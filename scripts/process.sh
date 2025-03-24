#process.sh
#!/bin/bash

# Set Environment variables
PROJECT="cloudfunctions"
BUCKET_NAME="gcp-ml-model"
JOB_NAME="vertex-train-model" # Unique to the model
REGION="us-central1"

# Setup Tooling 
export CLOUDSDK_PYTHON_SITEPACKAGES=1
sudo apt-get update
sudo apt-get install -yq python3-pip
sudo pip3 install apache_beam[gcp] --upgrade

# Deploy dataflow
python3 ./process-raw-csv.py \
--project=${PROJECT} \
--region=${REGION} \
--input="gs://${BUCKET_NAME}/raw" \
--output="gs://${BUCKET_NAME}/process" \
--job_name=${JOB_NAME}