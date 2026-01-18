#!/bin/bash

OP_WHALE=${OP_WHALE:-0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266}

# Deterministic Deployer
# https://github.com/Arachnid/deterministic-deployment-proxy

cast send 0x3fab184622dc19b6109349b94811493bf2a45362 \
    --from "$OP_WHALE" \
    --value 10000000000000000 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

cast rpc eth_sendRawTransaction 0xf8a58085174876e800830186a08080b853604580600e600039806000f350fe7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe03601600081602082378035828234f58015156039578182fd5b8082525050506014600cf31ba02222222222222222222222222222222222222222222222222222222222222222a02222222222222222222222222222222222222222222222222222222222222222

# Deploy Gnosis Safe

# Create a 1/1 multisig with gnosis safe with the OP_WHALE as the signer -> output an owner safe address

# Deploy superchain with the owner safe address (op-deployer)

# Update the l1 owner_safe_address in the manifest
