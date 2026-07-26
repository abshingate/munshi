#!/usr/bin/env bash
# Verify every external download location the bootstrap/repair depends on is
# still alive. Run locally any time; CI runs it weekly and alerts on failure.
set -uo pipefail
fails=0

check() {
  local code
  code=$(curl -sIL -o /dev/null -w '%{http_code}' --max-time 30 -A "Mozilla/5.0" "$1")
  if [[ "$code" == "200" ]]; then
    echo "OK          $1"
  else
    echo "DEAD ($code)  $1"
    fails=$((fails + 1))
  fi
}

# Chocolatey bootstrap
check "https://community.chocolatey.org/install.ps1"
# Amazon DCV latest server MSI
check "https://d1uj6qtbmh3dt5.cloudfront.net/nice-dcv-server-x64-Release.msi"
# TallyPrime: dynamic-discovery source + last-known-good mirrors (both editions)
check "https://tallysolutions.com/utility/js/DownloadUtility-india.js"
check "https://tallymirror.tallysolutions.com/download_centre/Rel7.1/TP/Full/setup.exe"
check "https://tallymirror.tallysolutions.com/download_centre/Rel7.1/TPEL/Full/setup.exe"
# VirtualHere client (DSC over USB-over-IP)
check "https://www.virtualhere.com/sites/default/files/usbclient/vhui64.exe"
# Claude Code npm package
check "https://registry.npmjs.org/@anthropic-ai/claude-code"
# IP self-detection used by setup/fix-ip
check "https://checkip.amazonaws.com"
# Terraform release used by the CloudShell deployer
check "https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip"

echo ""
if [[ $fails -gt 0 ]]; then
  echo "RESULT: $fails dead URL(s) — update vm/repair.ps1 / scripts before users hit this."
  exit 1
fi
echo "RESULT: all external URLs alive."
