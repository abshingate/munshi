#!/usr/bin/env bash
# Share the DSC token plugged into THIS Mac with the cloud computer.
# VirtualHere server runs here; the cloud VM's VirtualHere client reaches it
# through an SSH reverse tunnel — free, encrypted, no router changes, no
# EasyFind subscription needed.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

REGION=$(terraform output -raw region) || exit 1
ID=$(terraform output -raw instance_id)
KEY=$(terraform output -raw private_key_file)

APP="local/VirtualHereServerUniversal.app"
if [[ ! -d "$APP" ]]; then
  echo "Downloading the VirtualHere server app (one time)..."
  mkdir -p local
  DMG=$(mktemp -t vhdmg).dmg
  curl -sL --max-time 120 -o "$DMG" "https://www.virtualhere.com/sites/default/files/usbserver/VirtualHereServerUniversal.dmg"
  MNT=$(echo Y | hdiutil attach -nobrowse -readonly "$DMG" | grep -o '/Volumes/.*' | head -1)
  [[ -n "$MNT" ]] || { echo "Could not open the VirtualHere download — try again."; exit 1; }
  cp -R "$MNT"/*.app local/
  hdiutil detach "$MNT" -quiet
  rm -f "$DMG"
fi

STATE=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].State.Name' --output text)
if [[ "$STATE" != "running" ]]; then
  echo "The cloud computer is $STATE — run '1 - Turn ON Tally Computer' first."; exit 1
fi
IP=$(aws ec2 describe-instances --region "$REGION" --instance-ids "$ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo ""
echo "STEP 1  Plug your DSC token into THIS computer (if not already)."
echo "STEP 2  Starting the VirtualHere server app — allow it if macOS asks"
echo "        (it may request your Mac password the first time)."
open "$APP"
echo ""
echo "STEP 3  Secure tunnel to the cloud computer is starting..."
echo ""
echo "   ON THE CLOUD COMPUTER (first time only):"
echo "     - Open desktop folder 'DSC Setup' -> 'VirtualHere Client'"
echo "     - Right-click 'USB Hubs' -> Specify Hubs -> Add -> type:"
echo "           localhost:7575"
echo "     - OK. Your token appears -> right-click it -> 'Use this device'"
echo ""
echo "   KEEP THIS WINDOW OPEN while you sign. Press Ctrl+C here when done."
echo ""
ssh -i "$KEY" \
  -o StrictHostKeyChecking=accept-new \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -N -R 7575:localhost:7575 "Administrator@$IP"
