#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="gcpFunctionAPI"
REGION="us-central1"

# Grant invocation permission to a specific service account.
# This allows the "other-app" application to invoke the Cloud Run service.
gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
  --region=${REGION} \
  --member="serviceAccount:other-app@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# DO NOT USE allUsers UNLESS YOU ABSOLUTELY REQUIRE PUBLIC ACCESS
# gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
#   --region=${REGION} \
#   --member="allUsers" \
#   --role="roles/run.invoker"

echo "Cloud Run service ${SERVICE_NAME} configured with authentication policies"