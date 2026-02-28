#!/bin/bash
set -euo pipefail

export OPTIMISM_DIR=$HOME/repos/optimism 
docker compose down -v --remove-orphans
docker compose up -d
