#!/bin/bash
set -e

# Required: Fill in these values!
AWS_ACCOUNT_ID="YOUR_AWS_ACCOUNT_ID"  # Replace with your AWS account ID
S3_BUCKET="your-s3-bucket-name"       # Replace with your S3 bucket name
TRAINING_IMAGE_URI="your-training-image-uri"  # Replace with your training image URI

# Optional: You can customize these as needed
REGION="us-east-1" #Can put this in the same region
SAGEMAKER_ROLE_NAME="SageMakerRole"
INSTANCE_TYPE="ml.m5.xlarge"  # Or ml.g4dn.xlarge, ml.p3.2xlarge, etc.
INSTANCE_COUNT=1
VOLUME_SIZE_GB=30
MAX_RUNTIME_SECONDS=86400  # 24 hours

# Create a unique training job name
TRAINING_JOB_NAME="training-job-$(date +%s)"

# Hyperparameters to pass to your training script.  These will be available
# as command-line arguments in your training script.  Adjust these based
# on what your train.py script expects.
HYPERPARAMETERS="--learning-rate 0.001 --batch-size 32 --num-epochs 10"

# Launch SageMaker training job
aws sagemaker create-training-job \
    --training-job-name "${TRAINING_JOB_NAME}" \
    --algorithm-specification "TrainingImage=${TRAINING_IMAGE_URI},TrainingInputMode=File" \
    --role-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:role/${SAGEMAKER_ROLE_NAME}" \
    --input-data-config "[{\"ChannelName\": \"training\", \"DataSource\": {\"S3DataSource\": {\"S3DataType\": \"S3Prefix\", \"S3Uri\": \"s3://${S3_BUCKET}/sagemaker/data/train.csv\", \"S3DataDistributionType\": \"FullyReplicated\"}}, \"ContentType\": \"text/csv\", \"CompressionType\": \"None\"}, {\"ChannelName\": \"validation\", \"DataSource\": {\"S3DataSource\": {\"S3DataType\": \"S3Prefix\", \"S3Uri\": \"s3://${S3_BUCKET}/sagemaker/data/validation.csv\", \"S3DataDistributionType\": \"FullyReplicated\"}}, \"ContentType\": \"text/csv\", \"CompressionType\": \"None\"}]" \
    --output-data-config "S3OutputPath=s3://${S3_BUCKET}/sagemaker/output" \
    --resource-config "InstanceType=${INSTANCE_TYPE},InstanceCount=${INSTANCE_COUNT},VolumeSizeInGB=${VOLUME_SIZE_GB}" \
    --stopping-condition "MaxRuntimeInSeconds=${MAX_RUNTIME_SECONDS}" \
    --hyper-parameters "${HYPERPARAMETERS}" \
    --region "${REGION}"  # Explicitly specify the region
# TO DO: Implement parameter pass to train.py script.

# Check if the training job was launched successfully
if [ $? -eq 0 ]; then
    echo "Training job started: $TRAINING_JOB_NAME"
else
    echo "Error launching training job.  Check the AWS CLI output for details."
    exit 1  # Exit with an error code
fi