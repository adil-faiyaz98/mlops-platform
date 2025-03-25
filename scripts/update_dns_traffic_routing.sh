# Update Route53 records to point to the new endpoint
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [
      {
        "Action": "UPSERT",
        "ResourceRecordSet": {
          "Name": "api.mlops.example.com",
          "Type": "A",
          "AliasTarget": {
            "HostedZoneId": "'$LOAD_BALANCER_HOSTED_ZONE_ID'",
            "DNSName": "'$LOAD_BALANCER_DNS'",
            "EvaluateTargetHealth": true
          }
        }
      }
    ]
  }'