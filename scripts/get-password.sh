#!/usr/bin/env bash
# Print the Windows Administrator password (decrypted with the generated key pair).
# Available ~4 minutes after the very first launch.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION=$(terraform output -raw region)
ID=$(terraform output -raw instance_id)
KEY=$(terraform output -raw private_key_file)

PW=$(aws ec2 get-password-data --region "$REGION" --instance-id "$ID" \
  --priv-launch-key "$KEY" --query 'PasswordData' --output text)

if [[ -z "$PW" ]]; then
  echo "Password not ready yet — wait a few minutes after first launch and retry."
  exit 1
fi
echo "User    : Administrator"
echo "Password: $PW"
