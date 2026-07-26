#!/usr/bin/env bash
# End-to-end readiness check for the Tally workstation.
# Verifies the AWS side (instance, backups, alarms, protection) and — when the
# machine is running — executes the on-VM health check remotely via SSM.
# Exit code: 0 = all good, 1 = issues found (printed in red).
set -uo pipefail
cd "$(dirname "$0")/.."

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; RST=$'\033[0m'
ISSUES=0
pass() { echo "${GRN}PASS${RST}  $1"; }
warn() { echo "${YLW}WARN${RST}  $1"; }
fail() { echo "${RED}FAIL${RST}  $1"; ISSUES=$((ISSUES+1)); }

REGION=$(terraform output -raw region 2>/dev/null) || { fail "Terraform outputs missing — is it deployed? (terraform apply)"; exit 1; }
ID=$(terraform output -raw instance_id)

echo "== AWS infrastructure =="

STATE=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
if [[ -z "$STATE" || "$STATE" == "None" ]]; then
  fail "Instance $ID not found in $REGION"
  exit 1
fi
pass "Instance exists ($ID, state: $STATE)"

TP=$(aws ec2 describe-instance-attribute --region "$REGION" --instance-id "$ID" \
  --attribute disableApiTermination --query 'DisableApiTermination.Value' --output text)
[[ "$TP" == "True" ]] && pass "Termination protection enabled" \
                      || fail "Termination protection is OFF — data at risk (terraform apply to fix)"

ENC=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId' --output text)
VOLENC=$(aws ec2 describe-volumes --region "$REGION" --volume-ids "$ENC" \
  --query 'Volumes[0].Encrypted' --output text)
[[ "$VOLENC" == "True" ]] && pass "Disk is encrypted" || fail "Disk is NOT encrypted"

DLM=$(aws dlm get-lifecycle-policies --region "$REGION" \
  --query "Policies[?contains(Description, 'tally')].State | [0]" --output text 2>/dev/null)
[[ "$DLM" == "ENABLED" ]] && pass "Daily snapshot policy is ENABLED" \
                          || fail "Daily snapshot policy missing/disabled — no backups! (terraform apply)"

SNAPS=$(aws ec2 describe-snapshots --region "$REGION" --owner-ids self \
  --filters "Name=volume-id,Values=$ENC" --query 'length(Snapshots)' --output text 2>/dev/null || echo 0)
if [[ "${SNAPS:-0}" -gt 0 ]]; then pass "Snapshots exist ($SNAPS found)"
else warn "No snapshots yet — the first one is taken tonight at 2 AM IST (normal on day one)"; fi

ALARM=$(aws cloudwatch describe-alarms --region "$REGION" \
  --alarm-name-prefix "tally" --query 'length(MetricAlarms)' --output text)
[[ "${ALARM:-0}" -gt 0 ]] && pass "Idle auto-stop alarm in place" \
                          || warn "Idle auto-stop alarm not found — a forgotten machine will keep billing"

SUB=$(aws sns list-subscriptions --region "$REGION" \
  --query "Subscriptions[?contains(TopicArn, 'tally')].SubscriptionArn | [0]" --output text 2>/dev/null)
if [[ "$SUB" == "PendingConfirmation" ]]; then
  warn "Email alerts PENDING — click 'Confirm subscription' in the email from AWS"
elif [[ -n "$SUB" && "$SUB" != "None" ]]; then pass "Email alert subscription confirmed"
else warn "No email alert subscription found (set alert_email in terraform.tfvars)"; fi

if [[ "$STATE" != "running" ]]; then
  echo ""
  warn "Instance is $STATE — on-VM checks skipped. Run ./scripts/start.sh first for a full check."
else
  echo ""
  echo "== Connectivity (from this machine) =="
  IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
  if [[ "$(uname)" == "Darwin" ]]; then
    # -G is macOS nc's connect-timeout flag
    nc -z -G 5 "$IP" 8443 >/dev/null 2>&1 && pass "DCV browser port 8443 reachable (https://$IP:8443)" \
      || fail "Port 8443 unreachable — has your home IP changed? Run scripts/fix-ip.sh"
    nc -z -G 5 "$IP" 3389 >/dev/null 2>&1 && pass "RDP port 3389 reachable" \
      || fail "Port 3389 unreachable — has your home IP changed? Run scripts/fix-ip.sh"
  else
    # CloudShell runs inside AWS — its own IP is not in allowed_cidr, so an
    # unreachable port here proves nothing about the user's access. Skip.
    warn "Port reachability skipped (only meaningful from the user's own computer)"
  fi

  PING=$(aws ssm describe-instance-information --region "$REGION" \
    --filters "Key=InstanceIds,Values=$ID" --query 'InstanceInformationList[0].PingStatus' --output text 2>/dev/null)
  if [[ "$PING" != "Online" ]]; then
    warn "SSM agent not online yet (status: ${PING:-none}) — on-VM health check skipped; normal in the first minutes after boot"
  else
    pass "SSM agent online (Fleet Manager browser fallback available)"
    echo ""
    echo "== On-VM health check (via SSM) =="
    CMD=$(aws ssm send-command --region "$REGION" --instance-ids "$ID" \
      --document-name "AWS-RunPowerShellScript" \
      --parameters 'commands=["powershell -ExecutionPolicy Bypass -File C:\\HealthCheck\\health-check.ps1"]' \
      --query 'Command.CommandId' --output text)
    for _ in $(seq 1 30); do
      ST=$(aws ssm get-command-invocation --region "$REGION" --command-id "$CMD" \
        --instance-id "$ID" --query 'Status' --output text 2>/dev/null)
      [[ "$ST" == "Success" || "$ST" == "Failed" ]] && break
      # brief pause between polls (portable, no sleep-blocking issues)
      perl -e 'select(undef,undef,undef,2)' 2>/dev/null || python3 -c 'import time; time.sleep(2)'
    done
    OUT=$(aws ssm get-command-invocation --region "$REGION" --command-id "$CMD" \
      --instance-id "$ID" --query 'StandardOutputContent' --output text)
    echo "$OUT" | while IFS= read -r line; do
      case "$line" in
        PASS*) echo "${GRN}${line}${RST}" ;;
        WARN*) echo "${YLW}${line}${RST}" ;;
        FAIL*) echo "${RED}${line}${RST}" ;;
        *)     echo "$line" ;;
      esac
    done
    REMOTE_FAILS=$(echo "$OUT" | grep -c '^FAIL')
    if [[ "$REMOTE_FAILS" -gt 0 ]]; then
      ISSUES=$((ISSUES + REMOTE_FAILS))
    elif [[ "$ST" == "Failed" ]]; then
      ISSUES=$((ISSUES + 1))
    fi
  fi
fi

echo ""
if [[ $ISSUES -gt 0 ]]; then
  echo "${RED}RESULT: $ISSUES ISSUE(S) FOUND — see FAIL lines above.${RST}"
  exit 1
else
  echo "${GRN}RESULT: SYSTEM READY.${RST}"
fi
