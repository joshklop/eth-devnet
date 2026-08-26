#!/usr/bin/env python3
"""Collect OP Stack deployment and lifecycle transaction receipts.

The script uses only JSON-RPC (plus optional `docker logs op-batcher`) so it can
be rerun while the experiment is running. It discovers:

* every L1 op-deployer transaction by deployer nonce;
* the two L1 runtime-account funding transactions;
* the L1 portal deposit and its derived L2 deposit;
* native L2 transfers and the Standard Bridge withdrawal from the test account;
* optional L1 blob transactions that carried those L2 blocks.

It writes machine-readable JSON/CSV and a Markdown gas table.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_DEPLOYER = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
DEFAULT_USER = "0xe05fcc23807536bee418f142d19fa0d21bb0cff7"
L2_STANDARD_BRIDGE = "0x4200000000000000000000000000000000000010"


def hex_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    return int(value, 16) if value.startswith("0x") else int(value)


class Rpc:
    def __init__(self, url: str):
        self.url = url
        self.request_id = 0

    def call(self, method: str, params: list[Any] | None = None) -> Any:
        self.request_id += 1
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or [],
                "id": self.request_id,
            }
        ).encode()
        request = urllib.request.Request(
            self.url, body, {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
        if "error" in payload:
            raise RuntimeError(f"{method}: {payload['error']}")
        return payload["result"]


def transaction_row(
    chain: str,
    phase: str,
    tx: dict[str, Any],
    receipt: dict[str, Any],
    block: dict[str, Any],
    amsterdam_time: int,
    note: str = "",
) -> dict[str, Any]:
    gas_used = hex_int(receipt.get("gasUsed"))
    effective_gas_price = hex_int(receipt.get("effectiveGasPrice"))
    execution_fee = gas_used * effective_gas_price
    l1_data_fee = hex_int(receipt.get("l1Fee"))
    blob_gas_used = hex_int(receipt.get("blobGasUsed"))
    blob_gas_price = hex_int(receipt.get("blobGasPrice"))
    blob_fee = blob_gas_used * blob_gas_price
    block_time = hex_int(block["timestamp"])
    to = tx.get("to") or receipt.get("contractAddress")
    return {
        "chain": chain,
        "phase": phase,
        "hash": tx["hash"],
        "type": hex_int(tx.get("type")),
        "blockNumber": hex_int(receipt["blockNumber"]),
        "blockTimestamp": block_time,
        "postAmsterdam": chain != "L1" or block_time >= amsterdam_time,
        "transactionIndex": hex_int(receipt.get("transactionIndex")),
        "nonce": hex_int(tx.get("nonce")),
        "from": tx.get("from"),
        "to": to,
        "valueWei": hex_int(tx.get("value")),
        "status": hex_int(receipt.get("status")),
        "gasLimit": hex_int(tx.get("gas")),
        "gasUsed": gas_used,
        "effectiveGasPriceWei": effective_gas_price,
        "executionFeeWei": execution_fee,
        "l1DataGasUsed": hex_int(receipt.get("l1GasUsed")),
        "l1DataGasPriceWei": hex_int(receipt.get("l1GasPrice")),
        "l1DataFeeWei": l1_data_fee,
        "blobGasUsed": blob_gas_used,
        "blobGasPriceWei": blob_gas_price,
        "blobFeeWei": blob_fee,
        "totalObservedFeeWei": execution_fee + l1_data_fee + blob_fee,
        "inputSelector": (tx.get("input") or "")[:10],
        "note": note,
    }


def scan_blocks(rpc: Rpc, end_block: int):
    for number in range(end_block + 1):
        block = rpc.call("eth_getBlockByNumber", [hex(number), True])
        if block is not None:
            yield block


def load_portal(state_file: Path) -> str:
    state = json.loads(state_file.read_text())
    deployments = state.get("opChainDeployments") or []
    if not deployments:
        raise RuntimeError(f"no opChainDeployments in {state_file}")
    return deployments[0]["OptimismPortalProxy"].lower()


def deployment_phase(nonce: int, deployment_last_nonce: int) -> str:
    if nonce <= 4:
        return f"deploy-superchain-{nonce + 1:02d}"
    if nonce < deployment_last_nonce:
        return f"deploy-implementations-{nonce - 4:02d}"
    return "deploy-op-chain"


def collect_batcher_channels(container: str) -> list[dict[str, Any]]:
    try:
        lines = subprocess.check_output(
            ["docker", "logs", container], stderr=subprocess.STDOUT, text=True
        ).splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"warning: could not read {container} logs: {error}")
        return []

    last_published: tuple[str, int] | None = None
    channels: list[dict[str, Any]] = []
    for line in lines:
        published = re.search(
            r'Publishing transaction.*service=batcher tx=(0x[0-9a-f]+).*nonce=(\d+)',
            line,
        )
        if published:
            last_published = (published.group(1), int(published.group(2)))

        closed = re.search(
            r'Channel closed.*oldest_l2=\S+:(\d+) latest_l2=\S+:(\d+)', line
        )
        if closed and last_published:
            channels.append(
                {
                    "start": int(closed.group(1)),
                    "end": int(closed.group(2)),
                    "hash": last_published[0],
                    "nonce": last_published[1],
                }
            )
    # Retries can produce duplicate associations; nonce/hash/range uniquely identify one.
    return list(
        {
            (c["nonce"], c["hash"], c["start"], c["end"]): c for c in channels
        }.values()
    )


def write_outputs(
    rows: list[dict[str, Any]],
    output_dir: Path,
    metadata: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "lifecycle-transactions.json"
    csv_path = output_dir / "lifecycle-transactions.csv"
    markdown_path = output_dir / "lifecycle-gas-table.md"

    json_path.write_text(json.dumps({"metadata": metadata, "transactions": rows}, indent=2) + "\n")

    with csv_path.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    headers = [
        "#",
        "Chain",
        "Phase",
        "Nonce",
        "Block",
        "Transaction",
        "Gas used",
        "Effective gas price (wei)",
        "L1 data fee (wei)",
        "Blob gas / fee (wei)",
        "Total observed fee (wei)",
    ]
    lines = [
        "# Glamsterdam OP Stack lifecycle gas",
        "",
        f"All {metadata['l1TransactionCount']} listed L1 transactions executed after Amsterdam activation: **{metadata['allL1PostAmsterdam']}**.",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for index, row in enumerate(rows, 1):
        blob = (
            f"{row['blobGasUsed']} / {row['blobFeeWei']}"
            if row["blobGasUsed"]
            else "—"
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(index),
                    row["chain"],
                    row["phase"],
                    str(row["nonce"]),
                    str(row["blockNumber"]),
                    f"`{row['hash']}`",
                    str(row["gasUsed"]),
                    str(row["effectiveGasPriceWei"]),
                    str(row["l1DataFeeWei"]),
                    blob,
                    str(row["totalObservedFeeWei"]),
                ]
            )
            + " |"
        )

    grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"count": 0, "gasUsed": 0, "feeWei": 0}
    )
    for row in rows:
        phase_group = row["phase"].split("-")[0]
        if row["phase"].startswith("deploy-"):
            phase_group = "deployment"
        elif row["phase"].startswith("batch-submit-"):
            phase_group = "batch-submission"
        elif row["phase"].startswith("l2-transfer-"):
            phase_group = "transfer"
        key = (row["chain"], phase_group)
        grouped[key]["count"] += 1
        grouped[key]["gasUsed"] += row["gasUsed"]
        grouped[key]["feeWei"] += row["totalObservedFeeWei"]

    lines.extend(
        [
            "",
            "## Totals",
            "",
            "| Chain | Group | Transactions | Gas used | Total observed fee (wei) |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for (chain, group), values in grouped.items():
        lines.append(
            f"| {chain} | {group} | {values['count']} | {values['gasUsed']} | {values['feeWei']} |"
        )
    lines.extend(
        [
            "",
            "`totalObservedFeeWei` is execution gas × effective gas price, plus receipt-reported L2 L1-data fee, plus L1 blob gas × blob gas price where present.",
            "",
        ]
    )
    markdown_path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l1-rpc", default="http://127.0.0.1:8545")
    parser.add_argument("--l2-rpc", default="http://127.0.0.1:9545")
    parser.add_argument("--rollup-rpc", default="http://127.0.0.1:8547")
    parser.add_argument("--deployer", default=DEFAULT_DEPLOYER)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--deployment-last-nonce", type=int, default=34)
    parser.add_argument("--setup-last-nonce", type=int, default=36)
    parser.add_argument(
        "--state-file", default="experiment-results/op-deployer-state.json"
    )
    parser.add_argument(
        "--l1-genesis", default="experiment-results/l1-genesis.json"
    )
    parser.add_argument("--output-dir", default="experiment-results")
    parser.add_argument("--batcher-container", default="op-batcher")
    parser.add_argument("--no-batcher", action="store_true")
    args = parser.parse_args()

    deployer = args.deployer.lower()
    user = args.user.lower()
    portal = load_portal(Path(args.state_file))
    l1_genesis = json.loads(Path(args.l1_genesis).read_text())
    amsterdam_time = hex_int(l1_genesis["config"]["amsterdamTime"])

    l1 = Rpc(args.l1_rpc)
    l2 = Rpc(args.l2_rpc)
    rollup = Rpc(args.rollup_rpc)
    l1_end = hex_int(l1.call("eth_blockNumber"))
    l2_end = hex_int(l2.call("eth_blockNumber"))

    rows: list[dict[str, Any]] = []
    l1_by_hash: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for block in scan_blocks(l1, l1_end):
        for tx in block["transactions"]:
            l1_by_hash[tx["hash"]] = (tx, block)
            if (tx.get("from") or "").lower() != deployer:
                continue
            nonce = hex_int(tx["nonce"])
            if nonce <= args.deployment_last_nonce:
                phase = deployment_phase(nonce, args.deployment_last_nonce)
            elif nonce == 35:
                phase = "setup-fund-sequencer"
            elif nonce == 36:
                phase = "setup-fund-batcher"
            elif (tx.get("to") or "").lower() == portal:
                phase = "deposit-l1-portal"
            else:
                continue
            receipt = l1.call("eth_getTransactionReceipt", [tx["hash"]])
            rows.append(
                transaction_row(
                    "L1", phase, tx, receipt, block, amsterdam_time
                )
            )

    relevant_l2_blocks: set[int] = set()
    transfer_number = 0
    for block in scan_blocks(l2, l2_end):
        for tx in block["transactions"]:
            sender = (tx.get("from") or "").lower()
            recipient = (tx.get("to") or "").lower()
            tx_type = hex_int(tx.get("type"))
            if tx_type == 0x7E and recipient == user and hex_int(tx.get("value")) > 0:
                phase = "deposit-l2-derived"
            elif sender == user and recipient == L2_STANDARD_BRIDGE:
                phase = "withdrawal-l2-standard-bridge"
            elif sender == user:
                transfer_number += 1
                phase = f"l2-transfer-{transfer_number}"
            else:
                continue
            receipt = l2.call("eth_getTransactionReceipt", [tx["hash"]])
            relevant_l2_blocks.add(hex_int(receipt["blockNumber"]))
            rows.append(
                transaction_row(
                    "L2", phase, tx, receipt, block, amsterdam_time
                )
            )

    if not args.no_batcher:
        seen_hashes: set[str] = set()
        for channel in collect_batcher_channels(args.batcher_container):
            if not any(channel["start"] <= n <= channel["end"] for n in relevant_l2_blocks):
                continue
            tx_hash = channel["hash"]
            if tx_hash in seen_hashes:
                continue
            seen_hashes.add(tx_hash)
            tx_and_block = l1_by_hash.get(tx_hash)
            if tx_and_block is None:
                tx = l1.call("eth_getTransactionByHash", [tx_hash])
                if tx is None:
                    continue
                block = l1.call("eth_getBlockByNumber", [tx["blockNumber"], True])
            else:
                tx, block = tx_and_block
            receipt = l1.call("eth_getTransactionReceipt", [tx_hash])
            rows.append(
                transaction_row(
                    "L1",
                    f"batch-submit-l2-{channel['start']}-{channel['end']}",
                    tx,
                    receipt,
                    block,
                    amsterdam_time,
                    "supports lifecycle L2 transaction finalization",
                )
            )

    phase_order = {
        "setup-fund-sequencer": 100,
        "setup-fund-batcher": 101,
        "deposit-l1-portal": 200,
        "deposit-l2-derived": 201,
        "l2-transfer-1": 300,
        "l2-transfer-2": 301,
        "l2-transfer-3": 302,
        "withdrawal-l2-standard-bridge": 400,
    }

    def sort_key(row: dict[str, Any]):
        if row["phase"].startswith("deploy-"):
            return (0, row["nonce"])
        if row["phase"].startswith("batch-submit-"):
            return (500, row["nonce"])
        return (phase_order.get(row["phase"], 450), row["nonce"])

    rows.sort(key=sort_key)
    if not rows:
        raise RuntimeError("no lifecycle transactions found")

    sync_status = rollup.call("optimism_syncStatus")
    withdrawal_blocks = [
        row["blockNumber"]
        for row in rows
        if row["phase"] == "withdrawal-l2-standard-bridge"
    ]
    metadata = {
        "l1Rpc": args.l1_rpc,
        "l2Rpc": args.l2_rpc,
        "rollupRpc": args.rollup_rpc,
        "l1ChainId": hex_int(l1.call("eth_chainId")),
        "l2ChainId": hex_int(l2.call("eth_chainId")),
        "l1ScannedThroughBlock": l1_end,
        "l2ScannedThroughBlock": l2_end,
        "amsterdamTime": amsterdam_time,
        "deployer": deployer,
        "testUser": user,
        "optimismPortalProxy": portal,
        "l1TransactionCount": sum(row["chain"] == "L1" for row in rows),
        "l2TransactionCount": sum(row["chain"] == "L2" for row in rows),
        "allL1PostAmsterdam": all(
            row["postAmsterdam"] for row in rows if row["chain"] == "L1"
        ),
        "withdrawalL2Block": withdrawal_blocks[0] if withdrawal_blocks else None,
        "finalizedL2Block": sync_status["finalized_l2"]["number"],
        "withdrawalBlockFinalized": bool(withdrawal_blocks)
        and sync_status["finalized_l2"]["number"] >= withdrawal_blocks[0],
    }
    write_outputs(rows, Path(args.output_dir), metadata)
    print(
        f"wrote {len(rows)} transactions to {args.output_dir}; "
        f"withdrawalBlockFinalized={metadata['withdrawalBlockFinalized']}"
    )


if __name__ == "__main__":
    main()
