#!/usr/bin/env bash
# Start the Tally workstation, fix a stale IP allowlist, and print how to connect.
#
# The allowlist check is here rather than in a separate script because a stale
# entry is invisible: the browser simply hangs, which looks exactly like the
# machine being down. Users then reasonably conclude the server is broken.
# Checking at the moment of connecting is the only time it reliably gets caught.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION=$(terraform output -raw region)
ID=$(terraform output -raw instance_id)

# ---------------------------------------------------------------------------
# 1. Is this machine's current address still trusted by the cloud firewall?
#
# Done BEFORE starting the VM so a fix and a boot happen in one wait, not two.
# Never fatal: if the check itself fails (no network, curl missing), say so and
# carry on. A diagnostic that blocks the thing it diagnoses is worse than none.
# ---------------------------------------------------------------------------
check_allowlist() {
  # In CloudShell we would detect Amazon's address, not the user's, and
  # "fixing" it would lock the user out further. Skip with an explanation.
  if [[ -n "${AWS_EXECUTION_ENV:-}" ]] || [[ -d /home/cloudshell-user ]]; then
    echo "  (skipping IP check — in CloudShell this would detect Amazon's"
    echo "   address, not yours. Use Fleet Manager, or run this from your Mac.)"
    return 0
  fi

  local myip allowed
  myip=$(curl -s --max-time 10 https://checkip.amazonaws.com 2>/dev/null | tr -d '[:space:]' || true)
  if [[ -z "$myip" ]]; then
    echo "  (could not detect your public IP — skipping the allowlist check)"
    return 0
  fi

  allowed=$(grep -oE 'allowed_cidr[[:space:]]*=[[:space:]]*"[^"]*"' terraform.tfvars 2>/dev/null \
            | grep -oE '[0-9.]+/[0-9]+' || true)

  if [[ "$allowed" == "$myip/32" ]]; then
    echo "  your IP $myip is already trusted"
    return 0
  fi

  echo ""
  echo "  Your public IP has changed:"
  echo "    firewall trusts : ${allowed:-(none set)}"
  echo "    you are now on  : $myip"
  echo ""
  echo "  Without this the browser just hangs, as if the machine were off."
  echo "  Updating the firewall to trust $myip ..."

  if grep -q "allowed_cidr" terraform.tfvars 2>/dev/null; then
    sed -i.bak -e "s|allowed_cidr = \"[^\"]*\"|allowed_cidr = \"$myip/32\"|" terraform.tfvars
    rm -f terraform.tfvars.bak
  else
    echo "allowed_cidr = \"$myip/32\"" >> terraform.tfvars
  fi

  if terraform apply -auto-approve -input=false >/dev/null 2>&1; then
    echo "  firewall updated."
  else
    echo "  WARNING: terraform apply failed. Run ./scripts/fix-ip.sh and read"
    echo "  the error. RDP and Fleet Manager may still work."
  fi
}

echo "Checking network access ..."
check_allowlist

# ---------------------------------------------------------------------------
# 2. Start the machine.
# ---------------------------------------------------------------------------
echo ""
echo "Starting $ID in $REGION ..."
aws ec2 start-instances --region "$REGION" --instance-ids "$ID" >/dev/null
aws ec2 wait instance-running --region "$REGION" --instance-ids "$ID"

IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

# The VM upserts this Route 53 record with its current IP at every boot
# (ADR-0018), so prefer the hostname: the raw IP changes on every restart and
# a bookmarked IP breaks silently.
HOST=$(grep -oE 'dns_hostname[[:space:]]*=[[:space:]]*"[^"]*"' terraform.tfvars 2>/dev/null \
       | sed -E 's/.*"([^"]*)".*/\1/' || true)

echo ""
echo "Instance is running. Give Windows ~2 minutes to finish booting, then connect:"
echo ""
if [[ -n "$HOST" ]]; then
  echo "  Browser : https://$HOST:8443   (Amazon DCV — accept the certificate warning, login: Administrator)"
  echo "  RDP     : $HOST   (user: Administrator)"
  echo ""
  echo "  Use the hostname, not the IP — the IP ($IP) changes at every restart."
  echo "  DNS may take a minute to catch up after boot; if so, use $IP once."
else
  echo "  Browser : https://$IP:8443   (Amazon DCV — accept the certificate warning, login: Administrator)"
  echo "  RDP     : $IP   (user: Administrator)"
fi
echo ""
echo "Password : ./scripts/get-password.sh"
echo "When done: ./scripts/stop.sh   (or it auto-stops after ~1h idle)"
