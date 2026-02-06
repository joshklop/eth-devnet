#!/bin/bash
set -euo pipefail

# Configuration
OP_WHALE=${OP_WHALE:-0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266}
PRIVATE_KEY=${PRIVATE_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}
L1_RPC_URL=${L1_RPC_URL:-http://localhost:8545}
OUTPUT_DIR=${OUTPUT_DIR:-./deployments}
OPTIMISM_DIR=${OPTIMISM_DIR:-../optimism}
OP_DEPLOYER=${OP_DEPLOYER:-$OPTIMISM_DIR/op-deployer/bin/op-deployer}

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=== Step 1: Deploy Deterministic Deployer ==="
# https://github.com/Arachnid/deterministic-deployment-proxy

cast send 0x3fab184622dc19b6109349b94811493bf2a45362 \
    --from "$OP_WHALE" \
    --value 10000000000000000 \
    --private-key "$PRIVATE_KEY" \
    --rpc-url "$L1_RPC_URL"

cast rpc eth_sendRawTransaction 0xf8a58085174876e800830186a08080b853604580600e600039806000f350fe7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe03601600081602082378035828234f58015156039578182fd5b8082525050506014600cf31ba02222222222222222222222222222222222222222222222222222222222222222a02222222222222222222222222222222222222222222222222222222222222222 \
    --rpc-url "$L1_RPC_URL"

echo "Deterministic deployer deployed at 0x4e59b44847b379578588920cA78FbF26c0B4956C"

echo "=== Step 2: Deploy Safe Infrastructure ==="
# Deploy Safe singleton and SafeProxyFactory, then create 1/1 Safe with OP_WHALE as owner

# Verify forge dependencies exist
CONTRACTS_LIB="$OPTIMISM_DIR/packages/contracts-bedrock/lib"
if [ ! -d "$CONTRACTS_LIB/forge-std/src" ] || [ ! -d "$CONTRACTS_LIB/safe-contracts/contracts" ]; then
    echo "ERROR: Forge dependencies not found at $CONTRACTS_LIB"
    echo "OPTIMISM_DIR must point to an optimism repo with initialized submodules."
    echo "Run: cd \$OPTIMISM_DIR && git submodule update --init --recursive"
    exit 1
fi

cd "$OPTIMISM_DIR/op-service/gnosis/contracts"

# Run the forge script and capture output
FORGE_OUTPUT=$(forge script script/DeploySafe.s.sol:DeploySafe \
    --rpc-url "$L1_RPC_URL" \
    --private-key "$PRIVATE_KEY" \
    --broadcast \
    2>&1)

echo "$FORGE_OUTPUT"

# Parse Safe instance address from forge output
OWNER_SAFE=$(echo "$FORGE_OUTPUT" | grep "Safe instance deployed at:" | awk '{print $NF}')

if [ -z "$OWNER_SAFE" ]; then
    echo "ERROR: Failed to parse Safe address from forge output"
    exit 1
fi

echo "Owner Safe deployed at: $OWNER_SAFE"

# Return to original directory
cd - > /dev/null

echo "=== Step 3: Bootstrap Superchain ==="

"$OP_DEPLOYER" bootstrap superchain \
    --l1-rpc-url="$L1_RPC_URL" \
    --private-key="$PRIVATE_KEY" \
    --outfile="$OUTPUT_DIR/superchain.json" \
    --superchain-proxy-admin-owner="$OWNER_SAFE" \
    --protocol-versions-owner="$OWNER_SAFE" \
    --guardian="$OWNER_SAFE"

echo "Superchain bootstrap complete. Output: $OUTPUT_DIR/superchain.json"
cat "$OUTPUT_DIR/superchain.json"

echo "=== Step 4: Bootstrap Implementations ==="

# Parse outputs from superchain bootstrap
SUPERCHAIN_CONFIG_PROXY=$(jq -r '.superchainConfigProxyAddress' "$OUTPUT_DIR/superchain.json")
PROTOCOL_VERSIONS_PROXY=$(jq -r '.protocolVersionsProxyAddress' "$OUTPUT_DIR/superchain.json")
SUPERCHAIN_PROXY_ADMIN=$(jq -r '.proxyAdminAddress' "$OUTPUT_DIR/superchain.json")

"$OP_DEPLOYER" bootstrap implementations \
    --l1-rpc-url="$L1_RPC_URL" \
    --private-key="$PRIVATE_KEY" \
    --outfile="$OUTPUT_DIR/implementations.json" \
    --superchain-config-proxy="$SUPERCHAIN_CONFIG_PROXY" \
    --protocol-versions-proxy="$PROTOCOL_VERSIONS_PROXY" \
    --superchain-proxy-admin="$SUPERCHAIN_PROXY_ADMIN" \
    --upgrade-controller="$OWNER_SAFE" \
    --challenger="$OWNER_SAFE"

echo "Implementations bootstrap complete. Output: $OUTPUT_DIR/implementations.json"
cat "$OUTPUT_DIR/implementations.json"

echo "=== Step 5: Generate Combined Output ==="

# Combine all outputs into a single state file for netchef
jq -s '.[0] * .[1] * {ownerSafe: "'"$OWNER_SAFE"'"}' \
    "$OUTPUT_DIR/superchain.json" \
    "$OUTPUT_DIR/implementations.json" > "$OUTPUT_DIR/l1_state.json"

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo "Owner Safe: $OWNER_SAFE"
echo "State file: $OUTPUT_DIR/l1_state.json"
echo ""
echo "To verify contracts are deployed:"
echo "  cast code $OWNER_SAFE --rpc-url $L1_RPC_URL"
echo ""
echo "To verify Safe ownership:"
echo "  cast call $OWNER_SAFE \"getOwners()(address[])\" --rpc-url $L1_RPC_URL"
