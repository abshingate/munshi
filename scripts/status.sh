#!/usr/bin/env bash
# Show whether the workstation is running and its current IP.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION=$(terraform output -raw region)
ID=$(terraform output -raw instance_id)

aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].{State:State.Name,PublicIP:PublicIpAddress,Type:InstanceType,LaunchedAt:LaunchTime}' \
  --output table
