#!/bin/bash
set -euo pipefail

docker network create eth-devnet
docker compose up -d && docker wait chain-ready
OPTIMISM_DIR=$HOME/repos/optimism ./op.sh
OPTIMISM_DIR=$HOME/repos/optimism ./l2.sh
docker compose --profile l2 up -d --force-recreate
docker compose --profile l2 down -v
docker compose down -v
docker network rm eth-devnet
