#  This is a script to deploy the dataflow job to GCP
# Deprecated - Use Cloud Build to deploy the dataflow job


# PROJECT="gcp-project-id" # Your GCP Project
# BUCKET_NAME="gcp-project" # You will need to set the name with Bucket Name (Need It)
# REGION="us-central1" # Set region here

# # Allow Public Access (For Test - Restrict it or add private ips)
# # Create GCS Bucket (Replace Your Project and Bucket Name Here!)
# gsutil mb -l $REGION gs://$BUCKET_NAME

# # Set Tooling for the API
# #Allow gsutil to access
# gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME

# #Export command
# export CLOUDSDK_PYTHON_SITEPACKAGES=1

# # Install dependencies
# sudo apt-get update
# sudo apt-get install -yq python3-pip

# #Upgrade pip
# sudo pip3 install apache_beam[gcp] --upgrade
# sudo pip3 install -r requirements.txt

# # This will be ran locally or on Vertex.
# #Deploy to gcp function (You will need to set this to env mode)
# export BUCKET_NAME
# export PROJECT

# # Allow you the right configurations from the file.
# #gcloud functions deploy process-data \
# #--region us-central1 \
# #--runtime python39 \
# #--trigger-http \
# #--allow-unauthenticated