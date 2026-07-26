#!/usr/bin/env bash
# Remotely self-heal the VM: re-sync scripts from the assets bucket and
# reinstall anything missing/broken. Safe to run any time; takes minutes.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; RST=$'\033[0m'
REGION=$(terraform output -raw region) || exit 1
ID=$(terraform output -raw instance_id)

STATE=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].State.Name' --output text)
if [[ "$STATE" != "running" ]]; then
  echo "Instance is $STATE — start it first (./scripts/start.sh)."; exit 1
fi

echo "Running remote repair (sync from S3 + reinstall anything broken)..."
CMD=$(aws ssm send-command --region "$REGION" --instance-ids "$ID" \
  --document-name "AWS-RunPowerShellScript" \
  --parameters 'commands=["powershell -ExecutionPolicy Bypass -File C:\\HealthCheck\\update-and-repair.ps1"]' \
  --query 'Command.CommandId' --output text)

for _ in $(seq 1 120); do
  ST=$(aws ssm get-command-invocation --region "$REGION" --command-id "$CMD" \
    --instance-id "$ID" --query 'Status' --output text 2>/dev/null)
  [[ "$ST" == "Success" || "$ST" == "Failed" ]] && break
  perl -e 'select(undef,undef,undef,10)' 2>/dev/null || python3 -c 'import time; time.sleep(10)'
done

aws ssm get-command-invocation --region "$REGION" --command-id "$CMD" \
  --instance-id "$ID" --query 'StandardOutputContent' --output text |
while IFS= read -r line; do
  case "$line" in
    OK*)     echo "${GRN}${line}${RST}" ;;
    FIXED*)  echo "${YLW}${line}${RST}" ;;
    FAILED*) echo "${RED}${line}${RST}" ;;
    *)       echo "$line" ;;
  esac
done
[[ "$ST" == "Success" ]] || { echo "${RED}Repair reported remaining failures — run again or see C:\\HealthCheck\\repair-log.txt on the VM.${RST}"; exit 1; }
