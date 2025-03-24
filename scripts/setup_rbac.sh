#!/bin/bash
set -e

# Read environment variables
PROJECT_ID=$(gcloud config get-value project)
SERVICE_NAME="gcpFunctionAPI"
RUNTIME_SA_NAME="${SERVICE_NAME}-runtime-sa"
RUNTIME_SA_EMAIL="${RUNTIME_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
MODEL_SECRET_NAME="projects/${PROJECT_ID}/secrets/my-model-secret" # Example: Use full name if possible

# Create runtime service account
echo "Creating runtime service account..."
gcloud iam service-accounts create ${RUNTIME_SA_NAME} \
  --display-name="Runtime service account for ${SERVICE_NAME}"

# Grant minimal required permissions
echo "Granting necessary permissions..."
# Allow reading from storage
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/storage.objectViewer"

# Allow access to Secrets Manager secrets (only the model secret)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --condition="expression=resource.name=='${MODEL_SECRET_NAME}' , title=OnlyModelSecrets"  #More exact name!

# Allow ML model prediction (Vertex AI)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/aiplatform.user"

# Allow error reporting and logging
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
  --role="roles/errorreporting.writer"

# Store service account email in Secret Manager for CI/CD
echo "Storing service account email in Secret Manager..."
echo -n "${RUNTIME_SA_EMAIL}" | gcloud secrets create runtime-sa \
  --data-file=- \
  --replication-policy="automatic"

echo "RBAC setup complete!"
echo "Runtime service account email: ${RUNTIME_SA_EMAIL}"
echo "Runtime service account email stored in Secret Manager as 'runtime-sa'"
echo "Next, deploy the function using the runtime service account."


# To enable Vertex AI, you need to set up the following:
# gcloud services enable aiplatform.googleapis.com