#!/bin/bash
# filepath: c:\Users\adilm\repositories\Python\sagemaker-end-to-end-deployment\ops\backup\automated-backup.sh

# Set variables
SOURCE_BUCKET="mlops-models"
BACKUP_BUCKET="mlops-model-backup"
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
LOG_FILE="/var/log/mlops-backup/backup-${TIMESTAMP}.log"
ALERT_EMAIL="mlops-alerts@example.com"
RETENTION_DAYS=30

# Ensure log directory exists
mkdir -p $(dirname $LOG_FILE)

# Log start
echo "Starting automated backup at $(date)" | tee -a $LOG_FILE

# Check if source bucket exists
if ! aws s3 ls s3://${SOURCE_BUCKET} &>/dev/null; then
    echo "ERROR: Source bucket ${SOURCE_BUCKET} not found!" | tee -a $LOG_FILE
    echo "Backup failed at $(date)" | tee -a $LOG_FILE
    
    # Send alert
    echo "MLOps Backup Failed: Source bucket not found" | mail -s "ALERT: MLOps Backup Failed" $ALERT_EMAIL
    exit 1
fi

# Check if backup bucket exists
if ! aws s3 ls s3://${BACKUP_BUCKET} &>/dev/null; then
    echo "Backup bucket ${BACKUP_BUCKET} not found. Creating..." | tee -a $LOG_FILE
    
    # Create backup bucket with versioning
    aws s3 mb s3://${BACKUP_BUCKET} --region us-east-1 || {
        echo "ERROR: Failed to create backup bucket!" | tee -a $LOG_FILE
        echo "Backup failed at $(date)" | tee -a $LOG_FILE
        
        # Send alert
        echo "MLOps Backup Failed: Could not create backup bucket" | mail -s "ALERT: MLOps Backup Failed" $ALERT_EMAIL
        exit 1
    }
    
    # Enable versioning
    aws s3api put-bucket-versioning \
      --bucket ${BACKUP_BUCKET} \
      --versioning-configuration Status=Enabled
    
    # Enable encryption
    aws s3api put-bucket-encryption \
      --bucket ${BACKUP_BUCKET} \
      --server-side-encryption-configuration '{
        "Rules": [
          {
            "ApplyServerSideEncryptionByDefault": {
              "SSEAlgorithm": "AES256"
            }
          }
        ]
      }'
    
    # Add lifecycle policy for old versions
    aws s3api put-bucket-lifecycle-configuration \
      --bucket ${BACKUP_BUCKET} \
      --lifecycle-configuration '{
        "Rules": [
          {
            "ID": "Delete-old-versions",
            "Status": "Enabled",
            "NoncurrentVersionExpiration": {
              "NoncurrentDays": '$RETENTION_DAYS'
            }
          }
        ]
      }'
fi

echo "Starting sync from ${SOURCE_BUCKET} to ${BACKUP_BUCKET}..." | tee -a $LOG_FILE

# Sync with specific flags for backup purposes
aws s3 sync s3://${SOURCE_BUCKET}/ s3://${BACKUP_BUCKET}/ \
  --storage-class STANDARD_IA \
  --delete \
  --source-region us-east-1 \
  --region us-east-1 2>&1 | tee -a $LOG_FILE

# Check if sync was successful
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "Backup completed successfully at $(date)" | tee -a $LOG_FILE
    
    # Create a manifest of backed-up files
    echo "Creating backup manifest..." | tee -a $LOG_FILE
    aws s3 ls s3://${BACKUP_BUCKET}/ --recursive > /tmp/backup-manifest-${TIMESTAMP}.txt
    
    # Upload manifest to the backup bucket
    aws s3 cp /tmp/backup-manifest-${TIMESTAMP}.txt s3://${BACKUP_BUCKET}/manifests/backup-manifest-${TIMESTAMP}.txt
    
    # Clean up local manifest
    rm /tmp/backup-manifest-${TIMESTAMP}.txt
    
    # Send success notification
    echo "MLOps Backup Completed Successfully. See attached log." | mail -s "MLOps Daily Backup Success" -a $LOG_FILE $ALERT_EMAIL
else
    echo "ERROR: Backup failed at $(date)" | tee -a $LOG_FILE
    
    # Send alert
    echo "MLOps Backup Failed. See attached log for details." | mail -s "ALERT: MLOps Backup Failed" -a $LOG_FILE $ALERT_EMAIL
    exit 1
fi