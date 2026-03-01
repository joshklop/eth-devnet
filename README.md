# eth-devnet

OP Stack L2 devnet using Docker Compose. Supports three modes via profiles: L1-only, L2-only, or a full L1+L2 devnet.

## Quick Start

### Full Devnet (L1 + L2)

Spins up a local L1 (Geth + Lighthouse) and deploys a fresh OP Stack L2 on top of it. No configuration needed.

```bash
docker compose --profile l1 --profile l2 up -d
```

This starts all services: L1 execution/consensus, validator, contract deployment pipeline, and the L2 stack (op-reth, op-node, op-batcher).

### L1-Only

Runs just the local Ethereum L1 chain (Geth + Lighthouse + validator). Useful for L1 development or testing without the OP Stack.

```bash
docker compose --profile l1 up -d
```

### L2-Only (External L1)

Deploys a fresh OP Stack L2 against an existing L1. Requires `L1_RPC_URL`, `L1_BEACON_URL`, `L1_CHAIN_CONFIG` (optional for mainnet and sepolia), and `L2_CHAIN_ID`.

```bash
L1_RPC_URL=http://my-l1:8545 \
L1_BEACON_URL=http://my-l1:5052 \
L1_CHAIN_CONFIG=http://my-l1:8080/genesis.json \
L2_CHAIN_ID=1010101 \
DEPLOYER_ACCOUNT=0xYOUR_PRIVATE_KEY \
docker compose --profile l2 up -d
```

Only L2 services start. The deploy pipeline connects to the external L1 to deploy contracts, then boots the L2 chain.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `L1_RPC_URL` | `http://geth:8545` | L1 execution layer RPC endpoint |
| `L1_BEACON_URL` | `http://lighthouse:5052` | L1 consensus layer beacon API endpoint |
| `L1_CHAIN_CONFIG` | `/genesis-data/metadata/genesis.json` | Path or URL to L1 genesis JSON. In full devnet mode this file exists automatically. For L2-only against a well-known chain (mainnet, sepolia), the file won't exist and op-node omits the flag. For custom/unknown L1 chains, set this to a URL (e.g. `http://my-l1:8080/genesis.json`) and op-node will fetch it. |
| `L2_CHAIN_ID` | `10200` | L2 chain ID |
| `DEPLOYER_ACCOUNT` | `0xac0974bec...f2ff80` | Private key used to deploy all contracts to L1 (deterministic deployer, superchain, implementations, L2 chain). Must have ETH on the L1 to pay for gas. |

### When do you need to set what?

| Mode | Required Variables |
|------|--------------------|
| Full devnet (`--profile l1 --profile l2`) | None |
| L1-only (`--profile l1`) | None |
| L2-only, well-known L1 (`--profile l2`) | `L1_RPC_URL`, `L1_BEACON_URL`, `DEPLOYER_ACCOUNT` |
| L2-only, custom/devnet L1 (`--profile l2`) | `L1_RPC_URL`, `L1_BEACON_URL`, `L1_CHAIN_CONFIG`, `DEPLOYER_ACCOUNT` |

## Services

### L1 Services (profile: `l1`)

Only started when using `--profile l1`. Not needed when pointing at an external L1.

| Service | Description |
|---------|-------------|
| `genesis` | Generates L1 genesis config and validator keys |
| `geth-init` | Initializes Geth datadir from genesis |
| `geth` | L1 execution layer client |
| `lighthouse` | L1 consensus layer beacon node |
| `lighthouse-vc` | L1 validator client |
| `validator-keygen` | Generates validator keystores |
| `genesis-server` | Serves L1 genesis metadata over HTTP (port 8080) |

### L2 Services (profile: `l2`)

| Service | Description |
|---------|-------------|
| `l1-el-ready` | Polls L1 RPC until blocks are being produced |
| `deploy-deterministic-deployer` | Deploys the CREATE2 deployer to L1 |
| `bootstrap-superchain` | Deploys superchain contracts to L1 |
| `bootstrap-implementations` | Deploys OP Stack implementation contracts to L1 |
| `l2-deploy-init` | Scaffolds op-deployer intent for the L2 chain |
| `l2-deploy-apply` | Deploys L2 chain contracts to L1 |
| `l2-deploy-inspect` | Extracts L2 genesis, rollup config, and JWT |
| `l2-fund-accounts` | Funds sequencer and batcher accounts on L1 |
| `op-reth-init` | Initializes op-reth with L2 genesis |
| `op-reth` | L2 execution engine (port 9545) |
| `l2-el-ready` | Waits for op-reth RPC to be responsive |
| `op-node` | L2 derivation / consensus (port 8547) |
| `op-batcher` | Submits L2 batches to L1 (port 8548) |
| `blob-archiver` | Archives L1 blobs to local storage |
| `blob-api` | Serves archived blobs over HTTP (port 5058) |

## Exposed Ports

| Port | Service | Protocol |
|------|---------|----------|
| 8545 | geth (L1 EL) | HTTP RPC |
| 8546 | geth (L1 EL) | WebSocket |
| 8551 | geth (L1 EL) | Engine API |
| 5052 | lighthouse (L1 CL) | Beacon API |
| 8080 | genesis-server | HTTP |
| 9545 | op-reth (L2 EL) | HTTP RPC |
| 9546 | op-reth (L2 EL) | WebSocket |
| 8547 | op-node | RPC |
| 8548 | op-batcher | RPC |
| 5058 | blob-api | HTTP |

## Tear Down

```bash
# Stop everything and remove volumes
docker compose --profile l1 --profile l2 down -v
```

## Test Accounts

All accounts are derived from the standard test mnemonic:
`test test test test test test test test test test test junk`

| Role | Address | Private Key |
|------|---------|-------------|
| Admin / Funder | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` | `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80` |
| Sequencer | `0x70997970C51812dc3A010C7d01b50e0d17dc79C8` | `0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d` |
| Batcher | `0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC` | `0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a` |
