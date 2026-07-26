#!/bin/bash
cd "$(dirname "$0")"
./scripts/fix-ip.sh
echo ""
read -p "Finished. Press the Enter key to close this window."
