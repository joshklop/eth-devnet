#!/usr/bin/env bash
# Run the deposit -> L2 transfers -> withdrawal lifecycle on a fresh devnet.
# This is for local deterministic devnets only; the embedded keys are public.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
RESULTS=${RESULTS:-"$ROOT/experiment-results"}
L1_RPC=${L1_RPC:-http://127.0.0.1:8545}
L2_RPC=${L2_RPC:-http://127.0.0.1:9545}
ROLLUP_RPC=${ROLLUP_RPC:-http://127.0.0.1:8547}
DEPLOYER_KEY=${DEPLOYER_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}
USER_KEY=${USER_KEY:-0x00000000000000000000000000000000000000000000000000000000000a11ce}
USER=$(cast wallet address --private-key "$USER_KEY")

mkdir -p "$RESULTS"
RESULTS=$(cd "$RESULTS" && pwd)
rm -f "$RESULTS/final-sync-status.json"
# Copy the current run's deployment/genesis state before discovering addresses.
docker cp l2-deploy-inspect:/l2-data/state.json "$RESULTS/op-deployer-state.json"
docker cp l2-deploy-inspect:/l2-data/intent.toml "$RESULTS/intent.toml"
docker cp l2-deploy-inspect:/l2-data/rollup.json "$RESULTS/rollup.json"
docker cp genesis:/data/metadata/genesis.json "$RESULTS/l1-genesis.json"
docker cp genesis:/data/metadata/config.yaml "$RESULTS/l1-consensus-config.yaml"
docker cp bootstrap-superchain:/deployments/superchain.json "$RESULTS/superchain.json"
docker cp bootstrap-implementations:/deployments/implementations.json "$RESULTS/implementations.json"

PORTAL=$(python3 - "$RESULTS/op-deployer-state.json" <<'PY'
import json, sys
state = json.load(open(sys.argv[1]))
print(state["opChainDeployments"][0]["OptimismPortalProxy"])
PY
)

if [ "$(cast balance "$USER" --rpc-url "$L2_RPC")" != "0" ]; then
  echo "test user $USER already has an L2 balance; start from fresh volumes" >&2
  exit 1
fi

echo "Depositing 1 ETH through $PORTAL to $USER"
cast send "$PORTAL" \
  'depositTransaction(address,uint256,uint64,bool,bytes)' \
  "$USER" 1000000000000000000 100000 false 0x \
  --value 1ether --private-key "$DEPLOYER_KEY" --rpc-url "$L1_RPC" --json \
  | tee "$RESULTS/deposit-l1-receipt.json"

for _ in $(seq 1 180); do
  balance=$(cast balance "$USER" --rpc-url "$L2_RPC" 2>/dev/null || echo 0)
  [ "$balance" -ge 1000000000000000000 ] 2>/dev/null && break
  sleep 2
done
[ "$(cast balance "$USER" --rpc-url "$L2_RPC")" -ge 1000000000000000000 ]

send_transfer() {
  local label=$1 to=$2 value=$3
  cast send "$to" --value "$value" --private-key "$USER_KEY" \
    --rpc-url "$L2_RPC" --json | tee "$RESULTS/$label-l2-receipt.json"
}
send_transfer transfer-1 0x000000000000000000000000000000000000bEEF 10000000000000000
send_transfer transfer-2 0x000000000000000000000000000000000000cafE 20000000000000000
send_transfer transfer-3 0x000000000000000000000000000000000000D00d 30000000000000000

cast send 0x4200000000000000000000000000000000000010 \
  'bridgeETHTo(address,uint32,bytes)' "$USER" 200000 0x \
  --value 0.1ether --private-key "$USER_KEY" --rpc-url "$L2_RPC" --json \
  | tee "$RESULTS/withdrawal-l2-receipt.json"

TARGET=$(python3 - "$RESULTS/withdrawal-l2-receipt.json" <<'PY'
import json, sys
print(int(json.load(open(sys.argv[1]))["blockNumber"], 16))
PY
)
echo "Waiting for withdrawal-containing L2 block $TARGET to finalize..."
for _ in $(seq 1 180); do
  status=$(curl -sf -H 'Content-Type: application/json' \
    --data '{"jsonrpc":"2.0","method":"optimism_syncStatus","params":[],"id":1}' \
    "$ROLLUP_RPC")
  finalized=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["finalized_l2"]["number"])' <<<"$status")
  echo "finalized L2=$finalized target=$TARGET"
  if [ "$finalized" -ge "$TARGET" ]; then
    printf '%s\n' "$status" > "$RESULTS/final-sync-status.json"
    break
  fi
  sleep 12
done

[ -f "$RESULTS/final-sync-status.json" ]
finalized=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["finalized_l2"]["number"])' \
  < "$RESULTS/final-sync-status.json")
[ "$finalized" -ge "$TARGET" ]

cd "$ROOT"
./scripts/collect-lifecycle-transactions.py \
  --l1-rpc "$L1_RPC" --l2-rpc "$L2_RPC" --rollup-rpc "$ROLLUP_RPC" \
  --user "$USER" \
  --state-file "$RESULTS/op-deployer-state.json" \
  --l1-genesis "$RESULTS/l1-genesis.json" \
  --output-dir "$RESULTS"
echo "Lifecycle succeeded; results are in $RESULTS"
