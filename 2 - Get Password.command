#!/bin/bash
cd "$(dirname "$0")"
./scripts/get-password.sh
echo ""
read -p "Finished. Press the Enter key to close this window."
