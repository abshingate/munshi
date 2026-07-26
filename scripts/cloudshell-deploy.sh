#!/usr/bin/env bash
# Deploy from AWS CloudShell (the terminal inside the AWS website).
# NOTHING needs to be installed on the user's own computer — not Terraform,
# not the AWS CLI, nothing. CloudShell is already logged in to their account.
#
# How the user gets here (browser only):
#   1. Log in to aws.amazon.com, choose the Mumbai region (top-right).
#   2. Click the CloudShell icon (looks like >_ ) in the top bar.
#   3. Actions -> Upload file -> upload the setup zip, then:
#        unzip -o TallyCloud-new.zip -d tally && cd tally
#        bash scripts/cloudshell-deploy.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

echo "==> Checking Terraform (installing a private copy if needed)"
if ! command -v terraform >/dev/null 2>&1; then
  TFV=1.9.8
  mkdir -p ~/.local/bin
  curl -sLo /tmp/tf.zip "https://releases.hashicorp.com/terraform/${TFV}/terraform_${TFV}_linux_amd64.zip"
  unzip -o -q /tmp/tf.zip -d ~/.local/bin
  grep -q '.local/bin' ~/.bashrc 2>/dev/null || echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.bashrc
  export PATH=$PATH:$HOME/.local/bin
fi
echo "    Terraform OK."

echo "==> Checking AWS connection"
aws sts get-caller-identity >/dev/null 2>&1 || { echo "CloudShell has no AWS access — are you inside AWS CloudShell?"; exit 1; }
echo "    Connected to account $(aws sts get-caller-identity --query Account --output text)."

if [[ ! -f terraform.tfvars ]]; then
  echo ""
  echo "==> One question: which computer will you CONNECT FROM (home/office)?"
  echo "    CloudShell runs inside Amazon, so your address can't be detected here."
  echo "    On that computer (or your phone on the same Wi-Fi), open this site:"
  echo "        https://checkip.amazonaws.com"
  echo "    and type the number it shows (looks like 122.167.112.252):"
  read -r -p "    Your address: " MYIP
  [[ "$MYIP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "That does not look like an address — run this again."; exit 1; }
  read -r -p "    Email for alerts (billing warnings, auto-shutdown notices): " EMAIL
  {
    echo "allowed_cidr = \"$MYIP/32\""
    [[ -n "$EMAIL" ]] && echo "alert_email  = \"$EMAIL\""
  } > terraform.tfvars
fi

echo "==> Preparing"
terraform init -input=false >/dev/null || { echo "terraform init failed"; exit 1; }

if terraform state list 2>/dev/null | grep -q aws_instance.this; then
  echo "A cloud computer is already linked to this folder — nothing to deploy."
  exit 0
fi

EXISTING=$(aws ec2 describe-instances --region ap-south-1 \
  --filters "Name=tag:Name,Values=tally-workstation" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text 2>/dev/null)
if [[ -n "$EXISTING" && "$EXISTING" != "None" ]]; then
  echo "STOP: this AWS account ALREADY has the cloud computer ($EXISTING)."
  echo "Not creating a second one."
  exit 1
fi

echo "==> Building your cloud computer (a few minutes). Cost: ~Rs. 900-1,000/month with light use."
read -r -p "    Create it now? (y/n): " GO
[[ "$GO" == "y" || "$GO" == "Y" ]] || exit 0
terraform apply -auto-approve -input=false || { echo "Deployment failed — see the error above."; exit 1; }

IP=$(terraform output -raw public_ip_at_apply_time)
echo ""
echo "======================================================================"
echo " DONE! The computer is installing its software (~15 minutes)."
echo ""
echo " Your address today:  https://$IP:8443   (user: Administrator)"
echo " Password (wait ~5 min, then run):   bash scripts/get-password.sh"
echo " Check it's ready:                   bash scripts/check.sh"
echo " Turn off / on later:                bash scripts/stop.sh / start.sh"
echo ""
echo " IMPORTANT — do these two things now:"
echo " 1. Check your email for 'AWS Notification - Subscription Confirmation'"
echo "    and click the link inside it."
echo " 2. In CloudShell: Actions -> Download file, and download BOTH of:"
echo "        $(pwd)/terraform.tfstate"
echo "        $(pwd)/tally-workstation-key.pem"
echo "    Keep them somewhere safe (e.g. email them to yourself). They are"
echo "    the keys to this machine if CloudShell storage is ever cleared."
echo "======================================================================"
