#!/usr/bin/env bash
# Create a zip of this setup for sharing — no git knowledge needed by anyone.
#   ./scripts/make-share-zip.sh            -> TallyCloud-new.zip (for someone
#                                             deploying their OWN copy; no secrets)
#   ./scripts/make-share-zip.sh operator   -> TallyCloud-operator.zip (controls
#                                             YOUR machine; share only with a
#                                             trusted person — contains the key)
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${1:-new}"
OUT="$HOME/Desktop/TallyCloud-${MODE}.zip"
rm -f "$OUT"

if [[ "$MODE" == "operator" ]]; then
  zip -rq "$OUT" . -x ".git/*" ".terraform/*"
  echo "Created: $OUT"
  echo "WARNING: this zip contains the state file and the password key for YOUR"
  echo "cloud computer. Only give it to someone you trust to operate it."
else
  zip -rq "$OUT" . -x ".git/*" ".terraform/*" "terraform.tfstate*" "*.pem" "terraform.tfvars" "*.backup"
  echo "Created: $OUT"
  echo "Safe to share widely — contains no passwords, keys, or account details."
  echo "The recipient: unzip it, then double-click '0 - First Time Setup' (Mac)"
  echo "or upload it to AWS CloudShell and run scripts/cloudshell-deploy.sh (any browser)."
fi
