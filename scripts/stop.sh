#!/usr/bin/env bash
# Stop the Tally workstation. Data is fully preserved; billing drops to storage only.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION=$(terraform output -raw region)
ID=$(terraform output -raw instance_id)

echo "Stopping $ID ..."
aws ec2 stop-instances --region "$REGION" --instance-ids "$ID" >/dev/null
aws ec2 wait instance-stopped --region "$REGION" --instance-ids "$ID"
echo "Stopped. You are now only paying for the disk (a few \$/month)."
