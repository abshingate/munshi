#!/usr/bin/env bash
# Create a fenced, non-administrator Windows user on the VM for RDP access —
# e.g. an accountant (entry) or an auditor (review). Idempotent: re-running
# resets the password. Prints the generated password ONCE — save it.
#
#   ./scripts/add-vm-user.sh Accountant entry     # read/write Tally data + documents
#   ./scripts/add-vm-user.sh Auditor    review    # documents read-only; Tally opens
#                                                 # (display-only enforced via Tally security)
#
# Such users can NEVER: install software, change system settings, read the AI
# app's API key (C:\TallyAI), or touch backups (fenced by repair.ps1). When a
# real person joins, two follow-ups: allow their IP in the firewall (ADR-0019)
# and add a matching named user inside Tally (F1 > Security) so the Edit Log
# attributes their vouchers by name.
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

USERNAME="${1:-}"; MODE="${2:-entry}"
if [[ -z "$USERNAME" || ! "$MODE" =~ ^(entry|review)$ ]]; then
  echo "Usage: $0 <Username> <entry|review>"; exit 1
fi

REGION=$(terraform output -raw region)
ID=$(terraform output -raw instance_id)

STATE=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].State.Name' --output text)
if [[ "$STATE" != "running" ]]; then
  echo "Instance is $STATE — start it first (./scripts/start.sh)."; exit 1
fi

PW=$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-16)

PARAMS=$(mktemp)
trap 'rm -f "$PARAMS"' EXIT
USERNAME="$USERNAME" MODE="$MODE" PW="$PW" python3 - > "$PARAMS" <<'PYEOF'
import json, os
u, mode, pw = os.environ["USERNAME"], os.environ["MODE"], os.environ["PW"]
cmds = [
    f"$p = ConvertTo-SecureString '{pw}' -AsPlainText -Force",
    f"if (-not (Get-LocalUser -Name '{u}' -ErrorAction SilentlyContinue)) "
    f"{{ New-LocalUser -Name '{u}' -Password $p -PasswordNeverExpires | Out-Null; Write-Output 'created' }} "
    f"else {{ Set-LocalUser -Name '{u}' -Password $p; Write-Output 'password reset' }}",
    f"Add-LocalGroupMember -Group 'Remote Desktop Users' -Member '{u}' -ErrorAction SilentlyContinue",
]
if mode == "entry":
    cmds.append(f"icacls 'C:\\TallyData' /grant '{u}:(OI)(CI)M' | Out-Null; Write-Output 'grants: Tally data + documents read/write'")
else:
    cmds.append(f"icacls 'C:\\TallyData' /grant '{u}:(OI)(CI)RX' | Out-Null")
    # Tally needs write inside company-data folders (numeric names) even to open
    cmds.append(
        "Get-ChildItem 'C:\\TallyData' -Directory | Where-Object { $_.Name -match '^[0-9]+$' } | "
        f"ForEach-Object {{ icacls $_.FullName /grant '{u}:(OI)(CI)M' | Out-Null }}; "
        "Write-Output 'grants: documents read-only, company data open-able (display-only via Tally security)'")
cmds.append(f"net user '{u}' | Select-String 'Local Group'")
print(json.dumps({"commands": cmds}))
PYEOF

CMD=$(aws ssm send-command --region "$REGION" --instance-ids "$ID" \
  --document-name "AWS-RunPowerShellScript" \
  --parameters "file://$PARAMS" \
  --query 'Command.CommandId' --output text)

ST=""
for _ in $(seq 1 60); do
  ST=$(aws ssm get-command-invocation --region "$REGION" --command-id "$CMD" \
    --instance-id "$ID" --query 'Status' --output text 2>/dev/null)
  [[ "$ST" == "Success" || "$ST" == "Failed" ]] && break
  perl -e 'select(undef,undef,undef,5)' 2>/dev/null || python3 -c 'import time; time.sleep(5)'
done

aws ssm get-command-invocation --region "$REGION" --command-id "$CMD" \
  --instance-id "$ID" --query 'StandardOutputContent' --output text

if [[ "$ST" == "Success" ]]; then
  echo ""
  echo "User '$USERNAME' ($MODE) is ready. They connect with any RDP client"
  echo "(e.g. the free 'Windows App' on Mac/iPad/Windows) to the machine's address."
  echo ""
  echo "  Username: $USERNAME"
  echo "  Password: $PW        <-- shown only this once"
  echo ""
  echo "Follow-ups when a real person joins: allow their IP in the firewall"
  echo "(ADR-0019) and add a matching named user inside Tally (F1 > Security)."
else
  echo "FAILED — check AWS SSM Run Command history for details."; exit 1
fi
