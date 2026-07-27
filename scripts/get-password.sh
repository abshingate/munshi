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

# Default fenced users (Accountant/Auditor), if enabled — safe to share with
# the person taking that role; they cannot touch system settings, API keys or
# backups. See README "Multiple users".
USERS_JSON=$(terraform output -json user_passwords 2>/dev/null || echo '{}')
if [[ "$USERS_JSON" != "{}" && -n "$USERS_JSON" ]]; then
  echo ""
  echo "$USERS_JSON" | python3 -c '
import json, sys
for name, pw in sorted(json.load(sys.stdin).items()):
    print(f"User    : {name}")
    print(f"Password: {pw}")
'
fi
