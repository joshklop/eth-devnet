#!/bin/bash
set -euo pipefail

docker compose up -d && docker wait chain-ready && OPTIMISM_DIR=$HOME/repos/optimism ./op.sh
docker compose down -v
