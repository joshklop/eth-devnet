# op-deployer `develop` on a Glamsterdam L1

## Result

**Passed.** `op-deployer` from Optimism `develop` deployed a complete OP Stack
chain on a post-Amsterdam devnet-8 L1. A fresh account then:

1. received a 1 ETH portal deposit;
2. sent 0.01, 0.02, and 0.03 ETH native L2 transfers;
3. initiated a 0.1 ETH Standard Bridge withdrawal; and
4. had the withdrawal-containing L2 block 223 become safe and finalized.

`final-sync-status.json` records finalized L2 block 303, which is after the
withdrawal block. Both the sequencer and verifier derived the same safe chain.
All collected receipts have status 1.

The complete transaction/gas table is in [`lifecycle-gas-table.md`](lifecycle-gas-table.md).
Machine-readable forms are in `lifecycle-transactions.json` and
`lifecycle-transactions.csv`.

## Provenance

| Component | Version |
|---|---|
| eth-devnet baseline | `ea5b3859a8157362d0e1692f4bf5db2840f12b9a` |
| Optimism `develop` | `fabfc381ad17df149801b957058f38a66e3d0b2d` |
| Built image | `op-deployer:develop-fabfc381ad` |
| Built image ID | `sha256:336409d8fb2ca9e7d01ce33317d9be061168f905ff6640d90721c17def5a5591` |
| L1 chain ID | `7091047534` |
| L2 chain ID | `420120214` |
| L1 execution client | `ethpandaops/geth:glamsterdam-devnet-8` |
| L1 consensus client | `ethpandaops/teku:glamsterdam-devnet-8` |
| Genesis generator | `ethpandaops/ethereum-genesis-generator:6.2.0` |

Gloas/Amsterdam activated at epoch 1, execution timestamp `1787714550`.
Every deployment and lifecycle L1 transaction was in a block at or after that
timestamp. The 35 deployment transactions occupied L1 blocks 33 through 67.

An initial Gloas-at-genesis attempt was rejected by Teku because the generated
Gloas genesis block root did not match the genesis state's latest-block root.
Epoch 1 is the earliest schedule verified to work with these images. The
`l1-el-ready` service now gates local deployment on `amsterdamTime`, so running
both profiles together does not deploy during the pre-fork epoch.

## Gas summary

| Operation | Transactions | Gas used | Total observed fee (wei) | ETH |
|---|---:|---:|---:|---:|
| L1 contract deployment | 35 | 610,627,957 | 612,861,296,637,304,321 | 0.612861296637 |
| L1 sequencer/batcher funding | 2 | 42,000 | 42,069,627,054,000 | 0.000042069627 |
| L1 portal deposit | 1 | 129,038 | 129,090,556,274,134 | 0.000129090556 |
| L2 native transfers | 3 | 63,000 | 26,299,631,019,489 | 0.000026299631 |
| L2 Standard Bridge withdrawal | 1 | 158,213 | 65,001,051,203,256 | 0.000065001051 |
| Supporting L1 blob batches | 3 | 45,000 | 45,007,248,903,216 | 0.000045007249 |

`total observed fee` is execution gas times effective gas price, plus the
receipt-reported L2 L1-data fee, plus blob gas times blob gas price when the L1
receipt has those fields.

## Reproduce

Build the image from a clean Optimism checkout at `develop`:

```bash
git fetch origin develop
git checkout --detach origin/develop
git submodule update --init --recursive

export GIT_VERSION=untagged
export GIT_COMMIT=$(git rev-parse HEAD)
export GIT_DATE=$(git show -s --format=%ct HEAD)
docker buildx bake op-deployer --load \
  --set op-deployer.tags=op-deployer:develop-fabfc381ad \
  --set op-deployer.platform=linux/amd64
```

From this eth-devnet worktree, start from clean volumes. The L2 deployment is
automatically held until the epoch-1 Amsterdam timestamp:

```bash
export COMPOSE_PROJECT_NAME=glamsterdam-opdeployer-develop
export OP_DEPLOYER_IMAGE=op-deployer:develop-fabfc381ad

docker compose --profile l1 --profile l2 down -v --remove-orphans
docker compose --profile l1 --profile l2 up -d
```

Run the lifecycle after `op-node`, `op-reth`, and `op-batcher` are up:

```bash
./scripts/run-lifecycle.sh
```

To retrieve the table again without resending transactions:

```bash
./scripts/collect-lifecycle-transactions.py
```

The collector scans both chains, reads receipts, verifies L1 timestamps against
`amsterdamTime`, and optionally parses `op-batcher` logs to identify the three
blob batches that carried the relevant L2 blocks.
