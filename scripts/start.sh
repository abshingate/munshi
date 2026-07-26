#!/usr/bin/env bash
# Start the Tally workstation and print its connection details.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION=$(terraform output -raw region)
ID=$(terraform output -raw instance_id)

echo "Starting $ID in $REGION ..."
aws ec2 start-instances --region "$REGION" --instance-ids "$ID" >/dev/null
aws ec2 wait instance-running --region "$REGION" --instance-ids "$ID"

IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo ""
echo "Instance is running. Give Windows ~2 minutes to finish booting, then connect:"
echo ""
echo "  Browser : https://$IP:8443   (Amazon DCV — accept the certificate warning, login: Administrator)"
echo "  RDP     : $IP   (user: Administrator)"
echo ""
echo "Password : ./scripts/get-password.sh"
echo "When done: ./scripts/stop.sh   (or it auto-stops after ~1h idle)"
