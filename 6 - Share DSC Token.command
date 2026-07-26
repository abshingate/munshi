#!/bin/bash
cd "$(dirname "$0")"
./scripts/share-dsc.sh
echo ""
read -p "Tunnel closed. Press the Enter key to close this window."
