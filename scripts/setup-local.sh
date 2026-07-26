#!/usr/bin/env bash
# One-time setup for a NEW Mac: installs the needed tools, connects to AWS,
# and deploys the cloud computer (or just links up to an existing one if this
# folder was copied from another machine, state file included).
# Safe to run again any time — it skips whatever is already done.
set -uo pipefail
cd "$(dirname "$0")/.."

step() { echo ""; echo "==> $1"; }

step "Checking Homebrew (the Mac's app installer)"
if ! command -v brew >/dev/null 2>&1 && [[ ! -x /opt/homebrew/bin/brew && ! -x /usr/local/bin/brew ]]; then
  echo "    Installing Homebrew — this can take ~10 minutes."
  echo "    It may ask for your Mac login password (typing is invisible — that's normal)."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
    echo "Homebrew installation failed — check your internet and run this again."; exit 1; }
fi
eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
echo "    Homebrew OK."

step "Checking AWS command-line tool"
command -v aws >/dev/null 2>&1 || brew install awscli
echo "    AWS CLI OK."

step "Checking Terraform"
command -v terraform >/dev/null 2>&1 || brew install hashicorp/tap/terraform || brew install terraform
echo "    Terraform OK."

step "Checking your AWS account connection"
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "    You need the two AWS keys (Access Key ID and Secret Access Key)."
  echo "    Get them from whoever manages your AWS account, or create them at:"
  echo "    AWS Console -> IAM -> Users -> your user -> Security credentials -> Create access key"
  echo ""
  echo "    Region to enter: ap-south-1     Output format: just press Enter"
  echo ""
  aws configure
  aws sts get-caller-identity >/dev/null 2>&1 || { echo "AWS connection failed — check the keys and run this again."; exit 1; }
fi
echo "    Connected to AWS account $(aws sts get-caller-identity --query Account --output text)."

step "Checking your settings file"
if [[ ! -f terraform.tfvars ]]; then
  MYIP=$(curl -s --max-time 15 https://checkip.amazonaws.com | tr -d '[:space:]')
  echo "    Your internet address: $MYIP (only this address will be allowed to connect)"
  read -r -p "    Email for alerts (billing warnings, auto-shutdown notices): " EMAIL
  {
    echo "allowed_cidr = \"$MYIP/32\""
    [[ -n "$EMAIL" ]] && echo "alert_email  = \"$EMAIL\""
  } > terraform.tfvars
fi
echo "    Settings OK."

step "Preparing Terraform"
terraform init -input=false >/dev/null || { echo "terraform init failed"; exit 1; }

if terraform state list 2>/dev/null | grep -q aws_instance.this; then
  echo ""
  echo "A cloud computer is already linked to this folder — nothing to deploy."
  echo "You are ready! Use the numbered buttons:  1 = turn on,  5 = turn off."
  exit 0
fi

# Folder has no state — but does the AWS account already have the workstation?
# (Happens when someone starts from a fresh copy instead of copying the
# original folder. Deploying again would fail half-way on name collisions.)
EXISTING=$(aws ec2 describe-instances --region ap-south-1 \
  --filters "Name=tag:Name,Values=tally-workstation" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null)
if [[ -n "$EXISTING" && "$EXISTING" != "None" ]]; then
  echo ""
  echo "STOP: this AWS account ALREADY has the cloud computer ($EXISTING)."
  echo "Do not create a second one. To control the existing one from this Mac,"
  echo "copy the ORIGINAL folder from the computer that created it (it contains"
  echo "a 'terraform.tfstate' file and a '.pem' file — those are the link to it)."
  exit 1
fi

step "No cloud computer exists yet for this folder"
echo "    Creating it costs roughly Rs. 900-1,000 per month with light use."
read -r -p "    Create it now? (y/n): " GO
[[ "$GO" == "y" || "$GO" == "Y" ]] || { echo "Okay — run this button again whenever you're ready."; exit 0; }

step "Building your cloud computer (takes a few minutes)"
terraform apply -auto-approve -input=false || { echo "Deployment failed — see the error above."; exit 1; }

echo ""
echo "======================================================================"
echo " DONE! The computer is being prepared (software installs ~15 minutes)."
echo ""
echo " 1. If you gave an email above: check your inbox for an AWS email"
echo "    called 'Subscription Confirmation' and click the link inside."
echo " 2. In ~15 minutes, double-click '3 - Check Everything OK' until all"
echo "    lines say PASS, then '2 - Get Password', then '1 - Turn ON' for"
echo "    the address to open in your browser."
echo " 3. Read USER-GUIDE.md for everything else."
echo "======================================================================"
