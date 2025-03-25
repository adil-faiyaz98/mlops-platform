# Get latest automated backup snapshot
LATEST_SNAPSHOT=$(aws rds describe-db-snapshots \
  --db-instance-identifier mlops-db \
  --query "reverse(sort_by(DBSnapshots, &SnapshotCreateTime))[0].DBSnapshotIdentifier" \
  --output text)

# Restore database from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier mlops-db-restored \
  --db-snapshot-identifier $LATEST_SNAPSHOT \
  --db-instance-class db.t3.medium

# Wait for database to become available
aws rds wait db-instance-available --db-instance-identifier mlops-db-restored

# Update connection strings in Kubernetes secrets
kubectl create secret generic db-credentials \
  --from-literal=host=mlops-db-restored.example.region.rds.amazonaws.com \
  --from-literal=username=admin \
  --from-literal=password=$DB_PASSWORD \
  --dry-run=client -o yaml | kubectl apply -f -


