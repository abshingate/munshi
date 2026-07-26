#!/usr/bin/env bash
# Re-authorize this machine's current public IP in the security group.
# Fixes "cannot connect" after the home ISP rotates the IP address.
set -euo pipefail
cd "$(dirname "$0")/.."

MYIP=$(curl -s --max-time 15 https://checkip.amazonaws.com | tr -d '[:space:]')
[[ -n "$MYIP" ]] || { echo "Could not detect your public IP — is the internet working?"; exit 1; }

echo "Your current public IP: $MYIP"
if grep -q "allowed_cidr" terraform.tfvars 2>/dev/null; then
  sed -i '' -e "s|allowed_cidr = \"[^\"]*\"|allowed_cidr = \"$MYIP/32\"|" terraform.tfvars
else
  echo "allowed_cidr = \"$MYIP/32\"" >> terraform.tfvars
fi

echo "Updating the cloud firewall to trust this address..."
terraform apply -auto-approve -input=false >/dev/null
echo "Done. Try connecting again (run the Turn ON button if the machine is off)."
