#!/bin/bash
set -euo pipefail

# Configuration
PRIVATE_KEY=${PRIVATE_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}
L1_RPC_URL=${L1_RPC_URL:-http://localhost:8545}
DEPLOY_DIR=${DEPLOY_DIR:-./deployments}
L2_DATA_DIR=${L2_DATA_DIR:-./l2-data}
OPTIMISM_DIR=${OPTIMISM_DIR:-../optimism}
OP_DEPLOYER=${OP_DEPLOYER:-$OPTIMISM_DIR/op-deployer/bin/op-deployer}
L2_CHAIN_ID=${L2_CHAIN_ID:-10200}

# Addresses from test mnemonic (test test test test test test test test test test test junk)
ADMIN=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
SEQUENCER=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
BATCHER=0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC

# L2 chain ID as 32-byte hex for intent.toml
L2_CHAIN_ID_HEX=$(printf "0x%064x" "$L2_CHAIN_ID")

mkdir -p "$L2_DATA_DIR"

echo "=== Step 1: Extract OPCM Address ==="

if [ ! -f "$DEPLOY_DIR/implementations.json" ]; then
    echo "ERROR: $DEPLOY_DIR/implementations.json not found. Run op.sh first."
    exit 1
fi

OPCM_ADDRESS=$(jq -r '.opcmAddress' "$DEPLOY_DIR/implementations.json")
echo "OPCM address: $OPCM_ADDRESS"

echo "=== Step 2: Scaffold intent with op-deployer init ==="

L1_CHAIN_ID=$(cast chain-id --rpc-url "$L1_RPC_URL")
echo "L1 chain ID: $L1_CHAIN_ID"

"$OP_DEPLOYER" init \
    --l1-chain-id "$L1_CHAIN_ID" \
    --l2-chain-ids "$L2_CHAIN_ID" \
    --workdir "$L2_DATA_DIR" \
    --intent-type custom

echo "=== Step 3: Patch intent.toml ==="

# Read the locator values from the generated intent
INTENT_FILE="$L2_DATA_DIR/intent.toml"
L1_LOCATOR=$(grep '^l1ContractsLocator' "$INTENT_FILE" | sed 's/l1ContractsLocator = "\(.*\)"/\1/')
L2_LOCATOR=$(grep '^l2ContractsLocator' "$INTENT_FILE" | sed 's/l2ContractsLocator = "\(.*\)"/\1/')

echo "L1 contracts locator: $L1_LOCATOR"
echo "L2 contracts locator: $L2_LOCATOR"

cat > "$INTENT_FILE" <<EOF
configType = "custom"
l1ChainID = $L1_CHAIN_ID
l1ContractsLocator = "$L1_LOCATOR"
l2ContractsLocator = "$L2_LOCATOR"
fundDevAccounts = true
useInterop = false
opcmAddress = "$OPCM_ADDRESS"

[[chains]]
id = "$L2_CHAIN_ID_HEX"
baseFeeVaultRecipient = "$ADMIN"
l1FeeVaultRecipient = "$ADMIN"
sequencerFeeVaultRecipient = "$ADMIN"
operatorFeeVaultRecipient = "$ADMIN"
eip1559Denominator = 50
eip1559DenominatorCanyon = 250
eip1559Elasticity = 6
gasLimit = 60_000_000

[chains.roles]
l1ProxyAdminOwner = "$ADMIN"
l2ProxyAdminOwner = "$ADMIN"
systemConfigOwner = "$ADMIN"
unsafeBlockSigner = "$SEQUENCER"
batcher = "$BATCHER"
proposer = "$SEQUENCER"
challenger = "$ADMIN"
EOF

echo "intent.toml written:"
cat "$INTENT_FILE"

echo "=== Step 4: Deploy L2 chain contracts ==="

"$OP_DEPLOYER" apply \
    --workdir "$L2_DATA_DIR" \
    --l1-rpc-url "$L1_RPC_URL" \
    --private-key "$PRIVATE_KEY"

echo "=== Step 5: Extract genesis and rollup config ==="

"$OP_DEPLOYER" inspect genesis \
    --workdir "$L2_DATA_DIR" \
    "$L2_CHAIN_ID" > "$L2_DATA_DIR/genesis.json"

"$OP_DEPLOYER" inspect rollup \
    --workdir "$L2_DATA_DIR" \
    "$L2_CHAIN_ID" > "$L2_DATA_DIR/rollup.json"

echo "Genesis written to $L2_DATA_DIR/genesis.json"
echo "Rollup config written to $L2_DATA_DIR/rollup.json"

echo "=== Step 6: Generate JWT secret ==="

openssl rand -hex 32 > "$L2_DATA_DIR/jwt.txt"
echo "JWT secret written to $L2_DATA_DIR/jwt.txt"

echo "=== Step 7: Fund batcher and sequencer on L1 ==="

cast send "$SEQUENCER" \
    --from "$ADMIN" \
    --value 100ether \
    --private-key "$PRIVATE_KEY" \
    --rpc-url "$L1_RPC_URL"
echo "Funded sequencer ($SEQUENCER) with 100 ETH"

cast send "$BATCHER" \
    --from "$ADMIN" \
    --value 100ether \
    --private-key "$PRIVATE_KEY" \
    --rpc-url "$L1_RPC_URL"
echo "Funded batcher ($BATCHER) with 100 ETH"

echo ""
echo "=========================================="
echo "L2 deployment complete!"
echo "=========================================="
echo "L2 Chain ID: $L2_CHAIN_ID"
echo "Genesis: $L2_DATA_DIR/genesis.json"
echo "Rollup config: $L2_DATA_DIR/rollup.json"
echo "JWT: $L2_DATA_DIR/jwt.txt"
echo ""
echo "Start L2 services:"
echo "  docker compose --profile l2 up -d"
